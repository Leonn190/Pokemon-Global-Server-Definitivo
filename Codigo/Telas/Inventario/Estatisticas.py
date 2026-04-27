from __future__ import annotations

import pygame

from Codigo.Paineis.PainelEstatisticas import PainelEstatisticas
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class InventarioPerfil:
    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._painel_estatisticas = PainelEstatisticas(ator)
        self._botoes_rotas: list[tuple[Texto, Botao]] = []
        self._area_rotas = pygame.Rect(0, 0, 0, 0)

    def _reconstruir_layout(self, rect: pygame.Rect):
        chave = (rect.x, rect.y, rect.width, rect.height)
        if self._layout_chave == chave:
            return

        self._layout_chave = chave
        self._area_rotas = pygame.Rect(rect.x + 16, rect.bottom - 96, rect.width - 32, 82)

        rotas = [
            ("Intelectual", (76, 108, 178), (108, 143, 216)),
            ("Magnata", (155, 118, 33), (193, 149, 46)),
            ("Herói", (45, 130, 88), (61, 160, 109)),
            ("Campeão", (136, 52, 118), (168, 68, 146)),
            ("Imperador", (142, 62, 42), (180, 79, 56)),
        ]
        self._botoes_rotas = []
        gap = 12
        largura_botao = (self._area_rotas.width - gap * 4) // 5
        for i, (nome, cor, cor_hover) in enumerate(rotas):
            bx = self._area_rotas.x + i * (largura_botao + gap)
            label = Texto("caminho do", style={"outline": True, "outline_thickness": 1, "outline_color": (0, 0, 0), "shadow": False, "size": 14, "color": (154, 170, 204)})
            botao = Botao(
                pygame.Rect(bx, self._area_rotas.y + 18, largura_botao, 60),
                nome,
                execute=None,
                style={
                    "radius": 18,
                    "bg": cor,
                    "bg_hover": cor_hover,
                    "bg_pressed": cor,
                    "border": (227, 235, 255),
                    "border_hover": (255, 245, 214),
                    "text_style": {"size": 21, "outline_thickness": 1, "shadow": False},
                },
            )
            self._botoes_rotas.append((label, botao))

    def on_open(self):
        self._painel_estatisticas.on_open()

    def on_close(self):
        self._painel_estatisticas.on_close()

    def _desenhar_rotas(self, tela, eventos, dt):
        for label, botao in self._botoes_rotas:
            label.set_pos((botao.base_rect.x + 18, botao.base_rect.y + 2))
            label.draw(tela)
            botao.render(tela, eventos, dt, None)

    def renderizar(self, tela, rect, inventario=None, eventos=None, dt=0.0):
        self._painel_estatisticas.Ator = self.Ator
        self._reconstruir_layout(pygame.Rect(rect))
        self._painel_estatisticas.renderizar(tela, rect, inventario=inventario, eventos=eventos, dt=dt)
        self._desenhar_rotas(tela, eventos or [], dt)
