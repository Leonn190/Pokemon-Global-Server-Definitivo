from __future__ import annotations

from typing import Optional

import pygame

from Codigo.Modulos.CompositorModernGL import CompositorModernGL


class PipelineGrafica:
    def __init__(self, tela_logica: pygame.Surface, tela_display: pygame.Surface | None = None):
        self._tela_logica = tela_logica
        self._tela_display = tela_display if tela_display is not None else tela_logica
        self._scene_surface: Optional[pygame.Surface] = None
        self._hud_surface: Optional[pygame.Surface] = None
        self._scene_size = (0, 0)
        self._compositor_gl = None
        self._motivo_fallback = ""
        self._inicializar_compositor_gl()

    def _inicializar_compositor_gl(self) -> None:
        flags = int(self._tela_display.get_flags()) if self._tela_display is not None else 0
        if not (flags & pygame.OPENGL):
            self._motivo_fallback = "display sem OPENGL"
            return
        try:
            self._compositor_gl = CompositorModernGL()
            self._motivo_fallback = ""
        except Exception as exc:  # pragma: no cover - depende do ambiente grafico
            self._compositor_gl = None
            self._motivo_fallback = str(exc)

    def shader_disponivel(self) -> bool:
        return self._compositor_gl is not None

    def motivo_fallback(self) -> str:
        return str(self._motivo_fallback or "")

    def _garantir_surfaces(self) -> None:
        tamanho = self._tela_logica.get_size()
        if self._scene_surface is None or self._hud_surface is None or self._scene_size != tamanho:
            self._scene_surface = pygame.Surface(tamanho).convert()
            self._hud_surface = pygame.Surface(tamanho, pygame.SRCALPHA).convert_alpha()
            self._scene_size = tamanho

    def obter_surface_scene(self) -> pygame.Surface:
        self._garantir_surfaces()
        return self._scene_surface

    def obter_surface_hud(self) -> pygame.Surface:
        self._garantir_surfaces()
        return self._hud_surface

    @staticmethod
    def _hook(cena, nome: str):
        fn = getattr(cena, nome, None)
        return fn if callable(fn) else None

    def _coletar_efeito_shader(self, cena, jogo, dt):
        coletor = self._hook(cena, "coletar_efeito_shader")
        if coletor is None:
            return None
        return coletor(jogo, dt, self._scene_size)

    def _compor_tela_cena(self, jogo, cena, eventos, dt, render_subtelas_scene=None) -> None:
        scene_surface = self.obter_surface_scene()
        hud_surface = self.obter_surface_hud()
        scene_surface.fill((0, 0, 0))
        hud_surface.fill((0, 0, 0, 0))

        tela_complexa = self._hook(cena, "tela_atual_eh_complexa")
        eh_complexa = bool(tela_complexa()) if tela_complexa is not None else False

        if eh_complexa:
            render_base = self._hook(cena, "render_base")
            render_post = self._hook(cena, "render_post")
            render_hud = self._hook(cena, "render_hud")
            if render_base is not None:
                render_base(scene_surface, jogo, eventos, dt)
            if callable(render_subtelas_scene):
                render_subtelas_scene(scene_surface)
            if render_post is not None:
                render_post(scene_surface, jogo, eventos, dt)
            if render_hud is not None:
                render_hud(hud_surface, jogo, eventos, dt)
            return

        render_tela = self._hook(cena, "render_tela")
        if render_tela is not None:
            render_tela(scene_surface, jogo, eventos, dt)
            if callable(render_subtelas_scene):
                render_subtelas_scene(scene_surface)
            return

        render_hud = self._hook(cena, "render_hud")
        if render_hud is not None:
            render_hud(hud_surface, jogo, eventos, dt)

    def _apresentar(self, jogo, cena, dt) -> None:
        scene_surface = self.obter_surface_scene()
        hud_surface = self.obter_surface_hud()
        if self._compositor_gl is not None:
            efeito = self._coletar_efeito_shader(cena, jogo, dt)
            shader_ativo = bool(jogo.CONFIG.get("Shader", True))
            self._compositor_gl.renderizar(scene_surface, hud_surface, efeito, shader_ativo=shader_ativo)
            return

        self._tela_display.blit(scene_surface, (0, 0))
        self._tela_display.blit(hud_surface, (0, 0))

    def renderizar_frame(
        self,
        jogo,
        cena,
        eventos,
        dt,
        render_subtelas_scene=None,
        render_subtelas_hud=None,
        render_adicionais=None,
        aplicar_claridade=None,
        render_transicao=None,
    ) -> None:
        self._compor_tela_cena(jogo, cena, eventos, dt, render_subtelas_scene=render_subtelas_scene)

        if isinstance(getattr(jogo, "INFO", None), dict):
            jogo.INFO["_frame_scene_surface"] = self.obter_surface_scene()
            jogo.INFO["_frame_hud_surface"] = self.obter_surface_hud()

        hud_surface = self.obter_surface_hud()
        if callable(render_subtelas_hud):
            render_subtelas_hud(hud_surface)
        if callable(render_adicionais):
            render_adicionais(hud_surface)
        if callable(aplicar_claridade):
            aplicar_claridade(hud_surface)
        if callable(render_transicao):
            render_transicao(hud_surface)

        self._apresentar(jogo, cena, dt)

    def liberar(self) -> None:
        if self._compositor_gl is not None:
            self._compositor_gl.liberar()
            self._compositor_gl = None
