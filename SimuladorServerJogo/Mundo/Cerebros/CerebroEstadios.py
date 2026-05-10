"""Controle de dimensões de estádio (somente recorte espacial em chunks)."""

from __future__ import annotations

from typing import List, Tuple


Chunk = Tuple[int, int]

DIMENSOES_ESTADIO = [
    "EstadioNormal", "EstadioFogo", "EstadioAgua", "EstadioPlanta", "EstadioEletrico",
    "EstadioGelo", "EstadioLutador", "EstadioVenenoso", "EstadioTerra", "EstadioVoador",
    "EstadioPsiquico", "EstadioInseto", "EstadioPedra", "EstadioFantasma", "EstadioDragao",
    "EstadioSombrio", "EstadioMetal", "EstadioFada", "EstadioCosmico", "EstadioSonoro", "EstadioGeral",
]


class CerebroEstadios:
    def __init__(self, chunk_tiles: int = 10) -> None:
        self.chunk_tiles = max(1, int(chunk_tiles))
        self.chunks_largura = 6
        self.chunks_altura = 4

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
