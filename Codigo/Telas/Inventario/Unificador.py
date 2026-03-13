from __future__ import annotations

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Telas.Inventario.Estatisticas import InventarioPerfil
from Codigo.Telas.Inventario.InventarioItens import InventarioItens
from Codigo.Telas.Inventario.Pokemons import InventarioPokemons


class UnificadorInventario:
    def __init__(self, ator):
        self.Ator = ator
        self.Inventario = ator.Inventario
        self.Ativo = False
        self.Modo = "itens"
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._botoes = []
        self._tamanho_layout = None
        self._overlay_cache = None
        self._overlay_cache_size = None
        self._ativo_anterior = False

        self.TelaPerfil = InventarioPerfil()
        self.TelaPokemons = InventarioPokemons()
        self.TelaItens = InventarioItens(ator)

    def toggle(self):
        self.Ativo = not self.Ativo

    def _recalcular_layout(self, tamanho_tela):
        if self._tamanho_layout == tuple(tamanho_tela) and self._botoes:
            return
        self._tamanho_layout = tuple(tamanho_tela)

        largura, altura = tamanho_tela
        w = min(1210, int(largura * 0.93))
        h = min(760, int(altura * 0.90))
        self._rect = pygame.Rect((largura - w) // 2, (altura - h) // 2, w, h)

        topo = self._rect.y + 18
        bw, bh, gap = 182, 48, 18
        total = bw * 3 + gap * 2
        bx = self._rect.centerx - total // 2

        botoes = []
        for i, (texto, modo) in enumerate((("Perfil", "perfil"), ("Pokemons", "pokemons"), ("Itens", "itens"))):
            def _acao(_jogo, _botao, m=modo):
                self.Modo = m

            botao = Botao(pygame.Rect(bx + i * (bw + gap), topo, bw, bh), texto, execute=_acao)
            botoes.append(botao)
        self._botoes = botoes

    def atualizar(self, eventos, dt, tamanho_tela):
        self._recalcular_layout(tamanho_tela)

        if self._ativo_anterior and not self.Ativo:
            self.TelaItens.on_close()
        elif self.Ativo and not self._ativo_anterior:
            self.TelaItens.on_open()

        self._ativo_anterior = self.Ativo

    def desenhar(self, tela, eventos, dt):
        if not self.Ativo:
            return

        tamanho_tela = tela.get_size()
        if self._overlay_cache is None or self._overlay_cache_size != tamanho_tela:
            self._overlay_cache = pygame.Surface(tamanho_tela, pygame.SRCALPHA)
            self._overlay_cache.fill((0, 0, 0, 170))
            self._overlay_cache_size = tamanho_tela
        tela.blit(self._overlay_cache, (0, 0))

        sombra = self._rect.inflate(12, 12)
        pygame.draw.rect(tela, (8, 12, 22, 90), sombra, border_radius=22)
        pygame.draw.rect(tela, (24, 32, 52), self._rect, border_radius=20)
        pygame.draw.rect(tela, (76, 104, 168), self._rect, 2, border_radius=20)

        header = pygame.Rect(self._rect.x + 10, self._rect.y + 10, self._rect.width - 20, 64)
        pygame.draw.rect(tela, (20, 26, 42), header, border_radius=16)
        pygame.draw.rect(tela, (52, 70, 110), header, 1, border_radius=16)

        for botao in self._botoes:
            botao.render(tela, eventos, dt, None)

        area_conteudo = pygame.Rect(self._rect.x + 16, self._rect.y + 84, self._rect.width - 32, self._rect.height - 100)
        pygame.draw.rect(tela, (15, 22, 38), area_conteudo, border_radius=16)
        pygame.draw.rect(tela, (58, 80, 128), area_conteudo, 2, border_radius=16)

        if self.Modo == "perfil":
            self.TelaPerfil.renderizar(tela, area_conteudo, self.Inventario)
        elif self.Modo == "pokemons":
            self.TelaPokemons.renderizar(tela, area_conteudo, self.Inventario)
        else:
            self.TelaItens.renderizar(tela, area_conteudo, eventos, dt, ativo=self.Ativo)
            