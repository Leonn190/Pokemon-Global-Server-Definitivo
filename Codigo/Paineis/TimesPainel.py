from __future__ import annotations

import pygame

from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto


class TimesPainel(PainelRolavel):
    def __init__(self, rect, times=None, slots_por_time=6):
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
        self.Padding = 16
        self.GapCards = 14
        self.SlotGap = 8
        self.CabecalhoH = 54

        estilo = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtTitulo = Texto('Times', style={**estilo, 'size': 19, 'color': (236, 241, 255)})
        self.TxtSub = Texto('Arraste para montar equipes', style={**estilo, 'size': 13, 'color': (174, 190, 224)})
        self._normalizar_times()

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self.atualizar_area_real()

    def definir_times(self, times):
        self.Times = times if times is not None else []
        self._normalizar_times()
        self.atualizar_area_real()

    def definir_slots_por_time(self, slots_por_time):
        self.SlotsPorTime = max(1, int(slots_por_time))
        self._normalizar_times()
        self.atualizar_area_real()

    def _slot_px(self):
        largura_util = max(40, self.rect.width - self.Padding * 2 - 22)
        total_gap = self.SlotGap * max(0, self.SlotsPorTime - 1)
        return max(32, min(52, int((largura_util - total_gap) / max(1, self.SlotsPorTime))))

    def _card_h(self):
        return 42 + self._slot_px() + 18

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
        self.atualizar_area_real()

    def atualizar_area_real(self):
        total = len(self.Times)
        altura = self.Padding * 2 + self.CabecalhoH + total * self._card_h() + max(0, total - 1) * self.GapCards
        self.definir_area_real(self.rect.width, max(self.rect.height, altura))

    def garantir_minimo_times(self, quantidade):
        while len(self.Times) < quantidade:
            self.Times.append({'Nome': f'Time {len(self.Times) + 1}', 'Slots': [None] * self.SlotsPorTime})
        self._normalizar_times()

    def nome_time(self, indice):
        self._normalizar_times()
        return str(self.Times[indice].get('Nome') or f'Time {indice + 1}')

    def slots_time(self, indice):
        self._normalizar_times()
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
        return anterior

    def retirar_do_slot(self, indice_time, indice_slot):
        slots = self.slots_time(indice_time)
        pokemon = slots[indice_slot]
        slots[indice_slot] = None
        return pokemon

    def _card_rect(self, indice):
        y = self.rect.y + self.Padding + self.CabecalhoH + indice * (self._card_h() + self.GapCards) - self.ScrollY
        return pygame.Rect(self.rect.x + self.Padding, y, self.rect.width - self.Padding * 2, self._card_h())

    def slot_rect(self, indice_time, indice_slot):
        card = self._card_rect(indice_time)
        slot_px = self._slot_px()
        total_largura = slot_px * self.SlotsPorTime + self.SlotGap * max(0, self.SlotsPorTime - 1)
        inicio_x = card.centerx - total_largura // 2
        y = card.y + 42
        x = inicio_x + indice_slot * (slot_px + self.SlotGap)
        return pygame.Rect(x, y, slot_px, slot_px)

    def alvo_no_mouse(self, mouse_pos):
        if not self.rect.collidepoint(mouse_pos):
            return None
        for indice_time in range(len(self.Times)):
            for indice_slot in range(self.SlotsPorTime):
                rect = self.slot_rect(indice_time, indice_slot)
                if rect.collidepoint(mouse_pos) and self.rect.colliderect(rect):
                    return ('time', indice_time, indice_slot)
        return None

    def desenhar(self, tela, highlight=None, item_oculto=None):
        self._normalizar_times()
        self.atualizar_area_real()
        self.render(tela, [], 0)

        self.TxtTitulo.set_pos((self.rect.x + 16, self.rect.y + 12))
        self.TxtTitulo.draw(tela)
        self.TxtSub.set_pos((self.rect.x + 18, self.rect.y + 36))
        self.TxtSub.draw(tela)

        estilo_nome = {'size': 16, 'color': (240, 244, 255), 'outline': True, 'outline_color': (8, 12, 20), 'outline_thickness': 2}

        for indice_time in range(len(self.Times)):
            card = self._card_rect(indice_time)
            if not self.rect.colliderect(card):
                continue

            pygame.draw.rect(tela, (24, 34, 56), card, border_radius=14)
            pygame.draw.rect(tela, (58, 80, 128), card, 2, border_radius=14)

            txt_nome = Texto(self.nome_time(indice_time), style=estilo_nome)
            txt_nome.set_pos((card.x + 14, card.y + 12))
            txt_nome.draw(tela)

            for indice_slot in range(self.SlotsPorTime):
                rect_slot = self.slot_rect(indice_time, indice_slot)
                destaque = highlight == ('time', indice_time, indice_slot)
                surf = pygame.Surface(rect_slot.size, pygame.SRCALPHA)
                pygame.draw.rect(surf, (76, 96, 140, 255), surf.get_rect(), border_radius=10)
                pygame.draw.rect(surf, (228, 239, 255) if destaque else (20, 26, 40), surf.get_rect(), 2, border_radius=10)
                tela.blit(surf, rect_slot.topleft)

                if item_oculto == (indice_time, indice_slot):
                    continue
                pokemon = self.pokemon_no_slot(indice_time, indice_slot)
                if pokemon is not None:
                    PokemonInventario.desenhar_item_no_rect(
                        tela,
                        pokemon,
                        pygame.Rect(rect_slot.x + 5, rect_slot.y + 5, rect_slot.width - 10, rect_slot.height - 10),
                    )
