from __future__ import annotations


class ConstrutorLog:
    def __init__(self, partida):
        self.partida = partida
        self._sequencial = 600000

    def novo_log(self, rodada: int):
        self._sequencial += 1
        return {"id_log": str(self._sequencial), "rodada": int(rodada), "historico": [], "resultado": {}}

    def evento(self, log: dict, tipo: str, **dados):
        log.setdefault("historico", []).append({"tipo": str(tipo), **dados})

    def finalizar(self, log: dict):
        log["resultado"] = self.partida.gerar_resultado_diff()
        return log
