"""Integração com o gerador Java do mundo do servidor."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

LARGURA_BLOCOS = 10_000
ALTURA_BLOCOS = 10_000
CHUNK_BLOCOS = 10
BLOCO_TAMANHO_PX = 24
ARQUIVO_MUNDO = Path(__file__).resolve().parent / "MundoEstado.json"
RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
ARQUIVO_GRID_JAVA = RAIZ_REPOSITORIO / "world_grids.json"
JAVA_FONTE = RAIZ_REPOSITORIO / "WorldGenerator.java"
JAVA_CLASSE = RAIZ_REPOSITORIO / "WorldGenerator.class"
ARQUIVO_PREVIEW_BASE = RAIZ_REPOSITORIO / "01_blocos_biomas.png"
ARQUIVO_PREVIEW_ESTRUTURAS = RAIZ_REPOSITORIO / "02_estruturas_naturais.png"
ARQUIVO_PREVIEW_POIS = RAIZ_REPOSITORIO / "03_pois.png"
TILES_AGUA = {0, 1}


def _executar_gerador_java() -> None:
    if not JAVA_FONTE.exists():
        raise FileNotFoundError(f"Arquivo Java não encontrado: {JAVA_FONTE}")

    if (not JAVA_CLASSE.exists()) or JAVA_CLASSE.stat().st_mtime < JAVA_FONTE.stat().st_mtime:
        subprocess.run(
            ["javac", JAVA_FONTE.name],
            cwd=RAIZ_REPOSITORIO,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            text=True,
        )

    subprocess.run(
        ["java", "WorldGenerator"],
        cwd=RAIZ_REPOSITORIO,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if not ARQUIVO_GRID_JAVA.exists():
        raise FileNotFoundError(f"Arquivo de grids não gerado: {ARQUIVO_GRID_JAVA}")
    if not ARQUIVO_PREVIEW_BASE.exists():
        raise FileNotFoundError(f"Imagem de preview não gerada: {ARQUIVO_PREVIEW_BASE}")


def _carregar_world_grids() -> Dict[str, object]:
    if not ARQUIVO_GRID_JAVA.exists():
        raise FileNotFoundError(f"Arquivo world_grids.json não encontrado: {ARQUIVO_GRID_JAVA}")

    payload = json.loads(ARQUIVO_GRID_JAVA.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Formato inválido de world_grids.json")
    return payload


def _normalizar_grid(grid: object) -> List[List[int]]:
    if not isinstance(grid, list) or not grid:
        raise ValueError("Grid inválida: não é lista 2D")

    altura = len(grid)
    if altura <= 0:
        raise ValueError("Grid inválida: altura 0")

    primeira = grid[0]
    if not isinstance(primeira, list) or not primeira:
        raise ValueError("Grid inválida: primeira linha vazia")

    largura = len(primeira)
    resultado: List[List[int]] = []
    for y in range(altura):
        linha = grid[y]
        if not isinstance(linha, list) or len(linha) != largura:
            raise ValueError("Grid inválida: linhas com larguras diferentes")
        resultado.append([int(v) for v in linha])
    return resultado


def _tile_em(grid: List[List[int]], x: int, y: int, fallback: int = 0) -> int:
    if 0 <= y < len(grid) and 0 <= x < len(grid[y]):
        return int(grid[y][x])
    return int(fallback)


def _chunk_terra_firme(grid: List[List[int]], chunk_x: int, chunk_y: int) -> bool:
    x0 = chunk_x * CHUNK_BLOCOS
    y0 = chunk_y * CHUNK_BLOCOS
    for by in range(CHUNK_BLOCOS):
        for bx in range(CHUNK_BLOCOS):
            if _tile_em(grid, x0 + bx, y0 + by, fallback=0) in TILES_AGUA:
                return False
    return True


def _escolher_spawn_chunk(grid: List[List[int]]) -> List[int]:
    max_chunk_x = max(0, len(grid[0]) // CHUNK_BLOCOS - 1)
    max_chunk_y = max(0, len(grid) // CHUNK_BLOCOS - 1)

    melhor = None
    melhor_dist2 = None

    for cy in range(max_chunk_y + 1):
        for cx in range(max_chunk_x + 1):
            if not _chunk_terra_firme(grid, cx, cy):
                continue
            dist2 = (cx * cx) + (cy * cy)
            if melhor is None or dist2 < melhor_dist2:
                melhor = [cx, cy]
                melhor_dist2 = dist2

    return melhor if melhor is not None else [0, 0]


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


def _estado_a_partir_do_java() -> Dict[str, object]:
    _executar_gerador_java()
    payload = _carregar_world_grids()

    meta = payload.get("meta", {}) if isinstance(payload.get("meta", {}), dict) else {}
    grid_blocos = _normalizar_grid(payload.get("grid_blocos", []))
    grid_biomas = _normalizar_grid(payload.get("grid_biomas", []))
    grid_estruturas = _normalizar_grid(payload.get("grid_estruturas", []))

    altura = len(grid_blocos)
    largura = len(grid_blocos[0]) if altura else 0

    if len(grid_biomas) != altura or len(grid_estruturas) != altura:
        raise ValueError("Grids com alturas diferentes")
    if any(len(r) != largura for r in grid_biomas) or any(len(r) != largura for r in grid_estruturas):
        raise ValueError("Grids com larguras diferentes")

    spawn_chunk = _escolher_spawn_chunk(grid_blocos)
    spawn_tile = _escolher_spawn_posicao(grid_blocos, spawn_chunk)

    return {
        "meta": {
            "largura_blocos": int(meta.get("width", largura)),
            "altura_blocos": int(meta.get("height", altura)),
            "chunk_blocos": int(CHUNK_BLOCOS),
            "bloco_tamanho_px": int(BLOCO_TAMANHO_PX),
            "spawn_chunk": spawn_chunk,
            "seed": int(meta.get("seed", 0)),
        },
        "spawn": spawn_tile,
        "grid": grid_blocos,
        "grid_biomas": grid_biomas,
        "grid_estruturas_naturais": grid_estruturas,
        "players": {},
    }


def gerar_novo_estado_mundo(players: Dict[str, object] | None = None) -> Dict[str, object]:
    estado = _estado_a_partir_do_java()
    if players:
        estado["players"] = players
    return estado


def _normalizar_estado_carregado(estado: Dict[str, object]) -> Dict[str, object]:
    if not isinstance(estado, dict):
        return _estado_a_partir_do_java()

    grid = estado.get("grid")
    if not isinstance(grid, list) or not grid:
        return _estado_a_partir_do_java()

    meta = estado.get("meta", {}) if isinstance(estado.get("meta", {}), dict) else {}
    largura = int(meta.get("largura_blocos", len(grid[0]) if grid else LARGURA_BLOCOS))
    altura = int(meta.get("altura_blocos", len(grid) if grid else ALTURA_BLOCOS))

    spawn_chunk = meta.get("spawn_chunk")
    if not isinstance(spawn_chunk, (list, tuple)) or len(spawn_chunk) != 2:
        spawn_chunk = _escolher_spawn_chunk(grid)

    spawn = estado.get("spawn", [0.0, 0.0])
    spawn_invalido = (
        not isinstance(spawn, (list, tuple))
        or len(spawn) != 2
        or float(spawn[0]) < 0
        or float(spawn[1]) < 0
        or float(spawn[0]) >= float(max(1, largura))
        or float(spawn[1]) >= float(max(1, altura))
        or _tile_em(grid, int(float(spawn[0])), int(float(spawn[1])), fallback=0) in TILES_AGUA
    )
    if spawn_invalido:
        spawn = _escolher_spawn_posicao(grid, [int(spawn_chunk[0]), int(spawn_chunk[1])])

    estado["meta"] = {
        **meta,
        "largura_blocos": largura,
        "altura_blocos": altura,
        "chunk_blocos": int(CHUNK_BLOCOS),
        "bloco_tamanho_px": int(meta.get("bloco_tamanho_px", BLOCO_TAMANHO_PX)),
        "spawn_chunk": [int(spawn_chunk[0]), int(spawn_chunk[1])],
    }
    estado["spawn"] = [float(spawn[0]), float(spawn[1])]
    estado["players"] = estado.get("players", {}) if isinstance(estado.get("players", {}), dict) else {}

    # grids já devem estar prontas do Java; se faltar, regenera via Java
    try:
        estado["grid"] = _normalizar_grid(estado.get("grid", []))
        estado["grid_biomas"] = _normalizar_grid(estado.get("grid_biomas", []))
        estado["grid_estruturas_naturais"] = _normalizar_grid(estado.get("grid_estruturas_naturais", []))
    except Exception:
        novo = _estado_a_partir_do_java()
        novo["players"] = estado["players"]
        return novo

    return estado


def carregar_ou_criar_estado_mundo() -> Dict[str, object]:
    if ARQUIVO_MUNDO.exists():
        try:
            estado = json.loads(ARQUIVO_MUNDO.read_text(encoding="utf-8"))
            estado = _normalizar_estado_carregado(estado)
            salvar_estado_mundo(estado)
            return estado
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    estado = _estado_a_partir_do_java()
    salvar_estado_mundo(estado)
    return estado


def salvar_estado_mundo(estado: Dict[str, object]) -> None:
    ARQUIVO_MUNDO.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def obter_posicao_spawn(estado_mundo: Dict[str, object]) -> Tuple[float, float]:
    spawn = estado_mundo.get("spawn", [0.0, 0.0])
    if not isinstance(spawn, (list, tuple)) or len(spawn) != 2:
        return (0.0, 0.0)

    largura = int(estado_mundo.get("meta", {}).get("largura_blocos", LARGURA_BLOCOS))
    altura = int(estado_mundo.get("meta", {}).get("altura_blocos", ALTURA_BLOCOS))
    x = max(0.0, min(float(spawn[0]), float(max(1, largura - 1))))
    y = max(0.0, min(float(spawn[1]), float(max(1, altura - 1))))
    return (x, y)
