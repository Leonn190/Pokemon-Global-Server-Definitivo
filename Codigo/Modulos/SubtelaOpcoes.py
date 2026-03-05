"""Subtela de opções para a cena de mundo."""

from __future__ import annotations

import pygame


class SubtelaOpcoes:
    def __init__(self):
        self.Ativa = False
        self.Botoes = []

    def toggle(self, jogo):
        self.Ativa = not self.Ativa
        if self.Ativa:
            self._recalcular_layout(jogo)

    def _recalcular_layout(self, jogo):
        w, h = jogo.TELA.get_size()
        bw, bh = 360, 64
        cx = w // 2 - bw // 2
        y0 = h // 2 - 120
        gap = 18
        self.Botoes = [
            (pygame.Rect(cx, y0 + (bh + gap) * 0, bw, bh), "Voltar ao jogo", self._acao_voltar),
            (pygame.Rect(cx, y0 + (bh + gap) * 1, bw, bh), "Acessar tela de Config", self._acao_config),
            (pygame.Rect(cx, y0 + (bh + gap) * 2, bw, bh), "Sair do mundo", self._acao_sair_mundo),
        ]

    def processar_eventos(self, jogo, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                self.toggle(jogo)
                return True
            if not self.Ativa:
                continue
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self._recalcular_layout(jogo)
                for rect, _, acao in self.Botoes:
                    if rect.collidepoint(evento.pos):
                        acao(jogo)
                        return True
        return self.Ativa

    def desenhar(self, jogo):
        if not self.Ativa:
            return
        self._recalcular_layout(jogo)

        overlay = pygame.Surface(jogo.TELA.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        jogo.TELA.blit(overlay, (0, 0))

        mouse = pygame.mouse.get_pos()
        fonte = pygame.font.SysFont(None, 34)

        for rect, texto, _ in self.Botoes:
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(jogo.TELA, (55, 65, 85) if hover else (32, 38, 52), rect, border_radius=12)
            pygame.draw.rect(jogo.TELA, (200, 210, 230), rect, 2, border_radius=12)
            surf = fonte.render(texto, True, (235, 240, 252))
            jogo.TELA.blit(surf, surf.get_rect(center=rect.center))

    def _acao_voltar(self, jogo):
        self.Ativa = False

    def _acao_config(self, jogo):
        if hasattr(jogo, "FilaMensagensTecnicas"):
            jogo.FilaMensagensTecnicas.append("Tela de Config ainda não conectada nesta subtela.")

    def _acao_sair_mundo(self, jogo):
        self.Ativa = False
        jogo.CenaAlvo = "Menu"
