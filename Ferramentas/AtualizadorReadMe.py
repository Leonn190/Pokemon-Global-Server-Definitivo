from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


README_NOME = "README.md"

EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
EXTENSOES_AUDIO = {".ogg", ".mp3", ".wav", ".flac", ".midi", ".mid"}

CSV_POKEMONS = "Pokemon Global Server - Pokemons.csv"
CSV_ATAQUES = "Pokemon Global Server - Ataques.csv"
CSV_EFEITOS = "Pokemon Global Server - Efeitos.csv"
CSV_ITENS = "Pokemon Global Server - Itens.csv"
CSV_EQUIPAVEIS = "Pokemon Global Server - Equipaveis.csv"
CSV_NPC_COMBATENTE = "Pokemon Global Server - NPC Combatente.csv"
CSV_NPC_VENDEDOR = "Pokemon Global Server - NPC Vendedor.csv"
JSON_RECEITAS = "Pokemon Global Server - Receitas.json"
TOML_ESTRUTURAS = "Dados/Regras/EstruturasNaturais.toml"


# ============================================================
# UTILITÁRIOS
# ============================================================
def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_num(n: float, casas: int = 2) -> str:
    return f"{n:.{casas}f}".replace(",", ".")


def bytes_para_kb(num_bytes: int) -> float:
    return num_bytes / 1024.0


def bytes_para_gb(num_bytes: int) -> float:
    return num_bytes / (1024.0 ** 3)


def fmt_tamanho_kb(num_bytes: int) -> str:
    return f"{fmt_num(bytes_para_kb(num_bytes), 2)} KB"


def fmt_tamanho_gb_com_bytes(num_bytes: int) -> str:
    return f"{fmt_num(bytes_para_gb(num_bytes), 3)} GB ({fmt_int(num_bytes)} bytes)"


