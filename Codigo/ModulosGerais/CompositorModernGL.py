from __future__ import annotations

import re
import unicodedata
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
    """Compositor final de tela em ModernGL.

    O jogo ainda renderiza a cena e o HUD em surfaces do Pygame. Esta classe
    sobe essas duas surfaces como texturas e aplica um shader de tela inteira.
    Os arquivos GLSL ficam em ``Codigo/Visual/Shaders`` e podem usar includes simples.
    A pasta foi dividida em ``comum``, ``uniformes`` e ``efeitos`` para evitar
    um fragment shader gigante conforme novos efeitos surgirem.
    """

    _INCLUDE_RE = re.compile(r'^\s*#include\s+["<]([^">]+)[">]\s*$')
    _MODOS_EFEITO = {
        "": 0.0,
        "none": 0.0,
        "mundo": 1.0,
        "menu_logo": 2.0,
        "batalha": 3.0,
        "mapa": 4.0,
        "painel": 5.0,
        "hud": 5.0,
        "texto_cinematico": 5.0,
    }
    _MODELOS_ATAQUE = {
        "projetil": 1,
        "laser": 2,
        "raio": 3,
        "jato": 4,
        "explosao": 5,
        "avanco": 6,
        "salto": 6,
        "efeitoproprio": 7,
        "efeitoalvo": 7,
    }
    _TIPOS_ATAQUE = {
        "normal": 1,
        "fogo": 2,
        "agua": 3,
        "planta": 4,
        "eletrico": 5,
        "gelo": 6,
        "lutador": 7,
        "venenoso": 8,
        "veneno": 8,
        "terra": 9,
        "terrestre": 9,
        "voador": 10,
        "psiquico": 11,
        "inseto": 12,
        "pedra": 13,
        "fantasma": 14,
        "dragao": 15,
        "sombrio": 16,
        "metal": 17,
        "fada": 18,
        "cosmico": 19,
        "sonoro": 20,
        "fire": 2,
        "water": 3,
        "grass": 4,
        "electric": 5,
        "ice": 6,
        "fighting": 7,
        "poison": 8,
        "ground": 9,
        "flying": 10,
        "psychic": 11,
        "bug": 12,
        "rock": 13,
        "ghost": 14,
        "dragon": 15,
        "dark": 16,
        "steel": 17,
        "fairy": 18,
    }
    _TIPOS_AREA_BATALHA = {
        "destruido": 1,
        "queimado": 2,
        "envenenado": 3,
        "congelado": 4,
        "eletrificado": 5,
        "encharcado": 6,
        "amaldicoado": 7,
        "abencoado": 8,
    }

    def __init__(self) -> None:
        if moderngl is None:
            raise RuntimeError("moderngl indisponivel")

        base_dir = Path(__file__).resolve().parents[1] / "Visual" / "Shaders"
        vert_path = base_dir / "compositor.vert"
        frag_path = base_dir / "compositor.frag"
        if not vert_path.exists() or not frag_path.exists():
            raise FileNotFoundError("Arquivos de shader do compositor nao encontrados em Codigo/Visual/Shaders.")

        self._ctx = moderngl.create_context()
        self._ctx.disable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.disable(moderngl.BLEND)

        self._shader_dir = base_dir
        self._program = self._ctx.program(
            vertex_shader=self._ler_shader_com_includes(vert_path),
            fragment_shader=self._ler_shader_com_includes(frag_path),
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

    def _ler_shader_com_includes(self, path: Path, stack: tuple[Path, ...] = ()) -> str:
        path = path.resolve()
        if path in stack:
            ciclo = " -> ".join(p.name for p in (*stack, path))
            raise RuntimeError(f"Ciclo de #include em shaders: {ciclo}")
        if not path.exists():
            raise FileNotFoundError(str(path))

        partes: list[str] = []
        for linha in path.read_text(encoding="utf-8").splitlines():
            match = self._INCLUDE_RE.match(linha)
            if not match:
                partes.append(linha)
                continue
            rel = match.group(1).strip().replace("\\", "/")
            include_path = (path.parent / rel).resolve()
            if not include_path.exists():
                include_path = (self._shader_dir / rel).resolve()
            partes.append(f"// BEGIN_INCLUDE {rel}")
            partes.append(self._ler_shader_com_includes(include_path, (*stack, path)))
            partes.append(f"// END_INCLUDE {rel}")
        return "\n".join(partes) + "\n"

    @staticmethod
    def disponivel() -> bool:
        return moderngl is not None

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

    def _vec2(self, valor, padrao=(0.5, 0.5)) -> tuple[float, float]:
        try:
            if isinstance(valor, (list, tuple)) and len(valor) == 2:
                return (float(valor[0]), float(valor[1]))
        except Exception:
            pass
        return (float(padrao[0]), float(padrao[1]))

    def _vec3(self, valor, padrao=(1.0, 1.0, 1.0)) -> tuple[float, float, float]:
        try:
            if isinstance(valor, (list, tuple)) and len(valor) == 3:
                return (float(valor[0]), float(valor[1]), float(valor[2]))
        except Exception:
            pass
        return (float(padrao[0]), float(padrao[1]), float(padrao[2]))

    def _modo_efeito(self, tipo_efeito: str) -> float:
        return float(self._MODOS_EFEITO.get(str(tipo_efeito or "").strip().lower(), 0.0))

    @staticmethod
    def _chave_texto(valor) -> str:
        bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
        texto = "".join(ch for ch in bruto if not unicodedata.combining(ch))
        return "".join(ch for ch in texto if ch.isalnum())

    def _codigo_ataque(self, valor, mapa: dict[str, int]) -> int:
        try:
            return int(float(valor or 0))
        except (TypeError, ValueError):
            return int(mapa.get(self._chave_texto(valor), 0))

    def _aplicar_uniformes_estados_batalha(self, estados_batalha) -> None:
        # 12 alvos mantem custo baixo e cobre ate 6 Pokemon com 2 estados visuais fortes.
        max_estados = 12
        for i in range(max_estados):
            self._uniform(f"u_estado_batalha_{i}", (0.0, 0.0, 0.0, 0.0))
        if not isinstance(estados_batalha, list):
            return
        for i, item in enumerate(estados_batalha[:max_estados]):
            if not isinstance(item, dict):
                continue
            pos = self._vec2(item.get("pos_uv", item.get("uv", (0.5, 0.5))))
            try:
                raio = self._clamp(float(item.get("radius", item.get("raio", 0.0)) or 0.0), 0.0, 1.0)
                codigo = int(float(item.get("tipo", item.get("codigo", 0)) or 0))
                power = self._clamp(float(item.get("power", item.get("intensidade", 0.0)) or 0.0), 0.0, 1.0)
            except (TypeError, ValueError):
                continue
            if codigo <= 0 or raio <= 0.001 or power <= 0.001:
                continue
            codigo_power = float(codigo) + power * 0.1
            self._uniform(f"u_estado_batalha_{i}", (float(pos[0]), float(pos[1]), float(raio), float(codigo_power)))

    def _aplicar_uniformes_areas_batalha(self, areas_batalha) -> None:
        max_areas = 18
        for i in range(max_areas):
            self._uniform(f"u_area_batalha_{i}", (0.0, 0.0, 0.0, 0.0))
        if not isinstance(areas_batalha, list):
            return
        slot = 0
        for item in areas_batalha:
            if slot >= max_areas:
                break
            if not isinstance(item, dict):
                continue
            pos = self._vec2(item.get("pos_uv", item.get("uv", (0.5, 0.5))))
            try:
                raio = self._clamp(float(item.get("raio", item.get("radius", 0.0)) or 0.0), 0.0, 1.0)
                power = self._clamp(float(item.get("power", item.get("intensidade", 0.0)) or 0.0), 0.0, 1.0)
            except (TypeError, ValueError):
                continue
            try:
                codigo = int(float(item.get("codigo", 0) or 0))
            except (TypeError, ValueError):
                codigo = 0
            if codigo <= 0:
                codigo = int(self._TIPOS_AREA_BATALHA.get(self._chave_texto(item.get("tipo")), 0))
            if codigo <= 0 or raio <= 0.001 or power <= 0.001:
                continue
            codigo_power = float(codigo) + power * 0.1
            self._uniform(f"u_area_batalha_{slot}", (float(pos[0]), float(pos[1]), float(raio), float(codigo_power)))
            slot += 1

    def _cor_rgb_normalizada(self, valor, padrao=(1.0, 1.0, 1.0)) -> tuple[float, float, float, float]:
        try:
            if isinstance(valor, (list, tuple)) and len(valor) >= 3:
                r = float(valor[0])
                g = float(valor[1])
                b = float(valor[2])
                if max(r, g, b) > 1.0:
                    r, g, b = r / 255.0, g / 255.0, b / 255.0
                return (
                    float(self._clamp(r, 0.0, 1.0)),
                    float(self._clamp(g, 0.0, 1.0)),
                    float(self._clamp(b, 0.0, 1.0)),
                    1.0,
                )
        except Exception:
            pass
        return (float(padrao[0]), float(padrao[1]), float(padrao[2]), 0.0)

    def _aplicar_uniformes_ataques_batalha(self, ataques_batalha) -> None:
        max_ataques = 8
        for i in range(max_ataques):
            self._uniform(f"u_attack_fx_{i}_pos", (0.0, 0.0, 0.0, 0.0))
            self._uniform(f"u_attack_fx_{i}_data", (0.0, 0.0, 0.0, 0.0))
            self._uniform(f"u_attack_fx_{i}_extra", (0.0, 0.0, 0.0, 0.0))
            self._uniform(f"u_attack_fx_{i}_color", (0.0, 0.0, 0.0, 0.0))
        if not isinstance(ataques_batalha, list):
            return
        slot = 0
        for item in ataques_batalha:
            if slot >= max_ataques:
                break
            if not isinstance(item, dict):
                continue
            origem = self._vec2(item.get("origem_uv", item.get("origem", (0.5, 0.5))))
            alvo = self._vec2(item.get("alvo_uv", item.get("alvo", (0.5, 0.5))))
            try:
                modelo = self._codigo_ataque(item.get("modelo_codigo", item.get("modelo", 0)), self._MODELOS_ATAQUE)
                tipo = self._codigo_ataque(item.get("tipo_codigo", item.get("tipo", 0)), self._TIPOS_ATAQUE)
                fase = self._clamp(float(item.get("fase", 0.0) or 0.0), 0.0, 1.0)
                power = self._clamp(float(item.get("power", item.get("intensidade", 0.0)) or 0.0), 0.0, 1.5)
                raio = self._clamp(float(item.get("raio", item.get("radius", 0.055)) or 0.055), 0.004, 0.35)
                largura = self._clamp(float(item.get("largura", item.get("width", 1.0)) or 1.0), 0.20, 4.0)
                seed = float(item.get("seed", 0.0) or 0.0) % 1.0
                impacto_power = self._clamp(float(item.get("impacto_power", item.get("impacto", 0.0)) or 0.0), 0.0, 1.0)
            except (TypeError, ValueError):
                continue
            if modelo <= 0 or power <= 0.001:
                continue
            cor = self._cor_rgb_normalizada(item.get("cor", item.get("color")))
            self._uniform(f"u_attack_fx_{slot}_pos", (float(origem[0]), float(origem[1]), float(alvo[0]), float(alvo[1])))
            self._uniform(f"u_attack_fx_{slot}_data", (float(modelo), float(max(0, tipo)), float(fase), float(self._clamp(power, 0.0, 1.0))))
            self._uniform(f"u_attack_fx_{slot}_extra", (float(raio), float(largura), float(seed), float(impacto_power)))
            self._uniform(f"u_attack_fx_{slot}_color", cor)
            slot += 1

    def renderizar(self, scene_surface: pygame.Surface, hud_surface: pygame.Surface, efeito: Dict[str, object] | None, shader_ativo: bool) -> None:
        largura, altura = scene_surface.get_size()
        self._garantir_texturas((largura, altura))

        dados = dict(efeito or {})
        player_uv = self._vec2(dados.get("player_uv", (0.5, 0.5)))
        tint = self._vec3(dados.get("tint", (1.0, 1.0, 1.0)))
        tipo_efeito = str(dados.get("tipo") or "").strip().lower()
        modo_efeito = self._modo_efeito(tipo_efeito)
        captura_power = self._clamp(float(dados.get("capture_power", dados.get("captura_power", 0.0)) or 0.0), 0.0, 1.0)
        texto_cinematico_power = self._clamp(float(dados.get("texto_cinematico_power", 0.0) or 0.0), 0.0, 1.0)
        dungeon_power = self._clamp(float(dados.get("dungeon_power", 0.0) or 0.0), 0.0, 1.0)
        estados_batalha = list(dados.get("battle_status_targets", dados.get("estados_batalha_shader", [])) or [])
        areas_batalha = list(dados.get("battle_area_fx", dados.get("areas_batalha_shader", [])) or [])
        ataques_batalha = list(dados.get("battle_attack_fx", dados.get("ataques_batalha_shader", [])) or [])
        estados_batalha_ativos = False
        for item in estados_batalha:
            if not isinstance(item, dict):
                continue
            try:
                if float(item.get("power", item.get("intensidade", 0.0)) or 0.0) > 0.001:
                    estados_batalha_ativos = True
                    break
            except (TypeError, ValueError):
                continue
        areas_batalha_ativas = False
        for item in areas_batalha:
            if not isinstance(item, dict):
                continue
            try:
                if float(item.get("power", item.get("intensidade", 0.0)) or 0.0) > 0.001:
                    areas_batalha_ativas = True
                    break
            except (TypeError, ValueError):
                continue
        ataques_batalha_ativos = False
        for item in ataques_batalha:
            if not isinstance(item, dict):
                continue
            try:
                if float(item.get("power", item.get("intensidade", 0.0)) or 0.0) > 0.001:
                    ataques_batalha_ativos = True
                    break
            except (TypeError, ValueError):
                continue
        efeito_ativo = bool(
            shader_ativo
            and (
                modo_efeito in (1.0, 2.0, 4.0, 5.0)
                or (modo_efeito == 3.0 and bool(dados.get("ativo", True)))
                or captura_power > 0.001
                or texto_cinematico_power > 0.001
                or dungeon_power > 0.001
                or estados_batalha_ativos
                or areas_batalha_ativas
                or ataques_batalha_ativos
            )
        )
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
        self._uniform("u_effect_mode", float(modo_efeito))
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
        self._uniform("u_dungeon_power", float(dungeon_power))
        self._uniform("u_dungeon_darkness", float(self._clamp(float(dados.get("dungeon_darkness", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_battle_sun_power", float(self._clamp(float(dados.get("battle_sun_power", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_battle_sand_power", float(self._clamp(float(dados.get("battle_sand_power", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_battle_fog_power", float(self._clamp(float(dados.get("battle_fog_power", 0.0) or 0.0), 0.0, 1.0)))
        self._uniform("u_battle_acid_power", float(self._clamp(float(dados.get("battle_acid_power", 0.0) or 0.0), 0.0, 1.0)))
        self._aplicar_uniformes_areas_batalha(areas_batalha)
        self._aplicar_uniformes_estados_batalha(estados_batalha)
        self._aplicar_uniformes_ataques_batalha(ataques_batalha)

        menu_logo_rect = dados.get("menu_logo_rect", (0.0, 0.0, 0.0, 0.0))
        try:
            menu_logo_rect = tuple(float(v) for v in menu_logo_rect)
        except Exception:
            menu_logo_rect = (0.0, 0.0, 0.0, 0.0)
        if len(menu_logo_rect) != 4:
            menu_logo_rect = (0.0, 0.0, 0.0, 0.0)
        self._uniform("u_menu_logo_rect", menu_logo_rect)
        self._uniform("u_menu_logo_power", float(self._clamp(float(dados.get("menu_logo_power", 0.0) or 0.0), 0.0, 1.0)))

        texto_cinematico_rect = dados.get("texto_cinematico_rect", (0.0, 0.0, 0.0, 0.0))
        try:
            texto_cinematico_rect = tuple(float(v) for v in texto_cinematico_rect)
        except Exception:
            texto_cinematico_rect = (0.0, 0.0, 0.0, 0.0)
        if len(texto_cinematico_rect) != 4:
            texto_cinematico_rect = (0.0, 0.0, 0.0, 0.0)
        self._uniform("u_texto_cinematico_rect", texto_cinematico_rect)
        self._uniform("u_texto_cinematico_power", float(texto_cinematico_power))
        self._uniform("u_texto_cinematico_modo", float(dados.get("texto_cinematico_modo", 0.0) or 0.0))

        capture_uv = self._vec2(dados.get("capture_uv", dados.get("captura_uv", (0.5, 0.5))))
        self._uniform("u_capture_uv", (float(capture_uv[0]), float(capture_uv[1])))
        self._uniform("u_capture_power", float(captura_power))
        self._uniform("u_capture_phase", float(dados.get("capture_phase", dados.get("captura_phase", 0.0)) or 0.0))
        self._uniform("u_capture_result", float(dados.get("capture_result", dados.get("captura_result", -1.0)) if dados.get("capture_result", dados.get("captura_result", -1.0)) is not None else -1.0))
        self._uniform("u_capture_critical", float(self._clamp(float(dados.get("capture_critical", dados.get("captura_critical", 0.0)) or 0.0), 0.0, 1.0)))
        self._uniform("u_capture_check_index", float(dados.get("capture_check_index", dados.get("captura_check_index", 0.0)) or 0.0))
        self._uniform("u_capture_check_count", float(max(1.0, float(dados.get("capture_check_count", dados.get("captura_check_count", 3.0)) or 3.0))))
        self._uniform("u_capture_token_hash", float(self._clamp(float(dados.get("capture_token_hash", dados.get("captura_token_hash", 0.0)) or 0.0), 0.0, 1.0)))
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
