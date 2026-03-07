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
ARQUIVO_WORLD_META = RAIZ_REPOSITORIO / "world_meta.json"
PASTA_WORLD_CHUNKS = RAIZ_REPOSITORIO / "world_chunks"
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


def _carregar_world_meta() -> Dict[str, int]:
    if not ARQUIVO_WORLD_META.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_WORLD_META}")

    with ARQUIVO_WORLD_META.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("world_meta.json inválido: conteúdo raiz não é objeto")

    largura = int(payload.get("width", 0))
    altura = int(payload.get("height", 0))
    seed = int(payload.get("seed", 0))
    chunk_blocos_disco = int(payload.get("chunk_blocos_disco", payload.get("chunk_blocos", CHUNK_BLOCOS)))
    chunks_x = int(payload.get("chunks_x", 0))
    chunks_y = int(payload.get("chunks_y", 0))
    if largura <= 0 or altura <= 0:
        raise ValueError("world_meta.json inválido: width/height devem ser positivos")
    if chunk_blocos_disco <= 0:
        raise ValueError("world_meta.json inválido: chunk_blocos_disco deve ser positivo")
    if chunks_x <= 0 or chunks_y <= 0:
        raise ValueError("world_meta.json inválido: chunks_x/chunks_y devem ser positivos")

    return {
        "width": largura,
        "height": altura,
        "seed": seed,
        "chunk_blocos_disco": chunk_blocos_disco,
        "chunks_x": chunks_x,
        "chunks_y": chunks_y,
    }


def _carregar_chunk_blocos(meta: Dict[str, int], cx: int, cy: int) -> List[List[int]]:
    arquivo_chunk = PASTA_WORLD_CHUNKS / f"chunk_{cx}_{cy}.json"
    if not arquivo_chunk.exists():
        raise FileNotFoundError(f"Chunk não encontrado: {arquivo_chunk}")

    with arquivo_chunk.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Chunk inválido (raiz não é objeto): {arquivo_chunk.name}")

    chunk_meta = payload.get("meta", {})
    if not isinstance(chunk_meta, dict):
        raise ValueError(f"Chunk inválido (meta ausente): {arquivo_chunk.name}")

    chunk_blocos_disco = int(chunk_meta.get("chunk_blocos", meta["chunk_blocos_disco"]))
    grid_blocos = _validar_grid_numerica("grid_blocos", payload.get("grid_blocos"), chunk_blocos_disco, chunk_blocos_disco)
    return grid_blocos


def _chunk_totalmente_valido(chunk_grid: Sequence[Sequence[int]], chunk_blocos: int, cx: int, cy: int, largura: int, altura: int) -> bool:
    x0 = cx * chunk_blocos
    y0 = cy * chunk_blocos
    for by, linha in enumerate(chunk_grid):
        gy = y0 + by
        for bx, valor in enumerate(linha):
            gx = x0 + bx
            if gx >= largura or gy >= altura:
                continue
            if int(valor) != 3:
                return False
    return True


def _chunk_sem_agua(chunk_grid: Sequence[Sequence[int]], chunk_blocos: int, cx: int, cy: int, largura: int, altura: int) -> bool:
    x0 = cx * chunk_blocos
    y0 = cy * chunk_blocos
    for by, linha in enumerate(chunk_grid):
        gy = y0 + by
        for bx, valor in enumerate(linha):
            gx = x0 + bx
            if gx >= largura or gy >= altura:
                continue
            tile = int(valor)
            if tile == 0 or tile == 1:
                return False
    return True


