from __future__ import annotations

import copy
from itertools import combinations
from typing import Any, Iterable

from .ContextoIA import ContextoIA, fnum
from .GeradorAcoesIA import CandidatoIA


class MacroSimulador:
    """Simulador macro real de jogadas completas.

    O combo é executado em uma cópia da Partida com ColetorAcoes/RodadorTurno reais.
    Logs são silenciados na cópia para a simulação não poluir a partida original.
    """

    def simular_jogada(
        self,
        contexto: ContextoIA,
        combo: list[CandidatoIA],
        *,
        acoes_oponente: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        combo = self._normalizar_combo(contexto, combo)
        if not combo:
            return {"origem": "macro_real", "score": float("-inf"), "acoes": [], "quantidade_acoes": 0}
        real = self._simular_com_servidor_real(contexto, combo, acoes_oponente=acoes_oponente)
        if real:
            return real
        score = self._pontuar_combo_resumido(contexto, combo)
        return {
            "origem": "macro_resumido_fallback",
            "score": score,
            "acoes": [c.copia_acao() for c in combo],
            "quantidade_acoes": len(combo),
        }

    def refinar(self, contexto: ContextoIA, candidatos: list[CandidatoIA], rng) -> list[CandidatoIA]:
        budget = int(contexto.config.orcamento_macro_simulacoes)
        if budget <= 0 or not candidatos:
            return []

        pool = sorted(candidatos, key=lambda c: c.score, reverse=True)[: max(8, contexto.config.max_candidatos_planejamento)]
        melhor_combo: list[CandidatoIA] = []
        melhor_score = float("-inf")
        simuladas = 0

        for tamanho in range(1, min(contexto.config.max_acoes_por_lado, len(pool)) + 1):
            combo = self._normalizar_combo(contexto, pool[:tamanho])
            if not combo:
                continue
            resultado = self.simular_jogada(contexto, combo)
            score = float(resultado.get("score", float("-inf")))
            simuladas += 1
            if score > melhor_score:
                melhor_score = score
                melhor_combo = combo
            if simuladas >= budget:
                return melhor_combo

        tamanho_max = min(contexto.config.max_acoes_por_lado, 5, len(pool))
        for tamanho in range(2, tamanho_max + 1):
            for combo_bruto in combinations(pool[: min(len(pool), 18)], tamanho):
                combo = self._normalizar_combo(contexto, combo_bruto)
                if len(combo) != tamanho:
                    continue
                resultado = self.simular_jogada(contexto, combo)
                score = float(resultado.get("score", float("-inf")))
                simuladas += 1
                if score > melhor_score:
                    melhor_score = score
                    melhor_combo = combo
                if simuladas >= budget:
                    return melhor_combo

        while simuladas < budget:
            combo = []
            embaralhado = list(pool)
            rng.shuffle(embaralhado)
            for cand in embaralhado:
                tent = self._normalizar_combo(contexto, combo + [cand])
                if len(tent) > len(combo):
                    combo = tent
                if len(combo) >= contexto.config.max_acoes_por_lado:
                    break
            resultado = self.simular_jogada(contexto, combo)
            score = float(resultado.get("score", float("-inf")))
            simuladas += 1
            if score > melhor_score:
                melhor_score = score
                melhor_combo = combo
        return melhor_combo

    def _simular_com_servidor_real(
        self,
        contexto: ContextoIA,
        combo: list[CandidatoIA],
        *,
        acoes_oponente: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        try:
            partida = self._clonar_partida_silenciosa(contexto.partida)
            antes = self._snapshot(partida)
            jogadas: dict[int, dict[str, Any]] = {
                int(contexto.lado_id): {
                    "lado_id": int(contexto.lado_id),
                    "acoes": [c.copia_acao() for c in combo],
                    "modo_teste": False,
                }
            }
            for acao in list(acoes_oponente or []):
                if not isinstance(acao, dict):
                    continue
                lado = int(acao.get("lado_id") or self._lado_oponente(contexto) or 0)
                jogadas.setdefault(lado, {"lado_id": lado, "acoes": [], "modo_teste": False})
                jogadas[lado]["acoes"].append(copy.deepcopy(acao))
            for lado in self._lados_vivos(partida):
                jogadas.setdefault(int(lado), {"lado_id": int(lado), "acoes": [], "modo_teste": False})

            partida.jogadas_recebidas = copy.deepcopy(jogadas)
            invalidas = []
            try:
                # Usa o fluxo real completo da rodada: ColetorAcoes, RodadorTurno,
                # fim de rodada, substituições e efeitos derivados. Logs foram
                # silenciados na cópia, então a simulação não polui a partida real.
                resultado_rodada = partida.resolver_rodada()
                invalidas = list((resultado_rodada or {}).get("erros") or [])
            except Exception:
                acoes, invalidas = partida.coletor_acoes.coletar(jogadas)
                partida.rodador_turno.rodar(acoes, invalidas)
            depois = self._snapshot(partida)
            resultado = self._resumir_diff(contexto, combo, antes, depois, invalidas)
            resultado["acoes"] = [c.copia_acao() for c in combo]
            resultado["quantidade_acoes"] = len(combo)
            return resultado
        except Exception as exc:
            return {
                "origem": "macro_real_falhou",
                "erro": str(exc),
                "score": self._pontuar_combo_resumido(contexto, combo),
                "acoes": [c.copia_acao() for c in combo],
                "quantidade_acoes": len(combo),
            }

    def _clonar_partida_silenciosa(self, partida):
        clone = copy.deepcopy(partida)
        try:
            clone.registrar_evento_log = lambda *args, **kwargs: None
        except Exception:
            pass
        try:
            clone.avisos = []
        except Exception:
            pass
        return clone

    def _normalizar_combo(self, contexto: ContextoIA, candidatos: Iterable[CandidatoIA]) -> list[CandidatoIA]:
        combo: list[CandidatoIA] = []
        contagem: dict[str, int] = {}
        energia_restante: dict[str, float] = {}
        alvos_troca = set()
        for cand in sorted(candidatos, key=lambda c: c.score, reverse=True):
            pid = cand.pokemon_id
            if not pid:
                continue
            if len(combo) >= contexto.config.max_acoes_por_lado:
                break
            if contagem.get(pid, 0) >= contexto.config.max_acoes_por_pokemon:
                continue
            if pid in alvos_troca:
                continue
            if cand.tipo == "troca_reserva":
                if contagem.get(pid, 0) > 0:
                    continue
                reserva_id = cand.acao.get("pokemon_reserva_id") or cand.acao.get("troca_reserva_id")
                if reserva_id:
                    alvos_troca.add(str(reserva_id))
            ordem_pokemon = contagem.get(pid, 0) + 1
            mult = 1.10 if ordem_pokemon >= 2 else 1.0
            custo = float(cand.custo_base or 0.0) * mult
            energia = energia_restante.setdefault(pid, contexto.energia_atual(cand.pokemon))
            if energia < custo:
                continue
            energia_restante[pid] = energia - custo
            contagem[pid] = ordem_pokemon
            combo.append(cand)
        return combo

    def _snapshot(self, partida) -> dict[str, dict[str, Any]]:
        saida: dict[str, dict[str, Any]] = {}
        pokemons = list(getattr(partida, "pokemons", []) or [])
        if not pokemons and hasattr(partida, "pokemons_por_id"):
            pokemons = list(getattr(partida, "pokemons_por_id", {}).values())
        for p in pokemons:
            pid = str(getattr(p, "id_batalha", "") or "")
            if not pid:
                continue
            vida_max = fnum(p.obter_atributo("Vida", 1.0), 1.0) if hasattr(p, "obter_atributo") else 1.0
            energia_max = fnum(p.obter_atributo("EneM", 1.0), 1.0) if hasattr(p, "obter_atributo") else 1.0
            saida[pid] = {
                "vida": fnum(getattr(p, "VidaAtual", 0.0), 0.0),
                "vida_max": max(1.0, vida_max),
                "energia": fnum(getattr(p, "EnergiaAtual", 0.0), 0.0),
                "energia_max": max(1.0, energia_max),
                "barreira": fnum(getattr(p, "BarreiraAtual", 0.0), 0.0),
                "vivo": 1.0 if bool(p.esta_vivo() if hasattr(p, "esta_vivo") else getattr(p, "vivo", False)) else 0.0,
                "lado_id": int(getattr(p, "lado_id", 0) or 0),
                "area_id": str(getattr(p, "area_id", "") or ""),
                "ativo": bool(getattr(p, "ativo", False)),
                "reserva": bool(getattr(p, "reserva", False)),
                "efeitos": self._assinatura_efeitos(p),
                "valor_alvo": self._valor_pokemon_snapshot(p),
            }
        return saida

    @staticmethod
    def _assinatura_efeitos(pokemon) -> set[str]:
        return {str((e or {}).get("code") or (e or {}).get("nome") or "") for e in list(getattr(pokemon, "efeitos_formais", []) or []) if isinstance(e, dict)}

    @staticmethod
    def _valor_pokemon_snapshot(pokemon) -> float:
        try:
            atk = fnum(pokemon.obter_atributo("Atk", 0.0), 0.0)
            spa = fnum(pokemon.obter_atributo("SpA", 0.0), 0.0)
            vida = fnum(pokemon.obter_atributo("Vida", 1.0), 1.0)
            ene = fnum(pokemon.obter_atributo("EneM", 1.0), 1.0)
            return max(atk, spa) * 0.45 + vida * 0.15 + ene * 0.08
        except Exception:
            return 30.0

    def _resumir_diff(self, contexto: ContextoIA, combo: list[CandidatoIA], antes: dict, depois: dict, invalidas=None) -> dict[str, Any]:
        p = float(contexto.config.dificuldade.previsao or 0.0)
        per = contexto.config.personalidade
        rac = float(contexto.config.dificuldade.raciocinio or 0.0)
        resultado: dict[str, Any] = {
            "origem": "macro_real",
            "score": 0.0,
            "score_real": 0.0,
            "score_heuristico": self._pontuar_combo_resumido(contexto, combo),
            "previsao": p,
            "camadas_consideradas": self._camadas_consideradas(p),
            "dano_causado": 0.0,
            "dano_aliado": 0.0,
            "cura_feita": 0.0,
            "cura_inimigo": 0.0,
            "barreira_gerada": 0.0,
            "energia_recuperada": 0.0,
            "energia_gasta": 0.0,
            "alvos_mortos": [],
            "aliados_mortos": [],
            "efeitos_positivos": 0,
            "efeitos_negativos": 0,
            "efeitos_removidos": 0,
            "movimentos_melhores": 0,
            "acao_invalida": bool(invalidas),
            "invalidas": list(invalidas or []),
        }
        ids_ia = {c.pokemon_id for c in combo}

        for pid, a in antes.items():
            d = depois.get(pid, a)
            lado = int(a.get("lado_id", -999))
            aliado = lado == contexto.lado_id
            delta_vida = float(d.get("vida", 0.0)) - float(a.get("vida", 0.0))
            if delta_vida < 0:
                if aliado:
                    resultado["dano_aliado"] += abs(delta_vida)
                    resultado["score_real"] -= abs(delta_vida) * (0.75 + per.cautela + p * 0.25)
                else:
                    resultado["dano_causado"] += abs(delta_vida)
                    resultado["score_real"] += abs(delta_vida) * (0.55 + per.agressividade + rac * 0.25)
            elif delta_vida > 0:
                if aliado:
                    resultado["cura_feita"] += delta_vida
                    resultado["score_real"] += delta_vida * (0.45 + per.suporte + per.cautela * 0.35)
                else:
                    resultado["cura_inimigo"] += delta_vida
                    resultado["score_real"] -= delta_vida * (0.45 + per.agressividade)

            if p >= 0.25 and float(a.get("vivo", 0.0)) > 0 and float(d.get("vivo", 0.0)) <= 0:
                valor = float(a.get("valor_alvo", 30.0))
                if aliado:
                    resultado["aliados_mortos"].append(pid)
                    resultado["score_real"] -= (80.0 + valor) * (0.65 + per.cautela)
                else:
                    resultado["alvos_mortos"].append(pid)
                    resultado["score_real"] += (70.0 + valor) * (0.65 + per.foco)

            if p >= 0.35:
                delta_energia = float(d.get("energia", 0.0)) - float(a.get("energia", 0.0))
                if aliado:
                    if pid in ids_ia and delta_energia < 0:
                        resultado["energia_gasta"] += abs(delta_energia)
                        resultado["score_real"] -= abs(delta_energia) * 0.08 * (0.5 + rac)
                    elif delta_energia > 0:
                        resultado["energia_recuperada"] += delta_energia
                        resultado["score_real"] += delta_energia * 0.12 * (0.5 + rac)

            if p >= 0.45:
                delta_barreira = float(d.get("barreira", 0.0)) - float(a.get("barreira", 0.0))
                if delta_barreira > 0 and aliado:
                    resultado["barreira_gerada"] += delta_barreira
                    resultado["score_real"] += delta_barreira * (0.22 + per.cautela * 0.28)
                efeitos_antes = set(a.get("efeitos") or set())
                efeitos_depois = set(d.get("efeitos") or set())
                novos = efeitos_depois - efeitos_antes
                removidos = efeitos_antes - efeitos_depois
                if novos:
                    if aliado:
                        resultado["efeitos_positivos"] += len(novos)
                        resultado["score_real"] += len(novos) * 7.0 * (0.6 + per.suporte)
                    else:
                        resultado["efeitos_negativos"] += len(novos)
                        resultado["score_real"] += len(novos) * 7.0 * (0.6 + per.agressividade)
                if removidos:
                    resultado["efeitos_removidos"] += len(removidos)
                    resultado["score_real"] += len(removidos) * 3.0 * rac

            if p >= 0.60 and aliado and str(a.get("area_id") or "") != str(d.get("area_id") or ""):
                destino = str(d.get("area_id") or "")
                memoria = getattr(contexto, "memoria_ia", None)
                perigo = float(getattr(memoria, "areas_player", {}).get(destino, 0) or 0) if memoria is not None else 0.0
                if destino and destino not in contexto.areas_miradas and perigo <= 0:
                    resultado["movimentos_melhores"] += 1
                    resultado["score_real"] += 8.0 * (0.5 + per.cautela)

        if resultado["acao_invalida"]:
            resultado["score_real"] -= 60.0 + 20.0 * len(resultado["invalidas"])

        # Previsão baixa ainda usa execute real, mas o score final confia menos nas camadas profundas.
        confianca_real = 0.35 + 0.65 * p
        resultado["score"] = resultado["score_heuristico"] * (1.0 - confianca_real) + resultado["score_real"] * confianca_real
        return resultado

    def _pontuar_combo_resumido(self, contexto: ContextoIA, combo: list[CandidatoIA]) -> float:
        score = sum(float(c.score or 0.0) for c in combo)
        dano_por_alvo: dict[str, float] = {}
        cura_por_alvo: dict[str, float] = {}
        protegidos = set()
        trocados = set()
        atacantes_por_alvo: dict[str, int] = {}

        for cand in combo:
            if cand.tipo == "troca_reserva":
                trocados.add(cand.pokemon_id)
            if cand.categoria == "defesa":
                for alvo in cand.alvos or [cand.pokemon]:
                    protegidos.add(contexto.pid(alvo))
            alvo_id = (cand.estimativa or {}).get("alvo_principal_id")
            if alvo_id:
                dano_por_alvo[alvo_id] = dano_por_alvo.get(alvo_id, 0.0) + float((cand.estimativa or {}).get("melhor_dano") or 0.0)
                atacantes_por_alvo[alvo_id] = atacantes_por_alvo.get(alvo_id, 0) + 1
            if "cura_total" in cand.estimativa:
                for alvo in cand.alvos:
                    pid = contexto.pid(alvo)
                    cura_por_alvo[pid] = cura_por_alvo.get(pid, 0.0) + float(cand.estimativa.get("cura_total") or 0.0)

        for pid, dano in dano_por_alvo.items():
            alvo = contexto.obter_pokemon(pid)
            if alvo is None:
                continue
            vida = contexto.vida_atual(alvo)
            excesso = max(0.0, dano - vida * (1.0 + contexto.config.margem_overkill))
            if excesso > 0:
                score -= excesso * (0.15 + 0.35 * contexto.config.dificuldade.raciocinio)
            if atacantes_por_alvo.get(pid, 0) > 1:
                score += 10.0 * contexto.config.personalidade.foco

        for pid, cura in cura_por_alvo.items():
            alvo = contexto.obter_pokemon(pid)
            if alvo is None:
                continue
            faltante = max(0.0, contexto.vida_max(alvo) - contexto.vida_atual(alvo))
            excesso = max(0.0, cura - faltante)
            score -= excesso * 0.18

        if contexto.usar_leitura_player:
            for pid, ameaca in contexto.ameacas_por_pokemon.items():
                if pid in protegidos:
                    score += ameaca * 0.45
                if pid in trocados:
                    score += ameaca * 0.55
        return score

    @staticmethod
    def _camadas_consideradas(previsao: float) -> list[str]:
        camadas = ["vida", "dano", "cura"]
        if previsao >= 0.25:
            camadas.extend(["morte", "overkill"])
        if previsao >= 0.35:
            camadas.append("energia")
        if previsao >= 0.45:
            camadas.extend(["barreira", "efeitos"])
        if previsao >= 0.60:
            camadas.extend(["movimento", "posicionamento"])
        if previsao >= 0.80:
            camadas.extend(["ordem_real", "estado_completo"])
        return camadas

    def _lados_vivos(self, partida) -> set[int]:
        lados: set[int] = set()
        pokemons = list(getattr(partida, "pokemons", []) or [])
        if not pokemons and hasattr(partida, "pokemons_por_id"):
            pokemons = list(getattr(partida, "pokemons_por_id", {}).values())
        for p in pokemons:
            try:
                vivo = bool(p.esta_vivo()) if hasattr(p, "esta_vivo") else bool(getattr(p, "vivo", False))
                if vivo:
                    lados.add(int(getattr(p, "lado_id", 0) or 0))
            except Exception:
                pass
        return lados

    def _lado_oponente(self, contexto: ContextoIA) -> int | None:
        for lado in sorted({contexto.lado(p) for p in contexto.inimigos if contexto.vivo(p)}):
            if int(lado) != int(contexto.lado_id):
                return int(lado)
        return None
