from __future__ import annotations

import unicodedata


def _nome(v):
    return str(v or "").strip().lower()


def _normalizar_texto(v):
    texto = str(v or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _numero(v, padrao=0.0):
    try:
        if isinstance(v, str):
            return float(v.replace(",", "."))
        return float(v)
    except (TypeError, ValueError):
        return float(padrao)


def _stat(pokemon, chave, padrao=0.0):
    estado = pokemon.estado_extra if isinstance(getattr(pokemon, "estado_extra", None), dict) else {}
    stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
    if chave in stats:
        return _numero(stats.get(chave, padrao), padrao)
    stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}
    if chave in stats_base:
        return _numero(stats_base.get(chave, padrao), padrao)
    return _numero(estado.get(chave, padrao), padrao)


def _valor_alias(pokemon, aliases, padrao=0.0, blocos=("stats", "stats_base", "estado")):
    estado = pokemon.estado_extra if isinstance(getattr(pokemon, "estado_extra", None), dict) else {}
    fontes = []
    if "stats" in blocos and isinstance(estado.get("stats"), dict):
        fontes.append(estado.get("stats"))
    if "stats_base" in blocos and isinstance(estado.get("stats_base"), dict):
        fontes.append(estado.get("stats_base"))
    if "estado" in blocos:
        fontes.append(estado)
    for fonte in fontes:
        for chave in aliases:
            if chave in fonte and fonte.get(chave) not in (None, ""):
                return _numero(fonte.get(chave), padrao)
    return float(padrao)


def _nivel_pokemon(pokemon):
    return max(1, min(100, int(_valor_alias(pokemon, ("nivel", "Nivel", "level"), 1, blocos=("estado",)))))


def executar_pokebola(nome_bola, pokemon, contexto=None):
    n = _nome(nome_bola)
    c = contexto or {}

    if n == "pokeball": return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {}}
    if n == "greatball": return {"poder_base": 25.0, "captura_garantida": False, "efeitos": {}}
    if n == "ultraball": return {"poder_base": 60.0, "captura_garantida": False, "efeitos": {}}
    if n == "masterball": return {"poder_base": 1000.0, "captura_garantida": True, "efeitos": {}}
    if n == "levelball":
        nivel_atual = _nivel_pokemon(pokemon)
        return {"poder_base": float(1 + nivel_atual), "captura_garantida": False, "efeitos": {"nivel_aumentado": 5}}
    if n == "furyball":
        irritado = bool(pokemon.estado_extra.get("esta_irritado", False))
        return {"poder_base": 90.0 if irritado else 10.0, "captura_garantida": False, "efeitos": {"usou_estado_irritado": irritado}}
    if n == "heavyball":
        peso = _valor_alias(pokemon, ("Peso", "peso", "weight", "PesoKg", "peso_kg"), 30.0)
        return {"poder_base": min(100.0, 1.0 + peso / 3.0), "captura_garantida": False, "efeitos": {}}
    if n == "aquaball":
        tipos = [_normalizar_texto(x) for x in (pokemon.estado_extra.get("tipos") or [])]
        habitat = _normalizar_texto(pokemon.estado_extra.get("habitat"))
        bioma = _normalizar_texto(c.get("bioma", pokemon.estado_extra.get("bioma", "")))
        aquatico = bool(pokemon.estado_extra.get("eh_aquatico", False)) or ("agua" in tipos) or ("aqu" in habitat) or bioma == "agua"
        return {"poder_base": 70.0 if aquatico else 10.0, "captura_garantida": False, "efeitos": {"aquatico": aquatico}}
    if n == "attemptball":
        falhas = int(c.get("tentativas_falhas_anteriores", pokemon.estado_extra.get("tentativas_falhas_captura", 0)) or 0)
        return {"poder_base": float(5 + 10 * falhas), "captura_garantida": False, "efeitos": {"falhas_anteriores": falhas}}
    if n == "premierball":
        em_batalha = bool(c.get("em_batalha", False))
        return {"poder_base": 85.0 if em_batalha else 22.0, "captura_garantida": False, "efeitos": {"em_batalha": em_batalha}}
    if n == "candyball": return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {"multiplicador_doces": 3.0}}
    if n == "loveball": return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {"bonus_amizade": 10.0}}
    if n == "secretball": return {"poder_base": 20.0, "captura_garantida": False, "efeitos": {"bonus_iv_percentual": 10.0}}
    if n == "fastball":
        vel = _valor_alias(pokemon, ("Vel", "vel", "velocidade"), 0.0)
        return {"poder_base": 1.0 + vel, "captura_garantida": False, "efeitos": {}}
    if n == "fruitball":
        frutas = len(pokemon.estado_extra.get("frutas_aplicadas", []) or [])
        return {"poder_base": float(5 + 20 * frutas), "captura_garantida": False, "efeitos": {"frutas_contadas": frutas}}
    if n == "tallball":
        altura = _valor_alias(pokemon, ("AlturaCm", "altura_cm", "Altura", "altura", "height"), 50.0)
        altura_cm = altura * 100.0 if altura <= 10.0 else altura
        return {"poder_base": min(100.0, 1.0 + altura_cm / 5.0), "captura_garantida": False, "efeitos": {}}
    if n == "sniperball":
        dist = max(0.0, _numero(c.get("distancia_servidor_tiles", c.get("distancia_arremesso_tiles", 0.0)), 0.0))
        dist_cap = max(0.0, _numero(c.get("captura_sniperball_distancia_max_tiles", 9.0), 9.0))
        poder = 1.0 + 10.0 * min(dist, dist_cap)
        poder_max = c.get("captura_sniperball_poder_max")
        if poder_max not in (None, ""):
            poder = min(_numero(poder_max, 100.0), poder)
        return {"poder_base": poder, "captura_garantida": False, "efeitos": {"bonus_alcance_tiles": 2.0, "distancia_servidor_tiles": dist}}
    if n == "beastball":
        raridade = pokemon.estado_extra.get("raridade")
        raridade_norm = _normalizar_texto(raridade)
        try:
            raridade_alta = float(raridade) >= _numero(c.get("captura_beastball_raridade_min", 5.0), 5.0)
        except (TypeError, ValueError):
            raridade_alta = False
        raro = bool(
            pokemon.estado_extra.get("especial", False)
            or pokemon.estado_extra.get("nao_spawnavel", False)
            or pokemon.estado_extra.get("não_spawnavel", False)
            or raridade_norm in {"raro", "lendario", "evento", "especial"}
            or raridade_alta
        )
        return {"poder_base": 85.0 if raro else 15.0, "captura_garantida": False, "efeitos": {"raro_ou_especial": raro}}

    print(f"[CAPTURA_POKEBOLA_DESCONHECIDA] nome={nome_bola!r} fallback=pokeball")
    return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {"fallback": True, "motivo": "pokebola_desconhecida"}}
