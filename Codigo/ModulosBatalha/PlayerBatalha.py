from __future__ import annotations

from typing import Dict, List

import pygame

from Codigo.Geradores.PokemonBatalha import PokemonBatalha


class ControlePlayer:
    TECLAS_ATAQUE = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t]
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


class PlayerBatalha:
    def __init__(self, lado: str, pokemons_slots: List[Dict[str, object]] | None = None, max_ativos: int = 3):
        self.Lado = str(lado or "jogador")
        self.MaxAtivos = max(1, int(max_ativos))
        self.TimeCompleto: List[Dict[str, object]] = [dict(p) for p in (pokemons_slots or []) if isinstance(p, dict)]
        self.PokemonsAtivos: List[PokemonBatalha] = []
        self.PokemonsReserva: List[Dict[str, object]] = []
        self.Controle = ControlePlayer()

    def preparar_slots(self):
        ativos = self.TimeCompleto[: self.MaxAtivos]
        self.PokemonsReserva = self.TimeCompleto[self.MaxAtivos :]
        return ativos

    def definir_ativos(self, pokemons: List[PokemonBatalha]):
        self.PokemonsAtivos = list(pokemons or [])
