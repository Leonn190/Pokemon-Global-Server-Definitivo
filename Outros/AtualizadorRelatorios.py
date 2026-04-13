from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================
# CONFIGURAÇÃO MANUAL
# ============================================================
# Troque este valor sempre que quiser atualizar para um modelo novo.
MODELO_ATUAL = "modelo_atual_v1"

# Pasta dos relatórios antigos/originais.
PASTA_RELATORIOS_ORIGINAIS = "Outros/Relatorios"

# Pasta onde serão gravados os relatórios regenerados.
PASTA_RELATORIOS_ATUALIZADOS = "Outros/Relatorios atualizados"

# Caminho do gerador moderno que será usado para regenerar tudo.
CAMINHO_GERADOR_ATUAL = "Outros/GeradorRelatorios.py"

# Se True, relatórios sem campo de modelo também serão atualizados.
ATUALIZAR_SEM_MODELO = True

# Se quiser limitar testes, coloque um número. Ex.: 3
# None = sem limite.
LIMITE_RELATORIOS: Optional[int] = None

# Se True, mostra logs mais detalhados.
MODO_VERBOSE = True


# ============================================================
# UTILITÁRIOS
# ============================================================
def log(msg: str) -> None:
    print(msg)


def vlog(msg: str) -> None:
    if MODO_VERBOSE:
        print(msg)


def agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rodar(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def ler_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def salvar_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_datetime_seguro(valor: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except Exception:
        return None


# ============================================================
# MODELO DO RELATÓRIO
# ============================================================
def extrair_modelo(relatorio: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(relatorio, dict):
        return None

    candidatos = [
        relatorio.get("modelo"),
        relatorio.get("versao_modelo"),
        relatorio.get("model"),
        relatorio.get("report_model"),
    ]

    meta = relatorio.get("meta")
    if isinstance(meta, dict):
        candidatos.extend(
            [
                meta.get("modelo"),
                meta.get("versao_modelo"),
                meta.get("model"),
                meta.get("report_model"),
            ]
        )

    for item in candidatos:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def registrar_modelo(relatorio: Dict[str, Any], modelo: str) -> None:
    meta = relatorio.setdefault("meta", {})
    if not isinstance(meta, dict):
        meta = {}
        relatorio["meta"] = meta

    meta["modelo"] = modelo
    relatorio["modelo"] = modelo


# ============================================================
# DATA DO RELATÓRIO ANTIGO
# ============================================================
def extrair_data_relatorio(relatorio_path: Path, relatorio: Optional[Dict[str, Any]]) -> datetime:
    # 1) tentar meta.criado_em
    if isinstance(relatorio, dict):
        meta = relatorio.get("meta")
        if isinstance(meta, dict):
            criado_em = meta.get("criado_em")
            if isinstance(criado_em, str):
                dt = parse_datetime_seguro(criado_em)
                if dt is not None:
                    return dt

    # 2) tentar nome do arquivo: YYYY-MM-DD_HH-MM-SS.json
    try:
        return datetime.strptime(relatorio_path.stem, "%Y-%m-%d_%H-%M-%S")
    except Exception:
        pass

    # 3) fallback: mtime do arquivo
    return datetime.fromtimestamp(relatorio_path.stat().st_mtime)


# ============================================================
# GIT
# ============================================================
def validar_git(repo_root: Path) -> bool:
    if not (repo_root / ".git").exists():
        log("[ERRO] Esta pasta não parece ser um repositório Git.")
        return False

    try:
        proc = rodar(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_root)
        return proc.returncode == 0 and (proc.stdout or "").strip() == "true"
    except Exception:
        log("[ERRO] Não foi possível executar o Git neste ambiente.")
        return False


def achar_commit_por_data(repo_root: Path, dt: datetime) -> Optional[str]:
    # Usa o commit mais recente em ou antes do horário do relatório antigo.
    before = dt.strftime("%Y-%m-%d %H:%M:%S")
    proc = rodar(["git", "rev-list", "-n", "1", f"--before={before}", "HEAD"], cwd=repo_root)
    commit_hash = (proc.stdout or "").strip()
    if proc.returncode != 0 or not commit_hash:
        return None
    return commit_hash


def info_commit(repo_root: Path, commit_hash: str) -> Dict[str, str]:
    proc = rodar(
        ["git", "show", "-s", "--date=iso-strict", "--format=%H|%cI|%an|%s", commit_hash],
        cwd=repo_root,
    )
    linha = (proc.stdout or "").strip()
    partes = linha.split("|", 3)
    if len(partes) != 4:
        return {
            "hash": commit_hash,
            "data": "",
            "autor": "",
            "mensagem": "",
        }
    return {
        "hash": partes[0],
        "data": partes[1],
        "autor": partes[2],
        "mensagem": partes[3],
    }


# ============================================================
# WORKTREE TEMPORÁRIO
# ============================================================
def criar_worktree_temporario(repo_root: Path, commit_hash: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmp = tempfile.TemporaryDirectory(prefix="relatorio_rebuild_")
    worktree_dir = Path(tmp.name)

    proc = rodar(["git", "worktree", "add", "--detach", str(worktree_dir), commit_hash], cwd=repo_root)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        tmp.cleanup()
        raise RuntimeError(f"Falha ao criar worktree temporário: {stderr}")

    return tmp, worktree_dir


def remover_worktree_temporario(repo_root: Path, worktree_dir: Path, tmp: tempfile.TemporaryDirectory[str]) -> None:
    try:
        rodar(["git", "worktree", "remove", "--force", str(worktree_dir)], cwd=repo_root)
    finally:
        tmp.cleanup()


# ============================================================
# GERAR RELATÓRIO MODERNO EM SNAPSHOT ANTIGO
# ============================================================
def copiar_gerador_moderno_para_snapshot(repo_root: Path, worktree_dir: Path) -> Path:
    gerador_atual = repo_root / CAMINHO_GERADOR_ATUAL
    if not gerador_atual.exists():
        raise FileNotFoundError(f"Gerador atual não encontrado em: {gerador_atual}")

    destino = worktree_dir / CAMINHO_GERADOR_ATUAL
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(gerador_atual, destino)
    return destino


def localizar_json_gerado(relatorios_dir: Path, antes: set[str]) -> Optional[Path]:
    depois = sorted(relatorios_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in depois:
        if p.name not in antes:
            return p
    return depois[0] if depois else None


def rodar_gerador_moderno_no_snapshot(
    repo_root: Path,
    worktree_dir: Path,
) -> Path:
    gerador_no_snapshot = copiar_gerador_moderno_para_snapshot(repo_root, worktree_dir)
    relatorios_dir_snapshot = worktree_dir / PASTA_RELATORIOS_ORIGINAIS
    relatorios_dir_snapshot.mkdir(parents=True, exist_ok=True)

    antes = {p.name for p in relatorios_dir_snapshot.glob("*.json")}

    proc = subprocess.run(
        [sys.executable, str(gerador_no_snapshot)],
        cwd=str(worktree_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "Falha ao rodar o gerador moderno no snapshot antigo.\n"
            f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        )

    json_gerado = localizar_json_gerado(relatorios_dir_snapshot, antes)
    if json_gerado is None:
        raise RuntimeError("O gerador rodou, mas nenhum JSON novo foi encontrado no snapshot.")

    return json_gerado


# ============================================================
# ATUALIZAÇÃO DE UM RELATÓRIO
# ============================================================
def enriquecer_relatorio_atualizado(
    relatorio_gerado: Dict[str, Any],
    *,
    nome_original: str,
    modelo_original: Optional[str],
    data_original: datetime,
    commit_usado: Dict[str, str],
) -> Dict[str, Any]:
    registrar_modelo(relatorio_gerado, MODELO_ATUAL)

    meta = relatorio_gerado.setdefault("meta", {})
    if not isinstance(meta, dict):
        meta = {}
        relatorio_gerado["meta"] = meta

    meta["relatorio_original"] = nome_original
    meta["modelo_original"] = modelo_original
    meta["data_relatorio_original"] = data_original.isoformat(timespec="seconds")
    meta["atualizado_em"] = agora_iso()
    meta["reconstruido_por"] = "AtualizadorRelatorios.py"
    meta["commit_reconstruido"] = commit_usado.get("hash", "")
    meta["commit_reconstruido_data"] = commit_usado.get("data", "")
    meta["commit_reconstruido_autor"] = commit_usado.get("autor", "")
    meta["commit_reconstruido_mensagem"] = commit_usado.get("mensagem", "")
    meta["modo_reconstrucao"] = "commit_mais_recente_antes_da_data_do_relatorio"

    return relatorio_gerado


# ============================================================
# FLUXO PRINCIPAL
# ============================================================
def main() -> None:
    script_path = Path(__file__).resolve()
    outros_dir = script_path.parent
    repo_root = outros_dir.parent

    pasta_relatorios_origem = repo_root / PASTA_RELATORIOS_ORIGINAIS
    pasta_relatorios_atualizados = repo_root / PASTA_RELATORIOS_ATUALIZADOS
    pasta_relatorios_atualizados.mkdir(parents=True, exist_ok=True)

    if not validar_git(repo_root):
        return

    if not pasta_relatorios_origem.exists():
        log(f"[ERRO] Pasta de relatórios não encontrada: {pasta_relatorios_origem}")
        return

    relatorios = sorted(pasta_relatorios_origem.glob("*.json"))
    if LIMITE_RELATORIOS is not None:
        relatorios = relatorios[:LIMITE_RELATORIOS]

    total = len(relatorios)
    atualizados = 0
    pulados = 0
    falhas = 0

    log("=" * 70)
    log("ATUALIZADOR DE RELATÓRIOS")
    log("=" * 70)
    log(f"Repo: {repo_root}")
    log(f"Modelo alvo: {MODELO_ATUAL}")
    log(f"Origem: {pasta_relatorios_origem}")
    log(f"Destino: {pasta_relatorios_atualizados}")
    log(f"Relatórios encontrados: {total}")
    log("")

    for idx, relatorio_path in enumerate(relatorios, start=1):
        log(f"[{idx}/{total}] {relatorio_path.name}")
        relatorio_antigo = ler_json(relatorio_path)
        modelo_antigo = extrair_modelo(relatorio_antigo)

        precisa_atualizar = False
        if modelo_antigo is None:
            precisa_atualizar = ATUALIZAR_SEM_MODELO
        else:
            precisa_atualizar = modelo_antigo != MODELO_ATUAL

        if not precisa_atualizar:
            vlog(f"  - Pulado: já está no modelo alvo ({MODELO_ATUAL}).")
            pulados += 1
            continue

        data_relatorio = extrair_data_relatorio(relatorio_path, relatorio_antigo)
        vlog(f"  - Data base do relatório: {data_relatorio.isoformat(timespec='seconds')}")

        commit_hash = achar_commit_por_data(repo_root, data_relatorio)
        if not commit_hash:
            log("  - Falha: não foi encontrado commit compatível com essa data.")
            falhas += 1
            continue

        commit_usado = info_commit(repo_root, commit_hash)
        vlog(f"  - Commit escolhido: {commit_usado.get('hash', '')[:12]} | {commit_usado.get('data', '')}")

        tmp = None
        worktree_dir = None
        try:
            tmp, worktree_dir = criar_worktree_temporario(repo_root, commit_hash)
            json_gerado = rodar_gerador_moderno_no_snapshot(repo_root, worktree_dir)
            relatorio_novo = ler_json(json_gerado)
            if not isinstance(relatorio_novo, dict):
                raise RuntimeError("JSON gerado é inválido ou não pôde ser lido.")

            relatorio_novo = enriquecer_relatorio_atualizado(
                relatorio_novo,
                nome_original=relatorio_path.name,
                modelo_original=modelo_antigo,
                data_original=data_relatorio,
                commit_usado=commit_usado,
            )

            destino = pasta_relatorios_atualizados / relatorio_path.name
            salvar_json(destino, relatorio_novo)
            atualizados += 1
            vlog(f"  - Atualizado com sucesso em: {destino}")

        except Exception as e:
            falhas += 1
            log(f"  - Falha ao atualizar: {e}")
        finally:
            if tmp is not None and worktree_dir is not None:
                remover_worktree_temporario(repo_root, worktree_dir, tmp)

    log("")
    log("=" * 70)
    log("RESUMO")
    log("=" * 70)
    log(f"Total encontrados : {total}")
    log(f"Atualizados      : {atualizados}")
    log(f"Pulados          : {pulados}")
    log(f"Falhas           : {falhas}")
    log(f"Pasta de saída   : {pasta_relatorios_atualizados}")


if __name__ == "__main__":
    main()
