from __future__ import annotations

import csv
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[2]
_PASTA_TABELAS = _RAIZ / "Dados" / "Tabelas"
_cache_dict: dict[str, list[dict]] = {}
_cache_lista: dict[str, list[list[str]]] = {}


def caminho_tabela(nome: str | Path) -> Path:
    nome_path = Path(str(nome))
    return nome_path if nome_path.is_absolute() else _PASTA_TABELAS / nome_path


def carregar_csv_dict(nome: str | Path, *, encoding: str = "utf-8-sig", delimiter: str = ",") -> list[dict]:
    chave = f"{nome}|{encoding}|{delimiter}"
    if chave in _cache_dict:
        return [dict(l) for l in _cache_dict[chave]]
    caminho = caminho_tabela(nome)
    with caminho.open("r", encoding=encoding, newline="") as arquivo:
        linhas = [dict(linha) for linha in csv.DictReader(arquivo, delimiter=delimiter)]
    _cache_dict[chave] = [dict(l) for l in linhas]
    return linhas


def carregar_csv_lista(nome: str | Path, *, encoding: str = "utf-8-sig", delimiter: str = ",") -> list[list[str]]:
    chave = f"{nome}|{encoding}|{delimiter}"
    if chave in _cache_lista:
        return [list(l) for l in _cache_lista[chave]]
    caminho = caminho_tabela(nome)
    with caminho.open("r", encoding=encoding, newline="") as arquivo:
        linhas = [list(linha) for linha in csv.reader(arquivo, delimiter=delimiter)]
    _cache_lista[chave] = [list(l) for l in linhas]
    return linhas
