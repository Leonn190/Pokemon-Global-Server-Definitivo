from __future__ import annotations

import math
from typing import Dict, Iterable, Optional, Tuple

Vec2 = Tuple[float, float]


class RastreadorFluxos:
    @staticmethod
    def _safe_float(valor, padrao=0.0) -> float:
        try:
            if valor in (None, ""):
                return float(padrao)
            return float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            return float(padrao)

    @staticmethod
    def _normalizar(v: Vec2) -> Vec2:
        m = math.hypot(float(v[0]), float(v[1]))
        if m <= 1e-9:
            return (1.0, 0.0)
        return (float(v[0] / m), float(v[1] / m))

    @staticmethod
    def _dot(a: Vec2, b: Vec2) -> float:
        return float(a[0] * b[0] + a[1] * b[1])

    @staticmethod
    def _sub(a: Vec2, b: Vec2) -> Vec2:
        return (float(a[0] - b[0]), float(a[1] - b[1]))

    @staticmethod
    def _dist(a: Vec2, b: Vec2) -> float:
        return math.hypot(float(a[0] - b[0]), float(a[1] - b[1]))

    @classmethod
    def _segmento_intersecta_circulo(cls, inicio: Vec2, fim: Vec2, centro: Vec2, raio: float) -> bool:
        vx = float(fim[0] - inicio[0])
        vy = float(fim[1] - inicio[1])
        wx = float(centro[0] - inicio[0])
        wy = float(centro[1] - inicio[1])
        tamanho2 = (vx * vx) + (vy * vy)
        if tamanho2 <= 1e-9:
            return cls._dist(inicio, centro) <= float(raio)
        t = max(0.0, min(1.0, ((wx * vx) + (wy * vy)) / tamanho2))
        proj = (float(inicio[0] + vx * t), float(inicio[1] + vy * t))
        return cls._dist(proj, centro) <= float(raio)

    @classmethod
    def flow_contains_target(
        cls,
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
        _ = (tile_px, source_radius_tiles, paredes, pokemons, ignorar_pokemon_ids, override_ricochets)
        fluxo = dict(ataque or {}) if isinstance(ataque, dict) else {}
        subtipo = str(fluxo.get("subtipo") or fluxo.get("estilo") or "").strip().casefold()

        inicio_v = (float(inicio[0]), float(inicio[1]))
        fim_v = (float(fim[0]), float(fim[1]))
        alvo_v = (float(alvo_pos[0]), float(alvo_pos[1]))
        alvo_raio = max(0.0, float(alvo_raio_tiles))

        if subtipo == "zona" or override_circle_radius_tiles is not None:
            raio = max(0.0, cls._safe_float(override_circle_radius_tiles, cls._safe_float(fluxo.get("raio"), 0.0)))
            return cls._dist(inicio_v, alvo_v) <= (raio + alvo_raio)

        if subtipo == "area":
            alcance = max(0.0, cls._safe_float(override_range_tiles, cls._safe_float(fluxo.get("alcance"), 0.0)))
            largura = max(1.0, cls._safe_float(fluxo.get("largura_teto"), 50.0))
            direcao = cls._normalizar(cls._sub(fim_v, inicio_v))
            vetor_alvo = cls._sub(alvo_v, inicio_v)
            dist = math.hypot(vetor_alvo[0], vetor_alvo[1])
            if dist > (alcance + alvo_raio):
                return False
            if dist <= 1e-9:
                return True
            produto = max(-1.0, min(1.0, cls._dot(direcao, cls._normalizar(vetor_alvo))))
            angulo = math.degrees(math.acos(produto))
            return angulo <= max(1.0, largura * 0.5)

        # padrão: tiro/segmento
        raio_proj = max(0.0, cls._safe_float(fluxo.get("tamanho_elementos", fluxo.get("raio", 0.35)), 0.35))
        return cls._segmento_intersecta_circulo(inicio_v, fim_v, alvo_v, alvo_raio + raio_proj)

    @classmethod
    def rastrear_fluxo(
        cls,
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
        _ = (tile_px, source_radius_tiles, paredes, pokemons, ignorar_pokemon_ids, override_range_tiles, override_ricochets)
        inicio_v = (float(inicio[0]), float(inicio[1]))
        fim_v = (float(fim[0]), float(fim[1]))
        direcao = cls._normalizar(cls._sub(fim_v, inicio_v))
        return {
            "segments": [(inicio_v, fim_v, direcao, cls._dist(inicio_v, fim_v))],
            "eventos": [],
            "direcao_final": type("_V", (), {"x": direcao[0], "y": direcao[1]})(),
            "ricochetes_restantes": int(max(0, cls._safe_float(override_ricochets, 0))),
        }
