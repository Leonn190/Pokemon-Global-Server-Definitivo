from __future__ import annotations


def _nome(v):
    return str(v or "").strip().lower()


def _stat(pokemon, chave, padrao=0.0):
    stats = pokemon.estado_extra.get("stats") if isinstance(pokemon.estado_extra.get("stats"), dict) else {}
    return float(stats.get(chave, padrao) or padrao)


def executar_pokebola(nome_bola, pokemon, contexto=None):
    n = _nome(nome_bola)
    c = contexto or {}

    if n == "pokeball": return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {}}
    if n == "greatball": return {"poder_base": 25.0, "captura_garantida": False, "efeitos": {}}
    if n == "ultraball": return {"poder_base": 60.0, "captura_garantida": False, "efeitos": {}}
    if n == "masterball": return {"poder_base": 1000.0, "captura_garantida": True, "efeitos": {}}
    if n == "levelball":
        pokemon.estado_extra["nivel"] = max(1, min(100, int(pokemon.estado_extra.get("nivel", 1) or 1) + 5))
        return {"poder_base": float(1 + pokemon.estado_extra["nivel"]), "captura_garantida": False, "efeitos": {"nivel_aumentado": 5}}
    if n == "furyball":
        irritado = bool(pokemon.estado_extra.get("esta_irritado", False))
        return {"poder_base": 70.0 if irritado else 10.0, "captura_garantida": False, "efeitos": {"usou_estado_irritado": irritado}}
    if n == "heavyball": return {"poder_base": min(100.0, 1.0 + _stat(pokemon, "Peso", 30.0) / 3.0), "captura_garantida": False, "efeitos": {}}
    if n == "aquaball":
        tipos = [str(x).lower() for x in (pokemon.estado_extra.get("tipos") or [])]
        habitat = str(pokemon.estado_extra.get("habitat") or "").lower()
        aquatico = bool(pokemon.estado_extra.get("eh_aquatico", False)) or ("agua" in tipos) or ("aqu" in habitat) or (str(c.get("bioma", "")).lower() == "agua")
        return {"poder_base": 70.0 if aquatico else 10.0, "captura_garantida": False, "efeitos": {"aquatico": aquatico}}
    if n == "attemptball":
        falhas = int(c.get("tentativas_falhas_anteriores", 0) or 0)
        return {"poder_base": float(5 + 10 * falhas), "captura_garantida": False, "efeitos": {"falhas_anteriores": falhas}}
    if n == "premierball":
        em_batalha = bool(c.get("em_batalha", False))
        return {"poder_base": 80.0 if em_batalha else 20.0, "captura_garantida": False, "efeitos": {"em_batalha": em_batalha}}
    if n == "candyball": return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {"multiplicador_doces": 3.0}}
    if n == "loveball": return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {"bonus_amizade": 10.0}}
    if n == "secretball": return {"poder_base": 20.0, "captura_garantida": False, "efeitos": {"bonus_iv_percentual": 10.0}}
    if n == "fastball": return {"poder_base": 1.0 + _stat(pokemon, "Vel", 0.0), "captura_garantida": False, "efeitos": {}}
    if n == "fruitball":
        frutas = len(pokemon.estado_extra.get("frutas_aplicadas", []) or [])
        return {"poder_base": float(5 + 20 * frutas), "captura_garantida": False, "efeitos": {"frutas_contadas": frutas}}
    if n == "tallball":
        altura = _stat(pokemon, "AlturaCm", _stat(pokemon, "Altura", 50.0))
        return {"poder_base": min(100.0, 1.0 + altura / 5.0), "captura_garantida": False, "efeitos": {}}
    if n == "sniperball":
        dist = float(c.get("distancia_arremesso_tiles", 0.0) or 0.0)
        return {"poder_base": 1.0 + 10.0 * max(0.0, dist), "captura_garantida": False, "efeitos": {"bonus_alcance_tiles": 2.0}}
    if n == "beastball":
        raro = bool(pokemon.estado_extra.get("especial", False) or pokemon.estado_extra.get("raridade") in {"raro", "lendario", "evento"})
        return {"poder_base": 85.0 if raro else 15.0, "captura_garantida": False, "efeitos": {"raro_ou_especial": raro}}

    return {"poder_base": 10.0, "captura_garantida": False, "efeitos": {"fallback": True}}
