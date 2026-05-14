from __future__ import annotations

import unicodedata


def _nome(v):
    return str(v or "").strip().lower()


def _normalizar_texto(v):
    texto = str(v or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _estado(pokemon, contexto=None):
    ctx = dict(contexto or {})
    e = pokemon.estado_extra.setdefault("estado_frutificacao", {})
    e.setdefault("multiplicador_doces", 1.0)
    e.setdefault("bonus_captura_frutas", 0.0)
    e.setdefault("bonus_amizade_captura", 0.0)
    e.setdefault("bonus_iv_percentual_captura", 0.0)
    e.setdefault("bonus_nivel_captura", 0)
    e.setdefault("bonus_tamanho_barra_captura_percentual", 0.0)
    e.setdefault("multiplicador_velocidade_barra_captura", 1.0)
    e.setdefault("bonus_captura_bioma", {})
    limite_regra = int(ctx.get("limite_frutas", e.get("limite_frutas", 2)) or 2)
    e["limite_frutas"] = max(int(e.get("limite_frutas", limite_regra) or limite_regra), limite_regra)
    frutas = pokemon.estado_extra.setdefault("frutas_aplicadas", [])
    return e, frutas


def _retorno(aplicou, efeitos, e, frutas):
    return {
        "aplicou": bool(aplicou),
        "efeitos": dict(efeitos or {}),
        "estado_frutificacao": dict(e),
        "frutas_aplicadas": list(frutas),
    }


def executar_fruta(nome_fruta, pokemon, contexto=None):
    n = _nome(nome_fruta)
    ctx = dict(contexto or {})
    e, frutas = _estado(pokemon, contexto=contexto)
    limite = int(e.get("limite_frutas", 2) or 2)

    efeitos = {}
    if n == "caxi berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["multiplicador_doces"] *= 2.0
        efeitos = {"multiplicador_doces": e["multiplicador_doces"]}
    elif n == "frambo berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["bonus_captura_frutas"] += 10.0
        efeitos = {"bonus_captura_frutas": e["bonus_captura_frutas"]}
    elif n == "super frambo berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["bonus_captura_frutas"] += 25.0
        efeitos = {"bonus_captura_frutas": e["bonus_captura_frutas"]}
    elif n == "simp berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["bonus_amizade_captura"] += 10.0
        efeitos = {"bonus_amizade_captura": e["bonus_amizade_captura"]}
    elif n == "secret berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["bonus_iv_percentual_captura"] += 5.0
        efeitos = {"bonus_iv_percentual_captura": e["bonus_iv_percentual_captura"]}
    elif n == "lum berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["bonus_nivel_captura"] = int(e.get("bonus_nivel_captura", 0) or 0) + 3
        efeitos = {"bonus_nivel_captura": e["bonus_nivel_captura"]}
    elif n == "tomper berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["bonus_tamanho_barra_captura_percentual"] += 25.0
        efeitos = {"bonus_tamanho_barra_captura_percentual": e["bonus_tamanho_barra_captura_percentual"]}
    elif n == "abbajuur berry":
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        e["multiplicador_velocidade_barra_captura"] *= 0.75
        efeitos = {"multiplicador_velocidade_barra_captura": e["multiplicador_velocidade_barra_captura"]}
    elif n == "jujuca berry":
        max_jujuca = max(1, int(ctx.get("captura_jujuca_max_por_pokemon", 1) or 1))
        usadas = sum(1 for f in frutas if _nome((f or {}).get("nome") if isinstance(f, dict) else f) == "jujuca berry")
        if usadas >= max_jujuca:
            return _retorno(False, {"motivo": "jujuca_ja_aplicada"}, e, frutas)
        bonus_limite = int(ctx.get("captura_jujuca_bonus_limite_frutas", 2) or 2)
        e["limite_frutas"] = int(limite + bonus_limite)
        efeitos = {"limite_frutas": e["limite_frutas"], "bonus_limite_frutas": bonus_limite}
    elif n in {"jungle berry", "desert berry", "frozen berry", "field berry", "water berry", "lava berry", "magic berry"}:
        if len(frutas) >= limite:
            return _retorno(False, {"motivo": "limite_frutas"}, e, frutas)
        mapa = {
            "jungle berry": ("floresta",),
            "desert berry": ("deserto",),
            "frozen berry": ("gelo", "neve"),
            "field berry": ("campo",),
            "water berry": ("agua", "aquatico"),
            "lava berry": ("lava", "vulcanico"),
            "magic berry": ("magico",),
        }
        for k in mapa[n]:
            chave = _normalizar_texto(k)
            e["bonus_captura_bioma"][chave] = float(e["bonus_captura_bioma"].get(chave, 0.0) or 0.0) + 26.0
        efeitos = {"bonus_captura_bioma": dict(e["bonus_captura_bioma"])}
    else:
        return _retorno(False, {"motivo": "fruta_desconhecida"}, e, frutas)

    frutas.append({"nome": n})
    return _retorno(True, efeitos, e, frutas)
