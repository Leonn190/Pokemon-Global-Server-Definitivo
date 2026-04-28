from __future__ import annotations

import pygame

from Codigo.Prefabs.Botao import BotaoSelecao
from Codigo.Telas.Subtelas.SubtelaInventarioEstatisticas import InventarioPerfil
from Codigo.Telas.Subtelas.SubtelaInventarioItens import InventarioItens
from Codigo.Telas.Subtelas.SubtelaInventarioPokemons import InventarioPokemons


from Codigo.Telas.Subtelas.Subtela import Subtela


class SubtelaInventario(Subtela):
    alpha_overlay = 170

    def __init__(self, ator):
        super().__init__()
        self.Ator = ator
        self._jogo = None
        self.Inventario = ator.Inventario
        self.Ativo = False
        self.Modo = "perfil"
        self._modo_anterior = self.Modo
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._botoes = []
        self._tamanho_layout = None
        self._ativo_anterior = False
        self._eventos_pendentes = []
        self._tamanho_tela = None

        self.TelaPerfil = InventarioPerfil(ator)
        self.TelaPokemons = InventarioPokemons(
            ator,
            abrir_modal=self._abrir_modal,
            possui_modal=self._possui_modal,
        )
        self.TelaItens = InventarioItens(ator)

    def _abrir_modal(self, modal):
        if self._jogo is None or modal is None:
            return
        self._jogo.GerenciadorSubtelas.abrir(modal)

    def _possui_modal(self):
        return self._jogo is not None and self._jogo.GerenciadorSubtelas.topo is not self

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
        ordem_abas = (("Perfil", "perfil"), ("Pokemons", "pokemons"), ("Itens", "itens"))
        for i, (texto, modo) in enumerate(ordem_abas):
            def _acao(_jogo, _botao, m=modo):
                self.Modo = m

            botao = BotaoSelecao(pygame.Rect(bx + i * (bw + gap), topo, bw, bh), texto, execute=_acao, selecionado=(self.Modo == modo))
            botoes.append(botao)
        self._botoes = botoes

    def _tela_por_modo(self, modo):
        if modo == 'pokemons':
            return self.TelaPokemons
        if modo == 'itens':
            return self.TelaItens
        return self.TelaPerfil

    def _chamar_se_existir(self, tela, nome):
        metodo = getattr(tela, nome, None)
        if callable(metodo):
            metodo()

    def bloquear_toggle_inventario(self):
        if not self.Ativo:
            return False
        tela_atual = self._tela_por_modo(self.Modo)
        metodo = getattr(tela_atual, "bloqueia_toggle_inventario", None)
        return bool(metodo()) if callable(metodo) else False

    def processar_eventos(self, jogo, eventos):
        self._jogo = jogo
        self._eventos_pendentes = []
        for evento in list(eventos or []):
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_e and self.Ativo and not self.bloquear_toggle_inventario():
                self.Ativo = False
                controle = getattr(self.Ator, "Controle", None)
                if controle is not None and hasattr(controle, "InventarioAberto"):
                    controle.InventarioAberto = False
                continue
            self._eventos_pendentes.append(evento)
        self._tamanho_tela = jogo.TELA.get_size() if jogo is not None else self._tamanho_tela
        controle = getattr(self.Ator, "Controle", None)
        if controle is not None and hasattr(controle, "InventarioAberto"):
            self.Ativo = bool(controle.InventarioAberto)
        return self.Ativo

    def atualizar(self, dt):
        eventos = self._eventos_pendentes
        tamanho_tela = self._tamanho_tela or (0, 0)
        self._recalcular_layout(tamanho_tela)

        if self.Ativo:
            for evento in eventos:
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and not self._rect.collidepoint(evento.pos):
                    if self.Modo == "itens":
                        tratar_fora = getattr(self.TelaItens, "tratar_clique_fora", None)
                        if callable(tratar_fora) and tratar_fora(evento):
                            break
                    self.Ativo = False
                    controle = getattr(self.Ator, 'Controle', None)
                    if controle is not None and hasattr(controle, 'InventarioAberto'):
                        controle.InventarioAberto = False
                    break

        tela_atual = self._tela_por_modo(self.Modo)
        tela_anterior = self._tela_por_modo(self._modo_anterior)

        if self._ativo_anterior and not self.Ativo:
            self._chamar_se_existir(tela_anterior, 'on_close')
        elif self.Ativo and not self._ativo_anterior:
            self._chamar_se_existir(tela_atual, 'on_open')
        elif self.Ativo and self.Modo != self._modo_anterior:
            self._chamar_se_existir(tela_anterior, 'on_close')
            self._chamar_se_existir(tela_atual, 'on_open')

        self._ativo_anterior = self.Ativo
        self._modo_anterior = self.Modo

    def desenhar(self, tela, eventos, dt):
        if not self.Ativo:
            return

        sombra = self._rect.inflate(12, 12)
        pygame.draw.rect(tela, (8, 12, 22, 90), sombra, border_radius=22)
        pygame.draw.rect(tela, (24, 32, 52), self._rect, border_radius=20)
        pygame.draw.rect(tela, (76, 104, 168), self._rect, 2, border_radius=20)

        header = pygame.Rect(self._rect.x + 10, self._rect.y + 10, self._rect.width - 20, 64)
        pygame.draw.rect(tela, (20, 26, 42), header, border_radius=16)
        pygame.draw.rect(tela, (52, 70, 110), header, 1, border_radius=16)

        for botao, modo in zip(self._botoes, ("perfil", "pokemons", "itens")):
            botao.set_selecionado(self.Modo == modo)
            botao.render(tela, eventos, dt, None)

        area_conteudo = pygame.Rect(self._rect.x + 16, self._rect.y + 84, self._rect.width - 32, self._rect.height - 100)
        pygame.draw.rect(tela, (15, 22, 38), area_conteudo, border_radius=16)
        pygame.draw.rect(tela, (58, 80, 128), area_conteudo, 2, border_radius=16)

        if self.Modo == "perfil":
            self.TelaPerfil.renderizar(tela, area_conteudo, self.Inventario, eventos=eventos, dt=dt)
        elif self.Modo == "pokemons":
            self.TelaPokemons.renderizar(tela, area_conteudo, eventos, dt, ativo=self.Ativo)
        else:
            self.TelaItens.renderizar(tela, area_conteudo, eventos, dt, ativo=self.Ativo)

    @property
    def ativa(self):
        return bool(self.Ativo) and not self.encerrada

    def render(self, tela, eventos, dt, JOGO=None):
        self._jogo = JOGO
        self.desenhar(tela, eventos, dt)