def ler_texto(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def escrever_texto(path: Path, texto: str) -> None:
    path.write_text(texto, encoding="utf-8")


def ler_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(ler_texto(path))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def natural_key(path: Path) -> List[Any]:
    texto = path.name.lower()
    partes = re.split(r"(\d+)", texto)
    chave: List[Any] = []
    for parte in partes:
        if parte.isdigit():
            chave.append(int(parte))
        else:
            chave.append(parte)
    return chave


def caminho_md(path: Path, repo_root: Path) -> str:
    return str(path.relative_to(repo_root)).replace("\\", "/")


def parse_datetime_seguro(valor: str) -> Optional[datetime]:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return dt.astimezone().replace(tzinfo=None) if dt.tzinfo is not None else dt
    except Exception:
        return None


def extrair_prefixo(readme: str) -> str:
    match = re.search(r"^##\s+1\. Descrição\s*$", readme, flags=re.MULTILINE)
    if not match:
        return readme.strip() + "\n"
    return readme[: match.start()].rstrip() + "\n"


def extrair_secao(readme: str, titulo: str, fallback: str) -> str:
    padrao = re.compile(
        rf"(^##\s+{re.escape(titulo)}\s*$.*?)(?=^##\s+\d+\.\s+|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = padrao.search(readme)
    if match:
        secao = match.group(1).strip()
    else:
        secao = fallback.strip()
    # As seções fixas do README antigo podiam terminar com separador `---`.
    # O montador já controla os separadores, então removemos apenas essa sobra final.
    return re.sub(r"\n+---\s*$", "", secao).strip()


def valor_num(relatorio: Optional[Dict[str, Any]], caminho: Tuple[str, ...], default: float = 0.0) -> float:
    cur: Any = relatorio
    for parte in caminho:
        if not isinstance(cur, dict) or parte not in cur:
            return default
        cur = cur[parte]
    return float(cur) if isinstance(cur, (int, float)) else default


# ============================================================
# CONTADORES DE DADOS DO JOGO
# ============================================================
def resolver_path_dados(repo_root: Path, *candidatos: str) -> Path:
    for candidato in candidatos:
        path = repo_root / candidato
        if path.exists():
            return path
    return repo_root / candidatos[0]


def contar_csv_registros(path: Path) -> int:
    if not path.exists():
        return 0

    texto = ler_texto(path)
    if not texto.strip():
        return 0

    linhas = [linha for linha in texto.splitlines() if linha.strip()]
    if not linhas:
        return 0

    try:
        dialect = csv.Sniffer().sniff("\n".join(linhas[:10]), delimiters=",;\t")
    except Exception:
        dialect = csv.excel

    try:
        rows = list(csv.reader(linhas, dialect))
    except Exception:
        return max(0, len(linhas) - 1)

    rows_validas = [row for row in rows if any(str(c).strip() for c in row)]
    if not rows_validas:
        return 0

    registros = [row for row in rows_validas[1:] if row and str(row[0]).strip()]
    return len(registros)


def contar_json_dict(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(ler_texto(path))
    except Exception:
        return 0

    if isinstance(data, dict):
        return len(data)
    if isinstance(data, list):
        return len(data)
    return 0


def contar_estruturas_naturais(repo_root: Path) -> int:
    path = repo_root / TOML_ESTRUTURAS
    if not path.exists():
        return 0

    if tomllib is not None:
        try:
            data = tomllib.loads(ler_texto(path))
            tipos = data.get("tipos") if isinstance(data, dict) else None
            if isinstance(tipos, dict):
                return len(tipos)
        except Exception:
            pass

    texto = ler_texto(path)
    return len(re.findall(r"^\s*\[tipos\.\"?[^\]]+\"?\]\s*$", texto, flags=re.MULTILINE))


def contar_trilhas_sonoras(repo_root: Path) -> int:
    candidatos = [
        repo_root / "Recursos" / "Sonoridades" / "Musicas",
        repo_root / "Recursos" / "Audio" / "Musicas",
        repo_root / "Recursos" / "Áudio" / "Músicas",
        repo_root / "Recursos" / "Musicas",
    ]
    pasta = next((p for p in candidatos if p.exists() and p.is_dir()), None)
    if pasta is None:
        return 0

    return sum(1 for p in pasta.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSOES_AUDIO)


def coletar_estatisticas_jogo(repo_root: Path) -> List[Tuple[str, str]]:
    pokemon_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_POKEMONS}", f"Dados/{CSV_POKEMONS}")
    ataques_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_ATAQUES}", f"Dados/{CSV_ATAQUES}")
    efeitos_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_EFEITOS}", f"Dados/{CSV_EFEITOS}")
    itens_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_ITENS}", f"Dados/{CSV_ITENS}")
    equipaveis_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_EQUIPAVEIS}", f"Dados/{CSV_EQUIPAVEIS}")
    npc_combatente_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_NPC_COMBATENTE}", f"Dados/{CSV_NPC_COMBATENTE}")
    npc_vendedor_csv = resolver_path_dados(repo_root, f"Dados/Tabelas/{CSV_NPC_VENDEDOR}", f"Dados/{CSV_NPC_VENDEDOR}")
    receitas_json = resolver_path_dados(repo_root, f"Dados/Catalogos/{JSON_RECEITAS}", f"Dados/{JSON_RECEITAS}")

    dados: List[Tuple[str, str]] = [
        ("Pokémon registrados", fmt_int(contar_csv_registros(pokemon_csv))),
        ("Ataques registrados", fmt_int(contar_csv_registros(ataques_csv))),
        ("Efeitos registrados", fmt_int(contar_csv_registros(efeitos_csv))),
        ("Itens registrados", fmt_int(contar_csv_registros(itens_csv))),
        ("Equipáveis registrados", fmt_int(contar_csv_registros(equipaveis_csv))),
        (
            "NPCs cadastrados",
            fmt_int(contar_csv_registros(npc_combatente_csv) + contar_csv_registros(npc_vendedor_csv)),
        ),
        ("Estruturas naturais", fmt_int(contar_estruturas_naturais(repo_root))),
        ("Trilhas sonoras", fmt_int(contar_trilhas_sonoras(repo_root))),
        ("Receitas", fmt_int(contar_json_dict(receitas_json))),
        ("Tipos de Pokémon", "20"),
        ("Biomas", "7"),
        ("Mundo planejado", "10.000 x 10.000 tiles"),
        ("Critérios de Habilidade da IA", "12"),
        ("Critérios de Personalidade da IA", "7"),
    ]
    return dados


