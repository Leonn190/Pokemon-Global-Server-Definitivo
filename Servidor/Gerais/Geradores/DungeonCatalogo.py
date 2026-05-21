from __future__ import annotations

import random

from Servidor.Gerais.LoaderCatalogos import carregar_catalogo
from Servidor.Mundo.DungeonGeometria import ALTURA_BLOCO_SALA_TILES, LARGURA_BLOCO_SALA_TILES


def _catalogo_default() -> dict:
    return {
        "catalogo_versao": "v2_modelos_salas",
        "tamanho_sala_tiles": {
            "largura": LARGURA_BLOCO_SALA_TILES,
            "altura": ALTURA_BLOCO_SALA_TILES,
        },
        "calculo_dificuldade_sala": {
            "pesos_recomendados": {"armadilhas": 1.0, "servos": 1.0, "claridade": 0.35}
        },
        "configuracoes_armadilhas": {},
        "salas": [
            {
                "id": 1,
                "modelo_id": "entrada",
                "nome": "Entrada",
                "tipo": "entrada",
                "categoria": "fixa",
                "chance_spawn": 0.0,
                "dificuldade_base": 0,
                "servos": {"min": 0, "max": 0},
                "claridade": {"min": 10, "max": 10},
                "armadilhas": [],
            },
            {
                "id": 2,
                "modelo_id": "boss",
                "nome": "Sala de Boss",
                "tipo": "boss",
                "categoria": "fixa",
                "chance_spawn": 0.0,
                "dificuldade_base": 0,
                "servos": {"min": 0, "max": 0},
                "claridade": {"min": 8, "max": 10},
                "armadilhas": [],
            },
            {
                "id": 3,
                "modelo_id": "sala_comum",
                "nome": "Sala Comum",
                "tipo": "servos",
                "categoria": "combate",
                "chance_spawn": 1.0,
                "dificuldade_base": 1,
                "servos": {"min": 0, "max": 2},
                "claridade": {"min": 7, "max": 10},
                "armadilhas": [],
            },
        ],
    }

def _float_seguro(valor, default=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)

def _int_seguro(valor, default=0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)

def _intervalo_dict(valor, padrao_min=0, padrao_max=0) -> dict:
    bruto = valor if isinstance(valor, dict) else {}
    mn = _float_seguro(bruto.get("min"), padrao_min)
    mx = _float_seguro(bruto.get("max"), padrao_max)
    if mx < mn:
        mn, mx = mx, mn
    return {"min": mn, "max": mx, **({"peso_dificuldade": _float_seguro(bruto.get("peso_dificuldade"), 0.35)} if "peso_dificuldade" in bruto else {})}

