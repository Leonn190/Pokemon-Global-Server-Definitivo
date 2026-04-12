from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Dict, Iterable


_BASE_DADOS = Path(__file__).resolve().parents[2] / "Dados"
_ARQUIVO_FR = _BASE_DADOS / "Pokemon Global Server - Sistema FR.csv"

_CACHE_FR: dict[str, dict[str, float]] | None = None

_ALIAS_TIPOS = {
    "normal": "normal",
    "fogo": "fogo",
    "fire": "fogo",
    "agua": "agua",
    "water": "agua",
    "eletrico": "eletrico",
    "electric": "eletrico",
    "planta": "planta",
    "grass": "planta",
    "gelo": "gelo",
    "ice": "gelo",
    "lutador": "lutador",
    "fighting": "lutador",
    "venenoso": "venenoso",
    "poison": "venenoso",
    "terrestre": "terrestre",
    "ground": "terrestre",
    "voador": "voador",
    "flying": "voador",
    "psiquico": "psiquico",
    "psychic": "psiquico",
    "inseto": "inseto",
    "bug": "inseto",
    "pedra": "pedra",
    "rock": "pedra",
    "fantasma": "fantasma",
    "ghost": "fantasma",
    "dragao": "dragao",
    "dragon": "dragao",
    "sombrio": "sombrio",
    "dark": "sombrio",
    "metal": "metal",
    "steel": "metal",
    "fada": "fada",
    "fairy": "fada",
    "sonoro": "sonoro",
    "sound": "sonoro",
    "cosmico": "cosmico",
    "cosmic": "cosmico",
}


def _normalizar_texto(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return sem_acento.replace(" ", "").replace("-", "").replace("_", "")


def _fnum(valor: object, default: float = 1.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def normalizar_tipo(tipo: object) -> str:
    return _ALIAS_TIPOS.get(_normalizar_texto(tipo), _normalizar_texto(tipo))


def carregar_tabela_fr() -> Dict[str, Dict[str, float]]:
    global _CACHE_FR
    if _CACHE_FR is not None:
        return _CACHE_FR

    tabela: Dict[str, Dict[str, float]] = {}
    if not _ARQUIVO_FR.exists():
        _CACHE_FR = tabela
        return tabela

    with _ARQUIVO_FR.open("r", encoding="utf-8-sig", newline="") as arquivo:
        for row in csv.DictReader(arquivo):
            ataque = normalizar_tipo(row.get("ataque\\defesa"))
            if not ataque:
                continue
            linha: Dict[str, float] = {}
            for chave, valor in dict(row).items():
                defesa = normalizar_tipo(chave)
                if not defesa or defesa == ataque:
                    continue
                linha[defesa] = _fnum(valor, 1.0)
            tabela[ataque] = linha

    _CACHE_FR = tabela
    return tabela


def modificador_tipo(tipo_ataque: object, tipos_alvo: Iterable[object] | None = None) -> float:
    tabela = carregar_tabela_fr()
    ataque = normalizar_tipo(tipo_ataque)
    modificador = 1.0
    for tipo in list(tipos_alvo or []):
        defesa = normalizar_tipo(tipo)
        modificador *= float(tabela.get(ataque, {}).get(defesa, 1.0))
    return float(modificador)
