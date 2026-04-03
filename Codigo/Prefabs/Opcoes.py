from __future__ import annotations

import pygame

from Codigo.Modulos.Sonoridades import tocar
from Codigo.Prefabs.Botao import Botao


_ESTILO_BOTAO_OPCOES = {
    "radius": 0,
    "border_width": 1,
    "bg": (28, 34, 50),
    "bg_hover": (48, 62, 96),
    "bg_pressed": (22, 28, 42),
    "border": (8, 12, 20),
    "border_hover": (180, 198, 242),
    "hover_scale": 1.0,
    "press_scale": 1.0,
    "text_style": {
        "size": 14,
        "color": (238, 242, 255),
        "hover_color": (255, 255, 255),
        "outline": False,
        "shadow": False,
        "align": "midleft",
    },
    "text_anchor": "left",
}


class Opções:
    def __init__(self):
        self.Ativa = False
        self.Rect = pygame.Rect(0, 0, 0, 0)
        self._botoes = []
        self._largura = 162
        self._altura_item = 28

    def abrir(self, origem_pos, opcoes, tela_rect=None):
        self.fechar()
        opcoes_validas = [o for o in list(opcoes or []) if isinstance(o, dict) and callable(o.get("acao"))]
        if not opcoes_validas:
            return

        largura = max(120, int(max([self._largura] + [o.get("largura", self._largura) for o in opcoes_validas])))
        altura_item = max(24, int(max([self._altura_item] + [o.get("altura", self._altura_item) for o in opcoes_validas])))
        altura_total = altura_item * len(opcoes_validas)

        x, y = int(origem_pos[0]), int(origem_pos[1])
        tela_rect = pygame.Rect(tela_rect) if tela_rect is not None else None
        if tela_rect is not None:
            if x + largura > tela_rect.right - 2:
                x = tela_rect.right - largura - 2
            if y + altura_total > tela_rect.bottom - 2:
                y = tela_rect.bottom - altura_total - 2
            x = max(tela_rect.left + 2, x)
            y = max(tela_rect.top + 2, y)

        self.Rect = pygame.Rect(x, y, largura, altura_total)
        self._botoes = []
        tocar("CliqueOpções")

        for i, opcao in enumerate(opcoes_validas):
            rect = pygame.Rect(x, y + i * altura_item, largura, altura_item)

            def _acao(jogo, _botao, fn=opcao["acao"]):
                fn()
                self.fechar()

            botao = Botao(rect, str(opcao.get("texto") or "Opção"), execute=_acao, style=_ESTILO_BOTAO_OPCOES)
            botao.text.set_style(align="midleft")
            self._botoes.append(botao)

        self.Ativa = True

    def fechar(self):
        self.Ativa = False
        self._botoes = []
        self.Rect = pygame.Rect(0, 0, 0, 0)

    def processar_eventos(self, eventos):
        if not self.Ativa:
            return False

        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                self.fechar()
                return True
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button in (1, 3):
                if not self.Rect.collidepoint(evento.pos):
                    self.fechar()
                    return True

        return False

    def render(self, tela, eventos, dt, jogo=None):
        if not self.Ativa:
            return

        self.processar_eventos(eventos)
        if not self.Ativa:
            return

        fundo = pygame.Surface(self.Rect.size, pygame.SRCALPHA)
        fundo.fill((12, 16, 26, 230))
        tela.blit(fundo, self.Rect.topleft)
        pygame.draw.rect(tela, (8, 12, 20), self.Rect, 1)

        for botao in self._botoes:
            botao.render(tela, eventos, dt, JOGO=jogo)


Opcoes = Opções
