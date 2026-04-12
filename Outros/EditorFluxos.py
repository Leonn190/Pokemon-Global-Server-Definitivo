# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import copy
import json
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame

Vec2 = pygame.math.Vector2

WINDOW_W = 1560
WINDOW_H = 920
PREVIEW_W = 1020
PANEL_X = PREVIEW_W
PANEL_W = WINDOW_W - PREVIEW_W
FPS = 90
DEFAULT_TILE_PX = 52
MIN_TILE_PX = 24
MAX_TILE_PX = 100
DEFAULT_TEST_DIAMETER = 1.5
MAX_FLOWS = 5
MAX_SUBFLOWS = 5
MAX_RICOCHETS = 12
MAX_ENEMIES = 32
MAX_WALLS = 48

BG_PREVIEW = (22, 24, 27)
GRID_MINOR = (45, 49, 56)
GRID_MAJOR = (64, 70, 80)
GRID_AXIS = (96, 104, 118)
PANEL_BG = (28, 31, 37)
PANEL_BG_2 = (36, 40, 47)
PANEL_BG_3 = (46, 50, 59)
PANEL_STROKE = (74, 80, 92)
TEXT = (235, 238, 244)
TEXT_MID = (188, 196, 210)
TEXT_DIM = (138, 147, 162)
ACCENT = (91, 188, 255)
GREEN = (102, 214, 124)
RED = (226, 103, 103)
YELLOW = (241, 211, 98)
ORANGE = (250, 158, 78)
PURPLE = (187, 134, 252)
FLOW_FILL = [
    (190, 236, 255, 100),
    (255, 215, 175, 96),
    (222, 196, 255, 96),
    (204, 255, 224, 96),
    (255, 198, 224, 96),
]
FLOW_STROKE = [
    (215, 246, 255),
    (255, 229, 195),
    (233, 220, 255),
    (220, 255, 234),
    (255, 218, 236),
]
SUBFLOW_FILL = [
    (150, 220, 255, 90),
    (255, 198, 142, 86),
    (200, 170, 255, 86),
    (160, 255, 210, 86),
    (255, 165, 205, 86),
]
SUBFLOW_STROKE = [
    (210, 242, 255),
    (255, 227, 188),
    (226, 208, 255),
    (214, 255, 232),
    (255, 214, 232),
]

HASTES_OPTIONS = ["reto", "concavo", "convexo"]
SHAPE_OPTIONS = ["normal", "espinhos", "bolhas"]

FIELD_GROUPS = [
    {
        "title": "Geral",
        "keys": [
            "visible", "alcance", "ajustavel", "alcance_min", "alcance_max",
            "largura_teto", "largura_base", "grudado", "offset", "espacamento",
            "escalonavel", "intensidade_dano",
        ],
    },
    {
        "title": "Faixas",
        "keys": [
            "faixas", "largura_faixa", "repeticao_faixas", "faixas_ciclicas",
            "distancia_faixa",
        ],
    },
    {
        "title": "Ricochet",
        "keys": [
            "ricocheteia_objetos", "ricocheteia_pokemons", "atravessa_objetos",
            "atravessa_pokemons", "numero_ricochets",
        ],
    },
    {
        "title": "Curvatura",
        "keys": [
            "hastes", "pontos_curvatura", "curvatura_circular", "curvaturas_ciclicas",
            "distancia_entre_curvaturas", "invertido",
            "curvatura_1", "curvatura_2", "curvatura_3", "curvatura_4", "curvatura_5", "curvatura_6",
        ],
    },
    {
        "title": "Circular",
        "keys": [
            "circular", "centralizar", "raio", "shape", "tamanho_elementos", "quantidade_elementos",
        ],
    },
    {
        "title": "Subfluxo",
        "keys": ["subfluxo_atinge_a_si_mesmo"],
    },
]

FIELD_DEFS = {
    "visible": {"label": "Visível", "kind": "bool"},
    "alcance": {"label": "Alcance", "kind": "float", "step": 0.10, "min": 0.10, "max": 60.0},
    "ajustavel": {"label": "Ajustável", "kind": "bool"},
    "alcance_min": {"label": "Alcance min", "kind": "float", "step": 0.10, "min": 0.10, "max": 60.0},
    "alcance_max": {"label": "Alcance max", "kind": "float", "step": 0.10, "min": 0.10, "max": 60.0},
    "largura_teto": {"label": "Largura teto", "kind": "float", "step": 0.10, "min": 0.0, "max": 40.0},
    "largura_base": {"label": "Largura base", "kind": "float", "step": 0.10, "min": 0.0, "max": 40.0},
    "grudado": {"label": "Grudado", "kind": "bool"},
    "offset": {"label": "Offset", "kind": "float", "step": 0.10, "min": -40.0, "max": 40.0},
    "espacamento": {"label": "Espaçamento", "kind": "float", "step": 0.10, "min": -5.0, "max": 30.0},
    "faixas": {"label": "Faixas", "kind": "int", "step": 1, "min": 0, "max": 24},
    "largura_faixa": {"label": "Largura faixa", "kind": "float", "step": 0.10, "min": 0.0, "max": 40.0},
    "repeticao_faixas": {"label": "Repetição faixas", "kind": "bool"},
    "faixas_ciclicas": {"label": "Faixas cíclicas", "kind": "bool"},
    "distancia_faixa": {"label": "Distância faixa", "kind": "float", "step": 0.10, "min": 0.10, "max": 60.0},
    "ricocheteia_objetos": {"label": "Ricocheteia objetos", "kind": "bool"},
    "ricocheteia_pokemons": {"label": "Ricocheteia pokémons", "kind": "bool"},
    "atravessa_objetos": {"label": "Atravessa objetos", "kind": "bool"},
    "atravessa_pokemons": {"label": "Atravessa pokémons", "kind": "bool"},
    "numero_ricochets": {"label": "Número ricochets", "kind": "int", "step": 1, "min": 0, "max": MAX_RICOCHETS},
    "hastes": {"label": "Hastes", "kind": "choice", "options": HASTES_OPTIONS},
    "pontos_curvatura": {"label": "Pontos curvatura", "kind": "int", "step": 1, "min": 0, "max": 6},
    "curvatura_circular": {"label": "Curvatura circular", "kind": "bool"},
    "curvaturas_ciclicas": {"label": "Curvaturas cíclicas", "kind": "bool"},
    "distancia_entre_curvaturas": {"label": "Distância curvaturas", "kind": "float", "step": 0.10, "min": 0.10, "max": 60.0},
    "invertido": {"label": "Invertido", "kind": "bool"},
    "curvatura_1": {"label": "Curvatura 1", "kind": "float", "step": 0.10, "min": -30.0, "max": 30.0},
    "curvatura_2": {"label": "Curvatura 2", "kind": "float", "step": 0.10, "min": -30.0, "max": 30.0},
    "curvatura_3": {"label": "Curvatura 3", "kind": "float", "step": 0.10, "min": -30.0, "max": 30.0},
    "curvatura_4": {"label": "Curvatura 4", "kind": "float", "step": 0.10, "min": -30.0, "max": 30.0},
    "curvatura_5": {"label": "Curvatura 5", "kind": "float", "step": 0.10, "min": -30.0, "max": 30.0},
    "curvatura_6": {"label": "Curvatura 6", "kind": "float", "step": 0.10, "min": -30.0, "max": 30.0},
    "circular": {"label": "Circular", "kind": "bool"},
    "centralizar": {"label": "Centralizar", "kind": "bool"},
    "raio": {"label": "Raio", "kind": "float", "step": 0.10, "min": 0.10, "max": 40.0},
    "shape": {"label": "Shape", "kind": "choice", "options": SHAPE_OPTIONS},
    "tamanho_elementos": {"label": "Tamanho elementos", "kind": "float", "step": 0.10, "min": 0.0, "max": 12.0},
    "quantidade_elementos": {"label": "Qtd elementos", "kind": "int", "step": 1, "min": 0, "max": 128},
    "escalonavel": {"label": "Escalonável", "kind": "bool"},
    "intensidade_dano": {"label": "Intensidade dano", "kind": "float", "step": 0.05, "min": 0.0, "max": 20.0},
    "subfluxo_atinge_a_si_mesmo": {"label": "Subfluxo atinge a si mesmo", "kind": "bool"},
    "test_diameter": {"label": "Diâmetro pokémon teste", "kind": "float", "step": 0.10, "min": 0.3, "max": 8.0},
}


@dataclass
class EnemyPreview:
    pos: Vec2
    radius_tiles: float = DEFAULT_TEST_DIAMETER / 2.0


@dataclass
class WallPreview:
    a: Vec2
    b: Vec2


@dataclass
class PreviewHit:
    enemy_index: int
    enemy_center_px: Vec2
    direction: Vec2


