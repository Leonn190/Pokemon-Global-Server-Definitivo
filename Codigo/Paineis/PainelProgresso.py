from __future__ import annotations

import pygame

from Codigo.Prefabs.Botao import Botao


class PainelProgresso:
    def __init__(self, ator=None):
        self.Ator = ator
        self._botao_fechar = None

    def renderizar(self, tela, rect, eventos=None, dt=0.0):
        eventos = eventos or []
        fundo = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        fundo.fill((8, 12, 24, 236))
        tela.blit(fundo, rect.topleft)
        if self._botao_fechar is None:
            self._botao_fechar = Botao(pygame.Rect(rect.right - 58, rect.y + 12, 44, 44), "X", execute=lambda _j, _b: None, style={"bg": (186, 36, 36), "bg_hover": (220, 52, 52), "bg_pressed": (150, 26, 26), "radius": 10, "text_style": {"size": 26, "outline_thickness": 1, "shadow": False}})
        self._botao_fechar.base_rect.topleft = (rect.right - 58, rect.y + 12)
        return bool(self._botao_fechar.render(tela, eventos, dt, None))
