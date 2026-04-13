"""Integração do servidor simulado com o gerador de mundo em Java."""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, Tuple

from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_mundo

BLOCO_TAMANHO_PX = 32
CHUNK_BLOCOS = max(1, int(carregar_regras_mundo().get("ChunkTiles", 10)))

PASTA_SERVIDOR = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = PASTA_SERVIDOR.parent
PASTA_ESTADO_MUNDO = RAIZ_REPOSITORIO / "EstadoMundo"
ARQUIVO_MUNDO = PASTA_ESTADO_MUNDO / "MundoEstado.json"
ARQUIVO_WORLD_META = PASTA_ESTADO_MUNDO / "world_meta.json"
PASTA_WORLD_CHUNKS = PASTA_ESTADO_MUNDO / "chunks"
ARQUIVO_FOTO_MUNDO_JAVA = PASTA_ESTADO_MUNDO / "world_foto.png"
ARQUIVO_REGRAS_GERACAO_FONTE = RAIZ_REPOSITORIO / "Regras" / "Geracao.json"
ARQUIVO_JAVA = PASTA_SERVIDOR / "WorldGenerator.java"
ARQUIVO_CLASS = PASTA_SERVIDOR / "WorldGenerator.class"

LARGURA_BLOCOS = 0
ALTURA_BLOCOS = 0


def _gerar_seed() -> int:
    return int(time.time_ns() % 9_000_000_000_000_000_000)


def _obter_versao_major_class(arquivo_class: Path) -> int | None:
    if not arquivo_class.exists():
        return None

    with arquivo_class.open("rb") as f:
        cabecalho = f.read(8)

    if len(cabecalho) < 8 or cabecalho[:4] != b"\xCA\xFE\xBA\xBE":
        return None

    _, _, major = struct.unpack(">IHH", cabecalho)
    return int(major)


