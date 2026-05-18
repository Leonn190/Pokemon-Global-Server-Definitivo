from __future__ import annotations

import copy


TAMANHOS_MUNDO = {
    "pequeno": {"id": "pequeno", "rotulo": "Pequeno", "width": 7000, "height": 7000},
    "regular": {"id": "regular", "rotulo": "Regular", "width": 10000, "height": 10000},
    "grande": {"id": "grande", "rotulo": "Grande", "width": 12000, "height": 12000},
}

BIOMAS_CONFIGURAVEIS = ("FIELD", "FOREST", "DESERT", "SNOW", "MAGIC", "VOLCANIC", "SWAMP")

RECURSOS_POR_GRUPO = {
    "arvores": ("TREE", "TREE_TROMBOSA", "PALM", "PINE"),
    "pedras_minerios": ("ROCK", "COAL", "IRON", "COPPER"),
    "plantas_decorativas": ("BUSH", "FLOWER", "PLANT"),
    "recursos_raros": ("GOLD", "DIAMOND", "RUBY", "EMERALD", "SAPPHIRE", "TOPAZ", "AMETHYST", "JADE", "AQUAMARINE"),
}


def _clamp(valor, minimo, maximo):
    return minimo if valor < minimo else maximo if valor > maximo else valor


def _slider(config, chave, padrao=50) -> int:
    try:
        valor = int(round(float(config.get(chave, padrao))))
    except (TypeError, ValueError, AttributeError):
        valor = padrao
    return int(_clamp(valor, 0, 100))


def _slider_nested(config, secao, chave, padrao=50) -> int:
    bloco = config.get(secao) if isinstance(config, dict) else {}
    if not isinstance(bloco, dict):
        bloco = {}
    return _slider(bloco, chave, padrao)


def _fator_suave(slider: int) -> float:
    return float(_clamp(slider / 50.0, 0.5, 1.5))


def _fator_amplo(slider: int) -> float:
    return float(_clamp(slider / 50.0, 0.15, 2.0))


def _multiplicar_numero(bloco: dict, chave: str, fator: float, minimo=None, maximo=None, inteiro=False) -> None:
    if chave not in bloco:
        return
    try:
        valor = float(bloco[chave]) * float(fator)
    except (TypeError, ValueError):
        return
    if minimo is not None:
        valor = max(float(minimo), valor)
    if maximo is not None:
        valor = min(float(maximo), valor)
    bloco[chave] = int(round(valor)) if inteiro else float(valor)


def _aplicar_tamanho(regras_terreno: dict, config: dict) -> None:
    tamanho = config.get("tamanho_mundo") if isinstance(config, dict) else {}
    tamanho_id = "regular"
    if isinstance(tamanho, dict):
        tamanho_id = str(tamanho.get("id") or "regular").strip().lower()
    elif isinstance(tamanho, str):
        tamanho_id = tamanho.strip().lower()
    tamanho_norm = TAMANHOS_MUNDO.get(tamanho_id, TAMANHOS_MUNDO["regular"])
    world = regras_terreno.get("world")
    if isinstance(world, dict):
        world["width"] = int(tamanho_norm["width"])
        world["height"] = int(tamanho_norm["height"])


def _aplicar_agua(regras_terreno: dict, config: dict) -> None:
    ocean = regras_terreno.get("ocean")
    if not isinstance(ocean, dict):
        return
    slider = _slider(config, "agua")
    fator = _fator_suave(slider)

    if "sea_level" in ocean:
        try:
            base = float(ocean["sea_level"])
            ocean["sea_level"] = float(_clamp(base + ((fator - 1.0) * 0.075), 0.43, 0.60))
        except (TypeError, ValueError):
            pass

    _multiplicar_numero(ocean, "hard_border", fator, minimo=40, maximo=260, inteiro=True)
    _multiplicar_numero(ocean, "soft_border", fator, minimo=180, maximo=900, inteiro=True)
    _multiplicar_numero(ocean, "edge_penalty_strength", fator, minimo=0.20, maximo=0.95)
    _multiplicar_numero(ocean, "shallow_water_band", fator, minimo=0.006, maximo=0.06)
    _multiplicar_numero(ocean, "deep_water_extra_depth", fator, minimo=0.012, maximo=0.10)


