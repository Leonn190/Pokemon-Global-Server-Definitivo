from __future__ import annotations

import copy
import json


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
            "id_evento": f"{int(self.rodada):02d}{int(self._ordem_evento):06d}",
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
        return {
            "rodada_anterior": int(rodada_anterior),
            "rodada_atual": int(partida.rodada_atual),
            "estado_batalha": str(partida.estado_partida),
            "finalizada": bool(partida.finalizada),
            "vencedor": partida.vencedor,
            "perdedor": partida.perdedor,
            "pokemons": {pid: pokemon.serializar() for pid, pokemon in partida.pokemons_por_id.items()},
            "areas": dict(partida.ocupacao_areas),
            "lados": list(partida.lados.keys()),
            "avisos": list(avisos or []),
            "erros_acoes": list(erros_acoes or []),
            "acoes_falhas": list(acoes_falhas or []),
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
                "id_log": f"{int(rodada):06d}",
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
