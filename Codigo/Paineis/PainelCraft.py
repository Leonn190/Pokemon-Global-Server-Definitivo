from __future__ import annotations

import copy
import unicodedata
import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto


class PainelCraft:
    def __init__(self, rect=None):
        self.rect = pygame.Rect(rect or (0, 0, 0, 0))
        self.CraftSlots = [None] * 9
        self._origens = [None] * 9
        self._painel = Painel(self.rect, cor_fundo=(18, 26, 44, 242), cor_borda=(66, 88, 136), borda=2, raio=16)
        estilo = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtTitulo = Texto('Craft', style={**estilo, 'size': 19, 'color': (236, 241, 255)})
        self.TxtSeta = Texto('→', style={**estilo, 'size': 28, 'color': (180, 194, 228), 'align': 'center'})
        self.PreviewReceita = None
        self.SlotPx = 68
        self.Gap = 12
        self.PaddingX = 24
        self.PaddingTop = 48
        self.RectSaida = pygame.Rect(0, 0, 0, 0)

    @staticmethod
    def _norm(texto):
        base = ''.join(
            c for c in unicodedata.normalize('NFKD', str(texto or '').lower())
            if not unicodedata.combining(c)
        )
        for ch in ('_', '-', "'", '.'):
            base = base.replace(ch, ' ')
        return ' '.join(base.split())

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._painel.rect = pygame.Rect(rect)

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
        self.RectSaida = pygame.Rect(self.rect.right - 96, self.rect.y + 102, self.SlotPx, self.SlotPx)
        return self.RectSaida

    def chave_item(self, item):
        if isinstance(item, dict):
            return self._norm(item.get('Nome') or item.get('nome') or item.get('Code') or item.get('code') or '')
        return self._norm(item)

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

    def set_preview(self, receita):
        self.PreviewReceita = receita

    def limpar_preview(self):
        self.PreviewReceita = None

    def colocar_no_slot(self, indice, item, origem=None):
        destino = self.CraftSlots[indice]
        if destino is None:
            self.CraftSlots[indice] = copy.deepcopy(item)
            self._origens[indice] = origem
            return None
        if self.pode_empilhar(item, destino):
            destino['quantidade'] = self.quantidade(destino) + self.quantidade(item)
            return None
        self.CraftSlots[indice] = copy.deepcopy(item)
        antiga_origem = self._origens[indice]
        self._origens[indice] = origem
        return destino, antiga_origem

    def retirar_do_slot(self, indice, quantidade=None):
        item = self.CraftSlots[indice]
        if item is None:
            return None
        if quantidade is None:
            self.CraftSlots[indice] = None
            origem = self._origens[indice]
            self._origens[indice] = None
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
        return retirado, origem

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

    def _colocar_no_inventario(self, container, item):
        if item is None:
            return True
        resto = copy.deepcopy(item)
        for atual in container.Itens:
            if atual is not None and container.pode_empilhar(resto, atual):
                atual['quantidade'] = container.quantidade(atual) + self.quantidade(resto)
                return True
        for i, atual in enumerate(container.Itens):
            if atual is None:
                container.Itens[i] = resto
                return True
        return False

    def devolver_para_inventario(self, container):
        for i, item in enumerate(self.CraftSlots):
            if item is None:
                self._origens[i] = None
                continue
            if self._colocar_no_inventario(container, item):
                self.CraftSlots[i] = None
                self._origens[i] = None

    def _retirar_um_do_inventario(self, container, chave):
        for i, item in enumerate(container.Itens):
            if item is None:
                continue
            if self._norm(item.get('Nome') or item.get('nome') or '') != chave:
                continue
            retirado = container.recolher_do_slot(i, quantidade=1)
            if retirado is not None:
                return retirado, ('inventario', i)
        return None, None

    def preencher_receita(self, receita, container, parcial=False):
        if receita is None or container is None:
            return False

        self.devolver_para_inventario(container)
        preenchido = False
        quantidades = {self._norm(chave): valor for chave, valor in container.quantidade_por_nome().items()}

        for i, esperado in enumerate(receita['grade']):
            self.CraftSlots[i] = None
            self._origens[i] = None
            if esperado is None:
                continue

            chave = self.chave_item(esperado)
            disponivel = quantidades.get(chave, 0)
            if disponivel <= 0:
                if parcial:
                    continue
                self.devolver_para_inventario(container)
                return False

            retirado, origem = self._retirar_um_do_inventario(container, chave)
            if retirado is None:
                if parcial:
                    continue
                self.devolver_para_inventario(container)
                return False

            self.CraftSlots[i] = retirado
            self._origens[i] = origem
            quantidades[chave] = disponivel - 1
            preenchido = True

        return preenchido

    def coletar_resultado(self, container, receitas):
        resultado, receita = self.resultado(receitas)
        if resultado is None:
            return None
        if not self._colocar_no_inventario(container, resultado):
            return None
        self.consumir_para_craft(receita)
        return resultado

    def desenhar(self, tela, receitas, highlight=None):
        self._painel.render(tela, [], 0)
        self.TxtTitulo.set_pos((self.rect.x + 18, self.rect.y + 12))
        self.TxtTitulo.draw(tela)

        preview = self.preview_dict() or {}
        for i in range(9):
            rect = self.slot_rect(i)
            destaque = highlight == ('craft', i)
            transparente = i in preview
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (76, 96, 140, 120 if transparente else 255), surf.get_rect(), border_radius=10)
            pygame.draw.rect(surf, (228, 239, 255) if destaque else (20, 26, 40), surf.get_rect(), 2, border_radius=10)
            tela.blit(surf, rect.topleft)
            item = self.CraftSlots[i]
            if item is not None:
                ItemInventario.desenhar_item_no_rect(tela, item, self.item_rect_no_slot(rect))
            elif transparente:
                ghost = pygame.Surface(rect.size, pygame.SRCALPHA)
                ItemInventario.desenhar_item_no_rect(ghost, preview[i], pygame.Rect(6, 6, rect.width - 12, rect.height - 12))
                ghost.set_alpha(105)
                tela.blit(ghost, rect.topleft)

        rect_saida = self.slot_saida_rect()
        self.TxtSeta.set_pos((rect_saida.x - 20, rect_saida.centery))
        self.TxtSeta.draw(tela)
        pygame.draw.rect(tela, (64, 78, 112), rect_saida, border_radius=10)
        pygame.draw.rect(tela, (228, 239, 255) if highlight == ('saida', 0) else (20, 26, 40), rect_saida, 2, border_radius=10)
        resultado, _ = self.resultado(receitas)
        if resultado is not None:
            ItemInventario.desenhar_item_no_rect(tela, resultado, self.item_rect_no_slot(rect_saida))
        elif self.PreviewReceita is not None:
            ghost = pygame.Surface(rect_saida.size, pygame.SRCALPHA)
            ItemInventario.desenhar_item_no_rect(ghost, self.PreviewReceita['saida'], pygame.Rect(6, 6, rect_saida.width - 12, rect_saida.height - 12))
            ghost.set_alpha(90)
            tela.blit(ghost, rect_saida.topleft)
