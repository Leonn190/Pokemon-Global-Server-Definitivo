from __future__ import annotations

import copy


TIPOS_GLOBAIS = {"arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"}
TIPOS_LINHA = {"linha", "fileira", "row", "line"}
TIPOS_COLUNA = {"coluna", "column"}


def alvo_fallback():
    return {
        "tipo": "area",
        "quantidade": 1,
        "lados_permitidos": ["lado_oposto"],
        "exige_area_ocupada": False,
        "inclui_reserva": False,
        "area_id": None,
    }


def bool_config_alvo(valor):
    if isinstance(valor, bool):
        return valor
    texto = str(valor or "").strip().lower()
    if texto in {"1", "true", "sim", "yes", "on"}:
        return True
    if texto in {"0", "false", "nao", "no", "off", ""}:
        return False
    return bool(valor)


def normalizar_config_alvo(config):
    base = alvo_fallback()
    if isinstance(config, dict):
        for chave in ("tipo", "quantidade", "lados_permitidos", "exige_area_ocupada", "inclui_reserva", "area_id"):
            if chave in config:
                base[chave] = copy.deepcopy(config.get(chave))
    try:
        base["quantidade"] = max(1, int(float(base.get("quantidade") or 1)))
    except (TypeError, ValueError):
        base["quantidade"] = 1
    permitidos = base.get("lados_permitidos")
    if isinstance(permitidos, str):
        permitidos = [permitidos]
    if not isinstance(permitidos, (list, tuple, set)):
        permitidos = ["lado_oposto"]
    base["lados_permitidos"] = [str(item) for item in permitidos if str(item or "").strip()] or ["lado_oposto"]
    base["tipo"] = str(base.get("tipo") or "area").strip().lower() or "area"
    base["exige_area_ocupada"] = bool_config_alvo(base.get("exige_area_ocupada"))
    base["inclui_reserva"] = bool_config_alvo(base.get("inclui_reserva"))
    if base.get("area_id"):
        base["area_id"] = str(base.get("area_id")).strip().upper()
    else:
        base["area_id"] = None
    return base


def normalizar_alvos_config(props):
    props = props if isinstance(props, dict) else {}
    alvificacao = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
    alvos = alvificacao.get("alvos") if isinstance(alvificacao, dict) else None
    if isinstance(alvos, list):
        configs = [normalizar_config_alvo(item) for item in alvos if isinstance(item, dict)]
        if configs:
            return configs
    chaves_antigas = ("tipo", "quantidade", "lados_permitidos", "exige_area_ocupada", "inclui_reserva", "area_id")
    if isinstance(alvificacao, dict) and any(chave in alvificacao for chave in chaves_antigas):
        return [normalizar_config_alvo(alvificacao)]
    return [alvo_fallback()]


def config_para_selecao(selecao, props):
    configs = normalizar_alvos_config(props)
    try:
        grupo = int((selecao or {}).get("grupo", 0))
    except (TypeError, ValueError):
        grupo = 0
    if isinstance(selecao, dict) and isinstance(selecao.get("config"), dict):
        config = normalizar_config_alvo(selecao.get("config"))
        if str(config.get("tipo") or "").strip().lower() == "fixa" and not config.get("area_id") and 0 <= grupo < len(configs):
            config["area_id"] = configs[grupo].get("area_id")
        return config
    if 0 <= grupo < len(configs):
        return configs[grupo]
    return configs[0]


def area_id_para_selecao(selecao, alvo_cfg=None):
    selecao = selecao if isinstance(selecao, dict) else {}
    alvo_cfg = normalizar_config_alvo(alvo_cfg or selecao.get("config") or {})
    if str(alvo_cfg.get("tipo") or "").strip().lower() == "fixa":
        area_id = alvo_cfg.get("area_id") or selecao.get("area_id")
    else:
        area_id = selecao.get("area_id")
    return str(area_id or "").strip().upper()


