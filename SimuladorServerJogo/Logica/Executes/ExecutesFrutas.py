from __future__ import annotations


def _nome(v):
    return str(v or "").strip().lower()


def _estado(pokemon, contexto=None):
    ctx = dict(contexto or {})
    e = pokemon.estado_extra.setdefault("estado_frutificacao", {})
    e.setdefault("multiplicador_doces", 1.0)
    e.setdefault("bonus_captura_frutas", 0.0)
    e.setdefault("bonus_amizade_captura", 0.0)
    e.setdefault("bonus_iv_percentual_captura", 0.0)
    e.setdefault("bonus_tamanho_barra_captura_percentual", 0.0)
    e.setdefault("multiplicador_velocidade_barra_captura", 1.0)
    e.setdefault("bonus_captura_bioma", {})
    e["limite_frutas"] = int(ctx.get("limite_frutas", e.get("limite_frutas", 2)) or 2)
    frutas = pokemon.estado_extra.setdefault("frutas_aplicadas", [])
    return e, frutas


def executar_fruta(nome_fruta, pokemon, contexto=None):
    n = _nome(nome_fruta)
    e, frutas = _estado(pokemon, contexto=contexto)
    limite = int(e.get("limite_frutas", 2) or 2)
    if len(frutas) >= limite:
        return {"aplicou": False, "efeitos": {"motivo": "limite_frutas"}}

    efeitos = {}
    if n == "caxi berry":
        e["multiplicador_doces"] *= 2.0
        efeitos = {"multiplicador_doces": e["multiplicador_doces"]}
    elif n == "frambo berry":
        e["bonus_captura_frutas"] += 10.0
        efeitos = {"bonus_captura_frutas": e["bonus_captura_frutas"]}
    elif n == "super frambo berry":
        e["bonus_captura_frutas"] += 25.0
        efeitos = {"bonus_captura_frutas": e["bonus_captura_frutas"]}
    elif n == "simp berry":
        e["bonus_amizade_captura"] += 10.0
        efeitos = {"bonus_amizade_captura": e["bonus_amizade_captura"]}
    elif n == "secret berry":
        e["bonus_iv_percentual_captura"] += 5.0
        efeitos = {"bonus_iv_percentual_captura": e["bonus_iv_percentual_captura"]}
    elif n == "lum berry":
        pokemon.estado_extra["nivel"] = max(1, min(100, int(pokemon.estado_extra.get("nivel", 1) or 1) + 3))
        efeitos = {"nivel": pokemon.estado_extra["nivel"]}
    elif n == "tomper berry":
        e["bonus_tamanho_barra_captura_percentual"] += 25.0
        efeitos = {"bonus_tamanho_barra_captura_percentual": e["bonus_tamanho_barra_captura_percentual"]}
    elif n == "abbajuur berry":
        e["multiplicador_velocidade_barra_captura"] *= 0.75
        efeitos = {"multiplicador_velocidade_barra_captura": e["multiplicador_velocidade_barra_captura"]}
    elif n == "jujuca berry":
        efeitos = {"limite_frutas": limite}
    elif n in {"jungle berry", "desert berry", "frozen berry", "field berry", "water berry", "lava berry", "magic berry"}:
        mapa = {
            "jungle berry": "floresta", "desert berry": "deserto", "frozen berry": "gelo",
            "field berry": "campo", "water berry": "agua", "lava berry": "lava", "magic berry": "magico",
        }
        k = mapa[n]
        e["bonus_captura_bioma"][k] = float(e["bonus_captura_bioma"].get(k, 0.0) or 0.0) + 26.0
        efeitos = {"bonus_captura_bioma": dict(e["bonus_captura_bioma"])}
    else:
        return {"aplicou": False, "efeitos": {"motivo": "fruta_desconhecida"}}

    frutas.append({"nome": n})
    return {"aplicou": True, "efeitos": efeitos, "estado_frutificacao": dict(e), "frutas_aplicadas": list(frutas)}
