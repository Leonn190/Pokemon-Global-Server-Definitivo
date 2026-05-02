import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.TextoCinematico import TextoCinematico


class TelaMorrer:
    def __init__(self):
        self._ativa = False
        self._alpha_fundo = 0.0
        self._alpha_conteudo = 0.0
        self._texto = TextoCinematico("GAME OVER", tamanho=92)
        self._botoes = []

    @property
    def ativa(self):
        return self._ativa

    def abrir(self, tamanho_tela: tuple[int, int], ao_ressurgir, ao_menu):
        self._ativa = True
        self._alpha_fundo = 0.0
        self._alpha_conteudo = 0.0
        w, h = tamanho_tela
        self._texto = TextoCinematico("GAME OVER", tamanho=max(44, min(110, int(w / 10))))
        bw, bh = min(340, max(220, (w - 72) // 2)), 88
        y = int(h * 0.62)
        if w < 760:
            y = min(y, max(24, h - ((bh * 2) + 14) - 24))
            self._botoes = [
                Botao(pygame.Rect(w // 2 - bw // 2, y, bw, bh), "Ressurgir", execute=lambda jogo, botao: ao_ressurgir()),
                Botao(pygame.Rect(w // 2 - bw // 2, y + bh + 14, bw, bh), "Voltar ao menu", execute=lambda jogo, botao: ao_menu()),
            ]
        else:
            self._botoes = [
                Botao(pygame.Rect(w // 2 - bw - 24, y, bw, bh), "Ressurgir", execute=lambda jogo, botao: ao_ressurgir()),
                Botao(pygame.Rect(w // 2 + 24, y, bw, bh), "Voltar ao menu", execute=lambda jogo, botao: ao_menu()),
            ]

    def fechar(self):
        self._ativa = False

    def atualizar(self, eventos, dt, jogo):
        if not self._ativa:
            return
        self._alpha_fundo = min(255.0, self._alpha_fundo + (360.0 * dt))
        if self._alpha_fundo >= 255.0:
            self._alpha_conteudo = min(255.0, self._alpha_conteudo + (300.0 * dt))

    def desenhar(self, surface: pygame.Surface, eventos, dt, jogo):
        if not self._ativa:
            return
        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, int(self._alpha_fundo)))
        surface.blit(ov, (0, 0))

        self._texto.set_alpha(self._alpha_conteudo)
        self._texto.desenhar(surface, (surface.get_width() // 2, int(surface.get_height() * 0.36)))

        if self._alpha_conteudo < 255:
            return
        for botao in self._botoes:
            botao.render(surface, eventos, dt, JOGO=jogo)
