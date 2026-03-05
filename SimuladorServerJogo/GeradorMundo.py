"""Gerador e persistência do mundo de testes do simulador de servidor."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

LARGURA_BLOCOS = 320
ALTURA_BLOCOS = 320
CHUNK_BLOCOS = 32
BLOCO_TAMANHO_PX = 24
ARQUIVO_MUNDO = Path(__file__).resolve().parent / "MundoEstado.json"
TILES_AGUA = {0, 1, 2}


def _gerar_grid_teste() -> List[List[int]]:
    """Mundinho fixo: ilha simples com anéis de biomas para teste de comunicação."""
    cx = LARGURA_BLOCOS // 2
    cy = ALTURA_BLOCOS // 2

    grid: List[List[int]] = [[0 for _ in range(LARGURA_BLOCOS)] for _ in range(ALTURA_BLOCOS)]

    for y in range(ALTURA_BLOCOS):
        for x in range(LARGURA_BLOCOS):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < 118:
                tile = 3
            elif dist < 132:
                tile = 2
            elif dist < 146:
                tile = 1
            else:
                tile = 0

            if tile == 3 and ((x + y) % 11 == 0 or (x * 3 + y * 2) % 17 == 0):
                tile = 4

            grid[y][x] = tile

    return grid




def _tile_em(grid: List[List[int]], x: int, y: int, fallback: int = 0) -> int:
    if 0 <= y < len(grid) and 0 <= x < len(grid[y]):
        return int(grid[y][x])
    return int(fallback)


def _chunk_terra_firme(grid: List[List[int]], chunk_x: int, chunk_y: int) -> bool:
    x0 = chunk_x * CHUNK_BLOCOS
    y0 = chunk_y * CHUNK_BLOCOS
    for by in range(CHUNK_BLOCOS):
        for bx in range(CHUNK_BLOCOS):
            tile = _tile_em(grid, x0 + bx, y0 + by, fallback=0)
            if tile in TILES_AGUA:
                return False
    return True


def _escolher_spawn_chunk(grid: List[List[int]]) -> List[int]:
    max_chunk_x = max(0, LARGURA_BLOCOS // CHUNK_BLOCOS - 1)
    max_chunk_y = max(0, ALTURA_BLOCOS // CHUNK_BLOCOS - 1)

    melhor = None
    melhor_dist2 = None
    centro_cx = max_chunk_x / 2.0
    centro_cy = max_chunk_y / 2.0

    for cy in range(max_chunk_y + 1):
        for cx in range(max_chunk_x + 1):
            if not _chunk_terra_firme(grid, cx, cy):
                continue
            dx = cx - centro_cx
            dy = cy - centro_cy
            dist2 = dx * dx + dy * dy
            if melhor is None or dist2 < melhor_dist2:
                melhor = [cx, cy]
                melhor_dist2 = dist2

    if melhor is None:
        return [max_chunk_x // 2, max_chunk_y // 2]
    return melhor


def _escolher_spawn_posicao(grid: List[List[int]], spawn_chunk: List[int]) -> List[float]:
    cx, cy = int(spawn_chunk[0]), int(spawn_chunk[1])
    x0 = cx * CHUNK_BLOCOS
    y0 = cy * CHUNK_BLOCOS

    candidatos: List[Tuple[int, int]] = []
    for by in range(CHUNK_BLOCOS):
        for bx in range(CHUNK_BLOCOS):
            gx = x0 + bx
            gy = y0 + by
            if _tile_em(grid, gx, gy, fallback=0) not in TILES_AGUA:
                candidatos.append((gx, gy))

    if not candidatos:
        candidatos = [(x0 + CHUNK_BLOCOS // 2, y0 + CHUNK_BLOCOS // 2)]

    gx, gy = random.choice(candidatos)
    return [float(gx), float(gy)]


def gerar_novo_estado_mundo(players: Dict[str, object] | None = None) -> Dict[str, object]:
    estado = _estado_base()
    if players:
        estado["players"] = players
    return estado


def _estado_base() -> Dict[str, object]:
    grid = _gerar_grid_teste()
    spawn_chunk = _escolher_spawn_chunk(grid)
    spawn_tile = _escolher_spawn_posicao(grid, spawn_chunk)
    return {
        "meta": {
            "largura_blocos": LARGURA_BLOCOS,
            "altura_blocos": ALTURA_BLOCOS,
            "chunk_blocos": CHUNK_BLOCOS,
            "bloco_tamanho_px": BLOCO_TAMANHO_PX,
            "spawn_chunk": spawn_chunk,
        },
        "spawn": spawn_tile,
        "grid": grid,
        "players": {},
    }


def carregar_ou_criar_estado_mundo() -> Dict[str, object]:
    if ARQUIVO_MUNDO.exists():
        try:
            return json.loads(ARQUIVO_MUNDO.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    estado = _estado_base()
    salvar_estado_mundo(estado)
    return estado


def salvar_estado_mundo(estado: Dict[str, object]) -> None:
    ARQUIVO_MUNDO.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def obter_posicao_spawn(estado_mundo: Dict[str, object]) -> Tuple[float, float]:
    spawn = estado_mundo.get("spawn", [0.0, 0.0])
    if not isinstance(spawn, (list, tuple)) or len(spawn) != 2:
        return (0.0, 0.0)

    x = max(0.0, min(float(spawn[0]), float(LARGURA_BLOCOS - 1)))
    y = max(0.0, min(float(spawn[1]), float(ALTURA_BLOCOS - 1)))
    return (x, y)
