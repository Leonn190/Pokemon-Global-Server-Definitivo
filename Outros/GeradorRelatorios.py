from __future__ import annotations

import ast
import json
import re
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


def analisar_python_ast(path: Path) -> Dict[str, int]:
    try:
        codigo = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {
            "classes": 0,
            "funcoes": 0,
            "metodos": 0,
        }

    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        # fallback mínimo se o arquivo estiver com sintaxe quebrada
        return {
            "classes": contar_classes_py(path),
            "funcoes": 0,
            "metodos": 0,
        }

    classes = 0
    funcoes = 0
    metodos = 0

    def visitar(no: ast.AST, dentro_de_classe: bool = False) -> None:
        nonlocal classes, funcoes, metodos

        if isinstance(no, ast.ClassDef):
            classes += 1
            for filho in no.body:
                visitar(filho, dentro_de_classe=True)
            return

        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if dentro_de_classe:
                metodos += 1
            else:
                funcoes += 1

        for filho in ast.iter_child_nodes(no):
            visitar(filho, dentro_de_classe=dentro_de_classe)

    visitar(arvore)
    return {
        "classes": classes,
        "funcoes": funcoes,
        "metodos": metodos,
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


def resolver_import_local(
    modulo_atual: str,
    importado: Optional[str],
    nivel: int,
) -> Optional[str]:
    """
    Resolve imports relativos.
    """
    if nivel <= 0:
        return importado

    partes = modulo_atual.split(".")
    if not partes:
        return importado

    # Sobe `nivel - 1` níveis a partir do módulo atual
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

    # Remove autoimport do próprio arquivo
    encontrados.discard(rel)
    return sorted(encontrados)


def calcular_numero_relatorio(relatorios_dir: Path) -> int:
    if not relatorios_dir.exists():
        return 1
    return len(list(relatorios_dir.glob("*.json"))) + 1


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

    maiores_py: List[Dict[str, Any]] = []  # top 15 maiores .py
    maiores_geral: List[Dict[str, Any]] = []

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

            maiores_geral.append({
                "arquivo": str(p.relative_to(repo_root)).replace("\\", "/"),
                "ext": ext,
                "tamanho_bytes": size,
            })

            # Linhas por extensão textual
            if ext in EXTENSOES_TEXTO_INTERESSE or ext == "(sem_ext)":
                linhas = contar_linhas_arquivo(p)
                if linhas > 0:
                    linhas_por_ext[ext] += linhas
                    total_linhas_geral += linhas
            else:
                linhas = 0

            if ext == ".py":
                py_files += 1

                if linhas == 0:
                    linhas = contar_linhas_arquivo(p)
                    if linhas > 0:
                        linhas_por_ext[ext] += linhas
                        total_linhas_geral += linhas

                py_lines += linhas

                analise_py = analisar_python_ast(p)
                py_classes += analise_py["classes"]
                py_funcoes += analise_py["funcoes"]
                py_metodos += analise_py["metodos"]

                maiores_py.append({
                    "arquivo": str(p.relative_to(repo_root)).replace("\\", "/"),
                    "tamanho_bytes": size,
                    "tamanho_kib": round(bytes_para_kib(size), 2),
                    "linhas": linhas,
                })

                for arq_importado in coletar_imports_internos_py(
                    p,
                    repo_root,
                    relatorios_dir,
                    modulo_para_arquivo,
                    arquivo_para_modulo,
                ):
                    importado_por_count[arq_importado] += 1

        except OSError:
            continue

    top_ext_por_tamanho = sorted(ext_size.items(), key=lambda kv: kv[1], reverse=True)
    top_ext_por_qtd = ext_count.most_common()

    maiores_py.sort(key=lambda x: int(x["tamanho_bytes"]), reverse=True)
    top15_maiores_py = maiores_py[:15]

    maiores_geral.sort(key=lambda x: int(x["tamanho_bytes"]), reverse=True)
    top15_maiores_geral = maiores_geral[:15]
    for it in top15_maiores_geral:
        it["tamanho_kib"] = round(bytes_para_kib(int(it["tamanho_bytes"])), 2)

    top5_importados_py = [
        {
            "arquivo": arquivo,
            "importado_por_arquivos": qtd,
        }
        for arquivo, qtd in importado_por_count.most_common(5)
    ]

    linhas_por_ext_lista = [
        {"ext": ext, "linhas": linhas}
        for ext, linhas in sorted(linhas_por_ext.items(), key=lambda kv: kv[1], reverse=True)
        if linhas > 0
    ]

    media_linhas_por_py = (py_lines / py_files) if py_files else 0.0

    return {
        "resumo": {
            "pastas": total_dirs,
            "arquivos": total_files,
            "tamanho_bytes": total_size,
            "tamanho_gib": round(bytes_para_gib(total_size), 6),
            "linhas_totais_geral": total_linhas_geral,
        },
        "python": {
            "py_arquivos": py_files,
            "linhas_totais": py_lines,
            "classes_encontradas": py_classes,
            "funcoes_encontradas": py_funcoes,
            "metodos_encontrados": py_metodos,
            "total_funcoes_e_metodos": py_funcoes + py_metodos,
            "media_linhas_por_arquivo": round(media_linhas_por_py, 2),
            "top15_maiores_py": top15_maiores_py,
            "top5_arquivos_mais_importados": top5_importados_py,
        },
        "linhas_por_extensao": {
            "itens": linhas_por_ext_lista,
        },
        "arquivos": {
            "top15_maiores_geral": top15_maiores_geral,
        },
        "extensoes": {
            "contagem": dict(ext_count),
            "tamanho_bytes": dict(ext_size),
            "top_por_tamanho": [
                {
                    "ext": ext,
                    "tamanho_bytes": sz,
                    "tamanho_gib": round(bytes_para_gib(sz), 6),
                    "arquivos": ext_count[ext],
                }
                for ext, sz in top_ext_por_tamanho[:20]
            ],
            "top_por_quantidade": [
                {
                    "ext": ext,
                    "arquivos": cnt,
                    "tamanho_bytes": ext_size.get(ext, 0),
                    "tamanho_gib": round(bytes_para_gib(ext_size.get(ext, 0)), 6),
                }
                for ext, cnt in top_ext_por_qtd[:20]
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


def diff_extensoes(anterior: Dict[str, Any], atual: Dict[str, Any]) -> Dict[str, Any]:
    a_count = anterior.get("extensoes", {}).get("contagem", {}) or {}
    b_count = atual.get("extensoes", {}).get("contagem", {}) or {}

    a_size = anterior.get("extensoes", {}).get("tamanho_bytes", {}) or {}
    b_size = atual.get("extensoes", {}).get("tamanho_bytes", {}) or {}

    todas = set(a_count.keys()) | set(b_count.keys()) | set(a_size.keys()) | set(b_size.keys())

    mudancas = []
    for ext in sorted(todas):
        ca = int(a_count.get(ext, 0))
        cb = int(b_count.get(ext, 0))
        sa = int(a_size.get(ext, 0))
        sb = int(b_size.get(ext, 0))

        if ca == cb and sa == sb:
            continue

        mudancas.append({
            "ext": ext,
            "arquivos_anterior": ca,
            "arquivos_atual": cb,
            "delta_arquivos": cb - ca,
            "tamanho_bytes_anterior": sa,
            "tamanho_bytes_atual": sb,
            "delta_tamanho_bytes": sb - sa,
        })

    mudancas.sort(key=lambda m: abs(int(m["delta_tamanho_bytes"])), reverse=True)
    return {"mudancas": mudancas[:50]}


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

    diffs["extensoes"] = diff_extensoes(anterior, atual)
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


def markdown_top15_py(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top15_maiores_py") or [])[:15]
    if not itens:
        return "_Nenhum arquivo `.py` encontrado._"

    linhas = [
        "| Arquivo | Tamanho (KiB) | Linhas |",
        "|---|---:|---:|",
    ]
    for it in itens:
        arq = str(it["arquivo"])
        kib = float(it.get("tamanho_kib", round(bytes_para_kib(int(it["tamanho_bytes"])), 2)))
        linhas_count = int(it.get("linhas", 0))
        linhas.append(f"| `{arq}` | {kib:.2f} | {fmt_int(linhas_count)} |")
    return "\n".join(linhas)


def markdown_top_importados_py(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top5_arquivos_mais_importados") or [])[:5]
    if not itens:
        return "_Nenhum import interno Python encontrado._"

    linhas = [
        "| Arquivo | Importado por |",
        "|---|---:|",
    ]
    for it in itens:
        linhas.append(f"| `{it['arquivo']}` | {fmt_int(int(it['importado_por_arquivos']))} |")
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

    ext_mudancas = (diff.get("extensoes", {}) or {}).get("mudancas", []) or []
    if ext_mudancas:
        linhas.append("\n**Maiores mudanças por extensão (top 12 por |Δ tamanho|):**\n")
        linhas.append("| Ext | Δ arquivos | Δ tamanho (GiB) |")
        linhas.append("|---:|---:|---:|")
        for m in ext_mudancas[:12]:
            ext = m["ext"]
            da = int(m["delta_arquivos"])
            ds = int(m["delta_tamanho_bytes"])
            linhas.append(f"| `{ext}` | {fmt_int(da)} | {bytes_para_gib(ds):.3f} |")

    return "\n".join(linhas)


def gerar_markdown(atual: Dict[str, Any], diff: Optional[Dict[str, Any]]) -> str:
    resumo = atual["resumo"]
    py = atual["python"]
    meta = atual.get("meta", {})

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
    md.append(f"- **Linhas totais gerais:** {fmt_int(int(resumo['linhas_totais_geral']))}\n")

    md.append("## Python\n")
    md.append(f"- **Arquivos `.py`:** {fmt_int(int(py['py_arquivos']))}")
    md.append(f"- **Linhas totais:** {fmt_int(int(py['linhas_totais']))}")
    md.append(f"- **Classes encontradas:** {fmt_int(int(py['classes_encontradas']))}")
    md.append(f"- **Funções encontradas:** {fmt_int(int(py['funcoes_encontradas']))}")
    md.append(f"- **Métodos encontrados:** {fmt_int(int(py['metodos_encontrados']))}")
    md.append(f"- **Total funções + métodos:** {fmt_int(int(py['total_funcoes_e_metodos']))}")
    md.append(f"- **Média de linhas por arquivo `.py`:** {py['media_linhas_por_arquivo']:.2f}\n")

    md.append("### Top 15 maiores arquivos `.py`\n")
    md.append(markdown_top15_py(atual))
    md.append("")

    md.append("### Top 5 arquivos Python mais importados\n")
    md.append(markdown_top_importados_py(atual))
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
    