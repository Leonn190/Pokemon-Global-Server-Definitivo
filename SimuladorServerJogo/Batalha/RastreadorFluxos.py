from __future__ import annotations

import math


class _Vec2:
    __slots__ = ("x", "y")
    def __init__(self, x=0.0, y=0.0):
        if isinstance(x, (tuple, list)) and len(x) >= 2:
            self.x, self.y = float(x[0]), float(x[1])
        elif hasattr(x, "x") and hasattr(x, "y") and y == 0.0:
            self.x, self.y = float(getattr(x, "x")), float(getattr(x, "y"))
        else:
            self.x, self.y = float(x), float(y)
    def __add__(self, o): return self.__class__(self.x + float(o.x), self.y + float(o.y))
    def __sub__(self, o): return self.__class__(self.x - float(o.x), self.y - float(o.y))
    def __mul__(self, k): return self.__class__(self.x * float(k), self.y * float(k))
    def __rmul__(self, k): return self.__mul__(k)
    def __truediv__(self, k):
        k = float(k) or 1.0
        return self.__class__(self.x / k, self.y / k)
    def length_squared(self): return (self.x * self.x) + (self.y * self.y)
    def length(self): return math.hypot(self.x, self.y)
    def normalize(self): return self if self.length_squared() <= 1e-9 else self / self.length()
    def dot(self, o): return (self.x * float(o.x)) + (self.y * float(o.y))


Vec2 = _Vec2


