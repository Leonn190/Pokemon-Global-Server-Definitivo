from __future__ import annotations

import pygame

from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Prefabs.Arrastavel import Arrastavel
from Codigo.Prefabs.Painel import PainelRolavel


class InventarioItens:
    def __init__(self, inventario):
        self.Inventario = inventario
        self.Colunas = 8
        self.Linhas = 4
        self.TotalSlots = self.Colunas * self.Linhas
        self.SlotPx = 64
        self.Gap = 12

        self._montado = False
        self._arrastavel = Arrastavel()

    def _garantir_slots(self):
        if not hasattr(self.Inventario, "Itens") or not isinstance(self.Inventario.Itens, list):
            self.Inventario.Itens = []

        if len(self.Inventario.Itens) < self.TotalSlots:
            self.Inventario.Itens.extend([None] * (self.TotalSlots - len(self.Inventario.Itens)))
        elif len(self.Inventario.Itens) > self.TotalSlots:
            self.Inventario.Itens = self.Inventario.Itens[:self.TotalSlots]

    def _reconstruir(self, area):
        painel_rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        self.Painel = PainelRolavel(
            painel_rect,
            area_real=(0, 0, painel_rect.width - 2, 30 + self.Linhas * (self.SlotPx + self.Gap)),
            cor_fundo=(30, 36, 54, 240),
        )
        self._montado = True

    def _slot_local_pos(self, slot_id: int):
        col = slot_id % self.Colunas
        lin = slot_id // self.Colunas
        x = 18 + col * (self.SlotPx + self.Gap)
        y = 18 + lin * (self.SlotPx + self.Gap)
        return x, y

    def _slot_rect_tela(self, slot_id: int) -> pygame.Rect:
        x, y = self._slot_local_pos(slot_id)
        return pygame.Rect(
            self.Painel.rect.x + x - self.Painel.ScrollX,
            self.Painel.rect.y + y - self.Painel.ScrollY,
            self.SlotPx,
            self.SlotPx,
        )

    def _item_rect_no_slot(self, slot_rect: pygame.Rect) -> pygame.Rect:
        margem = 7
        return pygame.Rect(
            slot_rect.x + margem,
            slot_rect.y + margem,
            slot_rect.width - margem * 2,
            slot_rect.height - margem * 2,
        )

    def _slot_sob_mouse(self, mouse_pos):
        for i in range(self.TotalSlots):
            rect = self._slot_rect_tela(i)
            if rect.collidepoint(mouse_pos):
                return i
        return None

    def _desenhar_slot(self, tela, rect: pygame.Rect):
        pygame.draw.rect(tela, (76, 96, 140), rect, border_radius=8)
        pygame.draw.rect(tela, (20, 26, 40), rect, 2, border_radius=8)

    def _chave_stack(self, item):
        if hasattr(self.Inventario, "_chave_stack"):
            return self.Inventario._chave_stack(item)
        if not isinstance(item, dict):
            return str(item)
        return str(item.get("Code") or item.get("code") or item.get("Nome") or item.get("nome") or "")

    def _iniciar_arrasto(self, mouse_pos):
        if self._arrastavel.Ativo:
            return

        slot = self._slot_sob_mouse(mouse_pos)
        if slot is None:
            return

        item = self.Inventario.Itens[slot]
        if item is None:
            return

        rect_slot = self._slot_rect_tela(slot)
        rect_item = self._item_rect_no_slot(rect_slot)

        self._arrastavel.iniciar(item=item, origem=slot, rect_item=rect_item, mouse_pos=mouse_pos)

    def _soltar_arrasto(self, mouse_pos):
        if not self._arrastavel.Ativo:
            return

        origem = self._arrastavel.Origem
        destino = self._slot_sob_mouse(mouse_pos)

        if destino is None:
            self._arrastavel.cancelar()
            return

        itens = self.Inventario.Itens
        item_origem = itens[origem]
        item_destino = itens[destino]

        if origem == destino:
            self._arrastavel.cancelar()
            return

        if item_destino is None:
            itens[destino] = item_origem
            itens[origem] = None
            self._arrastavel.cancelar()
            return

        chave_a = self._chave_stack(item_origem)
        chave_b = self._chave_stack(item_destino)

        if isinstance(item_origem, dict) and isinstance(item_destino, dict) and chave_a == chave_b:
            item_destino["quantidade"] = int(max(1, item_destino.get("quantidade", 1))) + int(max(1, item_origem.get("quantidade", 1)))
            itens[origem] = None
        else:
            itens[destino], itens[origem] = itens[origem], itens[destino]

        self._arrastavel.cancelar()

    def atualizar(self, eventos, dt, area):
        self._garantir_slots()

        if not self._montado:
            self._reconstruir(area)

        self.Painel.rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        self.Painel.definir_area_real(
            self.Painel.rect.width - 2,
            max(360, 30 + self.Linhas * (self.SlotPx + self.Gap)),
        )

        self.Painel._processar_scroll(eventos)

        mouse_pos = pygame.mouse.get_pos()

        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self.Painel.rect.collidepoint(evento.pos):
                    self._iniciar_arrasto(evento.pos)

            elif evento.type == pygame.MOUSEMOTION and self._arrastavel.Ativo:
                self._arrastavel.atualizar(evento.pos)

            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                self._soltar_arrasto(evento.pos)

    def renderizar(self, tela, area, eventos, dt):
        self.atualizar(eventos, dt, area)

        self.Painel.render(tela, [], dt)

        for i in range(self.TotalSlots):
            rect_slot = self._slot_rect_tela(i)

            if not self.Painel.rect.colliderect(rect_slot):
                continue

            self._desenhar_slot(tela, rect_slot)

            item = self.Inventario.Itens[i]

            if item is None:
                continue

            if self._arrastavel.Ativo and i == self._arrastavel.Origem:
                continue

            rect_item = self._item_rect_no_slot(rect_slot)
            ItemInventario.desenhar_item_no_rect(tela, item, rect_item)

        if self._arrastavel.Ativo and self._arrastavel.Item is not None:
            ItemInventario.desenhar_item_no_rect(tela, self._arrastavel.Item, self._arrastavel.Rect)