from __future__ import annotations

from typing import Optional

import pygame

from Codigo.ModulosGerais.CompositorModernGL import CompositorModernGL
from Codigo.ModulosGerais.RenderizadorGL2D import RenderizadorGL2D


class PipelineGrafica:
    def __init__(self, tela_logica: pygame.Surface, tela_display: pygame.Surface | None = None):
        self._tela_logica = tela_logica
        self._tela_display = tela_display if tela_display is not None else tela_logica
        self._scene_surface: Optional[pygame.Surface] = None
        self._hud_surface: Optional[pygame.Surface] = None
        self._scene_size = (0, 0)
        self._compositor_gl = None
        self._renderizador_gl2d = None
        self._motivo_fallback = ""
        self._inicializar_compositor_gl()

    def _inicializar_compositor_gl(self) -> None:
        flags = int(self._tela_display.get_flags()) if self._tela_display is not None else 0
        if not (flags & pygame.OPENGL):
            self._motivo_fallback = "display sem OPENGL"
            return
        try:
            self._compositor_gl = CompositorModernGL()
            self._renderizador_gl2d = RenderizadorGL2D(ctx=self._compositor_gl.contexto)
            self._motivo_fallback = ""
        except Exception as exc:  # pragma: no cover - depende do ambiente grafico
            self._compositor_gl = None
            self._renderizador_gl2d = None
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


    def _renderizar_cena_gl2d(self, jogo, cena, eventos, dt) -> bool:
        render_gl = self._hook(cena, "render_gl")
        if render_gl is None or self._renderizador_gl2d is None:
            return False
        try:
            self._renderizador_gl2d.iniciar_frame(self._tela_display.get_size())
            renderizado = bool(render_gl(self._renderizador_gl2d, jogo, eventos, dt))
            if not renderizado:
                return False
            if isinstance(getattr(jogo, "INFO", None), dict):
                jogo.INFO["RenderPath"] = "menu_gl"
                jogo.INFO["GLUploadsFrame"] = int(self._renderizador_gl2d.uploads_frame)
                jogo.INFO["GLDrawCallsFrame"] = int(self._renderizador_gl2d.draw_calls_frame)
            return True
        except Exception as exc:
            self._motivo_fallback = f"render_gl falhou: {exc}"
            return False

    @staticmethod
    def _adicionais_suportados_em_gl(jogo, render_adicionais) -> bool:
        if not callable(render_adicionais):
            return True
        fn = getattr(render_adicionais, "__func__", None)
        alvo = getattr(getattr(jogo, "DesenharInfosAdicionais", None), "__func__", None)
        return fn is not None and alvo is not None and fn is alvo

    def _desenhar_infos_adicionais_gl(self, jogo, cena) -> None:
        if self._renderizador_gl2d is None:
            return
        cfg = getattr(jogo, "CONFIG", {}) if isinstance(getattr(jogo, "CONFIG", None), dict) else {}
        largura_tela = int(self._tela_display.get_width())
        itens_hud = []

        if cfg.get("FPS Visivel", False):
            jogo.TextoFPS.set_text(f"FPS: {int(jogo.RELOGIO.get_fps())}")
            itens_hud.append(jogo.TextoFPS)

        if cfg.get("Ping Visivel", False):
            jogo.TextoPing.set_text("Ping: 5")
            itens_hud.append(jogo.TextoPing)

        if cfg.get("Cords Visiveis", False):
            entidade_main = getattr(cena, "EntidadeMain", None)
            if entidade_main is not None and hasattr(entidade_main, "Posicao"):
                x, y = entidade_main.Posicao
                jogo.TextoCoords.set_text(f"X {x:.2f} | Y {y:.2f}")
            else:
                jogo.TextoCoords.set_text("--")
            itens_hud.append(jogo.TextoCoords)

        if cfg.get("MostrarHorario", False):
            if hasattr(cena, "ControladorMundo") and getattr(cena, "ControladorMundo", None) is not None:
                tempo = cena.ControladorMundo.tempo_mundo_atual()
                if "dia" in tempo and "hora" in tempo and "minuto" in tempo:
                    dia = int(tempo.get("dia", 0) or 0)
                    hora = int(tempo.get("hora", 0) or 0)
                    minuto = int(tempo.get("minuto", 0) or 0)
                    jogo.TextoHorario.set_text(f"Dia {dia} | {hora:02d}:{minuto:02d}")
                else:
                    jogo.TextoHorario.set_text("Dia -- | --:--")
            else:
                jogo.TextoHorario.set_text("Dia -- | --:--")
            itens_hud.append(jogo.TextoHorario)

        y_base = 12
        espaco = 32
        for idx, texto in enumerate(itens_hud):
            texto.set_pos((largura_tela - 16, y_base + idx * espaco))
            texto.draw_gl(self._renderizador_gl2d)

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
        subtelas_hud_ativas = callable(render_subtelas_hud) and bool(getattr(getattr(jogo, "GerenciadorSubtelas", None), "ativa", False))
        claridade_ativa = callable(aplicar_claridade) and int(getattr(jogo, "CONFIG", {}).get("Claridade", 75) or 75) != 75
        transicao_ativa = callable(render_transicao)
        adicionais_suportados = self._adicionais_suportados_em_gl(jogo, render_adicionais)

        if subtelas_hud_ativas or claridade_ativa or transicao_ativa or (not adicionais_suportados):
            self._compor_tela_cena(jogo, cena, eventos, dt, render_subtelas_scene=render_subtelas_scene)

            if isinstance(getattr(jogo, "INFO", None), dict):
                jogo.INFO["RenderPath"] = "surface_fallback"
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
            return

        if self._renderizar_cena_gl2d(jogo, cena, eventos, dt):
            if callable(render_adicionais):
                self._desenhar_infos_adicionais_gl(jogo, cena)
            if isinstance(getattr(jogo, "INFO", None), dict):
                jogo.INFO["GLUploadsFrame"] = int(self._renderizador_gl2d.uploads_frame)
                jogo.INFO["GLDrawCallsFrame"] = int(self._renderizador_gl2d.draw_calls_frame)
            self._renderizador_gl2d.finalizar_frame()
            return

        self._compor_tela_cena(jogo, cena, eventos, dt, render_subtelas_scene=render_subtelas_scene)

        if isinstance(getattr(jogo, "INFO", None), dict):
            jogo.INFO["RenderPath"] = "surface_fallback"
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
        if self._renderizador_gl2d is not None:
            self._renderizador_gl2d.liberar()
            self._renderizador_gl2d = None
        if self._compositor_gl is not None:
            self._compositor_gl.liberar()
            self._compositor_gl = None