def _escolher_spawn_por_chunks(meta: Dict[str, int]) -> Tuple[Tuple[int, int], Tuple[float, float]]:
    chunk_blocos = int(meta["chunk_blocos_disco"])
    largura = int(meta["width"])
    altura = int(meta["height"])
    total_chunks_x = int(meta["chunks_x"])
    total_chunks_y = int(meta["chunks_y"])

    centro_chunk = (total_chunks_x // 2, total_chunks_y // 2)

    melhor_chunk_bloco3 = None
    melhor_dist_bloco3 = None
    melhor_chunk_sem_agua = None
    melhor_dist_sem_agua = None
    for cy in range(total_chunks_y):
        for cx in range(total_chunks_x):
            grid_chunk = _carregar_chunk_blocos(meta, cx, cy)
            dist = abs(cx - centro_chunk[0]) + abs(cy - centro_chunk[1])
            if _chunk_totalmente_valido(grid_chunk, chunk_blocos, cx, cy, largura, altura):
                if melhor_dist_bloco3 is None or dist < melhor_dist_bloco3:
                    melhor_chunk_bloco3 = (cx, cy)
                    melhor_dist_bloco3 = dist
            if _chunk_sem_agua(grid_chunk, chunk_blocos, cx, cy, largura, altura):
                if melhor_dist_sem_agua is None or dist < melhor_dist_sem_agua:
                    melhor_chunk_sem_agua = (cx, cy)
                    melhor_dist_sem_agua = dist

    melhor_chunk = melhor_chunk_bloco3
    if melhor_chunk is None:
        melhor_chunk = melhor_chunk_sem_agua
    if melhor_chunk is None:
        melhor_chunk = centro_chunk

    x0 = melhor_chunk[0] * chunk_blocos
    y0 = melhor_chunk[1] * chunk_blocos

    chunk_spawn = _carregar_chunk_blocos(meta, melhor_chunk[0], melhor_chunk[1])

    candidatos = []
    for by, linha in enumerate(chunk_spawn):
        y = y0 + by
        if y >= altura:
            continue
        for bx, valor in enumerate(linha):
            x = x0 + bx
            if x >= largura:
                continue
            candidatos.append((x, y, int(valor) == 3))

    candidatos.sort(key=lambda item: (not item[2], abs(item[0] - (x0 + chunk_blocos / 2)), abs(item[1] - (y0 + chunk_blocos / 2))))
    if not candidatos:
        return melhor_chunk, (0.0, 0.0)

    sx, sy, _ = candidatos[0]
    return melhor_chunk, (float(sx), float(sy))


def gerar_novo_estado_mundo(players: Dict[str, object] | None = None) -> Dict[str, object]:
    seed = _gerar_seed()
    _executar_world_generator(seed)

    meta_java = _carregar_world_meta()
    spawn_chunk, spawn = _escolher_spawn_por_chunks(meta_java)

    estado = {
        "meta": {
            "largura_blocos": int(meta_java["width"]),
            "altura_blocos": int(meta_java["height"]),
            "seed": int(meta_java["seed"]),
            "chunk_blocos": int(CHUNK_BLOCOS),
            "chunk_blocos_disco": int(meta_java["chunk_blocos_disco"]),
            "bloco_tamanho_px": int(BLOCO_TAMANHO_PX),
            "spawn_chunk": [int(spawn_chunk[0]), int(spawn_chunk[1])],
            "chunks_x": int(meta_java["chunks_x"]),
            "chunks_y": int(meta_java["chunks_y"]),
        },
        "spawn": [float(spawn[0]), float(spawn[1])],
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
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
        if isinstance(estado, dict) and isinstance(estado.get("meta"), dict):
            meta = estado.get("meta", {}) if isinstance(estado.get("meta"), dict) else {}
            global LARGURA_BLOCOS, ALTURA_BLOCOS
            largura = int(meta.get("largura_blocos", 0))
            altura = int(meta.get("altura_blocos", 0))
            if largura > 0 and altura > 0:
                LARGURA_BLOCOS = largura
                ALTURA_BLOCOS = altura
                estado.setdefault("grid", [])
                estado.setdefault("grid_biomas", [])
                estado.setdefault("grid_estruturas_naturais", [])
                return estado

        if isinstance(estado, dict) and isinstance(estado.get("grid"), list) and estado.get("grid"):
            grid_legado = estado.get("grid", [])
            if isinstance(grid_legado, list):
                altura = len(grid_legado)
                largura = len(grid_legado[0]) if altura and isinstance(grid_legado[0], list) else 0
                if largura > 0 and altura > 0:
                    estado["meta"] = {
                        "largura_blocos": int(largura),
                        "altura_blocos": int(altura),
                        "seed": int((estado.get("meta", {}) or {}).get("seed", 0)) if isinstance(estado.get("meta", {}), dict) else 0,
                        "chunk_blocos": int(CHUNK_BLOCOS),
                        "chunk_blocos_disco": int(CHUNK_BLOCOS),
                        "bloco_tamanho_px": int(BLOCO_TAMANHO_PX),
                        "spawn_chunk": [0, 0],
                        "chunks_x": max(1, int((largura + CHUNK_BLOCOS - 1) // CHUNK_BLOCOS)),
                        "chunks_y": max(1, int((altura + CHUNK_BLOCOS - 1) // CHUNK_BLOCOS)),
                    }
                    LARGURA_BLOCOS = int(largura)
                    ALTURA_BLOCOS = int(altura)
                    estado.setdefault("grid_biomas", [])
                    estado.setdefault("grid_estruturas_naturais", [])
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
        try:
            meta = _carregar_world_meta()
            _, (x, y) = _escolher_spawn_por_chunks(meta)
        except Exception:
            return (0.0, 0.0)
    return (x, y)


try:
    _estado_existente = carregar_ou_criar_estado_mundo()
    _meta = _estado_existente.get("meta", {}) if isinstance(_estado_existente, dict) else {}
    LARGURA_BLOCOS = int(_meta.get("largura_blocos", LARGURA_BLOCOS))
    ALTURA_BLOCOS = int(_meta.get("altura_blocos", ALTURA_BLOCOS))
except Exception:
    pass
