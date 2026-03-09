"""Inventário simples do player."""

from __future__ import annotations


class PlayerInventario:
    def __init__(self, limite_itens=32):
        self.LimiteItens = int(max(1, limite_itens))
        self.Itens = []
        self.Pokemons = []
        self.TimesPokemon = []
        self.SlotSelecionado = 0

    def _chave_stack(self, item):
        if not isinstance(item, dict):
            return str(item)
        return str(item.get("Code") or item.get("code") or item.get("Nome") or item.get("nome") or "")

    def adicionar_item(self, item):
        item_copia = dict(item) if isinstance(item, dict) else item
        if isinstance(item_copia, dict):
            item_copia["quantidade"] = int(max(1, item_copia.get("quantidade", 1)))
            chave_nova = self._chave_stack(item_copia)
            for atual in self.Itens:
                if isinstance(atual, dict) and self._chave_stack(atual) == chave_nova:
                    atual["quantidade"] = int(max(1, atual.get("quantidade", 1))) + item_copia["quantidade"]
                    return True
        if len(self.Itens) >= self.LimiteItens:
            return False
        self.Itens.append(item_copia)
        return True

    def aplicar_serializado(self, dados):
        if not isinstance(dados, dict):
            return
        self.LimiteItens = int(max(1, dados.get("limite_itens", self.LimiteItens)))
        itens = dados.get("itens", self.Itens)
        self.Itens = []
        for i in list(itens)[: self.LimiteItens]:
            if isinstance(i, dict):
                item = dict(i)
                item["quantidade"] = int(max(1, item.get("quantidade", 1)))
                self.Itens.append(item)
            else:
                self.Itens.append(i)
        self.Pokemons = list(dados.get("pokemons", self.Pokemons))
        self.TimesPokemon = list(dados.get("times_pokemon", self.TimesPokemon))
        total_slots = max(1, min(8, len(self.Itens)))
        self.SlotSelecionado = int(dados.get("slot_selecionado", self.SlotSelecionado)) % total_slots if self.Itens else 0

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
