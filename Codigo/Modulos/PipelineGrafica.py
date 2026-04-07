from __future__ import annotations

import pygame


class PipelineGrafica:
    """Compositor global: tela da cena + topo global."""

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
    def _hook(cena, nome: str):
        fn = getattr(cena, nome, None)
        return fn if callable(fn) else None

    def _compor_tela_cena(self, jogo, cena, eventos, dt) -> None:
        destino = self._tela
        tela_complexa = self._hook(cena, "tela_atual_eh_complexa")
        eh_complexa = bool(tela_complexa()) if tela_complexa is not None else False

        if eh_complexa:
            scene_surface = self._garantir_scene_surface()
            scene_surface.fill((0, 0, 0))
            render_base = self._hook(cena, "render_base")
            render_post = self._hook(cena, "render_post")
            render_hud = self._hook(cena, "render_hud")
            if render_base is not None:
                render_base(scene_surface, jogo, eventos, dt)
            if render_post is not None:
                render_post(scene_surface, jogo, eventos, dt)
            destino.blit(scene_surface, (0, 0))
            if render_hud is not None:
                render_hud(destino, jogo, eventos, dt)
            return

        render_tela = self._hook(cena, "render_tela")
        if render_tela is not None:
            render_tela(destino, jogo, eventos, dt)
            return

        render_hud = self._hook(cena, "render_hud")
        if render_hud is not None:
            render_hud(destino, jogo, eventos, dt)

    def renderizar_frame(self, jogo, cena, eventos, dt, render_subtelas=None, render_adicionais=None, aplicar_claridade=None) -> None:
        self._compor_tela_cena(jogo, cena, eventos, dt)

        if callable(render_subtelas):
            render_subtelas()
        if callable(render_adicionais):
            render_adicionais()
        if callable(aplicar_claridade):
            aplicar_claridade()
