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
        renderizador_item=None,
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
        self.RenderizadorItem = renderizador_item or ItemInventario

        self._item_oculto_render = None
        self._highlight_render = None
        self._preview_render = None
        self._estado_visual = None
        self.BarraPesquisa = None
        self._topo_slots = 0
        self._mapeamento_visual_real = []
        self._buffer_linhas_geradas = 3

        self._normalizar_tamanho()
        self.atualizar_area_real()
        self.marcar_sujo()

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._atualizar_layout_barra()
        self.atualizar_area_real()
        self.marcar_sujo()

    def configurar_barra_pesquisa(self, barra_pesquisa, altura_topo=58):
        self.BarraPesquisa = barra_pesquisa
        self._topo_slots = max(0, int(altura_topo)) if barra_pesquisa is not None else 0
        self._atualizar_layout_barra()
        self.atualizar_area_real()
        self.marcar_sujo()

    def _atualizar_layout_barra(self):
        if self.BarraPesquisa is None:
            return
        altura = max(36, min(46, self._topo_slots - 12))
        largura = max(140, int(self.rect.width * 0.42))
        x = self.rect.x + 14
        y = self.rect.y + 10
        self.BarraPesquisa.configurar_rect(pygame.Rect(x, y, largura, altura))
        self.BarraPesquisa.definir_lista_base(self.Itens)

    def _normalizar_tamanho(self):
        if len(self.Itens) < self.SlotsTotal:
            self.Itens.extend([None] * (self.SlotsTotal - len(self.Itens)))
        elif len(self.Itens) > self.SlotsTotal:
            del self.Itens[self.SlotsTotal:]

    def _linhas_totais(self):
        return max(1, (self.SlotsTotal + self.Colunas - 1) // self.Colunas)

    def altura_conteudo(self):
        linhas = self._linhas_totais()
        return self.Padding * 2 + self._topo_slots + linhas * self.SlotPx + max(0, linhas - 1) * self.Gap

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

    def _mouse_global_para_local(self, mouse_pos):
        return (
            mouse_pos[0] - self.rect.x + self.ScrollX,
            mouse_pos[1] - self.rect.y + self.ScrollY,
        )

    def _rect_local_para_tela(self, rect_local):
        return pygame.Rect(
            self.rect.x + rect_local.x - self.ScrollX,
            self.rect.y + rect_local.y - self.ScrollY,
            rect_local.width,
            rect_local.height,
        )

    def slot_local_pos(self, slot_id):
        col = slot_id % self.Colunas
        lin = slot_id // self.Colunas
        grid_w = self.Colunas * self.SlotPx + max(0, self.Colunas - 1) * self.Gap
        x_base = max(self.Padding, (self.rect.width - grid_w) // 2)
        x = x_base + col * (self.SlotPx + self.Gap)
        y = self.Padding + self._topo_slots + lin * (self.SlotPx + self.Gap)
        return x, y

    def _indices_visiveis(self):
        if self.BarraPesquisa is None:
            return []
        if not self.BarraPesquisa.tem_projecao_ativa():
            return []
        self.BarraPesquisa.atualizar_projecao()
        return self.BarraPesquisa.lista_visivel()

    def _atualizar_mapeamento_visual(self):
        self._mapeamento_visual_real = [None] * self.SlotsTotal
        visiveis = self._indices_visiveis()
        if visiveis:
            limite = min(self.SlotsTotal, len(visiveis))
            for i in range(limite):
                self._mapeamento_visual_real[i] = visiveis[i]
            return
        for i in range(self.SlotsTotal):
            self._mapeamento_visual_real[i] = i

    def indice_real_por_visual(self, indice_visual, exigir_item=False):
        if indice_visual is None or not (0 <= int(indice_visual) < int(self.SlotsTotal)):
            return None
        indice_visual = int(indice_visual)
        if len(self._mapeamento_visual_real) != self.SlotsTotal:
            self._atualizar_mapeamento_visual()

        indice_real = self._mapeamento_visual_real[indice_visual]
        if indice_real is None:
            return None
        if exigir_item and self.Itens[indice_real] is None:
            return None
        return indice_real

    def item_por_slot_visual(self, indice_visual):
        indice_real = self.indice_real_por_visual(indice_visual, exigir_item=True)
        if indice_real is None:
            return None
        return self.Itens[indice_real]

    def projecao_ativa(self):
        return self.BarraPesquisa is not None and self.BarraPesquisa.tem_projecao_ativa()

    def permite_interacao_por_slot(self):
        return not self.projecao_ativa()

    def slot_rect_local(self, slot_id):
        x, y = self.slot_local_pos(slot_id)
        return pygame.Rect(x, y, self.SlotPx, self.SlotPx)

    def slot_rect(self, slot_id):
        return self._rect_local_para_tela(self.slot_rect_local(slot_id))

    def item_rect_no_slot(self, rect_slot):
        margem = 6
        return pygame.Rect(
            rect_slot.x + margem,
            rect_slot.y + margem,
            rect_slot.width - margem * 2,
            rect_slot.height - margem * 2,
        )

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
        if self.BarraPesquisa is not None and self.BarraPesquisa.contem_ponto_interativo(mouse_pos):
            return None

        mouse_local = self._mouse_global_para_local(mouse_pos)
        grid_w = self.Colunas * self.SlotPx + max(0, self.Colunas - 1) * self.Gap
        x_base = max(self.Padding, (self.rect.width - grid_w) // 2)
        y_base = self.Padding + self._topo_slots

        x_rel = mouse_local[0] - x_base
        y_rel = mouse_local[1] - y_base
        if x_rel < 0 or y_rel < 0:
            return None

        passo = self.SlotPx + self.Gap
        col = int(x_rel // passo)
        lin = int(y_rel // passo)
        if col < 0 or col >= self.Colunas or lin < 0:
            return None
        if (x_rel % passo) >= self.SlotPx or (y_rel % passo) >= self.SlotPx:
            return None

        indice = lin * self.Colunas + col
        if not (0 <= indice < self.SlotsTotal):
            return None
        return indice

    def item_no_mouse(self, mouse_pos):
        indice = self.indice_no_mouse(mouse_pos)
        if indice is None:
            return None, None
        indice_real = self.indice_real_por_visual(indice, exigir_item=True)
        if indice_real is None:
            return None, None
        return indice_real, self.Itens[indice_real]

    def pode_empilhar(self, item_a, item_b):
        return (
            self.Stackable
            and isinstance(item_a, dict)
            and isinstance(item_b, dict)
            and self.chave_item(item_a) == self.chave_item(item_b)
        )

    def recolher_do_slot(self, indice, quantidade=None):
        if indice is None or not (0 <= indice < self.SlotsTotal):
            return None

        item = self.Itens[indice]
        if item is None:
            return None

        if not self.Stackable or quantidade is None:
            self.Itens[indice] = None
            self.marcar_sujo()
            return self.copiar_item(item)

        qtd = self.quantidade(item)
        quantidade = max(1, min(qtd, int(quantidade)))
        retirado = self.copiar_item(item)
        retirado['quantidade'] = quantidade

        if quantidade >= qtd:
            self.Itens[indice] = None
        else:
            item['quantidade'] = qtd - quantidade

        self.marcar_sujo()
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
            self.marcar_sujo()

            if self.Stackable and quantidade is not None and self.quantidade(item) > qtd_carga:
                resto = self.copiar_item(item)
                resto['quantidade'] = self.quantidade(item) - qtd_carga
                return resto
            return None

        if self.pode_empilhar(carga, destino):
            destino['quantidade'] = self.quantidade(destino) + self.quantidade(carga)
            self.marcar_sujo()

            if self.Stackable and quantidade is not None and self.quantidade(item) > qtd_carga:
                resto = self.copiar_item(item)
                resto['quantidade'] = self.quantidade(item) - qtd_carga
                return resto
            return None

        self.Itens[indice] = carga
        self.marcar_sujo()
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
            self.marcar_sujo()
            return None

        return item

    def restaurar_item_no_slot_origem(self, indice_origem, item):
        if item is None:
            return None

        resto = self.devolver_para_origem_ou_vazio(indice_origem, item)
        if resto is None:
            return None

        if indice_origem is None or not (0 <= int(indice_origem) < int(self.SlotsTotal)):
            return resto

        origem = int(indice_origem)
        atual_origem = self.Itens[origem]
        if atual_origem is None:
            self.Itens[origem] = self.copiar_item(resto)
            self.marcar_sujo()
            return None

        if self.pode_empilhar(resto, atual_origem):
            atual_origem['quantidade'] = self.quantidade(atual_origem) + self.quantidade(resto)
            self.marcar_sujo()
            return None

        indice_vazio = self.encontrar_primeiro_slot_vazio()
        if indice_vazio is None:
            return resto

        self.Itens[indice_vazio] = self.copiar_item(atual_origem)
        self.Itens[origem] = self.copiar_item(resto)
        self.marcar_sujo()
        return None

    def agrupar_todos_no_item(self, item_base):
        if item_base is None or not self.Stackable:
            return item_base

        chave = self.chave_item(item_base)
        total = self.quantidade(item_base)
        alterou = False

        for i, item in enumerate(self.Itens):
            if item is None:
                continue
            if self.chave_item(item) == chave:
                total += self.quantidade(item)
                self.Itens[i] = None
                alterou = True

        novo = self.copiar_item(item_base)
        if isinstance(novo, dict):
            novo['quantidade'] = total

        if alterou:
            self.marcar_sujo()

        return novo

    def agrupar_todos_no_slot(self, indice):
        if indice is None or not (0 <= indice < self.SlotsTotal):
            return

        item = self.Itens[indice]
        if item is None or not self.Stackable:
            return

        chave = self.chave_item(item)
        total = self.quantidade(item)
        alterou = False

        for i, outro in enumerate(self.Itens):
            if i == indice or outro is None:
                continue
            if self.chave_item(outro) == chave:
                total += self.quantidade(outro)
                self.Itens[i] = None
                alterou = True

        item['quantidade'] = total

        if alterou:
            self.marcar_sujo()

    def quantidade_por_nome(self):
        mapa = {}
        for item in self.Itens:
            if item is None:
                continue
            chave = self.chave_item(item)
            mapa[chave] = mapa.get(chave, 0) + self.quantidade(item)
        return mapa

    def _desenhar_item(self, tela, item, rect):
        self.RenderizadorItem.desenhar_item_no_rect(tela, item, rect)

    def _assinatura_preview(self, preview):
        if not preview:
            return None

        assinatura = []
        for indice in sorted(preview.keys()):
            item = preview[indice]
            if item is None:
                assinatura.append((indice, None, 0))
            else:
                assinatura.append((indice, self.chave_item(item), self.quantidade(item)))
        return tuple(assinatura)

    def _assinatura_visual(self, item_oculto, highlight, preview):
        return (item_oculto, highlight, self._assinatura_preview(preview))

    def _intervalo_slots_gerados(self):
        linhas_totais = self._linhas_totais()
        passo = self.SlotPx + self.Gap
        if passo <= 0:
            return 0, self.SlotsTotal

        topo_grid = self.Padding + self._topo_slots
        y_inicio_visivel = self.ScrollY - topo_grid
        y_fim_visivel = self.ScrollY + self.rect.height - topo_grid

        lin_inicio = max(0, y_inicio_visivel // passo)
        lin_fim = min(linhas_totais - 1, y_fim_visivel // passo)

        lin_inicio = max(0, int(lin_inicio) - self._buffer_linhas_geradas)
        lin_fim = min(linhas_totais - 1, int(lin_fim) + self._buffer_linhas_geradas)

        slot_inicio = max(0, lin_inicio * self.Colunas)
        slot_fim = min(self.SlotsTotal, (lin_fim + 1) * self.Colunas)
        return slot_inicio, slot_fim

    def draw(self, tela):
        tela.fill((0, 0, 0, 0))
        if hasattr(self, 'CorFundo'):
            tela.fill(self.CorFundo)

        self._normalizar_tamanho()

        self._atualizar_mapeamento_visual()

        item_oculto = self._item_oculto_render
        highlight = self._highlight_render
        preview = self._preview_render or {}
        slot_inicio, slot_fim = self._intervalo_slots_gerados()

        for i in range(slot_inicio, slot_fim):
            rect_slot = self.slot_rect_local(i)
            self.desenhar_slot(tela, rect_slot, destaque=(highlight == i))

            indice_real = self._mapeamento_visual_real[i] if i < len(self._mapeamento_visual_real) else i
            item = self.Itens[indice_real] if indice_real is not None and 0 <= indice_real < len(self.Itens) else None
            if i == item_oculto or item is None:
                continue

            self._desenhar_item(tela, item, self.item_rect_no_slot(rect_slot))

        for indice, item_preview in preview.items():
            if item_preview is None:
                continue
            if not (slot_inicio <= indice < slot_fim):
                continue

            rect_slot = self.slot_rect_local(indice)
            self.desenhar_slot(tela, rect_slot, transparente=True)

            ghost = pygame.Surface(rect_slot.size, pygame.SRCALPHA)
            self.RenderizadorItem.desenhar_item_no_rect(
                ghost,
                item_preview,
                pygame.Rect(6, 6, rect_slot.width - 12, rect_slot.height - 12),
            )
            ghost.set_alpha(110)
            tela.blit(ghost, rect_slot.topleft)

    def desenhar(self, tela, item_oculto=None, highlight=None, preview=None, eventos=None, dt=0, jogo=None):
        estado_visual = self._assinatura_visual(item_oculto, highlight, preview)

        if estado_visual != self._estado_visual:
            self._item_oculto_render = item_oculto
            self._highlight_render = highlight
            self._preview_render = preview
            self._estado_visual = estado_visual
            self.marcar_sujo()

        eventos_render = eventos or []
        self.render(tela, eventos_render, dt, jogo=jogo)
        if self.BarraPesquisa is not None:
            self.BarraPesquisa.render(tela, eventos_render, dt, jogo=jogo)