# ============================================================
# ESTATÍSTICAS DO PROJETO A PARTIR DO ÚLTIMO RELATÓRIO
# ============================================================
def data_relatorio(path: Path, data: Optional[Dict[str, Any]]) -> datetime:
    if isinstance(data, dict):
        meta = data.get("meta")
        if isinstance(meta, dict):
            for chave in ("data_referencia", "criado_em", "data_relatorio_original"):
                dt = parse_datetime_seguro(str(meta.get(chave, "")))
                if dt is not None:
                    return dt
    try:
        return datetime.strptime(path.stem, "%Y-%m-%d_%H-%M-%S")
    except Exception:
        return datetime.fromtimestamp(path.stat().st_mtime)


def localizar_ultimo_relatorio(repo_root: Path) -> Optional[Dict[str, Any]]:
    candidatos: List[Path] = []
    for pasta in (
        repo_root / "Documentação" / "Relatorios" / "Relatorios",
        repo_root / "Documentação" / "Relatorios",
    ):
        if pasta.exists():
            candidatos.extend([p for p in pasta.glob("*.json") if p.is_file()])

    melhores: List[Tuple[datetime, Path, Dict[str, Any]]] = []
    for path in candidatos:
        data = ler_json(path)
        if isinstance(data, dict):
            melhores.append((data_relatorio(path, data), path, data))

    if not melhores:
        return None

    melhores.sort(key=lambda item: item[0], reverse=True)
    return melhores[0][2]


def coletar_estatisticas_projeto(repo_root: Path) -> List[Tuple[str, str]]:
    relatorio = localizar_ultimo_relatorio(repo_root)

    resumo = relatorio.get("resumo", {}) if isinstance(relatorio, dict) else {}
    python = relatorio.get("python", {}) if isinstance(relatorio, dict) else {}

    tamanho_texto_bytes = int(resumo.get("tamanho_texto_bytes", 0) or 0)
    tamanho_total_bytes = int(resumo.get("tamanho_bytes", 0) or 0)
    py_tamanho_bytes = int(python.get("tamanho_bytes", 0) or 0)
    dias_projeto = resumo.get("dias_desde_criacao_oficial", resumo.get("dias_desde_criacao_projeto", resumo.get("dias_desde_criacao_repo", 0)))

    return [
        ("Pastas", fmt_int(int(resumo.get("pastas", 0) or 0))),
        ("Arquivos", fmt_int(int(resumo.get("arquivos", 0) or 0))),
        ("Arquivos de texto", fmt_int(int(resumo.get("arquivos_texto", 0) or 0))),
        ("Peso dos arquivos de texto", fmt_tamanho_kb(tamanho_texto_bytes)),
        ("Tamanho total", fmt_tamanho_gb_com_bytes(tamanho_total_bytes)),
        ("Dias desde a criação do projeto", fmt_int(int(dias_projeto or 0))),
        ("Linhas totais gerais", fmt_int(int(resumo.get("linhas_totais_geral", 0) or 0))),
        ("Commits (projeto)", fmt_int(int(resumo.get("commits", 0) or 0))),
        ("Arquivos .py", fmt_int(int(python.get("py_arquivos", 0) or 0))),
        ("Linhas totais .py", fmt_int(int(python.get("linhas_totais", 0) or 0))),
        ("Tamanho total .py", fmt_tamanho_kb(py_tamanho_bytes)),
        ("Classes encontradas", fmt_int(int(python.get("classes_encontradas", 0) or 0))),
        ("Funções encontradas", fmt_int(int(python.get("funcoes_encontradas", 0) or 0))),
        ("Métodos encontrados", fmt_int(int(python.get("metodos_encontrados", 0) or 0))),
        ("Total funções + métodos", fmt_int(int(python.get("total_funcoes_e_metodos", 0) or 0))),
    ]


# ============================================================
# SNAPSHOTS
# ============================================================
def coletar_snapshots(repo_root: Path) -> List[Path]:
    pasta = repo_root / "Snapshots"
    if not pasta.exists() or not pasta.is_dir():
        return []
    imagens = [p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES_IMAGEM]
    imagens.sort(key=natural_key)
    return imagens


