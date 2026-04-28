from __future__ import annotations

import copy
import json
import random


def _jsonavel(valor):
    try:
        return json.loads(json.dumps(valor, ensure_ascii=False))
    except Exception:
        if isinstance(valor, dict):
            return {str(k): _jsonavel(v) for k, v in valor.items()}
        if isinstance(valor, (list, tuple, set)):
            return [_jsonavel(v) for v in valor]
        return str(valor)


def _i(valor, default=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _f(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


class ConstrutorLog:
    def __init__(self, partida):
        self.partida = partida
        self.rodada = int(getattr(partida, "rodada_atual", 1) or 1)
        self.historico = []
        self._ordem_evento = 0

    def iniciar_log_rodada(self, rodada):
        self.rodada = int(rodada or getattr(self.partida, "rodada_atual", 1) or 1)
        self.historico = []
        self._ordem_evento = 0
        return self

    def registrar_evento(self, tipo, dados=None, passo=None, ordem=None):
        tipo = str(tipo or "").strip()
        if not tipo:
            return None
        self._ordem_evento += 1
        passo_real = _i(passo, _i(getattr(self.partida, "passo_atual", 0), 0))
        ordem_real = _i(ordem, self._ordem_evento)
        evento = {
            "id_evento": str(self.partida.novo_id_evento()),
            "id_evento_legado": f"{int(self.rodada):02d}{int(self._ordem_evento):06d}",
            "rodada": int(self.rodada),
            "passo": int(passo_real),
            "ordem": int(ordem_real),
            "tipo": tipo,
            "dados": _jsonavel(copy.deepcopy(dados or {})),
        }
        self.historico.append(evento)
        return evento

    def registrar_diff(self, tipo, dados=None, passo=None, ordem=None):
        return self.registrar_evento(tipo, dados=dados, passo=passo, ordem=ordem)

    def montar_historico(self):
        return _jsonavel(self.historico)

    def montar_resultado(self, rodada_anterior: int, avisos=None, erros_acoes=None, acoes_falhas=None):
        partida = self.partida
        rodadas_totais = max(int(rodada_anterior), int(getattr(partida, "rodada_atual", rodada_anterior) or rodada_anterior))
        return {
            "rodada_anterior": int(rodada_anterior),
            "rodada_atual": int(partida.rodada_atual),
            "rodadas_totais": rodadas_totais,
            "estado_batalha": str(partida.estado_partida),
            "finalizada": bool(partida.finalizada),
            "motivo_finalizacao": str(getattr(partida, "motivo_finalizacao", None) or ("fim_normal" if partida.finalizada else "")),
            "vencedor": partida.vencedor,
            "perdedor": partida.perdedor,
            "pokemons": {pid: pokemon.serializar() for pid, pokemon in partida.pokemons_por_id.items()},
            "areas": dict(partida.ocupacao_areas),
            "lados": list(partida.lados.keys()),
            "estatisticas": self._montar_estatisticas(),
            "xp": self._montar_xp(rodadas_totais),
            "persistencia": self._montar_persistencia(rodadas_totais),
            "avisos": list(avisos or []),
            "erros_acoes": list(erros_acoes or []),
            "acoes_falhas": list(acoes_falhas or []),
        }

    def _montar_estatisticas(self):
        saida = {}
        for pid, pokemon in self.partida.pokemons_por_id.items():
            stats = dict(getattr(pokemon, "estatisticas_batalha", {}) or {})
            saida[pid] = {
                "dano_causado": round(_f(stats.get("dano_causado"), 0.0), 4),
                "dano_recebido": round(_f(stats.get("dano_recebido"), 0.0), 4),
                "cura_feita": round(_f(stats.get("cura_feita"), 0.0), 4),
                "cura_recebida": round(_f(stats.get("cura_recebida"), 0.0), 4),
                "energia_gasta": round(_f(stats.get("energia_gasta"), 0.0), 4),
                "abates": _i(stats.get("abates"), 0),
            }
        return saida

    def _montar_xp(self, rodadas_totais):
        saida = {}
        fuga = str(getattr(self.partida, "motivo_finalizacao", "") or "") == "fuga"
        for pid, pokemon in self.partida.pokemons_por_id.items():
            stats = dict(getattr(pokemon, "estatisticas_batalha", {}) or {})
            xp_base = _f(stats.get("dano_causado"), 0.0) + _f(stats.get("energia_gasta"), 0.0) + (int(rodadas_totais) * 10)
            rng = random.Random(f"{getattr(self.partida, 'seed_partida', 0)}:{pid}")
            multiplicador = 0.75 + (rng.random() * 0.75)
            xp_final = xp_base * multiplicador
            if fuga:
                xp_final *= 0.5
            saida[pid] = {
                "xp_base": round(xp_base, 4),
                "multiplicador": round(multiplicador, 4),
                "xp_final": int(round(max(0.0, xp_final))),
            }
        return saida

    def _montar_persistencia(self, rodadas_totais):
        xp = self._montar_xp(rodadas_totais)
        return {
            "pokemons": {
                pid: {
                    "id_original": pokemon.id_original,
                    "VidaAtual": round(_f(getattr(pokemon, "VidaAtual", 0.0), 0.0), 4),
                    "xp_ganho": int((xp.get(pid) or {}).get("xp_final", 0) or 0),
                }
                for pid, pokemon in self.partida.pokemons_por_id.items()
            }
        }

    def montar_resultado_publico(self, rodada_anterior: int, avisos=None, erros_acoes=None, acoes_falhas=None):
        return self.montar_resultado(rodada_anterior, avisos=avisos, erros_acoes=erros_acoes, acoes_falhas=acoes_falhas)

    def gerar_log(self, rodada_anterior: int | None = None, resultado=None, avisos=None, erros_acoes=None, acoes_falhas=None):
        rodada = int(rodada_anterior or self.rodada or getattr(self.partida, "rodada_atual", 1) or 1)
        resultado_final = resultado if isinstance(resultado, dict) else self.montar_resultado(
            rodada,
            avisos=avisos,
            erros_acoes=erros_acoes,
            acoes_falhas=acoes_falhas,
        )
        return _jsonavel(
            {
                "id_log": str(self.partida.novo_id_log()),
                "id_log_legado": f"{int(rodada):06d}",
                "rodada": int(rodada),
                "historico": self.montar_historico(),
                "resultado": resultado_final,
            }
        )

    def construir_resultado(self, rodada_anterior: int, avisos=None, erros_acoes=None, acoes_falhas=None):
        resultado = self.montar_resultado(
            int(rodada_anterior),
            avisos=avisos,
            erros_acoes=erros_acoes,
            acoes_falhas=acoes_falhas,
        )
        return self.gerar_log(int(rodada_anterior), resultado=resultado)
