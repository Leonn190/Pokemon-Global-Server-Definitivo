from __future__ import annotations

import unicodedata

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.CaixaTexto import CaixaTexto


class BarraPesquisa(CaixaTexto):
    def __init__(self, rect: pygame.Rect, placeholder='Pesquisar...', max_chars=28):
        super().__init__(rect, texto_inicial='', placeholder=placeholder, max_chars=max_chars, ativo=True)
        self._lista_base = []
        self._indices_fixos_imutaveis = 0
        self._acessor_nome = lambda item: str(item)
        self._ordens = []
        self._botoes_ordenacao = []
        self._projecao_indices = []
        self._projecao_suja = True
        self._rect_cache = pygame.Rect(self.rect)
        self._cache_nome_normalizado = {}

    @staticmethod
    def _norm(texto):
        base = ''.join(
            c
            for c in unicodedata.normalize('NFKD', str(texto or '').lower())
            if not unicodedata.combining(c)
        )
        return ' '.join(base.split())

    def definir_lista_base(self, lista):
        nova_lista = lista if isinstance(lista, list) else []
        if nova_lista is not self._lista_base:
            self._lista_base = nova_lista
            self._cache_nome_normalizado.clear()
            self._projecao_suja = True

    def definir_prefixo_imutavel(self, quantidade):
        self._indices_fixos_imutaveis = max(0, int(quantidade))
        self._projecao_suja = True

    def definir_acessor_nome(self, acessor_nome):
        if callable(acessor_nome):
            self._acessor_nome = acessor_nome

    def definir_ordenacoes(self, ordenacoes):
        self._ordens = []
        self._botoes_ordenacao = []

        for item in list(ordenacoes or []):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            rotulo = str(item[0])
            if len(item) >= 3 and callable(item[2]):
                self._ordens.append((rotulo, 'acao', item[2]))
                continue
            if callable(item[1]):
                self._ordens.append((rotulo, 'ordem', item[1]))
        self._reconstruir_botoes()

    def resetar_filtro(self):
        self.set_texto('')

    def tem_projecao_ativa(self):
        return bool(self.texto.strip())

    def esta_editando(self):
        return bool(self.selecionada)

    def set_texto(self, texto):
        texto_anterior = self.texto
        super().set_texto(texto)
        if self.texto != texto_anterior:
            self._projecao_suja = True

    def _aplicar_ordenacao(self, indice):
        if not (0 <= int(indice) < len(self._ordens)):
            return
        if not isinstance(self._lista_base, list):
            return

        _rotulo, _tipo, chave = self._ordens[int(indice)]
        prefixo = max(0, min(self._indices_fixos_imutaveis, len(self._lista_base)))
        itens_com_idx = [(idx, item) for idx, item in enumerate(self._lista_base[prefixo:], start=prefixo) if item is not None]
        itens_com_idx.sort(key=lambda par: (self._valor_ordem(chave, par[1]), par[0]))

        total = len(self._lista_base)
        for i, (_idx_antigo, item) in enumerate(itens_com_idx, start=prefixo):
            self._lista_base[i] = item
        for i in range(prefixo + len(itens_com_idx), total):
            self._lista_base[i] = None
        self._projecao_suja = True

    def _reconstruir_botoes(self):
        self._botoes_ordenacao = []

        gap = 8
        largura_max = 128
        altura = max(30, self.rect.height - 10)
        x = self.rect.right + gap

        for indice, (rotulo, tipo, _fn) in enumerate(self._ordens):
            largura = min(largura_max, max(78, 20 + len(rotulo) * 8))

            if tipo == 'ordem':
                def _acao(_jogo, _botao, idx=indice):
                    self._aplicar_ordenacao(idx)
            else:
                def _acao(_jogo, _botao, idx=indice):
                    self._ordens[idx][2]()

            botao = Botao(
                pygame.Rect(x, self.rect.centery - altura // 2, largura, altura),
                rotulo,
                execute=_acao,
                style={'text_style': {'size': 18, 'outline': False, 'shadow': False}},
            )
            self._botoes_ordenacao.append(botao)
            x += largura + gap

    def configurar_rect(self, rect: pygame.Rect):
        novo_rect = pygame.Rect(rect)
        if novo_rect == self._rect_cache:
            return
        self.rect = novo_rect
        self._rect_cache = pygame.Rect(novo_rect)
        self._reconstruir_botoes()

    def _valor_nome(self, item):
        chave_cache = id(item)
        assinatura = (item.get('Nome'), item.get('nome'), item.get('Code'), item.get('code')) if isinstance(item, dict) else item
        cache = self._cache_nome_normalizado.get(chave_cache)
        if cache is not None and cache[0] == assinatura:
            return cache[1]

        try:
            valor = self._norm(self._acessor_nome(item))
        except Exception:
            valor = ''

        self._cache_nome_normalizado[chave_cache] = (assinatura, valor)
        return valor

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
        if not self._projecao_suja:
            return
        termo = self._norm(self.texto)
        prefixo = max(0, min(self._indices_fixos_imutaveis, len(self._lista_base)))
        fixos = list(range(prefixo))
        base = [(i, item) for i, item in enumerate(self._lista_base[prefixo:], start=prefixo) if item is not None]
        if termo:
            base = [(i, item) for i, item in base if termo in self._valor_nome(item)]

        self._projecao_indices = fixos + [indice for indice, _item in base]
        self._projecao_suja = False

    def lista_visivel(self):
        return list(self._projecao_indices)

    def contem_ponto_interativo(self, pos):
        if self.rect.collidepoint(pos):
            return True
        return any(botao.rect.collidepoint(pos) for botao in self._botoes_ordenacao)

    def render(self, tela, eventos, dt, jogo=None):
        texto_anterior = self.texto
        super().render(tela, eventos, dt)
        if self.texto != texto_anterior:
            self._projecao_suja = True
        for botao in self._botoes_ordenacao:
            botao.render(tela, eventos, dt, jogo)
