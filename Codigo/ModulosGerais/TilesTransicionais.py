"""Renderização procedural de tiles de transição entre biomas.

Esta versão realmente mistura cores e arredonda a passagem entre biomas.
Ela não altera o grid lógico; só desenha tiles visuais melhores a partir
 da vizinhança imediata.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, Iterable, Optional, Tuple

import pygame

Cor = Tuple[int, int, int]
Vizinhanca = Tuple[int | None, int | None, int | None, int | None, int | None, int | None, int | None, int | None, int | None]


class TilesTransicionais:
    GRUPOS_PADRAO = {
        "agua": frozenset({0, 1}),
        "campo": frozenset({2, 3}),
        "areia": frozenset({4, 5}),
        "neve": frozenset({6, 10, 11}),
        "magico": frozenset({7}),
        "vulcanico": frozenset({8, 9}),
    }

    def __init__(
        self,
        cores_blocos: Dict[int, Cor],
        callback_bloco_global: Callable[[int, int], Optional[int]],
        grupos_bioma: Optional[Dict[str, Iterable[int]]] = None,
        largura_borda_ratio: float = 0.46,
        alpha_borda: int = 205,
        alpha_canto: int = 235,
        forca_ruido: float = 0.11,
    ) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.CallbackBlocoGlobal = callback_bloco_global
        self.LarguraBordaRatio = max(0.18, min(0.60, float(largura_borda_ratio)))
        self.AlphaBorda = max(24, min(255, int(alpha_borda)))
        self.AlphaCanto = max(24, min(255, int(alpha_canto)))
        self.ForcaRuido = max(0.0, min(0.30, float(forca_ruido)))

        grupos = grupos_bioma or self.GRUPOS_PADRAO
        self.GruposBioma: Dict[str, frozenset[int]] = {
            str(nome): frozenset(int(v) for v in valores)
            for nome, valores in grupos.items()
        }

        self._cache_tiles: Dict[Tuple[int, Vizinhanca], pygame.Surface] = {}
        self._mapa_grupos_por_bloco: Dict[int, str] = {}
        for nome, valores in self.GruposBioma.items():
            for bloco in valores:
                self._mapa_grupos_por_bloco[int(bloco)] = nome

    def atualizar_cores(self, cores_blocos: Dict[int, Cor]) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.limpar_cache()

    def limpar_cache(self) -> None:
        self._cache_tiles.clear()

    def renderizar_chunk(
        self,
        chave_chunk: Tuple[int, int],
        grid: list[list[int]],
        tile_px: int,
        tamanho_chunk: int,
    ) -> Optional[pygame.Surface]:
        if not grid:
            return None
        largura_chunk = max((len(linha) for linha in grid), default=0)
        altura_chunk = len(grid)
        if largura_chunk <= 0 or altura_chunk <= 0:
            return None

        tile_px = max(1, int(tile_px))
        tamanho_chunk = max(1, int(tamanho_chunk))
        superficie = pygame.Surface((largura_chunk * tile_px, altura_chunk * tile_px), pygame.SRCALPHA)

        base_x = int(chave_chunk[0]) * tamanho_chunk
        base_y = int(chave_chunk[1]) * tamanho_chunk

        for by, linha in enumerate(grid):
            for bx, bloco in enumerate(linha):
                mundo_x = base_x + bx
                mundo_y = base_y + by
                tile = self._renderizar_tile_por_contexto(mundo_x, mundo_y, int(bloco), tile_px)
                superficie.blit(tile, (bx * tile_px, by * tile_px))

        return superficie.convert_alpha()

    def _renderizar_tile_por_contexto(
        self,
        mundo_x: int,
        mundo_y: int,
        bloco_central: int,
        tile_px: int,
    ) -> pygame.Surface:
        vizinhanca = self._coletar_vizinhanca(mundo_x, mundo_y)
        chave = (tile_px, vizinhanca)
        cache = self._cache_tiles.get(chave)
        if cache is not None:
            return cache

        cor_central = self._cor_bloco(bloco_central)
        superficie = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)
        superficie.fill(cor_central)

        bloco_dominante = self._escolher_bloco_dominante(bloco_central, vizinhanca)
        if bloco_dominante is not None:
            n, ne, e, se, s, sw, w, nw = (
                vizinhanca[1], vizinhanca[2], vizinhanca[5], vizinhanca[8],
                vizinhanca[7], vizinhanca[6], vizinhanca[3], vizinhanca[0],
            )
            flags = {
                "n": self._mesmo_grupo(bloco_dominante, n),
                "ne": self._mesmo_grupo(bloco_dominante, ne),
                "e": self._mesmo_grupo(bloco_dominante, e),
                "se": self._mesmo_grupo(bloco_dominante, se),
                "s": self._mesmo_grupo(bloco_dominante, s),
                "sw": self._mesmo_grupo(bloco_dominante, sw),
                "w": self._mesmo_grupo(bloco_dominante, w),
                "nw": self._mesmo_grupo(bloco_dominante, nw),
            }
            overlay = self._construir_overlay(tile_px, self._cor_bloco(bloco_dominante), flags)
            if overlay is not None:
                superficie.blit(overlay, (0, 0))

        resultado = superficie.convert_alpha()
        self._cache_tiles[chave] = resultado
        return resultado

    def _construir_overlay(self, tile_px: int, cor_overlay: Cor, flags: Dict[str, bool]) -> Optional[pygame.Surface]:
        if not any(flags.values()):
            return None

        largura = max(1.0, float(tile_px) * self.LarguraBordaRatio)
        raio = max(largura * 1.15, float(tile_px) * 0.36)
        alpha_lado = self.AlphaBorda / 255.0
        alpha_canto = self.AlphaCanto / 255.0

        superficie = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)

        for py in range(tile_px):
            v = (py + 0.5) / float(tile_px)
            for px in range(tile_px):
                u = (px + 0.5) / float(tile_px)
                influencia = 0.0

                if flags["n"]:
                    influencia = max(influencia, self._gradiente_lado(v * tile_px, largura) * alpha_lado)
                if flags["s"]:
                    influencia = max(influencia, self._gradiente_lado((1.0 - v) * tile_px, largura) * alpha_lado)
                if flags["w"]:
                    influencia = max(influencia, self._gradiente_lado(u * tile_px, largura) * alpha_lado)
                if flags["e"]:
                    influencia = max(influencia, self._gradiente_lado((1.0 - u) * tile_px, largura) * alpha_lado)

                if flags["nw"] or (flags["n"] and flags["w"]):
                    dist = math.hypot(u * tile_px, v * tile_px)
                    influencia = max(influencia, self._gradiente_canto(dist, raio) * alpha_canto)
                if flags["ne"] or (flags["n"] and flags["e"]):
                    dist = math.hypot((1.0 - u) * tile_px, v * tile_px)
                    influencia = max(influencia, self._gradiente_canto(dist, raio) * alpha_canto)
                if flags["sw"] or (flags["s"] and flags["w"]):
                    dist = math.hypot(u * tile_px, (1.0 - v) * tile_px)
                    influencia = max(influencia, self._gradiente_canto(dist, raio) * alpha_canto)
                if flags["se"] or (flags["s"] and flags["e"]):
                    dist = math.hypot((1.0 - u) * tile_px, (1.0 - v) * tile_px)
                    influencia = max(influencia, self._gradiente_canto(dist, raio) * alpha_canto)

                if influencia <= 0.0:
                    continue

                ruido = self._ruido_contextual(px, py, flags)
                influencia = max(0.0, min(1.0, influencia + ((ruido - 0.5) * self.ForcaRuido)))
                if influencia <= 0.0:
                    continue

                alpha = int(max(0, min(255, round(influencia * 255.0))))
                superficie.set_at((px, py), (*cor_overlay, alpha))

        return superficie

    def _gradiente_lado(self, distancia_px: float, largura_px: float) -> float:
        if distancia_px >= largura_px:
            return 0.0
        t = 1.0 - (distancia_px / max(1e-6, largura_px))
        return t * t * (3.0 - 2.0 * t)

    def _gradiente_canto(self, distancia_px: float, raio_px: float) -> float:
        if distancia_px >= raio_px:
            return 0.0
        t = 1.0 - (distancia_px / max(1e-6, raio_px))
        return t * t * (3.0 - 2.0 * t)

    def _ruido_contextual(self, px: int, py: int, flags: Dict[str, bool]) -> float:
        s = 0
        for i, chave in enumerate(("n", "ne", "e", "se", "s", "sw", "w", "nw"), start=1):
            if flags.get(chave):
                s += i * 97
        valor = (px * 73856093) ^ (py * 19349663) ^ (s * 83492791)
        valor &= 0xFFFFFFFF
        return (valor % 1000) / 999.0

    def _coletar_vizinhanca(self, mundo_x: int, mundo_y: int) -> Vizinhanca:
        coords = (
            (mundo_x - 1, mundo_y - 1), (mundo_x, mundo_y - 1), (mundo_x + 1, mundo_y - 1),
            (mundo_x - 1, mundo_y),     (mundo_x, mundo_y),     (mundo_x + 1, mundo_y),
            (mundo_x - 1, mundo_y + 1), (mundo_x, mundo_y + 1), (mundo_x + 1, mundo_y + 1),
        )
        valores = []
        for x, y in coords:
            bloco = self.CallbackBlocoGlobal(int(x), int(y))
            valores.append(None if bloco is None else int(bloco))
        return tuple(valores)  # type: ignore[return-value]

    def _escolher_bloco_dominante(self, bloco_central: int, vizinhanca: Vizinhanca) -> Optional[int]:
        pesos = {
            0: 1.10, 1: 2.60, 2: 1.10,
            3: 2.60, 5: 2.60,
            6: 1.10, 7: 2.60, 8: 1.10,
        }
        grupo_central = self._grupo(bloco_central)
        if grupo_central is None:
            return None

        score_por_grupo: Dict[str, float] = {}
        bloco_representante: Dict[str, int] = {}
        for indice, bloco in enumerate(vizinhanca):
            if indice == 4 or bloco is None:
                continue
            grupo = self._grupo(bloco)
            if grupo is None or grupo == grupo_central:
                continue
            score_por_grupo[grupo] = score_por_grupo.get(grupo, 0.0) + pesos.get(indice, 1.0)
            bloco_representante.setdefault(grupo, int(bloco))

        if not score_por_grupo:
            return None

        grupo_vencedor = sorted(score_por_grupo.items(), key=lambda item: (-item[1], item[0]))[0][0]
        return bloco_representante.get(grupo_vencedor)

    def _grupo(self, bloco: int | None) -> Optional[str]:
        if bloco is None:
            return None
        return self._mapa_grupos_por_bloco.get(int(bloco), f"bloco_{int(bloco)}")

    def _mesmo_grupo(self, bloco_a: int | None, bloco_b: int | None) -> bool:
        return self._grupo(bloco_a) == self._grupo(bloco_b)

    def _cor_bloco(self, bloco: int) -> Cor:
        return tuple(self.CoresBlocos.get(int(bloco), (255, 0, 255)))
