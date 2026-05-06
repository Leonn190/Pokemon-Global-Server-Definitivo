"""Gerenciador visual dos tiles do mundo."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

Cor = Tuple[int, int, int]


class AparenciaBaseTiles:
    """Gera o visual base original dos tiles com variacao deterministica."""

    def __init__(self, cores_blocos: Dict[int, Cor]) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.SeedMundo = 0
        self._cache_tiles: Dict[Tuple[int, int, int], pygame.Surface] = {}

    def definir_seed(self, seed_mundo: int) -> None:
        novo_seed = int(seed_mundo or 0)
        if novo_seed != self.SeedMundo:
            self.SeedMundo = novo_seed
            self.limpar_cache()

    def atualizar_cores(self, cores_blocos: Dict[int, Cor]) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.limpar_cache()

    def limpar_cache(self) -> None:
        self._cache_tiles.clear()

    @staticmethod
    def _mix64(valor: int) -> int:
        x = int(valor) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 30)
        x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27)
        x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 31)
        return x & 0xFFFFFFFFFFFFFFFF

    def _variante_base(self, mundo_x: int, mundo_y: int, bloco: int) -> int:
        h = (
            int(self.SeedMundo)
            ^ (int(mundo_x) * 0x9E3779B185EBCA87)
            ^ (int(mundo_y) * 0xC2B2AE3D27D4EB4F)
            ^ (int(bloco) * 0x165667B19E3779F9)
        ) & 0xFFFFFFFFFFFFFFFF
        return int(self._mix64(h) % 8)

    @staticmethod
    def _clamp_cor(valor: float) -> int:
        return int(max(0, min(255, round(valor))))

    def _tile_base_cacheado(self, tile_px: int, bloco: int, variante: int) -> pygame.Surface:
        chave = (int(tile_px), int(bloco), int(variante))
        cache = self._cache_tiles.get(chave)
        if cache is not None:
            return cache

        base = tuple(self.CoresBlocos.get(int(bloco), (255, 0, 255)))
        superficie = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)
        if base == (0, 0, 0):
            superficie.fill((0, 0, 0, 255))
            resultado = superficie.convert_alpha()
            self._cache_tiles[chave] = resultado
            return resultado
        ganho = (int(variante) - 3.5) * 1.6
        r0 = self._clamp_cor(base[0] + ganho)
        g0 = self._clamp_cor(base[1] + ganho)
        b0 = self._clamp_cor(base[2] + ganho)

        for py in range(tile_px):
            t = (py + 0.5) / max(1.0, float(tile_px))
            grad = 0.94 + (0.12 * (1.0 - t))
            for px in range(tile_px):
                n = (((px + 3) * 73856093) ^ ((py + 5) * 19349663) ^ ((int(variante) + 11) * 83492791)) & 0xFFFFFFFF
                ruido = ((n % 17) - 8) * 0.005
                fator = max(0.80, min(1.20, grad + ruido))
                superficie.set_at(
                    (px, py),
                    (
                        self._clamp_cor(r0 * fator),
                        self._clamp_cor(g0 * fator),
                        self._clamp_cor(b0 * fator),
                        255,
                    ),
                )

        resultado = superficie.convert_alpha()
        self._cache_tiles[chave] = resultado
        return resultado

    def obter_tile_base(self, mundo_x: int, mundo_y: int, bloco: int, tile_px: int) -> pygame.Surface:
        variante = self._variante_base(mundo_x, mundo_y, bloco)
        return self._tile_base_cacheado(tile_px=max(1, int(tile_px)), bloco=int(bloco), variante=variante)


class GerenciadorTiles:
    """Compositor apenas da aparencia base dos tiles, sem transicoes."""

    def __init__(self, cores_blocos: Dict[int, Cor]) -> None:
        self._base = AparenciaBaseTiles(cores_blocos=cores_blocos)

    def definir_seed(self, seed_mundo: int) -> None:
        self._base.definir_seed(seed_mundo)

    def atualizar_cores(self, cores_blocos: Dict[int, Cor]) -> None:
        self._base.atualizar_cores(cores_blocos)

    def limpar_cache(self) -> None:
        self._base.limpar_cache()

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
        fila_blits: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for by, linha in enumerate(grid):
            destino_y = by * tile_px
            for bx, bloco in enumerate(linha):
                bloco_int = int(bloco)
                fila_blits.append((
                    self._base.obter_tile_base(base_x + bx, base_y + by, bloco_int, tile_px),
                    (bx * tile_px, destino_y),
                ))

        blits = getattr(superficie, "blits", None)
        if callable(blits):
            try:
                blits(fila_blits, doreturn=False)
            except TypeError:
                blits(fila_blits)
        else:
            for tile_superficie, destino in fila_blits:
                superficie.blit(tile_superficie, destino)
        return superficie.convert_alpha()
