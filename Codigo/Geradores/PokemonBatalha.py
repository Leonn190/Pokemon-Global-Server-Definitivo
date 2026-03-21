from __future__ import annotations

from typing import Dict


class PokemonBatalha:
    def __init__(self, dados: Dict[str, object]):
        self.Dados = dict(dados or {})
