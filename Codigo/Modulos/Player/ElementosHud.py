from __future__ import annotations

import pygame


class ElementosHud:
    def __init__(self):
        self.Fonte = pygame.font.SysFont("arial", 15)
        self.SlotsVisiveis = 8

    def desenhar(self, tela, inventario):
        largura, altura = tela.get_size()
        slot = 42
        gap = 8
        total = (slot * self.SlotsVisiveis) + (gap * (self.SlotsVisiveis - 1))
        x0 = (largura - total) // 2
        y = altura - slot - 20

        for i in range(self.SlotsVisiveis):
            rect = pygame.Rect(x0 + i * (slot + gap), y, slot, slot)
            selecionado = i == inventario.SlotSelecionado
            bg = (64, 68, 80) if not selecionado else (220, 190, 90)
            pygame.draw.rect(tela, bg, rect, border_radius=6)
            pygame.draw.rect(tela, (20, 22, 30), rect, 2, border_radius=6)

            if i < len(inventario.Itens):
                item = inventario.Itens[i]
                nome = str(item.get("nome", "item")) if isinstance(item, dict) else str(item)
                txt = self.Fonte.render(nome[:6], True, (245, 245, 250))
                tela.blit(txt, txt.get_rect(center=rect.center))
