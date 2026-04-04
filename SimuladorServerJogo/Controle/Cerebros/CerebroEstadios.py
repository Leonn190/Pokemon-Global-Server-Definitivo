"""Controle de estádios e dimensões internas (5x5 chunks de teste)."""

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
        self.chunks_por_lado = 5
        self._grids: Dict[str, Dict[Chunk, List[List[int]]]] = {}

    def _gerar_grid(self, dimensao: str) -> Dict[Chunk, List[List[int]]]:
        if dimensao in self._grids:
            return self._grids[dimensao]
        grid: Dict[Chunk, List[List[int]]] = {}
        for cy in range(self.chunks_por_lado):
            for cx in range(self.chunks_por_lado):
                grid[(cx, cy)] = [[2 for _ in range(self.chunk_tiles)] for _ in range(self.chunk_tiles)]
        self._grids[dimensao] = grid
        return grid

    def chunk_em_grade(self, dimensao: str, chunk_xy: Chunk) -> List[List[int]]:
        d = str(dimensao or "Mundo")
        if d == "Mundo":
            return []
        grid = self._gerar_grid(d)
        cx = int(chunk_xy[0]) % self.chunks_por_lado
        cy = int(chunk_xy[1]) % self.chunks_por_lado
        return [list(l) for l in grid.get((cx, cy), [])]

    def chunks_proximos(self, dimensao: str, centro: Chunk, raio: int) -> List[Chunk]:
        d = str(dimensao or "Mundo")
        if d == "Mundo":
            return []
        out: List[Chunk] = []
        for dx in range(-raio, raio + 1):
            for dy in range(-raio, raio + 1):
                out.append(((int(centro[0]) + dx) % self.chunks_por_lado, (int(centro[1]) + dy) % self.chunks_por_lado))
        return out


CEREBRO_ESTADIOS = CerebroEstadios()
