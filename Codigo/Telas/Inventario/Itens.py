from __future__ import annotations

import pygame

from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import PainelRolavel

class InventarioItens:
    def __init__(self, inventario):
        self.Inventario = inventario
        self.Colunas = 8
        self.Linhas = 4
        self.TotalSlots = self.Colunas * self.Linhas
        self.SlotPx = 64
        self.Gap = 12

        self._slots = []
        self._montado = False
        self._slot_arrastado = None

    def _reconstruir_slots(self, area):
        self._slots.clear()

        painel_rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        self.Painel = PainelRolavel(
            painel_rect,
            area_real=(0, 0, painel_rect.width - 2, 420),
            cor_fundo=(30, 36, 54, 240),
        )

        for i in range(self.TotalSlots):
            col = i % self.Colunas
            lin = i // self.Colunas
            x = 18 + col * (self.SlotPx + self.Gap)
            y = 18 + lin * (self.SlotPx + self.Gap)
            self._slots.append(ItemInventario((x, y, self.SlotPx, self.SlotPx), slot_id=i, inventario=self.Inventario))

        self._montado = True

    def _slot_local_pos(self, slot_id):
        col = slot_id % self.Colunas
        lin = slot_id // self.Colunas
        x = 18 + col * (self.SlotPx + self.Gap)
        y = 18 + lin * (self.SlotPx + self.Gap)
        return x, y

    def _slot_tela_rect(self, slot_id):
        x, y = self._slot_local_pos(slot_id)
        return pygame.Rect(
            self.Painel.rect.x + x - self.Painel.ScrollX,
            self.Painel.rect.y + y - self.Painel.ScrollY,
            self.SlotPx,
            self.SlotPx,
        )

    def _atualizar_areas_acao(self):
        areas = []
        for slot in self._slots:
            areas.append((slot.Id, self._slot_tela_rect(slot.Id)))

        for slot in self._slots:
            slot.limpar_areas_acao()
            for destino_id, destino_rect in areas:
                slot.adicionar_area_acao(destino_rect, callback=self._trocar_slots, area_id=destino_id)

    def _trocar_slots(self, arrastavel, area_id, _area_rect):
        origem = int(arrastavel.Id)
        destino = int(area_id)

        if origem == destino:
            return

        itens = self.Inventario.Itens

        if origem >= len(itens):
            return

        if destino >= len(itens):
            item = itens.pop(origem)
            itens.append(item)
            return

        a = itens[origem]
        b = itens[destino]

        chave_a = self.Inventario._chave_stack(a)
        chave_b = self.Inventario._chave_stack(b)

        if isinstance(a, dict) and isinstance(b, dict) and chave_a == chave_b:
            b["quantidade"] = int(max(1, b.get("quantidade", 1))) + int(max(1, a.get("quantidade", 1)))
            itens.pop(origem)
        else:
            itens[origem], itens[destino] = itens[destino], itens[origem]

    def atualizar(self, eventos, dt, area):
        if not self._montado:
            self._reconstruir_slots(area)

        self.Painel.rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        altura_real = max(360, 30 + self.Linhas * (self.SlotPx + self.Gap))
        self.Painel.definir_area_real(self.Painel.rect.width - 2, altura_real)

        self._atualizar_areas_acao()

        self._slot_arrastado = None

        for slot in self._slots:
            if not slot.Arrastando:
                slot.definir_posicao(self._slot_tela_rect(slot.Id).topleft)

            resultado = slot.update(eventos)

            if slot.Arrastando:
                self._slot_arrastado = slot

            if resultado is False:
                slot.definir_posicao(self._slot_tela_rect(slot.Id).topleft)

            elif resultado is True:
                slot.definir_posicao(self._slot_tela_rect(slot.Id).topleft)

        for slot in self._slots:
            if slot.Arrastando:
                self._slot_arrastado = slot
                break

    def renderizar(self, tela, area, eventos, dt):
        self.atualizar(eventos, dt, area)
        self.Painel.render(tela, eventos, dt)

        arrastado = self._slot_arrastado

        for slot in self._slots:
            if slot is arrastado:
                continue
            if self.Painel.rect.colliderect(slot.rect):
                slot.draw(tela)

        if arrastado is not None:
            arrastado.draw(tela)
