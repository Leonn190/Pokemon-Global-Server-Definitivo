from __future__ import annotations

import pygame

from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import PainelRolavel


class InventarioItens:
    def __init__(self, inventario):
        self.Inventario = inventario
        self.Colunas = 8
        self.Linhas = 4
        self.TotalSlots = self.Linhas * self.Colunas
        self.SlotPx = 64
        self.Gap = 12
        self._slots = []
        self._montado = False

    def _reconstruir_slots(self, area):
        self._slots.clear()
        painel_rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        self.Painel = PainelRolavel(painel_rect, area_real=(0, 0, painel_rect.width - 2, 420), cor_fundo=(30, 36, 54, 240))

        for i in range(self.TotalSlots):
            col = i % self.Colunas
            lin = i // self.Colunas
            x = 18 + col * (self.SlotPx + self.Gap)
            y = 18 + lin * (self.SlotPx + self.Gap)
            self._slots.append(ItemInventario((x, y, self.SlotPx, self.SlotPx), slot_id=i, inventario=self.Inventario, callback_troca=self._trocar_slots))

        self._sincronizar_areas_acao()
        self._montado = True

    def _sincronizar_areas_acao(self):
        for arr in self._slots:
            arr.limpar_areas_acao()
            for destino in self._slots:
                arr.adicionar_area_acao(destino.rect, callback=self._trocar_slots, area_id=destino.Id)

    def _trocar_slots(self, arrastavel, area_id, _area_rect):
        origem, destino = int(arrastavel.Id), int(area_id)
        if origem == destino:
            arrastavel.voltar_para_origem()
            return
        if origem >= len(self.Inventario.Itens):
            arrastavel.voltar_para_origem()
            return
        if destino >= len(self.Inventario.Itens):
            item_origem = self.Inventario.Itens.pop(origem)
            self.Inventario.Itens.append(item_origem)
            arrastavel.voltar_para_origem()
            return

        a = self.Inventario.Itens[origem]
        b = self.Inventario.Itens[destino]
        chave_a = self.Inventario._chave_stack(a)
        chave_b = self.Inventario._chave_stack(b)
        if isinstance(a, dict) and isinstance(b, dict) and chave_a == chave_b:
            b["quantidade"] = int(max(1, b.get("quantidade", 1))) + int(max(1, a.get("quantidade", 1)))
            self.Inventario.Itens.pop(origem)
        else:
            self.Inventario.Itens[origem], self.Inventario.Itens[destino] = b, a
        arrastavel.voltar_para_origem()

    def atualizar(self, eventos, dt, area):
        if not self._montado:
            self._reconstruir_slots(area)
        self.Painel.rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        self.Painel.definir_area_real(self.Painel.rect.width - 2, max(360, 30 + self.Linhas * (self.SlotPx + self.Gap)))

        for arr in self._slots:
            rect_original = arr.rect
            arr.rect = rect_original.move(self.Painel.rect.x - self.Painel.ScrollX, self.Painel.rect.y - self.Painel.ScrollY)

            arr.limpar_areas_acao()
            for destino in self._slots:
                destino_tela = destino.rect.move(self.Painel.rect.x - self.Painel.ScrollX, self.Painel.rect.y - self.Painel.ScrollY)
                arr.adicionar_area_acao(destino_tela, callback=self._trocar_slots, area_id=destino.Id)

            arr.update(eventos)
            arr.rect = rect_original

    def renderizar(self, tela, area, eventos, dt):
        self.atualizar(eventos, dt, area)
        self.Painel.render(tela, eventos, dt)

        for arr in self._slots:
            rect_tela = arr.rect.move(self.Painel.rect.x - self.Painel.ScrollX, self.Painel.rect.y - self.Painel.ScrollY)
            if self.Painel.rect.colliderect(rect_tela):
                antigo = arr.rect
                arr.rect = rect_tela
                arr.draw(tela)
                arr.rect = antigo
