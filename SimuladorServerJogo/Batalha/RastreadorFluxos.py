from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Tuple


class _Vec2:
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


Vec2 = _Vec2


class RastreadorFluxos:
    def __init__(self) -> None:
        self._tile_px = 42.0

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
    def _safe_normalize(vetor: Vec2) -> Vec2:
        if vetor.length_squared() <= 1e-9:
            return Vec2(1, 0)
        return vetor.normalize()

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
                raio_tiles = pokemon.get("raio_tiles") if pokemon.get("raio_tiles") is not None else pokemon.get("raio")
            else:
                bruto_id = getattr(pokemon, "Uid", None) or getattr(pokemon, "id", None) or indice
                posicao = getattr(pokemon, "Posicao", None) or getattr(pokemon, "pos", None)
                raio_tiles = getattr(pokemon, "RaioColisao", None) or getattr(pokemon, "radius_tiles", None)
            if posicao is None:
                continue
            pokemon_id = str(bruto_id)
            if pokemon_id in ignorados:
                continue
            saida.append({"id": pokemon_id, "pos": self._vec2(posicao), "raio_tiles": max(0.0, self._safe_float(raio_tiles, 0.0))})
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

    def compute_effective_range_tiles(self, flow: Dict[str, object], source_center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, is_subflow: bool, override_range_tiles: Optional[float] = None) -> float:
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

    def find_hit(self, start_px: Vec2, direction: Vec2, max_len_px: float, walls: List[Tuple[Vec2, Vec2]], pokemons: List[Dict[str, object]], *, origin_pokemon_id: Optional[str], flow: Dict[str, object]):
        best = None
        for a, b in walls:
            hit = self.segment_intersection(start_px, direction, max_len_px, a, b)
            if hit is None:
                continue
            dist_px, hit_px, normal = hit
            if best is None or dist_px < best[0]:
                best = (dist_px, hit_px, normal, "wall", None)
        for pokemon in pokemons:
            pokemon_id = str(pokemon.get("id") or "")
            if origin_pokemon_id is not None and pokemon_id == str(origin_pokemon_id) and not self._safe_bool(flow.get("subfluxo_atinge_a_si_mesmo"), False):
                continue
            hit = self.ray_circle_hit(
                start_px,
                direction,
                max_len_px,
                self._vec2(pokemon.get("pos")),
                max(0.0, self._safe_float(pokemon.get("raio_tiles"), 0.0)) * self._tile_px,
            )
            if hit is None:
                continue
            dist_px, hit_px, normal = hit
            if best is None or dist_px < best[0]:
                best = (dist_px, hit_px, normal, "pokemon", pokemon_id)
        return best

    def _tracar_segmentos(self, flow: Dict[str, object], center_px: Vec2, mouse_px: Vec2, source_radius_tiles: float, walls: List[Tuple[Vec2, Vec2]], pokemons: List[Dict[str, object]], *, is_subflow: bool, origin_pokemon_id: Optional[str], override_range_tiles: Optional[float] = None, override_ricochets: Optional[int] = None):
        start_px, final_direction, _perp = self.base_start(center_px, self._safe_normalize(mouse_px - center_px), flow, source_radius_tiles)
        total_range_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow, override_range_tiles=override_range_tiles)
        total_range_tiles *= self.scaled_factor(flow, source_radius_tiles)
        remaining_px = max(0.0, total_range_tiles * self._tile_px)
        current_start = start_px
        segments = []
        eventos = []
        ricochet_left = int(max(0, override_ricochets if override_ricochets is not None else self._safe_float(flow.get("numero_ricochets"), 0)))

        while remaining_px > 1e-6:
            hit = self.find_hit(current_start, final_direction, remaining_px, walls, pokemons, origin_pokemon_id=origin_pokemon_id, flow=flow)
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
                hit_type == "wall" and self._safe_bool(flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False)), False)
            ) or (
                hit_type == "pokemon" and self._safe_bool(flow.get("ricocheteia_pokemons"), False)
            )
            will_reflect = ricochet_left > 0 and can_reflect
            eventos.append({"tipo": hit_type, "pokemon_id": hit_id, "ponto": Vec2(hit_px), "normal": Vec2(normal), "direcao": Vec2(final_direction), "ricochete": will_reflect})
            if not will_reflect:
                current_start = hit_px
                break

            ricochet_left -= 1
            final_direction = self._safe_normalize(self.reflect(final_direction, normal))
            current_start = hit_px + final_direction * 1.5
            remaining_px = max(0.0, remaining_px - 2.0)

        return segments, eventos, final_direction, ricochet_left

    def rastrear_fluxo(self, ataque: object, inicio, fim, *, tile_px: float = 1.0, source_radius_tiles: Optional[float] = None, paredes: Optional[Iterable[object]] = None, pokemons: Optional[Iterable[object]] = None, ignorar_pokemon_ids: Optional[Iterable[object]] = None, override_range_tiles: Optional[float] = None, override_ricochets: Optional[int] = None) -> Dict[str, object]:
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
        return {"segments": segments, "eventos": eventos, "direcao_final": direcao_final, "ricochetes_restantes": ricochetes_restantes}

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
        self._tile_px = max(0.01, float(tile_px))
        pacote = self._pacote_fluxo(ataque)
        fluxo = self._fluxos_topo(pacote)
        if not fluxo:
            return False
        flow = fluxo[0]

        alvo_centro = Vec2(float(alvo_pos[0]), float(alvo_pos[1]))
        alvo_raio_px = max(0.0, float(alvo_raio_tiles) * float(tile_px))

        if self._safe_bool(flow.get("circular"), False):
            inicio_v = self._vec2(inicio)
            fim_v = self._vec2(fim)
            raio_origem = self._fonte_radius_tiles(pacote, source_radius_tiles)
            scale = self.scaled_factor(flow, raio_origem)
            raio_tiles = self._safe_float(flow.get("raio"), 2.0) * scale
            if override_circle_radius_tiles is not None:
                raio_tiles = max(0.0, float(override_circle_radius_tiles))
            if self._safe_bool(flow.get("centralizar"), False):
                centro = inicio_v
            else:
                aim = self._safe_normalize(fim_v - inicio_v)
                exit_dir = self.exit_direction(aim, flow)
                alcance = self.compute_effective_range_tiles(flow, inicio_v, fim_v, raio_origem, False, override_range_tiles=override_range_tiles) * scale
                if self._safe_bool(flow.get("grudado"), False):
                    centro = inicio_v + exit_dir * ((raio_origem + alcance) * self._tile_px)
                else:
                    perp = Vec2(-exit_dir.y, exit_dir.x)
                    centro = inicio_v + exit_dir * ((raio_origem + self._safe_float(flow.get("espacamento"), 0.0) + alcance) * self._tile_px) + perp * (self._safe_float(flow.get("offset"), 0.0) * self._tile_px)
            raio_px = raio_tiles * self._tile_px
            for ponto in self.circle_samples(alvo_centro, alvo_raio_px):
                if self.point_hit_circle_shape(ponto, centro, raio_px, flow):
                    return True
            return False

        trace = self.rastrear_fluxo(
            ataque,
            inicio,
            fim,
            tile_px=tile_px,
            source_radius_tiles=source_radius_tiles,
            paredes=paredes,
            pokemons=pokemons,
            ignorar_pokemon_ids=ignorar_pokemon_ids,
            override_range_tiles=override_range_tiles,
            override_ricochets=override_ricochets,
        )
        segmentos = list(trace.get("segments") or [])
        for ponto in self.circle_samples(alvo_centro, alvo_raio_px):
            for seg_start, seg_end, _seg_dir, _seg_len in segmentos:
                hit = self.ray_circle_hit(
                    self._vec2(seg_start),
                    self._safe_normalize(self._vec2(seg_end) - self._vec2(seg_start)),
                    (self._vec2(seg_end) - self._vec2(seg_start)).length(),
                    ponto,
                    0.01,
                )
                if hit is not None:
                    return True
        return False
