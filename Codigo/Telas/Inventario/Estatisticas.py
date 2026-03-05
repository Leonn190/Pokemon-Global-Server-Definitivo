from __future__ import annotations

import pygame


class InventarioPerfil:
    def renderizar(self, tela, rect, inventario):
        fonte = pygame.font.SysFont("arial", 24)
        txt = fonte.render("Perfil (em construção)", True, (232, 238, 250))
        tela.blit(txt, (rect.x + 18, rect.y + 22))
