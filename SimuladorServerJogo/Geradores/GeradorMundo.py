"""Integração do servidor simulado com o gerador de mundo em Java."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Dict, Tuple

from SimuladorServerJogo.Regras.Loader import carregar_regras_mundo

BLOCO_TAMANHO_PX = 32
CHUNK_BLOCOS = max(1, int(carregar_regras_mundo().get("ChunkTiles", 10)))

PASTA_SERVIDOR = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = PASTA_SERVIDOR.parent
ARQUIVO_MUNDO = PASTA_SERVIDOR / "MundoEstado.json"
ARQUIVO_WORLD_META = PASTA_SERVIDOR / "world_meta.json"
PASTA_WORLD_CHUNKS = PASTA_SERVIDOR / "world_chunks"
ARQUIVO_FOTO_MUNDO_JAVA = PASTA_SERVIDOR / "world_foto.png"
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


def _emitir_progresso(callback_progresso, percentual: int, mensagem: str) -> None:
    if not callable(callback_progresso):
        return
    callback_progresso(max(0, min(100, int(percentual))), str(mensagem))


def _executar_world_generator(seed: int, callback_progresso: Callable[[int, str], None] | None = None) -> None:
    _compilar_java_se_necessario()
    cmd = ["java", "-cp", str(PASTA_SERVIDOR), "WorldGenerator", str(seed), str(PASTA_SERVIDOR)]

    _emitir_progresso(callback_progresso, 1, "Preparando geração do mundo")

    proc = subprocess.Popen(
        cmd,
        cwd=PASTA_SERVIDOR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    etapa = "inicio"
    chunks_total = 0
    for raw_line in iter(proc.stdout.readline, ""):
        linha = raw_line.strip()
        if not linha:
            continue

        if "Gerando terreno base" in linha:
            etapa = "terreno"
            _emitir_progresso(callback_progresso, 5, "Gerando linhas do terreno")
            continue

        if "Gerando rios" in linha:
            etapa = "rios"
            _emitir_progresso(callback_progresso, 45, "Gerando rios e lagos")
            continue

        if "Posicionando estruturas naturais" in linha:
            etapa = "estruturas"
            _emitir_progresso(callback_progresso, 60, "Posicionando estruturas naturais")
            continue

        if "Posicionando ginasios, dungeons e vilas" in linha:
            etapa = "pois"
            _emitir_progresso(callback_progresso, 75, "Posicionando ginasios, dungeons e vilas")
            continue

        if "Exportando mundo em chunks" in linha:
            etapa = "chunks"
            chunks_total = 0
            if ARQUIVO_WORLD_META.exists():
                try:
                    meta = _carregar_world_meta()
                    chunks_total = int(meta.get("chunks_x", 0)) * int(meta.get("chunks_y", 0))
                except Exception:
                    chunks_total = 0
            _emitir_progresso(callback_progresso, 82, "Salvando chunks")
            continue

        m_linha = re.search(r"linha\s+(\d+)\s*/\s*(\d+)", linha)
        if m_linha and etapa == "terreno":
            atual = int(m_linha.group(1))
            total = max(1, int(m_linha.group(2)))
            pct = 5 + int((atual / total) * 40)
            _emitir_progresso(callback_progresso, pct, f"Gerando linhas do terreno ({atual}/{total})")
            continue

        m_estrut = re.search(r"estruturas na linha\s+(\d+)\s*/\s*(\d+)", linha)
        if m_estrut:
            atual = int(m_estrut.group(1))
            total = max(1, int(m_estrut.group(2)))
            pct = 60 + int((atual / total) * 15)
            _emitir_progresso(callback_progresso, pct, f"Posicionando estruturas naturais ({atual}/{total})")
            continue

        m_rios = re.search(r"fontes de rio criadas:\s*(\d+)\s*/\s*(\d+)", linha)
        if m_rios:
            atual = int(m_rios.group(1))
            total = max(1, int(m_rios.group(2)))
            pct = 45 + int((atual / total) * 15)
            _emitir_progresso(callback_progresso, pct, f"Gerando rios e lagos ({atual}/{total})")
            continue

        m_prog = re.search(r"\[PROGRESSO\]\s+ETAPA=CHUNKS\s+ATUAL=(\d+)\s+TOTAL=(\d+)\s+MSG=(.+)", linha)
        if m_prog:
            atual = int(m_prog.group(1))
            total = max(1, int(m_prog.group(2)))
            pct = 82 + int((atual / total) * 13)
            _emitir_progresso(callback_progresso, pct, f"Salvando chunks ({atual}/{total})")
            continue

        if etapa == "chunks" and PASTA_WORLD_CHUNKS.exists() and chunks_total > 0:
            chunks_prontos = len(list(PASTA_WORLD_CHUNKS.glob("chunk_*.json")))
            pct = 82 + int((chunks_prontos / max(1, chunks_total)) * 13)
            _emitir_progresso(callback_progresso, pct, f"Salvando chunks ({chunks_prontos}/{chunks_total})")

    saida = proc.wait()
    if saida != 0:
        raise subprocess.CalledProcessError(saida, cmd)
    if not ARQUIVO_FOTO_MUNDO_JAVA.exists():
        raise FileNotFoundError(f"Foto do mundo não foi gerada em {ARQUIVO_FOTO_MUNDO_JAVA}")


def limpar_arquivos_mundo() -> None:
    if ARQUIVO_MUNDO.exists():
        ARQUIVO_MUNDO.unlink()
    if ARQUIVO_WORLD_META.exists():
        ARQUIVO_WORLD_META.unlink()
    if ARQUIVO_FOTO_MUNDO_JAVA.exists():
        ARQUIVO_FOTO_MUNDO_JAVA.unlink()
    if PASTA_WORLD_CHUNKS.exists():
        for arquivo in PASTA_WORLD_CHUNKS.glob("*.json"):
            try:
                arquivo.unlink()
            except OSError:
                pass
        try:
            PASTA_WORLD_CHUNKS.rmdir()
        except OSError:
            pass


def _carregar_world_meta() -> Dict[str, int | float]:
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
    if chunk_blocos_disco != int(CHUNK_BLOCOS):
        raise ValueError(
            "world_meta.json inválido: chunk_blocos_disco deve ser igual a "
            f"{int(CHUNK_BLOCOS)} (10x10 tiles por chunk)"
        )
    if chunks_x <= 0 or chunks_y <= 0:
        raise ValueError("world_meta.json inválido: chunks_x/chunks_y devem ser positivos")

    required_spawn = ("spawn_chunk_x", "spawn_chunk_y", "spawn_x", "spawn_y")
    missing = [chave for chave in required_spawn if payload.get(chave) is None]
    if missing:
        raise ValueError("world_meta.json inválido: campos obrigatórios de spawn ausentes: " + ", ".join(missing))

    return {
        "width": largura,
        "height": altura,
        "seed": seed,
        "chunk_blocos_disco": chunk_blocos_disco,
        "chunks_x": chunks_x,
        "chunks_y": chunks_y,
        "spawn_chunk_x": int(payload["spawn_chunk_x"]),
        "spawn_chunk_y": int(payload["spawn_chunk_y"]),
        "spawn_x": float(payload["spawn_x"]),
        "spawn_y": float(payload["spawn_y"]),
    }


def gerar_novo_estado_mundo(players: Dict[str, object] | None = None, callback_progresso: Callable[[int, str], None] | None = None) -> Dict[str, object]:
    seed = _gerar_seed()
    _executar_world_generator(seed, callback_progresso=callback_progresso)

    meta_java = _carregar_world_meta()
    _emitir_progresso(callback_progresso, 96, "Finalizando mundo")
    spawn_chunk = (int(meta_java["spawn_chunk_x"]), int(meta_java["spawn_chunk_y"]))
    spawn = (float(meta_java["spawn_x"]), float(meta_java["spawn_y"]))

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


def carregar_estado_mundo() -> Dict[str, object]:
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

    return {
        "meta": {},
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
        "players": {},
        "spawn": [0.0, 0.0],
    }


def carregar_ou_criar_estado_mundo() -> Dict[str, object]:
    estado = carregar_estado_mundo()
    if estado.get("meta"):
        return estado
    estado = gerar_novo_estado_mundo(players={})
    salvar_estado_mundo(estado)
    return estado


def obter_posicao_spawn(estado_mundo: Dict[str, object] | None = None) -> Tuple[float, float]:
    estado = estado_mundo if isinstance(estado_mundo, dict) else carregar_estado_mundo()
    spawn = estado.get("spawn", [0.0, 0.0])
    try:
        x = float(spawn[0])
        y = float(spawn[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("Estado do mundo inválido: spawn ausente ou inválido") from exc
    return (x, y)


try:
    _estado_existente = carregar_estado_mundo()
    _meta = _estado_existente.get("meta", {}) if isinstance(_estado_existente, dict) else {}
    LARGURA_BLOCOS = int(_meta.get("largura_blocos", LARGURA_BLOCOS))
    ALTURA_BLOCOS = int(_meta.get("altura_blocos", ALTURA_BLOCOS))
except Exception:
    pass
