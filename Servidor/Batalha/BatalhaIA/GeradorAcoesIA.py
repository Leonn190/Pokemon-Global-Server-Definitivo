from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .ContextoIA import ContextoIA, fnum, inteiro, normalizar


@dataclass(slots=True)
class CandidatoIA:
    tipo: str
    acao: dict[str, Any]
    pokemon: object
    categoria: str = "neutro"
    ataque: dict[str, Any] | None = None
    propriedades: dict[str, Any] | None = None
    metadados: dict[str, Any] = field(default_factory=dict)
    alvos: list[object] = field(default_factory=list)
    area_id: str | None = None
    custo_base: float = 0.0
    score: float = 0.0
    estimativa: dict[str, Any] = field(default_factory=dict)

    @property
    def pokemon_id(self) -> str:
        return str(self.acao.get("pokemon_id") or "")

    def copia_acao(self) -> dict[str, Any]:
        return copy.deepcopy(self.acao)


class GeradorAcoesIA:
    def __init__(self, propriedades_ataques: Mapping[str, dict] | None = None):
        self.propriedades_ataques = dict(propriedades_ataques or {})

    def gerar(self, contexto: ContextoIA) -> list[CandidatoIA]:
        candidatos: list[CandidatoIA] = []
        for pokemon in sorted(contexto.aliados_ativos, key=lambda p: (-contexto.atributo(p, "Int"), -contexto.atributo(p, "Vel"), contexto.pid(p))):
            por_pokemon: list[CandidatoIA] = []
            por_pokemon.extend(self._gerar_ataques(contexto, pokemon))
            por_pokemon.extend(self._gerar_trocas_reserva(contexto, pokemon))
            por_pokemon.extend(self._gerar_movimentos(contexto, pokemon))
            por_pokemon.extend(self._gerar_trocas_posicao(contexto, pokemon))
            for candidato in por_pokemon:
                if candidato.ataque:
                    candidato.metadados = contexto.metadados_ataque(candidato.ataque)
            por_pokemon = self._ordenar_pre_analise(contexto, pokemon, por_pokemon)
            limite_base = int(contexto.config.max_candidatos_por_pokemon)
            limite = max(4, int(6 + contexto.config.dificuldade.inteligencia * max(1, limite_base - 6)))
            candidatos.extend(por_pokemon[:limite])
        return candidatos

    def _ordenar_pre_analise(self, contexto: ContextoIA, pokemon, candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        """Pré-filtro de Inteligência.

        Inteligência controla qualidade e quantidade das microanálises iniciais.
        Memória entra aqui para fazer mover/proteger/trocar subir antes da simulação.
        """
        memoria = getattr(contexto, "memoria_ia", None)
        peso_mem = float(contexto.config.dificuldade.memoria or 0.0)
        foco_mem = float(getattr(memoria, "foco_player", {}).get(contexto.pid(pokemon), 0) or 0) * peso_mem if memoria is not None else 0.0

        def chave(cand: CandidatoIA):
            meta = cand.metadados if isinstance(cand.metadados, dict) else {}
            prioridade = fnum(meta.get("prioridade_simulacao"), 0.35)
            score = prioridade * contexto.config.dificuldade.conhecimento
            score += max(0.0, 1.0 - contexto.vida_pct(pokemon)) * 0.35
            if cand.categoria in {"cura", "defesa"} or cand.tipo in {"movimento", "troca_reserva", "troca_posicao"}:
                score += foco_mem * 0.35
            if cand.categoria == "dano":
                score += contexto.config.personalidade.agressividade * 0.10
            return (-score, str(cand.tipo), str(cand.area_id or ""))

        candidatos.sort(key=chave)
        return candidatos

    def _gerar_ataques(self, contexto: ContextoIA, pokemon) -> list[CandidatoIA]:
        if not contexto.apto_para_acao(pokemon, "ataque"):
            return []
        saida: list[CandidatoIA] = []
        for ataque in contexto.ataques(pokemon):
            props = contexto.buscar_propriedades_ataque(ataque)
            if not isinstance(props, dict):
                continue
            estilo = str(props.get("estilo_logico") or "").strip().lower()
            if estilo == "passivo" or estilo not in {"alvo", "ativo"}:
                continue
            custo = fnum(props.get("custo", ataque.get("custo", ataque.get("Custo", 0.0))), 0.0)
            if contexto.energia_atual(pokemon) < custo:
                continue
            categoria = self.classificar_ataque(ataque, props)
            if estilo == "ativo":
                saida.append(self._montar_candidato_ataque(contexto, pokemon, ataque, props, categoria, None, []))
                continue
            saida.extend(self._gerar_ataques_alvo(contexto, pokemon, ataque, props, categoria))
        return saida

    def _gerar_ataques_alvo(self, contexto: ContextoIA, pokemon, ataque: dict, props: dict, categoria: str) -> list[CandidatoIA]:
        if not contexto.alvificacao_suportada_ia(props):
            return []
        alvo_cfg = contexto.config_alvo(props)
        tipo_alvo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        saida: list[CandidatoIA] = []

        if tipo_alvo == "pokemon":
            for alvo in self._pokemons_candidatos_para_props(contexto, pokemon, props, categoria):
                if not contexto.pokemon_permitido_para_ataque(pokemon, alvo, props):
                    continue
                acao = self._base_acao_ataque(contexto, pokemon, ataque, props)
                selecao = {
                    "tipo": "pokemon",
                    "pokemon_id": contexto.pid(alvo),
                    "reserva": bool(contexto.reserva(alvo)),
                    "grupo": 0,
                    "ordem": 0,
                    "config": copy.deepcopy(alvo_cfg),
                }
                area_id = contexto.area_id(alvo)
                if area_id:
                    selecao["area_id"] = area_id
                    selecao["areas"] = [area_id]
                acao["alvo"] = {"tipo": "multi", "alvos": [selecao]}
                saida.append(
                    CandidatoIA(
                        tipo="ataque",
                        acao=acao,
                        pokemon=pokemon,
                        categoria=categoria,
                        ataque=copy.deepcopy(ataque),
                        propriedades=copy.deepcopy(props),
                        alvos=[alvo],
                        area_id=contexto.area_id(alvo),
                        custo_base=fnum(props.get("custo"), 0.0),
                    )
                )
            return saida

        for area_id in self._areas_candidatas_para_props(contexto, pokemon, props, categoria):
            if not contexto.area_permitida_para_ataque(pokemon, area_id, props):
                continue
            alvos = contexto.alvos_por_area(area_id, props)
            if not alvos:
                # O coletor ate aceita algumas areas vazias, mas o rodador falha sem alvo real.
                # A IA evita gastar acao nessas tentativas vazias.
                continue
            acao = self._base_acao_ataque(contexto, pokemon, ataque, props)
            acao["alvo"] = {"tipo": "multi", "alvos": [{
                "tipo": "area",
                "area_id": str(area_id),
                "grupo": 0,
                "ordem": 0,
                "config": copy.deepcopy(alvo_cfg),
                "areas": contexto.areas_afetadas(area_id, props),
            }]}
            saida.append(
                CandidatoIA(
                    tipo="ataque",
                    acao=acao,
                    pokemon=pokemon,
                    categoria=categoria,
                    ataque=copy.deepcopy(ataque),
                    propriedades=copy.deepcopy(props),
                    alvos=alvos,
                    area_id=str(area_id),
                    custo_base=fnum(props.get("custo"), 0.0),
                )
            )
        return saida

    def _base_acao_ataque(self, contexto: ContextoIA, pokemon, ataque: dict, props: dict) -> dict[str, Any]:
        code = contexto.code_ataque(ataque, props)
        return {
            "tipo": "ataque",
            "estilo": str(props.get("estilo_logico") or "alvo"),
            "pokemon_id": contexto.pid(pokemon),
            "lado_id": contexto.lado(pokemon),
            "rodada": contexto.rodada,
            "ataque": {
                "ID": code,
                "Code": code,
                "nome": ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or props.get("nome"),
                "Tipo": ataque.get("Tipo") or ataque.get("tipo") or (props.get("parametros") or {}).get("tipo"),
            },
            "alvo": None,
        }

    def _montar_candidato_ataque(self, contexto: ContextoIA, pokemon, ataque: dict, props: dict, categoria: str, area_id: str | None, alvos: list) -> CandidatoIA:
        return CandidatoIA(
            tipo="ataque",
            acao=self._base_acao_ataque(contexto, pokemon, ataque, props),
            pokemon=pokemon,
            categoria=categoria,
            ataque=copy.deepcopy(ataque),
            propriedades=copy.deepcopy(props),
            alvos=list(alvos or []),
            area_id=area_id,
            custo_base=fnum(props.get("custo"), 0.0),
        )

    def _pokemons_candidatos_para_props(self, contexto: ContextoIA, pokemon, props: dict, categoria: str) -> list:
        alvo_cfg = contexto.config_alvo(props)
        permitidos = alvo_cfg.get("lados_permitidos") if isinstance(alvo_cfg.get("lados_permitidos"), (list, tuple, set)) else []
        incluir_reserva = bool(alvo_cfg.get("inclui_reserva", False))
        pools = []
        for token in [str(x).lower() for x in permitidos] or ["qualquer"]:
            if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"}:
                pools.extend(contexto.inimigos_ativos)
                if incluir_reserva:
                    pools.extend(contexto.reservas_inimigas)
            elif token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"}:
                pools.extend(contexto.aliados_ativos)
                if incluir_reserva:
                    pools.extend(contexto.reservas_aliadas)
            elif token in {"usuario", "proprio", "si_mesmo"}:
                pools.append(pokemon)
            else:
                pools.extend(contexto.aliados_ativos)
                pools.extend(contexto.inimigos_ativos)
                if incluir_reserva:
                    pools.extend(contexto.reservas_aliadas)
                    pools.extend(contexto.reservas_inimigas)
        unicos = []
        vistos = set()
        for alvo in pools:
            if alvo is None or not contexto.vivo(alvo):
                continue
            pid = contexto.pid(alvo)
            if pid in vistos:
                continue
            vistos.add(pid)
            unicos.append(alvo)
        return unicos

    def _areas_candidatas_para_props(self, contexto: ContextoIA, pokemon, props: dict, categoria: str) -> list[str]:
        alvo_cfg = contexto.config_alvo(props)
        permitidos = alvo_cfg.get("lados_permitidos") if isinstance(alvo_cfg.get("lados_permitidos"), (list, tuple, set)) else []
        areas: list[str] = []
        for area in contexto.todas_areas():
            area_id = str(area.get("id"))
            if not area_id:
                continue
            if contexto.area_permitida_para_ataque(pokemon, area_id, props):
                areas.append(area_id)

        # Ordenacao inicial barata para reduzir explosao em ataques de area.
        def chave(area_id: str):
            alvos = contexto.alvos_por_area(area_id, props)
            inimigos = sum(1 for a in alvos if contexto.lado(a) != contexto.lado(pokemon))
            aliados = sum(1 for a in alvos if contexto.lado(a) == contexto.lado(pokemon))
            vida_alvo = min((contexto.vida_pct(a) for a in alvos), default=1.0)
            ameaca = sum(contexto.ameacas_por_pokemon.get(contexto.pid(a), 0.0) for a in alvos)
            if categoria in {"cura", "defesa", "buff", "energia"}:
                return (aliados <= 0, -ameaca, vida_alvo, area_id)
            return (inimigos <= 0, -inimigos, vida_alvo, aliados, area_id)

        areas.sort(key=chave)
        limite = 12 if any(str(x).lower() in {"qualquer", "todos", "ambos"} for x in permitidos) else 9
        return areas[:limite]

    def _gerar_trocas_reserva(self, contexto: ContextoIA, pokemon) -> list[CandidatoIA]:
        if not contexto.apto_para_acao(pokemon, "troca_reserva") or not contexto.reservas_aliadas:
            return []
        hp = contexto.vida_pct(pokemon)
        energia = contexto.energia_pct(pokemon)
        ameacado = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0) > 0
        efeitos_ruins = contexto.qtd_efeitos_negativos(pokemon)
        memoria = getattr(contexto, "memoria_ia", None)
        foco_mem = float(getattr(memoria, "foco_player", {}).get(contexto.pid(pokemon), 0) or 0) * float(contexto.config.dificuldade.memoria or 0.0) if memoria is not None else 0.0
        # Mesmo com inteligência baixa, gera fallback se a situação for crítica ou a memória indicar foco recorrente.
        situacao_critica = hp < 0.35 or energia < 0.18 or efeitos_ruins > 0 or ameacado or foco_mem > 0
        if not situacao_critica and contexto.config.dificuldade.inteligencia < 0.35:
            return []

        reservas = sorted(
            contexto.reservas_aliadas,
            key=lambda r: (-(contexto.vida_pct(r) * 0.65 + contexto.energia_pct(r) * 0.35), -contexto.atributo(r, "Int"), contexto.pid(r)),
        )
        saida: list[CandidatoIA] = []
        for reserva in reservas[:3]:
            acao = {
                "tipo": "troca_reserva",
                "estilo": "movimento",
                "pokemon_id": contexto.pid(pokemon),
                "pokemon_reserva_id": contexto.pid(reserva),
                "troca_reserva_id": contexto.pid(reserva),
                "lado_id": contexto.lado(pokemon),
                "rodada": contexto.rodada,
                "origem": {"tipo": "area", "area_id": contexto.area_id(pokemon)},
                "destino": {"tipo": "reserva", "pokemon_id": contexto.pid(reserva)},
            }
            saida.append(
                CandidatoIA(
                    tipo="troca_reserva",
                    acao=acao,
                    pokemon=pokemon,
                    categoria="troca",
                    alvos=[reserva],
                    area_id=contexto.area_id(pokemon),
                    custo_base=20.0,
                    estimativa={"reserva": reserva},
                )
            )
        return saida

    def _gerar_movimentos(self, contexto: ContextoIA, pokemon) -> list[CandidatoIA]:
        if not contexto.apto_para_acao(pokemon, "movimento"):
            return []
        origem = contexto.area_id(pokemon)
        lado_atual = contexto.area_lado(origem)
        areas = [a for a in contexto.areas_do_lado(lado_atual) if a != origem and not contexto.area_ocupada(a)]
        if not areas:
            return []

        def distancia(area_id: str) -> int:
            c1 = contexto.coords_area(origem)
            c2 = contexto.coords_area(area_id)
            if c1 is None or c2 is None:
                return 9
            return abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])

        memoria = getattr(contexto, "memoria_ia", None)
        areas.sort(key=lambda aid: (
            aid in contexto.areas_miradas,
            float(getattr(memoria, "areas_player", {}).get(str(aid), 0) or 0) * float(contexto.config.dificuldade.memoria or 0.0) if memoria is not None else 0.0,
            distancia(aid),
            aid,
        ))
        saida: list[CandidatoIA] = []
        for area_id in areas[:4]:
            acao = {
                "tipo": "movimento",
                "estilo": "movimento",
                "pokemon_id": contexto.pid(pokemon),
                "lado_id": contexto.lado(pokemon),
                "rodada": contexto.rodada,
                "origem": {"tipo": "area", "area_id": origem},
                "destino": {"tipo": "area", "area_id": area_id},
            }
            saida.append(CandidatoIA(tipo="movimento", acao=acao, pokemon=pokemon, categoria="movimento", area_id=area_id, custo_base=15.0))
        return saida

    def _gerar_trocas_posicao(self, contexto: ContextoIA, pokemon) -> list[CandidatoIA]:
        if not contexto.apto_para_acao(pokemon, "troca_posicao"):
            return []
        memoria = getattr(contexto, "memoria_ia", None)
        foco_mem = float(getattr(memoria, "foco_player", {}).get(contexto.pid(pokemon), 0) or 0) * float(contexto.config.dificuldade.memoria or 0.0) if memoria is not None else 0.0
        if contexto.config.dificuldade.raciocinio < 0.45 and not contexto.usar_leitura_player and foco_mem <= 0:
            return []
        saida: list[CandidatoIA] = []
        pid = contexto.pid(pokemon)
        ameaca_pokemon = contexto.ameacas_por_pokemon.get(pid, 0.0) + foco_mem * 12.0
        for aliado in contexto.aliados_ativos:
            if aliado is pokemon or not contexto.vivo(aliado):
                continue
            # Prioriza trocar um alvo ameacado por outro mais robusto.
            if ameaca_pokemon <= 0 and contexto.vida_pct(pokemon) > 0.45:
                continue
            if contexto.vida_pct(aliado) <= contexto.vida_pct(pokemon) and contexto.barreira(aliado) <= contexto.barreira(pokemon):
                continue
            acao = {
                "tipo": "troca_posicao",
                "estilo": "movimento",
                "pokemon_id": pid,
                "pokemon_destino_id": contexto.pid(aliado),
                "lado_id": contexto.lado(pokemon),
                "rodada": contexto.rodada,
                "origem": {"tipo": "area", "area_id": contexto.area_id(pokemon)},
                "destino": {"tipo": "area", "area_id": contexto.area_id(aliado), "pokemon_id": contexto.pid(aliado)},
            }
            saida.append(CandidatoIA(tipo="troca_posicao", acao=acao, pokemon=pokemon, categoria="troca_posicao", alvos=[aliado], area_id=contexto.area_id(aliado), custo_base=20.0))
        return saida[:2]

    @staticmethod
    def classificar_ataque(ataque: Mapping[str, Any], props: Mapping[str, Any]) -> str:
        nome = normalizar(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or props.get("nome"))
        code = inteiro(ataque.get("ID") or ataque.get("Code") or props.get("ID"), 0)
        if code == 2 or nome == "biscoito":
            return "cura"
        if code == 5 or nome == "proteger":
            return "defesa"
        if code == 7 or nome == "recarga":
            return "energia"
        if code in {3, 14} or nome in {"enraivecer", "tankar"}:
            return "buff"
        if code in {4, 13} or nome in {"provocar", "resetar"}:
            return "controle"
        return "dano"
