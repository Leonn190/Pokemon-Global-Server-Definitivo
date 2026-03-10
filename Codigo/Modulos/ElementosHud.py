from __future__ import annotations

import pygame

from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto


class ElementosHud:
    def __init__(self):
        self.Fonte = pygame.font.SysFont("arial", 15)
        self.SlotsVisiveis = 8
        self.TextoQtd = Texto("", style={"size": 14, "align": "bottomright", "outline_thickness": 1})

    def desenhar(self, tela, inventario, terminal=None, eventos=None, dt=0.0):
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

            if i >= len(inventario.Itens):
                continue
            item = inventario.Itens[i]
            if item is None:
                continue
            sprite = ItemInventario.surface_item(item, lado_px=28)
            if sprite is not None:
                tela.blit(sprite, sprite.get_rect(center=rect.center))
            else:
                nome = ItemInventario.nome_item(item)
                if nome and str(nome).lower() != "none":
                    txt = self.Fonte.render(nome[:6], True, (245, 245, 250))
                    tela.blit(txt, txt.get_rect(center=rect.center))

            qtd = int(item.get("quantidade", 1)) if isinstance(item, dict) else 1
            if qtd > 1:
                self.TextoQtd.set_text(str(qtd))
                self.TextoQtd.set_pos((rect.right - 2, rect.bottom - 1))
                self.TextoQtd.draw(tela)

        if terminal is not None:
            terminal.desenhar(tela, eventos or [], dt)
