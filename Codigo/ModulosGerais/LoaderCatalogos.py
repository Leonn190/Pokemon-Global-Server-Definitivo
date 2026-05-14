from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parents[2]
_PASTA_CATALOGOS = _RAIZ / "Dados" / "Catalogos"
_cache_catalogos: dict[str, dict[str, Any]] = {}

_ALIAS_ARQUIVOS = {
    "baus": "Pokemon Global Server - Baus.json",
    "pokemon global server - baus": "Pokemon Global Server - Baus.json",
    "receitas": "Pokemon Global Server - Receitas.json",
    "pokemon global server - receitas": "Pokemon Global Server - Receitas.json",
}


def _nome_arquivo(nome: str | Path) -> str:
    nome_path = Path(str(nome))
    texto = str(nome_path).strip()
    if nome_path.suffix.lower() == ".json":
        return nome_path.name
    return _ALIAS_ARQUIVOS.get(texto.casefold(), f"{texto}.json")


def caminho_catalogo(nome: str | Path) -> Path:
    nome_path = Path(str(nome))
    if nome_path.is_absolute():
        return nome_path
    return _PASTA_CATALOGOS / _nome_arquivo(nome)


def carregar_catalogo(nome: str | Path) -> dict[str, Any]:
    caminho = caminho_catalogo(nome)
    chave = str(caminho.resolve()) if caminho.exists() else str(caminho)
    if chave in _cache_catalogos:
        return _cache_catalogos[chave]
    if not caminho.exists():
        print(f"[Catalogos] Arquivo nao encontrado: {caminho}")
        _cache_catalogos[chave] = {}
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[Catalogos] Falha ao carregar {caminho}: {exc}")
        dados = {}
    catalogo = dados if isinstance(dados, dict) else {}
    _cache_catalogos[chave] = catalogo
    return catalogo


def obter_catalogo(nome: str | Path) -> dict[str, Any]:
    return carregar_catalogo(nome)


def limpar_cache_catalogos() -> None:
    _cache_catalogos.clear()