class PreviewRenderer:
    def __init__(self, tile_px: float, preview_size: Tuple[int, int]):
        self.tile_px = tile_px
        self.preview_w, self.preview_h = preview_size

    def clamp(self, value, lo, hi):
        return max(lo, min(hi, value))

    def tile_to_px(self, origin_px: Vec2, p_tiles: Vec2) -> Vec2:
        return origin_px + p_tiles * self.tile_px

    def safe_normalize(self, v: Vec2) -> Vec2:
        if v.length_squared() <= 1e-9:
            return Vec2(1, 0)
        return v.normalize()

    def point_in_polygon(self, point: Vec2, polygon: List[Vec2]) -> bool:
        if len(polygon) < 3:
            return False
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i].x, polygon[i].y
            xj, yj = polygon[j].x, polygon[j].y
            if ((yi > point.y) != (yj > point.y)):
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

    def point_hit_circle_shape(self, point_px: Vec2, center_px: Vec2, radius_px: float, flow: Dict) -> bool:
        dist = (point_px - center_px).length()
        shape = flow.get("shape", "normal")
        if shape == "normal":
            return dist <= radius_px
        count = max(1, int(flow.get("quantidade_elementos", 0)))
        elem = max(0.0, float(flow.get("tamanho_elementos", 0.0))) * self.tile_px
        if count <= 0 or elem <= 0.0:
            return dist <= radius_px
        ang = math.atan2(point_px.y - center_px.y, point_px.x - center_px.x)
        wave = 0.5 * (1.0 + math.cos(ang * count))
        if shape == "espinhos":
            mod = wave
        else:
            mod = wave * 0.55
        local_radius = radius_px + elem * mod
        return dist <= local_radius

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
            n = Vec2(-wall_dir.y, wall_dir.x).normalize()
            if n.dot(ray_dir) > 0:
                n *= -1
            return max_len_px * t, hit_px, n
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
        n = hit_px - center_px
        if n.length_squared() <= 1e-8:
            return None
        return t, hit_px, n.normalize()

    def reflect(self, direction: Vec2, normal: Vec2) -> Vec2:
        n = self.safe_normalize(normal)
        return direction - 2.0 * direction.dot(n) * n

    def compute_effective_range_tiles(self, flow: Dict, source_center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, is_subflow: bool) -> float:
        if is_subflow:
            return max(0.10, float(flow.get("alcance", 4.0)))
        if not flow.get("ajustavel", False):
            return max(0.10, float(flow.get("alcance", 4.0)))
        min_v = max(0.10, float(flow.get("alcance_min", 1.0)))
        max_v = max(min_v, float(flow.get("alcance_max", min_v)))
        mouse_dist_tiles = max(0.0, (mouse_px - source_center_px).length() / self.tile_px - source_radius_tiles)
        return self.clamp(mouse_dist_tiles, min_v, max_v)

    def scaled_factor(self, flow: Dict, source_radius_tiles: float) -> float:
        return 1.0 + (source_radius_tiles * 2.0 - DEFAULT_TEST_DIAMETER) * 0.08 if flow.get("escalonavel", False) else 1.0

    def exit_direction(self, aim_dir: Vec2, flow: Dict, source_radius_tiles: float) -> Vec2:
        offset_value = float(flow.get("offset", 0.0))
        if abs(offset_value) <= 1e-9:
            return aim_dir
        if flow.get("grudado", False):
            base_ang = math.atan2(aim_dir.y, aim_dir.x)
            ang = math.radians(offset_value)
            return Vec2(math.cos(base_ang + ang), math.sin(base_ang + ang))
        return aim_dir

    def base_start(self, center_px: Vec2, aim_dir: Vec2, flow: Dict, source_radius_tiles: float) -> Tuple[Vec2, Vec2, Vec2]:
        exit_dir = self.exit_direction(aim_dir, flow, source_radius_tiles)
        perp = Vec2(-exit_dir.y, exit_dir.x)
        spacing_tiles = float(flow.get("espacamento", 0.0))
        offset_tiles = float(flow.get("offset", 0.0))
        if flow.get("grudado", False):
            start_center = center_px + exit_dir * (source_radius_tiles * self.tile_px)
        else:
            start_center = center_px + exit_dir * ((source_radius_tiles + spacing_tiles) * self.tile_px) + perp * (offset_tiles * self.tile_px)
        return start_center, exit_dir, perp

    def width_profile_tiles(self, flow: Dict, total_len_tiles: float) -> Tuple[List[float], List[float]]:
        total_len_tiles = max(0.10, total_len_tiles)
        widths = [max(0.0, float(flow.get("largura_base", 0.0))), max(0.0, float(flow.get("largura_teto", 0.0)))]
        dists = [0.0, total_len_tiles]
        faixas = max(0, int(flow.get("faixas", 0)))
        if faixas <= 0:
            return dists, widths
        largura_faixa = max(0.0, float(flow.get("largura_faixa", widths[-1])))
        repeticao = bool(flow.get("repeticao_faixas", True))
        ciclico = bool(flow.get("faixas_ciclicas", False))
        if ciclico:
            step = max(0.10, float(flow.get("distancia_faixa", 1.0)))
            pos = step
            toggle = True
            dists = [0.0]
            widths = [max(0.0, float(flow.get("largura_base", 0.0)))]
            while pos < total_len_tiles - 1e-6:
                dists.append(pos)
                if toggle:
                    widths.append(max(0.0, float(flow.get("largura_teto", 0.0))))
                else:
                    widths.append(largura_faixa)
                toggle = not toggle
                pos += step
            dists.append(total_len_tiles)
            widths.append(max(0.0, float(flow.get("largura_teto", 0.0)) if len(widths) % 2 == 1 else largura_faixa))
            return dists, widths
        segments = faixas + 2
        step = total_len_tiles / max(1, segments - 1)
        dists = [i * step for i in range(segments)]
        widths = [max(0.0, float(flow.get("largura_base", 0.0))), max(0.0, float(flow.get("largura_teto", 0.0)))]
        if repeticao:
            use_teto = False
            for _ in range(faixas):
                widths.append(max(0.0, float(flow.get("largura_teto", 0.0))) if use_teto else largura_faixa)
                use_teto = not use_teto
        else:
            widths.extend([largura_faixa for _ in range(faixas)])
        return dists, widths[: len(dists)]

    def curvature_anchors(self, flow: Dict, total_len_tiles: float) -> Tuple[List[float], List[float]]:
        total_len_tiles = max(0.10, total_len_tiles)
        points_n = max(0, int(flow.get("pontos_curvatura", 0)))
        cyclic = bool(flow.get("curvaturas_ciclicas", False))
        invertido = bool(flow.get("invertido", True))
        vals = [float(flow.get(f"curvatura_{i}", 0.0)) for i in range(1, 7)]
        positions: List[float] = []
        offsets: List[float] = []
        if cyclic:
            step = max(0.10, float(flow.get("distancia_entre_curvaturas", 1.0)))
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
        else:
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

    def build_centerline(self, flow: Dict, center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, is_subflow: bool) -> Tuple[List[Vec2], List[float], float, Vec2, Vec2, Vec2]:
        aim_dir = self.safe_normalize(mouse_px - center_px)
        total_len_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow)
        scale = self.scaled_factor(flow, source_radius_tiles)
        total_len_tiles *= scale
        start_center_px, axis_dir, perp = self.base_start(center_px, aim_dir, flow, source_radius_tiles)
        dists_nodes, widths_nodes = self.width_profile_tiles(flow, total_len_tiles)
        curvature_pos, curvature_vals = self.curvature_anchors(flow, total_len_tiles)
        anchor_map = {0.0: 0.0, total_len_tiles: 0.0}
        for d, v in zip(curvature_pos, curvature_vals):
            anchor_map[self.clamp(d, 0.0, total_len_tiles)] = v * scale
        anchor_keys = sorted(anchor_map.keys())
        anchor_points = [start_center_px + axis_dir * (d * self.tile_px) + perp * (anchor_map[d] * self.tile_px) for d in anchor_keys]
        if bool(flow.get("curvatura_circular", True)) and len(anchor_points) >= 3:
            smooth = self.catmull_rom(anchor_points, 10)
        else:
            smooth = []
            for i in range(len(anchor_points) - 1):
                a = anchor_points[i]
                b = anchor_points[i + 1]
                steps = max(2, int((b - a).length() / max(6.0, self.tile_px * 0.25)))
                for j in range(steps):
                    t = j / float(steps)
                    smooth.append(a.lerp(b, t))
            smooth.append(anchor_points[-1])
        if len(smooth) < 2:
            smooth = [start_center_px, start_center_px + axis_dir * (total_len_tiles * self.tile_px)]
        widths_px: List[float] = []
        cumulative_tiles = [0.0]
        total_px_len = 0.0
        for i in range(1, len(smooth)):
            total_px_len += (smooth[i] - smooth[i - 1]).length()
            cumulative_tiles.append(total_px_len / self.tile_px)
        for d in cumulative_tiles:
            idx = 0
            while idx < len(dists_nodes) - 1 and d > dists_nodes[idx + 1]:
                idx += 1
            if idx >= len(dists_nodes) - 1:
                w = widths_nodes[-1]
            else:
                a_d, b_d = dists_nodes[idx], dists_nodes[idx + 1]
                a_w, b_w = widths_nodes[idx], widths_nodes[idx + 1]
                t = 0.0 if abs(b_d - a_d) < 1e-8 else (d - a_d) / (b_d - a_d)
                if flow.get("hastes") == "concavo":
                    t = 1 - (1 - t) * (1 - t)
                elif flow.get("hastes") == "convexo":
                    t = t * t
                w = a_w + (b_w - a_w) * t
            widths_px.append(max(0.0, w * self.tile_px * scale))
        return smooth, widths_px, total_len_tiles, axis_dir, start_center_px, perp

    def polygon_from_centerline(self, points: List[Vec2], widths_px: List[float], source_center_px: Vec2, source_radius_tiles: float, flow: Dict, axis_dir: Vec2) -> List[Vec2]:
        if len(points) < 2:
            return []
        if flow.get("grudado", False):
            src_r_px = source_radius_tiles * self.tile_px
            outer_r_px = max(src_r_px, max((point - source_center_px).length() for point in points))
            center_ang = math.atan2(axis_dir.y, axis_dir.x)
            base_half_ang = min(math.tau * 0.5 - 1e-6, math.radians(max(0.0, float(flow.get("largura_base", 0.0))) * 0.5))
            teto_half_ang = min(math.tau * 0.5 - 1e-6, math.radians(max(0.0, float(flow.get("largura_teto", 0.0))) * 0.5))

            outer_samples = max(1, int(max(1e-6, teto_half_ang) * 18))
            inner_samples = max(1, int(max(1e-6, base_half_ang) * 18))

            outer_pts = []
            for i in range(outer_samples + 1):
                t = i / float(outer_samples)
                ang = center_ang + teto_half_ang - 2.0 * teto_half_ang * t
                outer_pts.append(source_center_px + Vec2(math.cos(ang), math.sin(ang)) * outer_r_px)

            inner_pts = []
            for i in range(inner_samples + 1):
                t = i / float(inner_samples)
                ang = center_ang - base_half_ang + 2.0 * base_half_ang * t
                inner_pts.append(source_center_px + Vec2(math.cos(ang), math.sin(ang)) * src_r_px)

            return outer_pts + inner_pts

        left: List[Vec2] = []
        right: List[Vec2] = []
        for i, point in enumerate(points):
            if i == 0:
                tangent = points[i + 1] - points[i]
            elif i == len(points) - 1:
                tangent = points[i] - points[i - 1]
            else:
                tangent = points[i + 1] - points[i - 1]
            tangent = self.safe_normalize(tangent)
            normal = Vec2(-tangent.y, tangent.x)
            half = widths_px[i] * 0.5
            left.append(point + normal * half)
            right.append(point - normal * half)
        return left + list(reversed(right))

    def circle_outline(self, center_px: Vec2, radius_px: float, flow: Dict) -> List[Vec2]:
        shape = flow.get("shape", "normal")
        count = max(24, int(flow.get("quantidade_elementos", 12)) * 6 if shape != "normal" else 48)
        elem_px = max(0.0, float(flow.get("tamanho_elementos", 0.0)) * self.tile_px)
        pts = []
        elements = max(1, int(flow.get("quantidade_elementos", 1)))
        for i in range(count):
            ang = (math.tau * i) / count
            r = radius_px
            if shape != "normal" and elem_px > 0.0 and elements > 0:
                wave = 0.5 * (1.0 + math.cos(ang * elements))
                if shape == "espinhos":
                    r += elem_px * wave
                else:
                    r += elem_px * wave * 0.55
            pts.append(center_px + Vec2(math.cos(ang), math.sin(ang)) * r)
        return pts

    def visible_circle_center(self, center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, flow: Dict, is_subflow: bool) -> Tuple[Vec2, float, Vec2]:
        aim_dir = self.safe_normalize(mouse_px - center_px)
        exit_dir = self.exit_direction(aim_dir, flow, source_radius_tiles)
        if flow.get("centralizar", False):
            radius_tiles = max(0.0, float(flow.get("raio", 2.0))) * self.scaled_factor(flow, source_radius_tiles)
            return center_px, radius_tiles * self.tile_px, exit_dir
        perp = Vec2(-exit_dir.y, exit_dir.x)
        range_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow)
        range_tiles *= self.scaled_factor(flow, source_radius_tiles)
        radius_tiles = max(0.0, float(flow.get("raio", 2.0))) * self.scaled_factor(flow, source_radius_tiles)
        spacing_tiles = float(flow.get("espacamento", 0.0))
        if flow.get("grudado", False):
            circle_center = center_px + exit_dir * ((source_radius_tiles + range_tiles) * self.tile_px)
        else:
            circle_center = center_px + exit_dir * ((source_radius_tiles + spacing_tiles + range_tiles) * self.tile_px) + perp * (float(flow.get("offset", 0.0)) * self.tile_px)
        return circle_center, radius_tiles * self.tile_px, exit_dir

    def find_hit(self, start_px: Vec2, direction: Vec2, remaining_px: float, walls: List[WallPreview], enemies: List[EnemyPreview], enemy_origin_px: Vec2, origin_index: Optional[int], flow: Dict):
        best = None
        if not flow.get("atravessa_objetos", flow.get("atravessa_paredes", False)):
            for wall in walls:
                hit = self.segment_intersection(start_px, direction, remaining_px, wall.a, wall.b)
                if hit is None:
                    continue
                dist_px, hit_px, normal = hit
                if best is None or dist_px < best[0]:
                    best = (dist_px, hit_px, normal, "wall", None)
        if not flow.get("atravessa_pokemons", False):
            for idx, enemy in enumerate(enemies):
                if origin_index is not None and idx == origin_index:
                    continue
                hit = self.ray_circle_hit(start_px, direction, remaining_px, enemy.pos, enemy.radius_tiles * self.tile_px)
                if hit is None:
                    continue
                dist_px, hit_px, normal = hit
                if best is None or dist_px < best[0]:
                    best = (dist_px, hit_px, normal, "enemy", idx)
        return best

    def build_segments(self, flow: Dict, center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, walls: List[WallPreview], enemies: List[EnemyPreview], is_subflow: bool, origin_enemy_index: Optional[int]) -> List[Tuple[Vec2, Vec2, Vec2, float]]:
        aim_dir = self.safe_normalize(mouse_px - center_px)
        total_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow)
        total_tiles *= self.scaled_factor(flow, source_radius_tiles)
        start_px, dir0, _ = self.base_start(center_px, aim_dir, flow, source_radius_tiles)
        remaining_px = total_tiles * self.tile_px
        ricochet_left = 0
        if flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False)) or flow.get("ricocheteia_pokemons", False):
            ricochet_left = max(0, int(flow.get("numero_ricochets", 0)))
        segments: List[Tuple[Vec2, Vec2, Vec2, float]] = []
        current_start = start_px
        direction = dir0
        enemy_self = origin_enemy_index if not flow.get("subfluxo_atinge_a_si_mesmo", False) else None
        while remaining_px > 1e-4:
            hit = self.find_hit(current_start, direction, remaining_px, walls, enemies, center_px, enemy_self, flow)
            if hit is None:
                end_px = current_start + direction * remaining_px
                segments.append((current_start, end_px, direction, remaining_px / self.tile_px))
                break
            dist_px, hit_px, normal, hit_type, hit_index = hit
            end_px = hit_px
            segments.append((current_start, end_px, direction, dist_px / self.tile_px))
            remaining_px -= dist_px
            can_reflect = (hit_type == "wall" and flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False))) or (hit_type == "enemy" and flow.get("ricocheteia_pokemons", False))
            if ricochet_left <= 0 or not can_reflect:
                break
            ricochet_left -= 1
            direction = self.safe_normalize(self.reflect(direction, normal))
            current_start = hit_px + direction * 1.5
            remaining_px = max(0.0, remaining_px - 2.0)
        return segments

    def flow_contains_enemy(self, flow_polygons: List[List[Vec2]], circle_infos: List[Tuple[Vec2, float, Dict]], enemy: EnemyPreview) -> bool:
        center_px = enemy.pos
        radius_px = enemy.radius_tiles * self.tile_px
        for pt in self.circle_samples(center_px, radius_px):
            for poly in flow_polygons:
                if self.point_in_polygon(pt, poly):
                    return True
            for c, r, flow in circle_infos:
                if self.point_hit_circle_shape(pt, c, r, flow):
                    return True
        return False