def selecoes_alvo_acao(alvo_ou_acao, props):
    entrada = alvo_ou_acao if isinstance(alvo_ou_acao, dict) else {}
    if "alvo" in entrada:
        alvo = entrada.get("alvo") if isinstance(entrada.get("alvo"), dict) else {}
    else:
        alvo = entrada
    if str(alvo.get("tipo") or "").strip().lower() == "multi":
        return [item for item in list(alvo.get("alvos") or []) if isinstance(item, dict)]
    config = normalizar_alvos_config(props)[0]
    if str(alvo.get("tipo") or "").strip().lower() == "pokemon" and alvo.get("pokemon_id"):
        return [{**alvo, "grupo": 0, "ordem": 0, "config": config}]
    if alvo.get("area_id"):
        return [{"tipo": "area", "area_id": alvo.get("area_id"), "grupo": 0, "ordem": 0, "config": config}]
    configs = normalizar_alvos_config(props)
    if all(str(cfg.get("tipo") or "").strip().lower() == "fixa" and cfg.get("area_id") for cfg in configs):
        selecoes = []
        for grupo, cfg in enumerate(configs):
            for ordem in range(int(cfg.get("quantidade") or 1)):
                selecoes.append(
                    {
                        "tipo": "area",
                        "area_id": cfg.get("area_id"),
                        "grupo": grupo,
                        "ordem": ordem,
                        "config": copy.deepcopy(cfg),
                    }
                )
        return selecoes
    return []


def validar_quantidade_selecoes(alvo, selecoes, props):
    configs = normalizar_alvos_config(props)
    alvo = alvo if isinstance(alvo, dict) else {}
    alvo_multi = str(alvo.get("tipo") or "").strip().lower() == "multi"
    alvo_fixo_implicito = not alvo and all(str(cfg.get("tipo") or "").strip().lower() == "fixa" for cfg in configs)
    if not alvo_multi and not alvo_fixo_implicito:
        if len(configs) > 1 or int(configs[0].get("quantidade") or 1) != 1:
            return "quantidade_alvos_incompleta"
        return None
    contagem = {}
    for selecao in selecoes:
        try:
            grupo = int(selecao.get("grupo", 0))
        except (TypeError, ValueError):
            grupo = 0
        if grupo < 0 or grupo >= len(configs):
            return "grupo_alvo_invalido"
        contagem[grupo] = contagem.get(grupo, 0) + 1
    for idx, config in enumerate(configs):
        if contagem.get(idx, 0) != int(config.get("quantidade") or 1):
            return "quantidade_alvos_incompleta"
    return None


def areas_afetadas_por_alvificacao(area_id, props=None, lado_usuario=None, alvo_cfg=None, partida=None):
    alvo_cfg = normalizar_config_alvo(alvo_cfg or normalizar_alvos_config(props)[0])
    if str(alvo_cfg.get("tipo") or "").strip().lower() == "fixa":
        area_id = alvo_cfg.get("area_id") or area_id
    area_id = str(area_id or "").strip().upper()
    if not area_id:
        return []
    tipo = str(alvo_cfg.get("tipo") or "area").strip().lower()
    if tipo in TIPOS_GLOBAIS:
        lado_area = _lado_area(partida, area_id)
        if lado_area is None:
            return [area_id]
        return [
            str(aid)
            for aid, area in (getattr(partida, "areas", {}) or {}).items()
            if _int_ou_none((area or {}).get("lado_id")) == lado_area
        ]
    try:
        idx = int(area_id[1:]) - 1
    except (TypeError, ValueError, IndexError):
        return [area_id]
    if idx < 0 or idx > 8:
        return [area_id]
    prefixo = area_id[:1]
    row, col = idx // 3, idx % 3
    if tipo in TIPOS_LINHA:
        colunas = range(3)
        try:
            if int(lado_usuario) == 51:
                colunas = range(2, -1, -1)
        except (TypeError, ValueError):
            pass
        return [f"{prefixo}{row * 3 + c + 1}" for c in colunas]
    if tipo in TIPOS_COLUNA:
        return [f"{prefixo}{r * 3 + col + 1}" for r in range(3)]
    return [area_id]


