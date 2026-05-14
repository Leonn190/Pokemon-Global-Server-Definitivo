from __future__ import annotations


class IDsBatalha:
    """Gerador determinístico de IDs oficiais v7 por partida."""

    PREFIXOS = {
        "pokemon": "0",
        "ataque": "1",
        "acao": "2",
        "evento": "3",
        "construto": "4",
        "lado": "5",
        "log": "6",
    }

    def __init__(self):
        self._contadores = {chave: 0 for chave in self.PREFIXOS}

    @staticmethod
    def _lado_num(lado_id) -> int:
        try:
            return int(float(lado_id))
        except (TypeError, ValueError):
            return 50

    def _next(self, tipo: str) -> int:
        self._contadores[tipo] = int(self._contadores.get(tipo, 0)) + 1
        return self._contadores[tipo]

    def novo_id_pokemon(self, lado_id) -> str:
        contador = self._next("pokemon")
        return f"{self.PREFIXOS['pokemon']}{self._lado_num(lado_id):02d}{contador:05d}"

    def novo_id_ataque(self, lado_id=None) -> str:
        contador = self._next("ataque")
        if lado_id is None:
            return f"{self.PREFIXOS['ataque']}{contador:07d}"
        return f"{self.PREFIXOS['ataque']}{self._lado_num(lado_id):02d}{contador:05d}"

    def novo_id_acao(self, lado_id=None) -> str:
        contador = self._next("acao")
        if lado_id is None:
            return f"{self.PREFIXOS['acao']}{contador:07d}"
        return f"{self.PREFIXOS['acao']}{self._lado_num(lado_id):02d}{contador:05d}"

    def novo_id_evento(self, rodada: int | None = None) -> str:
        contador = self._next("evento")
        if rodada is None:
            return f"{self.PREFIXOS['evento']}{contador:07d}"
        return f"{self.PREFIXOS['evento']}{int(rodada):03d}{contador:04d}"

    def novo_id_construto(self, lado_id=None) -> str:
        contador = self._next("construto")
        if lado_id is None:
            return f"{self.PREFIXOS['construto']}{contador:07d}"
        return f"{self.PREFIXOS['construto']}{self._lado_num(lado_id):02d}{contador:05d}"

    def novo_id_lado(self, indice: int | None = None) -> int:
        if indice is not None:
            return 50 + int(indice)
        contador = self._next("lado")
        return 50 + contador - 1

    def novo_id_log(self, rodada: int | None = None) -> str:
        contador = self._next("log")
        if rodada is None:
            return f"{self.PREFIXOS['log']}{contador:07d}"
        return f"{self.PREFIXOS['log']}{int(rodada):03d}{contador:04d}"