# ---------- data ----------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def safe_float(v, default=0.0) -> float:
    try:
        if v is None or v == "":
            return float(default)
        return float(str(v).replace(",", "."))
    except Exception:
        return float(default)


def safe_int(v, default=0) -> int:
    try:
        if v is None or v == "":
            return int(default)
        return int(round(float(str(v).replace(",", "."))))
    except Exception:
        return int(default)


def parse_csv_rows(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        sample = file.read(4096)
        file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","
        reader = csv.DictReader(file, delimiter=delimiter)
        rows = []
        for row in reader:
            clean = {str(k).strip(): (str(v).strip() if v is not None else "") for k, v in row.items()}
            rows.append(clean)
        return rows


def candidate_roots() -> List[str]:
    roots = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    for root in (cwd, script_dir, os.path.dirname(cwd), os.path.dirname(script_dir)):
        if root and root not in roots:
            roots.append(root)
    return roots


def resolve_data_paths() -> Tuple[str, str]:
    csv_name = "Pokemon Global Server - Ataques.csv"
    json_name = "Pokemon Global Server - Fluxos.json"
    roots = candidate_roots()
    data_candidates = []
    fallback_csv = None
    for root in roots:
        data_dir = os.path.join(root, "Dados")
        data_candidates.append((os.path.join(data_dir, csv_name), os.path.join(data_dir, json_name)))
        direct_csv = os.path.join(root, csv_name)
        if os.path.exists(direct_csv) and fallback_csv is None:
            fallback_csv = direct_csv
    for csv_path, json_path in data_candidates:
        if os.path.exists(csv_path):
            return csv_path, json_path
    if fallback_csv is not None:
        root = os.path.dirname(fallback_csv)
        return fallback_csv, os.path.join(root, "Dados", json_name)
    root = roots[0] if roots else os.getcwd()
    return os.path.join(root, "Dados", csv_name), os.path.join(root, "Dados", json_name)


def load_attacks(csv_path: str) -> List[dict]:
    if not os.path.exists(csv_path):
        return []
    rows = parse_csv_rows(csv_path)
    relevant = []
    for row in rows:
        estilo = row.get("Estilo", "").strip().lower()
        if estilo not in {"tiro", "area"}:
            continue
        relevant.append({
            "Ataque": row.get("Ataque", "").strip(),
            "Tipo": row.get("Tipo", "").strip().lower(),
            "Estilo": estilo,
        })
    relevant.sort(key=lambda item: item["Ataque"].lower())
    return relevant


def default_flow(is_subflow: bool = False) -> Dict:
    flow = {
        "visible": True,
        "alcance": 6.0,
        "largura_teto": 1.0,
        "largura_base": 1.0,
        "grudado": True,
        "offset": 0.0,
        "espacamento": 0.0,
        "faixas": 0,
        "largura_faixa": 1.0,
        "repeticao_faixas": True,
        "faixas_ciclicas": False,
        "distancia_faixa": 2.0,
        "hastes": "reto",
        "pontos_curvatura": 0,
        "curvatura_circular": True,
        "curvaturas_ciclicas": False,
        "distancia_entre_curvaturas": 2.0,
        "invertido": True,
        "curvatura_1": 0.0,
        "curvatura_2": 0.0,
        "curvatura_3": 0.0,
        "curvatura_4": 0.0,
        "curvatura_5": 0.0,
        "curvatura_6": 0.0,
        "circular": False,
        "centralizar": False,
        "raio": 2.0,
        "shape": "normal",
        "tamanho_elementos": 0.6,
        "quantidade_elementos": 8,
        "ricocheteia_objetos": False,
        "ricocheteia_pokemons": False,
        "atravessa_objetos": False,
        "atravessa_pokemons": False,
        "numero_ricochets": 1,
        "escalonavel": False,
        "intensidade_dano": 1.0,
        "subfluxo_atinge_a_si_mesmo": False,
        "expanded": True,
        "subfluxos": [],
    }
    if not is_subflow:
        flow["ajustavel"] = False
        flow["alcance_min"] = 3.0
        flow["alcance_max"] = 9.0
    return flow


def sanitize_flow(raw: Dict, is_subflow: bool = False) -> Dict:
    base = default_flow(is_subflow)
    data = copy.deepcopy(base)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in data:
                data[key] = value
    for key, field in FIELD_DEFS.items():
        if key not in data:
            continue
        kind = field["kind"]
        if kind == "bool":
            data[key] = bool(data.get(key, base.get(key, False)))
        elif kind == "int":
            data[key] = int(clamp(safe_int(data.get(key), base.get(key, 0)), field["min"], field["max"]))
        elif kind == "float":
            data[key] = float(clamp(safe_float(data.get(key), base.get(key, 0.0)), field["min"], field["max"]))
        elif kind == "choice":
            options = field["options"]
            data[key] = data.get(key, base.get(key)) if data.get(key) in options else base.get(key)
    if data["ajustavel"] if "ajustavel" in data else False:
        data["alcance_max"] = max(data["alcance_min"], data["alcance_max"])
    data["subfluxos"] = [sanitize_flow(item, True) for item in data.get("subfluxos", [])[:MAX_SUBFLOWS]]
    return data


def default_attack_entry() -> Dict:
    return {
        "test_diameter": DEFAULT_TEST_DIAMETER,
        "fluxos": [],
    }


def sanitize_attack_entry(raw: Dict) -> Dict:
    data = default_attack_entry()
    if isinstance(raw, dict):
        if "test_diameter" in raw:
            data["test_diameter"] = clamp(safe_float(raw.get("test_diameter"), DEFAULT_TEST_DIAMETER), 0.3, 8.0)
        fluxos = raw.get("fluxos", [])
        if isinstance(fluxos, list):
            data["fluxos"] = [sanitize_flow(item, False) for item in fluxos[:MAX_FLOWS]]
    return data


def load_fluxos(json_path: str, attacks: List[dict]) -> Dict[str, Dict]:
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
    except Exception:
        return {}
    root = raw.get("fluxos", raw) if isinstance(raw, dict) else {}
    result = {}
    valid_names = {a["Ataque"] for a in attacks}
    for attack_name, value in root.items():
        if attack_name not in valid_names:
            continue
        result[attack_name] = sanitize_attack_entry(value)
    return result


def save_fluxos(json_path: str, flows_by_attack: Dict[str, Dict], attacks: List[dict]) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    lookup = {a["Ataque"]: a for a in attacks}
    payload = {"_meta": {"gerado_por": "EditorFluxos", "versao": 2}, "fluxos": {}}
    for attack_name in sorted(flows_by_attack.keys(), key=lambda x: x.lower()):
        info = sanitize_attack_entry(flows_by_attack[attack_name])
        attack = lookup.get(attack_name, {})
        payload["fluxos"][attack_name] = {
            "ataque": attack_name,
            "tipo": attack.get("Tipo", ""),
            "estilo": attack.get("Estilo", ""),
            "test_diameter": info["test_diameter"],
            "fluxos": info["fluxos"],
        }
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)


