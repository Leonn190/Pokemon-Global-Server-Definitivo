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
import tomllib
from pathlib import Path
from typing import Callable, Dict, Tuple

from SimuladorServerJogo.Gerais import ContextoServidor

BLOCO_TAMANHO_PX = 32

PASTA_SERVIDOR = Path(__file__).resolve().parent
PASTA_MODULO_SIMULADOR = PASTA_SERVIDOR.parents[1]
RAIZ_REPOSITORIO = PASTA_SERVIDOR.parents[2]
PASTA_ESTADO_MUNDO = None
PASTAS_ESTADO_MUNDO_LEGADAS = ()
PASTA_WORLD_CHUNKS = None
PASTA_REGRAS = RAIZ_REPOSITORIO / "SimuladorServerJogo" / "Logica" / "Regras"
ARQUIVO_REGRAS_TERRENO_FONTE = PASTA_REGRAS / "Terreno.toml"
ARQUIVO_REGRAS_BIOMAS_FONTE = PASTA_REGRAS / "Biomas.toml"
ARQUIVO_REGRAS_LOCALIDADES_FONTE = PASTA_REGRAS / "Localidades.toml"

PASTA_JAVA = PASTA_SERVIDOR / "Java"
PASTA_JAVA_CLASSES = PASTA_JAVA / "classes"
PASTAS_JAVA_CLASSES_LEGADAS = (
    PASTA_JAVA / ".class",
)
ARQUIVOS_JAVA = [
    PASTA_JAVA / "WorldGenerator.java",
    PASTA_JAVA / "GeradorTerreno.java",
    PASTA_JAVA / "GeradorBiomas.java",
    PASTA_JAVA / "GeradorObjetos.java",
    PASTA_JAVA / "GeradorImagens.java",
    PASTA_JAVA / "GeradorLocalidades.java",
    PASTA_JAVA / "GeradorRotas.java",
]
ARQUIVO_CLASS_PRINCIPAL = PASTA_JAVA_CLASSES / "WorldGenerator.class"

LARGURA_BLOCOS = 0
ALTURA_BLOCOS = 0


def _carregar_regras_terreno() -> dict:
    if not ARQUIVO_REGRAS_TERRENO_FONTE.exists():
        raise FileNotFoundError(f"Arquivo de regras de terreno não encontrado: {ARQUIVO_REGRAS_TERRENO_FONTE}")
    with ARQUIVO_REGRAS_TERRENO_FONTE.open("rb") as f:
        payload = tomllib.load(f)
    if not isinstance(payload, dict):
        raise ValueError("Terreno.toml inválido: conteúdo raiz não é objeto")
    return payload


def _obter_chunk_blocos() -> int:
    payload = _carregar_regras_terreno()
    world = payload.get("world")
    if not isinstance(world, dict):
        raise ValueError("Terreno.toml inválido: seção [world] ausente")
    chunk_size = int(world.get("chunk_size", 0))
    if chunk_size <= 0:
        raise ValueError("Terreno.toml inválido: world.chunk_size deve ser positivo")
    return chunk_size


CHUNK_BLOCOS = _obter_chunk_blocos()
ARQUIVO_ESTADO_MUNDO_BASE = "MundoEstado.json"
ARQUIVOS_ESTADO_MUTAVEL = {
    "players": "MundoEstado.players.json",
    "npcs_vendedores": "MundoEstado.npcs_vendedores.json",
    "estruturas_naturais_tocadas": "MundoEstado.estruturas_naturais_tocadas.json",
    "tempo_mundo": "MundoEstado.tempo_mundo.json",
}


def obter_pasta_estado_mundo(criar: bool = False, exigir_ativo: bool = False) -> Path | None:
    try:
        pasta = ContextoServidor.obter_pasta_estado_mundo()
    except RuntimeError:
        if exigir_ativo:
            raise
        return None
    if criar:
        pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def obter_pasta_world_chunks() -> Path:
    pasta = obter_pasta_estado_mundo(criar=True, exigir_ativo=True)
    return pasta / "chunks"


def _estado_mundo_vazio() -> Dict[str, object]:
    return {
        "meta": {},
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
        "estruturas_naturais_tocadas": {},
        "players": {},
        "npcs_vendedores": {},
        "spawn": [0.0, 0.0],
        "tempo_mundo": {},
    }


def _pasta_estado_mundo_existente() -> Path | None:
    return obter_pasta_estado_mundo(criar=True, exigir_ativo=False)


def _arquivo_estado_mundo(nome: str, *, preferir_novo: bool = True) -> Path:
    pasta_base = obter_pasta_estado_mundo(criar=True, exigir_ativo=True) if preferir_novo else _pasta_estado_mundo_existente()
    if pasta_base is None:
        raise RuntimeError("Nenhum servidor local ativo definido")
    return pasta_base / nome


