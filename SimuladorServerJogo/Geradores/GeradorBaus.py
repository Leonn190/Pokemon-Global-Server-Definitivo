from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

TIPOS_ORDEM = ("Comum", "Incomum", "Raro", "Epico", "Lendario", "Mitico")
_RAIZ_DADOS = Path(__file__).resolve().parents[2] / "Dados"


def _parse_percent(valor: str) -> float:
    texto = str(valor or "").strip().replace("%", "")
    if not texto:
        return 0.0
    try:
        return max(0.0, float(texto))
    except ValueError:
        return 0.0


def _carregar_tabela_baus(arquivo_baus: Path) -> Dict[int, Dict[str, object]]:
    tabela: Dict[int, Dict[str, object]] = {}
    dia_atual: Optional[int] = None
    with arquivo_baus.open("r", encoding="utf-8") as f:
        for linha in csv.reader(f):
            colunas = [str(c or "").strip() for c in linha]
            tokens = [c for c in colunas if c]
            if not tokens:
                continue
            if tokens[0].lower().startswith("dia"):
                try:
                    dia_atual = int(tokens[0].split(" ")[1])
                except Exception:
                    dia_atual = None
                if dia_atual is not None and dia_atual not in tabela:
                    tabela[dia_atual] = {"chance_tipos": {}, "chance_raridade_por_tipo": {}}
                continue
            if dia_atual is None or tokens[0].lower() == "bau" or tokens[0] not in TIPOS_ORDEM:
                continue
            tipo = tokens[0]
            pesos_raridade = {idx + 1: _parse_percent(tokens[2 + idx] if len(tokens) > (2 + idx) else "0") for idx in range(6)}
            tabela[dia_atual]["chance_tipos"][tipo] = _parse_percent(tokens[1]) if len(tokens) > 1 else 0.0
            tabela[dia_atual]["chance_raridade_por_tipo"][tipo] = pesos_raridade
    return tabela


def _carregar_itens_validos(arquivo_itens: Path) -> Dict[int, List[Dict[str, object]]]:
    itens_por_raridade: Dict[int, List[Dict[str, object]]] = {k: [] for k in range(1, 7)}
    with arquivo_itens.open("r", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            if not isinstance(linha, dict):
                continue
            raridade_raw = str(linha.get("Raridade", "")).strip()
            if not raridade_raw.isdigit():
                continue
            raridade = int(raridade_raw)
            if 1 <= raridade <= 6:
                itens_por_raridade[raridade].append(
                    {
                        "Nome": str(linha.get("Nome", "")).strip(),
                        "Descrição": str(linha.get("Descrição", "")).strip(),
                        "Raridade": raridade,
                        "Estilo": str(linha.get("Estilo", "")).strip(),
                        "Code": str(linha.get("Code", "")).strip(),
                    }
                )
    return itens_por_raridade


def _escolher_por_peso(rng: random.Random, pesos: Dict[object, float]):
    opcoes = [(k, max(0.0, float(v))) for k, v in pesos.items() if float(v) > 0.0]
    if not opcoes:
        return None
    alvo, acumulado = rng.uniform(0.0, sum(v for _, v in opcoes)), 0.0
    for chave, peso in opcoes:
        acumulado += peso
        if acumulado >= alvo:
            return chave
    return opcoes[-1][0]


_ARQUIVO_BAUS = _RAIZ_DADOS / "Global server - Baus.csv"
_ARQUIVO_ITENS = _RAIZ_DADOS / "Global server - Itens.csv"
_TABELA_BAUS = _carregar_tabela_baus(_ARQUIVO_BAUS)
_ITENS_VALIDOS = _carregar_itens_validos(_ARQUIVO_ITENS)


def gerar_bau_server(rng: random.Random, dia_fixo: int = 1, tipo_forcado: str | None = None) -> Dict[str, object]:
    dias = sorted(_TABELA_BAUS.keys())
    if not dias:
        return {"tipo_bau": "Comum", "itens": []}
    dia = dias[min(len(dias) - 1, max(1, int(dia_fixo)) - 1)]
    bloco = _TABELA_BAUS.get(dia, {}) if isinstance(_TABELA_BAUS.get(dia, {}), dict) else {}

    tipo_fixado = str(tipo_forcado or "").strip().capitalize()
    tipo = tipo_fixado if tipo_fixado in TIPOS_ORDEM else (_escolher_por_peso(rng, bloco.get("chance_tipos", {})) or "Comum")
    tabela_tipo = bloco.get("chance_raridade_por_tipo", {}) if isinstance(bloco.get("chance_raridade_por_tipo", {}), dict) else {}
    chance_raridade = tabela_tipo.get(tipo, {}) if isinstance(tabela_tipo.get(tipo, {}), dict) else {}

    qtd_itens, usados, itens, tentativas = rng.randint(1, 3), set(), [], 0
    while len(itens) < qtd_itens and tentativas < 50:
        tentativas += 1
        raridade = _escolher_por_peso(rng, chance_raridade)
        if raridade is None:
            break
        pool = [item for item in _ITENS_VALIDOS.get(int(raridade), []) if item.get("Code") not in usados]
        if not pool:
            continue
        escolhido = dict(rng.choice(pool))
        usados.add(escolhido.get("Code"))
        itens.append(escolhido)

    if not itens:
        for raridade in range(1, 7):
            pool = [item for item in _ITENS_VALIDOS.get(raridade, []) if item.get("Code") not in usados]
            if pool:
                itens.append(dict(rng.choice(pool)))
                break

    return {"tipo_bau": str(tipo), "itens": itens[:3]}
