"""Inventário simples do player."""

from __future__ import annotations


class PlayerInventario:
    def __init__(self, limite_itens=32):
        self.LimiteItens = int(max(1, limite_itens))
        self.Itens = []
        self.Pokemons = []
        self.TimesPokemon = []
        self.SlotSelecionado = 0

    def adicionar_item(self, item):
        if len(self.Itens) >= self.LimiteItens:
            return False
        self.Itens.append(item)
        return True

    def mudar_slot_por_scroll(self, direcao):
        if not self.Itens:
            self.SlotSelecionado = 0
            return self.SlotSelecionado
        total = min(8, len(self.Itens))
        self.SlotSelecionado = (self.SlotSelecionado + int(direcao)) % total
        return self.SlotSelecionado

    def item_na_mao(self):
        if not self.Itens:
            return None
        if self.SlotSelecionado < 0 or self.SlotSelecionado >= len(self.Itens):
            return None
        return self.Itens[self.SlotSelecionado]

    def serializar(self):
        return {
            "itens": list(self.Itens),
            "pokemons": list(self.Pokemons),
            "times_pokemon": list(self.TimesPokemon),
            "limite_itens": self.LimiteItens,
            "slot_selecionado": self.SlotSelecionado,
        }
