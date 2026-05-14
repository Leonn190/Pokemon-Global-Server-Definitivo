from __future__ import annotations

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    adjacentes_mesmo_lado,
    aplicar_mod_atributo,
    dano_generico,
    executar_danca_clima,
    fnum,
    normalizar,
    pokemons_ativos_em_campo,
)


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _param_lista(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    valor = parametros.get(chave, default)
    if isinstance(valor, (list, tuple, set)):
        return [str(item) for item in valor]
    if valor is None:
        return list(default or [])
    return [str(valor)]


def _param_texto(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return str(parametros.get(chave, default) or default)


def _ataque_id_nome(ctx, fallback):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return {
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or fallback,
    }


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _inimigos_ativos(ctx):
    usuario = (ctx or {}).get("usuario")
    partida = (ctx or {}).get("partida")
    if usuario is None:
        return []
    return [
        pokemon
        for pokemon in pokemons_ativos_em_campo(partida)
        if int(getattr(pokemon, "lado_id", -1)) != int(getattr(usuario, "lado_id", -2))
    ]


def _areas_lado_inimigo(ctx):
    usuario = (ctx or {}).get("usuario")
    partida = (ctx or {}).get("partida")
    if usuario is None or partida is None:
        return []
    return [
        str(area_id).upper()
        for area_id, area in sorted((getattr(partida, "areas", {}) or {}).items())
        if int((area or {}).get("lado_id", -1)) != int(getattr(usuario, "lado_id", -2))
    ]


def _terreno_area(ctx, area_id):
    partida = (ctx or {}).get("partida")
    if partida is None or not area_id:
        return None
    if hasattr(partida, "obter_terreno_area"):
        return partida.obter_terreno_area(area_id)
    dado = (getattr(partida, "efeitos_area", {}) or {}).get(str(area_id or "").upper())
    if isinstance(dado, dict):
        return dado.get("terreno") or dado.get("nome") or dado.get("efeito")
    return dado


def _limpar_terreno(ctx, area_id, motivo):
    partida = (ctx or {}).get("partida")
    if partida is None or not area_id:
        return False
    if hasattr(partida, "limpar_terreno"):
        return bool(partida.limpar_terreno(area_id, motivo=motivo))
    efeitos_area = getattr(partida, "efeitos_area", None)
    if isinstance(efeitos_area, dict) and str(area_id).upper() in efeitos_area:
        efeitos_area.pop(str(area_id).upper(), None)
        return True
    return False


def _mudar_terreno(ctx, area_id, terreno):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or not area_id:
        return False
    dados = _ataque_id_nome(ctx, "Terra")
    if hasattr(partida, "mudar_terreno"):
        return bool(partida.mudar_terreno(area_id, terreno, origem=usuario, dados=dados))
    efeitos_area = getattr(partida, "efeitos_area", None)
    if isinstance(efeitos_area, dict):
        efeitos_area[str(area_id).upper()] = {"terreno": terreno, "nome": terreno, **dados}
        return True
    return False


def _remover_defensivos(ctx, alvo, nomes):
    if alvo is None:
        return {"removidos": 0, "efeitos": []}
    removidos = []
    for nome in list(nomes or []):
        antes = 1 if hasattr(alvo, "possui_efeito") and alvo.possui_efeito(nome) else 0
        qtd = alvo.RemoverEfeito(nome) if hasattr(alvo, "RemoverEfeito") else 0
        if qtd or antes:
            removidos.append(str(nome))
    if "Protegido" in {str(nome) for nome in list(nomes or [])} and getattr(alvo, "estados_transitorios", None):
        if alvo.estados_transitorios.pop("protegido", None) is not None:
            removidos.append("Protegido")
    if removidos:
        _registrar_log(
            ctx,
            "pokemon_removeu_efeitos_defensivos",
            {
                "pokemon_id": getattr(alvo, "id_batalha", None),
                "pokemon_nome": getattr(alvo, "nome", None),
                "efeitos": removidos,
                **_ataque_id_nome(ctx, "Terra"),
            },
        )
    return {"removidos": len(removidos), "efeitos": removidos}


def _exec_rachar_terra(ctx, alvo):
    usuario = ctx.get("usuario")
    dur_base = _param(ctx, "dur_base", _param(ctx, "valor_base", 5.0))
    dur_mag_usuario_pct = _param(ctx, "dur_mag_usuario_pct", _param(ctx, "percentual_mag", 0.10))
    perda = dur_base + usuario.obter_atributo("Mag") * dur_mag_usuario_pct
    return aplicar_mod_atributo(ctx, alvo, "Rachar Terra", "Dur", -perda, 0, True)


def _exec_areia(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    em_tempestade = normalizar(getattr(partida, "clima_atual", "")) in {"tempestadedeareia", "tempestadeareia"}
    mult = _param(ctx, "dano_spa_pct_tempestade_areia", 0.70) if em_tempestade else _param(ctx, "dano_spa_pct", 0.35)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    if em_tempestade and alvo is not None:
        perda = alvo.obter_atributo("Def") * _param(ctx, "def_debuff_tempestade_areia_pct", 0.08)
        ret["def_debuff"] = aplicar_mod_atributo(ctx, alvo, "Areia", "Def", -perda, 0, True)
    return ret


def _exec_rachadura(ctx, alvo):
    usuario = ctx.get("usuario")
    base = usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.75)
    bonus = 0.0
    if _terreno_area(ctx, getattr(alvo, "area_id", None)):
        bonus += _param(ctx, "bonus_terreno_alvo_pct", 0.25)
    if _terreno_area(ctx, getattr(usuario, "area_id", None)):
        bonus += _param(ctx, "bonus_terreno_usuario_pct", 0.25)
    return dano_generico(ctx, alvo, base * (1.0 + bonus), "normal")


def _exec_dominio_do_solo(ctx, alvo):
    usuario = ctx.get("usuario")
    area_usuario = str(getattr(usuario, "area_id", "") or "").upper()
    areas = [area_usuario] if area_usuario else []
    if bool(_param(ctx, "incluir_adjacentes_diagonais", 1.0)):
        areas.extend(adjacentes_mesmo_lado(area_usuario))
    removidos = [area for area in areas if _limpar_terreno(ctx, area, "Dominio do Solo")]
    return {"aplicado": True, "terrenos_removidos": len(removidos), "areas": removidos}


def _exec_danca_da_areia(ctx, alvo):
    return executar_danca_clima(ctx, _param_texto(ctx, "clima", "Tempestade de Areia"))


def _exec_golpe_de_ossos(ctx, alvo):
    usuario = ctx.get("usuario")
    removidos = _remover_defensivos(ctx, alvo, _param_lista(ctx, "efeitos_remover", ["Protegido", "Evasivo", "Refletindo"]))
    ret = dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.80),
        "normal",
        ignorar_defensivos=bool(_param(ctx, "ignorar_defensivos", 1.0)),
    )
    ret["efeitos_removidos"] = removidos
    return ret


