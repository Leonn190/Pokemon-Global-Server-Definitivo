"""Controle de estádios e dimensões internas (60x40 tiles = 6x4 chunks)."""

from __future__ import annotations

from typing import Dict, List, Tuple


Chunk = Tuple[int, int]

DIMENSOES_ESTADIO = [
    "EstadioNormal", "EstadioFogo", "EstadioAgua", "EstadioPlanta", "EstadioEletrico",
    "EstadioGelo", "EstadioLutador", "EstadioVenenoso", "EstadioTerra", "EstadioVoador",
    "EstadioPsiquico", "EstadioInseto", "EstadioPedra", "EstadioFantasma", "EstadioDragao",
    "EstadioSombrio", "EstadioMetal", "EstadioFada", "EstadioCosmico", "EstadioSonoro",
]


class CerebroEstadios:
    def __init__(self, chunk_tiles: int = 10) -> None:
        self.chunk_tiles = max(1, int(chunk_tiles))
        self.chunks_largura = 6
        self.chunks_altura = 4
        self._grids: Dict[str, Dict[Chunk, List[List[int]]]] = {}

    def _gerar_grid(self, dimensao: str) -> Dict[Chunk, List[List[int]]]:
        if dimensao in self._grids:
            return self._grids[dimensao]
        grid: Dict[Chunk, List[List[int]]] = {}
        for cy in range(self.chunks_altura):
            for cx in range(self.chunks_largura):
                chunk_grid: List[List[int]] = []
                base_x = cx * self.chunk_tiles
                base_y = cy * self.chunk_tiles
                for ly in range(self.chunk_tiles):
                    row: List[int] = []
                    for lx in range(self.chunk_tiles):
                        row.append(10 if ((base_x + lx + base_y + ly) % 2 == 0) else 11)
                    chunk_grid.append(row)
                grid[(cx, cy)] = chunk_grid
        self._grids[dimensao] = grid
        return grid

    def chunk_em_grade(self, dimensao: str, chunk_xy: Chunk) -> List[List[int]]:
        d = str(dimensao or "Mundo")
        if d == "Mundo":
            return []
        grid = self._gerar_grid(d)
        cx = int(chunk_xy[0])
        cy = int(chunk_xy[1])
        if cx < 0 or cy < 0 or cx >= self.chunks_largura or cy >= self.chunks_altura:
            return []
        return [list(l) for l in grid.get((cx, cy), [])]

    def chunks_proximos(self, dimensao: str, centro: Chunk, raio: int) -> List[Chunk]:
        d = str(dimensao or "Mundo")
        if d == "Mundo":
            return []
        out: List[Chunk] = []
        for dx in range(-raio, raio + 1):
            for dy in range(-raio, raio + 1):
                nx = int(centro[0]) + dx
                ny = int(centro[1]) + dy
                if 0 <= nx < self.chunks_largura and 0 <= ny < self.chunks_altura:
                    out.append((nx, ny))
        return out


CEREBRO_ESTADIOS = CerebroEstadios()
