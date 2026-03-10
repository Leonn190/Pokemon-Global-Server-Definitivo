"""Inventário simples do player."""

from __future__ import annotations


class Inventario:
    def __init__(self, limite_itens=100, limite_slots=32):
        self.LimiteItens = int(max(1, limite_itens))
        self.LimiteSlots = int(max(1, limite_slots))
        self.Itens = [None] * self.LimiteSlots
        self.Pokemons = []
        self.TimesPokemon = []
        self.SlotSelecionado = 0

    def definir_limite_itens(self, limite_itens, preservar=True):
        self.LimiteItens = int(max(1, limite_itens))

    def definir_limite_slots(self, limite_slots, preservar=True):
        novo_limite = int(max(1, limite_slots))
        if novo_limite == self.LimiteSlots:
            return

        itens_atuais = list(self.Itens) if preservar else []
        self.LimiteSlots = novo_limite
        self.Itens = [None] * self.LimiteSlots

        if preservar:
            for i, item in enumerate(itens_atuais[: self.LimiteSlots]):
                self.Itens[i] = self._normalizar_item(item)

        total_slots_mao = max(1, min(8, self.LimiteSlots))
        self.SlotSelecionado %= total_slots_mao

    def quantidade_slots_ocupados(self):
        return sum(1 for item in self.Itens if item is not None)

    def quantidade_total_itens(self):
        total = 0
        for item in self.Itens:
            if isinstance(item, dict):
                total += int(max(1, item.get("quantidade", 1)))
            elif item is not None:
                total += 1
        return total

    def primeiro_slot_livre(self):
        for i, item in enumerate(self.Itens):
            if item is None:
                return i
        return None

    def _chave_stack(self, item):
        if not isinstance(item, dict):
            return str(item)
        return str(item.get("Code") or item.get("code") or item.get("Nome") or item.get("nome") or "")

    def _normalizar_item(self, item):
        if item is None:
            return None
        if isinstance(item, dict):
            item_copia = dict(item)
            item_copia["quantidade"] = int(max(1, item_copia.get("quantidade", 1)))
            return item_copia
        return item

    def adicionar_item(self, item):
        item_copia = self._normalizar_item(item)
        if item_copia is None:
            return False

        quantidade_nova = int(item_copia.get("quantidade", 1)) if isinstance(item_copia, dict) else 1
        if (self.quantidade_total_itens() + quantidade_nova) > self.LimiteItens:
            return False

        if isinstance(item_copia, dict):
            chave_nova = self._chave_stack(item_copia)
            for atual in self.Itens:
                if isinstance(atual, dict) and self._chave_stack(atual) == chave_nova:
                    atual["quantidade"] = int(max(1, atual.get("quantidade", 1))) + item_copia["quantidade"]
                    return True

        slot_livre = self.primeiro_slot_livre()
        if slot_livre is None:
            return False

        self.Itens[slot_livre] = item_copia
        return True

    def aplicar_serializado(self, dados):
        if not isinstance(dados, dict):
            return

        self.LimiteItens = int(max(1, dados.get("limite_itens", self.LimiteItens)))
        self.LimiteSlots = int(max(1, dados.get("limite_slots", self.LimiteSlots)))
        itens_brutos = list(dados.get("itens", []))

        self.Itens = [None] * self.LimiteSlots
        for i in range(min(len(itens_brutos), self.LimiteSlots)):
            self.Itens[i] = self._normalizar_item(itens_brutos[i])

        self.Pokemons = list(dados.get("pokemons", self.Pokemons))
        self.TimesPokemon = list(dados.get("times_pokemon", self.TimesPokemon))

        total_slots_mao = max(1, min(8, self.LimiteSlots))
        self.SlotSelecionado = int(dados.get("slot_selecionado", self.SlotSelecionado)) % total_slots_mao

    def mudar_slot_por_scroll(self, direcao):
        total = max(1, min(8, self.LimiteSlots))
        self.SlotSelecionado = (self.SlotSelecionado + int(direcao)) % total
        return self.SlotSelecionado

    def item_na_mao(self):
        if self.SlotSelecionado < 0 or self.SlotSelecionado >= len(self.Itens):
            return None
        return self.Itens[self.SlotSelecionado]

    def serializar_itens(self):
        itens = []
        for item in self.Itens:
            normalizado = self._normalizar_item(item)
            if isinstance(normalizado, dict):
                itens.append({str(k): normalizado[k] for k in sorted(normalizado.keys())})
            else:
                itens.append(normalizado)
        return itens

    def serializar(self):
        return {
            "itens": self.serializar_itens(),
            "pokemons": list(self.Pokemons),
            "times_pokemon": list(self.TimesPokemon),
            "limite_itens": self.LimiteItens,
            "limite_slots": self.LimiteSlots,
            "slot_selecionado": self.SlotSelecionado,
        }


PlayerInventario = Inventario