def _exec_queda_sismica(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.60)
    bruto += fnum(getattr(usuario, "VidaAtual", 0.0), 0.0) * _param(ctx, "dano_vida_atual_usuario_pct", 0.20)
    ret = dano_generico(ctx, alvo, bruto, "normal")
    recoil = fnum(getattr(usuario, "VidaAtual", 0.0), 0.0) * _param(ctx, "recoil_vida_atual_usuario_pct", 0.08)
    ret["recoil"] = usuario.ReceberDano(recoil, origem=usuario, dados={"recuo": "Queda Sismica", "ignorar_defensivos": True, "reativos_acao": ctx.get("reativos_acao"), **_ataque_id_nome(ctx, "Queda Sismica")})
    return ret


def _exec_tiro_de_lama(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "dano_spa_pct", 0.50), "especial")
    critico = bool(ret.get("critico"))
    mag_pct = _param(ctx, "mag_debuff_critico_pct", 0.12) if critico else _param(ctx, "mag_debuff_pct", 0.08)
    vel_pct = _param(ctx, "vel_debuff_critico_pct", 0.15) if critico else _param(ctx, "vel_debuff_pct", 0.10)
    ret["mag_debuff"] = aplicar_mod_atributo(ctx, alvo, "Tiro de Lama", "Mag", -(alvo.obter_atributo("Mag") * mag_pct), 0, True)
    ret["vel_debuff"] = aplicar_mod_atributo(ctx, alvo, "Tiro de Lama", "Vel", -(alvo.obter_atributo("Vel") * vel_pct), 0, True)
    return ret


def _exec_tremor_focalizado(ctx, alvo):
    usuario = ctx.get("usuario")
    _limpar_terreno(ctx, getattr(alvo, "area_id", None), "Tremor Focalizado")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.65)
    bruto += fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) * _param(ctx, "dano_vida_atual_alvo_pct", 0.15)
    ret = dano_generico(ctx, alvo, bruto, "normal")
    perda = alvo.obter_atributo("Def") * _param(ctx, "def_debuff_pct", 0.10)
    ret["def_debuff"] = aplicar_mod_atributo(ctx, alvo, "Tremor Focalizado", "Def", -perda, 0, True)
    return ret


def _exec_tremor(ctx, alvo):
    usuario = ctx.get("usuario")
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        ret = dano_generico(ctx, inimigo, usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.55), "normal")
        perda = inimigo.obter_atributo("Def") * _param(ctx, "def_debuff_pct", 0.08)
        ret["def_debuff"] = aplicar_mod_atributo(ctx, inimigo, "Tremor", "Def", -perda, 0, True)
        resultados.append({"pokemon_id": inimigo.id_batalha, "resultado": ret})
    return {"aplicado": True, "alvos": len(resultados), "resultados": resultados}