def _aplicar_rios(regras_terreno: dict, config: dict) -> None:
    rivers = regras_terreno.get("rivers")
    if not isinstance(rivers, dict):
        return

    _multiplicar_numero(rivers, "sources", _fator_amplo(_slider_nested(config, "rios", "quantidade")), minimo=0, inteiro=True)
    _multiplicar_numero(rivers, "max_length", _fator_amplo(_slider_nested(config, "rios", "comprimento")), minimo=80, inteiro=True)
    largura = _fator_amplo(_slider_nested(config, "rios", "largura"))
    _multiplicar_numero(rivers, "min_width", largura, minimo=1, maximo=12, inteiro=True)
    _multiplicar_numero(rivers, "max_width", largura, minimo=1, maximo=18, inteiro=True)
    try:
        rivers["max_width"] = max(int(rivers.get("min_width", 1)), int(rivers.get("max_width", 1)))
        rivers["width"] = max(1, min(int(rivers.get("width", rivers["min_width"])), int(rivers["max_width"])))
    except (TypeError, ValueError):
        pass


def _aplicar_lagos(regras_terreno: dict, config: dict) -> None:
    lakes = regras_terreno.get("lakes")
    if not isinstance(lakes, dict):
        return
    slider = _slider(config, "lagos")
    delta = (slider - 50) / 50.0

    if "threshold" in lakes:
        try:
            lakes["threshold"] = float(_clamp(float(lakes["threshold"]) - (delta * 0.12), 0.58, 0.90))
        except (TypeError, ValueError):
            pass
    if "min_moisture" in lakes:
        try:
            lakes["min_moisture"] = float(_clamp(float(lakes["min_moisture"]) - (delta * 0.10), 0.48, 0.82))
        except (TypeError, ValueError):
            pass
    if "elevation_offset_from_sea_level" in lakes:
        try:
            lakes["elevation_offset_from_sea_level"] = float(
                _clamp(float(lakes["elevation_offset_from_sea_level"]) + (delta * 0.035), 0.035, 0.16)
            )
        except (TypeError, ValueError):
            pass


def _aplicar_biomas(regras_biomas: dict, config: dict) -> None:
    biomas_cfg = config.get("biomas") if isinstance(config, dict) else {}
    biomas = regras_biomas.get("biomes")
    if not isinstance(biomas_cfg, dict) or not isinstance(biomas, dict):
        return
    for bioma_id in BIOMAS_CONFIGURAVEIS:
        bloco = biomas.get(bioma_id)
        if isinstance(bloco, dict):
            _multiplicar_numero(bloco, "weight", _fator_amplo(_slider(biomas_cfg, bioma_id)), minimo=0.01, maximo=3.0)


def _aplicar_recursos(regras_biomas: dict, config: dict) -> None:
    recursos_cfg = config.get("recursos") if isinstance(config, dict) else {}
    biomas = regras_biomas.get("biomes")
    if not isinstance(recursos_cfg, dict) or not isinstance(biomas, dict):
        return
    for bloco_bioma in biomas.values():
        objetos = bloco_bioma.get("objects") if isinstance(bloco_bioma, dict) else None
        if not isinstance(objetos, dict):
            continue
        for grupo, objetos_grupo in RECURSOS_POR_GRUPO.items():
            fator = _fator_amplo(_slider(recursos_cfg, grupo))
            for objeto in objetos_grupo:
                _multiplicar_numero(objetos, objeto, fator, minimo=0.0, maximo=0.05)


def _aplicar_vilas(regras_localidades: dict, config: dict) -> None:
    villages = regras_localidades.get("villages")
    if not isinstance(villages, dict):
        return
    fator = _fator_amplo(_slider(config, "vilas"))
    _multiplicar_numero(villages, "min_count", fator, minimo=0, inteiro=True)
    _multiplicar_numero(villages, "max_count", fator, minimo=0, inteiro=True)
    try:
        villages["max_count"] = max(int(villages.get("min_count", 0)), int(villages.get("max_count", 0)))
    except (TypeError, ValueError):
        pass


def aplicar_config_mundo(regras_terreno, regras_biomas, regras_localidades, config_mundo):
    terreno = copy.deepcopy(regras_terreno or {})
    biomas = copy.deepcopy(regras_biomas or {})
    localidades = copy.deepcopy(regras_localidades or {})
    config = config_mundo if isinstance(config_mundo, dict) else {}

    _aplicar_tamanho(terreno, config)
    _aplicar_agua(terreno, config)
    _aplicar_rios(terreno, config)
    _aplicar_lagos(terreno, config)
    _aplicar_biomas(biomas, config)
    _aplicar_recursos(biomas, config)
    _aplicar_vilas(localidades, config)
    return terreno, biomas, localidades