def _migrar_estado_mundo_legado_se_necessario() -> None:
    return


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


def _migrar_classes_java_legadas_se_necessario() -> None:
    PASTA_JAVA_CLASSES.mkdir(parents=True, exist_ok=True)
    for pasta_legada in PASTAS_JAVA_CLASSES_LEGADAS:
        if not pasta_legada.exists() or pasta_legada == PASTA_JAVA_CLASSES:
            continue
        if not pasta_legada.is_dir():
            continue
        for entrada in pasta_legada.iterdir():
            destino = PASTA_JAVA_CLASSES / entrada.name
            if destino.exists():
                try:
                    if entrada.stat().st_mtime <= destino.stat().st_mtime:
                        if entrada.is_dir():
                            shutil.rmtree(entrada, ignore_errors=True)
                        else:
                            entrada.unlink()
                        continue
                except OSError:
                    pass
                if destino.is_dir():
                    shutil.rmtree(destino, ignore_errors=True)
                else:
                    destino.unlink()
            shutil.move(str(entrada), str(destino))
        shutil.rmtree(pasta_legada, ignore_errors=True)
    for arquivo_class in PASTA_JAVA.glob("*.class"):
        destino = PASTA_JAVA_CLASSES / arquivo_class.name
        if destino.exists():
            try:
                if arquivo_class.stat().st_mtime <= destino.stat().st_mtime:
                    arquivo_class.unlink()
                    continue
            except OSError:
                pass
            destino.unlink()
        shutil.move(str(arquivo_class), str(destino))


def _compilar_java_se_necessario() -> None:
    PASTA_JAVA.mkdir(parents=True, exist_ok=True)
    PASTA_JAVA_CLASSES.mkdir(parents=True, exist_ok=True)
    _migrar_classes_java_legadas_se_necessario()
    for arquivo in ARQUIVOS_JAVA:
        if not arquivo.exists():
            raise FileNotFoundError(f"Arquivo Java obrigatório ausente: {arquivo}")

    versao_class = _obter_versao_major_class(ARQUIVO_CLASS_PRINCIPAL)
    versao_java_local = _obter_versao_java_local()
    maior_compativel = (versao_java_local + 44) if versao_java_local else None

    class_incompativel = (
        versao_class is not None
        and maior_compativel is not None
        and versao_class > maior_compativel
    )
    ultima_fonte = max(arquivo.stat().st_mtime for arquivo in ARQUIVOS_JAVA)
    precisa_compilar = (
        (not ARQUIVO_CLASS_PRINCIPAL.exists())
        or (ultima_fonte > ARQUIVO_CLASS_PRINCIPAL.stat().st_mtime)
        or class_incompativel
    )
    if not precisa_compilar:
        return

    cmd = ["javac", "-d", str(PASTA_JAVA_CLASSES)] + [arquivo.name for arquivo in ARQUIVOS_JAVA]
    subprocess.run(cmd, check=True, cwd=PASTA_JAVA)


def _emitir_progresso(callback_progresso, percentual: int, mensagem: str) -> None:
    if not callable(callback_progresso):
        return
    callback_progresso(max(0, min(100, int(percentual))), str(mensagem))


