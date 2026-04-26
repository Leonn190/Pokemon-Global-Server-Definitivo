from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


README_NOME = "README.md"
REGISTRO_NOME = "Registro.md"

PASTAS_ARQUITETURA = [
    "Dados",
    "Codigo",
    "SimuladorServerJogo",
]

IGNORAR_PASTAS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "Relatorios",
    "RelatoriosLegado",
    "Relatorios atualizados",
}

IGNORAR_ARQUIVOS = {
    ".DS_Store",
    "Thumbs.db",
}

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
TOML_ESTRUTURAS = "SimuladorServerJogo/Logica/Regras/EstruturasNaturais.toml"


# ============================================================
# UTILITÁRIOS
# ============================================================
def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def ler_texto(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def escrever_texto(path: Path, texto: str) -> None:
    path.write_text(texto, encoding="utf-8")


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


def substituir_secao_por_titulo(readme: str, titulo: str, novo_conteudo: str) -> str:
    """Substitui uma seção Markdown de nível 2, do título informado até o próximo ##."""
    padrao = re.compile(
        rf"(^##\s+{re.escape(titulo)}\s*$)(.*?)(?=^##\s+|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    bloco = novo_conteudo.strip() + "\n\n"
    if padrao.search(readme):
        return padrao.sub(bloco, readme, count=1)

    if readme.endswith("\n"):
        return readme + "\n" + bloco
    return readme + "\n\n" + bloco


def substituir_entre_marcadores(readme: str, inicio: str, fim: str, conteudo: str) -> str:
    padrao = re.compile(
        rf"({re.escape(inicio)})(.*?)({re.escape(fim)})",
        flags=re.DOTALL,
    )
    novo_bloco = f"{inicio}\n\n{conteudo.strip()}\n\n{fim}"
    if padrao.search(readme):
        return padrao.sub(novo_bloco, readme, count=1)
    return readme.rstrip() + f"\n\n{novo_bloco}\n"


# ============================================================
# CONTADORES DE DADOS
# ============================================================
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

    # Os CSVs do projeto têm cabeçalho. O contador considera apenas registros.
    # Linhas exportadas com a primeira coluna vazia são tratadas como sobra de planilha.
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


def coletar_estatisticas(repo_root: Path) -> List[tuple[str, int]]:
    dados = repo_root / "Dados"
    return [
        (f"Pokémon cadastrados em `Dados/{CSV_POKEMONS}`", contar_csv_registros(dados / CSV_POKEMONS)),
        (f"Ataques cadastrados em `Dados/{CSV_ATAQUES}`", contar_csv_registros(dados / CSV_ATAQUES)),
        (f"Efeitos cadastrados em `Dados/{CSV_EFEITOS}`", contar_csv_registros(dados / CSV_EFEITOS)),
        (f"Itens cadastrados em `Dados/{CSV_ITENS}`", contar_csv_registros(dados / CSV_ITENS)),
        (f"Equipáveis cadastrados em `Dados/{CSV_EQUIPAVEIS}`", contar_csv_registros(dados / CSV_EQUIPAVEIS)),
        (
            "NPCs cadastrados",
            contar_csv_registros(dados / CSV_NPC_COMBATENTE) + contar_csv_registros(dados / CSV_NPC_VENDEDOR),
        ),
        ("Estruturas naturais", contar_estruturas_naturais(repo_root)),
        ("Trilhas sonoras", contar_trilhas_sonoras(repo_root)),
        ("Receitas", contar_json_dict(dados / JSON_RECEITAS)),
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
# ESTATÍSTICAS
# ============================================================
def gerar_secao_estatisticas(repo_root: Path) -> str:
    md: List[str] = [
        "## 3. Detalhes estatísticos",
        "",
        "Os números abaixo são atualizados automaticamente pelo `Outros/AtualizadorReadMe.py` a partir dos arquivos atuais do projeto.",
        "",
        "| Categoria | Quantidade atual |",
        "|---|---:|",
    ]

    for nome, valor in coletar_estatisticas(repo_root):
        md.append(f"| {nome} | **{fmt_int(int(valor))}** |")

    md.extend([
        "| Tipos de Pokémon | **20** |",
        "| Biomas | **7** |",
        "| Mundo planejado | **10.000 x 10.000 tiles** |",
        "",
        "Principais arquivos de dados:",
        "",
        f"- `Dados/{CSV_POKEMONS}`",
        f"- `Dados/{CSV_ATAQUES}`",
        f"- `Dados/{CSV_EFEITOS}`",
        f"- `Dados/{CSV_ITENS}`",
        f"- `Dados/{CSV_EQUIPAVEIS}`",
        f"- `Dados/{JSON_RECEITAS}`",
        "- `Dados/Pokemon Global Server - PropriedadesAtaques.json`",
        "- `Dados/Pokemon Global Server - Sistema FR.csv`",
    ])

    return "\n".join(md)


# ============================================================
# ARQUITETURA
# ============================================================
def deve_ignorar_path(path: Path) -> bool:
    if path.name in IGNORAR_ARQUIVOS:
        return True
    return any(parte in IGNORAR_PASTAS for parte in path.parts)


def listar_filhos_ordenados(pasta: Path) -> List[Path]:
    try:
        filhos = [p for p in pasta.iterdir() if not deve_ignorar_path(p)]
    except OSError:
        return []
    filhos.sort(key=lambda p: (not p.is_dir(), natural_key(p)))
    return filhos


def gerar_arvore(pasta: Path, prefixo: str = "") -> List[str]:
    filhos = listar_filhos_ordenados(pasta)
    linhas: List[str] = []

    for idx, filho in enumerate(filhos):
        ultimo = idx == len(filhos) - 1
        conector = "└── " if ultimo else "├── "
        nome = filho.name + ("/" if filho.is_dir() else "")
        linhas.append(f"{prefixo}{conector}{nome}")
        if filho.is_dir():
            novo_prefixo = prefixo + ("    " if ultimo else "│   ")
            linhas.extend(gerar_arvore(filho, novo_prefixo))

    return linhas


def gerar_bloco_arvore(repo_root: Path, nome_pasta: str) -> str:
    pasta = repo_root / nome_pasta
    if not pasta.exists() or not pasta.is_dir():
        return f"{nome_pasta}/\n└── (pasta não encontrada)"
    linhas = [f"{nome_pasta}/"]
    linhas.extend(gerar_arvore(pasta))
    return "\n".join(linhas)


def gerar_secao_arquitetura(repo_root: Path) -> str:
    md: List[str] = [
        "## 5. Arquitetura",
        "",
        "A arquitetura abaixo é atualizada automaticamente pelo `Outros/AtualizadorReadMe.py`, vasculhando as principais pastas do projeto.",
        "",
        "- `Codigo/`: cliente do jogo, interface, cenas, renderização, HUDs, telas e módulos visuais.",
        "- `Dados/`: base de dados do jogo, com CSVs e JSONs de Pokémon, ataques, itens, NPCs, receitas e interações.",
        "- `SimuladorServerJogo/`: servidor/simulador, regras, rotas, lógica autoritativa, mundo, batalha, geração e banco de dados.",
        "",
        "### Visão geral atualizada",
        "",
        "```text",
        ".",
    ]

    existentes = [p for p in PASTAS_ARQUITETURA if (repo_root / p).exists()]
    for idx, nome in enumerate(existentes):
        ultimo = idx == len(existentes) - 1
        conector = "└── " if ultimo else "├── "
        md.append(f"{conector}{nome}/")
    md.append("```")

    for nome in PASTAS_ARQUITETURA:
        md.extend(["", f"### `{nome}/`", "", "```text", gerar_bloco_arvore(repo_root, nome), "```"])

    return "\n".join(md)


# ============================================================
# REGISTRO
# ============================================================
def atualizar_registro_no_readme(readme: str, repo_root: Path) -> str:
    registro_path = repo_root / REGISTRO_NOME
    registro = ler_texto(registro_path).strip()
    if not registro:
        registro = f"> `{REGISTRO_NOME}` ainda não foi encontrado ou está vazio."

    return substituir_entre_marcadores(
        readme,
        "<!-- INICIO_REGISTRO_MD -->",
        "<!-- FIM_REGISTRO_MD -->",
        registro,
    )


# ============================================================
# MAIN API
# ============================================================
def atualizar_readme(repo_root: Optional[Path | str] = None) -> Path:
    if repo_root is None:
        # Arquivo esperado em Outros/AtualizadorReadMe.py.
        repo_root_path = Path(__file__).resolve().parent.parent
    else:
        repo_root_path = Path(repo_root).resolve()

    readme_path = repo_root_path / README_NOME
    if not readme_path.exists():
        raise FileNotFoundError(f"README não encontrado: {readme_path}")

    readme = ler_texto(readme_path)

    readme = substituir_secao_por_titulo(readme, "2. Snapshots", gerar_secao_snapshots(repo_root_path))
    readme = substituir_secao_por_titulo(readme, "3. Detalhes estatísticos", gerar_secao_estatisticas(repo_root_path))
    readme = substituir_secao_por_titulo(readme, "5. Arquitetura", gerar_secao_arquitetura(repo_root_path))
    readme = atualizar_registro_no_readme(readme, repo_root_path)

    escrever_texto(readme_path, readme.rstrip() + "\n")
    return readme_path


def main() -> None:
    path = atualizar_readme()
    print(f"README atualizado: {path}")


if __name__ == "__main__":
    main()
