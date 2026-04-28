"""Subtela de opções para a cena de mundo."""

from __future__ import annotations

import pygame
from Codigo.ModulosGerais.Sonoridades import tocar
from Codigo.Prefabs.Botao import Botao
from Codigo.Telas.Subtelas.Subtela import Subtela


class SubtelaOpcoes(Subtela):
    alpha_overlay = 150

    def __init__(self):
        super().__init__()
        self.Ativa = False
        self.Botoes = []
        self._botoes_ui = []
        self._tamanho_layout = None
        self._ignorar_esc = False
        self._fonte = pygame.font.SysFont("arial", 44, bold=True)
        self._estilo_botao = {
            "radius": 20,
            "border_width": 2,
            "border": (56, 76, 126),
            "border_hover": (255, 224, 135),
            "bg": (30, 44, 78),
            "bg_hover": (60, 86, 146),
            "bg_pressed": (22, 33, 62),
            "hover_scale": 1.03,
            "press_scale": 0.985,
            "text_style": {
                "size": 40,
                "color": (247, 250, 255),
                "hover_color": (255, 226, 120),
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 1,
                "shadow": True,
                "shadow_color": (0, 0, 0, 170),
                "shadow_offset": (2, 2),
            },
        }

    def toggle(self, jogo):
        self.Ativa = not self.Ativa
        if self.Ativa:
            tocar("Abre")
            self._ignorar_esc = True
            self._recalcular_layout(jogo)
        else:
            tocar("Fecha")

    def _recalcular_layout(self, jogo):
        w, h = jogo.TELA.get_size()
        tamanho = (w, h)
        if self._tamanho_layout == tamanho and self.Botoes:
            return

        self._tamanho_layout = tamanho
        bw, bh = min(520, int(w * 0.50)), 94
        cx = w // 2 - bw // 2
        y0 = h // 2 - 150
        gap = 20
        self.Botoes = [
            (pygame.Rect(cx, y0 + (bh + gap) * 0, bw, bh), "Voltar ao jogo", self._acao_voltar),
            (pygame.Rect(cx, y0 + (bh + gap) * 1, bw, bh), "Configurações", self._acao_config),
            (pygame.Rect(cx, y0 + (bh + gap) * 2, bw, bh), "Sair do mundo", self._acao_sair_mundo),
        ]
        self._botoes_ui = [
            Botao(rect, texto, execute=(lambda jogo, _botao, f=acao: f(jogo)), style=self._estilo_botao)
            for rect, texto, acao in self.Botoes
        ]

    def processar_eventos(self, jogo, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                if self._ignorar_esc:
                    self._ignorar_esc = False
                    continue
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

    def desenhar(self, tela, jogo, dt: float = 0.0):
        if not self.Ativa:
            return
        self._recalcular_layout(jogo)

        for botao in self._botoes_ui:
            rect = botao.rect
            sombra = pygame.Rect(rect.x + 2, rect.y + 4, rect.w, rect.h)
            pygame.draw.rect(tela, (12, 16, 32, 120), sombra, border_radius=20)
            botao.render(tela, [], dt, JOGO=jogo)

    def render(self, tela, eventos, dt, JOGO=None):
        if JOGO is None:
            return
        self.desenhar(tela, JOGO, dt)

    def _acao_voltar(self, jogo):
        self.Ativa = False
        tocar("Fecha")

    def _acao_config(self, jogo):
        self.Ativa = False
        cena = getattr(jogo, "Cena", None)
        if cena is not None and callable(getattr(cena, "DefinirTela", None)):
            cena.DefinirTela("Config")
            if getattr(cena, "ID", "") == "Mundo":
                jogo.INFO["MundoTelaSobreposta"] = "Config"
            else:
                jogo.INFO.pop("MundoTelaSobreposta", None)

    def _acao_sair_mundo(self, jogo):
        self.Ativa = False
        jogo.INFO.pop("MundoTelaSobreposta", None)
        jogo.INFO["MenuTelaInicial"] = "MenuPrincipal"
        jogo.CenaAlvo = "Menu"
