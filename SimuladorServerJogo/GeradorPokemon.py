"""Gerador de Pokémon do servidor (baseado em Dados/Global server - Pokemons.csv)."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List

from SimuladorServerJogo.ObjetosMundoServer import PokemonServer

ARQUIVO_POKEMONS = Path(__file__).resolve().parents[1] / "Dados" / "Global server - Pokemons.csv"
STATS_BASE = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "EnR", "CrD", "CrC"]


class GeradorPokemonServer:
    def __init__(self) -> None:
        self._base = self._carregar_base()

    @staticmethod
    def _fnum(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(default)

    def _carregar_base(self) -> List[Dict[str, object]]:
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
                raridade = self._fnum(raridade_raw, 0.0)
                if raridade < 1.0 or raridade > 10.0:
                    continue
                peso = 1.0 / raridade
                linhas.append({"row": row, "peso_spawn": peso})
        return linhas

    def _escolher_especie(self) -> Dict[str, str]:
        if not self._base:
            return {"Nome": "MissingNo", "Raridade": "10", "Altura": "1.0", "Peso": "1.0", **{k: "10" for k in STATS_BASE}}
        item = random.choices(self._base, weights=[x["peso_spawn"] for x in self._base], k=1)[0]
        return item["row"]

    def gerar(self, novo_id: int, posicao, chunk_xy) -> PokemonServer:
        row = self._escolher_especie()
        iv_global = random.randint(0, 100)
        nivel = max(1, min(100, int(1 + (iv_global / 100.0) * 99)))

        stats_base = {k: self._fnum(row.get(k), 1.0) for k in STATS_BASE}
        subivs: Dict[str, int] = {}
        stats_final: Dict[str, float] = {}
        for stat, base in stats_base.items():
            subiv = random.randint(0, 100)
            subivs[stat] = subiv
            fator = 0.8 + (subiv / 100.0) * 0.4
            stats_final[stat] = round(base * fator, 2)

        altura_base = self._fnum(row.get("Altura"), 1.0)
        peso_base = self._fnum(row.get("Peso"), 1.0)
        altura = round(altura_base * random.uniform(0.7, 1.3), 3)
        peso = round(peso_base * random.uniform(0.7, 1.3), 3)

        tipos = []
        for idx in (1, 2, 3):
            tipo = str(row.get(f"Tipo{idx}", "") or "").strip()
            chance = max(0.0, min(100.0, self._fnum(row.get(f"%{idx}"), 0.0)))
            if tipo and random.random() <= (chance / 100.0):
                tipos.append(tipo)

        poke = PokemonServer(id_objeto=novo_id, especie=str(row.get("Nome", "Desconhecido")), posicao=posicao)
        poke.estado_extra.update(
            {
                "nivel": nivel,
                "iv": iv_global,
                "subivs": subivs,
                "stats_base": stats_base,
                "stats": stats_final,
                "altura": altura,
                "peso": peso,
                "tipos": tipos,
                "grupo": str(row.get("Grupo", "")),
                "raridade": int(self._fnum(row.get("Raridade"), 1)),
                "estagio": int(self._fnum(row.get("Estagio"), 1)),
                "code": str(row.get("Code", "")),
                "linhagem": str(row.get("Linhagem", "")),
                "chunk_origem": [int(chunk_xy[0]), int(chunk_xy[1])],
            }
        )
        return poke


GERADOR_POKEMON_SERVER = GeradorPokemonServer()
