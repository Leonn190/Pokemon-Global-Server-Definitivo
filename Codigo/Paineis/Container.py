from __future__ import annotations

import copy
import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import PainelRolavel


class Container(PainelRolavel):
    def __init__(
        self,
        rect,
        itens,
        slots_total,
        colunas=8,
        linhas_visiveis=4,
        slot_px=66,
        gap=12,
        titulo=None,
        stackable=True,
        **kwargs,
    ):
        super().__init__(rect, area_real=(0, 0, rect[2], rect[3]), **kwargs)
        self.Itens = itens
        self.SlotsTotal = max(1, int(slots_total))
        self.Colunas = max(1, int(colunas))
        self.LinhasVisiveis = max(1, int(linhas_visiveis))
        self.SlotPx = max(24, int(slot_px))
        self.Gap = max(0, int(gap))
        self.Titulo = titulo
        self.Stackable = bool(stackable)
        self.Padding = 18

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self.atualizar_area_real()

    def _normalizar_tamanho(self):
        if len(self.Itens) < self.SlotsTotal:
            self.Itens.extend([None] * (self.SlotsTotal - len(self.Itens)))
        elif len(self.Itens) > self.SlotsTotal:
            del self.Itens[self.SlotsTotal:]

    def _linhas_totais(self):
        return max(1, (self.SlotsTotal + self.Colunas - 1) // self.Colunas)

    def altura_conteudo(self):
        linhas = self._linhas_totais()
        return self.Padding * 2 + linhas * self.SlotPx + max(0, linhas - 1) * self.Gap

    def atualizar_area_real(self):
        self.definir_area_real(self.rect.width, self.altura_conteudo())

    def chave_item(self, item):
        if not isinstance(item, dict):
            return str(item)
        return str(item.get('Code') or item.get('code') or item.get('Nome') or item.get('nome') or '')

    def quantidade(self, item):
        if not isinstance(item, dict):
            return 1 if item is not None else 0
        try:
            return max(0, int(item.get('quantidade', 1)))
        except (TypeError, ValueError):
            return 1

    def copiar_item(self, item):
        return copy.deepcopy(item) if isinstance(item, dict) else item

    def slot_local_pos(self, slot_id):
        col = slot_id % self.Colunas
        lin = slot_id // self.Colunas
        x = self.Padding + col * (self.SlotPx + self.Gap)
        y = self.Padding + lin * (self.SlotPx + self.Gap)
        return x, y

    def slot_rect(self, slot_id):
        x, y = self.slot_local_pos(slot_id)
        return pygame.Rect(
            self.rect.x + x - self.ScrollX,
            self.rect.y + y - self.ScrollY,
            self.SlotPx,
            self.SlotPx,
        )

    def item_rect_no_slot(self, rect_slot):
        margem = 6
        return pygame.Rect(rect_slot.x + margem, rect_slot.y + margem, rect_slot.width - margem * 2, rect_slot.height - margem * 2)

    def desenhar_slot(self, tela, rect, destaque=False, transparente=False):
        alpha = 120 if transparente else 255
        fundo = (76, 96, 140, alpha)
        borda = (228, 239, 255, alpha) if destaque else (20, 26, 40, alpha)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, fundo, surf.get_rect(), border_radius=10)
        pygame.draw.rect(surf, borda, surf.get_rect(), 2, border_radius=10)
        tela.blit(surf, rect.topleft)

    def indice_no_mouse(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos):
            return None
        for i in range(self.SlotsTotal):
            rect = self.slot_rect(i)
            if rect.collidepoint(mouse_pos) and self.rect.colliderect(rect):
                return i
        return None

    def item_no_mouse(self, mouse_pos):
        indice = self.indice_no_mouse(mouse_pos)
        if indice is None:
            return None, None
        return indice, self.Itens[indice]

    def pode_empilhar(self, item_a, item_b):
        return self.Stackable and isinstance(item_a, dict) and isinstance(item_b, dict) and self.chave_item(item_a) == self.chave_item(item_b)

    def recolher_do_slot(self, indice, quantidade=None):
        if indice is None or not (0 <= indice < self.SlotsTotal):
            return None
        item = self.Itens[indice]
        if item is None:
            return None
        if not self.Stackable or quantidade is None:
            self.Itens[indice] = None
            return self.copiar_item(item)

        qtd = self.quantidade(item)
        quantidade = max(1, min(qtd, int(quantidade)))
        retirado = self.copiar_item(item)
        retirado['quantidade'] = quantidade
        if quantidade >= qtd:
            self.Itens[indice] = None
        else:
            item['quantidade'] = qtd - quantidade
        return retirado

    def tentar_colocar_no_slot(self, indice, item, quantidade=None):
        if item is None or indice is None or not (0 <= indice < self.SlotsTotal):
            return item

        carga = self.copiar_item(item)
        if self.Stackable and quantidade is not None and isinstance(carga, dict):
            qtd_carga = max(1, min(self.quantidade(carga), int(quantidade)))
            carga['quantidade'] = qtd_carga
        else:
            qtd_carga = self.quantidade(carga)

        destino = self.Itens[indice]
        if destino is None:
            self.Itens[indice] = carga
            if self.Stackable and quantidade is not None and self.quantidade(item) > qtd_carga:
                resto = self.copiar_item(item)
                resto['quantidade'] = self.quantidade(item) - qtd_carga
                return resto
            return None

        if self.pode_empilhar(carga, destino):
            destino['quantidade'] = self.quantidade(destino) + self.quantidade(carga)
            if self.Stackable and quantidade is not None and self.quantidade(item) > qtd_carga:
                resto = self.copiar_item(item)
                resto['quantidade'] = self.quantidade(item) - qtd_carga
                return resto
            return None

        self.Itens[indice] = carga
        return destino

    def encontrar_primeiro_slot_vazio(self):
        for i in range(self.SlotsTotal):
            if self.Itens[i] is None:
                return i
        return None

    def devolver_para_origem_ou_vazio(self, indice_origem, item):
        if item is None:
            return None
        if indice_origem is not None and 0 <= indice_origem < self.SlotsTotal:
            resto = self.tentar_colocar_no_slot(indice_origem, item)
            if resto is None:
                return None
            item = resto
        indice_vazio = self.encontrar_primeiro_slot_vazio()
        if indice_vazio is not None:
            self.Itens[indice_vazio] = self.copiar_item(item)
            return None
        return item

    def agrupar_todos_no_item(self, item_base):
        if item_base is None or not self.Stackable:
            return item_base
        chave = self.chave_item(item_base)
        total = self.quantidade(item_base)
        for i, item in enumerate(self.Itens):
            if item is None:
                continue
            if self.chave_item(item) == chave:
                total += self.quantidade(item)
                self.Itens[i] = None
        novo = self.copiar_item(item_base)
        if isinstance(novo, dict):
            novo['quantidade'] = total
        return novo

    def agrupar_todos_no_slot(self, indice):
        if indice is None or not (0 <= indice < self.SlotsTotal):
            return
        item = self.Itens[indice]
        if item is None or not self.Stackable:
            return
        chave = self.chave_item(item)
        total = self.quantidade(item)
        for i, outro in enumerate(self.Itens):
            if i == indice or outro is None:
                continue
            if self.chave_item(outro) == chave:
                total += self.quantidade(outro)
                self.Itens[i] = None
        item['quantidade'] = total

    def quantidade_por_nome(self):
        mapa = {}
        for item in self.Itens:
            if item is None:
                continue
            chave = self.chave_item(item)
            mapa[chave] = mapa.get(chave, 0) + self.quantidade(item)
        return mapa

    def desenhar(self, tela, item_oculto=None, highlight=None, preview=None):
        self._normalizar_tamanho()
        self.atualizar_area_real()
        self.render(tela, [], 0)
        for i in range(self.SlotsTotal):
            rect_slot = self.slot_rect(i)
            if not self.rect.colliderect(rect_slot):
                continue
            self.desenhar_slot(tela, rect_slot, destaque=(highlight == i))
            item = self.Itens[i]
            if i == item_oculto or item is None:
                continue
            ItemInventario.desenhar_item_no_rect(tela, item, self.item_rect_no_slot(rect_slot))

        if preview:
            for indice, item_preview in preview.items():
                if item_preview is None:
                    continue
                rect_slot = self.slot_rect(indice)
                if not self.rect.colliderect(rect_slot):
                    continue
                self.desenhar_slot(tela, rect_slot, transparente=True)
                ghost = pygame.Surface(rect_slot.size, pygame.SRCALPHA)
                ItemInventario.desenhar_item_no_rect(ghost, item_preview, pygame.Rect(6, 6, rect_slot.width - 12, rect_slot.height - 12))
                ghost.set_alpha(110)
                tela.blit(ghost, rect_slot.topleft)
