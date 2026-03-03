from __future__ import annotations

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


def bytes_para_gib(num_bytes: int) -> float:
    return num_bytes / (1024 ** 3)


def bytes_para_kib(num_bytes: int) -> float:
    return num_bytes / 1024


def contar_linhas_py(path: Path) -> int:
    total = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                total += 1
    except OSError:
        return 0
    return total


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
    # Ignora qualquer coisa dentro de ".git", "__pycache__", e também o diretório de relatórios
    parts = set(p.parts)
    if any(x in parts for x in IGNORAR_PASTAS):
        return True
    if p.is_relative_to(relatorios_dir):
        return True
    if p.suffix.lower() in IGNORAR_EXTENSOES:
        return True
    return False


def coletar_metricas(repo_root: Path, relatorios_dir: Path) -> Dict[str, Any]:
    total_size = 0
    total_files = 0
    total_dirs = 0

    ext_count: Counter[str] = Counter()
    ext_size: Dict[str, int] = defaultdict(int)

    py_files = 0
    py_lines = 0
    py_classes = 0

    maiores_py: List[Dict[str, Any]] = []  # top 5 maiores .py

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

            if p.suffix.lower() == ".py":
                py_files += 1
                py_lines += contar_linhas_py(p)
                py_classes += contar_classes_py(p)

                maiores_py.append({
                    "arquivo": str(p.relative_to(repo_root)).replace("\\", "/"),
                    "tamanho_bytes": size
                })

        except OSError:
            continue

    # Top extensões
    top_ext_por_tamanho = sorted(ext_size.items(), key=lambda kv: kv[1], reverse=True)
    top_ext_por_qtd = ext_count.most_common()

    # Top 5 maiores .py
    maiores_py.sort(key=lambda x: int(x["tamanho_bytes"]), reverse=True)
    top5_maiores_py = maiores_py[:5]
    for it in top5_maiores_py:
        it["tamanho_kib"] = round(bytes_para_kib(int(it["tamanho_bytes"])), 2)

    return {
        "resumo": {
            "pastas": total_dirs,
            "arquivos": total_files,
            "tamanho_bytes": total_size,
            "tamanho_gib": round(bytes_para_gib(total_size), 6),
        },
        "python": {
            "py_arquivos": py_files,
            "linhas_totais": py_lines,
            "classes_encontradas": py_classes,
            "top5_maiores_py": top5_maiores_py,
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
        "py_arquivos": ("python", "py_arquivos"),
        "linhas_totais": ("python", "linhas_totais"),
        "classes_encontradas": ("python", "classes_encontradas"),
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


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_bytes(n: int) -> str:
    gib = bytes_para_gib(n)
    return f"{fmt_int(n)} bytes ({gib:.3f} GiB)"


def markdown_top_extensoes(atual: Dict[str, Any], limite: int = 12) -> str:
    itens = (atual.get("extensoes", {}).get("top_por_tamanho") or [])[:limite]
    linhas = [
        "| Ext | Tamanho (GiB) | Arquivos |",
        "|---:|---:|---:|",
    ]
    for it in itens:
        ext = it["ext"]
        tamanho = f'{bytes_para_gib(int(it["tamanho_bytes"])):.3f}'
        arqs = fmt_int(int(it["arquivos"]))
        linhas.append(f"| `{ext}` | {tamanho} | {arqs} |")
    return "\n".join(linhas)


def markdown_top5_py(atual: Dict[str, Any]) -> str:
    itens = (atual.get("python", {}).get("top5_maiores_py") or [])[:5]
    if not itens:
        return "_Nenhum arquivo `.py` encontrado._"

    linhas = [
        "| Arquivo | Tamanho (KiB) |",
        "|---|---:|",
    ]
    for it in itens:
        arq = str(it["arquivo"])
        kib = float(it.get("tamanho_kib", round(bytes_para_kib(int(it["tamanho_bytes"])), 2)))
        linhas.append(f"| `{arq}` | {kib:.2f} |")
    return "\n".join(linhas)


def markdown_diff(diff: Optional[Dict[str, Any]]) -> str:
    if not diff:
        return "_Sem relatório anterior para comparar._"

    linhas = []
    chaves = ["pastas", "arquivos", "tamanho_bytes", "py_arquivos", "linhas_totais", "classes_encontradas"]
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

    criado_em = atual.get("meta", {}).get("criado_em", "")
    nome_repo = atual.get("meta", {}).get("repo", "")

    md: List[str] = []
    md.append("# Registro\n")
    if nome_repo:
        md.append(f"**Repo:** `{nome_repo}`  \n")
    if criado_em:
        md.append(f"**Gerado em:** {criado_em}  \n")

    md.append("## Visão geral\n")
    md.append(f"- **Pastas:** {fmt_int(int(resumo['pastas']))}")
    md.append(f"- **Arquivos:** {fmt_int(int(resumo['arquivos']))}")
    md.append(f"- **Tamanho total:** {fmt_bytes(int(resumo['tamanho_bytes']))}\n")

    md.append("## Python\n")
    md.append(f"- **Arquivos `.py`:** {fmt_int(int(py['py_arquivos']))}")
    md.append(f"- **Linhas totais:** {fmt_int(int(py['linhas_totais']))}")
    md.append(f"- **Classes encontradas:** {fmt_int(int(py['classes_encontradas']))}\n")

    md.append("### Top 5 maiores arquivos `.py`\n")
    md.append(markdown_top5_py(atual))
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

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_name = f"{ts}.json"
    json_path = relatorios_dir / json_name

    anterior_path = encontrar_ultimo_relatorio(relatorios_dir)
    anterior = ler_json(anterior_path) if anterior_path else None

    atual = coletar_metricas(repo_root, relatorios_dir)
    atual["meta"] = {
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