from __future__ import annotations

from typing import Dict, List

from Codigo.Geradores.PokemonBatalha import PokemonBatalha


class PlayerBatalha:
    def __init__(self, lado: str, pokemons_slots: List[Dict[str, object]] | None = None, max_ativos: int = 3):
        self.Lado = str(lado or "jogador")
        self.MaxAtivos = max(1, int(max_ativos))
        self.TimeCompleto: List[Dict[str, object]] = [dict(p) for p in (pokemons_slots or []) if isinstance(p, dict)]
        self.PokemonsAtivos: List[PokemonBatalha] = []
        self.PokemonsReserva: List[Dict[str, object]] = []

    def preparar_slots(self):
        ativos = self.TimeCompleto[: self.MaxAtivos]
        self.PokemonsReserva = self.TimeCompleto[self.MaxAtivos :]
        return ativos

    def definir_ativos(self, pokemons: List[PokemonBatalha]):
        self.PokemonsAtivos = list(pokemons or [])