def area_permitida_para_ataque(partida, pokemon, area_id, props, alvo_cfg=None, checar_provocando=True):
    alvo_cfg = normalizar_config_alvo(alvo_cfg or normalizar_alvos_config(props)[0])
    area_id = area_id_para_selecao({"area_id": area_id, "config": alvo_cfg}, alvo_cfg)
    area = _area(partida, area_id)
    if not isinstance(area, dict):
        return False
    if bool(alvo_cfg.get("exige_area_ocupada")) and _pokemon_na_area(partida, area_id) is None:
        return False
    if not _lado_area_permitido(pokemon, area_id, area, alvo_cfg):
        return False
    tipo_alvo = str(alvo_cfg.get("tipo") or "area").strip().lower()
    if checar_provocando and tipo_alvo not in TIPOS_GLOBAIS:
        selecao = {"tipo": "area", "area_id": area_id, "grupo": 0, "ordem": 0, "config": copy.deepcopy(alvo_cfg)}
        return validar_provocando_selecoes(partida, pokemon, [selecao], props)
    return True


def pokemon_permitido_para_ataque(partida, pokemon, alvo, props, alvo_cfg=None, checar_provocando=True):
    if alvo is None or not _esta_vivo(alvo):
        return False
    alvo_cfg = normalizar_config_alvo(alvo_cfg or normalizar_alvos_config(props)[0])
    if _esta_reserva(alvo) and not bool(alvo_cfg.get("inclui_reserva", False)):
        return False
    if not _lado_pokemon_permitido(pokemon, alvo, alvo_cfg):
        return False
    tipo_alvo = str(alvo_cfg.get("tipo") or "pokemon").strip().lower()
    if checar_provocando and tipo_alvo not in TIPOS_GLOBAIS:
        selecao = {"tipo": "pokemon", "pokemon_id": _pid(alvo), "grupo": 0, "ordem": 0, "config": copy.deepcopy(alvo_cfg)}
        return validar_provocando_selecoes(partida, pokemon, [selecao], props)
    return True


def validar_provocando_selecoes(partida, pokemon, selecoes, props):
    lado_origem = _lado_pokemon(pokemon)
    if lado_origem is None:
        return True
    por_lado = {}
    for selecao in list(selecoes or []):
        if not isinstance(selecao, dict):
            continue
        alvo_cfg = config_para_selecao(selecao, props)
        tipo_alvo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        if tipo_alvo in TIPOS_GLOBAIS:
            continue
        if tipo_alvo == "pokemon":
            alvo = _obter_pokemon(partida, selecao.get("pokemon_id"))
            if alvo is None:
                continue
            lado_alvo = _lado_pokemon(alvo)
            if lado_alvo is None or lado_alvo == lado_origem:
                continue
            dados = por_lado.setdefault(lado_alvo, {"pokemon_ids": set(), "areas": set()})
            dados["pokemon_ids"].add(_pid(alvo))
            area_alvo = _area_pokemon(alvo)
            if area_alvo:
                dados["areas"].add(str(area_alvo).upper())
            continue
        area_id = area_id_para_selecao(selecao, alvo_cfg)
        lado_alvo = _lado_area(partida, area_id)
        if lado_alvo is None or lado_alvo == lado_origem:
            continue
        dados = por_lado.setdefault(lado_alvo, {"pokemon_ids": set(), "areas": set()})
        for area_afetada in areas_afetadas_por_alvificacao(area_id, props, _lado_pokemon(pokemon), alvo_cfg, partida):
            area_afetada = str(area_afetada or "").upper()
            if not area_afetada:
                continue
            dados["areas"].add(area_afetada)
            ocupante = _pokemon_na_area(partida, area_afetada)
            if ocupante is not None:
                dados["pokemon_ids"].add(_pid(ocupante))
    for lado_alvo, dados in por_lado.items():
        provocadores = _provocadores_lado(partida, lado_alvo)
        if not provocadores:
            continue
        if any(_pid(provocador) in dados["pokemon_ids"] or str(_area_pokemon(provocador) or "").upper() in dados["areas"] for provocador in provocadores):
            continue
        return False
    return True


