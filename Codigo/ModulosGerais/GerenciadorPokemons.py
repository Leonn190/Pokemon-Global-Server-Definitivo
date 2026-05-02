from __future__ import annotations

import unicodedata
from copy import deepcopy
from typing import Dict

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import (
    ganhar_xp_pokemon,
    aprender_ataque_aleatorio,
    evoluir_pokemon,
    materializar_pokemon,
    gerar_bando_confronto,
    subir_nivel_pokemon,
    criar_pokemon_inicial_materializado,
)

__all__ = [
    "ganhar_xp_pokemon",
    "aprender_ataque_aleatorio",
    "evoluir_pokemon",
    "materializar_pokemon",
    "gerar_bando_confronto",
    "subir_nivel_pokemon",
    "criar_pokemon_inicial_materializado",
    "buscar_equipavel",
    "atributos_equipavel",
    "definir_equipavel_slot",
    "retirar_equipavel_slot",
    "aplicar_bonus_equipavel",
    "remover_bonus_equipavel",
]

_ARQUIVO_EQUIPAVEIS = "Pokemon Global Server - Equipaveis.csv"
_BONUS_META = "_bonus_atributos_aplicado"
_CACHE_EQUIPAVEIS: dict[str, dict] | None = None


def _normalizar_busca(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def _normalizar_status(nome: object) -> str:
    texto = str(nome or "").strip()
    mapa = {
        "vida": "Vida",
        "spa": "SpA",
        "spd": "SpD",
        "ene": "Ene",
    }
    if texto == "EnR":
        return "EnR"
    return mapa.get(texto.lower(), texto)


def _float(valor: object, default: float = 0.0) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return float(default)


def _estado_pokemon(pokemon: dict | None) -> dict | None:
    if not isinstance(pokemon, dict):
        return None
    return pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon


def _equipaveis_por_nome() -> dict[str, dict]:
    global _CACHE_EQUIPAVEIS
    if _CACHE_EQUIPAVEIS is not None:
        return _CACHE_EQUIPAVEIS
    cache: dict[str, dict] = {}
    try:
        linhas = carregar_csv_dict(_ARQUIVO_EQUIPAVEIS, encoding="utf-8-sig")
    except OSError:
        linhas = []
    for linha in linhas:
        item = dict(linha)
        for chave in ("Nome", "Code"):
            valor = str(item.get(chave) or "").strip()
            if valor:
                cache[_normalizar_busca(valor)] = item
    _CACHE_EQUIPAVEIS = cache
    return cache


def buscar_equipavel(nome: str) -> dict | None:
    item = _equipaveis_por_nome().get(_normalizar_busca(nome))
    return dict(item) if isinstance(item, dict) else None


def atributos_equipavel(equipavel_ou_nome) -> dict[str, float]:
    equipavel = buscar_equipavel(equipavel_ou_nome) if isinstance(equipavel_ou_nome, str) else equipavel_ou_nome
    if not isinstance(equipavel, dict):
        return {}
    if not any(str(equipavel.get(f"Status {i}") or "").strip() for i in range(1, 5)):
        equipavel = buscar_equipavel(str(equipavel.get("Nome") or equipavel.get("nome") or equipavel.get("Code") or ""))
    if not isinstance(equipavel, dict):
        return {}
    atributos: dict[str, float] = {}
    for i in range(1, 5):
        status = _normalizar_status(equipavel.get(f"Status {i}"))
        if not status:
            continue
        aumento = _float(equipavel.get(f"Aumento {i}"), 0.0)
        if aumento:
            atributos[status] = atributos.get(status, 0.0) + aumento
    return atributos


def _garantir_build(estado: dict, indice: int) -> list:
    build = estado.get("BuildEquipaveis")
    if not isinstance(build, list):
        build = []
        estado["BuildEquipaveis"] = build
    while len(build) <= int(indice):
        build.append(None)
    return build


def _aplicar_delta(pokemon: dict, atributos: dict[str, float], sinal: float) -> None:
    estado = _estado_pokemon(pokemon)
    if estado is None:
        return
    for chave_stats in ("stats_base", "stats"):
        stats = estado.get(chave_stats)
        if not isinstance(stats, dict):
            stats = {}
            estado[chave_stats] = stats
        for nome, valor in atributos.items():
            stats[nome] = _float(stats.get(nome), 0.0) + (float(valor) * sinal)
    for nome, valor in atributos.items():
        if nome in estado:
            estado[nome] = _float(estado.get(nome), 0.0) + (float(valor) * sinal)
    _recalcular_campos_simples(estado)


def _recalcular_poder(stats: Dict[str, float]) -> float:
    vida = _float(stats.get("Vida"), 0.0)
    demais = sum(_float(v, 0.0) for k, v in stats.items() if k != "Vida")
    return round(vida + (demais * 2.0), 2)


def _recalcular_poder_relativo(stats: Dict[str, float]) -> float:
    ranking = []
    for chave, valor in stats.items():
        real = _float(valor, 0.0)
        relativo = (real / 2.0) if chave == "Vida" else real
        ranking.append((relativo, chave, real))
    ranking.sort(key=lambda x: x[0], reverse=True)
    total = 0.0
    for _, chave, real in ranking[:6]:
        total += real if chave == "Vida" else (real * 2.0)
    return round(total * 2.0, 2)


def _recalcular_campos_simples(estado: dict) -> None:
    stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
    if not stats:
        return
    poder = _recalcular_poder(stats)
    poder_relativo = _recalcular_poder_relativo(stats)
    for chave in ("poder", "Poder"):
        if chave in estado:
            estado[chave] = poder
    for chave in ("poder_relativo", "PoderRelativo"):
        if chave in estado:
            estado[chave] = poder_relativo


def aplicar_bonus_equipavel(pokemon: dict, equipavel: dict) -> None:
    if not isinstance(pokemon, dict) or not isinstance(equipavel, dict):
        return
    if isinstance(equipavel.get(_BONUS_META), dict):
        return
    bonus = atributos_equipavel(equipavel)
    if not bonus:
        return
    equipavel[_BONUS_META] = dict(bonus)
    _aplicar_delta(pokemon, bonus, 1.0)


def remover_bonus_equipavel(pokemon: dict, equipavel: dict) -> None:
    if not isinstance(pokemon, dict) or not isinstance(equipavel, dict):
        return
    bonus = equipavel.get(_BONUS_META)
    if isinstance(bonus, dict):
        bonus = dict(bonus)
    else:
        bonus = atributos_equipavel(equipavel)
    if not bonus:
        return
    _aplicar_delta(pokemon, bonus, -1.0)
    equipavel.pop(_BONUS_META, None)


def definir_equipavel_slot(pokemon: dict | None, indice: int, equipavel: dict | None) -> dict | None:
    estado = _estado_pokemon(pokemon)
    if estado is None:
        return None
    idx = int(indice)
    build = _garantir_build(estado, idx)
    anterior = build[idx]
    if isinstance(anterior, dict):
        remover_bonus_equipavel(estado, anterior)
    novo = deepcopy(equipavel) if isinstance(equipavel, dict) else None
    build[idx] = novo
    if isinstance(novo, dict):
        aplicar_bonus_equipavel(estado, novo)
    return anterior


def retirar_equipavel_slot(pokemon: dict | None, indice: int) -> dict | None:
    return definir_equipavel_slot(pokemon, indice, None)
