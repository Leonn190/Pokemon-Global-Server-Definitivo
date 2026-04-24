from __future__ import annotations
# LEGADO TEMPORÁRIO — não é contrato do novo modelo de batalha.

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import pygame
except ModuleNotFoundError:  # pragma: no cover - fallback para o simulador/headless.
    pygame = None


class _Vec2Fallback:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        if isinstance(x, (tuple, list)) and len(x) >= 2:
            self.x = float(x[0])
            self.y = float(x[1])
        elif hasattr(x, "x") and hasattr(x, "y") and y == 0.0:
            self.x = float(getattr(x, "x"))
            self.y = float(getattr(x, "y"))
        else:
            self.x = float(x)
            self.y = float(y)

    def __add__(self, other):
        return self.__class__(self.x + float(other.x), self.y + float(other.y))

    def __sub__(self, other):
        return self.__class__(self.x - float(other.x), self.y - float(other.y))

    def __mul__(self, escalar):
        return self.__class__(self.x * float(escalar), self.y * float(escalar))

    def __rmul__(self, escalar):
        return self.__mul__(escalar)

    def __truediv__(self, escalar):
        valor = float(escalar) or 1.0
        return self.__class__(self.x / valor, self.y / valor)

    def __neg__(self):
        return self.__class__(-self.x, -self.y)

    def length_squared(self) -> float:
        return (self.x * self.x) + (self.y * self.y)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalize(self):
        tamanho = self.length()
        if tamanho <= 1e-9:
            return self.__class__(1.0, 0.0)
        return self / tamanho

    def dot(self, other) -> float:
        return (self.x * float(other.x)) + (self.y * float(other.y))

    def lerp(self, other, t: float):
        return self.__class__(
            self.x + (float(other.x) - self.x) * float(t),
            self.y + (float(other.y) - self.y) * float(t),
        )


Vec2 = pygame.math.Vector2 if pygame is not None else _Vec2Fallback


