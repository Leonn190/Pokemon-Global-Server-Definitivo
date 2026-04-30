from __future__ import annotations

import json
import random
from pathlib import Path
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from typing import Dict, List

CAMINHO_BAUS_JSON = Path(__file__).resolve().parents[3] / "Dados" / "Catalogo" / "Pokemon Global Server - Baus.json"

_CHANCES_QTD_ITENS = {
    1: 30.0,
    2: 25.0,
    3: 25.0,
    4: 20.0,
}

_TAMANHO_BAU_POR_QTD = {
    1: 0.90,
    2: 1.10,
    3: 1.30,
    4: 1.50,
}


def _fnum(v, default=0.0):
    try:
        return float(str(v or "").strip().replace("%", ""))
    except (TypeError, ValueError):
        return float(default)


def _escolher_por_peso(rng: random.Random, pesos: Dict[object, float]):
    chaves = []
    valores = []
    for chave, peso in pesos.items():
        peso = float(peso)
        if peso > 0:
            chaves.append(chave)
            valores.append(peso)
    return rng.choices(chaves, weights=valores, k=1)[0]


def _carregar_tabela_baus() -> Dict[int, Dict[str, object]]:
    with CAMINHO_BAUS_JSON.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    return {
        int(dia): {
            "chance_tipos": {tipo: _fnum(info.get("chance")) for tipo, info in bloco.items()},
            "chance_raridade_por_tipo": {tipo: {int(r): _fnum(p) for r, p in info.get("raridades", {}).items()} for tipo, info in bloco.items()},
        }
        for dia, bloco in dados.items()
    }


def _carregar_itens_validos() -> Dict[int, List[Dict[str, object]]]:
    itens_por_raridade: Dict[int, List[Dict[str, object]]] = {i: [] for i in range(1, 7)}

    for linha in carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8"):
            entra_bau = str(linha.get("Bau", "")).strip().lower()
            if entra_bau and entra_bau != "s":
                continue
            raridade = int(_fnum(linha.get("Raridade"), 0))
            if raridade < 1 or raridade > 6:
                continue

            nome = str(linha.get("Nome", "")).strip()
            if not nome:
                continue

            code = str(linha.get("Code", "")).strip() or nome.lower().replace(" ", "_")

            itens_por_raridade[raridade].append(
                {
                    "Nome": nome,
                    "Descrição": str(linha.get("Descrição", "")).strip(),
                    "Raridade": raridade,
                    "Estilo": str(linha.get("Estilo", "")).strip(),
                    "Code": code,
                    "Stacks": int(_fnum(linha.get("Stacks"), 1)),
                    "quantidade": 1,
                }
            )

    return itens_por_raridade


_TABELA_BAUS = _carregar_tabela_baus()
_ITENS_VALIDOS = _carregar_itens_validos()


def _sortear_quantidade_itens(rng: random.Random) -> int:
    return int(_escolher_por_peso(rng, _CHANCES_QTD_ITENS))


def tamanho_bau_por_qtd(qtd_itens: int) -> float:
    qtd = max(1, min(4, int(qtd_itens or 1)))
    return float(_TAMANHO_BAU_POR_QTD[qtd])


def gerar_bau_server(rng: random.Random, dia_fixo: int = 0, tipo_forcado: str | None = None) -> Dict[str, object]:
    dia_fixo = int(dia_fixo)
    dias_disponiveis = sorted(_TABELA_BAUS.keys())
    dia_escolhido = max((d for d in dias_disponiveis if d <= dia_fixo), default=dias_disponiveis[0])
    bloco = _TABELA_BAUS[dia_escolhido]

    tipo = str(tipo_forcado or "").strip().capitalize()
    if not tipo:
        tipo = _escolher_por_peso(rng, bloco["chance_tipos"])

    chance_raridade = bloco["chance_raridade_por_tipo"][tipo]

    qtd_itens = _sortear_quantidade_itens(rng)
    itens = []
    usados = set()

    while len(itens) < qtd_itens:
        raridade = int(_escolher_por_peso(rng, chance_raridade))
        pool = [item for item in _ITENS_VALIDOS[raridade] if item["Code"] not in usados]
        if not pool:
            continue

        escolhido = dict(rng.choice(pool))
        usados.add(escolhido["Code"])
        itens.append(escolhido)

    quantidade_real = len(itens)
    tamanho_tiles = tamanho_bau_por_qtd(quantidade_real)
    raio_colisao = max(0.42, tamanho_tiles * 0.32)
    raio_interacao = max(0.85, raio_colisao + 0.45)

    return {
        "tipo_bau": tipo,
        "itens": itens,
        "quantidade_itens": quantidade_real,
        "tamanho_tiles": tamanho_tiles,
        "raio_colisao": raio_colisao,
        "raio_interacao": raio_interacao,
    }
