from __future__ import annotations

import copy
import csv
import unicodedata
from pathlib import Path

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto


class PainelCraft:
    _itens_cache = None
    _instancia_ativa = None

    def __init__(self, rect=None):
        self.rect = pygame.Rect(rect or (0, 0, 0, 0))
        self.CraftSlots = [None] * 9
        self._origens = [None] * 9
        self._painel = Painel(self.rect, cor_fundo=(18, 26, 44, 242), cor_borda=(66, 88, 136), borda=2, raio=16)
        self._painel_pai = None
        estilo = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtTitulo = Texto('Craft', style={**estilo, 'size': 19, 'color': (236, 241, 255)})
        self.TxtSeta = Texto('→', style={**estilo, 'size': 28, 'color': (180, 194, 228), 'align': 'center'})
        self.PreviewReceita = None
        self._receitas_cache = []
        self._highlight_cache = None
        self.SlotPx = 68
        self.Gap = 12
        self.PaddingX = 24
        self.PaddingTop = 48
        self.RectSaida = pygame.Rect(0, 0, 0, 0)
        PainelCraft._instancia_ativa = self

    @classmethod
    def instancia_ativa(cls):
        return cls._instancia_ativa

    def vincular_painel_pai(self, painel):
        self._painel_pai = painel
        return self

    def _marcar_sujo(self):
        if hasattr(self._painel_pai, 'marcar_sujo'):
            self._painel_pai.marcar_sujo()

    @staticmethod
    def _norm(texto):
        base = ''.join(c for c in unicodedata.normalize('NFKD', str(texto or '').lower()) if not unicodedata.combining(c))
        for ch in ('_', '-', "'", '.'):
            base = base.replace(ch, ' ')
        return ' '.join(base.split())

    @classmethod
    def _caminho_itens_csv(cls):
        caminhos = [
            Path('Dados') / 'Global server - Itens.csv',
            Path('Global server - Itens.csv'),
            Path(__file__).resolve().parents[3] / 'Dados' / 'Global server - Itens.csv',
            Path(__file__).resolve().parents[3] / 'Global server - Itens.csv',
        ]
        return next((p for p in caminhos if p.exists()), None)

    @classmethod
    def _carregar_itens_csv(cls):
        if cls._itens_cache is not None:
            return cls._itens_cache
        mapa = {}
        caminho = cls._caminho_itens_csv()
        if caminho is None:
            cls._itens_cache = mapa
            return mapa
        try:
            with caminho.open('r', encoding='utf-8-sig', newline='') as arquivo:
                for linha in csv.DictReader(arquivo):
                    dado = dict(linha)
                    nome = str(dado.get('Nome') or '').strip()
                    code = str(dado.get('Code') or '').strip()
                    if nome:
                        mapa[('nome', cls._norm(nome))] = dado
                    if code:
                        mapa[('code', cls._norm(code))] = dado
        except OSError:
            pass
        cls._itens_cache = mapa
        return mapa

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._painel.rect = pygame.Rect(rect)
        PainelCraft._instancia_ativa = self
        self._marcar_sujo()

    def slot_rect(self, indice):
        col = indice % 3
        lin = indice // 3
        return pygame.Rect(
            self.rect.x + self.PaddingX + col * (self.SlotPx + self.Gap),
            self.rect.y + self.PaddingTop + lin * (self.SlotPx + self.Gap),
            self.SlotPx,
            self.SlotPx,
        )

    def item_rect_no_slot(self, rect):
        return pygame.Rect(rect.x + 6, rect.y + 6, rect.width - 12, rect.height - 12)

    def slot_saida_rect(self):
        centro_y = self.slot_rect(4).centery
        self.RectSaida = pygame.Rect(self.rect.right - 96, centro_y - self.SlotPx // 2, self.SlotPx, self.SlotPx)
        return self.RectSaida

    def _nome_item(self, item):
        if not isinstance(item, dict):
            return self._norm(item)
        nome = str(item.get('Nome') or item.get('nome') or '').strip()
        if nome:
            return self._norm(nome)
        code = str(item.get('Code') or item.get('code') or '').strip()
        if code:
            base = self._carregar_itens_csv()
            dado = base.get(('code', self._norm(code)))
            if dado:
                return self._norm(dado.get('Nome'))
            return self._norm(code)
        return ''

    def chave_item(self, item):
        return self._nome_item(item)

    def quantidade(self, item):
        if not isinstance(item, dict):
            return 1 if item is not None else 0
        try:
            return max(0, int(item.get('quantidade', 1)))
        except (TypeError, ValueError):
            return 1

    def pode_empilhar(self, a, b):
        return isinstance(a, dict) and isinstance(b, dict) and self.chave_item(a) == self.chave_item(b)

    def indice_no_mouse(self, mouse_pos):
        for i in range(9):
            if self.slot_rect(i).collidepoint(mouse_pos):
                return i
        return None

    def alvo_no_mouse(self, mouse_pos):
        indice = self.indice_no_mouse(mouse_pos)
        if indice is not None:
            return ('craft', indice)
        if self.slot_saida_rect().collidepoint(mouse_pos):
            return ('saida', 0)
        return None

    def preview_dict(self):
        if self.PreviewReceita is None:
            return None
        return {i: item for i, item in enumerate(self.PreviewReceita['grade']) if item is not None and self.CraftSlots[i] is None}

    def preview_saida(self):
        if self.PreviewReceita is None:
            return None
        return self.PreviewReceita.get('saida')

    def set_preview(self, receita):
        self.PreviewReceita = receita
        self._marcar_sujo()

    def limpar_preview(self):
        self.PreviewReceita = None
        self._marcar_sujo()

    def colocar_no_slot(self, indice, item, origem=None):
        destino = self.CraftSlots[indice]
        if destino is None:
            self.CraftSlots[indice] = item
            self._origens[indice] = origem
            self._marcar_sujo()
            return None
        if self.pode_empilhar(item, destino):
            destino['quantidade'] = self.quantidade(destino) + self.quantidade(item)
            self._marcar_sujo()
            return None
        self.CraftSlots[indice] = item
        antiga_origem = self._origens[indice]
        self._origens[indice] = origem
        self._marcar_sujo()
        return destino, antiga_origem

    def retirar_do_slot(self, indice, quantidade=None):
        item = self.CraftSlots[indice]
        if item is None:
            return None
        if quantidade is None:
            self.CraftSlots[indice] = None
            origem = self._origens[indice]
            self._origens[indice] = None
            self._marcar_sujo()
            return copy.deepcopy(item), origem
        qtd = self.quantidade(item)
        quantidade = max(1, min(qtd, int(quantidade)))
        retirado = copy.deepcopy(item)
        retirado['quantidade'] = quantidade
        origem = self._origens[indice]
        if quantidade >= qtd:
            self.CraftSlots[indice] = None
            self._origens[indice] = None
        else:
            item['quantidade'] = qtd - quantidade
        self._marcar_sujo()
        return retirado, origem

    def _retirar_um_do_inventario(self, container, chave_desejada):
        if container is None:
            return None, None
        for idx, item in enumerate(getattr(container, 'Itens', [])):
            if item is None or self.chave_item(item) != chave_desejada:
                continue
            retirado = container.recolher_do_slot(idx, quantidade=1)
            if retirado is not None:
                return retirado, idx
        return None, None

    def preencher_receita(self, receita, container, estado='verde', mover_callback=None):
        if receita is None or estado == 'vermelho' or container is None:
            return False
        colocou_algo = False
        reservas = {}
        for idx, item in enumerate(getattr(container, 'Itens', [])):
            chave = self.chave_item(item)
            if item is None or not chave:
                continue
            reservas.setdefault(chave, []).append({
                'indice': idx,
                'quantidade': self.quantidade(item),
            })

        def _consumir_reserva(chave):
            pilha = reservas.get(chave) or []
            while pilha:
                topo = pilha[0]
                if topo['quantidade'] <= 0:
                    pilha.pop(0)
                    continue
                retirado = container.recolher_do_slot(topo['indice'], quantidade=1)
                if retirado is None:
                    pilha.pop(0)
                    continue
                topo['quantidade'] -= 1
                if topo['quantidade'] <= 0:
                    pilha.pop(0)
                return retirado, topo['indice']
            return None, None

        for i, esperado in enumerate(receita.get('grade', [])):
            if esperado is None:
                continue
            atual = self.CraftSlots[i]
            chave_esperada = self.chave_item(esperado)
            if atual is not None and self.chave_item(atual) != chave_esperada:
                continue
            retirado, origem = _consumir_reserva(self.chave_item(esperado))
            if retirado is None:
                continue
            if atual is None:
                self.CraftSlots[i] = retirado
                self._origens[i] = origem
            else:
                atual['quantidade'] = self.quantidade(atual) + self.quantidade(retirado)
            if callable(mover_callback):
                mover_callback(retirado, origem, i)
            colocou_algo = True
        self._marcar_sujo()
        return colocou_algo

    def resultado(self, receitas):
        for receita in receitas:
            ok = True
            for i, esperado in enumerate(receita['grade']):
                atual = self.CraftSlots[i]
                if esperado is None and atual is None:
                    continue
                if esperado is None or atual is None:
                    ok = False
                    break
                if self.chave_item(esperado) != self.chave_item(atual):
                    ok = False
                    break
            if ok:
                return copy.deepcopy(receita['saida']), receita
        return None, None

    def consumir_para_craft(self, receita):
        if receita is None:
            return
        for i, esperado in enumerate(receita['grade']):
            if esperado is None or self.CraftSlots[i] is None:
                continue
            qtd = self.quantidade(self.CraftSlots[i])
            if qtd <= 1:
                self.CraftSlots[i] = None
                self._origens[i] = None
            else:
                self.CraftSlots[i]['quantidade'] = qtd - 1
        self._marcar_sujo()

    def devolver_para_inventario(self, container):
        houve_mudanca = False
        for i, item in enumerate(self.CraftSlots):
            if item is None:
                self._origens[i] = None
                continue
            origem = self._origens[i]
            resto = container.devolver_para_origem_ou_vazio(origem, item) if hasattr(container, 'devolver_para_origem_ou_vazio') else None
            if resto is None:
                self.CraftSlots[i] = None
                self._origens[i] = None
                houve_mudanca = True
                continue
            if origem is not None:
                resto = container.tentar_colocar_no_slot(origem, resto)
            if resto is not None:
                for j in range(len(getattr(container, 'Itens', []))):
                    resto = container.tentar_colocar_no_slot(j, resto)
                    if resto is None:
                        break
            if resto is None:
                self.CraftSlots[i] = None
                self._origens[i] = None
                houve_mudanca = True
        if houve_mudanca:
            self._marcar_sujo()

    def desenhar(self, tela, receitas=None, highlight=None):
        if receitas is None:
            receitas = self._receitas_cache
        else:
            self._receitas_cache = receitas

        if highlight is None:
            highlight = self._highlight_cache
        else:
            self._highlight_cache = highlight

        self._painel.render(tela, [], 0)
        self.TxtTitulo.set_pos((self.rect.x + 18, self.rect.y + 12))
        self.TxtTitulo.draw(tela)

        for i in range(9):
            rect = self.slot_rect(i)
            destaque = highlight == ('craft', i)
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (76, 96, 140, 255), surf.get_rect(), border_radius=10)
            pygame.draw.rect(surf, (228, 239, 255) if destaque else (20, 26, 40), surf.get_rect(), 2, border_radius=10)
            tela.blit(surf, rect.topleft)
            item = self.CraftSlots[i]
            if item is not None:
                ItemInventario.desenhar_item_no_rect(tela, item, self.item_rect_no_slot(rect))

        rect_saida = self.slot_saida_rect()
        self.TxtSeta.set_pos((rect_saida.x - 20, rect_saida.centery))
        self.TxtSeta.draw(tela)
        pygame.draw.rect(tela, (64, 78, 112), rect_saida, border_radius=10)
        pygame.draw.rect(tela, (228, 239, 255) if highlight == ('saida', 0) else (20, 26, 40), rect_saida, 2, border_radius=10)
        resultado, _ = self.resultado(receitas)
        if resultado is not None:
            ItemInventario.desenhar_item_no_rect(tela, resultado, self.item_rect_no_slot(rect_saida))
