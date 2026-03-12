from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

TIPOS_ORDEM = ("Comum", "Incomum", "Raro", "Epico", "Lendario", "Mitico")
_CHANCES_QTD_ITENS = {1: 30.0, 2: 25.0, 3: 25.0, 4: 20.0}
_TAMANHO_BAU_POR_QTD = {1: 1.10, 2: 1.35, 3: 1.65, 4: 2.00}
_FALLBACK_ITENS = {
    1: [
        {"Nome": "Pokeball", "Descrição": "Esfera simples de captura.", "Raridade": 1, "Estilo": "bola", "Code": "pokeball", "quantidade": 1},
        {"Nome": "Poção", "Descrição": "Recupera um pouco de vida.", "Raridade": 1, "Estilo": "poção", "Code": "pocao", "quantidade": 1},
        {"Nome": "Fruta", "Descrição": "Fruta comum para interação com Pokémon.", "Raridade": 1, "Estilo": "fruta", "Code": "fruta", "quantidade": 1},
    ],
    2: [
        {"Nome": "Greatball", "Descrição": "Melhor chance de captura.", "Raridade": 2, "Estilo": "bola", "Code": "greatball", "quantidade": 1},
        {"Nome": "Super Poção", "Descrição": "Recupera mais vida.", "Raridade": 2, "Estilo": "poção", "Code": "super_pocao", "quantidade": 1},
        {"Nome": "Super Fruta", "Descrição": "Fruta reforçada.", "Raridade": 2, "Estilo": "fruta", "Code": "super_fruta", "quantidade": 1},
    ],
    3: [
        {"Nome": "Ultraball", "Descrição": "Alta chance de captura.", "Raridade": 3, "Estilo": "bola", "Code": "ultraball", "quantidade": 1},
        {"Nome": "Hiper Poção", "Descrição": "Recupera bastante vida.", "Raridade": 3, "Estilo": "poção", "Code": "hiper_pocao", "quantidade": 1},
    ],
    4: [
        {"Nome": "Revival", "Descrição": "Reanima um Pokémon.", "Raridade": 4, "Estilo": "poção", "Code": "revival", "quantidade": 1},
        {"Nome": "Mega Fruta", "Descrição": "Fruta rara de captura.", "Raridade": 4, "Estilo": "fruta", "Code": "mega_fruta", "quantidade": 1},
    ],
    5: [
        {"Nome": "Master Fruit", "Descrição": "Fruta lendária de apoio à captura.", "Raridade": 5, "Estilo": "fruta", "Code": "master_fruit", "quantidade": 1},
    ],
    6: [
        {"Nome": "Relíquia Mítica", "Descrição": "Item mítico raro.", "Raridade": 6, "Estilo": "reliquia", "Code": "reliquia_mitica", "quantidade": 1},
    ],
}


def _resolver_raiz_dados() -> Path:
    aqui = Path(__file__).resolve()
    candidatos = [
        aqui.parents[2] / "Dados",
        aqui.parents[1] / "Dados",
        aqui.parents[0] / "Dados",
        Path.cwd() / "Dados",
    ]
    for cand in candidatos:
        if cand.exists():
            return cand
    return candidatos[0]


_RAIZ_DADOS = _resolver_raiz_dados()


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
    if not arquivo_baus.exists():
        return tabela
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
    if not arquivo_itens.exists():
        return {k: [dict(item) for item in _FALLBACK_ITENS.get(k, [])] for k in range(1, 7)}
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
                        "quantidade": 1,
                    }
                )
    for raridade in range(1, 7):
        if not itens_por_raridade[raridade]:
            itens_por_raridade[raridade] = [dict(item) for item in _FALLBACK_ITENS.get(raridade, [])]
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


def _fallback_chance_tipos() -> Dict[str, float]:
    return {"Comum": 42.0, "Incomum": 24.0, "Raro": 16.0, "Epico": 10.0, "Lendario": 6.0, "Mitico": 2.0}


