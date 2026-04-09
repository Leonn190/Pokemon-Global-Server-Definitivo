from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, List


CLASS_RE = re.compile(r"^\s*class\s+[A-Za-z_]\w*\s*(\(|:)")


# Pastas que a varredura deve ignorar
IGNORAR_PASTAS = {".git", "__pycache__", "Relatorios"}  # Relatorios aqui cobre o de Outros também
IGNORAR_EXTENSOES = {".pyc"}

# Extensões que vale a pena tentar contar linhas
EXTENSOES_TEXTO_INTERESSE = {
    ".py", ".json", ".java", ".js", ".ts", ".jsx", ".tsx", ".css", ".html", ".htm",
    ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".csv", ".xml", ".sql",
    ".bat", ".sh", ".ps1", ".properties", ".gradle", ".kt", ".kts", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".lua", ".rs", ".go", ".php", ".rb", ".vue", ".vhd", ".vhdl"
}


# Pastas principais que devem compor o rank específico do projeto.
# Observação: a contagem é recursiva, então cada pasta inclui todas as suas subpastas e arquivos internos.
PASTAS_IMPORTANTES_RANK: List[Tuple[str, str]] = [
    ("Codigo/Cenas", "Cenas"),
    ("Codigo/Geradores", "Geradores"),
    ("Codigo/ModulosBatalha", "ModulosBatalha"),
    ("Codigo/ModulosGerais", "ModulosGerais"),
    ("Codigo/ModulosMundo", "ModulosMundo"),
    ("Codigo/Paineis", "Paineis"),
    ("Codigo/Prefabs", "Prefabs"),
    ("Codigo/Server", "Server"),
    ("Codigo/Telas", "Telas"),
    ("SimuladorServerJogo", "SimuladorServerJogo"),
]



def bytes_para_gib(num_bytes: int) -> float:
    return num_bytes / (1024 ** 3)


def bytes_para_kib(num_bytes: int) -> float:
    return num_bytes / 1024


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_bytes(n: int) -> str:
    gib = bytes_para_gib(n)
    return f"{fmt_int(n)} bytes ({gib:.3f} GiB)"


def contar_linhas_arquivo(path: Path) -> int:
    total = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                total += 1
    except OSError:
        return 0
    return total


def span_linhas_no(no: ast.AST) -> int:
    inicio = getattr(no, "lineno", None)
    fim = getattr(no, "end_lineno", None)
    if isinstance(inicio, int) and isinstance(fim, int):
        return max(1, fim - inicio + 1)
    if isinstance(inicio, int):
        return 1
    return 0


def contar_imports_no_arquivo_py(codigo: str) -> int:
    """
    Conta quantos statements de import existem no arquivo:
      - ast.Import
      - ast.ImportFrom
    """
    try:
        arvore = ast.parse(codigo)
    except Exception:
        return 0

    total = 0
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Import, ast.ImportFrom)):
            total += 1
    return total


def analisar_python_ast(path: Path) -> Dict[str, Any]:
    try:
        codigo = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {
            "classes": 0,
            "funcoes": 0,
            "metodos": 0,
            "itens_funcoes_metodos": [],
            "itens_classes": [],
            "imports": 0,
        }

    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        # fallback mínimo se o arquivo estiver com sintaxe quebrada
        return {
            "classes": contar_classes_py(path),
            "funcoes": 0,
            "metodos": 0,
            "itens_funcoes_metodos": [],
            "itens_classes": [],
            "imports": 0,
        }

    classes = 0
    funcoes = 0
    metodos = 0
    itens_funcoes_metodos: List[Dict[str, Any]] = []
    itens_classes: List[Dict[str, Any]] = []

    def visitar(no: ast.AST, dentro_de_classe: bool = False, pilha_classes: Optional[List[str]] = None) -> None:
        nonlocal classes, funcoes, metodos

        if pilha_classes is None:
            pilha_classes = []

        if isinstance(no, ast.ClassDef):
            classes += 1
            nome_classe = ".".join(pilha_classes + [no.name]) if pilha_classes else no.name
            itens_classes.append({
                "nome": nome_classe,
                "linhas": span_linhas_no(no),
            })
            for filho in no.body:
                visitar(filho, dentro_de_classe=True, pilha_classes=pilha_classes + [no.name])
            return

        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if dentro_de_classe:
                metodos += 1
                nome = ".".join(pilha_classes + [no.name]) if pilha_classes else no.name
                tipo = "metodo"
            else:
                funcoes += 1
                nome = no.name
                tipo = "funcao"

            itens_funcoes_metodos.append({
                "nome": nome,
                "tipo": tipo,
                "linhas": span_linhas_no(no),
            })

        for filho in ast.iter_child_nodes(no):
            visitar(filho, dentro_de_classe=dentro_de_classe, pilha_classes=pilha_classes)

    visitar(arvore)

    return {
        "classes": classes,
        "funcoes": funcoes,
        "metodos": metodos,
        "itens_funcoes_metodos": itens_funcoes_metodos,
        "itens_classes": itens_classes,
        "imports": contar_imports_no_arquivo_py(codigo),
    }


