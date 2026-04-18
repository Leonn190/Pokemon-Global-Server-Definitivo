from __future__ import annotations

from typing import Optional

import pygame

from Codigo.ModulosGerais.CacheTexturasGL import CacheTexturasGL

try:
    import moderngl
except ImportError:  # pragma: no cover
    moderngl = None


class RenderizadorGL2D:
    def __init__(self, ctx=None):
        if moderngl is None:
            raise RuntimeError("moderngl indisponivel")

        self._ctx = ctx if ctx is not None else moderngl.create_context()
        self._ctx.disable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self._cache = CacheTexturasGL(self._ctx)

        self._program_tex = self._ctx.program(
            vertex_shader="""
                #version 330
                in vec2 in_pos;
                in vec2 in_uv;
                out vec2 v_uv;
                uniform vec2 u_resolution;
                void main() {
                    vec2 ndc = vec2((in_pos.x / u_resolution.x) * 2.0 - 1.0,
                                    1.0 - (in_pos.y / u_resolution.y) * 2.0);
                    gl_Position = vec4(ndc, 0.0, 1.0);
                    v_uv = in_uv;
                }
            """,
            fragment_shader="""
                #version 330
                in vec2 v_uv;
                out vec4 f_color;
                uniform sampler2D u_texture;
                uniform float u_alpha;
                uniform vec2 u_rect_size;
                uniform float u_radius_px;
                uniform vec4 u_border_color;
                uniform float u_border_width_px;

                float roundedBoxSDF(vec2 p, vec2 b, float r) {
                    vec2 q = abs(p) - b + vec2(r);
                    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
                }

                void main() {
                    vec2 half_size = u_rect_size * 0.5;
                    vec2 p = (v_uv - 0.5) * u_rect_size;
                    float radius = clamp(u_radius_px, 0.0, min(half_size.x, half_size.y));
                    float d = roundedBoxSDF(p, half_size, radius);
                    float aa = 1.0;
                    float shape_alpha = 1.0 - smoothstep(0.0, aa, d);
                    if (shape_alpha <= 0.0) {
                        discard;
                    }

                    vec4 tex = texture(u_texture, v_uv);
                    vec4 fill = vec4(tex.rgb, tex.a * u_alpha * shape_alpha);

                    if (u_border_width_px <= 0.0 || u_border_color.a <= 0.0) {
                        f_color = fill;
                        return;
                    }

                    float inner_r = max(0.0, radius - u_border_width_px);
                    vec2 inner_half = max(vec2(0.0), half_size - vec2(u_border_width_px));
                    float inner_d = roundedBoxSDF(p, inner_half, inner_r);
                    float alpha_inner = 1.0 - smoothstep(0.0, aa, inner_d);
                    vec4 border = vec4(u_border_color.rgb, u_border_color.a * shape_alpha * (1.0 - alpha_inner));
                    f_color = border + (fill * alpha_inner);
                }
            """,
        )

        self._program_rect = self._ctx.program(
            vertex_shader="""
                #version 330
                in vec2 in_pos;
                in vec2 in_uv;
                out vec2 v_uv;
                uniform vec2 u_resolution;
                void main() {
                    vec2 ndc = vec2((in_pos.x / u_resolution.x) * 2.0 - 1.0,
                                    1.0 - (in_pos.y / u_resolution.y) * 2.0);
                    gl_Position = vec4(ndc, 0.0, 1.0);
                    v_uv = in_uv;
                }
            """,
            fragment_shader="""
                #version 330
                in vec2 v_uv;
                out vec4 f_color;
                uniform vec4 u_color;
                uniform vec4 u_border_color;
                uniform vec2 u_rect_size;
                uniform float u_radius_px;
                uniform float u_border_width_px;

                float roundedBoxSDF(vec2 p, vec2 b, float r) {
                    vec2 q = abs(p) - b + vec2(r);
                    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
                }

                void main() {
                    vec2 half_size = u_rect_size * 0.5;
                    vec2 p = (v_uv - 0.5) * u_rect_size;
                    float radius = clamp(u_radius_px, 0.0, min(half_size.x, half_size.y));
                    float d = roundedBoxSDF(p, half_size, radius);

                    float aa = 1.0;
                    float alpha_fill = 1.0 - smoothstep(0.0, aa, d);
                    if (alpha_fill <= 0.0) {
                        discard;
                    }

                    vec4 fill = vec4(u_color.rgb, u_color.a * alpha_fill);
                    if (u_border_width_px <= 0.0 || u_border_color.a <= 0.0) {
                        f_color = fill;
                        return;
                    }

                    float inner_r = max(0.0, radius - u_border_width_px);
                    vec2 inner_half = max(vec2(0.0), half_size - vec2(u_border_width_px));
                    float inner_d = roundedBoxSDF(p, inner_half, inner_r);
                    float alpha_inner = 1.0 - smoothstep(0.0, aa, inner_d);
                    vec4 border = vec4(u_border_color.rgb, u_border_color.a * alpha_fill * (1.0 - alpha_inner));
                    f_color = border + (fill * alpha_inner);
                }
            """,
        )

        self._vbo = self._ctx.buffer(reserve=6 * 4 * 4)
        self._vao_tex = self._ctx.vertex_array(self._program_tex, [(self._vbo, "2f 2f", "in_pos", "in_uv")])
        self._vao_rect = self._ctx.vertex_array(self._program_rect, [(self._vbo, "2f 2f", "in_pos", "in_uv")])
        self._tamanho_tela = (1, 1)
        self.draw_calls_frame = 0

        self._program_tex["u_texture"] = 0
        self._custom_programs = {}

    def iniciar_frame(self, tamanho_tela: tuple[int, int] | None = None) -> None:
        if tamanho_tela is not None:
            self._tamanho_tela = (max(1, int(tamanho_tela[0])), max(1, int(tamanho_tela[1])))
        self._ctx.disable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self._ctx.viewport = (0, 0, self._tamanho_tela[0], self._tamanho_tela[1])
        self._ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.draw_calls_frame = 0
        self._cache.iniciar_frame()

    def finalizar_frame(self) -> None:
        return

    @property
    def uploads_frame(self) -> int:
        return int(self._cache.uploads_frame)

    def _quad_data(self, rect: pygame.Rect, uv_rect=None):
        x0, y0, x1, y1 = float(rect.left), float(rect.top), float(rect.right), float(rect.bottom)
        if uv_rect is None:
            u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
        else:
            u0, v0, u1, v1 = [float(v) for v in uv_rect]

        import struct
        return struct.pack(
            "24f",
            x0, y0, u0, v0,
            x1, y0, u1, v0,
            x0, y1, u0, v1,
            x1, y0, u1, v0,
            x1, y1, u1, v1,
            x0, y1, u0, v1,
        )

    @staticmethod
    def _borda_px(borda):
        if not isinstance(borda, dict):
            return (0.0, 0.0, 0.0, 0.0), 0.0
        c = borda.get("cor", (0, 0, 0, 0))
        w = borda.get("largura", 0)
        cor = (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, (c[3] if len(c) > 3 else 255) / 255.0)
        largura = max(0.0, float(w))
        return cor, largura

    def desenhar_textura(self, texture_id, rect, alpha: float = 1.0, uv_rect=None, radius=0, borda=None) -> None:
        if rect is None:
            return
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return

        textura = texture_id
        if isinstance(texture_id, str):
            return

        self._vbo.write(self._quad_data(rect, uv_rect=uv_rect))
        self._program_tex["u_resolution"].value = self._tamanho_tela
        self._program_tex["u_alpha"].value = max(0.0, min(1.0, float(alpha)))
        self._program_tex["u_rect_size"].value = (float(rect.width), float(rect.height))
        self._program_tex["u_radius_px"].value = max(0.0, float(radius))
        border_color, border_width = self._borda_px(borda)
        self._program_tex["u_border_color"].value = border_color
        self._program_tex["u_border_width_px"].value = border_width
        textura.use(0)
        self._vao_tex.render(moderngl.TRIANGLES)
        self.draw_calls_frame += 1

    def desenhar_surface_cacheada(self, chave: str, surface: pygame.Surface, rect, dirty: bool = False, alpha: float = 1.0, uv_rect=None, radius=0, borda=None, filtro: str = "smooth") -> None:
        textura = self._cache.obter_textura(chave, surface, dirty=bool(dirty), filtro=filtro)
        self.desenhar_textura(textura, rect, alpha=alpha, uv_rect=uv_rect, radius=radius, borda=borda)

    def registrar_shader_textura(self, chave_shader: str, fragment_shader: str, vertex_shader: str | None = None) -> None:
        chave = str(chave_shader or "").strip()
        if not chave:
            return
        if chave in self._custom_programs:
            return
        vert = vertex_shader or """
            #version 330
            in vec2 in_pos;
            in vec2 in_uv;
            out vec2 v_uv;
            uniform vec2 u_resolution;
            void main() {
                vec2 ndc = vec2((in_pos.x / u_resolution.x) * 2.0 - 1.0,
                                1.0 - (in_pos.y / u_resolution.y) * 2.0);
                gl_Position = vec4(ndc, 0.0, 1.0);
                v_uv = in_uv;
            }
        """
        program = self._ctx.program(vertex_shader=vert, fragment_shader=str(fragment_shader))
        vao = self._ctx.vertex_array(program, [(self._vbo, "2f 2f", "in_pos", "in_uv")])
        try:
            program["u_texture"] = 0
        except KeyError:
            pass
        self._custom_programs[chave] = {"program": program, "vao": vao}

    def possui_shader(self, chave_shader: str) -> bool:
        return str(chave_shader or "").strip() in self._custom_programs

    @staticmethod
    def _atribuir_uniform(programa, nome: str, valor) -> None:
        try:
            programa[nome].value = valor
        except Exception:
            return

    def desenhar_surface_com_shader(
        self,
        chave_shader: str,
        chave_textura: str,
        surface: pygame.Surface,
        rect,
        uniforms: dict | None = None,
        dirty: bool = False,
        uv_rect=None,
        filtro: str = "smooth",
    ) -> None:
        info = self._custom_programs.get(str(chave_shader or "").strip())
        if info is None:
            return
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return
        textura = self._cache.obter_textura(chave_textura, surface, dirty=bool(dirty), filtro=filtro)
        self._vbo.write(self._quad_data(rect))
        program = info["program"]
        vao = info["vao"]
        self._atribuir_uniform(program, "u_resolution", self._tamanho_tela)
        self._atribuir_uniform(program, "u_rect_size", (float(rect.width), float(rect.height)))
        for nome, valor in dict(uniforms or {}).items():
            self._atribuir_uniform(program, str(nome), valor)
        textura.use(0)
        vao.render(moderngl.TRIANGLES)
        self.draw_calls_frame += 1

    def desenhar_retangulo(self, rect, cor, radius=0, borda=None) -> None:
        rect = pygame.Rect(rect)
        if rect.width <= 0 or rect.height <= 0:
            return

        border_color, border_width = self._borda_px(borda)

        self._vbo.write(self._quad_data(rect))
        self._program_rect["u_resolution"].value = self._tamanho_tela
        self._program_rect["u_color"].value = (
            float(cor[0]) / 255.0,
            float(cor[1]) / 255.0,
            float(cor[2]) / 255.0,
            float((cor[3] if len(cor) > 3 else 255)) / 255.0,
        )
        self._program_rect["u_border_color"].value = border_color
        self._program_rect["u_rect_size"].value = (float(rect.width), float(rect.height))
        self._program_rect["u_radius_px"].value = max(0.0, float(radius))
        self._program_rect["u_border_width_px"].value = border_width
        self._vao_rect.render(moderngl.TRIANGLES)
        self.draw_calls_frame += 1

    def liberar(self) -> None:
        self._cache.liberar()
        for obj in (self._vao_tex, self._vao_rect, self._vbo, self._program_tex, self._program_rect):
            if obj is None:
                continue
            try:
                obj.release()
            except Exception:
                pass
        for info in self._custom_programs.values():
            try:
                info["vao"].release()
            except Exception:
                pass
            try:
                info["program"].release()
            except Exception:
                pass
        self._custom_programs.clear()
