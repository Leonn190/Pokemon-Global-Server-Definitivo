from __future__ import annotations

import pygame

from Codigo.Prefabs.Botao import Botao, BotaoAlavanca
from Codigo.Prefabs.Texto import Texto


class SubtelaConfigAvancada:
    def __init__(self, jogo, estilo_base, confirmar_callback=None, cancelar_callback=None):
        self._jogo = jogo
        self._estilo_base = estilo_base
        self._confirmar_callback = confirmar_callback
        self._cancelar_callback = cancelar_callback
        self._snapshot = {k: jogo.CONFIG.get(k) for k in ("FPS Visivel", "Cords Visiveis", "Ping Visivel", "MostrarHorario", "MostrarMinimapa")}
        self._botoes_toggle = {}
        self._botao_salvar = None
        self._botao_cancelar = None
        self._titulo = None
        self._cache = None

    def _ao_toggle(self, chave, estado):
        self._jogo.CONFIG[chave] = estado

    def _montar_layout(self, tela_size):
        if self._cache == tuple(tela_size):
            return
        largura_tela, altura_tela = tela_size

        largura_toggle = 360
        altura_toggle = 70
        espaco_x = 30
        x_toggles = (largura_tela - (largura_toggle * 2 + espaco_x)) // 2
        y_toggles = int(altura_tela * 0.28)

        chaves = ["FPS Visivel", "Cords Visiveis", "Ping Visivel", "MostrarHorario", "MostrarMinimapa"]
        self._botoes_toggle = {}
        for i, chave in enumerate(chaves):
            coluna = i % 2
            linha = i // 2
            x = x_toggles + coluna * (largura_toggle + espaco_x)
            y = y_toggles + linha * (altura_toggle + 20)
            estilo_toggle = dict(self._estilo_base)
            estilo_toggle["text_style"] = dict(self._estilo_base["text_style"])
            self._botoes_toggle[chave] = BotaoAlavanca(
                pygame.Rect(x, y, largura_toggle, altura_toggle),
                chave,
                estado_inicial=bool(self._jogo.CONFIG.get(chave, False)),
                execute=lambda jogo, estado, botao, chave=chave: self._ao_toggle(chave, estado),
                style=estilo_toggle,
            )

        estilo_acao = dict(self._estilo_base)
        estilo_acao["text_style"] = dict(self._estilo_base["text_style"])
        estilo_acao["text_style"]["size"] = 34

        largura_acao = 260
        altura_acao = 80
        y_acao = int(altura_tela * 0.84)

        self._botao_cancelar = Botao(
            pygame.Rect(largura_tela // 2 - largura_acao - 20, y_acao, largura_acao, altura_acao),
            "Cancelar",
            execute=lambda jogo, botao: self.cancelar(),
            style=estilo_acao,
        )
        self._botao_salvar = Botao(
            pygame.Rect(largura_tela // 2 + 20, y_acao, largura_acao, altura_acao),
            "Salvar",
            execute=lambda jogo, botao: self.confirmar(),
            style=estilo_acao,
        )

        self._titulo = Texto(
            "Config avançada",
            pos=(largura_tela // 2, int(altura_tela * 0.13)),
            style={"size": 48, "align": "center", "outline": True, "outline_color": (0, 0, 0), "outline_thickness": 2, "shadow": True, "shadow_color": (0, 0, 0, 180), "shadow_offset": (2, 2)},
        )

        self._cache = tuple(tela_size)

    def confirmar(self):
        self._snapshot = {k: self._jogo.CONFIG.get(k) for k in self._snapshot}
        if callable(self._confirmar_callback):
            self._confirmar_callback()

    def cancelar(self):
        for chave, valor in self._snapshot.items():
            self._jogo.CONFIG[chave] = valor
        for chave, botao in self._botoes_toggle.items():
            botao.set_estado(bool(self._jogo.CONFIG.get(chave, False)))
        if callable(self._cancelar_callback):
            self._cancelar_callback()

    def render(self, tela, eventos, dt):
        self._montar_layout(tela.get_size())
        self._titulo.draw(tela)
        for botao in self._botoes_toggle.values():
            botao.render(tela, eventos, dt, JOGO=self._jogo)
        self._botao_cancelar.render(tela, eventos, dt, JOGO=self._jogo)
        self._botao_salvar.render(tela, eventos, dt, JOGO=self._jogo)