class RastreadorFluxos:
    def __init__(self): self._tile_px = 42.0

    @staticmethod
    def _safe_float(v, p=0.0):
        try:
            return float(p) if v in (None, "") else float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return float(p)

    @staticmethod
    def _safe_bool(v, p=False):
        if isinstance(v, bool): return v
        if v in (None, ""): return bool(p)
        t = str(v).strip().casefold()
        if t in {"1", "true", "verdadeiro", "sim", "yes", "on"}: return True
        if t in {"0", "false", "falso", "nao", "não", "no", "off"}: return False
        return bool(v)

    @staticmethod
    def _clamp(v, mn, mx): return max(mn, min(mx, v))
    @staticmethod
    def _safe_normalize(v): return Vec2(1.0, 0.0) if v.length_squared() <= 1e-9 else v.normalize()
    @staticmethod
    def _vec2(v, d=(0.0, 0.0)):
        if isinstance(v, (tuple, list)) and len(v) >= 2: return Vec2(float(v[0]), float(v[1]))
        if hasattr(v, "x") and hasattr(v, "y"): return Vec2(float(getattr(v, "x", 0.0)), float(getattr(v, "y", 0.0)))
        return Vec2(float(d[0]), float(d[1]))
    @staticmethod
    def _tuple(v): return (float(v.x), float(v.y))

    def _normalizar_paredes(self, paredes):
        saida = []
        for parede in list(paredes or []):
            a = b = None
            if isinstance(parede, dict):
                a = parede.get("a") or parede.get("inicio") or parede.get("from")
                b = parede.get("b") or parede.get("fim") or parede.get("to")
            elif isinstance(parede, (tuple, list)) and len(parede) >= 2:
                a, b = parede[0], parede[1]
            if a is None or b is None: continue
            a_v, b_v = self._vec2(a), self._vec2(b)
            if (b_v - a_v).length_squared() <= 1e-9: continue
            saida.append((a_v, b_v))
        return saida

    def _normalizar_pokemons(self, pokemons, ignorar_ids=None):
        ignorados = {str(v) for v in list(ignorar_ids or []) if str(v)}
        saida = []
        for i, pokemon in enumerate(list(pokemons or [])):
            bruto_id, posicao, raio_tiles = i, None, None
            if isinstance(pokemon, dict):
                bruto_id = pokemon.get("id") or pokemon.get("uid") or pokemon.get("pokemon_id") or i
                posicao = pokemon.get("pos") or pokemon.get("posicao") or pokemon.get("centro")
                raio_tiles = pokemon.get("raio_tiles") if pokemon.get("raio_tiles") is not None else pokemon.get("raio")
            else:
                bruto_id = getattr(pokemon, "Uid", None) or getattr(pokemon, "id", None) or i
                posicao = getattr(pokemon, "Posicao", None) or getattr(pokemon, "pos", None)
                raio_tiles = getattr(pokemon, "RaioColisao", None) or getattr(pokemon, "radius_tiles", None)
            if posicao is None: continue
            pokemon_id = str(bruto_id)
            if pokemon_id in ignorados: continue
            saida.append({"id": pokemon_id, "pos": self._vec2(posicao), "raio_tiles": max(0.0, self._safe_float(raio_tiles, 0.0))})
        return saida

    def segment_intersection(self, ray_start, ray_dir, max_len_px, a, b):
        p, r, q, s = ray_start, ray_dir * max_len_px, a, b - a
        den = r.x * s.y - r.y * s.x
        if abs(den) < 1e-8: return None
        qp = q - p
        t = (qp.x * s.y - qp.y * s.x) / den
        u = (qp.x * r.y - qp.y * r.x) / den
        if not (0.0 <= t <= 1.0 and 0.0 <= u <= 1.0): return None
        hit_px = p + r * t
        wall_dir = b - a
        if wall_dir.length_squared() <= 1e-8: return None
        normal = Vec2(-wall_dir.y, wall_dir.x).normalize()
        if normal.dot(ray_dir) > 0: normal = normal * -1.0
        return max_len_px * t, hit_px, normal

    def ray_circle_hit(self, ray_start, ray_dir, max_len_px, center_px, radius_px):
        m = ray_start - center_px
        b = m.dot(ray_dir)
        c = m.dot(m) - radius_px * radius_px
        if c > 0.0 and b > 0.0: return None
        disc = b * b - c
        if disc < 0.0: return None
        t = -b - math.sqrt(disc)
        if t < 0.0: t = 0.0
        if t > max_len_px: return None
        hit_px = ray_start + ray_dir * t
        normal = hit_px - center_px
        if normal.length_squared() <= 1e-8: return None
        return t, hit_px, normal.normalize()

    def reflect(self, direction, normal):
        normal_n = self._safe_normalize(normal)
        return direction - 2.0 * direction.dot(normal_n) * normal_n

    def _pacote_fluxo(self, ataque): return dict(ataque) if isinstance(ataque, dict) else {}
    def _fonte_radius_tiles(self, pacote, source_radius_tiles):
        if source_radius_tiles is not None: return max(0.1, float(source_radius_tiles))
        return max(0.1, self._safe_float(pacote.get("test_diameter"), 1.5) * 0.5)

    def _fluxos_topo(self, pacote):
        fluxos = [dict(i) for i in list(pacote.get("fluxos") or []) if isinstance(i, dict)]
        if fluxos: return fluxos
        if any(k in pacote for k in ("alcance", "largura_base", "largura_teto", "circular", "raio")): return [dict(pacote)]
        return []

    def compute_effective_range_tiles(self, flow, source_center_px, mouse_px, source_radius_tiles, is_subflow, override_range_tiles=None):
        if override_range_tiles is not None:
            alcance = max(0.10, float(override_range_tiles))
            if is_subflow or not self._safe_bool(flow.get("ajustavel"), False): return alcance
            mn = max(0.10, self._safe_float(flow.get("alcance_min"), alcance))
            mx = max(mn, self._safe_float(flow.get("alcance_max"), alcance))
            return self._clamp(alcance, mn, mx)
        if is_subflow or not self._safe_bool(flow.get("ajustavel"), False):
            return max(0.10, self._safe_float(flow.get("alcance"), 4.0))
        mn = max(0.10, self._safe_float(flow.get("alcance_min"), 1.0))
        mx = max(mn, self._safe_float(flow.get("alcance_max"), mn))
        mouse_dist_tiles = max(0.0, (mouse_px - source_center_px).length() / self._tile_px - source_radius_tiles)
        return self._clamp(mouse_dist_tiles, mn, mx)

    def scaled_factor(self, flow, source_radius_tiles):
        if not self._safe_bool(flow.get("escalonavel"), False): return 1.0
        return 1.0 + max(0.0, (source_radius_tiles * 2.0) - 1.5) * 0.08

    def exit_direction(self, aim_dir, flow):
        offset_value = self._safe_float(flow.get("offset"), 0.0)
        if abs(offset_value) <= 1e-9 or not self._safe_bool(flow.get("grudado"), False): return aim_dir
        base_ang = math.atan2(aim_dir.y, aim_dir.x)
        ang = math.radians(offset_value)
        return Vec2(math.cos(base_ang + ang), math.sin(base_ang + ang))

    def base_start(self, center_px, aim_dir, flow, source_radius_tiles):
        exit_dir = self.exit_direction(aim_dir, flow)
        perp = Vec2(-exit_dir.y, exit_dir.x)
        spacing_tiles = self._safe_float(flow.get("espacamento"), 0.0)
        offset_tiles = self._safe_float(flow.get("offset"), 0.0)
        if self._safe_bool(flow.get("grudado"), False):
            start_center = center_px + exit_dir * (source_radius_tiles * self._tile_px)
        else:
            start_center = center_px + exit_dir * ((source_radius_tiles + spacing_tiles) * self._tile_px) + perp * (offset_tiles * self._tile_px)
        return start_center, exit_dir, perp

    def find_hit(self, start_px, direction, max_len_px, walls, pokemons, origin_pokemon_id=None, flow=None):
        best = None
        for a, b in walls:
            hit = self.segment_intersection(start_px, direction, max_len_px, a, b)
            if hit is None: continue
            dist_px, hit_px, normal = hit
            if best is None or dist_px < best[0]: best = (dist_px, hit_px, normal, "wall", None)
        for pokemon in pokemons:
            pokemon_id = str(pokemon.get("id") or "")
            if origin_pokemon_id is not None and pokemon_id == str(origin_pokemon_id) and not self._safe_bool((flow or {}).get("subfluxo_atinge_a_si_mesmo"), False):
                continue
            hit = self.ray_circle_hit(start_px, direction, max_len_px, self._vec2(pokemon.get("pos")), max(0.0, self._safe_float(pokemon.get("raio_tiles"), 0.0)) * self._tile_px)
            if hit is None: continue
            dist_px, hit_px, normal = hit
            if best is None or dist_px < best[0]: best = (dist_px, hit_px, normal, "pokemon", pokemon_id)
        return best

    def _tracar_segmentos(self, flow, center_px, mouse_px, source_radius_tiles, walls, pokemons, is_subflow=False, origin_pokemon_id=None, override_range_tiles=None, override_ricochets=None):
        start_px, final_direction, _ = self.base_start(center_px, self._safe_normalize(mouse_px - center_px), flow, source_radius_tiles)
        total_range_tiles = self.compute_effective_range_tiles(flow, center_px, mouse_px, source_radius_tiles, is_subflow, override_range_tiles=override_range_tiles)
        total_range_tiles *= self.scaled_factor(flow, source_radius_tiles)
        remaining_px = max(0.0, total_range_tiles * self._tile_px)
        current_start, segments, eventos = start_px, [], []
        ricochet_left = int(max(0, override_ricochets if override_ricochets is not None else self._safe_float(flow.get("numero_ricochets"), 0)))
        while remaining_px > 1e-6:
            hit = self.find_hit(current_start, final_direction, remaining_px, walls, pokemons, origin_pokemon_id=origin_pokemon_id, flow=flow)
            if hit is None:
                end_px = current_start + final_direction * remaining_px
                segments.append((self._tuple(current_start), self._tuple(end_px), final_direction, remaining_px / self._tile_px))
                break
            dist_px, hit_px, normal, hit_type, hit_id = hit
            end_px = hit_px
            segments.append((self._tuple(current_start), self._tuple(end_px), final_direction, dist_px / self._tile_px))
            remaining_px -= dist_px
            can_reflect = ((hit_type == "wall" and self._safe_bool(flow.get("ricocheteia_objetos", flow.get("ricocheteia_paredes", False)), False)) or (hit_type == "pokemon" and self._safe_bool(flow.get("ricocheteia_pokemons"), False)))
            will_reflect = ricochet_left > 0 and can_reflect
            eventos.append({"tipo": hit_type, "pokemon_id": hit_id, "ponto": Vec2(hit_px), "normal": Vec2(normal), "direcao": Vec2(final_direction), "ricochete": will_reflect})
            if not will_reflect: break
            ricochet_left -= 1
            final_direction = self._safe_normalize(self.reflect(final_direction, normal))
            current_start = hit_px + final_direction * 1.5
            remaining_px = max(0.0, remaining_px - 2.0)
        return segments, eventos, final_direction, ricochet_left

    def rastrear_fluxo(self, ataque, inicio, fim, tile_px=1.0, source_radius_tiles=None, paredes=None, pokemons=None, ignorar_pokemon_ids=None, override_range_tiles=None, override_ricochets=None):
        self._tile_px = max(0.01, float(tile_px))
        pacote = self._pacote_fluxo(ataque)
        fluxos = self._fluxos_topo(pacote)
        if not fluxos:
            return {"segments": [], "eventos": [], "direcao_final": Vec2(1, 0), "ricochetes_restantes": int(max(0, override_ricochets or 0))}
        flow = fluxos[0]
        if self._safe_bool(flow.get("circular"), False):
            return {"segments": [], "eventos": [], "direcao_final": self._safe_normalize(self._vec2(fim) - self._vec2(inicio)), "ricochetes_restantes": int(max(0, override_ricochets or 0))}
        inicio_v, fim_v = self._vec2(inicio), self._vec2(fim)
        raio_origem = self._fonte_radius_tiles(pacote, source_radius_tiles)
        walls = self._normalizar_paredes(paredes)
        enemies = self._normalizar_pokemons(pokemons, ignorar_ids=ignorar_pokemon_ids)
        segments, eventos, direcao_final, ricochetes_restantes = self._tracar_segmentos(flow, inicio_v, fim_v, raio_origem, walls, enemies, is_subflow=False, origin_pokemon_id=None, override_range_tiles=override_range_tiles, override_ricochets=override_ricochets)
        return {"segments": segments, "eventos": eventos, "direcao_final": direcao_final, "ricochetes_restantes": ricochetes_restantes}

    def flow_contains_target(self, ataque, inicio, fim, alvo_pos, alvo_raio_tiles, tile_px=1.0, source_radius_tiles=None, paredes=None, pokemons=None, ignorar_pokemon_ids=None, override_range_tiles=None, override_circle_radius_tiles=None, override_ricochets=None):
        self._tile_px = max(0.01, float(tile_px))
        pacote = self._pacote_fluxo(ataque)
        fluxos = self._fluxos_topo(pacote)
        if not fluxos: return False
        flow = fluxos[0]
        alvo_centro = Vec2(float(alvo_pos[0]), float(alvo_pos[1]))
        alvo_raio_px = max(0.0, float(alvo_raio_tiles) * float(tile_px))
        if self._safe_bool(flow.get("circular"), False):
            inicio_v, fim_v = self._vec2(inicio), self._vec2(fim)
            raio_origem = self._fonte_radius_tiles(pacote, source_radius_tiles)
            scale = self.scaled_factor(flow, raio_origem)
            raio_tiles = self._safe_float(flow.get("raio"), 2.0) * scale
            if override_circle_radius_tiles is not None: raio_tiles = max(0.0, float(override_circle_radius_tiles))
            aim = self._safe_normalize(fim_v - inicio_v)
            exit_dir = self.exit_direction(aim, flow)
            if self._safe_bool(flow.get("centralizar"), False):
                centro = inicio_v
            else:
                alcance = self.compute_effective_range_tiles(flow, inicio_v, fim_v, raio_origem, False, override_range_tiles=override_range_tiles) * scale
                if self._safe_bool(flow.get("grudado"), False):
                    centro = inicio_v + exit_dir * ((raio_origem + alcance) * self._tile_px)
                else:
                    perp = Vec2(-exit_dir.y, exit_dir.x)
                    centro = inicio_v + exit_dir * ((raio_origem + self._safe_float(flow.get("espacamento"), 0.0) + alcance) * self._tile_px) + perp * (self._safe_float(flow.get("offset"), 0.0) * self._tile_px)
            return (alvo_centro - centro).length() <= (alvo_raio_px + (raio_tiles * self._tile_px))
        trace = self.rastrear_fluxo(ataque, inicio, fim, tile_px=tile_px, source_radius_tiles=source_radius_tiles, paredes=paredes, pokemons=pokemons, ignorar_pokemon_ids=ignorar_pokemon_ids, override_range_tiles=override_range_tiles, override_ricochets=override_ricochets)
        for seg_start, seg_end, _seg_dir, _seg_len in list(trace.get("segments") or []):
            inicio_seg, fim_seg = self._vec2(seg_start), self._vec2(seg_end)
            direcao = self._safe_normalize(fim_seg - inicio_seg)
            alcance = (fim_seg - inicio_seg).length()
            if self.ray_circle_hit(inicio_seg, direcao, alcance, alvo_centro, alvo_raio_px) is not None:
                return True
        return False
