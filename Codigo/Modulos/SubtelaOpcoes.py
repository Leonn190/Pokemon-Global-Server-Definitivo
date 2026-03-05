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
        bw, bh = min(460, int(w * 0.44)), 82
        cx = w // 2 - bw // 2
        y0 = h // 2 - 150
        gap = 18
        self.Botoes = [
            (pygame.Rect(cx, y0 + (bh + gap) * 0, bw, bh), "Voltar ao jogo", self._acao_voltar),
            (pygame.Rect(cx, y0 + (bh + gap) * 1, bw, bh), "Configurações", self._acao_config),
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
        overlay.fill((0, 0, 0, 150))
        jogo.TELA.blit(overlay, (0, 0))

        mouse = pygame.mouse.get_pos()
        fonte = pygame.font.SysFont(None, 40)

        for rect, texto, _ in self.Botoes:
            hover = rect.collidepoint(mouse)
            cor_bg = (34, 48, 84) if hover else (24, 34, 62)
            cor_borda = (255, 220, 120) if hover else (16, 22, 42)
            pygame.draw.rect(jogo.TELA, cor_bg, rect, border_radius=16)
            pygame.draw.rect(jogo.TELA, cor_borda, rect, 2, border_radius=16)
            surf = fonte.render(texto, True, (245, 246, 255))
            jogo.TELA.blit(surf, surf.get_rect(center=rect.center))

    def _acao_voltar(self, jogo):
        self.Ativa = False

    def _acao_config(self, jogo):
        self.Ativa = False
        jogo.INFO["ConfigRetorno"] = {
            "Cena": jogo.Cena.ID,
            "TelaAtual": getattr(jogo.Cena, "TelaAtual", None),
        }
        jogo.INFO["MenuTelaInicial"] = "Config"
        jogo.INFO["PreservarMusicaAtual"] = True
        jogo.CenaAlvo = "Menu"

    def _acao_sair_mundo(self, jogo):
        self.Ativa = False
        jogo.INFO["MenuTelaInicial"] = "MenuPrincipal"
        jogo.CenaAlvo = "Menu"