def _executar_world_generator(seed: int, callback_progresso: Callable[[int, str], None] | None = None) -> None:
    _compilar_java_se_necessario()

    pasta_estado_mundo = obter_pasta_estado_mundo(criar=True, exigir_ativo=True)
    arquivo_world_meta = pasta_estado_mundo / "world_meta.json"
    pasta_world_chunks = pasta_estado_mundo / "chunks"
    arquivo_foto_mundo_java = pasta_estado_mundo / "world_foto.png"
    pasta_estado_mundo.mkdir(parents=True, exist_ok=True)

    if not ARQUIVO_REGRAS_TERRENO_FONTE.exists():
        raise FileNotFoundError(f"Arquivo de regras de terreno não encontrado: {ARQUIVO_REGRAS_TERRENO_FONTE}")
    if not ARQUIVO_REGRAS_BIOMAS_FONTE.exists():
        raise FileNotFoundError(f"Arquivo de regras de biomas não encontrado: {ARQUIVO_REGRAS_BIOMAS_FONTE}")
    if not ARQUIVO_REGRAS_LOCALIDADES_FONTE.exists():
        raise FileNotFoundError(f"Arquivo de regras de localidades não encontrado: {ARQUIVO_REGRAS_LOCALIDADES_FONTE}")

    cmd = [
        "java",
        "-cp",
        str(PASTA_JAVA_CLASSES),
        "WorldGenerator",
        str(seed),
        str(pasta_estado_mundo),
        str(ARQUIVO_REGRAS_TERRENO_FONTE),
        str(ARQUIVO_REGRAS_BIOMAS_FONTE),
        str(ARQUIVO_REGRAS_LOCALIDADES_FONTE),
    ]

    _emitir_progresso(callback_progresso, 1, "Preparando geração do mundo")

    proc = subprocess.Popen(
        cmd,
        cwd=PASTA_JAVA,
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

        if "Gerando localidades, vilas e ginasios" in linha:
            etapa = "localidades"
            _emitir_progresso(callback_progresso, 58, "Gerando localidades, vilas e ginasios")
            continue

        if "Posicionando estruturas naturais" in linha:
            etapa = "estruturas"
            _emitir_progresso(callback_progresso, 68, "Posicionando estruturas naturais")
            continue

        if "Gerando rotas entre vilas" in linha:
            etapa = "rotas"
            _emitir_progresso(callback_progresso, 76, "Gerando rotas entre vilas")
            continue

        if "Posicionando dungeons" in linha:
            etapa = "dungeons"
            _emitir_progresso(callback_progresso, 84, "Posicionando dungeons")
            continue

        if "Exportando mundo em chunks" in linha:
            etapa = "chunks"
            chunks_total = 0
            if arquivo_world_meta.exists():
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
            _emitir_progresso(callback_progresso, 90, "Salvando chunks")
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
            pct = 68 + int((atual / total) * 8)
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
            pct = 90 + int((atual / total) * 6)
            _emitir_progresso(callback_progresso, pct, f"Salvando chunks ({atual}/{total})")
            continue

        if etapa == "chunks" and pasta_world_chunks.exists() and chunks_total > 0:
            chunks_prontos = len(list(pasta_world_chunks.glob("chunk_set_*.json")))
            if chunks_prontos <= 0:
                chunks_prontos = len(list(pasta_world_chunks.glob("chunk_*.json")))
            pct = 90 + int((chunks_prontos / max(1, chunks_total)) * 6)
            _emitir_progresso(callback_progresso, pct, f"Salvando chunks ({chunks_prontos}/{chunks_total})")

    saida = proc.wait()
    if saida != 0:
        erro = "\n".join(logs_execucao[-20:])
        raise subprocess.CalledProcessError(
            saida,
            cmd,
            output=erro,
        )
    if not arquivo_foto_mundo_java.exists():
        raise FileNotFoundError(f"Foto do mundo não foi gerada em {arquivo_foto_mundo_java}")


def limpar_arquivos_mundo() -> None:
    pasta = obter_pasta_estado_mundo(criar=False, exigir_ativo=True)
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True, exist_ok=True)


def _carregar_world_meta() -> Dict[str, int | float]:
    arquivo_world_meta = _arquivo_estado_mundo("world_meta.json", preferir_novo=False)
    if not arquivo_world_meta.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_world_meta}")

    with arquivo_world_meta.open("r", encoding="utf-8") as f:
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
            f"{int(CHUNK_BLOCOS)}"
        )
    if chunks_x <= 0 or chunks_y <= 0:
        raise ValueError("world_meta.json inválido: chunks_x/chunks_y devem ser positivos")

    required_spawn = ("spawn_chunk_x", "spawn_chunk_y", "spawn_x", "spawn_y")
    missing = [chave for chave in required_spawn if payload.get(chave) is None]
    if missing:
        raise ValueError("world_meta.json inválido: campos obrigatórios de spawn ausentes: " + ", ".join(missing))

    regioes = payload.get("regioes", []) if isinstance(payload.get("regioes"), list) else []
    vilas = payload.get("vilas", []) if isinstance(payload.get("vilas"), list) else []
    estadios = payload.get("estadios", []) if isinstance(payload.get("estadios"), list) else []
    rotas = payload.get("rotas", []) if isinstance(payload.get("rotas"), list) else []

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
        "regioes": regioes,
        "vilas": vilas,
        "estadios": estadios,
        "rotas": rotas,
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
            "regioes": list(meta_java.get("regioes", [])) if isinstance(meta_java.get("regioes", []), list) else [],
            "vilas": list(meta_java.get("vilas", [])) if isinstance(meta_java.get("vilas", []), list) else [],
            "estadios": list(meta_java.get("estadios", [])) if isinstance(meta_java.get("estadios", []), list) else [],
            "rotas": list(meta_java.get("rotas", [])) if isinstance(meta_java.get("rotas", []), list) else [],
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


def _salvar_json_atomico(arquivo: Path, payload) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(arquivo.parent), delete=False, prefix="mundo_", suffix=".tmp") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), check_circular=False)
        f.flush()
        os.fsync(f.fileno())
        caminho_tmp = f.name
    ultimo_erro = None
    for tentativa in range(8):
        try:
            os.replace(caminho_tmp, arquivo)
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


