from __future__ import annotations

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Telas.Inventario.Estatisticas import InventarioPerfil
from Codigo.Telas.Inventario.Itens import InventarioItens
from Codigo.Telas.Inventario.Pokemons import InventarioPokemons


class UnificadorInventario:
    def __init__(self, inventario):
        self.Inventario = inventario
        self.Ativo = False
        self.Modo = "itens"
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._botoes = []

        self.TelaPerfil = InventarioPerfil()
        self.TelaPokemons = InventarioPokemons()
        self.TelaItens = InventarioItens(inventario)

    def toggle(self):
        self.Ativo = not self.Ativo

    def _recalcular_layout(self, tamanho_tela):
        largura, altura = tamanho_tela
        w = min(860, int(largura * 0.82))
        h = min(620, int(altura * 0.82))
        self._rect = pygame.Rect((largura - w) // 2, (altura - h) // 2, w, h)

        topo = self._rect.y + 14
        bx = self._rect.x + 24
        bw, bh, gap = 170, 46, 14

        botoes = []
        for i, (texto, modo) in enumerate((("Perfil", "perfil"), ("Pokemons", "pokemons"), ("Itens", "itens"))):
            def _acao(_jogo, _botao, m=modo):
                self.Modo = m

            botao = Botao(pygame.Rect(bx + i * (bw + gap), topo, bw, bh), texto, execute=_acao)
            botoes.append(botao)
        self._botoes = botoes

    def atualizar(self, eventos, dt, tamanho_tela):
        if not self.Ativo:
            return
        self._recalcular_layout(tamanho_tela)

        for botao in self._botoes:
            botao.render(pygame.display.get_surface(), eventos, dt, None)

    def desenhar(self, tela, eventos, dt):
        if not self.Ativo:
            return
        overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        tela.blit(overlay, (0, 0))

        pygame.draw.rect(tela, (30, 36, 54), self._rect, border_radius=14)
        pygame.draw.rect(tela, (100, 120, 170), self._rect, 2, border_radius=14)

        for botao in self._botoes:
            botao.render(tela, eventos, dt, None)

        area_conteudo = pygame.Rect(self._rect.x + 16, self._rect.y + 76, self._rect.width - 32, self._rect.height - 92)
        pygame.draw.rect(tela, (24, 28, 42), area_conteudo, border_radius=10)

        if self.Modo == "perfil":
            self.TelaPerfil.renderizar(tela, area_conteudo, self.Inventario)
        elif self.Modo == "pokemons":
            self.TelaPokemons.renderizar(tela, area_conteudo, self.Inventario)
        else:
            self.TelaItens.renderizar(tela, area_conteudo, eventos, dt)
