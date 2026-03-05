"""Gerador e persistência do mundo de testes do simulador de servidor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

LARGURA_BLOCOS = 320
ALTURA_BLOCOS = 320
CHUNK_BLOCOS = 32
BLOCO_TAMANHO_PX = 24
ARQUIVO_MUNDO = Path(__file__).resolve().parent / "MundoEstado.json"


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


def _estado_base() -> Dict[str, object]:
    pos_centro = [LARGURA_BLOCOS * BLOCO_TAMANHO_PX / 2.0, ALTURA_BLOCOS * BLOCO_TAMANHO_PX / 2.0]
    return {
        "meta": {
            "largura_blocos": LARGURA_BLOCOS,
            "altura_blocos": ALTURA_BLOCOS,
            "chunk_blocos": CHUNK_BLOCOS,
            "bloco_tamanho_px": BLOCO_TAMANHO_PX,
        },
        "spawn": pos_centro,
        "grid": _gerar_grid_teste(),
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
    return (float(spawn[0]), float(spawn[1]))
