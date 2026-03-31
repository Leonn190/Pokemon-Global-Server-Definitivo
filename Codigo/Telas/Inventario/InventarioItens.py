from __future__ import annotations

import copy
import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Paineis.Container import Container
from Codigo.Paineis.FichaItem import FichaItem
from Codigo.Paineis.PainelCraft import PainelCraft
from Codigo.Paineis.PainelReceitas import PainelReceitas
from Codigo.Prefabs.Arrastavel import Arrastavel
from Codigo.Prefabs.BarraPesquisa import BarraPesquisa
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto


class InventarioItens:
    def __init__(self, ator):
        self.Ator = ator
        self.Inventario = ator.Inventario
        self.Perfil = ator.Perfil

        self._container = None
        self._painel_craft = None
        self._painel_receitas = None
        self._ficha = FichaItem()
        self._arrastavel = Arrastavel()
        self._item_hover = None
        self._ultimo_clique = {'tempo': 0, 'slot': None}
        self._estava_ativo = False
        self._layout_montado = False

        self._area_grid = pygame.Rect(0, 0, 0, 0)
        self._area_info = pygame.Rect(0, 0, 0, 0)
        self._area_craft = pygame.Rect(0, 0, 0, 0)
        self._area_receitas = pygame.Rect(0, 0, 0, 0)
        self._area_ficha = pygame.Rect(0, 0, 0, 0)
        self._area_total = pygame.Rect(0, 0, 0, 0)

        estilo = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtTotal = Texto('', style={**estilo, 'size': 23, 'color': (239, 243, 255), 'align': 'center'})
        self._painel_info = Painel((0, 0, 0, 0), cor_fundo=(18, 26, 44, 242), cor_borda=(66, 88, 136), borda=2, raio=16)
        self._barra_pesquisa = None

    def on_open(self):
        self._estava_ativo = True

    def on_close(self):
        if self._painel_craft is not None and self._container is not None:
            self._painel_craft.devolver_para_inventario(self._container)
        self._arrastavel.cancelar()
        self._item_hover = None
        if self._barra_pesquisa is not None:
            self._barra_pesquisa.resetar_filtro()
        self._estava_ativo = False

    def bloqueia_toggle_inventario(self):
        return self._barra_pesquisa is not None and self._barra_pesquisa.esta_editando()

    def _processar_atalho_enter_pesquisa(self, eventos):
        if self._barra_pesquisa is None:
            return
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._barra_pesquisa.selecionada = not self._barra_pesquisa.selecionada
                break

    def _capacidade_total(self):
        return max(1, int(getattr(self.Perfil, 'NivelMochila', 1)) * 100)

    def _limite_slots(self):
        return max(1, int(getattr(self.Perfil, 'LimiteSlotsInventario', 32)))

    def _quantidade_total_itens(self):
        total = 0
        for item in self.Inventario.Itens:
            if isinstance(item, dict):
                total += max(1, int(item.get('quantidade', 1)))
            elif item is not None:
                total += 1
        return total

    def _garantir_slots(self):
        capacidade = self._capacidade_total()
        slots = self._limite_slots()
        if hasattr(self.Inventario, 'definir_limite_itens'):
            self.Inventario.definir_limite_itens(capacidade)
            self.Inventario.definir_limite_slots(slots)
        else:
            self.Inventario.LimiteItens = capacidade
            self.Inventario.LimiteSlots = slots
            if len(self.Inventario.Itens) < slots:
                self.Inventario.Itens.extend([None] * (slots - len(self.Inventario.Itens)))
            elif len(self.Inventario.Itens) > slots:
                self.Inventario.Itens = self.Inventario.Itens[:slots]

    def _reconstruir(self, area):
        self._area_total = pygame.Rect(area)
        margem = 14
        topo = 10
        largura_esquerda = min(int(area.width * 0.64), 760)
        largura_direita = area.width - largura_esquerda - margem * 3

        self._area_grid = pygame.Rect(area.x + margem, area.y + topo, largura_esquerda, area.height - 110)
        self._area_info = pygame.Rect(area.x + margem, self._area_grid.bottom + 16, largura_esquerda, 65)
        self._area_craft = pygame.Rect(self._area_grid.right + margem, area.y + topo, largura_direita, 290)
        self._area_receitas = pygame.Rect(self._area_grid.right + margem, self._area_craft.bottom + 14, largura_direita, 173)
        self._area_ficha = pygame.Rect(self._area_grid.right + margem, self._area_receitas.bottom + 18, largura_direita, 135)

        if self._container is None:
            self._container = Container(
                self._area_grid,
                self.Inventario.Itens,
                slots_total=self._limite_slots(),
                colunas=8,
                linhas_visiveis=4,
                slot_px=68,
                gap=12,
                cor_fundo=(18, 26, 44, 242),
                cor_borda=(66, 88, 136),
                borda=2,
                raio=16,
                stackable=True,
            )
            self._barra_pesquisa = BarraPesquisa(pygame.Rect(0, 0, 10, 10), placeholder='Buscar item...')
            self._barra_pesquisa.definir_prefixo_imutavel(8)
            self._barra_pesquisa.definir_acessor_nome(ItemInventario.nome_item)
            self._barra_pesquisa.definir_ordenacoes([
                ('Alfabética', ItemInventario.nome_item),
                ('Raridade', ItemInventario.raridade_item),
                ('Estilo', ItemInventario.estilo_item),
            ])
            self._container.configurar_barra_pesquisa(self._barra_pesquisa)
            self._container.configurar_slots_especiais(8)
        else:
            self._container.Itens = self.Inventario.Itens
            self._container.SlotsTotal = self._limite_slots()
            self._container.SlotPx = 68
            self._container.configurar_rect(self._area_grid)
            self._container.configurar_barra_pesquisa(self._barra_pesquisa)
            self._container.configurar_slots_especiais(8)

        if self._painel_craft is None:
            self._painel_craft = PainelCraft(self._area_craft)
        else:
            self._painel_craft.configurar_rect(self._area_craft)

        if self._painel_receitas is None:
            self._painel_receitas = PainelReceitas(self._area_receitas)
        else:
            self._painel_receitas.configurar_rect(self._area_receitas)

        self._painel_info.rect = pygame.Rect(self._area_info)
        self._layout_montado = True

    def _item_ativo_ficha(self):
        if self._arrastavel.Ativo and self._arrastavel.Item is not None:
            return self._arrastavel.Item
        return self._item_hover

    def _alvo_no_mouse(self, mouse_pos):
        alvo_craft = self._painel_craft.alvo_no_mouse(mouse_pos)
        if alvo_craft is not None:
            return alvo_craft
        indice = self._container.indice_no_mouse(mouse_pos)
        if indice is not None:
            return ('inventario', indice)
        return None

    def _item_do_alvo(self, alvo):
        if alvo is None:
            return None
        grupo, indice = alvo
        if grupo == 'inventario':
            return self._container.item_por_slot_visual(indice)
        if grupo == 'craft':
            return self._painel_craft.CraftSlots[indice]
        if grupo == 'saida':
            return self._painel_craft.resultado(self._painel_receitas.Receitas)[0]
        return None

    def _quantidade(self, item):
        return self._container.quantidade(item)

    def _chave(self, item):
        return self._container.chave_item(item)

    def _click_duplo(self, alvo, agora):
        if alvo is None or alvo[0] != 'inventario':
            self._ultimo_clique = {'tempo': agora, 'slot': None}
            return False
        anterior = self._ultimo_clique
        self._ultimo_clique = {'tempo': agora, 'slot': alvo[1]}
        return anterior['slot'] == alvo[1] and agora - anterior['tempo'] <= 420

    def _iniciar_arrasto(self, alvo, mouse_pos, botao):
        item = self._item_do_alvo(alvo)
        if item is None or alvo is None or alvo[0] == 'saida':
            return
        qtd = None if botao == 1 else max(1, self._quantidade(item) // 2)
        if alvo[0] == 'inventario':
            indice_real = self._container.indice_real_por_visual(alvo[1], exigir_item=True)
            if indice_real is None:
                return
            item_pego = self._container.recolher_do_slot(indice_real, quantidade=qtd)
            rect_base = self._container.slot_rect(alvo[1])
            origem_aux = indice_real
        else:
            item_pego, origem_aux = self._painel_craft.retirar_do_slot(alvo[1], quantidade=qtd)
            rect_base = self._painel_craft.slot_rect(alvo[1])
        if item_pego is None:
            return
        origem = (alvo[0], alvo[1], origem_aux)
        self._arrastavel.iniciar(item_pego, origem, self._painel_craft.item_rect_no_slot(rect_base) if alvo[0] == 'craft' else self._container.item_rect_no_slot(rect_base), mouse_pos, botao=botao)
        if botao == 3:
            self._arrastavel.ativar_distribuidor()
        self._item_hover = item_pego

    def _retornar_para_origem(self):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return
        grupo, indice, origem_aux = self._arrastavel.Origem
        item = copy.deepcopy(self._arrastavel.Item)
        if grupo == 'inventario':
            rect = self._container.item_rect_no_slot(self._container.slot_rect(indice))
        else:
            rect = self._painel_craft.item_rect_no_slot(self._painel_craft.slot_rect(indice))

        def _finalizar():
            if grupo == 'inventario':
                resto = self._container.restaurar_item_no_slot_origem(origem_aux, item)
                if resto is not None:
                    self._container.devolver_para_origem_ou_vazio(origem_aux, resto)
            else:
                self._painel_craft.restaurar_no_slot_origem(indice, item, origem=origem_aux, container=self._container)
            self._arrastavel.cancelar()
        self._arrastavel.definir_pos_alvo(rect.topleft, ao_final=_finalizar)

    def _dropar_fora(self, quantidade=None):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return
        item = copy.deepcopy(self._arrastavel.Item)
        if quantidade is not None and isinstance(item, dict):
            quantidade = max(1, min(self._quantidade(item), int(quantidade)))
            item['quantidade'] = quantidade
        controle = getattr(self.Ator, 'Controle', None)
        if controle is not None:
            controle._acao_drop_item_mundo_pendente = {
                'item': item,
                'origem': tuple(getattr(self.Ator, 'Posicao', (0, 0))),
            }
        if quantidade is None or self._quantidade(self._arrastavel.Item) <= quantidade:
            self._arrastavel.cancelar()
            return
        self._arrastavel.Item['quantidade'] = self._quantidade(self._arrastavel.Item) - quantidade
        self._item_hover = self._arrastavel.Item

    def tratar_clique_fora(self, evento):
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button not in (1, 3):
            return False
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return False
        if evento.button == 1:
            self._dropar_fora()
        else:
            self._dropar_fora(quantidade=1)
        return True

    def _soltar_no_alvo(self, alvo, botao):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return
        item = self._arrastavel.Item
        grupo_origem, indice_origem, origem_aux = self._arrastavel.Origem

        if botao == 3:
            parte = copy.deepcopy(item)
            parte['quantidade'] = 1
            if alvo[0] == 'inventario':
                if not self._container.permite_interacao_por_slot():
                    return
                indice_real_destino = self._container.indice_real_por_visual(alvo[1], exigir_item=False)
                if indice_real_destino is None:
                    return
                resto = self._container.tentar_colocar_no_slot(indice_real_destino, parte)
                if resto is None:
                    item['quantidade'] = self._quantidade(item) - 1
            elif alvo[0] == 'craft':
                resto = self._painel_craft.colocar_no_slot(alvo[1], parte, origem=indice_origem if grupo_origem == 'inventario' else origem_aux)
                if not isinstance(resto, tuple) and resto is None:
                    item['quantidade'] = self._quantidade(item) - 1
            if self._quantidade(item) <= 0:
                self._arrastavel.cancelar()
            return

        if alvo[0] == 'inventario':
            if not self._container.permite_interacao_por_slot():
                self._retornar_para_origem()
                return
            indice_real_destino = self._container.indice_real_por_visual(alvo[1], exigir_item=False)
            if indice_real_destino is None:
                self._retornar_para_origem()
                return
            resto = self._container.tentar_colocar_no_slot(indice_real_destino, item)
            if resto is None:
                self._arrastavel.cancelar()
            else:
                self._arrastavel.Item = resto
        elif alvo[0] == 'craft':
            resto = self._painel_craft.colocar_no_slot(alvo[1], item, origem=indice_origem if grupo_origem == 'inventario' else origem_aux)
            if isinstance(resto, tuple):
                trocado, origem_trocada = resto
                self._arrastavel.Item = trocado
                self._arrastavel.Origem = ('craft', alvo[1], origem_trocada)
            elif resto is None:
                self._arrastavel.cancelar()

    def _coletar_saida_craft(self, mouse_pos):
        resultado, receita = self._painel_craft.resultado(self._painel_receitas.Receitas)
        if resultado is None:
            return
        self._painel_craft.consumir_para_craft(receita)
        self._painel_craft.limpar_preview()
        self._arrastavel.iniciar(resultado, ('saida', 0, None), self._painel_craft.item_rect_no_slot(self._painel_craft.slot_saida_rect()), mouse_pos, botao=1)
        self._item_hover = resultado

    def _aplicar_receita(self, receita, estado_receita=None):
        if receita is None:
            return
        estado = str(estado_receita or "").strip().lower()
        if not estado:
            estado = self._painel_receitas._estado_receita(receita, self._painel_receitas._quantidades_inventario(self._container))
        if estado == 'vermelho':
            return

        self._painel_craft.limpar_preview()
        self._painel_craft.preencher_receita(receita, self._container, estado=estado)

    def atualizar(self, tela, eventos, dt, area, ativo=True):
        self._garantir_slots()
        if not self._layout_montado:
            self._reconstruir(area)
        if not ativo:
            if self._estava_ativo:
                self.on_close()
            return
        if not self._estava_ativo:
            self.on_open()

        self._reconstruir(area)
        self._container._normalizar_tamanho()
        self._container._processar_scroll(eventos)
        self._processar_atalho_enter_pesquisa(eventos)

        receita_clicada, receita_hover = self._painel_receitas.processar_eventos(tela, eventos, dt, self._container)
        self._painel_craft.set_preview(receita_hover)
        if receita_clicada is not None:
            self._aplicar_receita(receita_clicada, estado_receita=self._painel_receitas.estado_atual_receita(receita_clicada, self._container))
        self._arrastavel.animar(dt)

        mouse = pygame.mouse.get_pos()
        alvo_mouse = self._alvo_no_mouse(mouse)
        self._item_hover = self._item_do_alvo(alvo_mouse)
        if self._item_hover is None and receita_hover is not None:
            self._item_hover = receita_hover.get('saida')
        if self._arrastavel.Ativo and self._arrastavel.Item is not None:
            self._item_hover = self._arrastavel.Item

        for evento in eventos:
            if evento.type == pygame.MOUSEMOTION and self._arrastavel.Ativo and self._arrastavel.PosAlvo is None:
                self._arrastavel.atualizar(evento.pos)
                if self._arrastavel.ModoDistribuidor and pygame.mouse.get_pressed()[2]:
                    alvo = self._alvo_no_mouse(evento.pos)
                    if alvo is not None and alvo[0] != 'saida' and self._arrastavel.pode_distribuir_em(alvo):
                        self._soltar_no_alvo(alvo, 3)
                        self._arrastavel.registrar_distribuicao(alvo)

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button in (1, 3):
                alvo = self._alvo_no_mouse(evento.pos)
                agora = pygame.time.get_ticks()
                if not self._arrastavel.Ativo and evento.button == 1 and self._click_duplo(alvo, agora):
                    indice_real = self._container.indice_real_por_visual(alvo[1], exigir_item=True) if alvo is not None else None
                    item = self._container.recolher_do_slot(indice_real) if indice_real is not None else None
                    if item is not None:
                        item = self._container.agrupar_todos_no_item(item)
                        self._arrastavel.iniciar(item, ('inventario', alvo[1], indice_real), self._container.item_rect_no_slot(self._container.slot_rect(alvo[1])), evento.pos, botao=1)
                    continue

                if self._arrastavel.Ativo:
                    if self._arrastavel.PosAlvo is not None:
                        continue
                    if alvo is None:
                        if self._area_total.collidepoint(evento.pos):
                            if evento.button == 1:
                                self._retornar_para_origem()
                            else:
                                pass
                        else:
                            if evento.button == 1:
                                self._dropar_fora()
                            else:
                                self._dropar_fora(quantidade=1)
                    elif alvo[0] == 'saida' and evento.button == 1:
                        self._coletar_saida_craft(evento.pos)
                    else:
                        self._soltar_no_alvo(alvo, evento.button)
                    continue

                if alvo is None:
                    self._item_hover = None
                    continue
                if alvo[0] == 'saida':
                    self._coletar_saida_craft(evento.pos)
                    continue
                if self._item_do_alvo(alvo) is not None:
                    self._iniciar_arrasto(alvo, evento.pos, evento.button)

            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 3 and self._arrastavel.Ativo:
                self._arrastavel.limpar_distribuidor()
                if self._arrastavel.vazio():
                    self._arrastavel.cancelar()

    def renderizar(self, tela, area, eventos, dt, ativo=True):
        self.atualizar(tela, eventos, dt, area, ativo=ativo)
        if not ativo:
            return

        highlight = self._alvo_no_mouse(pygame.mouse.get_pos())
        item_oculto = None
        if self._arrastavel.Ativo and self._arrastavel.Origem and self._arrastavel.Origem[0] == 'inventario':
            origem_visual = self._arrastavel.Origem[1]
            origem_real = self._arrastavel.Origem[2]
            if origem_real is not None and self.Inventario.Itens[origem_real] is None:
                item_oculto = origem_visual
        self._container.desenhar(
            tela,
            item_oculto=item_oculto,
            highlight=highlight[1] if highlight and highlight[0] == 'inventario' else None,
            eventos=eventos,
            dt=dt,
        )

        self._painel_info.render(tela, [], 0)
        self.TxtTotal.set_text(f'{self._quantidade_total_itens()} / {self._capacidade_total()} itens')
        self.TxtTotal.set_pos(self._area_info.center)
        self.TxtTotal.draw(tela)

        self._painel_craft.desenhar(tela, self._painel_receitas.Receitas, highlight=highlight)
        self._painel_receitas.renderizar(tela, self._container)
        self._ficha.renderizar(tela, self._area_ficha, self._item_ativo_ficha())

        if self._arrastavel.Ativo and self._arrastavel.Item is not None:
            ItemInventario.desenhar_item_no_rect(tela, self._arrastavel.Item, self._arrastavel.Rect)
