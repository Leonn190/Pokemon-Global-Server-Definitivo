"""Gerador de Pokémon do servidor (baseado em Dados/Global server - Pokemons.csv)."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

from SimuladorServerJogo.Controle.ObjetosMundoServer import PokemonServer

ARQUIVO_POKEMONS = Path(__file__).resolve().parents[2] / "Dados" / "Global server - Pokemons.csv"
STATS_BASE = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int", "CrD", "CrC"]
STATS_VARIAVEIS_IV = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int"]


def _fnum(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _inum(v, default=0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return int(default)


def _nivel_baixo_comum(max_nivel: int = 60) -> int:
    r = random.random() ** 2.35
    return max(0, min(int(max_nivel), int(round(r * max_nivel))))


def _recalcular_total(stats: Dict[str, float]) -> float:
    vida = _fnum(stats.get("Vida"), 0.0)
    soma_basicos = sum(_fnum(stats.get(k), 0.0) for k in STATS_VARIAVEIS_IV if k != "Vida")
    crc = _fnum(stats.get("CrC"), 0.0)
    crd = _fnum(stats.get("CrD"), 0.0)
    return round(vida + (soma_basicos * 2.0) + ((crc + crd) * 3.0), 2)


def _gerar_subivs_media(iv_global: int) -> Dict[str, int]:
    alvo = max(0, min(100, int(iv_global)))
    subivs = {k: alvo for k in STATS_VARIAVEIS_IV}
    for k in STATS_VARIAVEIS_IV:
        subivs[k] = max(0, min(100, alvo + random.randint(-24, 24)))

    soma_alvo = alvo * len(STATS_VARIAVEIS_IV)
    diff = soma_alvo - sum(subivs.values())
    while diff != 0:
        alterado = False
        ordem = STATS_VARIAVEIS_IV[:]
        random.shuffle(ordem)
        passo = 1 if diff > 0 else -1
        for k in ordem:
            if diff == 0:
                break
            nv = subivs[k] + passo
            if 0 <= nv <= 100:
                subivs[k] = nv
                diff -= passo
                alterado = True
        if not alterado:
            break
    return subivs


def _sortear_tipos(row: Dict[str, str]) -> List[str]:
    tipos: List[str] = []
    tipo1 = str(row.get("Tipo1", "") or "").strip()
    for idx in (1, 2, 3):
        tipo = str(row.get(f"Tipo{idx}", "") or "").strip()
        chance = max(0.0, min(100.0, _fnum(row.get(f"%{idx}"), 0.0)))
        if tipo and random.random() <= (chance / 100.0):
            tipos.append(tipo)
    if not tipos and tipo1:
        tipos.append(tipo1)
    return tipos


def subir_nivel_pokemon(pokemon: Dict[str, object], vezes: int = 1) -> Dict[str, object]:
    dados = pokemon if isinstance(pokemon, dict) else {}
    estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else dados
    stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
    stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}
    nivel_atual = max(0, min(100, _inum(estado.get("nivel", 0), 0)))

    ordem = STATS_VARIAVEIS_IV[:]
    for _ in range(max(0, int(vezes))):
        if nivel_atual >= 100:
            break
        stat = ordem[nivel_atual % len(ordem)]
        base = _fnum(stats_base.get(stat), _fnum(stats.get(stat), 0.0))
        stats[stat] = round(_fnum(stats.get(stat), base) + (base * 0.10), 2)
        nivel_atual += 1
        estado["nivel"] = nivel_atual
        estado["total"] = _recalcular_total(stats)
    estado["stats"] = stats
    return dados


def materializar_pokemon(pokemon_mundo: Dict[str, object], efeitos_captura: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    bruto = dict(pokemon_mundo or {})
    estado = bruto.get("estado") if isinstance(bruto.get("estado"), dict) else bruto
    efeitos = efeitos_captura if isinstance(efeitos_captura, dict) else {}

    nivel_original = max(0, min(100, _inum(estado.get("nivel", 0), 0)))
    bonus_nivel = _inum(efeitos.get("bonus_nivel", 0), 0)
    bonus_iv = _inum(efeitos.get("bonus_iv", 0), 0)
    bonus_amizade = _inum(efeitos.get("bonus_amizade", 0), 0)

    iv = max(0, min(100, _inum(estado.get("iv", 0), 0) + bonus_iv))
    dados_csv = estado.get("dados_csv", {}) if isinstance(estado.get("dados_csv"), dict) else {}
    stats_base = {}
    stats_base_origem = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}
    for k in STATS_BASE:
        stats_base[k] = _fnum(stats_base_origem.get(k), _fnum(dados_csv.get(k), _fnum(estado.get(k), 0.0)))

    subivs = _gerar_subivs_media(iv)
    stats_final = {}
    for stat in STATS_VARIAVEIS_IV:
        base = _fnum(stats_base.get(stat), 0.0)
        mult = 0.75 + (_inum(subivs.get(stat), iv) / 200.0)
        stats_final[stat] = round(base * mult, 2)
    stats_final["CrC"] = round(_fnum(stats_base.get("CrC"), 0.0), 2)
    stats_final["CrD"] = round(_fnum(stats_base.get("CrD"), 0.0), 2)

    amizade_base = random.randint(15, 70) + bonus_amizade
    amizade = max(1, amizade_base - nivel_original)

    estado["iv"] = iv
    estado["subivs"] = subivs
    estado["stats_base"] = stats_base
    estado["stats"] = stats_final
    estado["amizade"] = int(amizade)
    estado["tipos"] = _sortear_tipos(dados_csv)
    estado["nivel"] = 0
    estado["total"] = _recalcular_total(stats_final)

    subir_nivel_pokemon(estado, vezes=max(0, min(100, nivel_original + bonus_nivel)))
    return bruto


MaterializarPokemon = materializar_pokemon
SubirNivel = subir_nivel_pokemon


def _carregar_base() -> List[Dict[str, object]]:
    if not ARQUIVO_POKEMONS.exists():
        return []
    linhas: List[Dict[str, object]] = []
    with ARQUIVO_POKEMONS.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row.get("Nome"):
                continue
            raridade_raw = str(row.get("Raridade", "")).strip()
            if not raridade_raw:
                continue
            raridade = _fnum(raridade_raw, 0.0)
            if raridade < 1.0 or raridade > 10.0:
                continue
            linhas.append({"row": row, "peso_spawn": 1.0 / raridade})
    return linhas


_BASE_POKEMONS = _carregar_base()


def _escolher_especie(especie=None) -> Dict[str, str]:
    if not _BASE_POKEMONS:
        return {"Nome": "MissingNo", "Raridade": "10", "Altura": "1.0", "Peso": "1.0", **{k: "10" for k in STATS_BASE}}
    alvo = str(especie or "").strip().lower()
    if alvo:
        for item in _BASE_POKEMONS:
            row = item.get("row", {}) if isinstance(item, dict) else {}
            if str(row.get("Code", "")).strip().lower() == alvo or str(row.get("Nome", "")).strip().lower() == alvo:
                return row
    item = random.choices(_BASE_POKEMONS, weights=[x["peso_spawn"] for x in _BASE_POKEMONS], k=1)[0]
    return item["row"]


def gerar_pokemon_server(novo_id: int, posicao, chunk_xy, especie=None) -> PokemonServer:
    row = _escolher_especie(especie)
    iv_global = random.randint(0, 100)
    nivel = _nivel_baixo_comum(60)

    coef_genetico = random.uniform(0.5, 1.5)
    coef_altura = random.uniform(0.75, 1.25)
    coef_peso = random.uniform(0.75, 1.25)

    altura_base = _fnum(row.get("Altura"), 1.0)
    peso_base = _fnum(row.get("Peso"), 1.0)
    altura = round(altura_base * coef_genetico * coef_altura, 3)
    peso = round(peso_base * coef_genetico * coef_peso, 3)

    total_csv = _fnum(row.get("Total"), 0.0)
    dificuldade = round(total_csv * (iv_global / 100.0) * (nivel / 10.0), 2)
    tamanho_barra = round(max(0.05, 0.46 - (nivel / 160.0)), 3)
    velocidade_barra = round(min(260.0, 40.0 + (iv_global * 1.7)), 2)

    poke = PokemonServer(id_objeto=novo_id, especie=str(row.get("Nome", "Desconhecido")), posicao=posicao)
    poke.estado_extra.update(
        {
            "nivel": nivel,
            "iv": iv_global,
            "subivs": {},
            "altura": altura,
            "peso": peso,
            "coeficiente_genetico": round(coef_genetico, 5),
            "coeficiente_altura": round(coef_altura, 5),
            "coeficiente_peso": round(coef_peso, 5),
            "tipos": [],
            "grupo": str(row.get("Grupo", "")),
            "raridade": int(_fnum(row.get("Raridade"), 1)),
            "estagio": int(_fnum(row.get("Estagio"), 1)),
            "code": str(row.get("Code", "")),
            "linhagem": str(row.get("Linhagem", "")),
            "total_csv": total_csv,
            "total": total_csv,
            "dificuldade_captura": dificuldade,
            "tamanho_barra_captura": tamanho_barra,
            "velocidade_barra_captura": velocidade_barra,
            "chunk_origem": [int(chunk_xy[0]), int(chunk_xy[1])],
            "dados_csv": dict(row),
        }
    )
    return poke