def _fallback_raridade_por_tipo(tipo: str) -> Dict[int, float]:
    base = {
        "Comum": {1: 60.0, 2: 26.0, 3: 10.0, 4: 3.0, 5: 1.0, 6: 0.2},
        "Incomum": {1: 35.0, 2: 35.0, 3: 18.0, 4: 8.0, 5: 3.0, 6: 1.0},
        "Raro": {1: 18.0, 2: 30.0, 3: 28.0, 4: 15.0, 5: 7.0, 6: 2.0},
        "Epico": {1: 8.0, 2: 18.0, 3: 30.0, 4: 24.0, 5: 14.0, 6: 6.0},
        "Lendario": {1: 4.0, 2: 10.0, 3: 18.0, 4: 28.0, 5: 25.0, 6: 15.0},
        "Mitico": {1: 2.0, 2: 6.0, 3: 12.0, 4: 20.0, 5: 28.0, 6: 32.0},
    }
    return dict(base.get(str(tipo), base["Comum"]))


def _sortear_quantidade_itens(rng: random.Random) -> int:
    return int(_escolher_por_peso(rng, _CHANCES_QTD_ITENS) or 1)


def tamanho_bau_por_qtd(qtd_itens: int) -> float:
    qtd = max(1, min(4, int(qtd_itens or 1)))
    return float(_TAMANHO_BAU_POR_QTD.get(qtd, 1.10))


def gerar_bau_server(rng: random.Random, dia_fixo: int = 1, tipo_forcado: str | None = None) -> Dict[str, object]:
    dias = sorted(_TABELA_BAUS.keys())
    bloco = {}
    if dias:
        dia = dias[min(len(dias) - 1, max(1, int(dia_fixo)) - 1)]
        bloco = _TABELA_BAUS.get(dia, {}) if isinstance(_TABELA_BAUS.get(dia, {}), dict) else {}

    tipo_fixado = str(tipo_forcado or "").strip().capitalize()
    chance_tipos = bloco.get("chance_tipos", {}) if isinstance(bloco.get("chance_tipos", {}), dict) else {}
    tipo = tipo_fixado if tipo_fixado in TIPOS_ORDEM else (_escolher_por_peso(rng, chance_tipos or _fallback_chance_tipos()) or "Comum")

    tabela_tipo = bloco.get("chance_raridade_por_tipo", {}) if isinstance(bloco.get("chance_raridade_por_tipo", {}), dict) else {}
    chance_raridade = tabela_tipo.get(tipo, {}) if isinstance(tabela_tipo.get(tipo, {}), dict) else {}
    chance_raridade = chance_raridade or _fallback_raridade_por_tipo(tipo)

    qtd_itens, usados, itens, tentativas = _sortear_quantidade_itens(rng), set(), [], 0
    while len(itens) < qtd_itens and tentativas < 80:
        tentativas += 1
        raridade = _escolher_por_peso(rng, chance_raridade)
        if raridade is None:
            break
        pool = [item for item in _ITENS_VALIDOS.get(int(raridade), []) if str(item.get("Code") or item.get("Nome") or "") not in usados]
        if not pool:
            continue
        escolhido = dict(rng.choice(pool))
        chave_item = str(escolhido.get("Code") or escolhido.get("Nome") or f"raridade_{raridade}_{len(itens)}")
        if not escolhido.get("Code"):
            escolhido["Code"] = chave_item.lower().replace(" ", "_")
        usados.add(chave_item)
        itens.append(escolhido)

    if not itens:
        for raridade in range(1, 7):
            pool = [item for item in _ITENS_VALIDOS.get(raridade, []) if str(item.get("Code") or item.get("Nome") or "") not in usados]
            if pool:
                escolhido = dict(rng.choice(pool))
                if not escolhido.get("Code"):
                    escolhido["Code"] = str(escolhido.get("Nome") or f"fallback_{raridade}").lower().replace(" ", "_")
                itens.append(escolhido)
                break

    quantidade_real = max(1, min(4, len(itens) if itens else qtd_itens))
    tamanho_tiles = tamanho_bau_por_qtd(quantidade_real)
    raio_colisao = max(0.42, tamanho_tiles * 0.32)
    raio_interacao = max(0.85, raio_colisao + 0.45)
    return {
        "tipo_bau": str(tipo),
        "itens": itens[:4],
        "quantidade_itens": quantidade_real,
        "tamanho_tiles": tamanho_tiles,
        "raio_colisao": raio_colisao,
        "raio_interacao": raio_interacao,
    }
