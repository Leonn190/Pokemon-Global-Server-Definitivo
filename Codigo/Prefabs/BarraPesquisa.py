from __future__ import annotations

import unicodedata

import pygame

from Codigo.Prefabs.Botao import BotaoSelecao
from Codigo.Prefabs.CaixaTexto import CaixaTexto


class BarraPesquisa(CaixaTexto):
    def __init__(self, rect: pygame.Rect, placeholder='Pesquisar...', max_chars=28):
        super().__init__(rect, texto_inicial='', placeholder=placeholder, max_chars=max_chars, ativo=True)
        self._lista_base = []
        self._acessor_nome = lambda item: str(item)
        self._ordens = []
        self._indice_ordem = None
        self._botoes_ordenacao = []
        self._projecao_indices = []

    @staticmethod
    def _norm(texto):
        base = ''.join(
            c
            for c in unicodedata.normalize('NFKD', str(texto or '').lower())
            if not unicodedata.combining(c)
        )
        return ' '.join(base.split())

    def definir_lista_base(self, lista):
        self._lista_base = lista if isinstance(lista, list) else []

    def definir_acessor_nome(self, acessor_nome):
        if callable(acessor_nome):
            self._acessor_nome = acessor_nome

    def definir_ordenacoes(self, ordenacoes):
        self._ordens = []
        self._indice_ordem = None
        self._botoes_ordenacao = []

        for item in list(ordenacoes or []):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            rotulo, chave = item[0], item[1]
            if not callable(chave):
                continue
            self._ordens.append((str(rotulo), chave))

        self._reconstruir_botoes()

    def resetar_filtro(self):
        self.set_texto('')

    def tem_projecao_ativa(self):
        return bool(self.texto.strip()) or self._indice_ordem is not None

    def _reconstruir_botoes(self):
        self._botoes_ordenacao = []
        if not self._ordens:
            return

        gap = 8
        largura_max = 128
        altura = max(30, self.rect.height - 10)
        x = self.rect.right + gap

        for indice, (rotulo, _chave) in enumerate(self._ordens):
            largura = min(largura_max, max(78, 20 + len(rotulo) * 8))

            def _acao(_jogo, _botao, idx=indice):
                self._indice_ordem = idx

            botao = BotaoSelecao(
                pygame.Rect(x, self.rect.centery - altura // 2, largura, altura),
                rotulo,
                execute=_acao,
                selecionado=(indice == self._indice_ordem),
                style={'text_style': {'size': 18, 'outline': False, 'shadow': False}},
            )
            self._botoes_ordenacao.append(botao)
            x += largura + gap

    def configurar_rect(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self._reconstruir_botoes()

    def _valor_nome(self, item):
        try:
            return self._norm(self._acessor_nome(item))
        except Exception:
            return ''

    def _valor_ordem(self, func, item):
        try:
            valor = func(item)
        except Exception:
            valor = None

        if isinstance(valor, str):
            return self._norm(valor)
        if valor is None:
            return ''
        return valor

    def atualizar_projecao(self):
        termo = self._norm(self.texto)
        base = [(i, item) for i, item in enumerate(self._lista_base) if item is not None]
        if termo:
            base = [(i, item) for i, item in base if termo in self._valor_nome(item)]

        if self._indice_ordem is not None and 0 <= self._indice_ordem < len(self._ordens):
            _rotulo, chave = self._ordens[self._indice_ordem]
            base.sort(key=lambda par: (self._valor_ordem(chave, par[1]), par[0]))

        self._projecao_indices = [indice for indice, _item in base]

    def lista_visivel(self):
        return list(self._projecao_indices)

    def render(self, tela, eventos, dt, jogo=None):
        super().render(tela, eventos, dt)
        for indice, botao in enumerate(self._botoes_ordenacao):
            botao.set_selecionado(self._indice_ordem == indice)
            botao.render(tela, eventos, dt, jogo)
