from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ============================================================
# CONFIGURAÇÃO MANUAL
# ============================================================
MODELO_RELATORIO = 8
AUTOR_RELATORIO = "Leon Cunha Alvaro Lopez Soto"
INCREMENTO_HORAS = 0.0
HORAS_PADRAO_SEM_HISTORICO = 313.0

CLASS_RE = re.compile(r"^\s*class\s+[A-Za-z_]\w*\s*(\(|:)")

IGNORAR_PASTAS = {
    ".git",
    "__pycache__",
    "Relatorios",
    "Relatorios atualizados",
}
IGNORAR_EXTENSOES = {".pyc"}
IGNORAR_ARQUIVOS_EXATOS = {"Registro.md"}

EXTENSOES_TEXTO_INTERESSE = {
    ".py", ".json", ".java", ".js", ".ts", ".jsx", ".tsx", ".css", ".html", ".htm",
    ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".csv", ".xml", ".sql",
    ".bat", ".sh", ".ps1", ".properties", ".gradle", ".kt", ".kts", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".lua", ".rs", ".go", ".php", ".rb", ".vue", ".vhd", ".vhdl",
}

# 15 itens fixos conforme pedido.
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
    ("SimuladorServerJogo/Logica", "SimuladorServerJogo/Logica"),
    ("SimuladorServerJogo/Gerais", "SimuladorServerJogo/Gerais"),
    ("SimuladorServerJogo/Mundo", "SimuladorServerJogo/Mundo"),
    ("SimuladorServerJogo/Batalha", "SimuladorServerJogo/Batalha"),
    ("Outros", "Outros"),
    ("Dados", "Dados"),
]


# ============================================================
# FORMATAÇÃO
# ============================================================
def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_num(n: float, casas: int = 2) -> str:
    s = f"{n:.{casas}f}"
    return s.replace(",", ".")


def bytes_para_kb(num_bytes: int) -> float:
    return num_bytes / 1024.0


def bytes_para_mb(num_bytes: int) -> float:
    return num_bytes / (1024.0 ** 2)


def bytes_para_gb(num_bytes: int) -> float:
    return num_bytes / (1024.0 ** 3)


def fmt_tamanho_kb(num_bytes: int) -> str:
    return f"{fmt_num(bytes_para_kb(num_bytes), 2)} KB"


def fmt_tamanho_gb_com_bytes(num_bytes: int) -> str:
    return f"{fmt_num(bytes_para_gb(num_bytes), 3)} GB ({fmt_int(num_bytes)} bytes)"


# ============================================================
# DATAS / GIT
# ============================================================
def parse_datetime_seguro(valor: str) -> Optional[datetime]:
    if not valor or not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except Exception:
        return None


def obter_data_referencia() -> datetime:
    valor = os.environ.get("RELATORIO_DATA_REFERENCIA_ISO", "").strip()
    dt = parse_datetime_seguro(valor)
    if dt is not None:
        return dt
    return datetime.now().astimezone()


def rodar_git(repo_root: Path, args: Sequence[str]) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip()


def tentar_contar_commits(repo_root: Path, data_referencia: Optional[datetime] = None) -> Optional[int]:
    if not (repo_root / ".git").exists():
        return None

    args: List[str] = ["rev-list", "--count"]
    if data_referencia is not None:
        args.append(f"--before={data_referencia.isoformat(sep=' ', timespec='seconds')}")
    args.append("HEAD")

    out = rodar_git(repo_root, args)
    if out and out.isdigit():
        return int(out)
    return None


def tentar_primeiro_commit_data(repo_root: Path) -> Optional[datetime]:
    if not (repo_root / ".git").exists():
        return None
    out = rodar_git(repo_root, ["log", "--reverse", "--format=%cI", "HEAD"])
    if not out:
        return None
    primeira_linha = out.splitlines()[0].strip()
    return parse_datetime_seguro(primeira_linha)


# ============================================================
# ARQUIVOS / PARSE
# ============================================================
def eh_arquivo_texto_por_extensao(ext: str) -> bool:
    return ext in EXTENSOES_TEXTO_INTERESSE