def _exec_quebra_chao(ctx, alvo):
    usuario = ctx.get("usuario")
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        ret = dano_generico(ctx, inimigo, usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.40), "normal")
        resultados.append({"pokemon_id": inimigo.id_batalha, "resultado": ret})
    recoil = fnum(getattr(usuario, "VidaAtual", 0.0), 0.0) * _param(ctx, "recoil_vida_atual_usuario_pct", 0.10)
    terreno = _param_texto(ctx, "terreno_inimigo", "Destruida")
    areas = [area for area in _areas_lado_inimigo(ctx) if _mudar_terreno(ctx, area, terreno)]
    return {
        "aplicado": True,
        "alvos": len(resultados),
        "resultados": resultados,
        "recoil": usuario.ReceberDano(recoil, origem=usuario, dados={"recuo": "Quebra Chao", "ignorar_defensivos": True, "reativos_acao": ctx.get("reativos_acao"), **_ataque_id_nome(ctx, "Quebra Chao")}),
        "terreno": terreno,
        "areas_alteradas": areas,
    }


def _exec_fissura(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.45), "normal")
    vida_max = max(1.0, alvo.obter_atributo("Vida", 1.0))
    limite = _param(ctx, "executar_abaixo_vida_pct", 0.45)
    if alvo.esta_vivo() and (fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) / vida_max) < limite:
        executou = alvo.Morrer({"origem_id": getattr(usuario, "id_batalha", None), "origem": usuario, "ataque": "Fissura", "ataque_nome": "Fissura", "execucao": True, "ignorar_defensivos": True, "reativos_acao": ctx.get("reativos_acao")})
        _registrar_log(ctx, "pokemon_executado", {"pokemon_id": alvo.id_batalha, "pokemon_nome": alvo.nome, "limite_vida_pct": limite, **_ataque_id_nome(ctx, "Fissura")})
        ret["execucao"] = bool(executou)
    return ret


def _exec_terremoto(ctx, alvo):
    usuario = ctx.get("usuario")
    efeitos = _param_lista(ctx, "efeitos_remover", ["Protegido", "Evasivo", "Refletindo"])
    areas_removidas = [area for area in _areas_lado_inimigo(ctx) if _limpar_terreno(ctx, area, "Terremoto")]
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        removidos = _remover_defensivos(ctx, inimigo, efeitos)
        ret = dano_generico(
            ctx,
            inimigo,
            usuario.obter_atributo("Atk") * _param(ctx, "dano_atk_pct", 0.75),
            "normal",
            ignorar_defensivos=bool(_param(ctx, "ignorar_defensivos", 1.0)),
        )
        ret["efeitos_removidos"] = removidos
        resultados.append({"pokemon_id": inimigo.id_batalha, "resultado": ret})
    return {"aplicado": True, "terrenos_removidos": len(areas_removidas), "areas_removidas": areas_removidas, "alvos": len(resultados), "resultados": resultados}


def _exec_poeira_nos_olhos(ctx, alvo):
    usuario = ctx.get("usuario")
    acuracia_alvo_pct = _param(ctx, "acuracia_alvo_pct", _param(ctx, "percentual_alvo", 0.10))
    mag_usuario_pct = _param(ctx, "mag_usuario_pct", _param(ctx, "percentual_mag", 0.10))
    valor = alvo.obter_atributo("Acu") * acuracia_alvo_pct + usuario.obter_atributo("Mag") * mag_usuario_pct
    return aplicar_mod_atributo(ctx, alvo, "Poeira nos Olhos", "Acu", -valor, 0, True)


_EXECUTES = {
    "racharterra": _exec_rachar_terra,
    "areia": _exec_areia,
    "rachadura": _exec_rachadura,
    "dominiodosolo": _exec_dominio_do_solo,
    "dancadaareia": _exec_danca_da_areia,
    "golpedeossos": _exec_golpe_de_ossos,
    "quedasismica": _exec_queda_sismica,
    "tirodelama": _exec_tiro_de_lama,
    "tremorfocalizado": _exec_tremor_focalizado,
    "tremor": _exec_tremor,
    "quebrachao": _exec_quebra_chao,
    "fissura": _exec_fissura,
    "terremoto": _exec_terremoto,
    "poeiranosolhos": _exec_poeira_nos_olhos,
}

_ALIASES = {
    "159": "racharterra",
    "160": "areia",
    "161": "rachadura",
    "162": "dominiodosolo",
    "163": "dancadaareia",
    "164": "golpedeossos",
    "165": "quedasismica",
    "166": "tirodelama",
    "167": "tremorfocalizado",
    "168": "tremor",
    "169": "quebrachao",
    "170": "fissura",
    "171": "terremoto",
    "172": "poeiranosolhos",
    "ataqueracharterra": "racharterra",
    "ataqueareia": "areia",
    "ataquerachadura": "rachadura",
    "ataquedominiodosolo": "dominiodosolo",
    "ataquedancadaareia": "dancadaareia",
    "ataquegolpedeossos": "golpedeossos",
    "ataquequedasismica": "quedasismica",
    "ataquetirodelama": "tirodelama",
    "ataquetremorfocalizado": "tremorfocalizado",
    "ataquetremor": "tremor",
    "ataquequebrachao": "quebrachao",
    "ataquefissura": "fissura",
    "ataqueterremoto": "terremoto",
    "ataquepoeiranosolhos": "poeiranosolhos",
}


def obter_executes_terrestre():
    return dict(_EXECUTES)


def obter_passivas_ataques_terrestre():
    return []


def obter_aliases_executes_terrestre():
    return dict(_ALIASES)
