"""Inventário simples do player."""

from __future__ import annotations


class PlayerInventario:
    def __init__(self):
        self.Itens = []
        self.Pokemons = []
        self.TimesPokemon = []

    def serializar(self):
        return {
            "itens": list(self.Itens),
            "pokemons": list(self.Pokemons),
            "times_pokemon": list(self.TimesPokemon),
        }
