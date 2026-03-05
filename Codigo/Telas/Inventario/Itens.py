from __future__ import annotations

import pygame

from Codigo.Prefabs.Arrastavel import Arrastavel
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

    def _garantir_lista_itens(self):
        while len(self.Inventario.Itens) < self.TotalSlots:
            idx = len(self.Inventario.Itens) + 1
            self.Inventario.Itens.append({"nome": f"Item {idx}"})

    def _reconstruir_slots(self, area):
        self._garantir_lista_itens()
        self._slots.clear()
        painel_rect = pygame.Rect(area.x + 10, area.y + 10, area.width - 20, area.height - 20)
        self.Painel = PainelRolavel(painel_rect, area_real=(0, 0, painel_rect.width - 2, 420), cor_fundo=(30, 36, 54, 240))

        for i in range(self.TotalSlots):
            col = i % self.Colunas
            lin = i // self.Colunas
            x = 18 + col * (self.SlotPx + self.Gap)
            y = 18 + lin * (self.SlotPx + self.Gap)
            arr = Arrastavel((x, y, self.SlotPx, self.SlotPx), id_arrastavel=i, desenhar_callback=self._desenhar_slot)
            self._slots.append(arr)

        self._sincronizar_areas_acao()
        self._montado = True

    def _sincronizar_areas_acao(self):
        for arr in self._slots:
            arr.limpar_areas_acao()
            for destino in self._slots:
                arr.adicionar_area_acao(destino.rect, callback=self._trocar_slots, area_id=destino.Id)

    def _trocar_slots(self, arrastavel, area_id, _area_rect):
        origem = int(arrastavel.Id)
        destino = int(area_id)
        if origem == destino:
            arrastavel.voltar_para_origem()
            return
        self.Inventario.Itens[origem], self.Inventario.Itens[destino] = self.Inventario.Itens[destino], self.Inventario.Itens[origem]
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

    def _desenhar_slot(self, tela, arrastavel):
        pygame.draw.rect(tela, (76, 96, 140), arrastavel.rect, border_radius=8)
        pygame.draw.rect(tela, (20, 26, 40), arrastavel.rect, 2, border_radius=8)
        item = self.Inventario.Itens[int(arrastavel.Id)]
        nome = str(item.get("nome", "Vazio")) if isinstance(item, dict) else str(item)
        fonte = pygame.font.SysFont("arial", 16)
        txt = fonte.render(nome[:9], True, (244, 246, 255))
        tela.blit(txt, txt.get_rect(center=arrastavel.rect.center))
