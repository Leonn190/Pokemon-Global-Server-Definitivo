from __future__ import annotations

import unicodedata
from typing import Dict, Mapping, Tuple

CorRGB = Tuple[int, int, int]
PaletaTipo = Dict[str, CorRGB]


EFEITOS_ATAQUE_FPS: dict[str, float] = {
    'LabaredaMultipla': 31.25,
    'Corte': 10.2,
    'BolhasVerdes': 20,
    'CorteDourado': 10.87,
    'ChuvaVermelha': 31.25,
    'ChuvaBrilhante': 33.33,
    'Agua': 23.81,
    'AtemporalRosa': 40,
    'BarreiraCelular': 12.5,
    'ChicoteMultiplo': 13.89,
    'CorteDuploRoxo': 33.33,
    'CorteMagico': 25,
    'CorteRicocheteadoRoxo': 8.93,
    'CorteRosa': 25,
    'DomoVerde': 11.76,
    'EnergiaAzul': 15.38,
    'Engrenagem': 8.7,
    'EspiralAzul': 22.22,
    'Estouro': 10.31,
    'EstouroMagico': 20,
    'EstouroVermelho': 21.74,
    'Explosao': 22.22,
    'ExplosaoPedra': 10.87,
    'ExplosaoVerde': 8.93,
    'ExplosaoVermelha': 33.33,
    'ExplosaoRoxa': 9.52,
    'FacasAzuis': 35.71,
    'FacasBrancas': 26.32,
    'FacasColoridas': 31.25,
    'FacasRosas': 40,
    'FeixeMagenta': 23.81,
    'FeixeRoxo': 10.42,
    'FluxoAzul': 15.38,
    'Fogo': 10.53,
    'Fumaça': 28.57,
    'GasRoxo': 12.82,
    'Garra': 12.5,
    'HexagonoLaminas': 27.78,
    'ImpactoRochoso': 8.7,
    'Karate': 11.11,
    'LuaAmarela': 55.56,
    'MagiaAzul': 38.46,
    'MagiaMagenta': 20.83,
    'MarcaBrilhosa': 26.32,
    'MarcaAmarela': 19.23,
    'MarcaAzul': 26.32,
    'Mordida': 8.7,
    'MultiplasFacas': 27.78,
    'OrbesRoxos': 35.71,
    'PedaçoColorido': 26.32,
    'RaioAzul': 83.33,
    'RajadaAmarela': 28.57,
    'RasgoMagenta': 38.46,
    'RasgosRosa': 35.71,
    'RedemoinhoAzul': 26.32,
    'RedemoinhoCosmico': 10.53,
    'SuperDescarga': 12.2,
    'SuperNova': 31.25,
    'TirosAmarelos': 40,
    'TornadoAgua': 25.64,
}


_BASE_TIPOS: dict[str, CorRGB] = {
    "normal": (187, 176, 151),
    "fogo": (219, 106, 72),
    "agua": (80, 130, 219),
    "planta": (86, 171, 90),
    "eletrico": (224, 199, 61),
    "gelo": (152, 208, 225),
    "lutador": (168, 89, 71),
    "venenoso": (147, 92, 180),
    "terra": (164, 132, 73),
    "voador": (133, 168, 205),
    "psiquico": (217, 104, 146),
    "inseto": (140, 164, 63),
    "pedra": (128, 121, 107),
    "fantasma": (96, 90, 143),
    "dragao": (87, 97, 191),
    "sombrio": (86, 77, 76),
    "metal": (132, 145, 157),
    "fada": (220, 154, 196),
    "cosmico": (102, 105, 176),
    "sonoro": (198, 123, 219),
}

_ALIASES_TIPOS: dict[str, str] = {
    "agua": "agua",
    "aguas": "agua",
    "eletrico": "eletrico",
    "eletrica": "eletrico",
    "elétrico": "eletrico",
    "elétrica": "eletrico",
    "psiquico": "psiquico",
    "psíquico": "psiquico",
    "veneno": "venenoso",
    "venenoso": "venenoso",
    "dragao": "dragao",
    "dragão": "dragao",
    "aco": "metal",
    "aço": "metal",
    "steel": "metal",
    "dark": "sombrio",
    "fairy": "fada",
    "fire": "fogo",
    "water": "agua",
    "grass": "planta",
    "electric": "eletrico",
    "ice": "gelo",
    "fighting": "lutador",
    "poison": "venenoso",
    "ground": "terra",
    "flying": "voador",
    "psychic": "psiquico",
    "bug": "inseto",
    "rock": "pedra",
    "ghost": "fantasma",
    "dragon": "dragao",
    "normal": "normal",
    "cosmico": "cosmico",
    "cósmico": "cosmico",
    "sonoro": "sonoro",
}


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _clamp_rgb(valor: float) -> int:
    return max(0, min(255, int(round(valor))))


def _misturar(cor_a: CorRGB, cor_b: CorRGB, peso_b: float) -> CorRGB:
    peso_b = max(0.0, min(1.0, float(peso_b)))
    peso_a = 1.0 - peso_b
    return (
        _clamp_rgb(cor_a[0] * peso_a + cor_b[0] * peso_b),
        _clamp_rgb(cor_a[1] * peso_a + cor_b[1] * peso_b),
        _clamp_rgb(cor_a[2] * peso_a + cor_b[2] * peso_b),
    )


def _montar_paleta(cor_base: CorRGB) -> PaletaTipo:
    return {
        "base": cor_base,
        "clara": _misturar(cor_base, (255, 255, 255), 0.36),
        "brilho": _misturar(cor_base, (255, 255, 255), 0.62),
        "escura": _misturar(cor_base, (0, 0, 0), 0.28),
        "sombra": _misturar(cor_base, (0, 0, 0), 0.52),
    }


PALETAS_TIPOS_ATAQUE: dict[str, PaletaTipo] = {
    tipo: _montar_paleta(cor) for tipo, cor in _BASE_TIPOS.items()
}

CORES_TIPOS_ATAQUE: dict[str, CorRGB] = {
    tipo: paleta["base"] for tipo, paleta in PALETAS_TIPOS_ATAQUE.items()
}

# Compatibilidade com os módulos antigos que esperavam uma única cor por tipo.
PALETA_TIPOS_ATAQUE = CORES_TIPOS_ATAQUE


def normalizar_tipo_ataque(tipo: object, default: str = "normal") -> str:
    chave = _normalizar_nome(tipo)
    if not chave:
        return default
    return _ALIASES_TIPOS.get(chave, chave if chave in PALETAS_TIPOS_ATAQUE else default)


def obter_paleta_tipo(tipo: object, default: str = "normal") -> Mapping[str, CorRGB]:
    chave = normalizar_tipo_ataque(tipo, default=default)
    return PALETAS_TIPOS_ATAQUE.get(chave, PALETAS_TIPOS_ATAQUE[default])


def obter_cor_tipo(tipo: object, tom: str = "base", default: str = "normal") -> CorRGB:
    paleta = obter_paleta_tipo(tipo, default=default)
    return paleta.get(str(tom or "base"), paleta["base"])