def _obter_versao_java_local() -> int | None:
    try:
        proc = subprocess.run(
            ["javac", "-version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    saida = (proc.stdout or proc.stderr or "").strip()
    match = re.search(r"(\d+)(?:\.\d+)?", saida)
    if not match:
        return None
    return int(match.group(1))


def _compilar_java_se_necessario() -> None:
    versao_class = _obter_versao_major_class(ARQUIVO_CLASS)
    versao_java_local = _obter_versao_java_local()
    maior_compativel = (versao_java_local + 44) if versao_java_local else None

    class_incompativel = (
        versao_class is not None
        and maior_compativel is not None
        and versao_class > maior_compativel
    )
    precisa_compilar = (
        (not ARQUIVO_CLASS.exists())
        or (ARQUIVO_JAVA.stat().st_mtime > ARQUIVO_CLASS.stat().st_mtime)
        or class_incompativel
    )
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
    PASTA_ESTADO_MUNDO.mkdir(parents=True, exist_ok=True)
    if not ARQUIVO_REGRAS_GERACAO_FONTE.exists():
        raise FileNotFoundError(f"Arquivo de regras de geração não encontrado: {ARQUIVO_REGRAS_GERACAO_FONTE}")
    cmd = ["java", "-cp", str(PASTA_SERVIDOR), "WorldGenerator", str(seed), str(PASTA_ESTADO_MUNDO), str(ARQUIVO_REGRAS_GERACAO_FONTE)]

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
    logs_execucao: list[str] = []
    for raw_line in iter(proc.stdout.readline, ""):
        linha = raw_line.strip()
        if not linha:
            continue
        logs_execucao.append(linha)

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
                    chunks_x = int(meta.get("chunks_x", 0))
                    chunks_y = int(meta.get("chunks_y", 0))
                    chunks_por_arquivo = max(1, int(meta.get("chunks_por_arquivo", 10)))
                    grupos_x = max(1, int((chunks_x + chunks_por_arquivo - 1) // chunks_por_arquivo))
                    grupos_y = max(1, int((chunks_y + chunks_por_arquivo - 1) // chunks_por_arquivo))
                    chunks_total = grupos_x * grupos_y
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
            chunks_prontos = len(list(PASTA_WORLD_CHUNKS.glob("chunk_set_*.json")))
            if chunks_prontos <= 0:
                chunks_prontos = len(list(PASTA_WORLD_CHUNKS.glob("chunk_*.json")))
            pct = 82 + int((chunks_prontos / max(1, chunks_total)) * 13)
            _emitir_progresso(callback_progresso, pct, f"Salvando chunks ({chunks_prontos}/{chunks_total})")

    saida = proc.wait()
    if saida != 0:
        erro = "\n".join(logs_execucao[-20:])
        raise subprocess.CalledProcessError(
            saida,
            cmd,
            output=erro,
        )
    if not ARQUIVO_FOTO_MUNDO_JAVA.exists():
        raise FileNotFoundError(f"Foto do mundo não foi gerada em {ARQUIVO_FOTO_MUNDO_JAVA}")


def limpar_arquivos_mundo() -> None:
    if PASTA_ESTADO_MUNDO.exists():
        try:
            shutil.rmtree(PASTA_ESTADO_MUNDO)
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
    chunks_por_arquivo = max(1, int(payload.get("chunks_por_arquivo", 10)))

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

    estadios = payload.get("estadios", []) if isinstance(payload.get("estadios"), list) else []

    return {
        "width": largura,
        "height": altura,
        "seed": seed,
        "chunk_blocos_disco": chunk_blocos_disco,
        "chunks_x": chunks_x,
        "chunks_y": chunks_y,
        "chunks_por_arquivo": chunks_por_arquivo,
        "spawn_chunk_x": int(payload["spawn_chunk_x"]),
        "spawn_chunk_y": int(payload["spawn_chunk_y"]),
        "spawn_x": float(payload["spawn_x"]),
        "spawn_y": float(payload["spawn_y"]),
        "estadios": estadios,
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
            "chunks_por_arquivo": int(meta_java.get("chunks_por_arquivo", 10)),
            "estadios": list(meta_java.get("estadios", [])) if isinstance(meta_java.get("estadios", []), list) else [],
        },
        "spawn": [float(spawn[0]), float(spawn[1])],
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
        "players": dict(players or {}),
        "npcs_vendedores": {},
    }

    global LARGURA_BLOCOS, ALTURA_BLOCOS
    LARGURA_BLOCOS = int(meta_java["width"])
    ALTURA_BLOCOS = int(meta_java["height"])
    return estado


def salvar_estado_mundo(estado_mundo: Dict[str, object]) -> None:
    ARQUIVO_MUNDO.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(ARQUIVO_MUNDO.parent), delete=False, prefix="mundo_", suffix=".tmp") as f:
        json.dump(estado_mundo, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
        caminho_tmp = f.name
    ultimo_erro = None
    for tentativa in range(8):
        try:
            os.replace(caminho_tmp, ARQUIVO_MUNDO)
            return
        except PermissionError as exc:
            ultimo_erro = exc
            time.sleep(0.05 * (tentativa + 1))
    try:
        os.unlink(caminho_tmp)
    except OSError:
        pass
    if ultimo_erro is not None:
        raise ultimo_erro


def carregar_estado_mundo() -> Dict[str, object]:
    if not PASTA_ESTADO_MUNDO.exists():
        PASTA_ESTADO_MUNDO.mkdir(parents=True, exist_ok=True)
    if ARQUIVO_MUNDO.exists():
        try:
            with ARQUIVO_MUNDO.open("r", encoding="utf-8") as f:
                estado = json.load(f)
        except json.JSONDecodeError:
            bruto = ARQUIVO_MUNDO.read_text(encoding="utf-8", errors="ignore")
            bruto_limpo = bruto.lstrip()
            estado = None
            if bruto_limpo.lower().startswith("git"):
                idx = bruto_limpo.find("{")
                if idx >= 0:
                    try:
                        estado = json.loads(bruto_limpo[idx:])
                    except json.JSONDecodeError:
                        estado = None
            if not isinstance(estado, dict):
                return {
                    "meta": {},
                    "grid": [],
                    "grid_biomas": [],
                    "grid_estruturas_naturais": [],
                    "players": {},
                    "npcs_vendedores": {},
                    "spawn": [0.0, 0.0],
                }
            salvar_estado_mundo(estado)
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
                        "chunks_por_arquivo": 10,
                    }
                    LARGURA_BLOCOS = int(largura)
                    ALTURA_BLOCOS = int(altura)
                    estado.setdefault("grid_biomas", [])
                    estado.setdefault("grid_estruturas_naturais", [])
                    estado.setdefault("npcs_vendedores", {})
                    return estado

    return {
        "meta": {},
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
        "players": {},
        "npcs_vendedores": {},
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
