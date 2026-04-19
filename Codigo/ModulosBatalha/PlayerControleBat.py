from __future__ import annotations

import pygame


class PlayerControleBat:
    TECLAS_ATAQUE = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_a, pygame.K_s]
    TECLAS_POKEMON = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6]

    def processar_eventos(self, eventos, controlador_batalha, ficha, fluxos) -> None:
        for evento in eventos or []:
            if evento.type != pygame.KEYDOWN:
                continue

            if evento.key in self.TECLAS_POKEMON and controlador_batalha is not None:
                indice = self.TECLAS_POKEMON.index(evento.key)
                controlador_batalha.selecionar_slot_aliado(indice)
                continue

            if evento.key in self.TECLAS_ATAQUE and ficha is not None:
                indice = self.TECLAS_ATAQUE.index(evento.key)
                pokemon = getattr(controlador_batalha, "PokemonSelecionado", None) if controlador_batalha is not None else None
                ficha.selecionar_ataque_indice(indice, pokemon)
                continue

            if evento.key == pygame.K_ESCAPE:
                if fluxos is not None:
                    fluxos.cancelar_preparacao()
                if ficha is not None:
                    ficha.limpar_ataque_selecionado()
