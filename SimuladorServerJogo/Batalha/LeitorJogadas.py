from __future__ import annotations

import math
import re
from typing import Dict, List

from SimuladorServerJogo.Batalha.FuncoesAtaques import executar_ponto_ataque
from SimuladorServerJogo.Batalha.FraquezasResistencias import modificador_tipo as modificador_tipo_csv
from SimuladorServerJogo.Batalha.IA.BotBatalha import BotBatalha
from SimuladorServerJogo.Batalha.ObjetoBatalha import ObjetoBatalha
from SimuladorServerJogo.Batalha.SimuladorFisica import SimuladorFisica
from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha


class LeitorJogadas:
    _REGEX_ESCALA_STAT = re.compile(r"\(([\d.,]+)%\s+de\s+([A-Za-zÀ-ÿ]+)\)", re.IGNORECASE)
    _REGEX_EXECUTA = re.compile(r"executa[^\d]*(\d+(?:[.,]\d+)?)%\s+da\s+vida", re.IGNORECASE)
    _REGEX_CR = re.compile(r"\+(\d+(?:[.,]\d+)?)%\s+de\s+(CrC|CrD)", re.IGNORECASE)
    _REGEX_RECOIL = re.compile(r"usu[aá]rio\s+recebe\s+(\d+(?:[.,]\d+)?)%\s+do\s+dano\s+causado", re.IGNORECASE)
    _REGEX_RECUPERA_CUSTO = re.compile(r"recupera\s+(\d+(?:[.,]\d+)?)%\s+de\s+ene\s+gasta", re.IGNORECASE)

    def __init__(self) -> None:
        self._fisica: SimuladorFisica | None = None
        self._sistema_aux: SistemaBatalha | None = None
        self._bot_ia = BotBatalha()

    @staticmethod
    def _fnum(valor, default: float = 0.0) -> float:
        try:
            if isinstance(valor, str):
                return float(valor.replace(",", "."))
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _norm(valor: object) -> str:
        return str(valor or "").strip().casefold()

    @staticmethod
    def _log_evento(log: Dict[str, object], tick: int, tipo: str, **dados) -> Dict[str, object]:
        evento = {"tick": int(tick), "tipo": str(tipo), **dados}
        por_tick = log.setdefault("eventos_por_tick", {})
        por_tick.setdefault(str(int(tick)), []).append(evento)
        log.setdefault("eventos", []).append(evento)
        log["tick_final"] = max(int(log.get("tick_final", 0)), int(tick))
        return evento

    @staticmethod
    def _nome_combatente(sistema: SistemaBatalha, pokemon_id: object) -> str:
        pokemon = sistema.obter_pokemon(pokemon_id) if sistema is not None else None
        if pokemon is None:
            return ""
        return str(getattr(pokemon, "Nome", "") or getattr(pokemon, "Especie", "") or "")

    @staticmethod
    def _round_num(valor: object, casas: int = 4) -> float:
        try:
            return round(float(valor), int(casas))
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _round_pos(cls, valor: object) -> List[float] | None:
        if not isinstance(valor, (list, tuple)) or len(valor) != 2:
            return None
        return [cls._round_num(valor[0]), cls._round_num(valor[1])]

    @classmethod
    def _angulo_graus(cls, vetor: object) -> float | None:
        if not isinstance(vetor, (list, tuple)) or len(vetor) != 2:
            return None
        try:
            return round(math.degrees(math.atan2(float(vetor[1]), float(vetor[0]))), 2)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalizar_valor_publico(cls, valor: object) -> object:
        if isinstance(valor, dict):
            return {str(chave): cls._normalizar_valor_publico(item) for chave, item in valor.items()}
        if isinstance(valor, tuple):
            return [cls._normalizar_valor_publico(item) for item in valor]
        if isinstance(valor, list):
            return [cls._normalizar_valor_publico(item) for item in valor]
        if isinstance(valor, float):
            return round(valor, 4)
        return valor

    def _anexar_nomes_publicos(self, sistema: SistemaBatalha, publico: Dict[str, object]) -> Dict[str, object]:
        saida = dict(publico or {})
        executor_id = str(saida.get("executor_id") or "")
        alvo_id = str(saida.get("alvo_id") or "")
        pokemon_id = str(saida.get("pokemon_id") or "")
        if executor_id and not str(saida.get("executor_nome") or ""):
            nome = self._nome_combatente(sistema, executor_id)
            if nome:
                saida["executor_nome"] = nome
        if alvo_id and not str(saida.get("alvo_nome") or ""):
            nome = self._nome_combatente(sistema, alvo_id)
            if nome:
                saida["alvo_nome"] = nome
        if pokemon_id and not str(saida.get("pokemon_nome") or ""):
            nome = self._nome_combatente(sistema, pokemon_id)
            if nome:
                saida["pokemon_nome"] = nome
        if str(saida.get("saiu") or "") and not str(saida.get("saiu_nome") or ""):
            nome = self._nome_combatente(sistema, saida.get("saiu"))
            if nome:
                saida["saiu_nome"] = nome
        if str(saida.get("entrou") or "") and not str(saida.get("entrou_nome") or ""):
            nome = self._nome_combatente(sistema, saida.get("entrou"))
            if nome:
                saida["entrou_nome"] = nome
        alvos_ids = [str(item) for item in list(saida.get("alvo_ids") or []) if str(item)]
        if alvos_ids and "alvos" not in saida:
            saida["alvos"] = [
                {"id": alvo_uid, "nome": self._nome_combatente(sistema, alvo_uid)}
                for alvo_uid in alvos_ids
            ]
        return saida

    def _jogada_publica_ordem(self, sistema: SistemaBatalha, jogada: Dict[str, object], tick_base: int) -> Dict[str, object]:
        ignorar = {
            "indice_entrada",
            "executor",
            "spec",
            "inteligencia",
            "acertos_total",
            "pendencias_execucao",
            "finalizada",
            "start_tick",
            "duracao_estimada",
            "end_tick_estimada",
        }
        ordem = {
            str(chave): self._normalizar_valor_publico(valor)
            for chave, valor in dict(jogada or {}).items()
            if str(chave) not in ignorar
        }
        if "start_tick" in jogada:
            ordem["tick_inicio"] = max(0, int(jogada.get("start_tick", 0) or 0) - int(tick_base))
        return self._anexar_nomes_publicos(sistema, ordem)

    def _traduzir_evento_publico(self, sistema: SistemaBatalha, evento: Dict[str, object]) -> tuple[str | None, Dict[str, object] | None]:
        tipo = str(evento.get("tipo") or "").strip().casefold()
        executor_id = str(evento.get("executor_id") or evento.get("pokemon_id") or "")
        alvo_id = str(evento.get("alvo_id") or "")
        detalhe = evento.get("detalhe") if isinstance(evento.get("detalhe"), dict) else {}
        pacote = evento.get("pacote") if isinstance(evento.get("pacote"), dict) else {}

        if tipo in {"hook_ataque", "jogadas_ia"}:
            return (None, None)

        if tipo == "acao_iniciada":
            publico = {
                "tipo": "acao",
                "executor_id": executor_id,
                "ataque": str(evento.get("ataque") or ""),
                "estilo": str(evento.get("estilo") or ""),
                "posicao": self._round_pos(evento.get("posicao_inicial")),
            }
            destino = self._round_pos(evento.get("destino"))
            if destino is not None:
                publico["destino"] = destino
            if self._fnum(evento.get("velocidade"), 0.0) > 0.0:
                publico["velocidade"] = self._round_num(evento.get("velocidade"))
            if isinstance(evento.get("alvo_ids"), list) and list(evento.get("alvo_ids") or []):
                publico["alvo_ids"] = [str(item) for item in list(evento.get("alvo_ids") or []) if str(item)]
            return ("inicializacao", {k: v for k, v in publico.items() if v not in (None, [], "")})

        if tipo == "troca":
            publico = {"tipo": "troca", "executor_id": executor_id}
            if detalhe:
                for chave in ("saiu", "entrou", "slot", "status"):
                    if chave in detalhe:
                        publico[chave] = self._normalizar_valor_publico(detalhe.get(chave))
            return ("inicializacao", publico)

        if tipo == "movimento":
            colisoes = [dict(item) for item in list(detalhe.get("colisoes") or []) if isinstance(item, dict)]
            if colisoes:
                publico = {
                    "tipo": "colisao_movimento",
                    "pokemon_id": executor_id,
                    "origem": self._round_pos(detalhe.get("origem")),
                    "posicao": self._round_pos(detalhe.get("destino")),
                    "destino_planejado": self._round_pos(detalhe.get("destino_planejado")),
                    "colisoes": self._normalizar_valor_publico(colisoes),
                }
                return ("segmentacao", {k: v for k, v in publico.items() if v not in (None, "", [])})
            if bool(detalhe.get("concluido", False)):
                publico = {
                    "tipo": "movimento_finalizado",
                    "pokemon_id": executor_id,
                    "origem": self._round_pos(detalhe.get("origem")),
                    "posicao": self._round_pos(detalhe.get("destino")),
                    "destino_planejado": self._round_pos(detalhe.get("destino_planejado")),
                }
                return ("finalizacao", {k: v for k, v in publico.items() if v not in (None, "", [])})
            return (None, None)

        if tipo == "movimento_reacao_iniciado":
            publico = {
                "tipo": "movimento_reacao",
                "pokemon_id": executor_id,
                "colidiu_com": alvo_id,
                "origem": self._round_pos(detalhe.get("origem")),
                "destino": self._round_pos(detalhe.get("destino")),
                "velocidade": self._round_num(detalhe.get("velocidade", 0.0)),
                "causa": str(detalhe.get("causa") or "colisao_pokemon"),
            }
            return ("inicializacao", {k: v for k, v in publico.items() if v not in (None, "", [])})

        if tipo in {"objeto_criado", "objeto_movimento", "objeto_finalizado"}:
            objeto = detalhe.get("objeto") if isinstance(detalhe.get("objeto"), dict) else (detalhe if detalhe else {})
            subtipo = str(objeto.get("subtipo") or detalhe.get("subtipo") or "objeto")
            publico = {
                "tipo": subtipo,
                "objeto_id": str(objeto.get("id") or detalhe.get("objeto_id") or ""),
                "executor_id": str(evento.get("executor_id") or objeto.get("dono_id") or ""),
                "posicao": self._round_pos(objeto.get("posicao")),
                "destino": self._round_pos((objeto.get("dados_extras") or {}).get("destino")) if isinstance(objeto.get("dados_extras"), dict) else None,
                "velocidade": self._round_num(objeto.get("velocidade_tiles_tick", 0.0)),
            }
            angulo = self._angulo_graus(objeto.get("direcao"))
            if angulo is not None and subtipo in {"tiro", "area"}:
                publico["angulo"] = angulo
            if "raio_atual" in detalhe:
                publico["raio"] = self._round_num(detalhe.get("raio_atual"))
            elif subtipo == "zona" and objeto.get("raio") is not None:
                publico["raio"] = self._round_num(objeto.get("raio"))
            if "alcance_atual" in detalhe:
                publico["alcance"] = self._round_num(detalhe.get("alcance_atual"))
            if tipo == "objeto_movimento":
                return (None, None)
            fase = "inicializacao" if tipo == "objeto_criado" else "finalizacao"
            return (fase, {k: v for k, v in publico.items() if v not in (None, "")})

        if tipo == "dano":
            publico = {
                "tipo": "dano",
                "executor_id": executor_id,
                "alvo_id": alvo_id,
                "dano": self._round_num(detalhe.get("dano_hp", pacote.get("dano_final", 0.0))),
            }
            if float(detalhe.get("dano_barreira", 0.0) or 0.0) > 0.0:
                publico["dano_barreira"] = self._round_num(detalhe.get("dano_barreira"))
            if "morto" in detalhe:
                publico["morto"] = bool(detalhe.get("morto"))
            if "critico" in pacote:
                publico["critico"] = bool(pacote.get("critico"))
            detalhes_dano = {
                "dano_bruto": pacote.get("dano_bruto"),
                "bonus_intensidade": pacote.get("bonus_intensidade"),
                "multiplicador_dano_causado": pacote.get("multiplicador_dano_causado"),
                "multiplicador_critico": pacote.get("multiplicador_critico"),
                "perfuracao": pacote.get("perfuracao"),
                "defesa_base": pacote.get("defesa_base"),
                "defesa_reduzida_por_perfuracao": pacote.get("defesa_reduzida_por_perfuracao"),
                "defesa_aplicada": pacote.get("defesa_aplicada"),
                "multiplicador_tipo": pacote.get("tipo_multiplicador"),
                "multiplicador_hook": pacote.get("multiplicador_hook"),
                "delta_hook": pacote.get("delta_hook"),
                "dano_pos_defesa": pacote.get("dano_pos_defesa"),
                "dano_pos_tipo": pacote.get("dano_pos_tipo"),
                "multiplicador_dano_recebido": pacote.get("multiplicador_dano_recebido"),
            }
            publico["detalhes"] = {str(chave): self._round_num(valor) for chave, valor in detalhes_dano.items() if valor not in (None, "")}
            return ("segmentacao", publico)

        if tipo == "cura":
            return (
                "segmentacao",
                {
                    "tipo": "cura",
                    "executor_id": executor_id,
                    "alvo_id": alvo_id,
                    "valor": self._round_num(detalhe.get("cura_final", 0.0)),
                },
            )

        if tipo == "barreira":
            return (
                "segmentacao",
                {
                    "tipo": "barreira",
                    "executor_id": executor_id,
                    "alvo_id": alvo_id,
                    "valor": self._round_num(detalhe.get("barreira_ganha", 0.0)),
                    "barreira_total": self._round_num(detalhe.get("barreira_total", 0.0)),
                },
            )

        if tipo in {"efeito_aplicado", "efeito_self", "efeito_expirado"}:
            publico = {
                "tipo": "efeito",
                "executor_id": executor_id,
                "alvo_id": alvo_id or executor_id,
                "efeito": str(detalhe.get("efeito") or evento.get("efeito") or ""),
                "status": str(detalhe.get("status") or "ok"),
            }
            fase = "passiva" if tipo == "efeito_expirado" else "segmentacao"
            return (fase, {k: v for k, v in publico.items() if v not in (None, "")})

        if tipo == "reset_variacoes":
            return ("segmentacao", {"tipo": "reset_variacoes", "executor_id": executor_id, "alvo_id": alvo_id})

        if tipo in {"ricochete", "ricochete_pokemon", "ricochete_campo"}:
            publico = {
                "tipo": tipo,
                "objeto_id": str(evento.get("objeto_id") or ""),
                "alvo_id": alvo_id,
            }
            if "restante" in evento:
                publico["ricochetes_restantes"] = int(evento.get("restante") or 0)
            return ("segmentacao", {k: v for k, v in publico.items() if v not in (None, "")})

        if tipo in {"recoil", "execucao"}:
            publico = {
                "tipo": tipo,
                "executor_id": executor_id,
                "alvo_id": alvo_id or executor_id,
            }
            if detalhe:
                publico["valor"] = self._round_num(detalhe.get("dano_hp", detalhe.get("vida_antes", 0.0)))
            return ("segmentacao", publico)

        if tipo == "energia":
            if str(detalhe.get("status") or "").strip().casefold() == "ignorado_morto":
                return (None, None)
            publico = {
                "tipo": "energia",
                "pokemon_id": executor_id,
                "valor": self._round_num(detalhe.get("ganho_final", 0.0)),
                "energia": self._round_num(detalhe.get("energia", 0.0)),
            }
            motivo = str(detalhe.get("motivo") or "")
            if motivo:
                publico["motivo"] = motivo
            fase = "passiva" if motivo.casefold() == "fimturno" else "segmentacao"
            return (fase, publico)

        if tipo == "jogada_descartada":
            publico = {
                "tipo": "jogada_descartada",
                "executor_id": executor_id,
                "executor_nome": str(evento.get("executor_nome") or ""),
                "motivo": str(evento.get("motivo") or ""),
            }
            ataque = str(evento.get("ataque") or "")
            if ataque:
                publico["ataque"] = ataque
            return ("finalizacao", publico)

        if tipo == "fim_turno":
            publico = {"tipo": "fim_turno", "pokemon_id": str(evento.get("pokemon_id") or "")}
            if detalhe:
                if "dano_hp" in detalhe:
                    publico["dano"] = self._round_num(detalhe.get("dano_hp", 0.0))
                if "cura_final" in detalhe:
                    publico["cura"] = self._round_num(detalhe.get("cura_final", 0.0))
                if "ganho_final" in detalhe:
                    publico["energia"] = self._round_num(detalhe.get("ganho_final", 0.0))
                motivo = str(detalhe.get("motivo") or "")
                if motivo:
                    publico["motivo"] = motivo
            return ("passiva", publico)

        if tipo in {"impacto_cancelado", "acao_bloqueada", "acao_finalizada"}:
            publico = {
                "tipo": tipo,
                "executor_id": executor_id,
                "ataque": str(evento.get("ataque") or ""),
                "estilo": str(evento.get("estilo") or ""),
            }
            motivo = str(evento.get("motivo") or "")
            if motivo:
                publico["motivo"] = motivo
            return ("finalizacao", {k: v for k, v in publico.items() if v not in (None, "")})

        publico = {"tipo": tipo}
        if executor_id:
            publico["executor_id"] = executor_id
        if alvo_id:
            publico["alvo_id"] = alvo_id
        if detalhe:
            publico["detalhe"] = self._normalizar_valor_publico(detalhe)
        return ("segmentacao", publico)

    def _construir_historico_publico(self, sistema: SistemaBatalha, log: Dict[str, object], tick_base: int) -> List[Dict[str, object]]:
        historico: List[Dict[str, object]] = []
        por_tick = log.get("eventos_por_tick") if isinstance(log.get("eventos_por_tick"), dict) else {}
        for tick_abs in sorted((int(chave) for chave in por_tick.keys())):
            bloco = {"tick": max(0, int(tick_abs) - int(tick_base))}
            for evento in list(por_tick.get(str(tick_abs)) or []):
                fase, publico = self._traduzir_evento_publico(sistema, dict(evento or {}))
                if not fase or not isinstance(publico, dict):
                    continue
                bloco.setdefault(fase, []).append(self._anexar_nomes_publicos(sistema, publico))
            if len(bloco) > 1:
                historico.append(bloco)
        return historico

    @staticmethod
    def _lista_pokemon_com_uid(lista: object) -> bool:
        if not isinstance(lista, list) or not lista:
            return False
        return all(isinstance(item, dict) and str(item.get("uid") or item.get("id") or item.get("ID") or "") for item in lista)

    @classmethod
    def _diff_snapshot(cls, antes: object, depois: object) -> object | None:
        if isinstance(depois, dict):
            if not isinstance(antes, dict):
                return cls._normalizar_valor_publico(depois)
            diff = {}
            for chave, valor in depois.items():
                subdiff = cls._diff_snapshot(antes.get(chave), valor)
                if subdiff is not None:
                    diff[str(chave)] = subdiff
            return diff or None
        if isinstance(depois, list):
            if cls._lista_pokemon_com_uid(depois):
                antes_lista = antes if isinstance(antes, list) else []
                antes_map = {str(item.get("uid") or item.get("id") or item.get("ID") or ""): dict(item) for item in antes_lista if isinstance(item, dict)}
                depois_map = {str(item.get("uid") or item.get("id") or item.get("ID") or ""): dict(item) for item in depois if isinstance(item, dict)}
                ordem_antes = [str(item.get("uid") or item.get("id") or item.get("ID") or "") for item in antes_lista if isinstance(item, dict)]
                ordem_depois = [str(item.get("uid") or item.get("id") or item.get("ID") or "") for item in depois if isinstance(item, dict)]
                itens = []
                for uid in ordem_depois:
                    atual = depois_map.get(uid)
                    if atual is None:
                        continue
                    anterior = antes_map.get(uid)
                    if anterior is None:
                        itens.append(cls._normalizar_valor_publico(atual))
                        continue
                    subdiff = cls._diff_snapshot(anterior, atual)
                    if isinstance(subdiff, dict) and subdiff:
                        itens.append({"uid": uid, **subdiff})
                removidos = [uid for uid in ordem_antes if uid not in depois_map]
                payload = {"__tipo__": "lista_pokemon"}
                if ordem_antes != ordem_depois:
                    payload["ordem"] = ordem_depois
                if itens:
                    payload["itens"] = itens
                if removidos:
                    payload["removidos"] = removidos
                return payload if len(payload) > 1 else None
            normal_antes = cls._normalizar_valor_publico(antes)
            normal_depois = cls._normalizar_valor_publico(depois)
            return normal_depois if normal_antes != normal_depois else None
        normal_antes = cls._normalizar_valor_publico(antes)
        normal_depois = cls._normalizar_valor_publico(depois)
        return normal_depois if normal_antes != normal_depois else None

    def _resultado_publico_diff(self, sistema: SistemaBatalha, snapshot_inicial: Dict[str, object], snapshot_final: Dict[str, object]) -> Dict[str, object]:
        diff = self._diff_snapshot(snapshot_inicial, snapshot_final)
        resultado = {
            "batalha_id": str(snapshot_final.get("batalha_id") or snapshot_inicial.get("batalha_id") or sistema.BatalhaId),
            "tipo": str(snapshot_final.get("tipo") or snapshot_inicial.get("tipo") or sistema.Tipo),
            "turno_atual": int(snapshot_final.get("turno_atual", snapshot_inicial.get("turno_atual", sistema.TurnoAtual)) or sistema.TurnoAtual),
            "tick_global": int(snapshot_final.get("tick_global", snapshot_inicial.get("tick_global", sistema.TickGlobal)) or sistema.TickGlobal),
        }
        if isinstance(diff, dict):
            resultado.update(diff)
        return resultado

    def _construir_log_publico(
        self,
        sistema: SistemaBatalha,
        log: Dict[str, object],
        ordenadas: List[Dict[str, object]],
        descartadas: List[Dict[str, object]],
        *,
        tick_base: int,
        snapshot_inicial: Dict[str, object],
        snapshot_final: Dict[str, object],
    ) -> Dict[str, object]:
        return {
            "batalha_id": str(snapshot_inicial.get("batalha_id") or sistema.BatalhaId),
            "tipo": str(snapshot_inicial.get("tipo") or sistema.Tipo),
            "turno_atual": int(log.get("turno", sistema.TurnoAtual) or sistema.TurnoAtual),
            "clima": str(snapshot_inicial.get("clima") or sistema.ClimaAtual or ""),
            "arena": dict(snapshot_inicial.get("arena") or sistema.ArenaAtual or {}),
            "ordem_logica": [self._jogada_publica_ordem(sistema, item, tick_base) for item in ([*list(descartadas or []), *list(ordenadas or [])]) if isinstance(item, dict)],
            "historico": self._construir_historico_publico(sistema, log, tick_base),
            "resultado": self._resultado_publico_diff(sistema, snapshot_inicial, snapshot_final),
        }

    def _descricao_ataque(self, ataque: Dict[str, object]) -> str:
        nivel = max(1, min(3, int(self._fnum(ataque.get("Nivel", 1), 1))))
        for indice in (nivel, 1, 2, 3):
            chave = f"Descrição Nivel {indice}"
            if str(ataque.get(chave) or "").strip():
                return str(ataque.get(chave) or "").strip()
        for chave in ("Descricao", "Descrição", "descrição", "descricao"):
            if str(ataque.get(chave) or "").strip():
                return str(ataque.get(chave) or "").strip()
        return ""

    def _componentes_percentuais(self, trecho: str) -> list[dict[str, object]]:
        componentes = []
        for perc, stat in self._REGEX_ESCALA_STAT.findall(trecho or ""):
            valor = self._fnum(perc, 0.0)
            chave = str(stat or "").strip()
            chave_norm = chave.casefold()
            if chave_norm == "vida":
                if "perdida" in str(trecho or "").casefold():
                    chave = "VidaPerdida"
                else:
                    chave = "Vida"
            componentes.append({"escala": valor, "atributo": chave})
        return componentes

    def _extrair_efeitos_texto(self, sistema: SistemaBatalha, trecho: str) -> list[str]:
        texto_norm = str(trecho or "").casefold()
        encontrados = []
        for dados in sistema.BibliotecaEfeitos.values():
            bruto = str(dados.get("Efeito") or "").strip()
            if bruto and bruto.casefold() in texto_norm:
                encontrados.append(bruto)
        for nome in ("Protegido", "Biscoito"):
            if nome.casefold() in texto_norm:
                encontrados.append(nome)
        return encontrados

    def _interpretar_ataque(self, sistema: SistemaBatalha, ataque: Dict[str, object] | None) -> Dict[str, object]:
        ataque = dict(ataque or {})
        estilo = str(ataque.get("Estilo") or ataque.get("estilo") or "status").strip().casefold()
        descricao = self._descricao_ataque(ataque)
        fluxo = dict(sistema.BibliotecaFluxos.get(self._norm(ataque.get("Ataque") or ataque.get("Nome") or ""), {}))
        subfluxos = [dict(item) for item in list(fluxo.get("fluxos") or []) if isinstance(item, dict)]

        spec = {
            "nome": str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or ""),
            "tipo": str(ataque.get("Tipo") or ataque.get("tipo") or "normal").strip().casefold() or "normal",
            "estilo": estilo,
            "descricao": descricao,
            "fluxo": fluxo,
            "subfluxos": subfluxos,
            "dano_componentes": [],
            "cura_componentes": [],
            "barreira_componentes": [],
            "efeitos_self": [],
            "efeitos_target": [],
            "critico_bonus": {"CrC": 0.0, "CrD": 0.0},
            "execucao_threshold": 0.0,
            "recoil_percent": 0.0,
            "recupera_energia_percentual_custo": 0.0,
            "alvo_time": "inimigo",
            "dano_tipo": "especial" if "dano especial" in descricao.casefold() else "fisico",
            "reseta_variacoes_alvo": "remove todas as varia" in descricao.casefold(),
        }

        for sentenca in re.split(r"(?<=[.!?])\s+", descricao):
            trecho = str(sentenca or "").strip()
            trecho_norm = trecho.casefold()
            componentes = self._componentes_percentuais(trecho)
            if ("cura" in trecho_norm) and componentes:
                spec["cura_componentes"].extend(componentes)
                spec["alvo_time"] = "aliado"
            elif "barreira" in trecho_norm and componentes:
                spec["barreira_componentes"].extend(componentes)
            elif ("causa" in trecho_norm or "dano" in trecho_norm) and componentes:
                spec["dano_componentes"].extend(componentes)
            if "usuário ganha" in trecho_norm or "usuario ganha" in trecho_norm:
                spec["efeitos_self"].extend(self._extrair_efeitos_texto(sistema, trecho))
            if "o alvo fica" in trecho_norm or "alvo fica" in trecho_norm or ("ganha" in trecho_norm and "alvo" in trecho_norm):
                spec["efeitos_target"].extend(self._extrair_efeitos_texto(sistema, trecho))
            match_exec = self._REGEX_EXECUTA.search(trecho)
            if match_exec:
                spec["execucao_threshold"] = max(spec["execucao_threshold"], self._fnum(match_exec.group(1), 0.0) / 100.0)
            match_recoil = self._REGEX_RECOIL.search(trecho)
            if match_recoil:
                spec["recoil_percent"] = max(spec["recoil_percent"], self._fnum(match_recoil.group(1), 0.0) / 100.0)
            match_ene = self._REGEX_RECUPERA_CUSTO.search(trecho)
            if match_ene:
                spec["recupera_energia_percentual_custo"] = max(spec["recupera_energia_percentual_custo"], self._fnum(match_ene.group(1), 0.0) / 100.0)
            for bonus, atributo in self._REGEX_CR.findall(trecho):
                spec["critico_bonus"][str(atributo)] = spec["critico_bonus"].get(str(atributo), 0.0) + self._fnum(bonus, 0.0)

        possui_suporte = bool(
            spec["cura_componentes"]
            or spec["barreira_componentes"]
            or spec["efeitos_self"]
            or spec["efeitos_target"]
            or spec["reseta_variacoes_alvo"]
            or float(spec.get("recupera_energia_percentual_custo", 0.0) or 0.0) > 0.0
        )
        if not spec["dano_componentes"] and bool(str(descricao or "").strip()) and estilo in {"movimento", "area", "tiro", "alvo"} and not possui_suporte:
            atributo = "SpA" if spec["dano_tipo"] == "especial" else "Atk"
            spec["dano_componentes"] = [{"escala": 100.0, "atributo": atributo}]
        if estilo == "movimento":
            percentual = 100.0
            for sentenca in re.split(r"(?<=[.!?])\s+", descricao):
                if "avança" in sentenca.casefold() or "avanca" in sentenca.casefold():
                    for componente in self._componentes_percentuais(sentenca):
                        if str(componente.get("atributo")).casefold() == "vel":
                            percentual = self._fnum(componente.get("escala"), 100.0)
                            break
            spec["velocidade_movimento_percentual"] = percentual
        return spec

    def _flow_principal(self, spec: Dict[str, object]) -> Dict[str, object]:
        subfluxos = list(spec.get("subfluxos") or [])
        if subfluxos:
            return dict(subfluxos[0])
        return {
            "alcance": 3.0,
            "largura_teto": 50.0,
            "raio": 1.25,
            "tamanho_elementos": 0.55,
            "intensidade_dano": 1.0,
            "ricocheteia_objetos": False,
            "atravessa_objetos": False,
            "atravessa_pokemons": False,
            "numero_ricochets": 0,
        }

    def _duracao_estimativa(
        self,
        sistema: SistemaBatalha,
        executor,
        jogada: Dict[str, object],
        spec: Dict[str, object],
        fluxo_ref: Dict[str, object] | None = None,
    ) -> int:
        estilo = str(jogada.get("estilo") or spec.get("estilo") or "").casefold()
        destino = jogada.get("destino_mundo")
        origem = executor.Posicao
        fluxo = dict(fluxo_ref or self._flow_principal(spec))
        if estilo == "movimento":
            destino = tuple(destino) if isinstance(destino, (list, tuple)) and len(destino) == 2 else origem
            distancia = math.hypot(float(destino[0]) - float(origem[0]), float(destino[1]) - float(origem[1]))
            velocidade = self._fisica.velocidade_pokemon_tiles_tick(executor, spec.get("velocidade_movimento_percentual", 100.0))
            return max(1, int(math.ceil(distancia / max(0.01, velocidade))))
        if estilo in {"tiro", "area"}:
            destino = tuple(destino) if isinstance(destino, (list, tuple)) and len(destino) == 2 else origem
            distancia = math.hypot(float(destino[0]) - float(origem[0]), float(destino[1]) - float(origem[1]))
            velocidade = max(0.1, self._fnum(fluxo.get("velocidade_tiles_tick", fluxo.get("velocidade", 1.0)), 1.0))
            alcance = max(distancia, self._fnum(fluxo.get("alcance"), distancia))
            return max(1, int(math.ceil(alcance / velocidade)))
        if estilo == "zona":
            raio = max(0.5, self._fnum(fluxo.get("raio"), 1.25))
            velocidade = max(0.1, self._fnum(fluxo.get("velocidade_tiles_tick", fluxo.get("velocidade", raio * 4.0)), raio * 4.0))
            return max(1, int(math.ceil(raio / velocidade)))
        if estilo == "alvo":
            return max(1, int(self._fnum(fluxo.get("tempo_ticks", fluxo.get("delay_ticks", 1)), 1)))
        return 0

    def _ordenar_jogadas(self, sistema: SistemaBatalha, jogadas: List[Dict[str, object]]) -> tuple[List[Dict[str, object]], List[Dict[str, object]]]:
        normalizadas = []
        descartadas = []
        for indice, jogada in enumerate(list(jogadas or [])):
            if not isinstance(jogada, dict):
                continue
            executor = sistema.obter_pokemon(jogada.get("executor_id"))
            if executor is None:
                descartadas.append({**dict(jogada), "indice_entrada": indice, "status": "descartada", "motivo": "executor_invalido"})
                continue
            if executor.ForaDeCombate:
                descartadas.append({**dict(jogada), "indice_entrada": indice, "executor_id": executor.Uid, "executor_nome": executor.Nome, "status": "descartada", "motivo": "executor_fora_de_combate"})
                continue
            ataque = sistema._enriquecer_ataque(jogada.get("ataque")) if isinstance(jogada.get("ataque"), dict) else {}
            spec = self._interpretar_ataque(sistema, ataque)
            estilo_bruto = str(jogada.get("estilo") or "").strip().casefold()
            if not ataque and estilo_bruto:
                spec["estilo"] = estilo_bruto
                spec["nome"] = str(jogada.get("acao_chave") or ("Mover" if estilo_bruto == "movimento" else spec.get("nome") or "")).strip()
                if estilo_bruto == "movimento":
                    spec["velocidade_movimento_percentual"] = float(spec.get("velocidade_movimento_percentual", 100.0) or 100.0)
                    spec["dano_componentes"] = []
            normalizadas.append(
                {
                    **dict(jogada),
                    "indice_entrada": indice,
                    "executor": executor,
                    "executor_id": executor.Uid,
                    "ataque": ataque,
                    "spec": spec,
                    "executor_nome": executor.Nome,
                    "inteligencia": executor.obter_atributo("Int"),
                    "acertos_total": 0,
                    "pendencias_execucao": 0,
                    "finalizada": False,
                }
            )

        max_int = max([item["inteligencia"] for item in normalizadas], default=0.0)
        por_executor: Dict[str, List[Dict[str, object]]] = {}
        for item in normalizadas:
            por_executor.setdefault(str(item["executor_id"]), []).append(item)
        for lista in por_executor.values():
            lista.sort(key=lambda x: int(x.get("indice_entrada", 0)))

        ordenadas = []
        for lista in por_executor.values():
            base = int(sistema.TickGlobal) + max(1, int(round(max_int - float(lista[0]["inteligencia"]))) + 1)
            tick_cursor = base
            for item in lista:
                duracao = self._duracao_estimativa(sistema, item["executor"], item, item["spec"])
                item["start_tick"] = int(tick_cursor)
                item["duracao_estimada"] = int(duracao)
                item["end_tick_estimada"] = int(tick_cursor + max(0, duracao - 1))
                tick_cursor = int(item["end_tick_estimada"]) + 1
                ordenadas.append(item)

        ordenadas.sort(key=lambda x: (int(x.get("start_tick", 0)), -float(x.get("inteligencia", 0.0)), int(x.get("indice_entrada", 0))))
        descartadas.sort(key=lambda x: int(x.get("indice_entrada", 0)))
        return (ordenadas, descartadas)

    def _modificador_tipo(self, tipo_ataque: str, tipos_alvo: List[str]) -> float:
        return float(modificador_tipo_csv(tipo_ataque, tipos_alvo))

    @staticmethod
    def _registrar_acerto_jogada(jogada: Dict[str, object] | None) -> None:
        if not isinstance(jogada, dict):
            return
        jogada["acertos_total"] = int(jogada.get("acertos_total", 0) or 0) + 1

    def _finalizar_jogada(self, sistema: SistemaBatalha, jogada: Dict[str, object], spec: Dict[str, object], log: Dict[str, object], tick: int, motivo: str) -> None:
        if not isinstance(jogada, dict) or bool(jogada.get("finalizada", False)):
            return
        jogada["finalizada"] = True
        self._log_evento(
            log,
            tick,
            "acao_finalizada",
            executor_id=getattr(jogada.get("executor"), "Uid", jogada.get("executor_id", "")),
            ataque=spec.get("nome"),
            estilo=spec.get("estilo"),
            motivo=str(motivo or ""),
        )
        hook_fim = executar_ponto_ataque(
            spec.get("nome"),
            "FIM",
            {
                "sistema": sistema,
                "tick": int(tick),
                "executor": jogada.get("executor"),
                "jogada": jogada,
                "spec": spec,
                "log": log,
                "acertos_total": int(jogada.get("acertos_total", 0) or 0),
                "motivo_finalizacao": str(motivo or ""),
            },
        )
        if hook_fim:
            self._log_evento(log, tick, "hook_ataque", executor_id=getattr(jogada.get("executor"), "Uid", ""), detalhe=dict(hook_fim))

    def _consumir_pendencia_jogada(self, sistema: SistemaBatalha, jogada: Dict[str, object], spec: Dict[str, object], log: Dict[str, object], tick: int, motivo: str) -> None:
        if not isinstance(jogada, dict):
            return
        restante = max(0, int(jogada.get("pendencias_execucao", 0) or 0) - 1)
        jogada["pendencias_execucao"] = restante
        if restante <= 0:
            self._finalizar_jogada(sistema, jogada, spec, log, tick, motivo)

    def _aplicar_defesa_lol(self, dano: float, defesa: float) -> float:
        defesa_real = float(defesa)
        if defesa_real >= 0.0:
            return dano * (100.0 / (100.0 + defesa_real))
        return dano * (2.0 - (100.0 / (100.0 - defesa_real)))

    def _roll_critico(self, sistema: SistemaBatalha, atacante, alvo, spec: Dict[str, object], jogada: Dict[str, object], log: Dict[str, object], tick: int) -> tuple[bool, float]:
        chance = max(0.0, atacante.obter_atributo("CrC") + self._fnum(spec.get("critico_bonus", {}).get("CrC"), 0.0))
        chance *= atacante.MultiplicadoresTemporarios.get("critico_chance", 1.0)
        hook_crit = executar_ponto_ataque(
            spec.get("nome"),
            "CRI",
            {
                "sistema": sistema,
                "tick": int(tick),
                "atacante": atacante,
                "alvo": alvo,
                "spec": spec,
                "jogada": jogada,
                "log": log,
                "chance_critica": chance,
            },
        )
        chance += self._fnum((hook_crit or {}).get("chance_delta"), 0.0)
        chance_max = self._fnum((hook_crit or {}).get("chance_maxima"), 100.0)
        critico = bool((hook_crit or {}).get("forcar_critico", False)) or atacante.Flags.get("focado", False) or (sistema.Rng.random() <= min(1.0, max(0.0, min(chance, chance_max)) / 100.0))
        mult = 1.0
        if critico:
            bonus = max(0.0, atacante.obter_atributo("CrD") + self._fnum(spec.get("critico_bonus", {}).get("CrD"), 0.0))
            mult = (1.5 + (bonus / 100.0)) * atacante.MultiplicadoresTemporarios.get("critico_dano", 1.0)
        mult += self._fnum((hook_crit or {}).get("multiplicador_delta"), 0.0)
        return (bool(critico), float(mult))

    def _calcular_pacote_dano(self, sistema: SistemaBatalha, atacante, alvo, spec: Dict[str, object], fluxo: Dict[str, object], tick: int, jogada: Dict[str, object], log: Dict[str, object]) -> Dict[str, object]:
        componentes = list(spec.get("dano_componentes") or [])
        dano_bruto = 0.0
        perfuracao = 0.0
        for componente in componentes:
            escala = self._fnum(componente.get("escala"), 0.0) / 100.0
            atributo = str(componente.get("atributo") or "").strip()
            if self._norm(atributo) == "vidaperdida":
                valor_attr = max(0.0, atacante.obter_atributo("Vida") - atacante.VidaAtual)
            else:
                valor_attr = atacante.obter_atributo(atributo)
            dano_bruto += float(valor_attr) * escala
            if self._norm(atributo) == "per":
                perfuracao += float(valor_attr) * escala
        bonus_intensidade = float(fluxo.get("intensidade_dano", spec.get("fluxo", {}).get("intensidade_dano", 1.0)) or 1.0)
        mult_dano_causado = float(atacante.MultiplicadoresTemporarios.get("dano_causado", 1.0))
        dano_bruto *= bonus_intensidade
        dano_bruto *= mult_dano_causado

        critico, crit_mult = self._roll_critico(sistema, atacante, alvo, spec, jogada, log, tick)
        dano_critico = dano_bruto * crit_mult
        defesa_chave = "SpD" if str(spec.get("dano_tipo") or "fisico").casefold() == "especial" else "Def"
        defesa_base = max(0.0, alvo.obter_atributo(defesa_chave))
        defesa_reduzida = min(defesa_base, perfuracao * 0.5)
        defesa = max(0.0, defesa_base - defesa_reduzida)
        dano_defendido = self._aplicar_defesa_lol(dano_critico, defesa)
        mod_tipo = self._modificador_tipo(str(spec.get("tipo") or "normal"), list(alvo.Tipos))
        dano_pos_tipo = max(0.0, dano_defendido * mod_tipo)
        dano_final = dano_pos_tipo

        contexto_hook = {
            "sistema": sistema,
            "tick": int(tick),
            "atacante": atacante,
            "alvo": alvo,
            "spec": spec,
            "jogada": jogada,
            "log": log,
            "dano_bruto": dano_bruto,
            "dano_final": dano_final,
            "critico": bool(critico),
            "fluxo": fluxo,
        }
        alteracoes = executar_ponto_ataque(spec.get("nome"), "DMG", contexto_hook)
        mult_hook = 1.0
        delta_hook = 0.0
        if isinstance(alteracoes, dict):
            mult_hook = float(alteracoes.get("multiplicador_dano", 1.0) or 1.0)
            delta_hook = float(alteracoes.get("delta_dano", 0.0) or 0.0)
            dano_final *= mult_hook
            dano_final += delta_hook

        return {
            "origem_id": atacante.Uid,
            "alvo_id": alvo.Uid,
            "tick": int(tick),
            "dano_bruto": round(dano_bruto, 4),
            "bonus_intensidade": round(bonus_intensidade, 4),
            "multiplicador_dano_causado": round(mult_dano_causado, 4),
            "dano_critico": round(dano_critico, 4),
            "multiplicador_critico": round(crit_mult, 4),
            "defesa_base": round(defesa_base, 4),
            "defesa_reduzida_por_perfuracao": round(defesa_reduzida, 4),
            "dano_final": round(max(0.0, dano_final), 4),
            "defesa_aplicada": round(defesa, 4),
            "dano_pos_defesa": round(dano_defendido, 4),
            "dano_pos_tipo": round(dano_pos_tipo, 4),
            "tipo_multiplicador": round(mod_tipo, 4),
            "multiplicador_hook": round(mult_hook, 4),
            "delta_hook": round(delta_hook, 4),
            "multiplicador_dano_recebido": round(float(alvo.MultiplicadoresTemporarios.get("dano_recebido", 1.0)), 4),
            "critico": bool(critico),
            "dano_tipo": str(spec.get("dano_tipo") or "fisico"),
            "perfuracao": round(perfuracao, 4),
        }

    def _aplicar_componentes_auxiliares(self, sistema: SistemaBatalha, executor, alvo, jogada: Dict[str, object], spec: Dict[str, object], log: Dict[str, object], tick: int) -> None:
        hook_aux = executar_ponto_ataque(
            spec.get("nome"),
            "AUX",
            {"sistema": sistema, "tick": int(tick), "executor": executor, "alvo": alvo, "jogada": jogada, "spec": spec, "log": log},
        )
        bonus_cura_fixa = self._fnum((hook_aux or {}).get("cura_bonus_fixa"), 0.0)
        bonus_barreira_fixa = self._fnum((hook_aux or {}).get("barreira_bonus_fixa"), 0.0)
        efeitos_target_extra = list((hook_aux or {}).get("efeitos_target_extra") or [])
        efeitos_self_extra = list((hook_aux or {}).get("efeitos_self_extra") or [])

        for componente in list(spec.get("cura_componentes") or []):
            escala = self._fnum(componente.get("escala"), 0.0) / 100.0
            atributo = str(componente.get("atributo") or "")
            if self._norm(atributo) == "vidaperdida":
                valor = max(0.0, alvo.obter_atributo("Vida") - alvo.VidaAtual) * escala
            else:
                valor = executor.obter_atributo(atributo) * escala
            valor += bonus_cura_fixa
            cura = alvo.ReceberCura(valor, origem=executor, motivo=spec.get("nome"))
            self._log_evento(log, tick, "cura", executor_id=executor.Uid, alvo_id=alvo.Uid, detalhe=cura)

        for componente in list(spec.get("barreira_componentes") or []):
            escala = self._fnum(componente.get("escala"), 0.0) / 100.0
            valor = executor.obter_atributo(str(componente.get("atributo") or "Mag")) * escala + bonus_barreira_fixa
            barreira = alvo.ReceberBarreira(valor)
            self._log_evento(log, tick, "barreira", executor_id=executor.Uid, alvo_id=alvo.Uid, detalhe=barreira)

        for efeito in list(spec.get("efeitos_target") or []) + efeitos_target_extra:
            detalhe = executor.AplicarEfeito(alvo, efeito, origem=executor)
            self._log_evento(log, tick, "efeito_aplicado", executor_id=executor.Uid, alvo_id=alvo.Uid, detalhe=detalhe)
        for efeito in list(spec.get("efeitos_self") or []) + efeitos_self_extra:
            detalhe = executor.ReceberEfeito(efeito, origem=executor)
            self._log_evento(log, tick, "efeito_self", executor_id=executor.Uid, alvo_id=executor.Uid, detalhe=detalhe)

        if spec.get("reseta_variacoes_alvo"):
            alvo.VariacoesFixas = {ch: 0.0 for ch in alvo.VariacoesFixas}
            alvo.Verifica()
            self._log_evento(log, tick, "reset_variacoes", executor_id=executor.Uid, alvo_id=alvo.Uid)

    def _executar_impacto(self, sistema: SistemaBatalha, executor, alvo, jogada: Dict[str, object], spec: Dict[str, object], fluxo: Dict[str, object], log: Dict[str, object], tick: int) -> bool:
        if alvo is None or alvo.ForaDeCombate:
            return False
        hook_pre = executar_ponto_ataque(spec.get("nome"), "PRE", {"sistema": sistema, "tick": tick, "executor": executor, "alvo": alvo, "jogada": jogada, "spec": spec, "log": log})
        if bool(dict(hook_pre or {}).get("cancelar", False)):
            self._log_evento(log, tick, "impacto_cancelado", executor_id=executor.Uid, alvo_id=alvo.Uid, ataque=spec.get("nome"))
            return False

        self._registrar_acerto_jogada(jogada)
        pacote = self._calcular_pacote_dano(sistema, executor, alvo, spec, fluxo, tick, jogada, log)
        detalhe = executor.AplicarDano(alvo, pacote, sistema=sistema, tick=tick)
        self._log_evento(log, tick, "dano", executor_id=executor.Uid, alvo_id=alvo.Uid, ataque=spec.get("nome"), pacote=pacote, detalhe=detalhe)
        self._aplicar_componentes_auxiliares(sistema, executor, alvo, jogada, spec, log, tick)

        if bool(spec.get("execucao_threshold")) and not alvo.ForaDeCombate:
            vida_max = max(1.0, alvo.obter_atributo("Vida"))
            if (alvo.VidaAtual / vida_max) <= float(spec.get("execucao_threshold")):
                detalhe_exec = alvo.TomarDano({"dano_final": alvo.VidaAtual, "origem": executor, "origem_id": executor.Uid}, sistema=sistema, tick=tick)
                self._log_evento(log, tick, "execucao", executor_id=executor.Uid, alvo_id=alvo.Uid, detalhe=detalhe_exec)

        if float(spec.get("recoil_percent", 0.0) or 0.0) > 0.0 and float(detalhe.get("dano_hp", 0.0) or 0.0) > 0.0:
            dano_recoil = float(detalhe.get("dano_hp", 0.0)) * float(spec.get("recoil_percent"))
            detalhe_recoil = executor.TomarDano({"dano_final": dano_recoil, "origem": executor, "origem_id": executor.Uid}, sistema=sistema, tick=tick)
            self._log_evento(log, tick, "recoil", executor_id=executor.Uid, alvo_id=executor.Uid, detalhe=detalhe_recoil)

        hook_pos = executar_ponto_ataque(
            spec.get("nome"),
            "POS",
            {"sistema": sistema, "tick": tick, "executor": executor, "alvo": alvo, "detalhe": detalhe, "spec": spec, "jogada": jogada, "pacote": pacote, "log": log},
        )
        if hook_pos:
            self._log_evento(log, tick, "hook_ataque", executor_id=executor.Uid, alvo_id=alvo.Uid, detalhe=dict(hook_pos))
        return True

    def _alvos_padrao(self, sistema: SistemaBatalha, executor, spec: Dict[str, object], jogada: Dict[str, object]) -> List[object]:
        ids = [str(uid) for uid in list(jogada.get("alvo_ids") or []) if str(uid)]
        if ids:
            return [alvo for alvo in (sistema.obter_pokemon(uid) for uid in ids) if alvo is not None]
        alvo_time = str(spec.get("alvo_time") or "inimigo").casefold()
        if alvo_time == "aliado":
            return [p for p in sistema.listar_ativos(executor.Lado) if not p.ForaDeCombate]
        if alvo_time == "ambos":
            return [p for p in sistema.listar_ativos() if not p.ForaDeCombate]
        return [p for p in sistema.listar_ativos("inimigo" if executor.Lado == "jogador" else "jogador") if not p.ForaDeCombate]

    def _criar_objeto_fluxo(self, executor, spec: Dict[str, object], jogada: Dict[str, object], fluxo: Dict[str, object], tick: int, indice: int) -> ObjetoBatalha:
        destino = jogada.get("destino_mundo")
        origem = executor.Posicao
        if isinstance(destino, (list, tuple)) and len(destino) == 2:
            vetor = (float(destino[0]) - float(origem[0]), float(destino[1]) - float(origem[1]))
        else:
            vetor = (1.0, 0.0)
        direcao = self._fisica._normalizar(vetor)
        subtipo = str(spec.get("estilo") or "")
        velocidade = max(0.1, self._fnum(fluxo.get("velocidade_tiles_tick", fluxo.get("velocidade", 1.0)), 1.0))
        if subtipo == "zona":
            origem = tuple(destino) if isinstance(destino, (list, tuple)) and len(destino) == 2 else origem
        return ObjetoBatalha(
            Id=f"{executor.Uid}:{tick}:{indice}",
            Tipo="ataque",
            Subtipo=subtipo,
            DonoId=executor.Uid,
            Lado=executor.Lado,
            Ataque=dict(jogada.get("ataque") or {}),
            Fluxo=dict(fluxo),
            Posicao=(float(origem[0]), float(origem[1])),
            PosicaoAnterior=(float(origem[0]), float(origem[1])),
            Direcao=direcao,
            VelocidadeTilesTick=velocidade,
            Raio=max(0.2, self._fnum(fluxo.get("tamanho_elementos", fluxo.get("raio", 0.35)), 0.35)),
            InicioTick=int(tick),
            TickAtual=int(tick),
            DuracaoTicks=max(1, int(self._duracao_estimativa(self._sistema_aux, executor, jogada, spec, fluxo))),
            RicochetesRestantes=max(0, int(self._fnum(fluxo.get("numero_ricochets", 0), 0))),
            AtravessaObjetos=bool(fluxo.get("atravessa_objetos", fluxo.get("atravessa_paredes", False))),
            AtravessaPokemons=bool(fluxo.get("atravessa_pokemons", False)),
            AtingeSiMesmo=bool(fluxo.get("subfluxo_atinge_a_si_mesmo", False)),
            IntensidadeDano=float(fluxo.get("intensidade_dano", 1.0) or 1.0),
            DadosExtras={
                "destino": list(destino) if isinstance(destino, (list, tuple)) and len(destino) == 2 else None,
                "alcance": self._fnum(fluxo.get("alcance", 3.0), 3.0),
                "largura_teto": self._fnum(fluxo.get("largura_teto", 50.0), 50.0),
                "raio_max": self._fnum(fluxo.get("raio", 1.25), 1.25),
                "executor_id": executor.Uid,
                "origem_execucao": [float(origem[0]), float(origem[1])],
            },
        )

    def _resolver_objeto(self, sistema: SistemaBatalha, objeto: ObjetoBatalha, executor, jogada: Dict[str, object], spec: Dict[str, object], log: Dict[str, object], tick: int) -> None:
        avancado = self._fisica.avancar_objeto_um_tick(objeto)
        origem = tuple(avancado.get("origem") or objeto.PosicaoAnterior)
        destino = tuple(avancado.get("destino") or objeto.Posicao)
        elapsed = max(1, int(tick - objeto.InicioTick + 1))
        detalhe_objeto = {
            "objeto": objeto.serializar(),
            "origem": [round(origem[0], 4), round(origem[1], 4)],
            "destino": [round(destino[0], 4), round(destino[1], 4)],
        }
        if objeto.Subtipo == "area":
            detalhe_objeto["alcance_atual"] = round(min(self._fnum(objeto.DadosExtras.get("alcance"), 3.0), float(elapsed) * max(0.1, objeto.VelocidadeTilesTick)), 4)
        elif objeto.Subtipo == "zona":
            detalhe_objeto["raio_atual"] = round(min(self._fnum(objeto.DadosExtras.get("raio_max"), 1.25), float(elapsed) * max(0.1, objeto.VelocidadeTilesTick)), 4)
        self._log_evento(log, tick, "objeto_movimento", executor_id=executor.Uid, detalhe=detalhe_objeto)

        for alvo in self._alvos_padrao(sistema, executor, spec, jogada):
            if alvo is None or alvo.ForaDeCombate:
                continue
            if alvo.Uid == executor.Uid and not objeto.AtingeSiMesmo:
                continue
            if alvo.Uid in objeto.AlvosAtingidos:
                continue

            atingiu = False
            if objeto.Subtipo == "tiro":
                atingiu = self._fisica.segmento_intersecta_circulo(origem, destino, alvo.Posicao, alvo.RaioColisao + objeto.Raio)
            elif objeto.Subtipo == "area":
                alcance_atual = min(self._fnum(objeto.DadosExtras.get("alcance"), 3.0), float(elapsed) * max(0.1, objeto.VelocidadeTilesTick))
                origem_cone = tuple(objeto.DadosExtras.get("origem_execucao") or executor.Posicao)
                atingiu = self._fisica.pokemon_em_cone(alvo, origem_cone, objeto.Direcao, alcance_atual, self._fnum(objeto.DadosExtras.get("largura_teto"), 50.0))
            elif objeto.Subtipo == "zona":
                raio_atual = min(self._fnum(objeto.DadosExtras.get("raio_max"), 1.25), float(elapsed) * max(0.1, objeto.VelocidadeTilesTick))
                atingiu = self._fisica.circulos_colidem(objeto.Posicao, raio_atual, alvo.Posicao, alvo.RaioColisao)

            if not atingiu:
                continue
            objeto.AlvosAtingidos.add(alvo.Uid)
            acertou = self._executar_impacto(sistema, executor, alvo, jogada, spec, objeto.Fluxo, log, tick)
            if not acertou:
                continue
            if objeto.Subtipo == "tiro" and not objeto.AtravessaPokemons:
                if objeto.RicochetesRestantes > 0 and bool(objeto.Fluxo.get("ricocheteia_pokemons", False)):
                    normal = self._fisica._normalizar(self._fisica._sub(objeto.Posicao, alvo.Posicao))
                    objeto.Direcao = self._fisica.refletir_vetor(objeto.Direcao, normal)
                    objeto.RicochetesRestantes -= 1
                    self._log_evento(log, tick, "ricochete_pokemon", objeto_id=objeto.Id, alvo_id=alvo.Uid, restante=int(objeto.RicochetesRestantes))
                else:
                    objeto.Ativo = False
                break

        if objeto.Subtipo == "tiro":
            for estatico in self._fisica.objetos_estaticos():
                if not self._fisica.segmento_intersecta_circulo(origem, destino, tuple(estatico.get("posicao") or (0.0, 0.0)), float(estatico.get("raio") or 0.6) + objeto.Raio):
                    continue
                if objeto.AtravessaObjetos:
                    break
                if objeto.RicochetesRestantes > 0 and bool(objeto.Fluxo.get("ricocheteia_objetos", objeto.Fluxo.get("ricocheteia_paredes", False))):
                    normal = self._fisica._normalizar(self._fisica._sub(objeto.Posicao, tuple(estatico.get("posicao") or (0.0, 0.0))))
                    objeto.Direcao = self._fisica.refletir_vetor(objeto.Direcao, normal)
                    objeto.RicochetesRestantes -= 1
                    self._log_evento(log, tick, "ricochete", objeto_id=objeto.Id, normal=[round(normal[0], 4), round(normal[1], 4)], restante=int(objeto.RicochetesRestantes))
                else:
                    objeto.Ativo = False
                break

            normal_campo = tuple(avancado.get("normal_campo") or (0.0, 0.0))
            if abs(normal_campo[0]) > 1e-9 or abs(normal_campo[1]) > 1e-9:
                if objeto.RicochetesRestantes > 0 and bool(objeto.Fluxo.get("ricocheteia_objetos", objeto.Fluxo.get("ricocheteia_paredes", False))):
                    objeto.Direcao = self._fisica.refletir_vetor(objeto.Direcao, normal_campo)
                    objeto.RicochetesRestantes -= 1
                    self._log_evento(log, tick, "ricochete_campo", objeto_id=objeto.Id, normal=[round(normal_campo[0], 4), round(normal_campo[1], 4)], restante=int(objeto.RicochetesRestantes))
                elif not objeto.AtravessaObjetos:
                    objeto.Ativo = False

        if elapsed >= int(objeto.DuracaoTicks):
            objeto.Ativo = False

    def _criar_movimento_impulso(self, pokemon, origem: object, destino: object, velocidade: object, *, causa: str, colidiu_com: str) -> Dict[str, object]:
        origem_t = tuple(origem) if isinstance(origem, (list, tuple)) and len(origem) == 2 else tuple(pokemon.Posicao)
        destino_t = tuple(destino) if isinstance(destino, (list, tuple)) and len(destino) == 2 else tuple(pokemon.Posicao)
        return {
            "ativo": True,
            "executor": pokemon,
            "destino": (float(destino_t[0]), float(destino_t[1])),
            "velocidade": max(0.01, self._fnum(velocidade, 0.01)),
            "jogada": {"executor_id": pokemon.Uid, "destino_mundo": [float(destino_t[0]), float(destino_t[1])]},
            "spec": {"nome": "Impacto de Colisão", "estilo": "movimento", "dano_componentes": []},
            "atingidos": set(),
            "consumir_pendencia": False,
            "permitir_morto_em_movimento": True,
            "origem_movimento": (float(origem_t[0]), float(origem_t[1])),
            "causa_movimento": str(causa or "colisao_pokemon"),
            "colidiu_com": str(colidiu_com or ""),
        }

    def _aplicar_dano_colisao(self, executor, alvo, dano: float, log: Dict[str, object], tick: int) -> None:
        pacote = {
            "origem_id": executor.Uid,
            "alvo_id": alvo.Uid,
            "tick": int(tick),
            "dano_bruto": round(max(0.0, float(dano)), 4),
            "bonus_intensidade": 1.0,
            "multiplicador_dano_causado": 1.0,
            "dano_critico": round(max(0.0, float(dano)), 4),
            "multiplicador_critico": 1.0,
            "defesa_base": 0.0,
            "defesa_reduzida_por_perfuracao": 0.0,
            "defesa_aplicada": 0.0,
            "dano_pos_defesa": round(max(0.0, float(dano)), 4),
            "dano_pos_tipo": round(max(0.0, float(dano)), 4),
            "tipo_multiplicador": 1.0,
            "multiplicador_hook": 1.0,
            "delta_hook": 0.0,
            "multiplicador_dano_recebido": round(float(alvo.MultiplicadoresTemporarios.get("dano_recebido", 1.0)), 4),
            "dano_final": round(max(0.0, float(dano)), 4),
            "critico": False,
            "dano_tipo": "colisao",
            "perfuracao": 0.0,
        }
        detalhe = executor.AplicarDano(alvo, pacote, sistema=self._sistema_aux, tick=tick)
        self._log_evento(log, tick, "dano", executor_id=executor.Uid, alvo_id=alvo.Uid, ataque="Colisão", pacote=pacote, detalhe=detalhe)

    def _processar_colisoes_movimento(self, sistema: SistemaBatalha, detalhe: Dict[str, object], ativos_movimento: List[Dict[str, object]], log: Dict[str, object], tick: int) -> None:
        for colisao in [dict(item) for item in list(detalhe.get("colisoes") or []) if isinstance(item, dict)]:
            if str(colisao.get("tipo") or "").strip().casefold() != "colisao_pokemon":
                continue
            atacante = sistema.obter_pokemon(colisao.get("a"))
            defensor = sistema.obter_pokemon(colisao.get("b"))
            if atacante is None or defensor is None:
                continue
            self._aplicar_dano_colisao(atacante, defensor, self._fnum(colisao.get("dano_em_b"), 0.0), log, tick)
            self._aplicar_dano_colisao(defensor, atacante, self._fnum(colisao.get("dano_em_a"), 0.0), log, tick)
            for movimento_reacao in [dict(item) for item in list(colisao.get("movimentos") or []) if isinstance(item, dict)]:
                pokemon = sistema.obter_pokemon(movimento_reacao.get("pokemon_id"))
                if pokemon is None:
                    continue
                pacote_movimento = self._criar_movimento_impulso(
                    pokemon,
                    movimento_reacao.get("origem"),
                    movimento_reacao.get("destino"),
                    movimento_reacao.get("velocidade"),
                    causa="colisao_pokemon",
                    colidiu_com=defensor.Uid if pokemon.Uid == atacante.Uid else atacante.Uid,
                )
                ativos_movimento.append(pacote_movimento)
                self._log_evento(
                    log,
                    tick,
                    "movimento_reacao_iniciado",
                    executor_id=pokemon.Uid,
                    alvo_id=str(pacote_movimento.get("colidiu_com") or ""),
                    detalhe={
                        "origem": [round(float(pacote_movimento["origem_movimento"][0]), 4), round(float(pacote_movimento["origem_movimento"][1]), 4)],
                        "destino": [round(float(pacote_movimento["destino"][0]), 4), round(float(pacote_movimento["destino"][1]), 4)],
                        "velocidade": round(float(pacote_movimento["velocidade"]), 4),
                        "causa": str(pacote_movimento.get("causa_movimento") or "colisao_pokemon"),
                    },
                )

    def _processar_movimento_ativo(self, sistema: SistemaBatalha, movimento: Dict[str, object], ativos_movimento: List[Dict[str, object]], log: Dict[str, object], tick: int) -> None:
        executor = movimento["executor"]
        if executor.ForaDeCombate and not bool(movimento.get("permitir_morto_em_movimento", False)):
            movimento["ativo"] = False
            self._consumir_pendencia_jogada(sistema, movimento["jogada"], movimento["spec"], log, tick, "executor_fora_de_combate")
            return
        detalhe = self._fisica.mover_pokemon_um_tick(executor, movimento["destino"], movimento["velocidade"], tick)
        self._log_evento(log, tick, "movimento", executor_id=executor.Uid, detalhe=detalhe)
        self._processar_colisoes_movimento(sistema, detalhe, ativos_movimento, log, tick)
        spec = movimento["spec"]
        if spec.get("dano_componentes"):
            for alvo in self._alvos_padrao(sistema, executor, spec, movimento["jogada"]):
                if alvo.Uid in movimento["atingidos"] or alvo.ForaDeCombate or alvo.Uid == executor.Uid:
                    continue
                if not self._fisica.circulos_colidem(executor.Posicao, executor.RaioColisao, alvo.Posicao, alvo.RaioColisao):
                    continue
                movimento["atingidos"].add(alvo.Uid)
                self._executar_impacto(sistema, executor, alvo, movimento["jogada"], spec, self._flow_principal(spec), log, tick)
        if detalhe.get("concluido"):
            movimento["ativo"] = False
            if bool(movimento.get("consumir_pendencia", True)):
                motivo = "movimento_interrompido_por_colisao" if bool(detalhe.get("interrompido_por_colisao", False)) else "movimento_concluido"
                self._consumir_pendencia_jogada(sistema, movimento["jogada"], spec, log, tick, motivo)

    def _gerar_jogadas_ia(self, sistema: SistemaBatalha, client_id: str, log: Dict[str, object]) -> List[Dict[str, object]]:
        if sistema.Tipo in {"player", "pvp"}:
            return []
        lado_cliente = sistema.lado_do_cliente(client_id)
        lado_ia = "inimigo" if lado_cliente == "jogador" else "jogador"
        cliente_ia = str(sistema.Lados.get(lado_ia, {}).get("cliente_id") or f"{lado_ia}:ia")
        if sistema.JogadasPendentes.get(cliente_ia):
            return [dict(item) for item in list(sistema.JogadasPendentes.get(cliente_ia) or []) if isinstance(item, dict)]
        jogadas_ia = [dict(item) for item in self._bot_ia.escolher_jogadas(sistema, lado_controlado=lado_ia) if isinstance(item, dict)]
        if not jogadas_ia:
            return []
        sistema.adicionar_jogadas(cliente_ia, jogadas_ia)
        self._log_evento(log, int(sistema.TickGlobal), "jogadas_ia", lado=lado_ia, client_id=cliente_ia, jogadas=[dict(item) for item in jogadas_ia])
        return jogadas_ia

    def executar_turno(self, sistema: SistemaBatalha, client_id: str, jogadas: List[Dict[str, object]] | None = None) -> Dict[str, object]:
        sistema.adicionar_jogadas(client_id, list(jogadas or []))
        status_turno, jogadas_brutas = sistema.coletar_jogadas_pendentes_turno(client_id)
        if status_turno == "aguardando":
            return {"status": "aguardando", "mensagem": "Aguardando jogadas do outro jogador", "batalha": sistema.snapshot()}

        self._sistema_aux = sistema
        self._fisica = SimuladorFisica(sistema)
        for pokemon in sistema.listar_pokemons():
            pokemon.Verifica()

        tick_base_turno = int(sistema.TickGlobal)
        snapshot_inicial = sistema.snapshot(incluir_metadados=False)
        log = {
            "batalha_id": sistema.BatalhaId,
            "tipo": sistema.Tipo,
            "turno": int(sistema.TurnoAtual),
            "tick_inicial": int(sistema.TickGlobal) + 1,
            "tick_final": int(sistema.TickGlobal),
            "ordem_jogadas": [],
            "eventos": [],
            "eventos_por_tick": {},
            "snapshot_inicial": dict(snapshot_inicial),
        }

        jogadas_computadas = [dict(item) for item in list(jogadas_brutas or []) if isinstance(item, dict)]
        jogadas_computadas.extend(self._gerar_jogadas_ia(sistema, client_id, log))
        ordenadas, descartadas = self._ordenar_jogadas(sistema, jogadas_computadas)
        for item in descartadas:
            self._log_evento(
                log,
                int(sistema.TickGlobal) + 1,
                "jogada_descartada",
                executor_id=str(item.get("executor_id") or ""),
                executor_nome=str(item.get("executor_nome") or ""),
                ataque=str(((item.get("ataque") or {}) if isinstance(item.get("ataque"), dict) else {}).get("Ataque") or ""),
                motivo=str(item.get("motivo") or "descartada"),
            )
        for item in ordenadas:
            log["ordem_jogadas"].append(
                {
                    "executor_id": item["executor_id"],
                    "ataque": str(item["spec"].get("nome") or ""),
                    "estilo": str(item["spec"].get("estilo") or ""),
                    "start_tick": int(item.get("start_tick", 0)),
                    "end_tick_estimada": int(item.get("end_tick_estimada", 0)),
                    "inteligencia": float(item.get("inteligencia", 0.0)),
                }
            )

        pendentes = [dict(item) for item in ordenadas]
        ativos_movimento: List[Dict[str, object]] = []
        objetos_ativos: List[Dict[str, object]] = []
        acertos_alvo: List[Dict[str, object]] = []
        tick = int(sistema.TickGlobal)
        limite = int(max([item.get("end_tick_estimada", 0) for item in ordenadas], default=0) + 80)

        while tick < limite and (pendentes or ativos_movimento or objetos_ativos or acertos_alvo):
            tick += 1
            for item in [p for p in list(pendentes) if int(p.get("start_tick", 0)) == tick]:
                pendentes.remove(item)
                executor = item["executor"]
                spec = item["spec"]
                ataque_nome = spec.get("nome")
                custo = executor.gastar_energia(self._fnum(item.get("custo"), self._fnum(item.get("custo_base"), 0.0)))
                self._log_evento(
                    log,
                    tick,
                    "acao_iniciada",
                    executor_id=executor.Uid,
                    ataque=ataque_nome,
                    estilo=spec.get("estilo"),
                    custo_energia=round(custo, 4),
                    posicao_inicial=[round(executor.Posicao[0], 4), round(executor.Posicao[1], 4)],
                    destino=list(item.get("destino_mundo")) if isinstance(item.get("destino_mundo"), (list, tuple)) and len(item.get("destino_mundo")) == 2 else None,
                    alvo_ids=[str(uid) for uid in list(item.get("alvo_ids") or []) if str(uid)],
                    velocidade=(
                        round(self._fisica.velocidade_pokemon_tiles_tick(executor, spec.get("velocidade_movimento_percentual", 100.0)), 4)
                        if str(spec.get("estilo") or "").casefold() == "movimento"
                        else None
                    ),
                )

                hook_inicio = executar_ponto_ataque(ataque_nome, "INI", {"sistema": sistema, "tick": tick, "executor": executor, "jogada": item, "spec": spec, "log": log})
                if hook_inicio:
                    self._log_evento(log, tick, "hook_ataque", executor_id=executor.Uid, detalhe=dict(hook_inicio))

                if item.get("troca_reserva_id"):
                    detalhe = sistema.substituir_ativo_por_reserva(executor.Uid, item.get("troca_reserva_id"))
                    self._log_evento(log, tick, "troca", executor_id=executor.Uid, detalhe=detalhe)
                    continue

                estilo = str(spec.get("estilo") or item.get("estilo") or "").casefold()
                if not executor.Flags.get("pode_agir", True):
                    self._log_evento(log, tick, "acao_bloqueada", executor_id=executor.Uid, motivo="pode_agir_false")
                    continue
                if estilo != "movimento" and spec.get("dano_componentes") and not executor.Flags.get("pode_atacar", True):
                    self._log_evento(log, tick, "acao_bloqueada", executor_id=executor.Uid, motivo="pode_atacar_false")
                    continue
                if estilo == "movimento" and not executor.Flags.get("pode_mover", True):
                    self._log_evento(log, tick, "acao_bloqueada", executor_id=executor.Uid, motivo="pode_mover_false")
                    continue

                if estilo == "status":
                    self._aplicar_componentes_auxiliares(sistema, executor, executor, item, spec, log, tick)
                    if float(spec.get("recupera_energia_percentual_custo", 0.0) or 0.0) > 0.0:
                        ganho = self._fnum(item.get("custo"), 0.0) * float(spec.get("recupera_energia_percentual_custo"))
                        detalhe = executor.GanharEnergia(ganho, motivo=str(ataque_nome or "status"))
                        self._log_evento(log, tick, "energia", executor_id=executor.Uid, detalhe=detalhe)
                    self._finalizar_jogada(sistema, item, spec, log, tick, "status_imediato")
                    continue

                if estilo == "alvo":
                    duracao = self._duracao_estimativa(sistema, executor, item, spec)
                    alvos = self._alvos_padrao(sistema, executor, spec, item)
                    item["pendencias_execucao"] = max(1, len(alvos))
                    for alvo in alvos:
                        acertos_alvo.append({"tick": tick + duracao, "executor": executor, "alvo": alvo, "jogada": item, "spec": spec})
                    if not alvos:
                        self._finalizar_jogada(sistema, item, spec, log, tick, "sem_alvos")
                    continue

                if estilo == "movimento":
                    destino = tuple(item.get("destino_mundo")) if isinstance(item.get("destino_mundo"), (list, tuple)) and len(item.get("destino_mundo")) == 2 else executor.Posicao
                    item["pendencias_execucao"] = 1
                    ativos_movimento.append(
                        {
                            "ativo": True,
                            "executor": executor,
                            "destino": (float(destino[0]), float(destino[1])),
                            "velocidade": self._fisica.velocidade_pokemon_tiles_tick(executor, spec.get("velocidade_movimento_percentual", 100.0)),
                            "jogada": item,
                            "spec": spec,
                            "atingidos": set(),
                        }
                    )
                    continue

                if estilo in {"tiro", "area", "zona"}:
                    subfluxos = list(spec.get("subfluxos") or [self._flow_principal(spec)])
                    item["pendencias_execucao"] = max(1, len(subfluxos))
                    for indice, fluxo in enumerate(subfluxos):
                        objeto = self._criar_objeto_fluxo(executor, spec, item, fluxo, tick, indice)
                        objetos_ativos.append({"objeto": objeto, "executor": executor, "jogada": item, "spec": spec})
                        self._log_evento(log, tick, "objeto_criado", executor_id=executor.Uid, detalhe=objeto.serializar())
                    continue

            for movimento in list(ativos_movimento):
                if not movimento.get("ativo", False):
                    ativos_movimento.remove(movimento)
                    continue
                self._processar_movimento_ativo(sistema, movimento, ativos_movimento, log, tick)
                if not movimento.get("ativo", False):
                    ativos_movimento.remove(movimento)

            for objeto_pacote in list(objetos_ativos):
                objeto = objeto_pacote["objeto"]
                if not objeto.Ativo:
                    objetos_ativos.remove(objeto_pacote)
                    self._log_evento(log, tick, "objeto_finalizado", executor_id=objeto_pacote["executor"].Uid, detalhe={"objeto": objeto.serializar()})
                    self._consumir_pendencia_jogada(sistema, objeto_pacote["jogada"], objeto_pacote["spec"], log, tick, "objeto_finalizado")
                    continue
                self._resolver_objeto(sistema, objeto, objeto_pacote["executor"], objeto_pacote["jogada"], objeto_pacote["spec"], log, tick)
                if not objeto.Ativo:
                    objetos_ativos.remove(objeto_pacote)
                    self._log_evento(log, tick, "objeto_finalizado", executor_id=objeto_pacote["executor"].Uid, detalhe={"objeto": objeto.serializar()})
                    self._consumir_pendencia_jogada(sistema, objeto_pacote["jogada"], objeto_pacote["spec"], log, tick, "objeto_finalizado")

            for pacote in [p for p in list(acertos_alvo) if int(p.get("tick", 0)) == tick]:
                acertos_alvo.remove(pacote)
                self._executar_impacto(sistema, pacote["executor"], pacote["alvo"], pacote["jogada"], pacote["spec"], self._flow_principal(pacote["spec"]), log, tick)
                self._consumir_pendencia_jogada(sistema, pacote["jogada"], pacote["spec"], log, tick, "impacto_alvo")

            for pokemon in sistema.listar_pokemons():
                for evento in pokemon.passar_ticks(1):
                    self._log_evento(log, tick, str(evento.get("tipo") or "evento"), pokemon_id=pokemon.Uid, detalhe=dict(evento))
                pokemon.Verifica()

        tick_final_turno = int(log.get("tick_final", sistema.TickGlobal))
        for pokemon in sistema.listar_pokemons():
            for evento in pokemon.FimTurno(sistema=sistema, tick=tick_final_turno + 1):
                self._log_evento(log, tick_final_turno + 1, "fim_turno", pokemon_id=pokemon.Uid, detalhe=evento)
            pokemon.Verifica()

        snapshot_final = sistema.snapshot(incluir_metadados=False)
        log["snapshot_final"] = dict(snapshot_final)
        log_publico = self._construir_log_publico(
            sistema,
            log,
            ordenadas,
            descartadas,
            tick_base=tick_base_turno,
            snapshot_inicial=snapshot_inicial,
            snapshot_final=snapshot_final,
        )
        sistema.avancar_turno(log_publico, tick_global_final=int(log.get("tick_final", sistema.TickGlobal)))
        resultado = sistema.snapshot()
        return {
            "status": "ok",
            "mensagem": "Turno computado",
            "batalha": resultado,
            "log": log_publico,
        }
