from __future__ import annotations

import pygame

from Codigo.ModulosMundo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto


class PainelTimes(PainelRolavel):
    def __init__(self, rect, times=None, slots_por_time=6, modo_selecao=False, indice_selecionado=-1):
        super().__init__(
            rect,
            area_real=(0, 0, rect[2], rect[3]),
            cor_fundo=(18, 26, 44, 242),
            cor_borda=(66, 88, 136),
            borda=2,
            raio=16,
        )
        self.Times = times if times is not None else []
        self.SlotsPorTime = max(1, int(slots_por_time))
        self.Padding = 12
        self.GapCards = 10
        self.SlotGap = 8
        self.ModoSelecao = bool(modo_selecao)
        self.IndiceSelecionado = int(indice_selecionado)

        estilo = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20),
        }
        self.TxtTitulo = Texto('', style={**estilo, 'size': 19, 'color': (236, 241, 255)})
        self.TxtTipoEquipePct = Texto('', style={**estilo, 'size': 13, 'color': (186, 202, 236), 'align': 'midleft'})

        self._highlight_render = None
        self._item_oculto_render = None
        self._estado_visual = None

        self._normalizar_times()
        self.atualizar_area_real()
        self.marcar_sujo()

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self.atualizar_area_real()
        self.marcar_sujo()

    def definir_times(self, times):
        self.Times = times if times is not None else []
        self._normalizar_times()
        self.atualizar_area_real()
        self.marcar_sujo()

    def definir_slots_por_time(self, slots_por_time):
        self.SlotsPorTime = max(1, int(slots_por_time))
        self._normalizar_times()
        self.atualizar_area_real()
        self.marcar_sujo()

    def _slot_px(self):
        largura_util = max(40, self.rect.width - self.Padding * 2 - 4)
        total_gap = self.SlotGap * max(0, self.SlotsPorTime - 1)
        return max(32, min(52, int((largura_util - total_gap) / max(1, self.SlotsPorTime))))

    def _card_h(self):
        return 44 + self._slot_px() + 16

    def _topo_util_conteudo(self):
        return self.Padding

    def _normalizar_time(self, time, indice):
        nome_padrao = f'Time {indice + 1}'

        if isinstance(time, dict):
            nome = str(time.get('Nome') or time.get('nome') or nome_padrao)
            slots = list(time.get('Slots') or time.get('slots') or [])

            if len(slots) < self.SlotsPorTime:
                slots.extend([None] * (self.SlotsPorTime - len(slots)))
            elif len(slots) > self.SlotsPorTime:
                slots = slots[:self.SlotsPorTime]

            time['Nome'] = nome
            time['Slots'] = slots
            if 'slots' in time:
                time['slots'] = slots
            return time

        if isinstance(time, list):
            slots = list(time)
            if len(slots) < self.SlotsPorTime:
                slots.extend([None] * (self.SlotsPorTime - len(slots)))
            elif len(slots) > self.SlotsPorTime:
                slots = slots[:self.SlotsPorTime]
            return {'Nome': nome_padrao, 'Slots': slots}

        return {'Nome': nome_padrao, 'Slots': [None] * self.SlotsPorTime}

    def _normalizar_times(self):
        if not isinstance(self.Times, list):
            self.Times = []

        for i in range(len(self.Times)):
            self.Times[i] = self._normalizar_time(self.Times[i], i)

    def atualizar_area_real(self):
        total = len(self.Times)
        altura = (
            self.Padding * 2
            + total * self._card_h()
            + max(0, total - 1) * self.GapCards
        )
        self.definir_area_real(self.rect.width, max(self.rect.height, altura))

    def garantir_minimo_times(self, quantidade):
        alterou = False
        while len(self.Times) < quantidade:
            self.Times.append({
                'Nome': f'Time {len(self.Times) + 1}',
                'Slots': [None] * self.SlotsPorTime
            })
            alterou = True

        if alterou:
            self._normalizar_times()
            self.atualizar_area_real()
            self.marcar_sujo()

    def nome_time(self, indice):
        return str(self.Times[indice].get('Nome') or f'Time {indice + 1}')

    def slots_time(self, indice):
        return self.Times[indice]['Slots']

    def pokemon_no_slot(self, indice_time, indice_slot):
        return self.slots_time(indice_time)[indice_slot]

    def definir_slot(self, indice_time, indice_slot, pokemon, limpar_duplicados=False):
        slots = self.slots_time(indice_time)

        if limpar_duplicados and pokemon is not None:
            chave = PokemonInventario.chave_pokemon(pokemon)
            for i, atual in enumerate(slots):
                if i == indice_slot or atual is None:
                    continue
                if PokemonInventario.chave_pokemon(atual) == chave:
                    slots[i] = None

        anterior = slots[indice_slot]
        slots[indice_slot] = pokemon
        self.marcar_sujo()
        return anterior

    def retirar_do_slot(self, indice_time, indice_slot):
        slots = self.slots_time(indice_time)
        pokemon = slots[indice_slot]
        slots[indice_slot] = None
        self.marcar_sujo()
        return pokemon

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

    def _card_rect_local(self, indice):
        y = self._topo_util_conteudo() + indice * (self._card_h() + self.GapCards)
        return pygame.Rect(
            self.Padding,
            y,
            self.rect.width - self.Padding * 2,
            self._card_h(),
        )

    def _slot_rect_local(self, indice_time, indice_slot):
        card = self._card_rect_local(indice_time)
        slot_px = self._slot_px()
        total_largura = slot_px * self.SlotsPorTime + self.SlotGap * max(0, self.SlotsPorTime - 1)
        inicio_x = card.centerx - total_largura // 2
        y = card.y + 42
        x = inicio_x + indice_slot * (slot_px + self.SlotGap)
        return pygame.Rect(x, y, slot_px, slot_px)

    def _tipagens_predominantes(self, indice_time):
        contagem = {}
        total = 0
        for pokemon in self.slots_time(indice_time):
            if pokemon is None:
                continue
            total += 1
            for tipo in PokemonInventario.tipos_pokemon(pokemon):
                contagem[tipo] = contagem.get(tipo, 0) + 1
        if total <= 0:
            return []
        ordenado = sorted(contagem.items(), key=lambda par: (-par[1], PokemonInventario.normalizar_tipo(par[0])))
        return [(tipo, (qtd / total) * 100.0) for tipo, qtd in ordenado[:3]]

    def _assinatura_visual(self, highlight, item_oculto):
        return (highlight, item_oculto)

    def slot_rect(self, indice_time, indice_slot):
        return self._rect_local_para_tela(self._slot_rect_local(indice_time, indice_slot))

    def alvo_no_mouse(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos):
            return None

        mouse_local = self._mouse_global_para_local(mouse_pos)

        for indice_time in range(len(self.Times)):
            for indice_slot in range(self.SlotsPorTime):
                rect = self._slot_rect_local(indice_time, indice_slot)
                if rect.collidepoint(mouse_local):
                    return ('time', indice_time, indice_slot)

        return None

    def alvo_contexto_no_mouse(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos):
            return None
        mouse_local = self._mouse_global_para_local(mouse_pos)
        for indice_time in range(len(self.Times)):
            card = self._card_rect_local(indice_time)
            if not card.collidepoint(mouse_local):
                continue
            for indice_slot in range(self.SlotsPorTime):
                rect = self._slot_rect_local(indice_time, indice_slot)
                if rect.collidepoint(mouse_local):
                    return ('time_slot', indice_time, indice_slot)
            return ('time_card', indice_time, None)
        return None

    def poder_time(self, indice):
        total = 0.0
        for pokemon in self.slots_time(indice):
            total += PokemonInventario.poder_total(pokemon)
        return int(total)


    def definir_modo_selecao(self, ativo: bool):
        self.ModoSelecao = bool(ativo)
        self.marcar_sujo()

    def definir_indice_selecionado(self, indice: int):
        self.IndiceSelecionado = int(indice)
        self.marcar_sujo()

    def indice_time_no_mouse(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos):
            return None
        mouse_local = self._mouse_global_para_local(mouse_pos)
        for indice_time in range(len(self.Times)):
            if self._card_rect_local(indice_time).collidepoint(mouse_local):
                return indice_time
        return None
    def draw(self, tela):
        tela.fill((0, 0, 0, 0))
        tela.fill(self.CorFundo)

        estilo_nome = {
            'size': 16,
            'color': (240, 244, 255),
            'outline': True,
            'outline_color': (8, 12, 20),
            'outline_thickness': 2,
        }

        highlight = self._highlight_render
        item_oculto = self._item_oculto_render

        for indice_time in range(len(self.Times)):
            card = self._card_rect_local(indice_time)

            selecionado = self.ModoSelecao and indice_time == self.IndiceSelecionado
            cor_card = (34, 48, 74) if selecionado else (24, 34, 56)
            cor_borda = (255, 224, 104) if selecionado else (58, 80, 128)
            pygame.draw.rect(tela, cor_card, card, border_radius=14)
            pygame.draw.rect(tela, cor_borda, card, 2, border_radius=14)

            txt_poder = Texto(f'Poder: {self.poder_time(indice_time)}', style={**estilo_nome, 'size': 13, 'color': (175, 196, 236)})
            txt_poder.set_pos((card.x + 12, card.y + card.height - 12))
            txt_poder.draw(tela)

            txt_nome = Texto(self.nome_time(indice_time), style=estilo_nome)
            txt_nome.set_pos((card.x + 14, card.y + 10))
            txt_nome.draw(tela)

            tipagens = self._tipagens_predominantes(indice_time)
            lado_tipo = 20
            gap_tipo = 10
            bloco_largura = len(tipagens) * (lado_tipo + 34 + gap_tipo)
            x_tipo = card.right - 10 - bloco_largura
            y_tipo = card.y + 10
            for tipo, pct in tipagens:
                fundo = pygame.Rect(x_tipo, y_tipo, lado_tipo, lado_tipo)
                icone = PokemonInventario.icone_tipo(tipo, lado_tipo + 1)
                if icone is not None:
                    tela.blit(icone, icone.get_rect(center=fundo.center))
                cor_pct = (255, 224, 92) if int(round(pct)) >= 100 else (186, 202, 236)
                self.TxtTipoEquipePct.set_text(f'{int(round(pct))}%')
                self.TxtTipoEquipePct.style['color'] = cor_pct
                self.TxtTipoEquipePct.set_pos((fundo.right + 5, fundo.centery))
                self.TxtTipoEquipePct.draw(tela)
                x_tipo += lado_tipo + 34 + gap_tipo

            for indice_slot in range(self.SlotsPorTime):
                rect_slot = self._slot_rect_local(indice_time, indice_slot)
                destaque = highlight == ('time', indice_time, indice_slot)

                surf = pygame.Surface(rect_slot.size, pygame.SRCALPHA)
                pygame.draw.rect(surf, (76, 96, 140, 255), surf.get_rect(), border_radius=10)
                pygame.draw.rect(
                    surf,
                    (228, 239, 255) if destaque else (20, 26, 40),
                    surf.get_rect(),
                    2,
                    border_radius=10,
                )
                tela.blit(surf, rect_slot.topleft)

                if item_oculto == (indice_time, indice_slot):
                    continue

                pokemon = self.pokemon_no_slot(indice_time, indice_slot)
                if pokemon is not None:
                    PokemonInventario.desenhar_item_no_rect(
                        tela,
                        pokemon,
                        pygame.Rect(
                            rect_slot.x + 5,
                            rect_slot.y + 5,
                            rect_slot.width - 10,
                            rect_slot.height - 10,
                        ),
                    )

    def desenhar(self, tela, highlight=None, item_oculto=None, eventos=None, dt=0, jogo=None):
        estado_visual = self._assinatura_visual(highlight, item_oculto)

        if estado_visual != self._estado_visual:
            self._highlight_render = highlight
            self._item_oculto_render = item_oculto
            self._estado_visual = estado_visual
            self.marcar_sujo()

        self.render(tela, eventos or [], dt, jogo=jogo)
