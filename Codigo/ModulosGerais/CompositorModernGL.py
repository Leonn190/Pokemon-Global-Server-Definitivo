from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pygame

try:
    import moderngl
except ImportError:  # pragma: no cover - depende do ambiente do usuario
    moderngl = None


_QUAD_FULLSCREEN = (
    b"\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x80\x3f\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00"
    b"\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00\x00\x00\x80\x3f"
    b"\x00\x00\x80\x3f\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00"
    b"\x00\x00\x80\x3f\x00\x00\x80\x3f\x00\x00\x80\x3f\x00\x00\x80\x3f"
    b"\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00\x00\x00\x80\x3f"
)


class CompositorModernGL:
    def __init__(self) -> None:
        if moderngl is None:
            raise RuntimeError("moderngl indisponivel")

        base_dir = Path(__file__).resolve().parents[1] / "Outros" / "Shaders"
        vert_path = base_dir / "mundo.vert"
        frag_path = base_dir / "mundo.frag"
        if not vert_path.exists() or not frag_path.exists():
            raise FileNotFoundError("Arquivos de shader do mundo nao encontrados.")

        self._ctx = moderngl.create_context()
        self._ctx.disable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.disable(moderngl.BLEND)

        self._program = self._ctx.program(
            vertex_shader=vert_path.read_text(encoding="utf-8"),
            fragment_shader=frag_path.read_text(encoding="utf-8"),
        )
        self._quad = self._ctx.buffer(data=_QUAD_FULLSCREEN)
        self._vao = self._ctx.vertex_array(self._program, [(self._quad, "2f 2f", "in_pos", "in_uv")])
        self._scene_tex = None
        self._hud_tex = None
        self._size = (0, 0)
        self._compose_surface: pygame.Surface | None = None
        self._compose_surface_size = (0, 0)
        self._scene_upload_info = {"rapido": False, "swizzle": "RGBA"}
        self._hud_upload_info = {"rapido": False, "swizzle": "RGBA"}

        self._program["u_scene_tex"] = 0
        self._program["u_hud_tex"] = 1

    @staticmethod
    def disponivel() -> bool:
        return moderngl is not None

    @property
    def contexto(self):
        return self._ctx

    def _recriar_texturas(self, size: Tuple[int, int]) -> None:
        if self._scene_tex is not None:
            self._scene_tex.release()
        if self._hud_tex is not None:
            self._hud_tex.release()

        self._scene_tex = self._ctx.texture(size, 4)
        self._hud_tex = self._ctx.texture(size, 4)
        for textura in (self._scene_tex, self._hud_tex):
            textura.filter = (moderngl.LINEAR, moderngl.LINEAR)
            textura.repeat_x = False
            textura.repeat_y = False
        self._hud_tex.write(bytes(max(1, int(size[0])) * max(1, int(size[1])) * 4))
        self._size = size

    def _garantir_surface_composta(self, size: Tuple[int, int]) -> pygame.Surface:
        if self._compose_surface is None or self._compose_surface_size != size:
            self._compose_surface = pygame.Surface(size).convert()
            self._compose_surface_size = size
        return self._compose_surface

    @staticmethod
    def _detectar_upload(surface: pygame.Surface) -> Dict[str, object]:
        try:
            pitch = int(surface.get_pitch())
            largura = int(surface.get_width())
            bytesize = int(surface.get_bytesize())
            bitsize = int(surface.get_bitsize())
            masks = tuple(int(v) & 0xFFFFFFFF for v in surface.get_masks())
        except Exception:
            return {"rapido": False, "swizzle": "RGBA"}

        if bitsize != 32 or bytesize != 4 or pitch != (largura * bytesize):
            return {"rapido": False, "swizzle": "RGBA"}

        if masks[:4] == (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000):
            return {"rapido": True, "swizzle": "BGRA"}
        if masks[:4] == (0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000):
            return {"rapido": True, "swizzle": "BGR1"}
        if masks[:4] == (0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000):
            return {"rapido": True, "swizzle": "RGBA"}
        if masks[:4] == (0x000000FF, 0x0000FF00, 0x00FF0000, 0x00000000):
            return {"rapido": True, "swizzle": "RGB1"}
        return {"rapido": False, "swizzle": "RGBA"}

    def _upload_surface(self, texture, surface: pygame.Surface, info: Dict[str, object]) -> None:
        if bool(info.get("rapido", False)):
            texture.swizzle = str(info.get("swizzle", "RGBA") or "RGBA")
            texture.write(surface.get_view("1"))
            return
        texture.swizzle = "RGBA"
        texture.write(pygame.image.tobytes(surface, "RGBA", False))

    def _garantir_texturas(self, size: Tuple[int, int]) -> None:
        if self._scene_tex is None or self._hud_tex is None or self._size != size:
            self._recriar_texturas(size)

    @staticmethod
    def _clamp(v: float, a: float, b: float) -> float:
        return a if v < a else b if v > b else v

    def _uniform(self, nome: str, valor) -> None:
        try:
            self._program[nome].value = valor
        except KeyError:
            return

    def renderizar(self, scene_surface: pygame.Surface, hud_surface: pygame.Surface, efeito: Dict[str, object] | None, shader_ativo: bool) -> None:
        largura, altura = scene_surface.get_size()
        self._garantir_texturas((largura, altura))
        self._ctx.disable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.disable(moderngl.BLEND)

        dados = dict(efeito or {})
        player_uv = dados.get("player_uv", (0.5, 0.5))
        tint = dados.get("tint", (1.0, 1.0, 1.0))
        efeito_ativo = bool(shader_ativo and dados.get("tipo") == "mundo")
        scene_upload_surface = scene_surface
        hud_upload_surface = hud_surface if efeito_ativo else None
        if not efeito_ativo:
            composta = self._garantir_surface_composta((largura, altura))
            composta.blit(scene_surface, (0, 0))
            composta.blit(hud_surface, (0, 0))
            scene_upload_surface = composta

        self._scene_upload_info = self._detectar_upload(scene_upload_surface)
        if hud_upload_surface is not None:
            self._hud_upload_info = self._detectar_upload(hud_upload_surface)

        self._uniform("u_resolution", (float(largura), float(altura)))
        self._uniform("u_player_uv", (float(player_uv[0]), float(player_uv[1])))
        self._uniform("u_tint", (float(tint[0]), float(tint[1]), float(tint[2])))
        self._uniform("u_darkness", float(self._clamp(float(dados.get("darkness", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_rain_power", float(self._clamp(float(dados.get("rain_power", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_lightning", float(self._clamp(float(dados.get("lightning", 0.0) or 0.0), 0.0, 1.25)))
        self._uniform("u_star_strength", float(self._clamp(float(dados.get("star_strength", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_inside", 1.0 if bool(dados.get("inside", False)) else 0.0)
        self._uniform("u_time", float(dados.get("time", 0.0) or 0.0))
        self._uniform("u_biome_mode", float(dados.get("biome_mode", 0.0) or 0.0))
        self._uniform("u_biome_power", float(self._clamp(float(dados.get("biome_power", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_shader_enabled", 1.0 if efeito_ativo else 0.0)

        self._upload_surface(self._scene_tex, scene_upload_surface, self._scene_upload_info)
        if hud_upload_surface is not None:
            self._upload_surface(self._hud_tex, hud_upload_surface, self._hud_upload_info)

        self._ctx.clear(0.0, 0.0, 0.0, 1.0)
        self._scene_tex.use(0)
        self._hud_tex.use(1)
        self._vao.render(moderngl.TRIANGLES)

    def liberar(self) -> None:
        if self._scene_tex is not None:
            self._scene_tex.release()
            self._scene_tex = None
        if self._hud_tex is not None:
            self._hud_tex.release()
            self._hud_tex = None
        if self._vao is not None:
            self._vao.release()
            self._vao = None
        if self._quad is not None:
            self._quad.release()
            self._quad = None
        if self._program is not None:
            self._program.release()
            self._program = None
        if self._ctx is not None:
            self._ctx.release()
            self._ctx = None
        self._compose_surface = None