def _estado_mundo_base(estado_mundo: Dict[str, object]) -> Dict[str, object]:
    meta = estado_mundo.get("meta", {}) if isinstance(estado_mundo.get("meta"), dict) else {}
    spawn = estado_mundo.get("spawn", [0.0, 0.0])
    return {
        "meta": dict(meta),
        "grid": estado_mundo.get("grid", []),
        "grid_biomas": estado_mundo.get("grid_biomas", []),
        "grid_estruturas_naturais": estado_mundo.get("grid_estruturas_naturais", []),
        "estruturas_naturais_tocadas": {},
        "players": {},
        "npcs_vendedores": {},
        "spawn": list(spawn) if isinstance(spawn, (list, tuple)) else [0.0, 0.0],
        "tempo_mundo": {},
    }


def _estado_mundo_secao_mutavel(estado_mundo: Dict[str, object], secao: str):
    if secao == "players":
        return dict(estado_mundo.get("players", {})) if isinstance(estado_mundo.get("players"), dict) else {}
    if secao == "npcs_vendedores":
        return dict(estado_mundo.get("npcs_vendedores", {})) if isinstance(estado_mundo.get("npcs_vendedores"), dict) else {}
    if secao == "estruturas_naturais_tocadas":
        return dict(estado_mundo.get("estruturas_naturais_tocadas", {})) if isinstance(estado_mundo.get("estruturas_naturais_tocadas"), dict) else {}
    if secao == "tempo_mundo":
        return dict(estado_mundo.get("tempo_mundo", {})) if isinstance(estado_mundo.get("tempo_mundo"), dict) else {}
    raise KeyError(f"Secao de estado mutavel desconhecida: {secao}")


def _normalizar_secoes_mutaveis(secoes) -> Tuple[str, ...]:
    if secoes is None:
        return tuple(ARQUIVOS_ESTADO_MUTAVEL.keys())
    out = []
    for secao in secoes:
        secao_norm = str(secao or "").strip()
        if secao_norm in ARQUIVOS_ESTADO_MUTAVEL and secao_norm not in out:
            out.append(secao_norm)
    return tuple(out)


def salvar_estado_mundo(estado_mundo: Dict[str, object], secoes_mutaveis=None) -> None:
    arquivo_base = _arquivo_estado_mundo(ARQUIVO_ESTADO_MUNDO_BASE, preferir_novo=True)
    secoes_norm = _normalizar_secoes_mutaveis(secoes_mutaveis)
    meta_valida = isinstance(estado_mundo.get("meta"), dict) and bool(estado_mundo.get("meta"))
    if secoes_mutaveis is None or (not arquivo_base.exists() and meta_valida):
        _salvar_json_atomico(arquivo_base, _estado_mundo_base(estado_mundo))
    for secao in secoes_norm:
        nome_arquivo = ARQUIVOS_ESTADO_MUTAVEL.get(secao)
        if nome_arquivo is None:
            continue
        _salvar_json_atomico(
            _arquivo_estado_mundo(nome_arquivo, preferir_novo=True),
            _estado_mundo_secao_mutavel(estado_mundo, secao),
        )


def carregar_estado_mundo() -> Dict[str, object]:
    pasta_estado_mundo = _pasta_estado_mundo_existente()
    if pasta_estado_mundo is None:
        return _estado_mundo_vazio()
    if not pasta_estado_mundo.exists():
        pasta_estado_mundo.mkdir(parents=True, exist_ok=True)
    arquivo_mundo = pasta_estado_mundo / ARQUIVO_ESTADO_MUNDO_BASE
    if arquivo_mundo.exists():
        try:
            with arquivo_mundo.open("r", encoding="utf-8") as f:
                estado = json.load(f)
        except json.JSONDecodeError:
            bruto = arquivo_mundo.read_text(encoding="utf-8", errors="ignore")
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
                return _estado_mundo_vazio()
            salvar_estado_mundo(estado)
        for secao, nome_arquivo in ARQUIVOS_ESTADO_MUTAVEL.items():
            arquivo_secao = pasta_estado_mundo / nome_arquivo
            if not arquivo_secao.exists():
                continue
            try:
                with arquivo_secao.open("r", encoding="utf-8") as f:
                    payload_secao = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload_secao, dict):
                estado[secao] = payload_secao
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
                estado.setdefault("estruturas_naturais_tocadas", {})
                estado.setdefault("players", {})
                estado.setdefault("npcs_vendedores", {})
                estado.setdefault("tempo_mundo", {})
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
                    estado.setdefault("estruturas_naturais_tocadas", {})
                    estado.setdefault("players", {})
                    estado.setdefault("npcs_vendedores", {})
                    estado.setdefault("tempo_mundo", {})
                    return estado

    return _estado_mundo_vazio()


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
