from __future__ import annotations

from typing import Dict, List


class SistemaBatalha:
    """Controla o estado físico/espacial básico do campo de batalha."""

    def __init__(self, contexto: Dict[str, object] | None = None) -> None:
        self.Contexto = dict(contexto or {})
        self.PokemonsAliados: List[object] = []
        self.PokemonsInimigos: List[object] = []

    def definir_lados(self, aliados: List[object], inimigos: List[object]) -> None:
        self.PokemonsAliados = list(aliados or [])
        self.PokemonsInimigos = list(inimigos or [])

    def atualizar(self, _eventos, _dt: float) -> None:
        return
