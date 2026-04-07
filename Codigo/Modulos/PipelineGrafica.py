from __future__ import annotations

import pygame


class PipelineGrafica:
    """Compositor global de camadas de cena (sem lógica de update)."""

    def __init__(self, tela: pygame.Surface):
        self._tela = tela
        self._scene_surface = None
        self._scene_size = (0, 0)

    def _garantir_scene_surface(self) -> pygame.Surface:
        tamanho = self._tela.get_size()
        if self._scene_surface is None or self._scene_size != tamanho:
            self._scene_surface = pygame.Surface(tamanho).convert()
            self._scene_size = tamanho
        return self._scene_surface

    @staticmethod
    def _tem_hook(cena, nome: str) -> bool:
        return callable(getattr(cena, nome, None))

    def compor_cena(self, jogo, cena, eventos, dt) -> None:
        destino = self._tela
        tem_base = self._tem_hook(cena, "render_base")
        tem_post = self._tem_hook(cena, "render_post")
        tem_hud = self._tem_hook(cena, "render_hud")
        tem_overlay = self._tem_hook(cena, "render_overlay")

        if tem_base or tem_post:
            scene_surface = self._garantir_scene_surface()
            scene_surface.fill((0, 0, 0))
            if tem_base:
                cena.render_base(scene_surface, jogo, eventos, dt)
            if tem_post:
                cena.render_post(scene_surface, jogo, eventos, dt)
            destino.blit(scene_surface, (0, 0))

        if tem_hud:
            cena.render_hud(destino, jogo, eventos, dt)

        if tem_overlay:
            cena.render_overlay(destino, jogo, eventos, dt)
