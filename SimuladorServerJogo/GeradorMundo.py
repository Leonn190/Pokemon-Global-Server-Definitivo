"""Integração do servidor simulado com o gerador de mundo em Java."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

BLOCO_TAMANHO_PX = 32
CHUNK_BLOCOS = 10

PASTA_SERVIDOR = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = PASTA_SERVIDOR.parent
ARQUIVO_MUNDO = PASTA_SERVIDOR / "MundoEstado.json"
ARQUIVO_WORLD_GRIDS = RAIZ_REPOSITORIO / "world_grids.json"
ARQUIVO_PREVIEW = RAIZ_REPOSITORIO / "01_blocos_biomas.png"
ARQUIVO_JAVA = PASTA_SERVIDOR / "WorldGenerator.java"
ARQUIVO_CLASS = PASTA_SERVIDOR / "WorldGenerator.class"

LARGURA_BLOCOS = 0
ALTURA_BLOCOS = 0


def _gerar_seed() -> int:
    return int(time.time_ns() % 9_000_000_000_000_000_000)


def _compilar_java_se_necessario() -> None:
    precisa_compilar = (not ARQUIVO_CLASS.exists()) or (ARQUIVO_JAVA.stat().st_mtime > ARQUIVO_CLASS.stat().st_mtime)
    if not precisa_compilar:
        return

    cmd = ["javac", ARQUIVO_JAVA.name]
    subprocess.run(cmd, check=True, cwd=PASTA_SERVIDOR)


def _executar_world_generator(seed: int) -> None:
    _compilar_java_se_necessario()
    cmd = ["java", "-cp", str(PASTA_SERVIDOR), "WorldGenerator", str(seed), str(RAIZ_REPOSITORIO)]
    subprocess.run(cmd, check=True, cwd=RAIZ_REPOSITORIO)


def _validar_grid_numerica(nome: str, grid: object, largura: int, altura: int) -> List[List[int]]:
    if not isinstance(grid, list) or len(grid) != altura:
        raise ValueError(f"{nome} inválida: altura diferente de meta.height")

    grid_numerica: List[List[int]] = []
    for y, linha in enumerate(grid):
        if not isinstance(linha, list) or len(linha) != largura:
            raise ValueError(f"{nome} inválida: largura incorreta na linha {y}")
        nova_linha: List[int] = []
        for x, valor in enumerate(linha):
            try:
                nova_linha.append(int(valor))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{nome} inválida: valor não numérico em [{y}][{x}]") from exc
        grid_numerica.append(nova_linha)
    return grid_numerica


def _carregar_world_grids() -> Tuple[Dict[str, int], List[List[int]], List[List[int]], List[List[int]]]:
    if not ARQUIVO_WORLD_GRIDS.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_WORLD_GRIDS}")

    with ARQUIVO_WORLD_GRIDS.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("world_grids.json inválido: conteúdo raiz não é objeto")

    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        raise ValueError("world_grids.json inválido: meta ausente")

    largura = int(meta.get("width", 0))
    altura = int(meta.get("height", 0))
    seed = int(meta.get("seed", 0))
    if largura <= 0 or altura <= 0:
        raise ValueError("world_grids.json inválido: meta.width/meta.height devem ser positivos")

    grid_blocos = _validar_grid_numerica("grid_blocos", payload.get("grid_blocos"), largura, altura)
    grid_biomas = _validar_grid_numerica("grid_biomas", payload.get("grid_biomas"), largura, altura)
    grid_estruturas = _validar_grid_numerica("grid_estruturas", payload.get("grid_estruturas"), largura, altura)

    return ({"width": largura, "height": altura, "seed": seed}, grid_blocos, grid_biomas, grid_estruturas)


def _chunk_totalmente_valido(grid_blocos: Sequence[Sequence[int]], cx: int, cy: int) -> bool:
    y0 = cy * CHUNK_BLOCOS
    x0 = cx * CHUNK_BLOCOS
    for y in range(y0, min(y0 + CHUNK_BLOCOS, len(grid_blocos))):
        linha = grid_blocos[y]
        for x in range(x0, min(x0 + CHUNK_BLOCOS, len(linha))):
            if int(linha[x]) != 3:
                return False
    return True


def _escolher_spawn(grid_blocos: Sequence[Sequence[int]]) -> Tuple[Tuple[int, int], Tuple[float, float]]:
    altura = len(grid_blocos)
    largura = len(grid_blocos[0]) if altura else 0
    total_chunks_x = max(1, largura // CHUNK_BLOCOS)
    total_chunks_y = max(1, altura // CHUNK_BLOCOS)

    centro_chunk = (total_chunks_x // 2, total_chunks_y // 2)

    melhor_chunk = None
    melhor_dist = None
    for cy in range(total_chunks_y):
        for cx in range(total_chunks_x):
            if not _chunk_totalmente_valido(grid_blocos, cx, cy):
                continue
            dist = abs(cx - centro_chunk[0]) + abs(cy - centro_chunk[1])
            if melhor_dist is None or dist < melhor_dist:
                melhor_chunk = (cx, cy)
                melhor_dist = dist

    if melhor_chunk is None:
        melhor_chunk = centro_chunk

    x0 = melhor_chunk[0] * CHUNK_BLOCOS
    y0 = melhor_chunk[1] * CHUNK_BLOCOS

    candidatos = []
    for y in range(y0, min(y0 + CHUNK_BLOCOS, altura)):
        for x in range(x0, min(x0 + CHUNK_BLOCOS, largura)):
            candidatos.append((x, y, int(grid_blocos[y][x]) == 3))

    candidatos.sort(key=lambda item: (not item[2], abs(item[0] - (x0 + CHUNK_BLOCOS / 2)), abs(item[1] - (y0 + CHUNK_BLOCOS / 2))))
    if not candidatos:
        return melhor_chunk, (0.0, 0.0)

    sx, sy, _ = candidatos[0]
    return melhor_chunk, (float(sx), float(sy))


def gerar_novo_estado_mundo(players: Dict[str, object] | None = None) -> Dict[str, object]:
    seed = _gerar_seed()
    _executar_world_generator(seed)

    meta_java, grid_blocos, grid_biomas, grid_estruturas = _carregar_world_grids()
    if not ARQUIVO_PREVIEW.exists():
        raise FileNotFoundError(f"Preview de biomas não foi gerado: {ARQUIVO_PREVIEW}")

    spawn_chunk, spawn = _escolher_spawn(grid_blocos)

    estado = {
        "meta": {
            "largura_blocos": int(meta_java["width"]),
            "altura_blocos": int(meta_java["height"]),
            "seed": int(meta_java["seed"]),
            "chunk_blocos": int(CHUNK_BLOCOS),
            "bloco_tamanho_px": int(BLOCO_TAMANHO_PX),
            "spawn_chunk": [int(spawn_chunk[0]), int(spawn_chunk[1])],
        },
        "spawn": [float(spawn[0]), float(spawn[1])],
        "grid": grid_blocos,
        "grid_biomas": grid_biomas,
        "grid_estruturas_naturais": grid_estruturas,
        "players": dict(players or {}),
    }

    global LARGURA_BLOCOS, ALTURA_BLOCOS
    LARGURA_BLOCOS = int(meta_java["width"])
    ALTURA_BLOCOS = int(meta_java["height"])
    return estado


def salvar_estado_mundo(estado_mundo: Dict[str, object]) -> None:
    with ARQUIVO_MUNDO.open("w", encoding="utf-8") as f:
        json.dump(estado_mundo, f, ensure_ascii=False, indent=2)


def carregar_ou_criar_estado_mundo() -> Dict[str, object]:
    if ARQUIVO_MUNDO.exists():
        with ARQUIVO_MUNDO.open("r", encoding="utf-8") as f:
            estado = json.load(f)
        if isinstance(estado, dict) and isinstance(estado.get("grid"), list) and estado.get("grid"):
            meta = estado.get("meta", {}) if isinstance(estado.get("meta"), dict) else {}
            global LARGURA_BLOCOS, ALTURA_BLOCOS
            LARGURA_BLOCOS = int(meta.get("largura_blocos", len(estado["grid"][0]) if estado["grid"] else 0))
            ALTURA_BLOCOS = int(meta.get("altura_blocos", len(estado["grid"])))
            return estado

    estado = gerar_novo_estado_mundo(players={})
    salvar_estado_mundo(estado)
    return estado


def obter_posicao_spawn(estado_mundo: Dict[str, object] | None = None) -> Tuple[float, float]:
    estado = estado_mundo if isinstance(estado_mundo, dict) else carregar_ou_criar_estado_mundo()
    spawn = estado.get("spawn", [0.0, 0.0])
    try:
        x = float(spawn[0])
        y = float(spawn[1])
    except (TypeError, ValueError, IndexError):
        grid = estado.get("grid", [])
        if not isinstance(grid, list) or not grid:
            return (0.0, 0.0)
        _, (x, y) = _escolher_spawn(grid)
    return (x, y)


try:
    _estado_existente = carregar_ou_criar_estado_mundo()
    _meta = _estado_existente.get("meta", {}) if isinstance(_estado_existente, dict) else {}
    LARGURA_BLOCOS = int(_meta.get("largura_blocos", LARGURA_BLOCOS))
    ALTURA_BLOCOS = int(_meta.get("altura_blocos", ALTURA_BLOCOS))
except Exception:
    pass