# ---------- ui ----------

def draw_text(surface, text, font, color, pos, align="topleft", max_width=None):
    if max_width is None:
        img = font.render(text, True, color)
        rect = img.get_rect(**{align: pos})
        surface.blit(img, rect)
        return rect
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = pos
    max_rect = pygame.Rect(x, y, 0, 0)
    for line in lines:
        img = font.render(line, True, color)
        rect = img.get_rect(topleft=(x, y))
        surface.blit(img, rect)
        y += rect.h + 2
        max_rect.union_ip(rect)
    return max_rect


class EditorFluxos:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("EditorFluxos")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        self.font_xs = pygame.font.SysFont("consolas", 13)
        self.font_sm = pygame.font.SysFont("consolas", 15)
        self.font_md = pygame.font.SysFont("consolas", 18)
        self.font_lg = pygame.font.SysFont("consolas", 24, bold=True)

        self.csv_path, self.json_path = resolve_data_paths()
        self.attacks = load_attacks(self.csv_path)
        self.flows_by_attack = load_fluxos(self.json_path, self.attacks)

        self.selected_attack_index = 0
        self.current_data = default_attack_entry()
        self.preview_origin = Vec2(PREVIEW_W * 0.32, WINDOW_H * 0.54)
        self.tile_px = DEFAULT_TILE_PX
        self.preview_mouse = self.preview_origin + Vec2(240, 0)
        self.renderer = PreviewRenderer(self.tile_px, (PREVIEW_W, WINDOW_H))

        self.attack_scroll = 0.0
        self.panel_scroll = 0.0
        self.filter_text = ""
        self.active_input: Optional[Tuple[str, Optional[str]]] = None
        self.edit_buffers: Dict[str, str] = {}
        self.hold_adjust = None
        self.status_text = ""
        self.status_color = TEXT_MID
        self.status_until = 0

        self.mode = "idle"
        self.wall_first_point: Optional[Vec2] = None
        self.enemies: List[EnemyPreview] = []
        self.walls: List[WallPreview] = []

        self.ui_attack_items = []
        self.ui_button_rects = {}
        self.ui_field_items = []
        self.ui_flow_headers = []
        self.filter_rect = pygame.Rect(0, 0, 0, 0)
        self.attack_list_rect = pygame.Rect(0, 0, 0, 0)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)

        if self.attacks:
            self.select_attack(0)
        else:
            self.status("CSV de ataques não encontrado em Dados/ ou sem estilo tiro/area.", RED)

    def status(self, text: str, color=TEXT_MID):
        self.status_text = text
        self.status_color = color
        self.status_until = pygame.time.get_ticks() + 2400

    def current_attack(self) -> Optional[Dict]:
        if not self.attacks:
            return None
        idx = int(clamp(self.selected_attack_index, 0, len(self.attacks) - 1))
        return self.attacks[idx]

    def attack_entry(self, name: str) -> Dict:
        return sanitize_attack_entry(self.flows_by_attack.get(name, default_attack_entry()))

    def select_attack(self, index: int):
        self.selected_attack_index = int(clamp(index, 0, max(0, len(self.attacks) - 1)))
        attack = self.current_attack()
        if not attack:
            return
        self.current_data = self.attack_entry(attack["Ataque"])
        self.panel_scroll = 0.0
        self.active_input = None
        self.edit_buffers.clear()
        self.status(f"Ataque selecionado: {attack['Ataque']}", ACCENT)

    def save_current_attack_entry(self):
        attack = self.current_attack()
        if not attack:
            return
        self.flows_by_attack[attack["Ataque"]] = sanitize_attack_entry(self.current_data)

    def save_all(self):
        self.save_current_attack_entry()
        try:
            save_fluxos(self.json_path, self.flows_by_attack, self.attacks)
            self.status(f"Salvo em {self.json_path}", GREEN)
        except Exception as exc:
            self.status(f"Erro ao salvar: {exc}", RED)

    def reload_all(self):
        self.attacks = load_attacks(self.csv_path)
        self.flows_by_attack = load_fluxos(self.json_path, self.attacks)
        if self.attacks:
            idx = min(self.selected_attack_index, len(self.attacks) - 1)
            self.select_attack(idx)
            self.status("CSV/JSON recarregados.", GREEN)
        else:
            self.current_data = default_attack_entry()
            self.status("Não foi possível recarregar ataques.", RED)

    def filtered_attacks(self) -> List[Dict]:
        token = self.filter_text.strip().lower()
        if not token:
            return self.attacks
        return [attack for attack in self.attacks if token in attack["Ataque"].lower()]

    def find_attack_index(self, name: str) -> Optional[int]:
        for i, attack in enumerate(self.attacks):
            if attack["Ataque"] == name:
                return i
        return None

    def flows(self) -> List[Dict]:
        return self.current_data.setdefault("fluxos", [])

    def commit_active_input(self):
        if self.active_input is None:
            return
        mode, key = self.active_input
        if mode == "filter":
            self.active_input = None
            return
        if mode == "global" and key == "test_diameter":
            field = FIELD_DEFS[key]
            value = clamp(safe_float(self.edit_buffers.get(key, ""), self.current_data.get("test_diameter", DEFAULT_TEST_DIAMETER)), field["min"], field["max"])
            self.current_data["test_diameter"] = value
        elif mode == "field" and key:
            obj, field_key = self.resolve_field_target(key)
            if obj is not None and field_key in FIELD_DEFS:
                field = FIELD_DEFS[field_key]
                kind = field["kind"]
                raw = self.edit_buffers.get(key, "")
                if kind == "float":
                    value = clamp(safe_float(raw, obj.get(field_key, 0.0)), field["min"], field["max"])
                    obj[field_key] = float(value)
                elif kind == "int":
                    value = clamp(safe_int(raw, obj.get(field_key, 0)), field["min"], field["max"])
                    obj[field_key] = int(value)
                elif kind == "choice":
                    opts = field["options"]
                    if raw in opts:
                        obj[field_key] = raw
            self.normalize_current()
        self.active_input = None

    def normalize_current(self):
        self.current_data = sanitize_attack_entry(self.current_data)

    def resolve_field_target(self, token: str):
        parts = token.split("|")
        if len(parts) == 2 and parts[0].startswith("flow"):
            idx = safe_int(parts[0][4:], -1)
            if 0 <= idx < len(self.flows()):
                return self.flows()[idx], parts[1]
        if len(parts) == 3 and parts[0].startswith("flow") and parts[1].startswith("sub"):
            fidx = safe_int(parts[0][4:], -1)
            sidx = safe_int(parts[1][3:], -1)
            if 0 <= fidx < len(self.flows()):
                subs = self.flows()[fidx].setdefault("subfluxos", [])
                if 0 <= sidx < len(subs):
                    return subs[sidx], parts[2]
        return None, None

    def start_edit(self, token: str, initial: str):
        self.active_input = ("field" if token != "test_diameter" else "global", token)
        self.edit_buffers[token] = initial

    def format_value(self, value, kind: str) -> str:
        if kind == "bool":
            return "on" if value else "off"
        if kind == "int":
            return str(int(value))
        if kind == "choice":
            return str(value)
        try:
            value = float(value)
        except Exception:
            return str(value)
        if abs(value - int(value)) < 1e-9:
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def begin_hold(self, token: str, direction: int):
        self.hold_adjust = {
            "token": token,
            "direction": direction,
            "next_time": pygame.time.get_ticks() + 320,
            "period": 58,
        }
        self.adjust_field(token, direction)

    def stop_hold(self):
        self.hold_adjust = None

    def adjust_field(self, token: str, direction: int):
        obj, field_key = self.resolve_field_target(token)
        if obj is None:
            if token == "test_diameter":
                field = FIELD_DEFS[token]
                step = field.get("step", 1)
                self.current_data["test_diameter"] = clamp(self.current_data.get("test_diameter", DEFAULT_TEST_DIAMETER) + step * direction, field["min"], field["max"])
            return
        field = FIELD_DEFS.get(field_key)
        if not field:
            return
        kind = field["kind"]
        if kind == "bool":
            obj[field_key] = not bool(obj.get(field_key, False))
        elif kind == "choice":
            opts = field["options"]
            idx = opts.index(obj.get(field_key, opts[0])) if obj.get(field_key, opts[0]) in opts else 0
            obj[field_key] = opts[(idx + direction) % len(opts)]
        else:
            step = field.get("step", 1)
            if field_key in ("largura_base", "largura_teto") and obj.get("grudado", False):
                step = 1.0
            value = obj.get(field_key, 0)
            mods = pygame.key.get_mods()
            mult = 1.0
            if mods & pygame.KMOD_SHIFT:
                mult = 10.0
            elif mods & pygame.KMOD_CTRL:
                mult = 0.2
            value = value + step * direction * mult
            value = clamp(value, field["min"], field["max"])
            obj[field_key] = int(round(value)) if kind == "int" else round(float(value), 4)
        self.normalize_current()

    def toggle_field_token(self, token: str):
        obj, field_key = self.resolve_field_target(token)
        if obj is None:
            return
        field = FIELD_DEFS.get(field_key)
        if not field:
            return
        if field["kind"] == "bool":
            obj[field_key] = not bool(obj.get(field_key, False))
        elif field["kind"] == "choice":
            opts = field["options"]
            current = obj.get(field_key, opts[0])
            idx = opts.index(current) if current in opts else 0
            obj[field_key] = opts[(idx + 1) % len(opts)]
        self.normalize_current()

    def attack_select_by_name(self, name: str):
        idx = self.find_attack_index(name)
        if idx is not None:
            self.commit_active_input()
            self.select_attack(idx)

    def create_flow(self):
        attack = self.current_attack()
        if not attack:
            return
        flows = self.flows()
        if len(flows) >= MAX_FLOWS:
            self.status("Máximo de 5 fluxos por ataque.", RED)
            return
        flows.append(default_flow(False))
        self.normalize_current()
        self.status("Fluxo criado.", GREEN)

    def clone_flow(self, fidx: int):
        flows = self.flows()
        if not (0 <= fidx < len(flows)):
            return
        if len(flows) >= MAX_FLOWS:
            self.status("Máximo de 5 fluxos por ataque.", RED)
            return
        clone = sanitize_flow(copy.deepcopy(flows[fidx]), False)
        clone["expanded"] = True
        flows.insert(fidx + 1, clone)
        self.normalize_current()
        self.status("Fluxo clonado.", GREEN)

    def add_subflow(self, fidx: int):
        flows = self.flows()
        if not (0 <= fidx < len(flows)):
            return
        subs = flows[fidx].setdefault("subfluxos", [])
        if len(subs) >= MAX_SUBFLOWS:
            self.status("Máximo de 5 subfluxos por fluxo.", RED)
            return
        subs.append(default_flow(True))
        self.normalize_current()
        self.status("Subfluxo criado.", GREEN)

    def clone_subflow(self, fidx: int, sidx: int):
        flows = self.flows()
        if not (0 <= fidx < len(flows)):
            return
        subs = flows[fidx].setdefault("subfluxos", [])
        if not (0 <= sidx < len(subs)):
            return
        if len(subs) >= MAX_SUBFLOWS:
            self.status("Máximo de 5 subfluxos por fluxo.", RED)
            return
        clone = sanitize_flow(copy.deepcopy(subs[sidx]), True)
        clone["expanded"] = True
        subs.insert(sidx + 1, clone)
        self.normalize_current()
        self.status("Subfluxo clonado.", GREEN)

    def remove_flow(self, fidx: int):
        flows = self.flows()
        if 0 <= fidx < len(flows):
            del flows[fidx]
            self.normalize_current()
            self.status("Fluxo removido.", ORANGE)

    def remove_subflow(self, fidx: int, sidx: int):
        flows = self.flows()
        if 0 <= fidx < len(flows):
            subs = flows[fidx].setdefault("subfluxos", [])
            if 0 <= sidx < len(subs):
                del subs[sidx]
                self.normalize_current()
                self.status("Subfluxo removido.", ORANGE)

    def toggle_expand_flow(self, fidx: int):
        flows = self.flows()
        if 0 <= fidx < len(flows):
            flows[fidx]["expanded"] = not flows[fidx].get("expanded", True)

    def toggle_expand_subflow(self, fidx: int, sidx: int):
        flows = self.flows()
        if 0 <= fidx < len(flows):
            subs = flows[fidx].setdefault("subfluxos", [])
            if 0 <= sidx < len(subs):
                subs[sidx]["expanded"] = not subs[sidx].get("expanded", True)

    def flow_token(self, fidx: int, key: str) -> str:
        return f"flow{fidx}|{key}"

    def subflow_token(self, fidx: int, sidx: int, key: str) -> str:
        return f"flow{fidx}|sub{sidx}|{key}"

    def draw_preview(self):
        self.renderer.tile_px = self.tile_px
        self.screen.fill(BG_PREVIEW, pygame.Rect(0, 0, PREVIEW_W, WINDOW_H))
        # grid
        for x in range(-100, 120):
            sx = self.preview_origin.x + x * self.tile_px
            color = GRID_AXIS if x == 0 else (GRID_MAJOR if x % 5 == 0 else GRID_MINOR)
            pygame.draw.line(self.screen, color, (sx, 0), (sx, WINDOW_H), 1)
        for y in range(-100, 100):
            sy = self.preview_origin.y + y * self.tile_px
            color = GRID_AXIS if y == 0 else (GRID_MAJOR if y % 5 == 0 else GRID_MINOR)
            pygame.draw.line(self.screen, color, (0, sy), (PREVIEW_W, sy), 1)

        mouse = self.preview_mouse
        aim_dir = self.renderer.safe_normalize(mouse - self.preview_origin)
        aim_start = self.preview_origin + aim_dir * max(8.0, self.test_radius_tiles() * self.tile_px)
        aim_end = self.preview_origin + aim_dir * (40 * self.tile_px)
        pygame.draw.line(self.screen, (188, 194, 210), aim_start, aim_end, 1)

        enemy_hits_for_subflows: List[Tuple[int, PreviewHit, Dict, int]] = []
        all_flow_hit_polygons = []
        circle_infos = []

        flows = self.flows()
        for fidx, flow in enumerate(flows):
            if not flow.get("visible", True):
                continue
            fill = FLOW_FILL[fidx % len(FLOW_FILL)]
            border = FLOW_STROKE[fidx % len(FLOW_STROKE)]
            hit_polys, hit_circles, hits = self.draw_single_flow(flow, self.preview_origin, mouse, self.test_radius_tiles(), fill, border, False, None)
            all_flow_hit_polygons.extend(hit_polys)
            circle_infos.extend([(c, r, flow) for c, r in hit_circles])
            for hit in hits:
                enemy_hits_for_subflows.append((fidx, hit, flow, hit.enemy_index))

        # subflows behind objects/pokémons, like the fluxo normal
        for fidx, hit, flow, enemy_idx in enemy_hits_for_subflows:
            subs = flow.get("subfluxos", [])
            for sidx, sub in enumerate(subs):
                if not sub.get("visible", True):
                    continue
                fill = SUBFLOW_FILL[sidx % len(SUBFLOW_FILL)]
                border = SUBFLOW_STROKE[sidx % len(SUBFLOW_STROKE)]
                self.draw_single_flow(sub, hit.enemy_center_px, hit.enemy_center_px + hit.direction * self.tile_px * 10, self.enemies[enemy_idx].radius_tiles, fill, border, True, enemy_idx)

        # walls
        for wall in self.walls:
            a = self.world_to_preview(wall.a)
            b = self.world_to_preview(wall.b)
            pygame.draw.line(self.screen, (228, 232, 240), a, b, 4)
            pygame.draw.line(self.screen, (80, 88, 102), a, b, 1)

        # source pokemon
        src_r = self.test_radius_tiles() * self.tile_px
        pygame.draw.circle(self.screen, (76, 104, 178), (int(self.preview_origin.x), int(self.preview_origin.y)), int(src_r + 4))
        pygame.draw.circle(self.screen, (220, 228, 236), (int(self.preview_origin.x), int(self.preview_origin.y)), int(src_r))
        pygame.draw.circle(self.screen, (98, 132, 192), (int(self.preview_origin.x), int(self.preview_origin.y)), int(src_r * 0.60))

        # enemies
        for idx, enemy in enumerate(self.enemies):
            enemy_center = self.world_to_preview(enemy.pos)
            preview_enemy = EnemyPreview(enemy_center, enemy.radius_tiles)
            hit = self.renderer.flow_contains_enemy(all_flow_hit_polygons, circle_infos, preview_enemy)
            radius_px = enemy.radius_tiles * self.tile_px
            ring = RED if hit else (32, 38, 46)
            inner = (196, 225, 196) if hit else (214, 220, 232)
            pygame.draw.circle(self.screen, ring, (int(enemy_center.x), int(enemy_center.y)), int(radius_px + 4))
            pygame.draw.circle(self.screen, inner, (int(enemy_center.x), int(enemy_center.y)), int(radius_px))
            pygame.draw.circle(self.screen, (136, 166, 146) if hit else (152, 160, 180), (int(enemy_center.x), int(enemy_center.y)), int(radius_px * 0.58))
            draw_text(self.screen, f"Inimigo {idx+1}", self.font_xs, TEXT, (enemy_center.x, enemy_center.y + radius_px + 8), align="midtop")

        # temporary wall anchor
        if self.mode == "add_wall" and self.wall_first_point is not None:
            pygame.draw.line(self.screen, YELLOW, self.world_to_preview(self.wall_first_point), mouse, 2)

        hud = [
            f"Mouse: ({(mouse.x-self.preview_origin.x)/self.tile_px:.2f}t, {(mouse.y-self.preview_origin.y)/self.tile_px:.2f}t)",
            f"Zoom: {self.tile_px:.0f}px/tile",
            f"Pokémon teste: {self.current_data.get('test_diameter', DEFAULT_TEST_DIAMETER):.2f} tiles",
            f"Modo: {self.mode}",
        ]
        for i, line in enumerate(hud):
            draw_text(self.screen, line, self.font_sm, TEXT_MID, (14, 12 + i * 20))

    def draw_single_flow(self, flow: Dict, source_center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, fill_rgba, border_color, is_subflow: bool, origin_enemy_index: Optional[int]):
        hit_polygons: List[List[Vec2]] = []
        hit_circles: List[Tuple[Vec2, float]] = []
        hit_enemies: List[PreviewHit] = []
        preview_walls = [WallPreview(self.world_to_preview(wall.a), self.world_to_preview(wall.b)) for wall in self.walls]
        preview_enemies = [EnemyPreview(self.world_to_preview(enemy.pos), enemy.radius_tiles) for enemy in self.enemies]
        segments = self.renderer.build_segments(flow, source_center_px, mouse_px, source_radius_tiles, preview_walls, preview_enemies, is_subflow, origin_enemy_index)
        if flow.get("circular", False):
            circle_center, radius_px, exit_dir = self.renderer.visible_circle_center(source_center_px, mouse_px, source_radius_tiles, flow, is_subflow)
            pts = self.renderer.circle_outline(circle_center, radius_px, flow)
            if len(pts) >= 3:
                int_pts = [(int(round(p.x)), int(round(p.y))) for p in pts]
                pygame.draw.polygon(self.screen, fill_rgba, int_pts)
                pygame.draw.polygon(self.screen, border_color, int_pts, 2)
                hit_circles.append((circle_center, radius_px))
                for idx, enemy in enumerate(preview_enemies):
                    if origin_enemy_index is not None and idx == origin_enemy_index and not flow.get("subfluxo_atinge_a_si_mesmo", False):
                        continue
                    if self.renderer.flow_contains_enemy([], [(circle_center, radius_px, flow)], enemy):
                        hit_enemies.append(PreviewHit(idx, enemy.pos, exit_dir))
            return hit_polygons, hit_circles, hit_enemies

        if not segments:
            return hit_polygons, hit_circles, hit_enemies

        total_len_tiles = sum(seg[3] for seg in segments)
        drawn_polys = []
        current_source = source_center_px
        current_radius = source_radius_tiles
        # build per segment, but preserve flow when it crosses itself by only drawing additive polygons.
        for seg_idx, (seg_start, seg_end, seg_dir, seg_len_tiles) in enumerate(segments):
            temp_flow = copy.deepcopy(flow)
            temp_flow["espacamento"] = 0.0
            temp_flow["offset"] = 0.0 if seg_idx > 0 else flow.get("offset", 0.0)
            temp_flow["grudado"] = flow.get("grudado", False) if seg_idx == 0 else False
            temp_flow["ajustavel"] = False
            temp_flow["alcance"] = max(0.1, seg_len_tiles)
            points, widths_px, _, axis_dir, start_center_px, _ = self.renderer.build_centerline(temp_flow, seg_start if seg_idx > 0 else current_source, seg_end, 0.0 if seg_idx > 0 else current_radius, True)
            poly = self.renderer.polygon_from_centerline(points, widths_px, current_source if seg_idx == 0 else seg_start, current_radius if seg_idx == 0 else 0.0, temp_flow, axis_dir)
            if len(poly) >= 3:
                int_pts = [(int(round(p.x)), int(round(p.y))) for p in poly]
                pygame.draw.polygon(self.screen, fill_rgba, int_pts)
                pygame.draw.polygon(self.screen, border_color, int_pts, 2)
                drawn_polys.append(poly)
                hit_polygons.append(poly)

        for idx, enemy in enumerate(preview_enemies):
            if origin_enemy_index is not None and idx == origin_enemy_index and not flow.get("subfluxo_atinge_a_si_mesmo", False):
                continue
            if self.renderer.flow_contains_enemy(drawn_polys, [], enemy):
                last_dir = segments[-1][2] if segments else Vec2(1, 0)
                hit_enemies.append(PreviewHit(idx, enemy.pos, last_dir))

        return hit_polygons, hit_circles, hit_enemies

    def test_radius_tiles(self) -> float:
        return self.current_data.get("test_diameter", DEFAULT_TEST_DIAMETER) * 0.5

    def preview_to_world(self, pos) -> Vec2:
        return (Vec2(pos) - self.preview_origin) / self.tile_px

    def world_to_preview(self, pos: Vec2) -> Vec2:
        return self.preview_origin + pos * self.tile_px

    def draw_button(self, rect: pygame.Rect, label: str, color, fill=(46, 50, 58)):
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, color, rect, 1, border_radius=8)
        draw_text(self.screen, label, self.font_sm, TEXT, rect.center, align="center")

    def draw_panel(self):
        pygame.draw.rect(self.screen, PANEL_BG, pygame.Rect(PANEL_X, 0, PANEL_W, WINDOW_H))
        pygame.draw.line(self.screen, PANEL_STROKE, (PANEL_X, 0), (PANEL_X, WINDOW_H), 1)

        x0 = PANEL_X + 16
        y = 14
        draw_text(self.screen, "EditorFluxos", self.font_lg, TEXT, (x0, y))
        y += 38

        # filter and attack list
        self.filter_rect = pygame.Rect(x0, y, PANEL_W - 32, 32)
        pygame.draw.rect(self.screen, PANEL_BG_2, self.filter_rect, border_radius=8)
        pygame.draw.rect(self.screen, ACCENT if self.active_input == ("filter", None) else PANEL_STROKE, self.filter_rect, 2, border_radius=8)
        draw_text(self.screen, self.filter_text or "filtrar ataque...", self.font_sm, TEXT if self.filter_text else TEXT_DIM, (self.filter_rect.x + 10, self.filter_rect.y + 7))
        y += 40

        self.attack_list_rect = pygame.Rect(x0, y, PANEL_W - 32, 160)
        pygame.draw.rect(self.screen, PANEL_BG_2, self.attack_list_rect, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_STROKE, self.attack_list_rect, 1, border_radius=10)
        self.ui_attack_items = []
        attacks = self.filtered_attacks()
        item_h = 30
        total_h = len(attacks) * item_h
        self.attack_scroll = clamp(self.attack_scroll, 0, max(0, total_h - self.attack_list_rect.h + 8))
        clip = self.screen.get_clip()
        self.screen.set_clip(self.attack_list_rect.inflate(-4, -4))
        yy = self.attack_list_rect.y + 4 - self.attack_scroll
        for attack in attacks:
            rect = pygame.Rect(self.attack_list_rect.x + 4, yy, self.attack_list_rect.w - 8, item_h - 2)
            if rect.bottom >= self.attack_list_rect.y and rect.top <= self.attack_list_rect.bottom:
                selected = self.current_attack() and self.current_attack()["Ataque"] == attack["Ataque"]
                pygame.draw.rect(self.screen, (56, 66, 81) if selected else (44, 49, 58), rect, border_radius=7)
                pygame.draw.rect(self.screen, ACCENT if selected else (58, 64, 74), rect, 1, border_radius=7)
                draw_text(self.screen, attack["Ataque"], self.font_sm, TEXT, (rect.x + 10, rect.y + 6))
                self.ui_attack_items.append((rect.copy(), attack["Ataque"]))
            yy += item_h
        self.screen.set_clip(clip)
        y += 170

        attack = self.current_attack()
        info_rect = pygame.Rect(x0, y, PANEL_W - 32, 38)
        pygame.draw.rect(self.screen, PANEL_BG_2, info_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_STROKE, info_rect, 1, border_radius=8)
        draw_text(self.screen, attack["Ataque"] if attack else "Sem ataque", self.font_md, TEXT, (info_rect.x + 10, info_rect.y + 8))
        y += 46

        btn_w = (PANEL_W - 32 - 8 * 3) // 4
        self.ui_button_rects = {
            "criar_fluxo": pygame.Rect(x0, y, btn_w, 32),
            "salvar": pygame.Rect(x0 + btn_w + 8, y, btn_w, 32),
            "recarregar": pygame.Rect(x0 + (btn_w + 8) * 2, y, btn_w, 32),
            "limpar_objetos": pygame.Rect(x0 + (btn_w + 8) * 3, y, btn_w, 32),
        }
        self.draw_button(self.ui_button_rects["criar_fluxo"], "Criar fluxo", GREEN)
        self.draw_button(self.ui_button_rects["salvar"], "Salvar", ACCENT)
        self.draw_button(self.ui_button_rects["recarregar"], "F5", YELLOW)
        self.draw_button(self.ui_button_rects["limpar_objetos"], "Limpar objs", RED)
        y += 40

        btn2_w = (PANEL_W - 32 - 8 * 2) // 3
        self.ui_button_rects.update({
            "add_enemy": pygame.Rect(x0, y, btn2_w, 30),
            "add_wall": pygame.Rect(x0 + btn2_w + 8, y, btn2_w, 30),
            "remove_obj": pygame.Rect(x0 + (btn2_w + 8) * 2, y, btn2_w, 30),
        })
        self.draw_button(self.ui_button_rects["add_enemy"], "Adicionar inimigo", GREEN if self.mode == "add_enemy" else ACCENT)
        self.draw_button(self.ui_button_rects["add_wall"], "Adicionar parede", GREEN if self.mode == "add_wall" else ACCENT)
        self.draw_button(self.ui_button_rects["remove_obj"], "Remover objeto", GREEN if self.mode == "remove" else ACCENT)
        y += 38

        # test diameter
        test_rect = pygame.Rect(x0, y, PANEL_W - 32, 32)
        pygame.draw.rect(self.screen, PANEL_BG_2, test_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_STROKE, test_rect, 1, border_radius=8)
        draw_text(self.screen, "Diâmetro do pokémon teste", self.font_sm, TEXT, (test_rect.x + 10, test_rect.y + 8))
        token = "test_diameter"
        minus_rect = pygame.Rect(test_rect.right - 124, test_rect.y + 4, 24, 24)
        value_rect = pygame.Rect(test_rect.right - 96, test_rect.y + 4, 64, 24)
        plus_rect = pygame.Rect(test_rect.right - 28, test_rect.y + 4, 24, 24)
        for rect, label in ((minus_rect, "-"), (plus_rect, "+")):
            pygame.draw.rect(self.screen, (32, 36, 42), rect, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_STROKE, rect, 1, border_radius=6)
            draw_text(self.screen, label, self.font_md, TEXT, rect.center, align="center")
        editing = self.active_input == ("global", token)
        pygame.draw.rect(self.screen, (24, 28, 33), value_rect, border_radius=6)
        pygame.draw.rect(self.screen, ACCENT if editing else PANEL_STROKE, value_rect, 2 if editing else 1, border_radius=6)
        draw_text(self.screen, self.edit_buffers.get(token, "") if editing else self.format_value(self.current_data.get("test_diameter", DEFAULT_TEST_DIAMETER), "float"), self.font_sm, TEXT, value_rect.center, align="center")
        self.ui_field_items = [
            {"rect": minus_rect.copy(), "action": "minus", "token": token},
            {"rect": plus_rect.copy(), "action": "plus", "token": token},
            {"rect": value_rect.copy(), "action": "edit_global", "token": token},
        ]
        y += 40

        self.panel_rect = pygame.Rect(x0, y, PANEL_W - 32, WINDOW_H - y - 60)
        pygame.draw.rect(self.screen, PANEL_BG_2, self.panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_STROKE, self.panel_rect, 1, border_radius=10)
        self.ui_flow_headers = []

        content_h = 0
        for fidx, flow in enumerate(self.flows()):
            content_h += 40
            if flow.get("expanded", True):
                content_h += self.estimate_flow_height(flow)
            for sidx, sub in enumerate(flow.get("subfluxos", [])):
                content_h += 34
                if sub.get("expanded", False):
                    content_h += self.estimate_flow_height(sub, True)
        self.panel_scroll = clamp(self.panel_scroll, 0, max(0, content_h - self.panel_rect.h + 16))

        clip = self.screen.get_clip()
        self.screen.set_clip(self.panel_rect.inflate(-4, -4))
        yy = self.panel_rect.y + 8 - self.panel_scroll
        for fidx, flow in enumerate(self.flows()):
            yy = self.draw_flow_block(fidx, flow, yy, False, None)
        self.screen.set_clip(clip)

        footer_y = WINDOW_H - 50
        draw_text(self.screen, f"CSV: {self.csv_path}", self.font_xs, TEXT_DIM, (PANEL_X + 18, footer_y - 8), max_width=PANEL_W - 36)
        draw_text(self.screen, f"JSON: {self.json_path}", self.font_xs, TEXT_DIM, (PANEL_X + 18, footer_y + 10), max_width=PANEL_W - 36)
        if self.status_text and pygame.time.get_ticks() < self.status_until:
            status_rect = pygame.Rect(PANEL_X + 16, WINDOW_H - 92, PANEL_W - 32, 28)
            pygame.draw.rect(self.screen, (22, 25, 30), status_rect, border_radius=8)
            pygame.draw.rect(self.screen, self.status_color, status_rect, 1, border_radius=8)
            draw_text(self.screen, self.status_text, self.font_xs, self.status_color, (status_rect.x + 10, status_rect.y + 7), max_width=status_rect.w - 20)
        elif self.status_text:
            self.status_text = ""

    def estimate_flow_height(self, flow: Dict, is_subflow: bool = False) -> int:
        h = 0
        for group in FIELD_GROUPS:
            keys = self.visible_keys_for_group(flow, group["keys"], is_subflow)
            if not keys:
                continue
            h += 26 + len(keys) * 34
        h += 34
        return h

    def visible_keys_for_group(self, flow: Dict, keys: List[str], is_subflow: bool) -> List[str]:
        out = []
        for key in keys:
            if key in ("alcance_min", "alcance_max") and not flow.get("ajustavel", False):
                continue
            if key == "alcance" and flow.get("ajustavel", False) and not is_subflow:
                continue
            if key == "espacamento" and flow.get("grudado", False):
                continue
            if key in ("distancia_faixa",) and not flow.get("faixas_ciclicas", False):
                continue
            if key == "numero_ricochets" and not (flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False)) or flow.get("ricocheteia_pokemons", False)):
                continue
            if key in ("distancia_entre_curvaturas", "invertido") and not flow.get("curvaturas_ciclicas", False):
                continue
            if key.startswith("curvatura_") and key[-1].isdigit() and not flow.get("curvaturas_ciclicas", False):
                count = int(flow.get("pontos_curvatura", 0))
                if int(key.split("_")[-1]) > count:
                    continue
            if key in ("centralizar", "raio", "shape") and not flow.get("circular", False):
                continue
            if key in ("tamanho_elementos", "quantidade_elementos") and not (flow.get("circular", False) and flow.get("shape", "normal") != "normal"):
                continue
            if key == "subfluxo_atinge_a_si_mesmo" and is_subflow:
                continue
            if key == "ajustavel" and is_subflow:
                continue
            out.append(key)
        return out

    def draw_flow_block(self, fidx: int, flow: Dict, y: float, is_subflow: bool, parent_idx: Optional[int]):
        x = self.panel_rect.x + 8 + (22 if is_subflow else 0)
        w = self.panel_rect.w - 16 - (22 if is_subflow else 0)
        header = pygame.Rect(x, y, w, 32)
        pygame.draw.rect(self.screen, PANEL_BG_3 if not is_subflow else (40, 44, 52), header, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_STROKE, header, 1, border_radius=8)
        title = f"Subfluxo {parent_idx+1}.{fidx+1}" if is_subflow else f"Fluxo {fidx+1}"
        draw_text(self.screen, ("â–¼ " if flow.get("expanded", True) else "â–¶ ") + title, self.font_sm, TEXT, (header.x + 8, header.y + 8))

        vis_rect = pygame.Rect(header.right - 178, header.y + 4, 26, 24)
        clone_rect = pygame.Rect(header.right - 148, header.y + 4, 50, 24)
        add_sub_rect = pygame.Rect(header.right - 94, header.y + 4, 40, 24)
        del_rect = pygame.Rect(header.right - 50, header.y + 4, 42, 24)
        self.draw_button(vis_rect, "V", GREEN if flow.get("visible", True) else RED, fill=(30, 34, 40))
        self.draw_button(clone_rect, "Clone", ACCENT, fill=(30, 34, 40))
        if not is_subflow:
            self.draw_button(add_sub_rect, "+Sub", YELLOW, fill=(30, 34, 40))
        else:
            pygame.draw.rect(self.screen, (30, 34, 40), add_sub_rect, border_radius=8)
            pygame.draw.rect(self.screen, (50, 55, 65), add_sub_rect, 1, border_radius=8)
            draw_text(self.screen, "--", self.font_xs, TEXT_DIM, add_sub_rect.center, align="center")
        self.draw_button(del_rect, "Del", RED, fill=(30, 34, 40))
        self.ui_flow_headers.append({
            "expand": header.copy(), "visible": vis_rect.copy(), "clone": clone_rect.copy(),
            "add_sub": add_sub_rect.copy(), "delete": del_rect.copy(),
            "fidx": fidx, "is_sub": is_subflow, "parent": parent_idx,
        })
        y += 38

        if flow.get("expanded", True):
            for group in FIELD_GROUPS:
                keys = self.visible_keys_for_group(flow, group["keys"], is_subflow)
                if not keys:
                    continue
                draw_text(self.screen, group["title"], self.font_sm, ACCENT, (x + 4, y + 2))
                pygame.draw.line(self.screen, (65, 72, 84), (x + 4, y + 20), (x + w - 4, y + 20), 1)
                y += 24
                for key in keys:
                    token = self.subflow_token(parent_idx, fidx, key) if is_subflow else self.flow_token(fidx, key)
                    y = self.draw_field_row(flow, token, key, x, y, w)
                y += 6

        if not is_subflow:
            subs = flow.get("subfluxos", [])
            for sidx, sub in enumerate(subs):
                y = self.draw_flow_block(sidx, sub, y, True, fidx)
        return y + 2

    def draw_field_row(self, obj: Dict, token: str, key: str, x: int, y: float, w: int):
        field = FIELD_DEFS[key]
        row = pygame.Rect(x, y, w, 30)
        pygame.draw.rect(self.screen, (44, 49, 58), row, border_radius=8)
        pygame.draw.rect(self.screen, (66, 72, 84), row, 1, border_radius=8)
        draw_text(self.screen, field["label"], self.font_sm, TEXT, (row.x + 10, row.y + 7))
        kind = field["kind"]
        if kind in {"bool", "choice"}:
            value_rect = pygame.Rect(row.right - 128, row.y + 4, 118, 22)
            pygame.draw.rect(self.screen, (26, 29, 34), value_rect, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_STROKE, value_rect, 1, border_radius=6)
            draw_text(self.screen, self.format_value(obj.get(key), kind), self.font_sm, ACCENT if kind == "choice" else (GREEN if obj.get(key) else TEXT_DIM), value_rect.center, align="center")
            self.ui_field_items.append({"rect": value_rect.copy(), "action": "toggle", "token": token})
        else:
            minus_rect = pygame.Rect(row.right - 124, row.y + 4, 24, 22)
            value_rect = pygame.Rect(row.right - 96, row.y + 4, 64, 22)
            plus_rect = pygame.Rect(row.right - 28, row.y + 4, 24, 22)
            for rect, label in ((minus_rect, "-"), (plus_rect, "+")):
                pygame.draw.rect(self.screen, (28, 31, 37), rect, border_radius=6)
                pygame.draw.rect(self.screen, PANEL_STROKE, rect, 1, border_radius=6)
                draw_text(self.screen, label, self.font_md, TEXT, rect.center, align="center")
            editing = self.active_input == ("field", token)
            pygame.draw.rect(self.screen, (24, 28, 33), value_rect, border_radius=6)
            pygame.draw.rect(self.screen, ACCENT if editing else PANEL_STROKE, value_rect, 2 if editing else 1, border_radius=6)
            txt = self.edit_buffers.get(token, "") if editing else self.format_value(obj.get(key), kind)
            draw_text(self.screen, txt, self.font_sm, TEXT, value_rect.center, align="center")
            self.ui_field_items.extend([
                {"rect": minus_rect.copy(), "action": "minus", "token": token},
                {"rect": plus_rect.copy(), "action": "plus", "token": token},
                {"rect": value_rect.copy(), "action": "edit", "token": token},
            ])
        return y + 34

    def object_at_point(self, pos: Vec2):
        for idx, enemy in enumerate(self.enemies):
            if (self.world_to_preview(enemy.pos) - pos).length() <= enemy.radius_tiles * self.tile_px + 4:
                return ("enemy", idx)
        for idx, wall in enumerate(self.walls):
            if self.distance_point_to_segment(pos, self.world_to_preview(wall.a), self.world_to_preview(wall.b)) <= 8.0:
                return ("wall", idx)
        return None

    def distance_point_to_segment(self, p: Vec2, a: Vec2, b: Vec2) -> float:
        ab = b - a
        if ab.length_squared() <= 1e-8:
            return (p - a).length()
        t = clamp((p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
        proj = a + ab * t
        return (p - proj).length()

    def handle_preview_click(self, pos: Tuple[int, int]):
        self.preview_mouse = Vec2(pos)
        if self.mode == "add_enemy":
            if len(self.enemies) < MAX_ENEMIES:
                self.enemies.append(EnemyPreview(self.preview_to_world(pos), self.current_data.get("test_diameter", DEFAULT_TEST_DIAMETER) * 0.5))
                self.status("Pokémon inimigo adicionado.", GREEN)
            else:
                self.status("Máximo de inimigos atingido.", RED)
            return
        if self.mode == "add_wall":
            world_pos = self.preview_to_world(pos)
            if self.wall_first_point is None:
                self.wall_first_point = world_pos
                self.status("Primeiro ponto da parede marcado.", YELLOW)
            else:
                if len(self.walls) < MAX_WALLS:
                    self.walls.append(WallPreview(self.wall_first_point, world_pos))
                    self.status("Parede adicionada.", GREEN)
                else:
                    self.status("Máximo de objetos atingido.", RED)
                self.wall_first_point = None
            return
        if self.mode == "remove":
            target = self.object_at_point(Vec2(pos))
            if target is None:
                self.mode = "idle"
                self.status("Saiu do modo remover.", TEXT_MID)
                return
            kind, idx = target
            if kind == "enemy":
                del self.enemies[idx]
                self.status("Inimigo removido.", ORANGE)
            elif kind == "wall":
                del self.walls[idx]
                self.status("Parede removida.", ORANGE)
            return

    def handle_mouse_down(self, event):
        pos = Vec2(event.pos)
        if pos.x < PREVIEW_W:
            self.commit_active_input()
            self.handle_preview_click(event.pos)
            return
        if self.filter_rect.collidepoint(event.pos):
            self.commit_active_input()
            self.active_input = ("filter", None)
            return
        for rect, attack_name in self.ui_attack_items:
            if rect.collidepoint(event.pos):
                self.attack_select_by_name(attack_name)
                return
        for key, rect in self.ui_button_rects.items():
            if rect.collidepoint(event.pos):
                self.commit_active_input()
                if key == "criar_fluxo":
                    self.create_flow()
                elif key == "salvar":
                    self.save_all()
                elif key == "recarregar":
                    self.reload_all()
                elif key == "limpar_objetos":
                    self.enemies.clear(); self.walls.clear(); self.wall_first_point = None
                    self.status("Objetos de teste limpos.", ORANGE)
                elif key == "add_enemy":
                    self.mode = "idle" if self.mode == "add_enemy" else "add_enemy"
                    self.wall_first_point = None
                elif key == "add_wall":
                    self.mode = "idle" if self.mode == "add_wall" else "add_wall"
                    self.wall_first_point = None
                elif key == "remove_obj":
                    self.mode = "idle" if self.mode == "remove" else "remove"
                    self.wall_first_point = None
                return
        for item in self.ui_flow_headers:
            fidx, is_sub, parent = item["fidx"], item["is_sub"], item["parent"]
            if item["visible"].collidepoint(event.pos):
                self.commit_active_input()
                if is_sub:
                    subs = self.flows()[parent].setdefault("subfluxos", [])
                    subs[fidx]["visible"] = not subs[fidx].get("visible", True)
                else:
                    self.flows()[fidx]["visible"] = not self.flows()[fidx].get("visible", True)
                return
            if item["clone"].collidepoint(event.pos):
                self.commit_active_input()
                if is_sub:
                    self.clone_subflow(parent, fidx)
                else:
                    self.clone_flow(fidx)
                return
            if item["add_sub"].collidepoint(event.pos) and not is_sub:
                self.commit_active_input()
                self.add_subflow(fidx)
                return
            if item["delete"].collidepoint(event.pos):
                self.commit_active_input()
                if is_sub:
                    self.remove_subflow(parent, fidx)
                else:
                    self.remove_flow(fidx)
                return
            if item["expand"].collidepoint(event.pos):
                self.commit_active_input()
                if is_sub:
                    self.toggle_expand_subflow(parent, fidx)
                else:
                    self.toggle_expand_flow(fidx)
                return
        for item in self.ui_field_items:
            if item["rect"].collidepoint(event.pos):
                self.commit_active_input()
                action = item["action"]
                token = item["token"]
                if action == "toggle":
                    self.toggle_field_token(token)
                elif action == "minus":
                    self.begin_hold(token, -1)
                elif action == "plus":
                    self.begin_hold(token, +1)
                elif action == "edit":
                    obj, field_key = self.resolve_field_target(token)
                    if obj is not None:
                        self.active_input = ("field", token)
                        self.edit_buffers[token] = self.format_value(obj.get(field_key), FIELD_DEFS[field_key]["kind"])
                elif action == "edit_global":
                    self.active_input = ("global", token)
                    self.edit_buffers[token] = self.format_value(self.current_data.get("test_diameter", DEFAULT_TEST_DIAMETER), "float")
                return
        self.commit_active_input()

    def handle_mouse_up(self, event):
        if event.button == 1:
            self.stop_hold()

    def handle_mouse_wheel(self, event):
        mx, my = pygame.mouse.get_pos()
        if mx < PREVIEW_W:
            self.tile_px = clamp(self.tile_px + event.y * 3, MIN_TILE_PX, MAX_TILE_PX)
            return
        if self.attack_list_rect.collidepoint((mx, my)):
            self.attack_scroll = max(0.0, self.attack_scroll - event.y * 26)
        elif self.panel_rect.collidepoint((mx, my)):
            self.panel_scroll = max(0.0, self.panel_scroll - event.y * 28)

    def handle_key_down(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.active_input is not None:
                self.active_input = None
                return
            if self.mode != "idle":
                self.mode = "idle"
                self.wall_first_point = None
                self.status("Modo cancelado.", TEXT_MID)
                return
            pygame.quit()
            raise SystemExit
        if event.key == pygame.K_F5:
            self.commit_active_input()
            self.reload_all()
            return
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL and event.key == pygame.K_s:
            self.commit_active_input()
            self.save_all()
            return
        if event.key == pygame.K_LEFTBRACKET and self.attacks:
            self.commit_active_input(); self.select_attack(self.selected_attack_index - 1); return
        if event.key == pygame.K_RIGHTBRACKET and self.attacks:
            self.commit_active_input(); self.select_attack(self.selected_attack_index + 1); return
        if self.active_input is None:
            return
        mode, token = self.active_input
        if mode == "filter":
            if event.key == pygame.K_RETURN:
                self.active_input = None
                return
            if event.key == pygame.K_BACKSPACE:
                self.filter_text = self.filter_text[:-1]
                return
            if event.unicode and event.unicode.isprintable():
                self.filter_text += event.unicode
                return
        if mode in {"field", "global"} and token:
            if event.key == pygame.K_RETURN:
                self.commit_active_input(); return
            if event.key == pygame.K_BACKSPACE:
                self.edit_buffers[token] = self.edit_buffers.get(token, "")[:-1]
                return
            if event.key == pygame.K_MINUS:
                if not self.edit_buffers.get(token, ""):
                    self.edit_buffers[token] = "-"
                    return
            allowed = "0123456789-.,"
            if event.unicode and event.unicode in allowed:
                self.edit_buffers[token] = self.edit_buffers.get(token, "") + event.unicode

    def update_runtime(self):
        self.preview_mouse = Vec2(pygame.mouse.get_pos()) if pygame.mouse.get_pos()[0] < PREVIEW_W else self.preview_mouse
        if self.hold_adjust is not None and pygame.mouse.get_pressed()[0]:
            now = pygame.time.get_ticks()
            if now >= self.hold_adjust["next_time"]:
                self.adjust_field(self.hold_adjust["token"], self.hold_adjust["direction"])
                self.hold_adjust["next_time"] = now + self.hold_adjust["period"]
        elif self.hold_adjust is not None and not pygame.mouse.get_pressed()[0]:
            self.stop_hold()

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.update_runtime()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse_down(event)
                if event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event)
                if event.type == pygame.MOUSEWHEEL:
                    self.handle_mouse_wheel(event)
                if event.type == pygame.KEYDOWN:
                    self.handle_key_down(event)
            self.draw_preview()
            self.draw_panel()
            help_rect = pygame.Rect(12, WINDOW_H - 42, PREVIEW_W - 24, 30)
            pygame.draw.rect(self.screen, (25, 30, 34), help_rect, border_radius=10)
            pygame.draw.rect(self.screen, (68, 78, 88), help_rect, 1, border_radius=10)
            draw_text(self.screen, "Mouse mira | scroll no preview = zoom | segurar +/- repete | Ctrl+S salva | [ ] troca ataque | Esc cancela modo", self.font_xs, TEXT_MID, (help_rect.x + 10, help_rect.y + 8), max_width=help_rect.w - 20)
            pygame.display.flip()


def main():
    app = EditorFluxos()
    app.run()


if __name__ == "__main__":
    main()