class LeitorFluxos:
    def __init__(self) -> None:
        self._tempo = 0.0
        self._fluxos = self._carregar_fluxos()
        self._tile_px = 42.0

    def atualizar(self, dt: float) -> None:
        self._tempo += max(0.0, float(dt))

    @staticmethod
    def _safe_float(valor, padrao=0.0) -> float:
        try:
            if valor in (None, ""):
                return float(padrao)
            return float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            return float(padrao)

    @staticmethod
    def _safe_bool(valor, padrao: bool = False) -> bool:
        if isinstance(valor, bool):
            return valor
        if valor in (None, ""):
            return bool(padrao)
        texto = str(valor).strip().casefold()
        if texto in {"1", "true", "verdadeiro", "sim", "yes", "on"}:
            return True
        if texto in {"0", "false", "falso", "nao", "não", "no", "off"}:
            return False
        return bool(valor)

    @staticmethod
    def _clamp(valor: float, minimo: float, maximo: float) -> float:
        return max(minimo, min(maximo, valor))

    @staticmethod
    def _normalizar_nome(valor: object) -> str:
        return str(valor or "").strip().casefold()

    @classmethod
    def _arquivo_fluxos(cls) -> Optional[Path]:
        atual = Path(__file__).resolve()
        candidatos = [
            atual.parents[2] / "Dados" / "Pokemon Global Server - Fluxos.json",
            Path("Dados") / "Pokemon Global Server - Fluxos.json",
        ]
        for caminho in candidatos:
            if caminho.exists():
                return caminho
        return None

    def _carregar_fluxos(self) -> Dict[str, Dict[str, object]]:
        caminho = self._arquivo_fluxos()
        if caminho is None:
            return {}
        try:
            bruto = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        fluxos = bruto.get("fluxos") if isinstance(bruto, dict) else {}
        if not isinstance(fluxos, dict):
            return {}
        saida: Dict[str, Dict[str, object]] = {}
        for nome, dados in fluxos.items():
            if not isinstance(dados, dict):
                continue
            saida[self._normalizar_nome(nome)] = dict(dados)
        return saida

    def obter_fluxo(self, ataque: object) -> Dict[str, object]:
        if isinstance(ataque, dict) and isinstance(ataque.get("fluxos"), list):
            return dict(ataque)
        if isinstance(ataque, dict):
            nome = ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome")
        else:
            nome = ataque
        return dict(self._fluxos.get(self._normalizar_nome(nome), {}))

    @staticmethod
    def _safe_normalize(vetor: Vec2) -> Vec2:
        if vetor.length_squared() <= 1e-9:
            return Vec2(1, 0)
        return vetor.normalize()

    @staticmethod
    def _desenhar_poligono(area: pygame.Surface, pontos: Iterable[Vec2], cor_fill, cor_borda, largura_borda: int = 2) -> None:
        if pygame is None:
            return
        pts = [(float(pt.x), float(pt.y)) for pt in pontos]
        if len(pts) < 3:
            return
        pygame.draw.polygon(area, cor_fill, pts)
        pygame.draw.polygon(area, cor_borda, pts, max(1, int(largura_borda)))

    def point_in_polygon(self, point: Vec2, polygon: List[Vec2]) -> bool:
        if len(polygon) < 3:
            return False
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i].x, polygon[i].y
            xj, yj = polygon[j].x, polygon[j].y
            if (yi > point.y) != (yj > point.y):
                x_cross = (xj - xi) * (point.y - yi) / ((yj - yi) or 1e-8) + xi
                if point.x < x_cross:
                    inside = not inside
            j = i
        return inside

    def circle_samples(self, center_px: Vec2, radius_px: float) -> List[Vec2]:
        pts = [center_px]
        for ang in range(0, 360, 24):
            rad = math.radians(ang)
            for mul in (0.48, 0.82, 1.0):
                pts.append(center_px + Vec2(math.cos(rad), math.sin(rad)) * radius_px * mul)
        return pts

    def point_hit_circle_shape(self, point_px: Vec2, center_px: Vec2, radius_px: float, flow: Dict[str, object]) -> bool:
        dist = (point_px - center_px).length()
        shape = str(flow.get("shape") or "normal").strip().casefold() or "normal"
        if shape == "normal":
            return dist <= radius_px
        count = max(1, int(self._safe_float(flow.get("quantidade_elementos"), 0)))
        elem = max(0.0, self._safe_float(flow.get("tamanho_elementos"), 0.0)) * self._tile_px
        if count <= 0 or elem <= 0.0:
            return dist <= radius_px
        ang = math.atan2(point_px.y - center_px.y, point_px.x - center_px.x)
        wave = 0.5 * (1.0 + math.cos(ang * count))
        mod = wave if shape == "espinhos" else wave * 0.55
        return dist <= (radius_px + elem * mod)

    @staticmethod
    def _vec2(valor, default=(0.0, 0.0)) -> Vec2:
        if isinstance(valor, (tuple, list)) and len(valor) >= 2:
            return Vec2(float(valor[0]), float(valor[1]))
        if hasattr(valor, "x") and hasattr(valor, "y"):
            return Vec2(float(getattr(valor, "x", 0.0)), float(getattr(valor, "y", 0.0)))
        return Vec2(float(default[0]), float(default[1]))

    def _normalizar_paredes(self, paredes: Optional[Iterable[object]]) -> List[Tuple[Vec2, Vec2]]:
        saida: List[Tuple[Vec2, Vec2]] = []
        for parede in list(paredes or []):
            a = b = None
            if isinstance(parede, dict):
                a = parede.get("a") or parede.get("inicio") or parede.get("from")
                b = parede.get("b") or parede.get("fim") or parede.get("to")
            elif isinstance(parede, (tuple, list)) and len(parede) >= 2:
                a, b = parede[0], parede[1]
            if a is None or b is None:
                continue
            a_v = self._vec2(a)
            b_v = self._vec2(b)
            if (b_v - a_v).length_squared() <= 1e-9:
                continue
            saida.append((a_v, b_v))
        return saida

    def _normalizar_pokemons(
        self,
        pokemons: Optional[Iterable[object]],
        *,
        ignorar_ids: Optional[Iterable[object]] = None,
    ) -> List[Dict[str, object]]:
        ignorados = {str(valor) for valor in list(ignorar_ids or []) if str(valor)}
        saida: List[Dict[str, object]] = []
        for indice, pokemon in enumerate(list(pokemons or [])):
            bruto_id = indice
            posicao = None
            raio_tiles = None
            if isinstance(pokemon, dict):
                bruto_id = pokemon.get("id") or pokemon.get("uid") or pokemon.get("pokemon_id") or indice
                posicao = pokemon.get("pos") or pokemon.get("posicao") or pokemon.get("centro")
                raio_tiles = (
                    pokemon.get("raio_tiles")
                    if pokemon.get("raio_tiles") is not None
                    else pokemon.get("raio")
                )
            else:
                bruto_id = getattr(pokemon, "Uid", None) or getattr(pokemon, "id", None) or indice
                posicao = getattr(pokemon, "Posicao", None) or getattr(pokemon, "pos", None)
                raio_tiles = getattr(pokemon, "RaioColisao", None) or getattr(pokemon, "radius_tiles", None)
            if posicao is None:
                continue
            pokemon_id = str(bruto_id)
            if pokemon_id in ignorados:
                continue
            saida.append(
                {
                    "id": pokemon_id,
                    "pos": self._vec2(posicao),
                    "raio_tiles": max(0.0, self._safe_float(raio_tiles, 0.0)),
                }
            )
        return saida

    def segment_intersection(self, ray_start: Vec2, ray_dir: Vec2, max_len_px: float, a: Vec2, b: Vec2):
        p = ray_start
        r = ray_dir * max_len_px
        q = a
        s = b - a
        den = r.x * s.y - r.y * s.x
        if abs(den) < 1e-8:
            return None
        qp = q - p
        t = (qp.x * s.y - qp.y * s.x) / den
        u = (qp.x * r.y - qp.y * r.x) / den
        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            hit_px = p + r * t
            wall_dir = b - a
            if wall_dir.length_squared() <= 1e-8:
                return None
            normal = Vec2(-wall_dir.y, wall_dir.x).normalize()
            if normal.dot(ray_dir) > 0:
                normal *= -1
            return max_len_px * t, hit_px, normal
        return None

    def ray_circle_hit(self, ray_start: Vec2, ray_dir: Vec2, max_len_px: float, center_px: Vec2, radius_px: float):
        m = ray_start - center_px
        b = m.dot(ray_dir)
        c = m.dot(m) - radius_px * radius_px
        if c > 0.0 and b > 0.0:
            return None
        disc = b * b - c
        if disc < 0.0:
            return None
        t = -b - math.sqrt(disc)
        if t < 0.0:
            t = 0.0
        if t > max_len_px:
            return None
        hit_px = ray_start + ray_dir * t
        normal = hit_px - center_px
        if normal.length_squared() <= 1e-8:
            return None
        return t, hit_px, normal.normalize()

    def reflect(self, direction: Vec2, normal: Vec2) -> Vec2:
        normal_n = self._safe_normalize(normal)
        return direction - 2.0 * direction.dot(normal_n) * normal_n

    def _pacote_fluxo(self, ataque: object) -> Dict[str, object]:
        pacote = self.obter_fluxo(ataque)
        if pacote:
            return pacote
        if isinstance(ataque, dict):
            return dict(ataque)
        return {}

    def _fonte_radius_tiles(self, pacote: Dict[str, object], source_radius_tiles: Optional[float]) -> float:
        if source_radius_tiles is not None:
            return max(0.1, float(source_radius_tiles))
        diametro = self._safe_float(pacote.get("test_diameter"), 1.5)
        return max(0.1, diametro * 0.5)

    def _fluxos_topo(self, pacote: Dict[str, object]) -> List[Dict[str, object]]:
        fluxos = [dict(item) for item in list(pacote.get("fluxos") or []) if isinstance(item, dict)]
        if fluxos:
            return fluxos
        if any(chave in pacote for chave in ("alcance", "largura_base", "largura_teto", "circular", "raio")):
            return [dict(pacote)]
        return []

    def compute_effective_range_tiles(
        self,
        flow: Dict[str, object],
        source_center_px: Vec2,
        mouse_px: Vec2,
        source_radius_tiles: float,
        is_subflow: bool,
        override_range_tiles: Optional[float] = None,
    ) -> float:
        if override_range_tiles is not None:
            alcance = max(0.10, float(override_range_tiles))
            if is_subflow or not self._safe_bool(flow.get("ajustavel"), False):
                return alcance
            minimo = max(0.10, self._safe_float(flow.get("alcance_min"), alcance))
            maximo = max(minimo, self._safe_float(flow.get("alcance_max"), alcance))
            return self._clamp(alcance, minimo, maximo)
        if is_subflow or not self._safe_bool(flow.get("ajustavel"), False):
            return max(0.10, self._safe_float(flow.get("alcance"), 4.0))
        minimo = max(0.10, self._safe_float(flow.get("alcance_min"), 1.0))
        maximo = max(minimo, self._safe_float(flow.get("alcance_max"), minimo))
        mouse_dist_tiles = max(0.0, (mouse_px - source_center_px).length() / self._tile_px - source_radius_tiles)
        return self._clamp(mouse_dist_tiles, minimo, maximo)

    def scaled_factor(self, flow: Dict[str, object], source_radius_tiles: float) -> float:
        if not self._safe_bool(flow.get("escalonavel"), False):
            return 1.0
        return 1.0 + max(0.0, (source_radius_tiles * 2.0) - 1.5) * 0.08

    def exit_direction(self, aim_dir: Vec2, flow: Dict[str, object]) -> Vec2:
        offset_value = self._safe_float(flow.get("offset"), 0.0)
        if abs(offset_value) <= 1e-9 or not self._safe_bool(flow.get("grudado"), False):
            return aim_dir
        base_ang = math.atan2(aim_dir.y, aim_dir.x)
        ang = math.radians(offset_value)
        return Vec2(math.cos(base_ang + ang), math.sin(base_ang + ang))

    def base_start(self, center_px: Vec2, aim_dir: Vec2, flow: Dict[str, object], source_radius_tiles: float) -> Tuple[Vec2, Vec2, Vec2]:
        exit_dir = self.exit_direction(aim_dir, flow)
        perp = Vec2(-exit_dir.y, exit_dir.x)
        spacing_tiles = self._safe_float(flow.get("espacamento"), 0.0)
        offset_tiles = self._safe_float(flow.get("offset"), 0.0)
        if self._safe_bool(flow.get("grudado"), False):
            start_center = center_px + exit_dir * (source_radius_tiles * self._tile_px)
        else:
            start_center = center_px + exit_dir * ((source_radius_tiles + spacing_tiles) * self._tile_px) + perp * (offset_tiles * self._tile_px)
        return start_center, exit_dir, perp

    def width_profile_tiles(self, flow: Dict[str, object], total_len_tiles: float) -> Tuple[List[float], List[float]]:
        total_len_tiles = max(0.10, total_len_tiles)
        base = max(0.0, self._safe_float(flow.get("largura_base"), 0.0))
        teto = max(0.0, self._safe_float(flow.get("largura_teto"), 0.0))
        dists = [0.0, total_len_tiles]
        widths = [base, teto]
        faixas = max(0, int(self._safe_float(flow.get("faixas"), 0)))
        if faixas <= 0:
            return dists, widths
        largura_faixa = max(0.0, self._safe_float(flow.get("largura_faixa"), teto))
        repeticao = self._safe_bool(flow.get("repeticao_faixas"), True)
        ciclico = self._safe_bool(flow.get("faixas_ciclicas"), False)
        if ciclico:
            step = max(0.10, self._safe_float(flow.get("distancia_faixa"), 1.0))
            pos = step
            toggle = True
            dists = [0.0]
            widths = [base]
            while pos < total_len_tiles - 1e-6:
                dists.append(pos)
                widths.append(teto if toggle else largura_faixa)
                toggle = not toggle
                pos += step
            dists.append(total_len_tiles)
            widths.append(teto if len(widths) % 2 == 1 else largura_faixa)
            return dists, widths
        segments = faixas + 2
        step = total_len_tiles / max(1, segments - 1)
        dists = [i * step for i in range(segments)]
        widths = [base, teto]
        if repeticao:
            use_teto = False
            for _ in range(faixas):
                widths.append(teto if use_teto else largura_faixa)
                use_teto = not use_teto
        else:
            widths.extend([largura_faixa for _ in range(faixas)])
        return dists, widths[: len(dists)]

    def curvature_anchors(self, flow: Dict[str, object], total_len_tiles: float) -> Tuple[List[float], List[float]]:
        total_len_tiles = max(0.10, total_len_tiles)
        points_n = max(0, int(self._safe_float(flow.get("pontos_curvatura"), 0)))
        cyclic = self._safe_bool(flow.get("curvaturas_ciclicas"), False)
        invertido = self._safe_bool(flow.get("invertido"), True)
        vals = [self._safe_float(flow.get(f"curvatura_{i}"), 0.0) for i in range(1, 7)]
        positions: List[float] = []
        offsets: List[float] = []
        if cyclic:
            step = max(0.10, self._safe_float(flow.get("distancia_entre_curvaturas"), 1.0))
            pos = step
            idx = 0
            while pos < total_len_tiles + 1e-6 and len(positions) < 24:
                base = vals[idx % max(1, points_n if points_n > 0 else 1)] if points_n > 0 else vals[0]
                if invertido and idx % 2 == 1:
                    base = -base
                positions.append(pos)
                offsets.append(base)
                pos += step
                idx += 1
            return positions, offsets
        if points_n <= 0:
            return positions, offsets
        step = total_len_tiles / max(1, points_n + 1)
        for i in range(points_n):
            positions.append(step * (i + 1))
            offsets.append(vals[i])
        return positions, offsets

    def catmull_rom(self, points: List[Vec2], segments_per_edge: int = 10) -> List[Vec2]:
        if len(points) < 2:
            return points[:]
        out = [points[0]]
        ext = [points[0]] + points + [points[-1]]
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            for j in range(1, segments_per_edge + 1):
                t = j / float(segments_per_edge)
                t2 = t * t
                t3 = t2 * t
                point = 0.5 * (
                    (2 * p1)
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
                )
                out.append(point)
        return out

    def build_centerline(
        self,
        flow: Dict[str, object],
        center_px: Vec2,
        mouse_px: Vec2,
        source_radius_tiles: float,
        is_subflow: bool,
        override_range_tiles: Optional[float] = None,
    ) -> Tuple[List[Vec2], List[float], float, Vec2, Vec2]:
        aim_dir = self._safe_normalize(mouse_px - center_px)
        total_len_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow, override_range_tiles=override_range_tiles)
        scale = self.scaled_factor(flow, source_radius_tiles)
        total_len_tiles *= scale
        start_center_px, axis_dir, perp = self.base_start(center_px, aim_dir, flow, source_radius_tiles)
        dists_nodes, widths_nodes = self.width_profile_tiles(flow, total_len_tiles)
        curvature_pos, curvature_vals = self.curvature_anchors(flow, total_len_tiles)
        anchor_map = {0.0: 0.0, total_len_tiles: 0.0}
        for dist, curv in zip(curvature_pos, curvature_vals):
            anchor_map[self._clamp(dist, 0.0, total_len_tiles)] = curv * scale
        anchor_keys = sorted(anchor_map.keys())
        anchor_points = [start_center_px + axis_dir * (dist * self._tile_px) + perp * (anchor_map[dist] * self._tile_px) for dist in anchor_keys]
        if self._safe_bool(flow.get("curvatura_circular"), True) and len(anchor_points) >= 3:
            smooth = self.catmull_rom(anchor_points, 10)
        else:
            smooth: List[Vec2] = []
            for idx in range(len(anchor_points) - 1):
                a = anchor_points[idx]
                b = anchor_points[idx + 1]
                steps = max(2, int((b - a).length() / max(6.0, self._tile_px * 0.25)))
                for step in range(steps):
                    smooth.append(a.lerp(b, step / float(steps)))
            smooth.append(anchor_points[-1])
        if len(smooth) < 2:
            smooth = [start_center_px, start_center_px + axis_dir * (total_len_tiles * self._tile_px)]
        widths_px: List[float] = []
        cumulative_tiles = [0.0]
        total_px_len = 0.0
        for idx in range(1, len(smooth)):
            total_px_len += (smooth[idx] - smooth[idx - 1]).length()
            cumulative_tiles.append(total_px_len / self._tile_px)
        haste = str(flow.get("hastes") or "reto").strip().casefold() or "reto"
        for dist in cumulative_tiles:
            idx = 0
            while idx < len(dists_nodes) - 1 and dist > dists_nodes[idx + 1]:
                idx += 1
            if idx >= len(dists_nodes) - 1:
                width = widths_nodes[-1]
            else:
                a_d, b_d = dists_nodes[idx], dists_nodes[idx + 1]
                a_w, b_w = widths_nodes[idx], widths_nodes[idx + 1]
                interp = 0.0 if abs(b_d - a_d) < 1e-8 else (dist - a_d) / (b_d - a_d)
                if haste == "concavo":
                    interp = 1 - (1 - interp) * (1 - interp)
                elif haste == "convexo":
                    interp = interp * interp
                width = a_w + (b_w - a_w) * interp
            widths_px.append(max(0.0, width * self._tile_px * scale))
        return smooth, widths_px, total_len_tiles, axis_dir, start_center_px

    def polygon_from_centerline(self, points: List[Vec2], widths_px: List[float], source_center_px: Vec2, source_radius_tiles: float, flow: Dict[str, object], axis_dir: Vec2) -> List[Vec2]:
        if len(points) < 2:
            return []
        if self._safe_bool(flow.get("grudado"), False):
            src_r_px = source_radius_tiles * self._tile_px
            outer_r_px = max(src_r_px, max((point - source_center_px).length() for point in points))
            center_ang = math.atan2(axis_dir.y, axis_dir.x)
            base_half_ang = min(math.tau * 0.5 - 1e-6, math.radians(max(0.0, self._safe_float(flow.get("largura_base"), 0.0)) * 0.5))
            teto_half_ang = min(math.tau * 0.5 - 1e-6, math.radians(max(0.0, self._safe_float(flow.get("largura_teto"), 0.0)) * 0.5))
            outer_samples = max(1, int(max(1e-6, teto_half_ang) * 18))
            inner_samples = max(1, int(max(1e-6, base_half_ang) * 18))
            outer_pts = []
            for idx in range(outer_samples + 1):
                interp = idx / float(outer_samples)
                ang = center_ang + teto_half_ang - 2.0 * teto_half_ang * interp
                outer_pts.append(source_center_px + Vec2(math.cos(ang), math.sin(ang)) * outer_r_px)
            inner_pts = []
            for idx in range(inner_samples + 1):
                interp = idx / float(inner_samples)
                ang = center_ang - base_half_ang + 2.0 * base_half_ang * interp
                inner_pts.append(source_center_px + Vec2(math.cos(ang), math.sin(ang)) * src_r_px)
            return outer_pts + inner_pts
        left: List[Vec2] = []
        right: List[Vec2] = []
        for idx, point in enumerate(points):
            if idx == 0:
                tangent = points[idx + 1] - points[idx]
            elif idx == len(points) - 1:
                tangent = points[idx] - points[idx - 1]
            else:
                tangent = points[idx + 1] - points[idx - 1]
            tangent = self._safe_normalize(tangent)
            normal = Vec2(-tangent.y, tangent.x)
            half = widths_px[idx] * 0.5
            left.append(point + normal * half)
            right.append(point - normal * half)
        return left + list(reversed(right))

    def circle_outline(self, center_px: Vec2, radius_px: float, flow: Dict[str, object]) -> List[Vec2]:
        shape = str(flow.get("shape") or "normal").strip().casefold() or "normal"
        elementos = max(1, int(self._safe_float(flow.get("quantidade_elementos"), 1)))
        count = max(24, elementos * 6 if shape != "normal" else 48)
        elem_px = max(0.0, self._safe_float(flow.get("tamanho_elementos"), 0.0)) * self._tile_px
        pts = []
        for idx in range(count):
            ang = (math.tau * idx) / count
            raio = radius_px
            if shape != "normal" and elem_px > 0.0:
                wave = 0.5 * (1.0 + math.cos(ang * elementos))
                raio += elem_px * wave if shape == "espinhos" else elem_px * wave * 0.55
            pts.append(center_px + Vec2(math.cos(ang), math.sin(ang)) * raio)
        return pts

    def visible_circle_center(
        self,
        center_px: Vec2,
        mouse_px: Vec2,
        source_radius_tiles: float,
        flow: Dict[str, object],
        is_subflow: bool,
        override_range_tiles: Optional[float] = None,
        override_circle_radius_tiles: Optional[float] = None,
    ) -> Tuple[Vec2, float, Vec2]:
        aim_dir = self._safe_normalize(mouse_px - center_px)
        exit_dir = self.exit_direction(aim_dir, flow)
        scale = self.scaled_factor(flow, source_radius_tiles)
        radius_tiles = self._safe_float(flow.get("raio"), 2.0) * scale
        if override_circle_radius_tiles is not None:
            radius_tiles = max(0.0, float(override_circle_radius_tiles))
        if self._safe_bool(flow.get("centralizar"), False):
            return center_px, radius_tiles * self._tile_px, exit_dir
        perp = Vec2(-exit_dir.y, exit_dir.x)
        range_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow, override_range_tiles=override_range_tiles)
        range_tiles *= scale
        spacing_tiles = self._safe_float(flow.get("espacamento"), 0.0)
        if self._safe_bool(flow.get("grudado"), False):
            circle_center = center_px + exit_dir * ((source_radius_tiles + range_tiles) * self._tile_px)
        else:
            circle_center = center_px + exit_dir * ((source_radius_tiles + spacing_tiles + range_tiles) * self._tile_px) + perp * (self._safe_float(flow.get("offset"), 0.0) * self._tile_px)
        return circle_center, radius_tiles * self._tile_px, exit_dir

    def find_hit(
        self,
        start_px: Vec2,
        direction: Vec2,
        remaining_px: float,
        walls: List[Tuple[Vec2, Vec2]],
        pokemons: List[Dict[str, object]],
        origin_pokemon_id: Optional[str],
        flow: Dict[str, object],
    ):
        best = None
        if not self._safe_bool(flow.get("atravessa_objetos", flow.get("atravessa_paredes", False)), False):
            for a, b in walls:
                hit = self.segment_intersection(start_px, direction, remaining_px, a, b)
                if hit is None:
                    continue
                dist_px, hit_px, normal = hit
                if best is None or dist_px < best[0]:
                    best = (dist_px, hit_px, normal, "wall", None)
        if not self._safe_bool(flow.get("atravessa_pokemons"), False):
            for pokemon in pokemons:
                if origin_pokemon_id is not None and str(pokemon.get("id")) == str(origin_pokemon_id):
                    continue
                hit = self.ray_circle_hit(
                    start_px,
                    direction,
                    remaining_px,
                    self._vec2(pokemon.get("pos")),
                    max(0.0, self._safe_float(pokemon.get("raio_tiles"), 0.0)) * self._tile_px,
                )
                if hit is None:
                    continue
                dist_px, hit_px, normal = hit
                if best is None or dist_px < best[0]:
                    best = (dist_px, hit_px, normal, "pokemon", str(pokemon.get("id")))
        return best

    def _tracar_segmentos(
        self,
        flow: Dict[str, object],
        center_px: Vec2,
        mouse_px: Vec2,
        source_radius_tiles: float,
        walls: List[Tuple[Vec2, Vec2]],
        pokemons: List[Dict[str, object]],
        *,
        is_subflow: bool,
        origin_pokemon_id: Optional[str],
        override_range_tiles: Optional[float] = None,
        override_ricochets: Optional[int] = None,
    ) -> Tuple[List[Tuple[Vec2, Vec2, Vec2, float]], List[Dict[str, object]], Vec2, int]:
        aim_dir = self._safe_normalize(mouse_px - center_px)
        total_tiles = self.compute_effective_range_tiles(
            flow,
            center_px,
            mouse_px,
            source_radius_tiles,
            is_subflow,
            override_range_tiles=override_range_tiles,
        )
        total_tiles *= self.scaled_factor(flow, source_radius_tiles)
        start_px, direction, _ = self.base_start(center_px, aim_dir, flow, source_radius_tiles)
        remaining_px = max(0.0, total_tiles * self._tile_px)
        if override_ricochets is None:
            ricochet_left = 0
            if self._safe_bool(flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False)), False) or self._safe_bool(flow.get("ricocheteia_pokemons"), False):
                ricochet_left = max(0, int(self._safe_float(flow.get("numero_ricochets"), 0)))
        else:
            ricochet_left = max(0, int(override_ricochets))

        origin_block_id = origin_pokemon_id if not self._safe_bool(flow.get("subfluxo_atinge_a_si_mesmo"), False) else None
        current_start = start_px
        final_direction = Vec2(direction)
        segments: List[Tuple[Vec2, Vec2, Vec2, float]] = []
        eventos: List[Dict[str, object]] = []

        while remaining_px > 1e-4:
            hit = self.find_hit(current_start, final_direction, remaining_px, walls, pokemons, origin_block_id, flow)
            if hit is None:
                end_px = current_start + final_direction * remaining_px
                segments.append((current_start, end_px, final_direction, remaining_px / self._tile_px))
                current_start = end_px
                break

            dist_px, hit_px, normal, hit_type, hit_id = hit
            end_px = hit_px
            segments.append((current_start, end_px, final_direction, dist_px / self._tile_px))
            remaining_px -= dist_px
            can_reflect = (
                hit_type == "wall"
                and self._safe_bool(flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False)), False)
            ) or (
                hit_type == "pokemon"
                and self._safe_bool(flow.get("ricocheteia_pokemons"), False)
            )
            will_reflect = ricochet_left > 0 and can_reflect
            eventos.append(
                {
                    "tipo": hit_type,
                    "pokemon_id": hit_id,
                    "ponto": Vec2(hit_px),
                    "normal": Vec2(normal),
                    "direcao": Vec2(final_direction),
                    "ricochete": will_reflect,
                }
            )
            if not will_reflect:
                current_start = hit_px
                break

            ricochet_left -= 1
            final_direction = self._safe_normalize(self.reflect(final_direction, normal))
            current_start = hit_px + final_direction * 1.5
            remaining_px = max(0.0, remaining_px - 2.0)

        return segments, eventos, final_direction, ricochet_left

    def build_segments(
        self,
        flow: Dict[str, object],
        center_px: Vec2,
        mouse_px: Vec2,
        source_radius_tiles: float,
        walls: List[Tuple[Vec2, Vec2]],
        pokemons: List[Dict[str, object]],
        *,
        is_subflow: bool,
        origin_pokemon_id: Optional[str],
        override_range_tiles: Optional[float] = None,
        override_ricochets: Optional[int] = None,
    ) -> List[Tuple[Vec2, Vec2, Vec2, float]]:
        segments, _eventos, _final_direction, _ricochet_left = self._tracar_segmentos(
            flow,
            center_px,
            mouse_px,
            source_radius_tiles,
            walls,
            pokemons,
            is_subflow=is_subflow,
            origin_pokemon_id=origin_pokemon_id,
            override_range_tiles=override_range_tiles,
            override_ricochets=override_ricochets,
        )
        return segments

    def rastrear_fluxo(
        self,
        ataque: object,
        inicio,
        fim,
        *,
        tile_px: float = 1.0,
        source_radius_tiles: Optional[float] = None,
        paredes: Optional[Iterable[object]] = None,
        pokemons: Optional[Iterable[object]] = None,
        ignorar_pokemon_ids: Optional[Iterable[object]] = None,
        override_range_tiles: Optional[float] = None,
        override_ricochets: Optional[int] = None,
    ) -> Dict[str, object]:
        self._tile_px = max(0.01, float(tile_px))
        pacote = self._pacote_fluxo(ataque)
        fluxos = self._fluxos_topo(pacote)
        if not fluxos:
            return {"segments": [], "eventos": [], "direcao_final": Vec2(1, 0), "ricochetes_restantes": int(max(0, override_ricochets or 0))}
        flow = fluxos[0]
        if self._safe_bool(flow.get("circular"), False):
            return {"segments": [], "eventos": [], "direcao_final": self._safe_normalize(self._vec2(fim) - self._vec2(inicio)), "ricochetes_restantes": int(max(0, override_ricochets or 0))}
        inicio_v = self._vec2(inicio)
        fim_v = self._vec2(fim)
        raio_origem = self._fonte_radius_tiles(pacote, source_radius_tiles)
        walls = self._normalizar_paredes(paredes)
        enemies = self._normalizar_pokemons(pokemons, ignorar_ids=ignorar_pokemon_ids)
        segments, eventos, direcao_final, ricochetes_restantes = self._tracar_segmentos(
            flow,
            inicio_v,
            fim_v,
            raio_origem,
            walls,
            enemies,
            is_subflow=False,
            origin_pokemon_id=None,
            override_range_tiles=override_range_tiles,
            override_ricochets=override_ricochets,
        )
        return {
            "segments": segments,
            "eventos": eventos,
            "direcao_final": direcao_final,
            "ricochetes_restantes": ricochetes_restantes,
        }

    def _pokemon_atingido_por_forma(
        self,
        colidiveis: List[List[Vec2]],
        circulos: List[Tuple[Vec2, float, Dict[str, object], bool]],
        pokemon: Dict[str, object],
    ) -> bool:
        centro = self._vec2(pokemon.get("pos"))
        raio_px = max(0.0, self._safe_float(pokemon.get("raio_tiles"), 0.0)) * self._tile_px
        for ponto in self.circle_samples(centro, raio_px):
            for poligono in colidiveis:
                if self.point_in_polygon(ponto, poligono):
                    return True
            for centro_circulo, raio_circulo, flow_circulo, _visivel in circulos:
                if self.point_hit_circle_shape(ponto, centro_circulo, raio_circulo, flow_circulo):
                    return True
        return False

    def _construir_formas_fluxo(
        self,
        flow: Dict[str, object],
        center_px: Vec2,
        mouse_px: Vec2,
        source_radius_tiles: float,
        *,
        is_subflow: bool = False,
        walls: Optional[Iterable[object]] = None,
        pokemons: Optional[Iterable[object]] = None,
        origin_pokemon_id: Optional[str] = None,
        override_range_tiles: Optional[float] = None,
        override_circle_radius_tiles: Optional[float] = None,
        override_ricochets: Optional[int] = None,
    ) -> Tuple[List[Tuple[List[Vec2], Dict[str, object]]], List[List[Vec2]], List[Tuple[Vec2, float, Dict[str, object], bool]], Vec2]:
        visiveis: List[Tuple[List[Vec2], Dict[str, object]]] = []
        colidiveis: List[List[Vec2]] = []
        circulos: List[Tuple[Vec2, float, Dict[str, object], bool]] = []
        proxima_origem = Vec2(center_px)
        walls_norm = self._normalizar_paredes(walls)
        pokemons_norm = self._normalizar_pokemons(pokemons)
        direcao_subfluxo = self._safe_normalize(mouse_px - center_px)
        eventos_segmentos: List[Dict[str, object]] = []
        hits_para_subfluxo: List[Dict[str, object]] = []

        if self._safe_bool(flow.get("circular"), False):
            circle_center, radius_px, exit_dir = self.visible_circle_center(
                center_px,
                mouse_px,
                source_radius_tiles,
                flow,
                is_subflow,
                override_range_tiles=override_range_tiles,
                override_circle_radius_tiles=override_circle_radius_tiles,
            )
            circulos.append((circle_center, radius_px, dict(flow), self._safe_bool(flow.get("visible"), True)))
            if self._safe_bool(flow.get("visible"), True):
                visiveis.append((self.circle_outline(circle_center, radius_px, flow), dict(flow)))
            proxima_origem = circle_center if self._safe_bool(flow.get("centralizar"), False) else (circle_center + exit_dir * radius_px)
            direcao_subfluxo = exit_dir
        else:
            if walls_norm or pokemons_norm:
                segments, eventos_segmentos, _direcao_final, _ricochetes_restantes = self._tracar_segmentos(
                    flow,
                    center_px,
                    mouse_px,
                    source_radius_tiles,
                    walls_norm,
                    pokemons_norm,
                    is_subflow=is_subflow,
                    origin_pokemon_id=origin_pokemon_id,
                    override_range_tiles=override_range_tiles,
                    override_ricochets=override_ricochets,
                )
            else:
                segments = []
            if segments:
                current_source = center_px
                current_radius = source_radius_tiles
                direcao_subfluxo = segments[-1][2]
                for seg_idx, (seg_start, seg_end, _seg_dir, seg_len_tiles) in enumerate(segments):
                    temp_flow = dict(flow)
                    temp_flow["espacamento"] = 0.0
                    temp_flow["offset"] = 0.0 if seg_idx > 0 else flow.get("offset", 0.0)
                    temp_flow["grudado"] = flow.get("grudado", False) if seg_idx == 0 else False
                    temp_flow["ajustavel"] = False
                    temp_flow["alcance"] = max(0.1, seg_len_tiles)
                    pontos, larguras, _alcance, eixo, _inicio = self.build_centerline(
                        temp_flow,
                        seg_start if seg_idx > 0 else current_source,
                        seg_end,
                        0.0 if seg_idx > 0 else current_radius,
                        True,
                    )
                    poligono = self.polygon_from_centerline(
                        pontos,
                        larguras,
                        current_source if seg_idx == 0 else seg_start,
                        current_radius if seg_idx == 0 else 0.0,
                        temp_flow,
                        eixo,
                    )
                    if poligono:
                        colidiveis.append(poligono)
                        if self._safe_bool(flow.get("visible"), True):
                            visiveis.append((poligono, dict(flow)))
                proxima_origem = segments[-1][1]
            else:
                pontos, larguras, _alcance, eixo, _inicio = self.build_centerline(
                    flow,
                    center_px,
                    mouse_px,
                    source_radius_tiles,
                    is_subflow,
                    override_range_tiles=override_range_tiles,
                )
                poligono = self.polygon_from_centerline(pontos, larguras, center_px, source_radius_tiles, flow, eixo)
                if poligono:
                    colidiveis.append(poligono)
                    if self._safe_bool(flow.get("visible"), True):
                        visiveis.append((poligono, dict(flow)))
                if pontos:
                    proxima_origem = pontos[-1]
                    if len(pontos) >= 2:
                        direcao_subfluxo = self._safe_normalize(pontos[-1] - pontos[-2])

        for pokemon in pokemons_norm:
            pokemon_id = str(pokemon.get("id"))
            if origin_pokemon_id is not None and pokemon_id == str(origin_pokemon_id) and not self._safe_bool(flow.get("subfluxo_atinge_a_si_mesmo"), False):
                continue
            if not self._pokemon_atingido_por_forma(colidiveis, circulos, pokemon):
                continue
            hits_para_subfluxo.append(
                {
                    "id": pokemon_id,
                    "pos": self._vec2(pokemon.get("pos")),
                    "raio_tiles": max(0.0, self._safe_float(pokemon.get("raio_tiles"), 0.0)),
                    "direcao": Vec2(direcao_subfluxo),
                }
            )
        hit_ids = {str(hit.get("id")) for hit in hits_para_subfluxo}
        for evento in eventos_segmentos:
            if str(evento.get("tipo") or "") != "pokemon":
                continue
            pokemon_id = str(evento.get("pokemon_id") or "")
            if not pokemon_id or pokemon_id in hit_ids:
                continue
            pokemon = next((item for item in pokemons_norm if str(item.get("id")) == pokemon_id), None)
            if pokemon is None:
                continue
            hit_ids.add(pokemon_id)
            hits_para_subfluxo.append(
                {
                    "id": pokemon_id,
                    "pos": self._vec2(pokemon.get("pos")),
                    "raio_tiles": max(0.0, self._safe_float(pokemon.get("raio_tiles"), 0.0)),
                    "direcao": Vec2(direcao_subfluxo),
                }
            )

        for subfluxo in [dict(item) for item in list(flow.get("subfluxos") or []) if isinstance(item, dict)]:
            for hit in hits_para_subfluxo:
                alvo_subfluxo = hit["pos"] + hit["direcao"] * self._tile_px * 10.0
                sub_visiveis, sub_colidiveis, sub_circulos, _ = self._construir_formas_fluxo(
                    subfluxo,
                    hit["pos"],
                    alvo_subfluxo,
                    hit["raio_tiles"],
                    is_subflow=True,
                    walls=walls_norm,
                    pokemons=pokemons_norm,
                    origin_pokemon_id=str(hit["id"]),
                )
                visiveis.extend(sub_visiveis)
                colidiveis.extend(sub_colidiveis)
                circulos.extend(sub_circulos)
        return visiveis, colidiveis, circulos, proxima_origem

    def _coletar_formas(
        self,
        ataque: object,
        inicio,
        fim,
        *,
        tile_px: float,
        source_radius_tiles: Optional[float] = None,
        paredes: Optional[Iterable[object]] = None,
        pokemons: Optional[Iterable[object]] = None,
        ignorar_pokemon_ids: Optional[Iterable[object]] = None,
        override_range_tiles: Optional[float] = None,
        override_circle_radius_tiles: Optional[float] = None,
        override_ricochets: Optional[int] = None,
    ) -> Tuple[List[Tuple[List[Vec2], Dict[str, object]]], List[List[Vec2]], List[Tuple[Vec2, float, Dict[str, object], bool]]]:
        self._tile_px = max(0.01, float(tile_px))
        pacote = self._pacote_fluxo(ataque)
        inicio_v = Vec2(float(inicio[0]), float(inicio[1]))
        fim_v = Vec2(float(fim[0]), float(fim[1]))
        raio_origem = self._fonte_radius_tiles(pacote, source_radius_tiles)
        fluxos = self._fluxos_topo(pacote)
        pokemons_norm = self._normalizar_pokemons(pokemons, ignorar_ids=ignorar_pokemon_ids)
        walls_norm = self._normalizar_paredes(paredes)
        visiveis: List[Tuple[List[Vec2], Dict[str, object]]] = []
        colidiveis: List[List[Vec2]] = []
        circulos: List[Tuple[Vec2, float, Dict[str, object], bool]] = []
        for indice_fluxo, fluxo in enumerate(fluxos):
            vis, col, cir, _ = self._construir_formas_fluxo(
                fluxo,
                inicio_v,
                fim_v,
                raio_origem,
                is_subflow=False,
                walls=walls_norm,
                pokemons=pokemons_norm,
                origin_pokemon_id=None,
                override_range_tiles=override_range_tiles,
                override_circle_radius_tiles=override_circle_radius_tiles,
                override_ricochets=override_ricochets if indice_fluxo == 0 else None,
            )
            visiveis.extend(vis)
            colidiveis.extend(col)
            circulos.extend(cir)
        return visiveis, colidiveis, circulos

    def _desenhar_circulo(self, area: pygame.Surface, pontos: List[Vec2], alpha: int) -> None:
        self._desenhar_poligono(
            area,
            pontos,
            (255, 255, 255, max(14, int(alpha * 0.32))),
            (255, 255, 255, max(40, int(alpha * 0.82))),
            2,
        )

    def _desenhar_animacao(self, area: pygame.Surface, inicio: Vec2, fim: Vec2, alpha: int) -> None:
        if pygame is None:
            return
        direcao = self._safe_normalize(fim - inicio)
        distancia = max(1.0, (fim - inicio).length())
        perpendicular = Vec2(-direcao.y, direcao.x)
        passo = 36.0
        deslocamento = (self._tempo * 180.0) % passo
        cursor = -deslocamento
        while cursor < distancia + passo:
            centro = inicio + direcao * cursor + perpendicular * (math.sin(self._tempo * 5.5 + cursor * 0.06) * 3.0)
            largura = 24 + 8 * math.sin(self._tempo * 3.7 + cursor * 0.08)
            ponta = centro + direcao * largura
            pygame.draw.line(
                area,
                (255, 255, 255, max(0, int(alpha * 0.14))),
                (int(centro.x), int(centro.y)),
                (int(ponta.x), int(ponta.y)),
                3,
            )
            cursor += passo

    def desenhar(
        self,
        tela: pygame.Surface,
        ataque: object,
        inicio,
        fim,
        *,
        alpha: int = 120,
        animado: bool = True,
        tile_px: float = 42.0,
        source_radius_tiles: Optional[float] = None,
        paredes: Optional[Iterable[object]] = None,
        pokemons: Optional[Iterable[object]] = None,
        ignorar_pokemon_ids: Optional[Iterable[object]] = None,
    ) -> None:
        if pygame is None:
            return
        visiveis, _colidiveis, circulos = self._coletar_formas(
            ataque,
            inicio,
            fim,
            tile_px=tile_px,
            source_radius_tiles=source_radius_tiles,
            paredes=paredes,
            pokemons=pokemons,
            ignorar_pokemon_ids=ignorar_pokemon_ids,
        )
        inicio_v = Vec2(float(inicio[0]), float(inicio[1]))
        fim_v = Vec2(float(fim[0]), float(fim[1]))
        area = pygame.Surface(tela.get_size(), pygame.SRCALPHA)

        if not visiveis and not circulos:
            direcao = self._safe_normalize(fim_v - inicio_v)
            fallback = [
                inicio_v + Vec2(-direcao.y, direcao.x) * 18.0,
                fim_v,
                inicio_v - Vec2(-direcao.y, direcao.x) * 18.0,
            ]
            self._desenhar_poligono(area, fallback, (255, 255, 255, max(18, int(alpha * 0.32))), (255, 255, 255, max(40, int(alpha * 0.82))), 2)
            if animado:
                self._desenhar_animacao(area, inicio_v, fim_v, alpha)
            tela.blit(area, (0, 0))
            return

        for poligono, _flow in visiveis:
            self._desenhar_poligono(
                area,
                poligono,
                (255, 255, 255, max(16, int(alpha * 0.34))),
                (255, 255, 255, max(42, int(alpha * 0.84))),
                2,
            )
        for centro, raio_px, flow, visivel in circulos:
            if not visivel:
                continue
            self._desenhar_circulo(area, self.circle_outline(centro, raio_px, flow), alpha)

        if animado:
            self._desenhar_animacao(area, inicio_v, fim_v, alpha)
        tela.blit(area, (0, 0))

    def flow_contains_target(
        self,
        ataque: object,
        inicio,
        fim,
        alvo_pos,
        alvo_raio_tiles: float,
        *,
        tile_px: float = 1.0,
        source_radius_tiles: Optional[float] = None,
        paredes: Optional[Iterable[object]] = None,
        pokemons: Optional[Iterable[object]] = None,
        ignorar_pokemon_ids: Optional[Iterable[object]] = None,
        override_range_tiles: Optional[float] = None,
        override_circle_radius_tiles: Optional[float] = None,
        override_ricochets: Optional[int] = None,
    ) -> bool:
        _visiveis, colidiveis, circulos = self._coletar_formas(
            ataque,
            inicio,
            fim,
            tile_px=tile_px,
            source_radius_tiles=source_radius_tiles,
            paredes=paredes,
            pokemons=pokemons,
            ignorar_pokemon_ids=ignorar_pokemon_ids,
            override_range_tiles=override_range_tiles,
            override_circle_radius_tiles=override_circle_radius_tiles,
            override_ricochets=override_ricochets,
        )
        alvo_centro = Vec2(float(alvo_pos[0]), float(alvo_pos[1]))
        alvo_raio_px = max(0.0, float(alvo_raio_tiles) * float(tile_px))
        for ponto in self.circle_samples(alvo_centro, alvo_raio_px):
            for poligono in colidiveis:
                if self.point_in_polygon(ponto, poligono):
                    return True
            for centro, raio_px, flow, _visivel in circulos:
                if self.point_hit_circle_shape(ponto, centro, raio_px, flow):
                    return True
        return False
