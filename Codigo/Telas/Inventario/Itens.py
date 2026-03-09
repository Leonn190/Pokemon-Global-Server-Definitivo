from __future__ import annotations

import pygame

from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Prefabs.Arrastavel import Arrastavel
from Codigo.Prefabs.Painel import Painel, PainelRolavel
from Codigo.Paineis.FichaItem import FichaItem


class InventarioItens:
    def __init__(self, player):
        self.Player = player
        self.Inventario = player.Inventario
        self.Perfil = player.Perfil

        self.Colunas = 8
        self.SlotPx = 64
        self.Gap = 12
        self.LinhasVisiveis = 4

        self.CraftSlots = [None] * 9
        self.CraftOrigens = [None] * 9
        self.SaidaCraft = None

        self._montado = False
        self._arrastavel = Arrastavel()
        self._slot_hover = None
        self._hover_item = None
        self._estava_ativo = False
        self._ficha = FichaItem()
        self._painel_esquerda = None
        self._painel_ficha = None
        self._area_grid = pygame.Rect(0, 0, 0, 0)
        self._area_info = pygame.Rect(0, 0, 0, 0)
        self._area_craft = pygame.Rect(0, 0, 0, 0)
        self._slot_saida_rect = pygame.Rect(0, 0, 0, 0)

    def on_open(self):
        self._estava_ativo = True

    def on_close(self):
        self._devolver_itens_craft()
        self._arrastavel.cancelar()
        self._hover_item = None
        self._slot_hover = None
        self._estava_ativo = False

    def _capacidade_total(self):
        return max(1, int(getattr(self.Perfil, "NivelMochila", 1)) * 100)

    def _quantidade_total_itens(self):
        return sum(1 for item in self.Inventario.Itens if item is not None)

    def _garantir_slots(self):
        capacidade = self._capacidade_total()
        if hasattr(self.Inventario, "definir_limite_itens"):
            self.Inventario.definir_limite_itens(capacidade)
        else:
            self.Inventario.LimiteItens = capacidade
            if len(self.Inventario.Itens) < capacidade:
                self.Inventario.Itens.extend([None] * (capacidade - len(self.Inventario.Itens)))
            elif len(self.Inventario.Itens) > capacidade:
                self.Inventario.Itens = self.Inventario.Itens[:capacidade]

    def _reconstruir(self, area):
        margem = 14
        topo = 12
        largura_esquerda = min(690, int(area.width * 0.66))
        largura_direita = area.width - largura_esquerda - margem * 3

        self._area_grid = pygame.Rect(area.x + margem, area.y + topo, largura_esquerda, area.height - 138)
        self._area_info = pygame.Rect(area.x + margem, self._area_grid.bottom + 10, largura_esquerda, 52)
        self._area_craft = pygame.Rect(self._area_grid.right + margem, area.y + topo, largura_direita, 226)
        self._area_ficha = pygame.Rect(self._area_grid.right + margem, self._area_craft.bottom + 12, largura_direita, area.bottom - (self._area_craft.bottom + 12) - 12)

        self._painel_esquerda = PainelRolavel(
            self._area_grid,
            area_real=(0, 0, self._area_grid.width, self._area_grid.height),
            cor_fundo=(18, 26, 44, 242),
            cor_borda=(66, 88, 136),
            borda=2,
            raio=16,
        )
        self._painel_ficha = Painel(
            self._area_info,
            cor_fundo=(18, 26, 44, 242),
            cor_borda=(66, 88, 136),
            borda=2,
            raio=16,
        )
        self._montado = True

    def _total_linhas(self):
        return max(1, (len(self.Inventario.Itens) + self.Colunas - 1) // self.Colunas)

    def _slot_local_pos_inventario(self, slot_id: int):
        col = slot_id % self.Colunas
        lin = slot_id // self.Colunas
        x = 18 + col * (self.SlotPx + self.Gap)
        y = 18 + lin * (self.SlotPx + self.Gap)
        return x, y

    def _slot_rect_inventario(self, slot_id: int):
        x, y = self._slot_local_pos_inventario(slot_id)
        return pygame.Rect(
            self._painel_esquerda.rect.x + x - self._painel_esquerda.ScrollX,
            self._painel_esquerda.rect.y + y - self._painel_esquerda.ScrollY,
            self.SlotPx,
            self.SlotPx,
        )

    def _slot_rect_craft(self, slot_id: int):
        col = slot_id % 3
        lin = slot_id // 3
        base_x = self._area_craft.x + 22
        base_y = self._area_craft.y + 46
        return pygame.Rect(
            base_x + col * (self.SlotPx + 10),
            base_y + lin * (self.SlotPx + 10),
            self.SlotPx,
            self.SlotPx,
        )

    def _item_rect_no_slot(self, slot_rect):
        margem = 7
        return pygame.Rect(
            slot_rect.x + margem,
            slot_rect.y + margem,
            slot_rect.width - margem * 2,
            slot_rect.height - margem * 2,
        )

    def _desenhar_slot(self, tela, rect, destaque=False, saida=False):
        cor_fundo = (76, 96, 140) if not saida else (64, 78, 112)
        cor_borda = (20, 26, 40) if not destaque else (228, 239, 255)
        pygame.draw.rect(tela, cor_fundo, rect, border_radius=10)
        pygame.draw.rect(tela, cor_borda, rect, 2, border_radius=10)
        if destaque:
            brilho = rect.inflate(8, 8)
            pygame.draw.rect(tela, (120, 180, 255), brilho, 1, border_radius=13)

    def _chave_stack(self, item):
        if hasattr(self.Inventario, "_chave_stack"):
            return self.Inventario._chave_stack(item)
        if not isinstance(item, dict):
            return str(item)
        return str(item.get("Code") or item.get("code") or item.get("Nome") or item.get("nome") or "")

    def _origem_valida(self, origem):
        return isinstance(origem, tuple) and len(origem) == 2

    def _pegar_item_origem(self, origem):
        if not self._origem_valida(origem):
            return None
        grupo, indice = origem
        if grupo == "inventario" and 0 <= indice < len(self.Inventario.Itens):
            return self.Inventario.Itens[indice]
        if grupo == "craft" and 0 <= indice < len(self.CraftSlots):
            return self.CraftSlots[indice]
        return None

    def _setar_item_origem(self, origem, item):
        if not self._origem_valida(origem):
            return
        grupo, indice = origem
        if grupo == "inventario" and 0 <= indice < len(self.Inventario.Itens):
            self.Inventario.Itens[indice] = item
        elif grupo == "craft" and 0 <= indice < len(self.CraftSlots):
            self.CraftSlots[indice] = item
            if item is None:
                self.CraftOrigens[indice] = None

    def _detectar_alvo(self, mouse_pos):
        if self._slot_saida_rect.collidepoint(mouse_pos):
            return ("saida", 0)

        for i in range(len(self.CraftSlots)):
            if self._slot_rect_craft(i).collidepoint(mouse_pos):
                return ("craft", i)

        for i in range(len(self.Inventario.Itens)):
            rect = self._slot_rect_inventario(i)
            if rect.collidepoint(mouse_pos) and self._painel_esquerda.rect.colliderect(rect):
                return ("inventario", i)
        return None

    def _iniciar_arrasto(self, mouse_pos):
        if self._arrastavel.Ativo:
            return

        origem = self._detectar_alvo(mouse_pos)
        if origem is None or origem[0] == "saida":
            return

        item = self._pegar_item_origem(origem)
        if item is None:
            return

        rect_base = self._slot_rect_inventario(origem[1]) if origem[0] == "inventario" else self._slot_rect_craft(origem[1])
        rect_item = self._item_rect_no_slot(rect_base)
        self._arrastavel.iniciar(item=item, origem=origem, rect_item=rect_item, mouse_pos=mouse_pos)

    def _empilhar_se_der(self, item_a, item_b):
        if not (isinstance(item_a, dict) and isinstance(item_b, dict)):
            return False
        if self._chave_stack(item_a) != self._chave_stack(item_b):
            return False
        item_b["quantidade"] = int(max(1, item_b.get("quantidade", 1))) + int(max(1, item_a.get("quantidade", 1)))
        return True

    def _soltar_arrasto(self, mouse_pos):
        if not self._arrastavel.Ativo:
            return

        origem = self._arrastavel.Origem
        destino = self._detectar_alvo(mouse_pos)

        if destino is None or destino[0] == "saida" or destino == origem:
            self._arrastavel.cancelar()
            return

        item_origem = self._pegar_item_origem(origem)
        item_destino = self._pegar_item_origem(destino)
        if item_origem is None:
            self._arrastavel.cancelar()
            return

        origem_craft_retorno = None
        if origem[0] == "craft":
            origem_craft_retorno = self.CraftOrigens[origem[1]]

        if destino[0] == "craft":
            indice_craft = destino[1]
            origem_craft_antiga = self.CraftOrigens[indice_craft]

            if item_destino is None:
                self._setar_item_origem(origem, None)
                self.CraftSlots[indice_craft] = item_origem
                self.CraftOrigens[indice_craft] = origem[1] if origem[0] == "inventario" else origem_craft_retorno
            else:
                if self._empilhar_se_der(item_origem, item_destino):
                    self._setar_item_origem(origem, None)
                else:
                    self._setar_item_origem(origem, item_destino)
                    self.CraftSlots[indice_craft] = item_origem
                    self.CraftOrigens[indice_craft] = origem[1] if origem[0] == "inventario" else origem_craft_retorno
                    if origem[0] == "craft":
                        self.CraftOrigens[origem[1]] = origem_craft_antiga

            self._arrastavel.cancelar()
            return

        if destino[0] == "inventario":
            indice_inv = destino[1]
            if item_destino is None:
                self._setar_item_origem(origem, None)
                self.Inventario.Itens[indice_inv] = item_origem
            else:
                if self._empilhar_se_der(item_origem, item_destino):
                    self._setar_item_origem(origem, None)
                else:
                    self._setar_item_origem(origem, item_destino)
                    self.Inventario.Itens[indice_inv] = item_origem
                    if origem[0] == "craft":
                        self.CraftOrigens[origem[1]] = indice_inv
            self._arrastavel.cancelar()

    def _devolver_itens_craft(self):
        for i, item in enumerate(self.CraftSlots):
            if item is None:
                self.CraftOrigens[i] = None
                continue

            origem = self.CraftOrigens[i]
            colocado = False

            if origem is not None and 0 <= origem < len(self.Inventario.Itens):
                if self.Inventario.Itens[origem] is None:
                    self.Inventario.Itens[origem] = item
                    colocado = True
                elif self._empilhar_se_der(item, self.Inventario.Itens[origem]):
                    colocado = True

            if not colocado:
                for idx, atual in enumerate(self.Inventario.Itens):
                    if atual is None:
                        self.Inventario.Itens[idx] = item
                        colocado = True
                        break

            if not colocado:
                for atual in self.Inventario.Itens:
                    if atual is not None and self._empilhar_se_der(item, atual):
                        colocado = True
                        break

            self.CraftSlots[i] = None
            self.CraftOrigens[i] = None

    def _atualizar_hover(self, mouse_pos):
        self._slot_hover = self._detectar_alvo(mouse_pos)
        if self._slot_hover is None or self._slot_hover[0] == "saida" or self._arrastavel.Ativo:
            self._hover_item = None
            return
        self._hover_item = self._pegar_item_origem(self._slot_hover)

    def atualizar(self, eventos, dt, area, ativo=True):
        self._garantir_slots()

        if not self._montado:
            self._reconstruir(area)

        if not ativo:
            if self._estava_ativo:
                self.on_close()
            return

        if not self._estava_ativo:
            self.on_open()

        self._reconstruir(area)
        altura_real = 30 + self._total_linhas() * (self.SlotPx + self.Gap)
        self._painel_esquerda.rect = pygame.Rect(self._area_grid)
        self._painel_esquerda.definir_area_real(self._area_grid.width - 2, max(self._area_grid.height, altura_real))
        self._painel_esquerda._processar_scroll(eventos)

        mouse_pos = pygame.mouse.get_pos()
        self._atualizar_hover(mouse_pos)

        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self._iniciar_arrasto(evento.pos)
            elif evento.type == pygame.MOUSEMOTION and self._arrastavel.Ativo:
                self._arrastavel.atualizar(evento.pos)
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                self._soltar_arrasto(evento.pos)

    def _desenhar_area_craft(self, tela):
        pygame.draw.rect(tela, (18, 26, 44), self._area_craft, border_radius=16)
        pygame.draw.rect(tela, (66, 88, 136), self._area_craft, 2, border_radius=16)

        fonte_titulo = pygame.font.SysFont("arial", 22, bold=True)
        fonte_seta = pygame.font.SysFont("arial", 28, bold=True)
        titulo = fonte_titulo.render("Craft", True, (236, 241, 255))
        tela.blit(titulo, (self._area_craft.x + 18, self._area_craft.y + 12))

        for i, item in enumerate(self.CraftSlots):
            rect = self._slot_rect_craft(i)
            destaque = self._slot_hover == ("craft", i)
            self._desenhar_slot(tela, rect, destaque=destaque)
            if item is not None and not (self._arrastavel.Ativo and self._arrastavel.Origem == ("craft", i)):
                ItemInventario.desenhar_item_no_rect(tela, item, self._item_rect_no_slot(rect))

        self._slot_saida_rect = pygame.Rect(self._area_craft.right - 96, self._area_craft.y + 88, 64, 64)
        seta = fonte_seta.render("→", True, (180, 194, 228))
        tela.blit(seta, seta.get_rect(center=(self._slot_saida_rect.x - 22, self._slot_saida_rect.centery)))
        self._desenhar_slot(tela, self._slot_saida_rect, destaque=self._slot_hover == ("saida", 0), saida=True)

        if self.SaidaCraft is not None:
            ItemInventario.desenhar_item_no_rect(tela, self.SaidaCraft, self._item_rect_no_slot(self._slot_saida_rect))

        fonte_dica = pygame.font.SysFont("arial", 15)
        dica = fonte_dica.render("Itens aqui são temporários até fechar o inventário.", True, (165, 178, 208))
        tela.blit(dica, (self._area_craft.x + 18, self._area_craft.bottom - 24))

    def _desenhar_info_inventario(self, tela):
        self._painel_ficha.rect = pygame.Rect(self._area_info)
        self._painel_ficha.render(tela, [], 0)

        fonte = pygame.font.SysFont("arial", 20, bold=True)
        texto = f"{self._quantidade_total_itens()} / {self._capacidade_total()} slots"
        txt = fonte.render(texto, True, (239, 243, 255))
        tela.blit(txt, txt.get_rect(center=self._area_info.center))

    def renderizar(self, tela, area, eventos, dt, ativo=True):
        self.atualizar(eventos, dt, area, ativo=ativo)
        if not ativo:
            return

        self._painel_esquerda.render(tela, [], dt)

        for i in range(len(self.Inventario.Itens)):
            rect_slot = self._slot_rect_inventario(i)
            if not self._painel_esquerda.rect.colliderect(rect_slot):
                continue

            destaque = self._slot_hover == ("inventario", i)
            self._desenhar_slot(tela, rect_slot, destaque=destaque)
            item = self.Inventario.Itens[i]
            if item is None:
                continue
            if self._arrastavel.Ativo and self._arrastavel.Origem == ("inventario", i):
                continue
            ItemInventario.desenhar_item_no_rect(tela, item, self._item_rect_no_slot(rect_slot))

        self._desenhar_info_inventario(tela)
        self._desenhar_area_craft(tela)
        self._ficha.renderizar(tela, self._area_ficha, self._hover_item)

        if self._arrastavel.Ativo and self._arrastavel.Item is not None:
            ItemInventario.desenhar_item_no_rect(tela, self._arrastavel.Item, self._arrastavel.Rect)
