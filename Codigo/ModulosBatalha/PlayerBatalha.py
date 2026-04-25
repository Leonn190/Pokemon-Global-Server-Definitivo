from __future__ import annotations

import pygame


class PlayerBatalha:
    def __init__(self, controlador) -> None:
        self.controlador = controlador

    def processar_eventos(self, eventos):
        for evento in eventos or []:
            if evento.type == pygame.KEYDOWN:
                self.processar_tecla(evento.key)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.processar_clique(evento.pos)

    def processar_clique(self, pos_mouse):
        ctrl = self.controlador

        if ctrl.hud and ctrl.hud.consumiu_clique(pos_mouse):
            return

        for pokemon in reversed(ctrl.pokemons):
            if pokemon.contem_ponto(pos_mouse):
                if ctrl.pokemon_selecionado is pokemon:
                    ctrl.desselecionar_pokemon()
                    return
                ctrl.selecionar_pokemon(pokemon)
                return

        slot = ctrl.arena.reserva_em_posicao_mouse(pos_mouse)
        if slot is not None:
            poke = ctrl.pokemons_por_id.get(slot.get("pokemon_id"))
            if poke is not None:
                if ctrl.pokemon_selecionado is poke:
                    ctrl.desselecionar_pokemon()
                else:
                    ctrl.selecionar_pokemon(poke)
            return

        area_id = ctrl.arena.area_em_posicao_mouse(pos_mouse, ctrl.camera)
        if area_id:
            if ctrl.area_selecionada == area_id:
                ctrl.area_selecionada = None
            else:
                ctrl.selecionar_area(area_id)
        else:
            self.cancelar_selecao()

    def processar_tecla(self, tecla):
        if tecla == pygame.K_ESCAPE:
            if self.controlador.ataque_selecionado is not None:
                self.controlador.limpar_ataque()
            else:
                self.cancelar_selecao()

    def pode_controlar_pokemon(self, pokemon):
        if pokemon is None:
            return False
        if pokemon.Lado == "jogador":
            return True
        return bool(self.controlador.modo_teste)

    def cancelar_selecao(self):
        self.controlador.desselecionar_pokemon()
        self.controlador.area_selecionada = None