def _normalizar_modelo_sala(item: dict, indice: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    modelo_id = str(item.get("modelo_id") or item.get("id") or "").strip()
    if not modelo_id:
        return None
    tipo = str(item.get("tipo") or "servos").strip().lower() or "servos"
    try:
        id_catalogo = int(item.get("id", indice) or indice)
    except (TypeError, ValueError):
        id_catalogo = int(indice)
    return {
        "id": id_catalogo,
        "modelo_id": modelo_id,
        "nome": str(item.get("nome") or item.get("Nome") or modelo_id),
        "tipo": tipo,
        "categoria": str(item.get("categoria") or "").strip().lower(),
        "chance_spawn": max(0.0, _float_seguro(item.get("chance_spawn", item.get("chance", 0.0)), 0.0)),
        "dificuldade_base": _float_seguro(item.get("dificuldade_base", item.get("dificuldade", 0)), 0.0),
        "servos": _intervalo_dict(item.get("servos"), 0, 0),
        "claridade": _intervalo_dict(item.get("claridade"), 10, 10),
        "armadilhas": [dict(a) for a in list(item.get("armadilhas") or []) if isinstance(a, dict)],
        "conteudo_especial": dict(item.get("conteudo_especial") or {}) if isinstance(item.get("conteudo_especial"), dict) else {},
        "variacao_dificuldade": dict(item.get("variacao_dificuldade") or {}) if isinstance(item.get("variacao_dificuldade"), dict) else {},
    }

def _normalizar_catalogo(data: dict) -> dict:
    if not isinstance(data, dict):
        return _catalogo_default()
    bruto = data.get("salas") if isinstance(data.get("salas"), (list, dict)) else []
    salas = []
    if isinstance(bruto, dict):
        iter_salas = bruto.values()
    else:
        iter_salas = bruto if isinstance(bruto, list) else []
    for idx, item in enumerate(iter_salas, start=1):
        modelo = _normalizar_modelo_sala(item, idx)
        if modelo is not None:
            salas.append(modelo)
    if not salas:
        return _catalogo_default()
    por_id = {str(s.get("modelo_id") or "") for s in salas}
    for sala in _catalogo_default()["salas"]:
        if str(sala.get("modelo_id") or "") not in por_id:
            salas.append(dict(sala))
    tamanho = data.get("tamanho_sala_tiles") if isinstance(data.get("tamanho_sala_tiles"), dict) else {}
    calculo = data.get("calculo_dificuldade_sala") if isinstance(data.get("calculo_dificuldade_sala"), dict) else {}
    configs = data.get("configuracoes_armadilhas") if isinstance(data.get("configuracoes_armadilhas"), dict) else {}
    return {
        "catalogo_versao": str(data.get("catalogo_versao") or "v2_modelos_salas"),
        "tamanho_sala_tiles": {
            "largura": _int_seguro(tamanho.get("largura"), LARGURA_BLOCO_SALA_TILES),
            "altura": _int_seguro(tamanho.get("altura"), ALTURA_BLOCO_SALA_TILES),
        },
        "calculo_dificuldade_sala": dict(calculo),
        "configuracoes_armadilhas": dict(configs),
        "salas": salas,
    }

def carregar_catalogo_dungeons() -> dict:
    try:
        dados = carregar_catalogo("Dungeon")
        if dados:
            return _normalizar_catalogo(dados)
    except Exception as exc:
        print(f"[Dungeons] Catalogo invalido: {exc}")
    return _catalogo_default()

def _modelos_catalogo(catalogo: dict) -> list[dict]:
    return [dict(s) for s in list(catalogo.get("salas") or []) if isinstance(s, dict)]

def _modelo_por_id(catalogo: dict) -> dict[str, dict]:
    return {str(s.get("modelo_id") or "").strip(): dict(s) for s in _modelos_catalogo(catalogo) if str(s.get("modelo_id") or "").strip()}

def _modelos_alocaveis(catalogo: dict) -> list[dict]:
    return [
        dict(s)
        for s in _modelos_catalogo(catalogo)
        if str(s.get("tipo") or "").strip().lower() not in {"entrada", "boss"}
        and str(s.get("modelo_id") or "").strip() not in {"entrada", "boss"}
        and float(s.get("chance_spawn", 0.0) or 0.0) > 0.0
    ]


def _dificuldade_num_catalogo(valor) -> int:
    mapa = {"facil": 1, "fácil": 1, "media": 2, "média": 2, "normal": 2, "dificil": 4, "difícil": 4, "lendaria": 6, "lendária": 6}
    txt = str(valor or "").strip().lower()
    if txt in mapa:
        return mapa[txt]
    try:
        return int(float(txt))
    except (TypeError, ValueError):
        return 2


def _modelo_para_tipo(catalogo: dict, tipo: str) -> dict:
    tipo_norm = str(tipo or "").strip().lower()
    for modelo in _modelos_catalogo(catalogo):
        if str(modelo.get("tipo") or "").strip().lower() == tipo_norm or str(modelo.get("modelo_id") or "").strip().lower() == tipo_norm:
            return modelo
    alocaveis = _modelos_alocaveis(catalogo)
    return alocaveis[0] if alocaveis else _catalogo_default()["salas"][2]


def _escolher_modelo_sala(rng: random.Random, catalogo: dict, dificuldade=2) -> dict:
    modelos = _modelos_alocaveis(catalogo)
    if not modelos:
        return _catalogo_default()["salas"][2]
    dif = max(1, min(6, _dificuldade_num_catalogo(dificuldade)))
    pesos = []
    for modelo in modelos:
        peso = max(0.0, float(modelo.get("chance_spawn", 0.0) or 0.0))
        distancia = abs(float(modelo.get("dificuldade_base", 1.0) or 1.0) - float(dif))
        pesos.append(peso * max(0.20, 1.0 - distancia * 0.16))
    if not any(p > 0.0 for p in pesos):
        pesos = [1.0 for _ in modelos]
    return dict(rng.choices(modelos, weights=pesos, k=1)[0])