def contar_classes_py(path: Path) -> int:
    n = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if CLASS_RE.match(line):
                    n += 1
    except OSError:
        return 0
    return n


def deve_ignorar(p: Path, relatorios_dir: Path) -> bool:
    parts = set(p.parts)
    if any(x in parts for x in IGNORAR_PASTAS):
        return True
    if p.is_relative_to(relatorios_dir):
        return True
    if p.suffix.lower() in IGNORAR_EXTENSOES:
        return True
    return False


def construir_mapa_modulos_py(repo_root: Path, relatorios_dir: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Retorna:
      - modulo -> caminho relativo do arquivo
      - caminho relativo -> modulo
    Ex.: Codigo/Utils/a.py -> Codigo.Utils.a
    """
    modulo_para_arquivo: Dict[str, str] = {}
    arquivo_para_modulo: Dict[str, str] = {}

    for p in repo_root.rglob("*.py"):
        if deve_ignorar(p, relatorios_dir):
            continue
        if not p.is_file():
            continue

        rel = str(p.relative_to(repo_root)).replace("\\", "/")
        partes = list(p.relative_to(repo_root).with_suffix("").parts)

        if partes and partes[-1] == "__init__":
            partes = partes[:-1]

        if not partes:
            continue

        modulo = ".".join(partes)
        modulo_para_arquivo[modulo] = rel
        arquivo_para_modulo[rel] = modulo

    return modulo_para_arquivo, arquivo_para_modulo


def resolver_import_local(modulo_atual: str, importado: Optional[str], nivel: int) -> Optional[str]:
    """
    Resolve imports relativos.
    """
    if nivel <= 0:
        return importado

    partes = modulo_atual.split(".")
    if not partes:
        return importado

    base = partes[:-nivel] if nivel <= len(partes) else []

    if importado:
        final = base + importado.split(".")
    else:
        final = base

    final = [p for p in final if p]
    if not final:
        return None
    return ".".join(final)


def coletar_imports_internos_py(
    path: Path,
    repo_root: Path,
    relatorios_dir: Path,
    modulo_para_arquivo: Dict[str, str],
    arquivo_para_modulo: Dict[str, str],
) -> List[str]:
    try:
        codigo = path.read_text(encoding="utf-8", errors="ignore")
        arvore = ast.parse(codigo)
    except Exception:
        return []

    rel = str(path.relative_to(repo_root)).replace("\\", "/")
    modulo_atual = arquivo_para_modulo.get(rel, "")

    encontrados: set[str] = set()

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                nome = alias.name
                partes = nome.split(".")
                for i in range(len(partes), 0, -1):
                    candidato = ".".join(partes[:i])
                    if candidato in modulo_para_arquivo:
                        encontrados.add(modulo_para_arquivo[candidato])
                        break

        elif isinstance(no, ast.ImportFrom):
            base = resolver_import_local(modulo_atual, no.module, no.level)
            if base:
                partes = base.split(".")
                for i in range(len(partes), 0, -1):
                    candidato = ".".join(partes[:i])
                    if candidato in modulo_para_arquivo:
                        encontrados.add(modulo_para_arquivo[candidato])
                        break

            for alias in no.names:
                if alias.name == "*":
                    continue
                if base:
                    candidato = f"{base}.{alias.name}"
                else:
                    candidato = resolver_import_local(modulo_atual, alias.name, no.level) or alias.name

                if candidato in modulo_para_arquivo:
                    encontrados.add(modulo_para_arquivo[candidato])

    encontrados.discard(rel)
    return sorted(encontrados)


def calcular_numero_relatorio(relatorios_dir: Path) -> int:
    if not relatorios_dir.exists():
        return 1
    return len(list(relatorios_dir.glob("*.json"))) + 1


def tentar_contar_commits(repo_root: Path) -> Optional[int]:
    """
    Bônus: conta commits do repo.
    Não quebra se:
      - não for repo git,
      - git não estiver instalado,
      - comando falhar.
    """
    try:
        if not (repo_root / ".git").exists():
            return None
        proc = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        out = (proc.stdout or "").strip()
        if out.isdigit():
            return int(out)
        return None
    except Exception:
        return None




def coletar_metricas_pasta_importante(
    pasta_base: Path,
    relatorios_dir: Path,
) -> Dict[str, Any]:
    if not pasta_base.exists() or not pasta_base.is_dir():
        return {
            "existe": False,
            "arquivos": 0,
            "subpastas": 0,
            "tamanho_bytes": 0,
            "linhas_gerais": 0,
            "linhas_por_extensao": {},
        }

    total_files = 0
    total_dirs = 0
    total_size = 0
    total_linhas = 0
    linhas_por_ext: Counter[str] = Counter()

    for p in pasta_base.rglob("*"):
        try:
            if deve_ignorar(p, relatorios_dir):
                continue

            if p.is_dir():
                total_dirs += 1
                continue

            if not p.is_file():
                continue

            total_files += 1
            total_size += p.stat().st_size

            ext = p.suffix.lower() if p.suffix else "(sem_ext)"
            if ext in EXTENSOES_TEXTO_INTERESSE or ext == "(sem_ext)":
                linhas = contar_linhas_arquivo(p)
                if linhas > 0:
                    total_linhas += linhas
                    linhas_por_ext[ext] += linhas

        except OSError:
            continue

    return {
        "existe": True,
        "arquivos": total_files,
        "subpastas": total_dirs,
        "tamanho_bytes": total_size,
        "linhas_gerais": total_linhas,
        "linhas_por_extensao": dict(linhas_por_ext),
    }


def coletar_rank_pastas_importantes(repo_root: Path, relatorios_dir: Path) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []

    for caminho_relativo, nome_exibicao in PASTAS_IMPORTANTES_RANK:
        pasta = repo_root / caminho_relativo
        metricas = coletar_metricas_pasta_importante(pasta, relatorios_dir)
        linhas_por_ext = metricas.get("linhas_por_extensao", {}) or {}

        linhas_py = int(linhas_por_ext.get(".py", 0))
        linhas_json = int(linhas_por_ext.get(".json", 0))
        linhas_toml = int(linhas_por_ext.get(".toml", 0))
        linhas_gerais = int(metricas.get("linhas_gerais", 0))
        outras_linhas = max(0, linhas_gerais - linhas_py - linhas_json - linhas_toml)

        itens.append({
            "pasta": nome_exibicao,
            "caminho": caminho_relativo.replace("\\", "/"),
            "existe": bool(metricas.get("existe", False)),
            "arquivos": int(metricas.get("arquivos", 0)),
            "subpastas": int(metricas.get("subpastas", 0)),
            "tamanho_bytes": int(metricas.get("tamanho_bytes", 0)),
            "linhas_gerais": linhas_gerais,
            "linhas_py": linhas_py,
            "linhas_json": linhas_json,
            "linhas_toml": linhas_toml,
            "outras_linhas": outras_linhas,
        })

    itens.sort(key=lambda x: int(x["linhas_gerais"]), reverse=True)
    for i, item in enumerate(itens, start=1):
        item["rank"] = i

    return itens


def coletar_metricas(repo_root: Path, relatorios_dir: Path) -> Dict[str, Any]:
    total_size = 0
    total_files = 0
    total_dirs = 0

    ext_count: Counter[str] = Counter()
    ext_size: Dict[str, int] = defaultdict(int)

    py_files = 0
    py_lines = 0
    py_classes = 0
    py_funcoes = 0
    py_metodos = 0

    linhas_por_ext: Counter[str] = Counter()
    total_linhas_geral = 0

    # Top lists (tudo em LINHAS, conforme pedido)
    maiores_py_por_linhas: List[Dict[str, Any]] = []
    maiores_arquivos_por_linhas: List[Dict[str, Any]] = []
    maiores_json_por_linhas: List[Dict[str, Any]] = []
    maiores_funcoes_metodos: List[Dict[str, Any]] = []
    maiores_classes_py: List[Dict[str, Any]] = []
    py_import_stmt_por_arquivo: List[Dict[str, Any]] = []

    maiores_geral_por_tamanho: List[Dict[str, Any]] = []

    # Import interno (opcional manter para estatística geral do python — mas não vai pro markdown)
    modulo_para_arquivo, arquivo_para_modulo = construir_mapa_modulos_py(repo_root, relatorios_dir)
    importado_por_count: Counter[str] = Counter()

    for p in repo_root.rglob("*"):
        try:
            if deve_ignorar(p, relatorios_dir):
                continue

            if p.is_dir():
                total_dirs += 1
                continue

            if not p.is_file():
                continue

            total_files += 1
            size = p.stat().st_size
            total_size += size

            ext = p.suffix.lower() if p.suffix else "(sem_ext)"
            ext_count[ext] += 1
            ext_size[ext] += size

            rel = str(p.relative_to(repo_root)).replace("\\", "/")

            maiores_geral_por_tamanho.append({
                "arquivo": rel,
                "ext": ext,
                "tamanho_bytes": size,
            })

            # Linhas por extensão textual
            linhas = 0
            if ext in EXTENSOES_TEXTO_INTERESSE or ext == "(sem_ext)":
                linhas = contar_linhas_arquivo(p)
                if linhas > 0:
                    linhas_por_ext[ext] += linhas
                    total_linhas_geral += linhas
                    maiores_arquivos_por_linhas.append({
                        "arquivo": rel,
                        "ext": ext,
                        "linhas": linhas,
                    })
                    if ext == ".json":
                        maiores_json_por_linhas.append({
                            "arquivo": rel,
                            "linhas": linhas,
                        })

            if ext == ".py":
                py_files += 1

                if linhas == 0:
                    linhas = contar_linhas_arquivo(p)
                    if linhas > 0:
                        linhas_por_ext[ext] += linhas
                        total_linhas_geral += linhas

                py_lines += linhas

                analise_py = analisar_python_ast(p)
                py_classes += int(analise_py["classes"])
                py_funcoes += int(analise_py["funcoes"])
                py_metodos += int(analise_py["metodos"])

                maiores_py_por_linhas.append({
                    "arquivo": rel,
                    "linhas": int(linhas),
                    "tamanho_bytes": int(size),
                    "tamanho_kib": round(bytes_para_kib(int(size)), 2),
                })

                py_import_stmt_por_arquivo.append({
                    "arquivo": rel,
                    "imports": int(analise_py.get("imports", 0)),
                    "linhas": int(linhas),
                })

                for item in analise_py.get("itens_funcoes_metodos", []):
                    maiores_funcoes_metodos.append({
                        "arquivo": rel,
                        "nome": str(item["nome"]),
                        "tipo": str(item["tipo"]),
                        "linhas": int(item["linhas"]),
                    })

                for item in analise_py.get("itens_classes", []):
                    maiores_classes_py.append({
                        "arquivo": rel,
                        "nome": str(item["nome"]),
                        "linhas": int(item["linhas"]),
                    })

                # Mantém contagem de “importado por” (não entra no relatório final)
                for arq_importado in coletar_imports_internos_py(
                    p, repo_root, relatorios_dir, modulo_para_arquivo, arquivo_para_modulo
                ):
                    importado_por_count[arq_importado] += 1

        except OSError:
            continue

    # ===== ordenar e cortar tops =====

    # Top 50 .py por linhas
    maiores_py_por_linhas.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top50_maiores_py = maiores_py_por_linhas[:50]

    # Top 15 maiores funções/métodos por linhas
    maiores_funcoes_metodos.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top15_funcoes_metodos = maiores_funcoes_metodos[:15]

    # Top 15 maiores classes por linhas
    maiores_classes_py.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top15_classes_py = maiores_classes_py[:15]

    # Top 10 json por linhas
    maiores_json_por_linhas.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top10_json_por_linhas = maiores_json_por_linhas[:10]

    # Top 10 arquivos por linhas (geral)
    maiores_arquivos_por_linhas.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top10_arquivos_por_linhas = maiores_arquivos_por_linhas[:10]

    # Top 10 maiores arquivos por tamanho (geral)
    maiores_geral_por_tamanho.sort(key=lambda x: int(x["tamanho_bytes"]), reverse=True)
    top10_maiores_geral = maiores_geral_por_tamanho[:10]
    for it in top10_maiores_geral:
        it["tamanho_kib"] = round(bytes_para_kib(int(it["tamanho_bytes"])), 2)

    # Top 5 arquivos com mais IMPORT statements
    py_import_stmt_por_arquivo.sort(key=lambda x: int(x["imports"]), reverse=True)
    top5_py_mais_imports = py_import_stmt_por_arquivo[:5]

    linhas_por_ext_lista = [
        {"ext": ext, "linhas": linhas}
        for ext, linhas in sorted(linhas_por_ext.items(), key=lambda kv: kv[1], reverse=True)
        if linhas > 0
    ]

    media_linhas_por_py = (py_lines / py_files) if py_files else 0.0

    commits = tentar_contar_commits(repo_root)
    rank_pastas_importantes = coletar_rank_pastas_importantes(repo_root, relatorios_dir)

    return {
        "resumo": {
            "pastas": total_dirs,
            "arquivos": total_files,
            "tamanho_bytes": total_size,
            "tamanho_gib": round(bytes_para_gib(total_size), 6),
            "linhas_totais_geral": total_linhas_geral,
            "commits": commits,
        },
        "python": {
            "py_arquivos": py_files,
            "linhas_totais": py_lines,
            "classes_encontradas": py_classes,
            "funcoes_encontradas": py_funcoes,
            "metodos_encontrados": py_metodos,
            "total_funcoes_e_metodos": py_funcoes + py_metodos,
            "media_linhas_por_arquivo": round(media_linhas_por_py, 2),

            "top50_maiores_py_por_linhas": top50_maiores_py,
            "top40_maiores_py_por_linhas": top50_maiores_py,
            "top15_maiores_funcoes_metodos": top15_funcoes_metodos,
            "top15_maiores_classes": top15_classes_py,
            "top5_py_com_mais_imports": top5_py_mais_imports,
        },
        "pastas_importantes": {
            "observacao": "Rank recursivo por linhas das 10 pastas principais, incluindo subpastas e arquivos internos.",
            "itens": rank_pastas_importantes,
        },
        "linhas_por_extensao": {
            "itens": linhas_por_ext_lista,
        },
        "arquivos": {
            "top10_maiores_geral": top10_maiores_geral,
            "top10_json_por_linhas": top10_json_por_linhas,
            "top10_maiores_por_linhas": top10_arquivos_por_linhas,
        },
        "extensoes": {
            "contagem": dict(ext_count),
            "tamanho_bytes": dict(ext_size),
            # mantemos “top por tamanho” porque isso não é o trecho removido do diff
            "top_por_tamanho": [
                {
                    "ext": ext,
                    "tamanho_bytes": sz,
                    "tamanho_gib": round(bytes_para_gib(sz), 6),
                    "arquivos": ext_count[ext],
                }
                for ext, sz in sorted(ext_size.items(), key=lambda kv: kv[1], reverse=True)[:20]
            ],
        },
    }


def ler_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def encontrar_ultimo_relatorio(relatorios_dir: Path, ignorar_nome: Optional[str] = None) -> Optional[Path]:
    if not relatorios_dir.exists():
        return None

    candidatos = []
    for p in relatorios_dir.glob("*.json"):
        if ignorar_nome and p.name == ignorar_nome:
            continue
        candidatos.append(p)

    if not candidatos:
        return None

    candidatos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidatos[0]


def get_num(d: Dict[str, Any], path: Tuple[str, ...]) -> Optional[int]:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    if isinstance(cur, (int, float)):
        return int(cur)
    return None


def gerar_diff(anterior: Optional[Dict[str, Any]], atual: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not anterior:
        return None

    caminhos = {
        "pastas": ("resumo", "pastas"),
        "arquivos": ("resumo", "arquivos"),
        "tamanho_bytes": ("resumo", "tamanho_bytes"),
        "linhas_totais_geral": ("resumo", "linhas_totais_geral"),
        "py_arquivos": ("python", "py_arquivos"),
        "linhas_totais": ("python", "linhas_totais"),
        "classes_encontradas": ("python", "classes_encontradas"),
        "funcoes_encontradas": ("python", "funcoes_encontradas"),
        "metodos_encontrados": ("python", "metodos_encontrados"),
    }

    diffs: Dict[str, Any] = {}
    for nome, path in caminhos.items():
        a = get_num(anterior, path)
        b = get_num(atual, path)
        if a is None or b is None:
            continue
        diffs[nome] = {"anterior": a, "atual": b, "delta": b - a}

    return diffs


def markdown_top_extensoes(atual: Dict[str, Any], limite: int = 12) -> str:
    itens = (atual.get("extensoes", {}).get("top_por_tamanho") or [])[:limite]
    linhas = [
        "| Ext | Tamanho (GiB) | Arquivos |",
        "|---:|---:|---:|",
    ]
    for it in itens:
        ext = it["ext"]
        tamanho = f"{bytes_para_gib(int(it['tamanho_bytes'])):.3f}"
        arqs = fmt_int(int(it["arquivos"]))
        linhas.append(f"| `{ext}` | {tamanho} | {arqs} |")
    return "\n".join(linhas)




def markdown_rank_pastas_importantes(atual: Dict[str, Any]) -> str:
    itens = (atual.get("pastas_importantes", {}).get("itens") or [])[:10]
    if not itens:
        return "_Nenhuma pasta importante encontrada para montar o rank._"

    linhas = [
        "| Rank | Pasta | Caminho | Subpastas | Arquivos | Linhas gerais | `.py` | `.json` | `.toml` | Outras |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for it in itens:
        linhas.append(
            f"| {fmt_int(int(it['rank']))} | `{it['pasta']}` | `{it['caminho']}` | "
            f"{fmt_int(int(it['subpastas']))} | {fmt_int(int(it['arquivos']))} | "
            f"{fmt_int(int(it['linhas_gerais']))} | {fmt_int(int(it['linhas_py']))} | "
            f"{fmt_int(int(it['linhas_json']))} | {fmt_int(int(it['linhas_toml']))} | "
            f"{fmt_int(int(it['outras_linhas']))} |"
        )
    return "\n".join(linhas)


def markdown_top50_py_por_linhas(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top50_maiores_py_por_linhas") or atual.get("python", {}).get("top40_maiores_py_por_linhas") or [])[:50]
    if not itens:
        return "_Nenhum arquivo `.py` encontrado._"

    linhas = [
        "| Arquivo | Linhas | Tamanho (KiB) |",
        "|---|---:|---:|",
    ]
    for it in itens:
        arq = str(it["arquivo"])
        linhas_count = int(it.get("linhas", 0))
        kib = float(it.get("tamanho_kib", round(bytes_para_kib(int(it["tamanho_bytes"])), 2)))
        linhas.append(f"| `{arq}` | {fmt_int(linhas_count)} | {kib:.2f} |")
    return "\n".join(linhas)


def markdown_top_funcoes_metodos(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top15_maiores_funcoes_metodos") or [])[:15]
    if not itens:
        return "_Nenhuma função ou método Python encontrado._"

    linhas = [
        "| Arquivo | Nome | Tipo | Linhas |",
        "|---|---|---:|---:|",
    ]
    for it in itens:
        linhas.append(
            f"| `{it['arquivo']}` | `{it['nome']}` | {it['tipo']} | {fmt_int(int(it['linhas']))} |"
        )
    return "\n".join(linhas)


def markdown_top_classes(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top15_maiores_classes") or [])[:15]
    if not itens:
        return "_Nenhuma classe Python encontrada._"

    linhas = [
        "| Arquivo | Classe | Linhas |",
        "|---|---|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | `{it['nome']}` | {fmt_int(int(it['linhas']))} |")
    return "\n".join(linhas)


def markdown_top_json_por_linhas(atual: Dict[str, Any]) -> str:
    itens = (atual.get("arquivos", {}).get("top10_json_por_linhas") or [])[:10]
    if not itens:
        return "_Nenhum arquivo `.json` encontrado._"

    linhas = [
        "| Arquivo | Linhas |",
        "|---|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | {fmt_int(int(it['linhas']))} |")
    return "\n".join(linhas)


def markdown_top_arquivos_por_linhas(atual: Dict[str, Any]) -> str:
    itens = (atual.get("arquivos", {}).get("top10_maiores_por_linhas") or [])[:10]
    if not itens:
        return "_Nenhum arquivo textual encontrado._"

    linhas = [
        "| Arquivo | Ext | Linhas |",
        "|---|---:|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | `{it['ext']}` | {fmt_int(int(it['linhas']))} |")
    return "\n".join(linhas)


def markdown_top_maiores_por_tamanho(atual: Dict[str, Any]) -> str:
    itens = (atual.get("arquivos", {}).get("top10_maiores_geral") or [])[:10]
    if not itens:
        return "_Nenhum arquivo encontrado._"

    linhas = [
        "| Arquivo | Ext | Tamanho (KiB) |",
        "|---|---:|---:|",
    ]
    for it in itens:
        linhas.append(
            f"| `{it['arquivo']}` | `{it['ext']}` | {float(it.get('tamanho_kib', 0.0)):.2f} |"
        )
    return "\n".join(linhas)


def markdown_top_py_com_mais_imports(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top5_py_com_mais_imports") or [])[:5]
    if not itens:
        return "_Nenhum arquivo `.py` encontrado._"

    linhas = [
        "| Arquivo | Imports | Linhas |",
        "|---|---:|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | {fmt_int(int(it['imports']))} | {fmt_int(int(it['linhas']))} |")
    return "\n".join(linhas)


def markdown_linhas_por_extensao(atual: Dict[str, Any]) -> str:
    itens = atual.get("linhas_por_extensao", {}).get("itens", []) or []
    if not itens:
        return "_Nenhuma linha contabilizada por extensão._"

    linhas = [
        "| Ext | Linhas |",
        "|---:|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['ext']}` | {fmt_int(int(it['linhas']))} |")
    return "\n".join(linhas)


def markdown_diff(diff: Optional[Dict[str, Any]]) -> str:
    if not diff:
        return "_Sem relatório anterior para comparar._"

    linhas = []
    chaves = [
        "pastas",
        "arquivos",
        "tamanho_bytes",
        "linhas_totais_geral",
        "py_arquivos",
        "linhas_totais",
        "classes_encontradas",
        "funcoes_encontradas",
        "metodos_encontrados",
    ]
    linhas.append("| Métrica | Anterior | Atual | Δ |")
    linhas.append("|---|---:|---:|---:|")

    for k in chaves:
        if k not in diff:
            continue
        a = int(diff[k]["anterior"])
        b = int(diff[k]["atual"])
        d = int(diff[k]["delta"])

        if k == "tamanho_bytes":
            a_s = f"{bytes_para_gib(a):.3f} GiB"
            b_s = f"{bytes_para_gib(b):.3f} GiB"
            d_s = f"{bytes_para_gib(d):.3f} GiB"
        else:
            a_s = fmt_int(a)
            b_s = fmt_int(b)
            d_s = fmt_int(d)

        linhas.append(f"| {k} | {a_s} | {b_s} | {d_s} |")

    # REMOVIDO: “Maiores mudanças por extensão (top 12 por |Δ tamanho|)”
    return "\n".join(linhas)


def gerar_markdown(atual: Dict[str, Any], diff: Optional[Dict[str, Any]]) -> str:
    resumo = atual["resumo"]
    py = atual["python"]
    meta = atual.get("meta", {}) or {}

    criado_em = meta.get("criado_em", "")
    nome_repo = meta.get("repo", "")
    numero_relatorio = meta.get("numero_relatorio")

    md: List[str] = []
    md.append("# Registro\n")
    if numero_relatorio is not None:
        md.append(f"**Relatório:** #{numero_relatorio}  ")
    if nome_repo:
        md.append(f"**Repo:** `{nome_repo}`  ")
    if criado_em:
        md.append(f"**Gerado em:** {criado_em}  \n")

    md.append("## Visão geral\n")
    md.append(f"- **Pastas:** {fmt_int(int(resumo['pastas']))}")
    md.append(f"- **Arquivos:** {fmt_int(int(resumo['arquivos']))}")
    md.append(f"- **Tamanho total:** {fmt_bytes(int(resumo['tamanho_bytes']))}")
    md.append(f"- **Linhas totais gerais:** {fmt_int(int(resumo['linhas_totais_geral']))}")
    if resumo.get("commits") is not None:
        md.append(f"- **Commits (repo):** {fmt_int(int(resumo['commits']))}")
    md.append("")

    md.append("## Python\n")
    md.append(f"- **Arquivos `.py`:** {fmt_int(int(py['py_arquivos']))}")
    md.append(f"- **Linhas totais:** {fmt_int(int(py['linhas_totais']))}")
    md.append(f"- **Classes encontradas:** {fmt_int(int(py['classes_encontradas']))}")
    md.append(f"- **Funções encontradas:** {fmt_int(int(py['funcoes_encontradas']))}")
    md.append(f"- **Métodos encontrados:** {fmt_int(int(py['metodos_encontrados']))}")
    md.append(f"- **Total funções + métodos:** {fmt_int(int(py['total_funcoes_e_metodos']))}")
    md.append(f"- **Média de linhas por arquivo `.py`:** {py['media_linhas_por_arquivo']:.2f}\n")

    md.append("### Rank das 10 pastas mais importantes por linhas\n")
    md.append("Contagem recursiva: cada pasta inclui todas as subpastas e todos os arquivos internos.\n")
    md.append(markdown_rank_pastas_importantes(atual))
    md.append("")

    md.append("### Top 50 maiores arquivos `.py` por linhas\n")
    md.append(markdown_top50_py_por_linhas(atual))
    md.append("")

    md.append("### Top 15 maiores funções e métodos (linhas)\n")
    md.append(markdown_top_funcoes_metodos(atual))
    md.append("")

    md.append("### Top 15 maiores classes (linhas)\n")
    md.append(markdown_top_classes(atual))
    md.append("")

    md.append("### Top 5 arquivos `.py` com mais imports\n")
    md.append(markdown_top_py_com_mais_imports(atual))
    md.append("")

    md.append("## Arquivos por linhas\n")
    md.append("### Top 10 arquivos `.json` por linhas\n")
    md.append(markdown_top_json_por_linhas(atual))
    md.append("")

    md.append("### Top 10 maiores arquivos por linhas\n")
    md.append(markdown_top_arquivos_por_linhas(atual))
    md.append("")

    md.append("## Arquivos por tamanho\n")
    md.append("### Top 10 maiores arquivos (tamanho)\n")
    md.append(markdown_top_maiores_por_tamanho(atual))
    md.append("")

    md.append("## Linhas por extensão\n")
    md.append(markdown_linhas_por_extensao(atual))
    md.append("")

    md.append("## Top extensões por tamanho\n")
    md.append(markdown_top_extensoes(atual, limite=12))
    md.append("\n## Diferenças vs último relatório\n")
    md.append(markdown_diff(diff))

    return "\n".join(md).strip() + "\n"


def main() -> None:
    # Script fica em: repo_root/Outros/gerar_relatorio_repo.py
    script_path = Path(__file__).resolve()
    outros_dir = script_path.parent
    repo_root = outros_dir.parent

    # JSONs ficam em: repo_root/Outros/Relatorios
    relatorios_dir = outros_dir / "Relatorios"
    relatorios_dir.mkdir(parents=True, exist_ok=True)

    # Markdown fica fora, na raiz: repo_root/Registro.md
    registro_md_path = repo_root / "Registro.md"

    numero_relatorio = calcular_numero_relatorio(relatorios_dir)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_name = f"{ts}.json"
    json_path = relatorios_dir / json_name

    anterior_path = encontrar_ultimo_relatorio(relatorios_dir)
    anterior = ler_json(anterior_path) if anterior_path else None

    atual = coletar_metricas(repo_root, relatorios_dir)
    atual["meta"] = {
        "numero_relatorio": numero_relatorio,
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "repo": repo_root.name,
        "arquivo": json_name,
        "base_dir": str(repo_root),
        "script": str(script_path.relative_to(repo_root)).replace("\\", "/"),
        "relatorios_dir": str(relatorios_dir.relative_to(repo_root)).replace("\\", "/"),
    }

    diff = gerar_diff(anterior, atual)
    if anterior_path:
        atual["meta"]["comparado_com"] = anterior_path.name
    if diff:
        atual["diff"] = diff

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)

    md = gerar_markdown(atual, diff)
    registro_md_path.write_text(md, encoding="utf-8")

    print("Relatório gerado:")
    print(f"- JSON: {json_path}")
    print(f"- Markdown: {registro_md_path}")


if __name__ == "__main__":
    main()