def ler_texto(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


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


def deve_ignorar(p: Path, repo_root: Path, relatorios_dir: Path) -> bool:
    parts = set(p.parts)
    if any(x in parts for x in IGNORAR_PASTAS):
        return True
    if p.is_relative_to(relatorios_dir):
        return True
    if p.suffix.lower() in IGNORAR_EXTENSOES:
        return True
    if p.name in IGNORAR_ARQUIVOS_EXATOS and p.parent == repo_root:
        return True
    return False


def construir_mapa_modulos_py(repo_root: Path, relatorios_dir: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    modulo_para_arquivo: Dict[str, str] = {}
    arquivo_para_modulo: Dict[str, str] = {}

    for p in repo_root.rglob("*.py"):
        if deve_ignorar(p, repo_root, relatorios_dir):
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
    if nivel <= 0:
        return importado

    partes = modulo_atual.split(".") if modulo_atual else []
    base = partes[:-nivel] if nivel <= len(partes) else []

    if importado:
        final = base + importado.split(".")
    else:
        final = base

    final = [p for p in final if p]
    if not final:
        return None
    return ".".join(final)


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


def analisar_python_ast(
    path: Path,
    repo_root: Path,
    relatorios_dir: Path,
    modulo_para_arquivo: Dict[str, str],
    arquivo_para_modulo: Dict[str, str],
) -> Dict[str, Any]:
    codigo = ler_texto(path)
    if not codigo:
        return {
            "classes": 0,
            "funcoes": 0,
            "metodos": 0,
            "itens_funcoes_metodos": [],
            "itens_classes": [],
            "imports_total": 0,
            "bibliotecas_roots": set(),
            "imports_internos": [],
        }

    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        return {
            "classes": contar_classes_py(path),
            "funcoes": 0,
            "metodos": 0,
            "itens_funcoes_metodos": [],
            "itens_classes": [],
            "imports_total": 0,
            "bibliotecas_roots": set(),
            "imports_internos": [],
        }

    rel = str(path.relative_to(repo_root)).replace("\\", "/")
    modulo_atual = arquivo_para_modulo.get(rel, "")

    classes = 0
    funcoes = 0
    metodos = 0
    itens_funcoes_metodos: List[Dict[str, Any]] = []
    itens_classes: List[Dict[str, Any]] = []
    bibliotecas_roots: set[str] = set()
    imports_internos: set[str] = set()
    imports_total = 0

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

    def registrar_modulo_e_interno(nome_modulo: Optional[str]) -> None:
        if not nome_modulo:
            return

        root = nome_modulo.split(".")[0].strip()
        if root:
            bibliotecas_roots.add(root)

        partes = nome_modulo.split(".")
        for i in range(len(partes), 0, -1):
            candidato = ".".join(partes[:i])
            arq = modulo_para_arquivo.get(candidato)
            if arq:
                imports_internos.add(arq)
                break

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            imports_total += 1
            for alias in no.names:
                registrar_modulo_e_interno(alias.name)

        elif isinstance(no, ast.ImportFrom):
            imports_total += 1
            base = resolver_import_local(modulo_atual, no.module, no.level)
            registrar_modulo_e_interno(base)

            for alias in no.names:
                if alias.name == "*":
                    continue
                candidato: Optional[str]
                if base:
                    candidato = f"{base}.{alias.name}"
                else:
                    candidato = resolver_import_local(modulo_atual, alias.name, no.level) or alias.name
                registrar_modulo_e_interno(candidato)

    imports_internos.discard(rel)
    return {
        "classes": classes,
        "funcoes": funcoes,
        "metodos": metodos,
        "itens_funcoes_metodos": itens_funcoes_metodos,
        "itens_classes": itens_classes,
        "imports_total": imports_total,
        "bibliotecas_roots": bibliotecas_roots,
        "imports_internos": sorted(imports_internos),
    }


# ============================================================
# RELATÓRIOS ANTERIORES / HISTÓRICO
# ============================================================
def ler_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def obter_data_relatorio_de_dict(relatorio: Dict[str, Any], fallback: Optional[datetime] = None) -> Optional[datetime]:
    meta = relatorio.get("meta")
    if isinstance(meta, dict):
        for chave in ("data_referencia", "criado_em", "data_relatorio_original"):
            dt = parse_datetime_seguro(str(meta.get(chave, "")))
            if dt is not None:
                return dt
    return fallback


def obter_data_relatorio_de_arquivo(path: Path) -> datetime:
    data = ler_json(path)
    dt = obter_data_relatorio_de_dict(data or {}, None)
    if dt is not None:
        return dt

    try:
        return datetime.strptime(path.stem, "%Y-%m-%d_%H-%M-%S")
    except Exception:
        return datetime.fromtimestamp(path.stat().st_mtime)


def encontrar_ultimo_relatorio_anterior(relatorios_dir: Path, data_referencia: datetime) -> Optional[Path]:
    if not relatorios_dir.exists():
        return None

    candidatos: List[Tuple[datetime, Path]] = []
    for p in relatorios_dir.glob("*.json"):
        try:
            dt = obter_data_relatorio_de_arquivo(p)
            if dt <= data_referencia:
                candidatos.append((dt, p))
        except Exception:
            continue

    if not candidatos:
        return None

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1]


def extrair_primeiro_numero(relatorio: Dict[str, Any], caminhos: Iterable[Tuple[str, ...]]) -> Optional[float]:
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
    if not isinstance(relatorio, dict):
        return None
    return extrair_primeiro_numero(
        relatorio,
        [
            ("resumo", "horas_estimadas"),
            ("visao_geral", "horas_estimadas"),
            ("meta", "horas_estimadas"),
        ],
    )


def calcular_horas_estimadas(relatorios_dir: Path, data_referencia: datetime) -> Tuple[float, Optional[str], float]:
    relatorio_anterior_path = encontrar_ultimo_relatorio_anterior(relatorios_dir, data_referencia)
    relatorio_anterior = ler_json(relatorio_anterior_path) if relatorio_anterior_path else None
    horas_base = extrair_horas_estimadas_relatorio(relatorio_anterior)
    if horas_base is None:
        horas_base = HORAS_PADRAO_SEM_HISTORICO
    horas_atual = max(0.0, horas_base + float(INCREMENTO_HORAS))
    return horas_atual, relatorio_anterior_path.name if relatorio_anterior_path else None, horas_base


def extrair_metricas_historicas(relatorio: Dict[str, Any]) -> Dict[str, Optional[float]]:
    return {
        "linhas_totais_geral": extrair_primeiro_numero(
            relatorio,
            [
                ("resumo", "linhas_totais_geral"),
                ("resumo", "linhas_totais"),
                ("visao_geral", "linhas_totais_geral"),
            ],
        ),
        "linhas_py": extrair_primeiro_numero(
            relatorio,
            [
                ("python", "linhas_totais"),
                ("python", "linhas_py"),
            ],
        ),
        "arquivos_py": extrair_primeiro_numero(
            relatorio,
            [
                ("python", "py_arquivos"),
                ("python", "arquivos_py"),
            ],
        ),
        "commits": extrair_primeiro_numero(
            relatorio,
            [
                ("resumo", "commits"),
                ("meta", "commits"),
            ],
        ),
    }


def coletar_historico_relatorios(
    relatorios_dir: Path,
    atual: Dict[str, Any],
    data_referencia: datetime,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    pontos: List[Dict[str, Any]] = []

    if relatorios_dir.exists():
        for p in relatorios_dir.glob("*.json"):
            relatorio = ler_json(p)
            if not relatorio:
                continue
            dt = obter_data_relatorio_de_dict(relatorio, None)
            if dt is None:
                try:
                    dt = datetime.strptime(p.stem, "%Y-%m-%d_%H-%M-%S")
                except Exception:
                    dt = datetime.fromtimestamp(p.stat().st_mtime)

            metricas = extrair_metricas_historicas(relatorio)
            commits = metricas["commits"]
            if commits is None:
                commits = tentar_contar_commits(repo_root, dt)

            pontos.append({
                "data": dt.isoformat(timespec="seconds"),
                "linhas_totais_geral": metricas["linhas_totais_geral"],
                "linhas_py": metricas["linhas_py"],
                "arquivos_py": metricas["arquivos_py"],
                "commits": commits,
            })

    pontos.append({
        "data": data_referencia.isoformat(timespec="seconds"),
        "linhas_totais_geral": atual.get("resumo", {}).get("linhas_totais_geral"),
        "linhas_py": atual.get("python", {}).get("linhas_totais"),
        "arquivos_py": atual.get("python", {}).get("py_arquivos"),
        "commits": atual.get("resumo", {}).get("commits"),
    })

    dedup: Dict[str, Dict[str, Any]] = {}
    for ponto in pontos:
        data = str(ponto.get("data", ""))
        if not data:
            continue
        dedup[data] = ponto

    pontos_finais = sorted(dedup.values(), key=lambda x: x["data"])
    return pontos_finais


# ============================================================
# GRÁFICOS
# ============================================================
def preparar_plot() -> Tuple[bool, Optional[Any], Optional[Any]]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return True, matplotlib, plt
    except Exception:
        return False, None, None


def salvar_grafico_barras(plt: Any, labels: List[str], valores: List[float], titulo: str, y_label: str, destino: Path) -> bool:
    if not labels or not valores:
        return False
    try:
        fig = plt.figure(figsize=(14, 7))
        ax = fig.add_subplot(111)
        ax.bar(range(len(labels)), valores)
        ax.set_title(titulo)
        ax.set_ylabel(y_label)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        destino.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destino, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception:
        return False


def salvar_grafico_pizza(plt: Any, labels: List[str], valores: List[float], titulo: str, destino: Path) -> bool:
    if not labels or not valores:
        return False
    total = sum(v for v in valores if v > 0)
    if total <= 0:
        return False
    try:
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111)
        ax.pie(valores, labels=labels, autopct=lambda pct: f"{pct:.1f}%" if pct >= 3 else "")
        ax.set_title(titulo)
        fig.tight_layout()
        destino.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destino, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception:
        return False


def salvar_grafico_linha(plt: Any, labels: List[str], valores: List[float], titulo: str, y_label: str, destino: Path) -> bool:
    if len(labels) < 1 or len(valores) < 1:
        return False
    try:
        fig = plt.figure(figsize=(14, 7))
        ax = fig.add_subplot(111)
        ax.plot(range(len(valores)), valores, marker="o")
        ax.set_title(titulo)
        ax.set_ylabel(y_label)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        destino.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destino, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception:
        return False


def labels_datas_historico(historico: List[Dict[str, Any]]) -> List[str]:
    labels: List[str] = []
    for ponto in historico:
        dt = parse_datetime_seguro(str(ponto.get("data", "")))
        if dt is None:
            labels.append(str(ponto.get("data", ""))[:10])
        else:
            labels.append(dt.strftime("%Y-%m-%d"))
    return labels


def gerar_graficos(
    atual: Dict[str, Any],
    historico: List[Dict[str, Any]],
    imagens_base_dir: Path,
    report_stem: str,
) -> Dict[str, str]:
    disponivel, _, plt = preparar_plot()
    if not disponivel or plt is None:
        return {}

    imagens_dir = imagens_base_dir / report_stem
    imagens_rel_root = f"Outros/Relatorios/Imagens/{report_stem}"
    imagens_rel_local = f"../Imagens/{report_stem}"

    graficos: Dict[str, str] = {}

    rank_itens = atual.get("pastas_importantes", {}).get("itens", []) or []
    labels_rank = [str(it.get("pasta", "")) for it in rank_itens[:15]]
    valores_rank = [float(it.get("linhas_gerais", 0)) for it in rank_itens[:15]]

    destino = imagens_dir / "rank_15_pastas_barras.png"
    if salvar_grafico_barras(plt, labels_rank, valores_rank, "Rank das 15 pastas mais relevantes por linhas", "Linhas", destino):
        graficos["rank_15_pastas_barras"] = f"{imagens_rel_local}/{destino.name}"
        graficos["rank_15_pastas_barras_root"] = f"{imagens_rel_root}/{destino.name}"

    destino = imagens_dir / "rank_15_pastas_pizza.png"
    if salvar_grafico_pizza(plt, labels_rank, valores_rank, "Fatia das 15 pastas mais relevantes por linhas", destino):
        graficos["rank_15_pastas_pizza"] = f"{imagens_rel_local}/{destino.name}"
        graficos["rank_15_pastas_pizza_root"] = f"{imagens_rel_root}/{destino.name}"

    linhas_ext = atual.get("linhas_por_extensao", {}).get("itens", []) or []
    linhas_ext_plot = list(linhas_ext[:10])
    if len(linhas_ext) > 10:
        resto = sum(int(it.get("linhas", 0)) for it in linhas_ext[10:])
        if resto > 0:
            linhas_ext_plot.append({"ext": "Outras", "linhas": resto})

    labels_ext = [str(it.get("ext", "")) for it in linhas_ext_plot]
    valores_ext = [float(it.get("linhas", 0)) for it in linhas_ext_plot]
    destino = imagens_dir / "linhas_por_extensao_pizza.png"
    if salvar_grafico_pizza(plt, labels_ext, valores_ext, "Linhas por extensão", destino):
        graficos["linhas_por_extensao_pizza"] = f"{imagens_rel_local}/{destino.name}"
        graficos["linhas_por_extensao_pizza_root"] = f"{imagens_rel_root}/{destino.name}"

    labels_hist = labels_datas_historico(historico)
    series = [
        ("linhas_totais_geral", "Crescimento de linhas gerais", "Linhas", "crescimento_linhas_totais.png"),
        ("linhas_py", "Crescimento de linhas .py", "Linhas .py", "crescimento_linhas_py.png"),
        ("arquivos_py", "Crescimento de arquivos .py", "Arquivos .py", "crescimento_arquivos_py.png"),
        ("commits", "Crescimento de commits", "Commits", "crescimento_commits.png"),
    ]

    for chave, titulo, y_label, nome_arquivo in series:
        valores = []
        labels = []
        for label, ponto in zip(labels_hist, historico):
            valor = ponto.get(chave)
            if isinstance(valor, (int, float)):
                labels.append(label)
                valores.append(float(valor))
        if not valores:
            continue
        destino = imagens_dir / nome_arquivo
        if salvar_grafico_linha(plt, labels, valores, titulo, y_label, destino):
            graficos[chave] = f"{imagens_rel_local}/{destino.name}"
            graficos[f"{chave}_root"] = f"{imagens_rel_root}/{destino.name}"

    return graficos


# ============================================================
# COLETA DE MÉTRICAS
# ============================================================
def coletar_metricas_pasta_importante(pasta_base: Path, repo_root: Path, relatorios_dir: Path) -> Dict[str, Any]:
    if not pasta_base.exists() or not pasta_base.is_dir():
        return {
            "existe": False,
            "arquivos": 0,
            "subpastas": 0,
            "tamanho_bytes": 0,
            "linhas_gerais": 0,
        }

    total_files = 0
    total_dirs = 0
    total_size = 0
    total_linhas = 0

    for p in pasta_base.rglob("*"):
        try:
            if deve_ignorar(p, repo_root, relatorios_dir):
                continue

            if p.is_dir():
                total_dirs += 1
                continue

            if not p.is_file():
                continue

            total_files += 1
            total_size += p.stat().st_size
            ext = p.suffix.lower() if p.suffix else ""
            if eh_arquivo_texto_por_extensao(ext) or ext == "":
                total_linhas += contar_linhas_arquivo(p)
        except OSError:
            continue

    return {
        "existe": True,
        "arquivos": total_files,
        "subpastas": total_dirs,
        "tamanho_bytes": total_size,
        "linhas_gerais": total_linhas,
    }


def coletar_rank_pastas_importantes(repo_root: Path, relatorios_dir: Path) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []

    for caminho_relativo, nome_exibicao in PASTAS_IMPORTANTES_RANK:
        pasta = repo_root / caminho_relativo
        metricas = coletar_metricas_pasta_importante(pasta, repo_root, relatorios_dir)
        itens.append({
            "pasta": nome_exibicao,
            "caminho": caminho_relativo.replace("\\", "/"),
            "existe": bool(metricas.get("existe", False)),
            "arquivos": int(metricas.get("arquivos", 0)),
            "subpastas": int(metricas.get("subpastas", 0)),
            "tamanho_bytes": int(metricas.get("tamanho_bytes", 0)),
            "tamanho_kb": round(bytes_para_kb(int(metricas.get("tamanho_bytes", 0))), 2),
            "linhas_gerais": int(metricas.get("linhas_gerais", 0)),
        })

    itens.sort(key=lambda x: int(x["linhas_gerais"]), reverse=True)
    for i, item in enumerate(itens, start=1):
        item["rank"] = i
    return itens


def coletar_metricas(
    repo_root: Path,
    relatorios_dir: Path,
    data_referencia: datetime,
    horas_estimadas: float,
) -> Dict[str, Any]:
    total_size = 0
    total_files = 0
    total_dirs = 0
    total_text_files = 0
    total_text_bytes = 0

    py_files = 0
    py_lines = 0
    py_size_bytes = 0
    py_classes = 0
    py_funcoes = 0
    py_metodos = 0
    bibliotecas_diferentes: set[str] = set()

    linhas_por_ext: Counter[str] = Counter()
    total_linhas_geral = 0

    top_py_por_linhas: List[Dict[str, Any]] = []
    top_funcoes_metodos: List[Dict[str, Any]] = []
    top_classes: List[Dict[str, Any]] = []
    top_arquivos_por_linhas: List[Dict[str, Any]] = []
    arquivos_que_mais_importam: List[Dict[str, Any]] = []

    modulo_para_arquivo, arquivo_para_modulo = construir_mapa_modulos_py(repo_root, relatorios_dir)
    importado_por_count: Counter[str] = Counter()

    for p in repo_root.rglob("*"):
        try:
            if deve_ignorar(p, repo_root, relatorios_dir):
                continue

            if p.is_dir():
                total_dirs += 1
                continue

            if not p.is_file():
                continue

            total_files += 1
            size = p.stat().st_size
            total_size += size

            ext = p.suffix.lower() if p.suffix else ""
            rel = str(p.relative_to(repo_root)).replace("\\", "/")

            if eh_arquivo_texto_por_extensao(ext) or ext == "":
                total_text_files += 1
                total_text_bytes += size
                linhas = contar_linhas_arquivo(p)
                if linhas > 0:
                    linhas_por_ext[ext or "(sem_ext)"] += linhas
                    total_linhas_geral += linhas
                    top_arquivos_por_linhas.append({
                        "arquivo": rel,
                        "ext": ext or "(sem_ext)",
                        "linhas": linhas,
                    })
            else:
                linhas = 0

            if ext == ".py":
                py_files += 1
                py_lines += linhas
                py_size_bytes += size

                analise_py = analisar_python_ast(p, repo_root, relatorios_dir, modulo_para_arquivo, arquivo_para_modulo)
                py_classes += int(analise_py["classes"])
                py_funcoes += int(analise_py["funcoes"])
                py_metodos += int(analise_py["metodos"])
                bibliotecas_diferentes.update({x for x in analise_py.get("bibliotecas_roots", set()) if x})

                top_py_por_linhas.append({
                    "arquivo": rel,
                    "linhas": int(linhas),
                    "tamanho_bytes": int(size),
                    "tamanho_kb": round(bytes_para_kb(int(size)), 2),
                })

                imports_internos = list(analise_py.get("imports_internos", []))
                arquivos_que_mais_importam.append({
                    "arquivo": rel,
                    "arquivos_internos_importados": len(imports_internos),
                    "imports_totais": int(analise_py.get("imports_total", 0)),
                    "linhas": int(linhas),
                })
                for arq_importado in imports_internos:
                    importado_por_count[arq_importado] += 1

                for item in analise_py.get("itens_funcoes_metodos", []):
                    top_funcoes_metodos.append({
                        "arquivo": rel,
                        "nome": str(item["nome"]),
                        "tipo": str(item["tipo"]),
                        "linhas": int(item["linhas"]),
                    })

                for item in analise_py.get("itens_classes", []):
                    top_classes.append({
                        "arquivo": rel,
                        "nome": str(item["nome"]),
                        "linhas": int(item["linhas"]),
                    })

        except OSError:
            continue

    top_py_por_linhas.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top_funcoes_metodos.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top_classes.sort(key=lambda x: int(x["linhas"]), reverse=True)
    top_arquivos_por_linhas.sort(key=lambda x: int(x["linhas"]), reverse=True)
    arquivos_que_mais_importam.sort(
        key=lambda x: (int(x["arquivos_internos_importados"]), int(x["imports_totais"]), int(x["linhas"])),
        reverse=True,
    )

    arquivos_mais_importados = [
        {
            "arquivo": arq,
            "vezes_importado": int(count),
        }
        for arq, count in importado_por_count.most_common(10)
    ]

    primeira_data = tentar_primeiro_commit_data(repo_root)
    dias_desde_criacao = None
    if primeira_data is not None:
        dias_desde_criacao = max(0, (data_referencia.date() - primeira_data.date()).days)

    commits = tentar_contar_commits(repo_root, data_referencia)
    rank_pastas = coletar_rank_pastas_importantes(repo_root, relatorios_dir)
    linhas_por_ext_lista = [
        {"ext": ext, "linhas": linhas}
        for ext, linhas in sorted(linhas_por_ext.items(), key=lambda kv: kv[1], reverse=True)
        if linhas > 0
    ]

    return {
        "resumo": {
            "pastas": total_dirs,
            "arquivos": total_files,
            "arquivos_texto": total_text_files,
            "tamanho_texto_bytes": total_text_bytes,
            "tamanho_texto_kb": round(bytes_para_kb(total_text_bytes), 2),
            "tamanho_bytes": total_size,
            "tamanho_gb": round(bytes_para_gb(total_size), 6),
            "linhas_totais_geral": total_linhas_geral,
            "dias_desde_criacao_repo": dias_desde_criacao,
            "horas_estimadas": round(horas_estimadas, 2),
            "commits": commits,
        },
        "python": {
            "py_arquivos": py_files,
            "linhas_totais": py_lines,
            "tamanho_bytes": py_size_bytes,
            "tamanho_kb": round(bytes_para_kb(py_size_bytes), 2),
            "classes_encontradas": py_classes,
            "funcoes_encontradas": py_funcoes,
            "metodos_encontrados": py_metodos,
            "total_funcoes_e_metodos": py_funcoes + py_metodos,
            "bibliotecas_diferentes": len(bibliotecas_diferentes),
            "bibliotecas": sorted(bibliotecas_diferentes),
            "top50_maiores_py_por_linhas": top_py_por_linhas[:50],
            "top20_maiores_funcoes_metodos": top_funcoes_metodos[:20],
            "top20_maiores_classes": top_classes[:20],
            "top10_arquivos_mais_importados": arquivos_mais_importados[:10],
            "top10_arquivos_que_mais_importam": arquivos_que_mais_importam[:10],
        },
        "pastas_importantes": {
            "observacao": "Rank recursivo por linhas das 15 pastas principais definidas manualmente.",
            "itens": rank_pastas,
        },
        "linhas_por_extensao": {
            "itens": linhas_por_ext_lista,
        },
        "arquivos": {
            "top10_maiores_por_linhas": top_arquivos_por_linhas[:10],
        },
    }


# ============================================================
# MARKDOWN
# ============================================================
def markdown_rank_pastas_importantes(atual: Dict[str, Any]) -> str:
    itens = (atual.get("pastas_importantes", {}).get("itens") or [])[:15]
    if not itens:
        return "_Nenhuma pasta importante encontrada para montar o rank._"

    linhas = [
        "| Rank | Pasta | Caminho | Subpastas | Arquivos | Linhas gerais | Tamanho (KB) |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for it in itens:
        linhas.append(
            f"| {fmt_int(int(it['rank']))} | `{it['pasta']}` | `{it['caminho']}` | "
            f"{fmt_int(int(it['subpastas']))} | {fmt_int(int(it['arquivos']))} | "
            f"{fmt_int(int(it['linhas_gerais']))} | {fmt_num(float(it.get('tamanho_kb', 0.0)), 2)} |"
        )
    return "\n".join(linhas)


def markdown_top50_py_por_linhas(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top50_maiores_py_por_linhas") or [])[:50]
    if not itens:
        return "_Nenhum arquivo `.py` encontrado._"

    linhas = [
        "| Arquivo | Linhas | Tamanho (KB) |",
        "|---|---:|---:|",
    ]
    for it in itens:
        linhas.append(
            f"| `{it['arquivo']}` | {fmt_int(int(it['linhas']))} | {fmt_num(float(it.get('tamanho_kb', 0.0)), 2)} |"
        )
    return "\n".join(linhas)


def markdown_top_funcoes_metodos(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top20_maiores_funcoes_metodos") or [])[:20]
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
    itens = (atual.get("python", {}).get("top20_maiores_classes") or [])[:20]
    if not itens:
        return "_Nenhuma classe Python encontrada._"

    linhas = [
        "| Arquivo | Classe | Linhas |",
        "|---|---|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | `{it['nome']}` | {fmt_int(int(it['linhas']))} |")
    return "\n".join(linhas)


def markdown_top_arquivos_mais_importados(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top10_arquivos_mais_importados") or [])[:10]
    if not itens:
        return "_Nenhum arquivo interno importado foi encontrado._"

    linhas = [
        "| Arquivo | Vezes importado |",
        "|---|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | {fmt_int(int(it['vezes_importado']))} |")
    return "\n".join(linhas)


def markdown_top_arquivos_que_mais_importam(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top10_arquivos_que_mais_importam") or [])[:10]
    if not itens:
        return "_Nenhum arquivo `.py` com imports internos foi encontrado._"

    linhas = [
        "| Arquivo | Arquivos internos importados | Imports totais | Linhas |",
        "|---|---:|---:|---:|",
    ]
    for it in itens:
        linhas.append(
            f"| `{it['arquivo']}` | {fmt_int(int(it['arquivos_internos_importados']))} | "
            f"{fmt_int(int(it['imports_totais']))} | {fmt_int(int(it['linhas']))} |"
        )
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


def bloco_imagem(rel_path: Optional[str], titulo: str) -> List[str]:
    if not rel_path:
        return [f"_Imagem não gerada: {titulo}._", ""]
    return [f"![{titulo}]({rel_path})", ""]


def gerar_markdown(atual: Dict[str, Any], imagem_key_suffix: str = "") -> str:
    resumo = atual["resumo"]
    py = atual["python"]
    meta = atual.get("meta", {}) or {}
    graficos = atual.get("graficos", {}) or {}

    criado_em = str(meta.get("criado_em", ""))
    nome_repo = str(meta.get("repo", ""))
    numero_relatorio = meta.get("numero_relatorio")

    def g(chave: str) -> Optional[str]:
        return graficos.get(chave + imagem_key_suffix)

    md: List[str] = []
    md.append("# Registro")
    md.append("")
    if numero_relatorio is not None:
        md.append(f"**Relatório:** #{numero_relatorio}  ")
    if nome_repo:
        md.append(f"**Repo:** `{nome_repo}`  ")
    if criado_em:
        md.append(f"**Gerado em:** {criado_em}  ")
    md.append(f"**Modelo de relatório:** {MODELO_RELATORIO}  ")
    md.append(f"**Autor:** {AUTOR_RELATORIO}")
    md.append("")

    md.append("## Visão geral")
    md.append("")
    md.append(f"- **Pastas:** {fmt_int(int(resumo['pastas']))}")
    md.append(f"- **Arquivos:** {fmt_int(int(resumo['arquivos']))}")
    md.append(f"- **Arquivos de texto:** {fmt_int(int(resumo['arquivos_texto']))}")
    md.append(f"- **Peso dos arquivos de texto:** {fmt_tamanho_kb(int(resumo['tamanho_texto_bytes']))}")
    md.append(f"- **Tamanho total:** {fmt_tamanho_gb_com_bytes(int(resumo['tamanho_bytes']))}")
    if resumo.get("dias_desde_criacao_repo") is not None:
        md.append(f"- **Dias desde a criação do repo:** {fmt_int(int(resumo['dias_desde_criacao_repo']))}")
    md.append(f"- **Horas estimadas:** {fmt_num(float(resumo['horas_estimadas']), 2)}")
    md.append(f"- **Linhas totais gerais:** {fmt_int(int(resumo['linhas_totais_geral']))}")
    if resumo.get("commits") is not None:
        md.append(f"- **Commits (repo):** {fmt_int(int(resumo['commits']))}")
    md.append("")

    md.append("## Python")
    md.append("")
    md.append(f"- **Arquivos `.py`:** {fmt_int(int(py['py_arquivos']))}")
    md.append(f"- **Linhas totais:** {fmt_int(int(py['linhas_totais']))}")
    md.append(f"- **Tamanho total `.py`:** {fmt_tamanho_kb(int(py['tamanho_bytes']))}")
    md.append(f"- **Classes encontradas:** {fmt_int(int(py['classes_encontradas']))}")
    md.append(f"- **Funções encontradas:** {fmt_int(int(py['funcoes_encontradas']))}")
    md.append(f"- **Métodos encontrados:** {fmt_int(int(py['metodos_encontrados']))}")
    md.append(f"- **Total funções + métodos:** {fmt_int(int(py['total_funcoes_e_metodos']))}")
    md.append(f"- **Bibliotecas diferentes usadas:** {fmt_int(int(py['bibliotecas_diferentes']))}")
    md.append("")

    md.append("## Rank das 15 pastas mais relevantes por linhas")
    md.append("")
    md.extend(bloco_imagem(g("rank_15_pastas_barras"), "Gráfico de barras do rank das 15 pastas"))
    md.extend(bloco_imagem(g("rank_15_pastas_pizza"), "Gráfico de pizza do rank das 15 pastas"))
    md.append(markdown_rank_pastas_importantes(atual))
    md.append("")

    md.append("## Top 50 maiores arquivos `.py` por linhas")
    md.append("")
    md.append(markdown_top50_py_por_linhas(atual))
    md.append("")

    md.append("## Top 20 maiores funções e métodos")
    md.append("")
    md.append(markdown_top_funcoes_metodos(atual))
    md.append("")

    md.append("## Top 20 maiores classes")
    md.append("")
    md.append(markdown_top_classes(atual))
    md.append("")

    md.append("## Top 10 arquivos mais importados")
    md.append("")
    md.append(markdown_top_arquivos_mais_importados(atual))
    md.append("")

    md.append("## Top 10 arquivos que mais importam")
    md.append("")
    md.append(markdown_top_arquivos_que_mais_importam(atual))
    md.append("")

    md.append("## Top 10 maiores arquivos por linhas")
    md.append("")
    md.append(markdown_top_arquivos_por_linhas(atual))
    md.append("")

    md.append("## Linhas por extensão")
    md.append("")
    md.extend(bloco_imagem(g("linhas_por_extensao_pizza"), "Gráfico de pizza das linhas por extensão"))
    md.append(markdown_linhas_por_extensao(atual))
    md.append("")

    md.append("## Gráficos de crescimento")
    md.append("")
    md.extend(bloco_imagem(g("linhas_totais_geral"), "Crescimento de linhas gerais"))
    md.extend(bloco_imagem(g("linhas_py"), "Crescimento de linhas .py"))
    md.extend(bloco_imagem(g("arquivos_py"), "Crescimento de arquivos .py"))
    md.extend(bloco_imagem(g("commits"), "Crescimento de commits"))

    return "\n".join(md).strip() + "\n"


# ============================================================
# MAIN
# ============================================================
def main() -> None:
    script_path = Path(__file__).resolve()
    outros_dir = script_path.parent
    repo_root = outros_dir.parent

    relatorios_root_dir = outros_dir / "Relatorios"
    imagens_base_dir = relatorios_root_dir / "Imagens"
    registros_dir = relatorios_root_dir / "Registros"
    relatorios_json_dir = relatorios_root_dir / "Relatorios"

    relatorios_root_dir.mkdir(parents=True, exist_ok=True)
    imagens_base_dir.mkdir(parents=True, exist_ok=True)
    registros_dir.mkdir(parents=True, exist_ok=True)
    relatorios_json_dir.mkdir(parents=True, exist_ok=True)

    agora_real = datetime.now().astimezone()
    data_referencia = obter_data_referencia()

    numero_relatorio = len(list(relatorios_json_dir.glob("*.json"))) + 1
    basename = agora_real.strftime("%Y-%m-%d_%H-%M-%S")
    json_name = f"{basename}.json"
    md_name = f"{basename}.md"

    json_path = relatorios_json_dir / json_name
    md_path = registros_dir / md_name
    registro_md_path = repo_root / "Registro.md"

    horas_estimadas, relatorio_anterior_nome, horas_base = calcular_horas_estimadas(relatorios_json_dir, data_referencia)

    atual = coletar_metricas(repo_root, relatorios_root_dir, data_referencia, horas_estimadas)
    atual["meta"] = {
        "numero_relatorio": numero_relatorio,
        "criado_em": agora_real.isoformat(timespec="seconds"),
        "data_referencia": data_referencia.isoformat(timespec="seconds"),
        "repo": repo_root.name,
        "arquivo": json_name,
        "arquivo_markdown": md_name,
        "base_dir": str(repo_root),
        "script": str(script_path.relative_to(repo_root)).replace("\\", "/"),
        "relatorios_dir": str(relatorios_root_dir.relative_to(repo_root)).replace("\\", "/"),
        "relatorios_json_dir": str(relatorios_json_dir.relative_to(repo_root)).replace("\\", "/"),
        "registros_dir": str(registros_dir.relative_to(repo_root)).replace("\\", "/"),
        "modelo": MODELO_RELATORIO,
        "autor": AUTOR_RELATORIO,
        "incremento_horas": float(INCREMENTO_HORAS),
        "horas_base_anterior": float(horas_base),
        "relatorio_anterior": relatorio_anterior_nome,
        "imagens_dir": f"Outros/Relatorios/Imagens/{basename}",
    }

    historico = coletar_historico_relatorios(relatorios_json_dir, atual, data_referencia, repo_root)
    atual["historico_crescimento"] = {"itens": historico}

    graficos = gerar_graficos(atual, historico, imagens_base_dir, basename)
    atual["graficos"] = graficos

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)

    md_local = gerar_markdown(atual, imagem_key_suffix="")
    md_root = gerar_markdown(atual, imagem_key_suffix="_root")
    md_path.write_text(md_local, encoding="utf-8")
    registro_md_path.write_text(md_root, encoding="utf-8")

    print("Relatório gerado:")
    print(f"- JSON: {json_path}")
    print(f"- Markdown do relatório: {md_path}")
    print(f"- Markdown da raiz: {registro_md_path}")
    if graficos:
        print(f"- Pasta de imagens: {imagens_base_dir / basename}")
    else:
        print("- Gráficos: não gerados (matplotlib ausente ou falha durante a renderização)")


if __name__ == "__main__":
    main()
