"""Controlador dedicado ao player local."""

from __future__ import annotations

import pygame


class ControladorPlayer:
    def __init__(self, controlador_objetos):
        self._objetos = controlador_objetos

    @property
    def player_local(self):
        return self._objetos.PlayerLocal

    def montar_player_local(self, dados_player):
        return self._objetos.montar_player_local(dados_player)

    def atualizar_frame(self, eventos, dt, camera, bloqueado: bool) -> None:
        if self.player_local is None:
            return
        if not bloqueado:
            mouse_tela = pygame.mouse.get_pos()
            mouse_mundo_tiles = camera.tela_para_mundo_tiles(mouse_tela)
            self._objetos.atualizar_player_local(eventos, dt, mouse_mundo_tiles)
            return
        if self.player_local.Controle is not None:
            self.player_local.Controle.atualizar_bloqueado(dt)

    def sincronizar_regras_mundo(self, leitor_mundo) -> None:
        if self.player_local is None:
            return
        leitor_mundo.atualizar_regras_mundo(self.player_local.Controle)

    def supervisionar_envio(self) -> None:
        # Reutiliza a supervisão de snapshots já estabilizada na rodada anterior.
        self._objetos._supervisionar_player_e_enfileirar_saida()

    def aplicar_diff_autoritativa(self, diff: dict) -> None:
        self._objetos.aplicar_diff(diff)