def gerar_secao_snapshots(repo_root: Path) -> str:
    imagens = coletar_snapshots(repo_root)

    md: List[str] = [
        "## 2. Snapshots",
        "",
        "> O vídeo de showcase ainda será adicionado. As imagens abaixo são renderizadas diretamente do diretório `Snapshots/` do repositório.",
        "",
        "### Showcase em vídeo",
        "",
        "[Assistir showcase no YouTube](https://www.youtube.com/watch?v=COLOCAR_ID_DO_VIDEO_AQUI)",
        "",
        "### Galeria",
        "",
    ]

    if not imagens:
        md.append("> Nenhuma imagem encontrada em `Snapshots/` no momento.")
        return "\n".join(md)

    md.extend(["| Snapshot | Snapshot |", "|---|---|"])
    for i in range(0, len(imagens), 2):
        esquerda = imagens[i]
        direita = imagens[i + 1] if i + 1 < len(imagens) else None
        celula_esq = f'<img src="{caminho_md(esquerda, repo_root)}" alt="Snapshot {i + 1:02d}" width="420">'
        celula_dir = ""
        if direita is not None:
            celula_dir = f'<img src="{caminho_md(direita, repo_root)}" alt="Snapshot {i + 2:02d}" width="420">'
        md.append(f"| {celula_esq} | {celula_dir} |")

    return "\n".join(md)


# ============================================================
# SEÇÕES GERADAS DO README
# ============================================================
def gerar_secao_estatisticas(repo_root: Path) -> str:
    md: List[str] = [
        "## 3. Detalhes estatísticos",
        "",
        "Os números abaixo são atualizados automaticamente pelo `Ferramentas/AtualizadorReadMe.py` a partir dos arquivos atuais do projeto e do último relatório gerado.",
        "",
        "### Dados estatísticos do jogo",
        "",
        "| Categoria | Quantidade atual |",
        "|---|---:|",
    ]

    for nome, valor in coletar_estatisticas_jogo(repo_root):
        md.append(f"| {nome} | **{valor}** |")

    md.extend([
        "",
        "### Dados estatísticos do projeto",
        "",
        "| Categoria | Quantidade atual |",
        "|---|---:|",
    ])

    for nome, valor in coletar_estatisticas_projeto(repo_root):
        md.append(f"| {nome} | **{valor}** |")

    return "\n".join(md)


def gerar_secao_autor_site() -> str:
    return "\n".join([
        "## 5. Autor e Site",
        "",
        "- **Autor:** Leon Cunha Alvaro Lopez Soto",
        "- **Site oficial:** `COLOCAR_SITE_DO_GLOBAL_SERVER_AQUI`",
    ])


def montar_readme(readme_atual: str, repo_root: Path) -> str:
    cabecalho = extrair_prefixo(readme_atual)
    descricao = extrair_secao(
        readme_atual,
        "1. Descrição",
        "## 1. Descrição\n\nDescrição ainda não preenchida.",
    )
    features = extrair_secao(
        readme_atual,
        "4. Features principais e conceitos",
        "## 4. Features principais e conceitos\n\nFeatures ainda não preenchidas.",
    )

    partes = [
        cabecalho.strip(),
        descricao.strip(),
        "---",
        gerar_secao_snapshots(repo_root).strip(),
        gerar_secao_estatisticas(repo_root).strip(),
        features.strip(),
        "---",
        gerar_secao_autor_site().strip(),
    ]
    return "\n\n".join([p for p in partes if p]).rstrip() + "\n"


# ============================================================
# MAIN API
# ============================================================
def atualizar_readme(repo_root: Optional[Path | str] = None) -> Path:
    if repo_root is None:
        repo_root_path = Path(__file__).resolve().parent.parent
    else:
        repo_root_path = Path(repo_root).resolve()

    readme_path = repo_root_path / README_NOME
    if not readme_path.exists():
        raise FileNotFoundError(f"README não encontrado: {readme_path}")

    readme = ler_texto(readme_path)
    novo_readme = montar_readme(readme, repo_root_path)
    escrever_texto(readme_path, novo_readme)
    return readme_path


def main() -> None:
    path = atualizar_readme()
    print(f"README atualizado: {path}")


if __name__ == "__main__":
    main()
