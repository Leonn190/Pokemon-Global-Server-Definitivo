from __future__ import annotations

import pygame


class PlayerBatalha:
    def __init__(self, controlador) -> None:
        self.controlador = controlador
        self.mouse_down_pos = None
        self.mouse_down_pokemon = None
        self.mouse_down_em_hud = False
        self.arraste_pendente = False
        self.arrastando = False
        self.drag_threshold_px = 10

    def processar_eventos(self, eventos):
        if str(self.controlador.estado_batalha) != "montando_jogada":
            return
        for evento in eventos or []:
            if evento.type == pygame.KEYDOWN:
                self.processar_tecla(evento.key)
            elif evento.type == pygame.MOUSEMOTION:
                self.processar_movimento_mouse(evento.pos)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.processar_mouse_down(evento.pos)
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                self.processar_mouse_up(evento.pos)

    def processar_movimento_mouse(self, pos):
        montador = self.controlador.montador_jogadas
        if self.arraste_pendente and not self.arrastando and self.mouse_down_pos is not None and self.mouse_down_pokemon is not None:
            dx = float(pos[0]) - float(self.mouse_down_pos[0])
            dy = float(pos[1]) - float(self.mouse_down_pos[1])
            if (dx * dx + dy * dy) >= float(self.drag_threshold_px * self.drag_threshold_px):
                self.arrastando = True
                montador.iniciar_arraste_pokemon(self.mouse_down_pokemon, self.mouse_down_pos)
        if self.arrastando:
            montador.atualizar_arraste(pos)
        elif montador.estado_montagem == "preparando_ataque":
            montador.atualizar_preparacao(pos)

    def processar_mouse_down(self, pos_mouse):
        ctrl = self.controlador
        self.mouse_down_pos = pos_mouse
        self.mouse_down_em_hud = bool(ctrl.hud and ctrl.hud.consumiu_clique(pos_mouse))
        self.arraste_pendente = False
        self.mouse_down_pokemon = None
        if self.mouse_down_em_hud:
            return

        poke = self._pokemon_no_ponto(pos_mouse)
        if poke is not None and self.pode_controlar_pokemon(poke) and poke.esta_ativo() and not poke.esta_na_reserva():
            self.arraste_pendente = True
            self.mouse_down_pokemon = poke
            return
        self.processar_clique(pos_mouse)

    def processar_mouse_up(self, pos_mouse):
        if self.arrastando:
            self.controlador.montador_jogadas.soltar_arraste(pos_mouse)
        elif self.arraste_pendente and not self.mouse_down_em_hud:
            self.processar_clique(pos_mouse)
        self.arrastando = False
        self.arraste_pendente = False
        self.mouse_down_pokemon = None
        self.mouse_down_pos = None
        self.mouse_down_em_hud = False

    def processar_clique(self, pos_mouse):
        ctrl = self.controlador
        montador = ctrl.montador_jogadas

        if ctrl.hud and ctrl.hud.consumiu_clique(pos_mouse):
            return

        slot = ctrl.arena.reserva_em_posicao_mouse(pos_mouse, ctrl.camera)
        if slot is not None:
            poke = ctrl.pokemons_por_id.get(slot.get("pokemon_id"))
            if poke is not None:
                if ctrl.pokemon_selecionado == poke:
                    ctrl.desselecionar_pokemon()
                else:
                    ctrl.selecionar_pokemon(poke)
            return

        poke = self._pokemon_no_ponto(pos_mouse)
        if poke is not None:
            area_id = getattr(poke, "AreaId", None)
            if ctrl.ataque_selecionado is not None and area_id:
                if montador.confirmar_alvo(area_id):
                    ctrl.limpar_ataque()
                return
            if ctrl.pokemon_selecionado == poke:
                ctrl.desselecionar_pokemon()
            else:
                ctrl.selecionar_pokemon(poke)
            return

        area_id = ctrl.arena.area_em_posicao_mouse(pos_mouse, ctrl.camera)
        if area_id:
            if ctrl.ataque_selecionado is not None:
                if montador.confirmar_alvo(area_id):
                    ctrl.limpar_ataque()
                return
            if ctrl.area_selecionada == area_id:
                ctrl.desselecionar_pokemon()
            else:
                ctrl.selecionar_area(area_id)
            return

        self.cancelar_selecao()

    def processar_tecla(self, tecla):
        if tecla == pygame.K_ESCAPE:
            montador = self.controlador.montador_jogadas
            if montador.indicador_previa is not None or self.controlador.ataque_selecionado is not None:
                montador.cancelar_previa()
                self.controlador.limpar_ataque()
                return
            self.cancelar_selecao()

    def pode_controlar_pokemon(self, pokemon):
        if pokemon is None:
            return False
        if bool(self.controlador.modo_teste):
            return True
        return int(getattr(pokemon, "lado_id", -1)) == int(self.controlador.lado_jogador)

    def cancelar_selecao(self):
        self.controlador.desselecionar_pokemon()
        self.controlador.area_selecionada = None

    def _pokemon_no_ponto(self, pos_mouse):
        for pokemon in reversed(self.controlador.pokemons):
            if pokemon.contem_ponto(pos_mouse):
                return pokemon
        return None