def resolver_alvos_reais_acao(partida, acao, props, usuario=None):
    if partida is None:
        return []
    usuario = usuario if usuario is not None else _obter_pokemon(partida, (acao or {}).get("pokemon_id"))
    lado_usuario = _lado_pokemon(usuario)
    alvos = []
    vistos = set()
    for selecao in selecoes_alvo_acao(acao, props):
        alvo_cfg = config_para_selecao(selecao, props)
        tipo_alvo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        if tipo_alvo == "pokemon":
            if not selecao.get("pokemon_id"):
                continue
            alvo = _obter_pokemon(partida, selecao.get("pokemon_id"))
            _adicionar_alvo_unico(alvos, vistos, alvo)
            continue
        area_id = area_id_para_selecao(selecao, alvo_cfg)
        if not area_id:
            continue
        for area_afetada in areas_afetadas_por_alvificacao(area_id, props, lado_usuario, alvo_cfg, partida):
            ocupante = _pokemon_na_area(partida, area_afetada)
            _adicionar_alvo_unico(alvos, vistos, ocupante)
    return alvos


def _adicionar_alvo_unico(alvos, vistos, pokemon):
    if pokemon is None:
        return
    chave = _pid(pokemon) or id(pokemon)
    if chave in vistos:
        return
    vistos.add(chave)
    alvos.append(pokemon)


def _lado_area_permitido(pokemon, area_id, area, alvo_cfg):
    permitidos = alvo_cfg.get("lados_permitidos")
    if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
        return True
    lado_area = _int_ou_none((area or {}).get("lado_id"))
    lado_origem = _lado_pokemon(pokemon)
    area_origem = str(_area_pokemon(pokemon) or "")
    for item in permitidos:
        token = str(item or "").strip().lower()
        if token in {"qualquer", "qualquer_lado", "todos", "ambos"}:
            return True
        if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"} and lado_area != lado_origem:
            return True
        if token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"} and lado_area == lado_origem:
            return True
        if token in {"usuario", "proprio", "si_mesmo"} and str(area_id) == area_origem:
            return True
    return False


def _lado_pokemon_permitido(pokemon, alvo, alvo_cfg):
    permitidos = alvo_cfg.get("lados_permitidos")
    if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
        return True
    lado_alvo = _lado_pokemon(alvo)
    lado_origem = _lado_pokemon(pokemon)
    for item in permitidos:
        token = str(item or "").strip().lower()
        if token in {"qualquer", "qualquer_lado", "todos", "ambos"}:
            return True
        if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"} and lado_alvo != lado_origem:
            return True
        if token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"} and lado_alvo == lado_origem:
            return True
        if token in {"usuario", "proprio", "si_mesmo"} and _pid(alvo) == _pid(pokemon):
            return True
    return False


def _provocadores_lado(partida, lado_id):
    por_lado = getattr(partida, "pokemons_por_lado", {}) or {}
    pokemons = por_lado.get(lado_id, [])
    return [p for p in pokemons if _esta_vivo(p) and _esta_ativo(p) and not _esta_reserva(p) and _possui_efeito(p, "Provocando")]


def _area(partida, area_id):
    areas = getattr(partida, "areas", {}) or {}
    chave = str(area_id or "").strip()
    return areas.get(chave) or areas.get(chave.upper())


def _lado_area(partida, area_id):
    area = _area(partida, area_id)
    if not isinstance(area, dict):
        return None
    return _int_ou_none(area.get("lado_id"))


def _pokemon_na_area(partida, area_id):
    func = getattr(partida, "pokemon_na_area", None)
    if callable(func):
        return func(area_id)
    return None


def _obter_pokemon(partida, pokemon_id):
    func = getattr(partida, "obter_pokemon", None)
    if callable(func):
        return func(pokemon_id)
    return None


def _pid(pokemon):
    return str(getattr(pokemon, "id_batalha", "") or "")


def _area_pokemon(pokemon):
    return getattr(pokemon, "area_id", None) or getattr(pokemon, "AreaId", None)


def _lado_pokemon(pokemon):
    return _int_ou_none(getattr(pokemon, "lado_id", None))


def _esta_vivo(pokemon):
    func = getattr(pokemon, "esta_vivo", None)
    if callable(func):
        return bool(func())
    return bool(getattr(pokemon, "vivo", True))


def _esta_ativo(pokemon):
    return bool(getattr(pokemon, "ativo", getattr(pokemon, "Ativo", False)))


def _esta_reserva(pokemon):
    return bool(getattr(pokemon, "reserva", getattr(pokemon, "Reserva", False)))


def _possui_efeito(pokemon, nome):
    func = getattr(pokemon, "possui_efeito", None)
    return bool(callable(func) and func(nome))


def _int_ou_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None
