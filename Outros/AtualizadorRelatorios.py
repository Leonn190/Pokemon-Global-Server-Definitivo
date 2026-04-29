from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# ============================================================
# CONFIGURAÇÃO MANUAL
# ============================================================
MODELO_ATUAL = 9
PASTA_RELATORIOS_ORIGINAIS = "Outros/RelatoriosLegado"
PASTA_RELATORIOS_ATUALIZADOS = "Outros/Relatorios"
CAMINHO_GERADOR_ATUAL = "Outros/GeradorRelatorios.py"
CAMINHO_ATUALIZADOR_README_ATUAL = "Outros/AtualizadorReadMe.py"
ATUALIZAR_SEM_MODELO = True
LIMITE_RELATORIOS: Optional[int] = None
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
    return datetime.now().astimezone().isoformat(timespec="seconds")


def rodar(cmd: list[str], cwd: Path, check: bool = False, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    env_final = None
    if env:
        env_final = dict(**env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
        env=env_final,
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


def salvar_texto(path: Path, texto: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def parse_datetime_seguro(valor: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return dt.astimezone().replace(tzinfo=None) if dt.tzinfo is not None else dt
    except Exception:
        return None


def extrair_primeiro_numero(relatorio: Optional[Dict[str, Any]], caminhos: tuple[tuple[str, ...], ...]) -> Optional[float]:
    if not isinstance(relatorio, dict):
        return None
    for caminho in caminhos:
        cur: Any = relatorio
        ok = True
        for chave in caminho:
            if not isinstance(cur, dict) or chave not in cur:
                ok = False
                break
            cur = cur[chave]
        if ok and isinstance(cur, (int, float)):
            return float(cur)
    return None


def extrair_horas_estimadas_relatorio(relatorio: Optional[Dict[str, Any]]) -> Optional[float]:
    return extrair_primeiro_numero(
        relatorio,
        (
            ("resumo", "horas_estimadas"),
            ("visao_geral", "horas_estimadas"),
            ("meta", "horas_estimadas"),
        ),
    )


def aplicar_horas_preservadas(relatorio: Dict[str, Any], horas: Optional[float]) -> None:
    if horas is None:
        return
    resumo = relatorio.setdefault("resumo", {})
    if not isinstance(resumo, dict):
        resumo = {}
        relatorio["resumo"] = resumo
    resumo["horas_estimadas"] = horas

    meta = relatorio.setdefault("meta", {})
    if not isinstance(meta, dict):
        meta = {}
        relatorio["meta"] = meta
    meta["horas_preservadas_do_relatorio_original"] = horas


def aplicar_horas_preservadas_markdown(texto: str, horas: Optional[float]) -> str:
    if horas is None:
        return texto
    valor = f"{horas:.2f}"
    linhas = []
    trocou = False
    for linha in texto.splitlines():
        if linha.startswith("- **Horas estimadas:**"):
            linhas.append(f"- **Horas estimadas:** {valor}")
            trocou = True
        else:
            linhas.append(linha)
    resultado = "\n".join(linhas)
    if texto.endswith("\n"):
        resultado += "\n"
    return resultado if trocou else texto


# ============================================================
# MODELO DO RELATÓRIO
# ============================================================
def extrair_modelo(relatorio: Optional[Dict[str, Any]]) -> Optional[Any]:
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
        if item is None:
            continue
        if isinstance(item, str) and item.strip():
            texto = item.strip()
            if texto.isdigit():
                return int(texto)
            return texto
        if isinstance(item, (int, float)):
            return int(item)
    return None


def registrar_modelo(relatorio: Dict[str, Any], modelo: Any) -> None:
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
    if isinstance(relatorio, dict):
        meta = relatorio.get("meta")
        if isinstance(meta, dict):
            for chave in ("data_referencia", "criado_em", "data_relatorio_original"):
                criado_em = meta.get(chave)
                if isinstance(criado_em, str):
                    dt = parse_datetime_seguro(criado_em)
                    if dt is not None:
                        return dt

    try:
        return datetime.strptime(relatorio_path.stem, "%Y-%m-%d_%H-%M-%S")
    except Exception:
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
def criar_worktree_temporario(repo_root: Path, commit_hash: str) -> Tuple[tempfile.TemporaryDirectory[str], Path]:
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

    atualizador_readme = repo_root / CAMINHO_ATUALIZADOR_README_ATUAL
    if atualizador_readme.exists():
        destino_readme = worktree_dir / CAMINHO_ATUALIZADOR_README_ATUAL
        destino_readme.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(atualizador_readme, destino_readme)

    return destino


def json_dir_de_relatorios(relatorios_root: Path) -> Path:
    estruturado = relatorios_root / "Relatorios"
    return estruturado if estruturado.exists() or not list(relatorios_root.glob("*.json")) else relatorios_root


def registros_dir_de_relatorios(relatorios_root: Path) -> Path:
    estruturado = relatorios_root / "Registros"
    return estruturado if estruturado.exists() else relatorios_root


def imagens_dir_de_relatorios(relatorios_root: Path) -> Path:
    return relatorios_root / "Imagens"


def readmes_dir_de_relatorios(relatorios_root: Path) -> Path:
    return relatorios_root / "Readmes"


def garantir_estrutura_relatorios(relatorios_root: Path) -> None:
    imagens_dir_de_relatorios(relatorios_root).mkdir(parents=True, exist_ok=True)
    registros_dir = relatorios_root / "Registros"
    registros_dir.mkdir(parents=True, exist_ok=True)
    readmes_dir = relatorios_root / "Readmes"
    readmes_dir.mkdir(parents=True, exist_ok=True)
    json_dir = relatorios_root / "Relatorios"
    json_dir.mkdir(parents=True, exist_ok=True)


def listar_jsons_relatorios(relatorios_root: Path) -> list[Path]:
    json_dir = json_dir_de_relatorios(relatorios_root)
    return sorted(json_dir.glob("*.json"))


def localizar_json_gerado(relatorios_root: Path, antes: set[str]) -> Optional[Path]:
    json_dir = json_dir_de_relatorios(relatorios_root)
    depois = sorted(json_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in depois:
        if p.name not in antes:
            return p
    return depois[0] if depois else None


def localizar_md_gerado(relatorios_root: Path, stem_json: str) -> Optional[Path]:
    candidato = registros_dir_de_relatorios(relatorios_root) / f"{stem_json}.md"
    if candidato.exists():
        return candidato
    legado = relatorios_root / f"{stem_json}.md"
    if legado.exists():
        return legado
    return None


def localizar_pasta_imagens_gerada(relatorios_root: Path, stem_json: str) -> Optional[Path]:
    candidato = imagens_dir_de_relatorios(relatorios_root) / stem_json
    if candidato.exists() and candidato.is_dir():
        return candidato
    return None


def localizar_readme_gerado(relatorios_root: Path, stem_json: str) -> Optional[Path]:
    candidato = readmes_dir_de_relatorios(relatorios_root) / f"{stem_json}.md"
    if candidato.exists():
        return candidato
    return None


def rodar_gerador_moderno_no_snapshot(
    repo_root: Path,
    worktree_dir: Path,
    data_referencia: datetime,
) -> Tuple[Path, Optional[Path], Optional[Path], Optional[Path]]:
    gerador_no_snapshot = copiar_gerador_moderno_para_snapshot(repo_root, worktree_dir)
    relatorios_dir_snapshot = worktree_dir / PASTA_RELATORIOS_ATUALIZADOS
    relatorios_dir_snapshot.mkdir(parents=True, exist_ok=True)

    antes = {p.name for p in listar_jsons_relatorios(relatorios_dir_snapshot)}

    env = dict(os_environ_seguro())
    env["RELATORIO_DATA_REFERENCIA_ISO"] = data_referencia.isoformat(timespec="seconds")

    proc = subprocess.run(
        [sys.executable, str(gerador_no_snapshot)],
        cwd=str(worktree_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env=env,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "Falha ao rodar o gerador moderno no snapshot antigo.\n"
            f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        )

    json_gerado = localizar_json_gerado(relatorios_dir_snapshot, antes)
    if json_gerado is None:
        raise RuntimeError("O gerador rodou, mas nenhum JSON novo foi encontrado no snapshot.")

    md_gerado = localizar_md_gerado(relatorios_dir_snapshot, json_gerado.stem)
    imagens_geradas = localizar_pasta_imagens_gerada(relatorios_dir_snapshot, json_gerado.stem)
    readme_gerado = localizar_readme_gerado(relatorios_dir_snapshot, json_gerado.stem)
    return json_gerado, md_gerado, imagens_geradas, readme_gerado


def os_environ_seguro() -> Dict[str, str]:
    import os
    return dict(os.environ)


# ============================================================
# CÓPIA / AJUSTES DE ARTEFATOS
# ============================================================
def reescrever_referencias_imagens_md(texto: str, stem_original: str, stem_gerado: str) -> str:
    return texto.replace(f"Imagens/{stem_gerado}/", f"Imagens/{stem_original}/")


def copiar_pasta_imagens(origem: Path, destino: Path) -> None:
    if destino.exists():
        shutil.rmtree(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(origem, destino)


def preparar_pastas_relatorios(repo_root: Path) -> Tuple[Path, Path]:
    pasta_atual = repo_root / PASTA_RELATORIOS_ATUALIZADOS
    pasta_legado = repo_root / PASTA_RELATORIOS_ORIGINAIS

    if not pasta_legado.exists():
        if pasta_atual.exists():
            pasta_legado.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pasta_atual), str(pasta_legado))
            log(f"[OK] Pasta antiga movida para legado: {pasta_legado}")
        else:
            raise FileNotFoundError(f"Nenhuma pasta de relatórios encontrada em: {pasta_atual}")

    garantir_estrutura_relatorios(pasta_atual)
    return pasta_legado, pasta_atual


# ============================================================
# ATUALIZAÇÃO DE UM RELATÓRIO
# ============================================================
def enriquecer_relatorio_atualizado(
    relatorio_gerado: Dict[str, Any],
    *,
    repo_root: Path,
    nome_original: str,
    nome_md_original: str,
    stem_original: str,
    stem_gerado: str,
    modelo_original: Optional[Any],
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
    meta["arquivo"] = nome_original
    meta["arquivo_markdown"] = nome_md_original
    meta["imagens_dir"] = f"Outros/Relatorios/Imagens/{stem_original}"
    meta["projeto"] = repo_root.name
    meta["base_dir"] = str(repo_root)
    meta["relatorios_dir"] = PASTA_RELATORIOS_ATUALIZADOS
    meta["relatorios_json_dir"] = f"{PASTA_RELATORIOS_ATUALIZADOS}/Relatorios"
    meta["registros_dir"] = f"{PASTA_RELATORIOS_ATUALIZADOS}/Registros"
    meta["readmes_dir"] = f"{PASTA_RELATORIOS_ATUALIZADOS}/Readmes"
    meta["script"] = "Outros/AtualizadorRelatorios.py"
    meta["script_gerador_modelo"] = CAMINHO_GERADOR_ATUAL

    graficos = relatorio_gerado.get("graficos")
    if isinstance(graficos, dict):
        for chave, valor in list(graficos.items()):
            if not isinstance(valor, str):
                continue
            valor = valor.replace(
                f"Outros/Relatorios/Imagens/{stem_gerado}/",
                f"Outros/Relatorios/Imagens/{stem_original}/",
            )
            valor = valor.replace(f"Imagens/{stem_gerado}/", f"Imagens/{stem_original}/")
            graficos[chave] = valor

    return relatorio_gerado


# ============================================================
# FLUXO PRINCIPAL
# ============================================================
def main() -> None:
    script_path = Path(__file__).resolve()
    outros_dir = script_path.parent
    repo_root = outros_dir.parent

    if not validar_git(repo_root):
        return

    try:
        pasta_relatorios_origem, pasta_relatorios_atualizados = preparar_pastas_relatorios(repo_root)
    except Exception as e:
        log(f"[ERRO] {e}")
        return

    pasta_imagens_atualizadas = imagens_dir_de_relatorios(pasta_relatorios_atualizados)
    pasta_registros_atualizados = registros_dir_de_relatorios(pasta_relatorios_atualizados)
    pasta_readmes_atualizados = readmes_dir_de_relatorios(pasta_relatorios_atualizados)
    pasta_jsons_atualizados = json_dir_de_relatorios(pasta_relatorios_atualizados)

    relatorios = listar_jsons_relatorios(pasta_relatorios_origem)
    if LIMITE_RELATORIOS is not None:
        relatorios = relatorios[:LIMITE_RELATORIOS]

    total = len(relatorios)
    atualizados = 0
    pulados = 0
    falhas = 0

    log("=" * 70)
    log("ATUALIZADOR DE RELATÓRIOS")
    log("=" * 70)
    log(f"Projeto: {repo_root}")
    log(f"Modelo alvo: {MODELO_ATUAL}")
    log(f"Origem: {pasta_relatorios_origem}")
    log(f"Destino: {pasta_relatorios_atualizados}")
    log(f"Relatórios encontrados: {total}")
    log("")

    for idx, relatorio_path in enumerate(relatorios, start=1):
        log(f"[{idx}/{total}] {relatorio_path.name}")
        relatorio_antigo = ler_json(relatorio_path)
        modelo_antigo = extrair_modelo(relatorio_antigo)
        horas_original = extrair_horas_estimadas_relatorio(relatorio_antigo)

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
            json_gerado, md_gerado, imagens_geradas, readme_gerado = rodar_gerador_moderno_no_snapshot(repo_root, worktree_dir, data_relatorio)

            relatorio_novo = ler_json(json_gerado)
            if not isinstance(relatorio_novo, dict):
                raise RuntimeError("JSON gerado é inválido ou não pôde ser lido.")

            stem_original = relatorio_path.stem
            nome_md_original = f"{stem_original}.md"

            relatorio_novo = enriquecer_relatorio_atualizado(
                relatorio_novo,
                repo_root=repo_root,
                nome_original=relatorio_path.name,
                nome_md_original=nome_md_original,
                stem_original=stem_original,
                stem_gerado=json_gerado.stem,
                modelo_original=modelo_antigo,
                data_original=data_relatorio,
                commit_usado=commit_usado,
            )
            aplicar_horas_preservadas(relatorio_novo, horas_original)

            destino_json = pasta_jsons_atualizados / relatorio_path.name
            salvar_json(destino_json, relatorio_novo)

            if md_gerado and md_gerado.exists():
                md_texto = md_gerado.read_text(encoding="utf-8", errors="ignore")
                md_texto = reescrever_referencias_imagens_md(md_texto, stem_original=stem_original, stem_gerado=json_gerado.stem)
                md_texto = aplicar_horas_preservadas_markdown(md_texto, horas_original)
                destino_md = pasta_registros_atualizados / nome_md_original
                salvar_texto(destino_md, md_texto)
                vlog(f"  - Markdown atualizado: {destino_md}")
            else:
                vlog("  - Aviso: markdown não foi encontrado no snapshot gerado.")

            if readme_gerado and readme_gerado.exists():
                readme_texto = readme_gerado.read_text(encoding="utf-8", errors="ignore")
                destino_readme = pasta_readmes_atualizados / nome_md_original
                salvar_texto(destino_readme, readme_texto)
                vlog(f"  - README atualizado: {destino_readme}")
            else:
                vlog("  - Aviso: README não foi encontrado no snapshot gerado.")

            if imagens_geradas and imagens_geradas.exists():
                destino_imagens = pasta_imagens_atualizadas / stem_original
                copiar_pasta_imagens(imagens_geradas, destino_imagens)
                vlog(f"  - Imagens atualizadas: {destino_imagens}")
            else:
                vlog("  - Aviso: pasta de imagens não foi encontrada no snapshot gerado.")

            atualizados += 1
            vlog(f"  - Atualizado com sucesso em: {destino_json}")

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
