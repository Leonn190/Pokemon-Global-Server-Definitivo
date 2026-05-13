from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    area_alvo_contexto,
    alvos_linha_inimigos_area,
    dano_generico,
    execute_passiva_nao_manual,
    executar_bola,
    executar_danca_clima,
    fnum,
    inimigos_vivos_adjacentes_area,
    inimigos_vivos_adjacentes_ao_alvo,
    normalizar,
    resolver_critico_contextual,
)


_CACHE_PROPS = None


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _props_por_code(code):
    global _CACHE_PROPS
    if _CACHE_PROPS is None:
        try:
            from SimuladorServerJogo.Batalha.PropriedadesAtaques import carregar_propriedades_ataques

            _CACHE_PROPS = carregar_propriedades_ataques()
        except Exception:
            _CACHE_PROPS = {}
    code = str(code or "").strip()
    return (_CACHE_PROPS or {}).get(code) if code else {}


def _param_passiva(ctx, chave, default):
    passiva = (ctx or {}).get("passiva")
    props = _props_por_code(getattr(passiva, "code", None))
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _ctx_passiva(ctx, dono, fallback):
    passiva = (ctx or {}).get("passiva")
    code = getattr(passiva, "code", None)
    props = _props_por_code(code)
    return {
        **dict(ctx or {}),
        "usuario": dono,
        "ataque": {"ID": code, "Code": code, "Nome": props.get("nome") or fallback},
        "propriedades": props,
    }


def _ataque_id_nome(ctx, fallback):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return {
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or fallback,
    }


def _lado(pokemon):
    try:
        return int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        return -1


def _aliados_ativos(ctx):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or usuario is None:
        return [usuario] if usuario is not None else []
    por_lado = getattr(partida, "pokemons_por_lado", {}) or {}
    return [
        p
        for p in list(por_lado.get(getattr(usuario, "lado_id", None), []))
        if p is not None and p.esta_vivo() and getattr(p, "ativo", False) and not getattr(p, "reserva", False)
    ]


def _ativos_vivos(ctx):
    partida = (ctx or {}).get("partida")
    if partida is None:
        return []
    return [
        p
        for p in list(getattr(partida, "pokemons_por_id", {}).values())
        if p is not None and p.esta_vivo() and getattr(p, "ativo", False) and not getattr(p, "reserva", False)
    ]


def _perder_energia(ctx, alvo, valor, motivo):
    if alvo is None:
        return {"aplicado": False, "motivo": "alvo_invalido"}
    usuario = (ctx or {}).get("usuario")
    antes = fnum(getattr(alvo, "EnergiaAtual", 0.0), 0.0)
    alvo.EnergiaAtual = max(0.0, antes - max(0.0, fnum(valor, 0.0)))
    real = max(0.0, antes - alvo.EnergiaAtual)
    if real > 0:
        _registrar_log(
            ctx,
            "pokemon_perdeu_energia",
            {
                "pokemon_id": alvo.id_batalha,
                "pokemon_nome": alvo.nome,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "origem_id": getattr(usuario, "id_batalha", None),
                "origem_nome": getattr(usuario, "nome", None),
                "valor": round(real, 4),
                "energia_antes": round(antes, 4),
                "energia_depois": round(alvo.EnergiaAtual, 4),
                "motivo": motivo,
                **_ataque_id_nome(ctx, motivo),
            },
        )
    return {"aplicado": True, "energia_removida": round(real, 4)}


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _exec_bola_de_agua(ctx, alvo):
    return executar_bola(ctx, alvo, "agua")


def _exec_gota_pesada(ctx, alvo):
    return aplicar_status(ctx, alvo, "Encharcado", negativo=True)


def _exec_splash(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    chance_falha = _param(ctx, "chance_falha", 0.5)
    rolagem = rng.random() if rng is not None else 1.0
    if rolagem < chance_falha:
        _registrar_log(
            ctx,
            "ataque_sem_efeito",
            {
                "pokemon_id": getattr(usuario, "id_batalha", None),
                "pokemon_nome": getattr(usuario, "nome", None),
                "alvo_id": getattr(alvo, "id_batalha", None),
                "alvo_nome": getattr(alvo, "nome", None),
                "motivo": "splash_nao_fez_nada",
                "chance_falha": round(chance_falha, 4),
                "rolagem": round(rolagem, 4),
                **_ataque_id_nome(ctx, "Splash"),
            },
        )
        return {"aplicado": True, "sem_efeito": True, "motivo": "splash_nao_fez_nada"}
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.70), "especial")


def _exec_bolhas(ctx, alvo):
    usuario = ctx.get("usuario")
    chave = "Bolhas"
    usos_anteriores = int(fnum(usuario.contadores_especiais.get(chave), 0.0))
    usos_considerados = min(usos_anteriores, int(_param(ctx, "max_acumulos", 6)))
    mult = _param(ctx, "base_spa", 0.35) + usos_considerados * _param(ctx, "bonus_spa_por_uso", 0.10)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    usuario.contadores_especiais[chave] = usos_anteriores + 1
    ret["usos_anteriores_bolhas"] = usos_anteriores
    ret["usos_considerados_bolhas"] = usos_considerados
    ret["usos_bolhas"] = usos_anteriores + 1
    return ret


def _exec_esguicho_suave(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    if _lado(usuario) != _lado(alvo):
        bruto = usuario.obter_atributo("SpA") * _param(ctx, "dano_spa", 0.45)
        bruto += usuario.obter_atributo("Mag") * _param(ctx, "dano_mag", 0.20)
        return dano_generico(ctx, alvo, bruto, "especial")
    cura = usuario.obter_atributo("Mag") * _param(ctx, "cura_mag", 0.45)
    cura += usuario.obter_atributo("SpA") * _param(ctx, "cura_spa", 0.15)
    ret = usuario.AplicarCura(alvo, cura, dados={**_ataque_id_nome(ctx, "Esguicho Suave"), "reativos_acao": ctx.get("reativos_acao")})
    removidos = alvo.RemoverEfeito("Queimado")
    if removidos:
        _registrar_log(ctx, "pokemon_removeu_efeito", {"pokemon_id": alvo.id_batalha, "pokemon_nome": alvo.nome, "efeito_nome": "Queimado", "motivo": "Esguicho Suave"})
    ret["queimado_removido"] = int(removidos)
    return ret


def _exec_jato_de_agua(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.65), "especial")
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["encharcado"] = aplicar_status(ctx, alvo, "Encharcado", negativo=True)
    return ret


def _exec_jato_multiplo(ctx, alvo, fallback_hits, fallback_mult):
    usuario = ctx.get("usuario")
    mult = _param(ctx, "mult_spa", fallback_mult)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["encharcado"] = aplicar_status(ctx, alvo, "Encharcado", negativo=True)
    return ret


def _exec_jato_duplo(ctx, alvo):
    return _exec_jato_multiplo(ctx, alvo, 2, 0.50)


def _exec_jato_triplo(ctx, alvo):
    return _exec_jato_multiplo(ctx, alvo, 3, 0.45)


def _exec_golpe_de_concha(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.45)
    bruto += usuario.obter_atributo("Def") * _param(ctx, "mult_def", 0.35)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_chuva_curativa(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    clima = normalizar(getattr(partida, "clima_atual", ""))
    mult = _param(ctx, "cura_chuva", 0.60) if clima == "chuva" else _param(ctx, "cura_base", 0.45)
    resultados = []
    for aliado in _aliados_ativos(ctx):
        resultados.append(usuario.AplicarCura(aliado, usuario.obter_atributo("Mag") * mult, dados={**_ataque_id_nome(ctx, "Chuva Curativa"), "reativos_acao": ctx.get("reativos_acao")}))
    return {"aplicado": True, "cura_chuva": clima == "chuva", "alvos_curados": len(resultados), "resultados": resultados}


def _exec_lanca_de_agua(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto_base = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.75)
    bruto_base += usuario.obter_atributo("Per") * _param(ctx, "mult_per", 0.20)
    mult_cadeia = 1.0
    ultimo = {}
    resultados = []
    area_id = area_alvo_contexto(ctx) or getattr(alvo, "area_id", None)
    for alvo_linha in alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo):
        ultimo = dano_generico(
            ctx,
            alvo_linha,
            bruto_base,
            "especial",
            multiplicadores_condicionais=[{"label": "Cadeia Lanca de Agua", "multiplicador": mult_cadeia}],
        )
        resultados.append(ultimo)
        if alvo_linha.possui_efeito("Encharcado"):
            mult_cadeia *= 1.0 + _param(ctx, "aumento_encharcado", 0.10)
        else:
            mult_cadeia *= 1.0 - _param(ctx, "reducao", 0.30)
    ultimo["alvos_linha"] = len(resultados)
    ultimo["resultados_linha"] = resultados
    return ultimo


def _exec_torrente_vital(ctx, alvo):
    usuario = ctx.get("usuario")
    alvos = [p for p in list(ctx.get("alvos") or []) if p is not None and p.esta_vivo()]
    aliado = next((p for p in alvos if _lado(p) == _lado(usuario)), None)
    inimigo = next((p for p in alvos if _lado(p) != _lado(usuario)), None)
    if aliado is None or inimigo is None:
        return {"falha": True, "motivo": "torrente_vital_exige_aliado_e_inimigo"}
    dano = dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial")
    dano_vida = fnum(dano.get("dano_vida"), 0.0)
    cura = usuario.AplicarCura(aliado, dano_vida * _param(ctx, "cura_dano", 0.40), dados={**_ataque_id_nome(ctx, "Torrente Vital"), "reativos_acao": ctx.get("reativos_acao")})
    dano["cura_aliado"] = cura
    return dano


def _exec_esfera_hidrocaotica(ctx, alvo):
    usuario = ctx.get("usuario")
    encharcado = alvo is not None and alvo.possui_efeito("Encharcado")
    extras = {}
    if encharcado and alvo is not None:
        defesa = max(0.0, alvo.obter_atributo("SpD") - (usuario.obter_atributo("Per") / 2.0))
        extras["multiplicadores_condicionais"] = [{"label": "Ignora SpD por Encharcado", "multiplicador": (100.0 + defesa) / 100.0}]
    area_id = area_alvo_contexto(ctx)
    secundarios = inimigos_vivos_adjacentes_ao_alvo(ctx, alvo) if alvo is not None else inimigos_vivos_adjacentes_area(ctx, area_id)
    alvo_principal_id = getattr(alvo, "id_batalha", None)
    secundarios_ids = [getattr(p, "id_batalha", None) for p in secundarios if p is not None]
    if alvo is None:
        ultimo = {"aplicado": True, "area_alvo": area_id, "impacto_area_vazia": True, "alvos_secundarios": len(secundarios)}
        for adjacente in secundarios:
            ultimo = dano_generico(ctx, adjacente, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.90) * _param(ctx, "adj_base", 0.25), "especial", alvos_secundarios_ids=secundarios_ids, impacto_secundario=True, area_alvo=area_id)
        return ultimo
    ret = dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.90),
        "especial",
        alvo_principal_id=alvo_principal_id,
        alvos_secundarios_ids=secundarios_ids,
        impacto_principal=True,
        **extras,
    )
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida > 0:
        frac = _param(ctx, "adj_encharcado", 0.35) if encharcado else _param(ctx, "adj_base", 0.25)
        for adjacente in secundarios:
            dano_generico(ctx, adjacente, dano_vida * frac, "especial", alvo_principal_id=alvo_principal_id, alvos_secundarios_ids=secundarios_ids, impacto_secundario=True)
    return ret


def _exec_cachoeira(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.80), "normal")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    rolagem = rng.random() if rng is not None else 1.0
    if alvo is not None and alvo.esta_vivo() and rolagem < _param(ctx, "chance_recuo", 0.25):
        ret["recuo"] = alvo.receber_recuo(origem=usuario, dados={**_ataque_id_nome(ctx, "Cachoeira"), "reativos_acao": ctx.get("reativos_acao")})
    ret["rolagem_recuo"] = round(rolagem, 4)
    return ret


def _exec_aguas_magicas(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Mag") * _param(ctx, "mult_mag", 0.85), "especial")


def _exec_fonte_termal(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    removidos = []
    restantes = []
    for efeito in list(getattr(alvo, "efeitos_formais", []) or []):
        nome = normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
        negativo = str((efeito or {}).get("tipo") or "").strip().lower() == "negativo" or nome in {"queimado", "envenenado", "intoxicado", "congelado", "dormindo", "paralisado", "enraizado", "cauterizado", "descarregado", "encharcado", "atordoado", "quebrado", "enfraquecido", "confuso", "bloqueado", "amaldicoado"}
        if negativo and not bool((efeito or {}).get("permanente")):
            removidos.append(efeito)
        else:
            restantes.append(efeito)
    alvo.efeitos_formais = restantes
    if hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    efeito = None
    if removidos:
        efeito = aplicar_status(ctx, alvo, "Encharcado", negativo=True)
    cura = usuario.AplicarCura(alvo, usuario.obter_atributo("Mag") * _param(ctx, "cura_mag", 0.30), dados={**_ataque_id_nome(ctx, "Fonte Termal"), "reativos_acao": ctx.get("reativos_acao")})
    return {"aplicado": True, "efeitos_removidos": len(removidos), "encharcado": efeito, "cura": cura}


def _exec_absorcao_total(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None:
        return {"falha": True, "motivo": "usuario_invalido"}
    removidos = 0
    for pokemon in _ativos_vivos(ctx):
        removidos += int(pokemon.RemoverEfeito("Encharcado") or 0)
    cura_total = removidos * usuario.obter_atributo("Mag") * _param(ctx, "cura_mag", 0.03)
    amp_total = removidos * usuario.obter_atributo("Mag") * _param(ctx, "amp_mag", 0.03)
    cura = usuario.ReceberCura(cura_total, origem=usuario, dados={**_ataque_id_nome(ctx, "Absorcao Total"), "reativos_acao": ctx.get("reativos_acao")})
    amp = aplicar_mod_atributo(ctx, usuario, "Absorcao Total", "Amp", amp_total, negativo=False)
    return {"aplicado": True, "encharcados_removidos": removidos, "cura": cura, "amp": amp}


def _exec_redemoinho(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    multiplicadores = []
    if normalizar(getattr(partida, "clima_atual", "")) == "chuva":
        multiplicadores.append({"label": "Redemoinho em Chuva", "multiplicador": _param(ctx, "mult_chuva", 1.20)})
    if alvo is not None and alvo.possui_efeito("Encharcado"):
        multiplicadores.append({"label": "Redemoinho em Encharcado", "multiplicador": _param(ctx, "mult_encharcado", 1.20)})
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.70), "especial", multiplicadores_condicionais=multiplicadores)


def _exec_geiser(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.85), "especial")
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        perda = alvo.obter_atributo("SpD") * _param(ctx, "percentual_spd_critico", 0.15)
        ret["reducao_spd"] = aplicar_mod_atributo(ctx, alvo, "Geiser", "SpD", -perda, negativo=True)
    return ret


def _exec_mergulho(ctx, alvo):
    usuario = ctx.get("usuario")
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="efeito")
    chance = _param(ctx, "chance_critico", 0.70) if critico_ctx.get("critico") else _param(ctx, "chance_base", 0.50)
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    rolagem = rng.random() if rng is not None else 1.0
    efeito = None
    if rolagem <= chance:
        efeito = aplicar_status(ctx, usuario, "Evasivo", duracao=_param(ctx, "duracao", 3), negativo=False)
    return {"aplicado": True, "critico_contextual": critico_ctx, "chance": round(chance, 4), "rolagem": round(rolagem, 4), "evasivo": efeito}


def _exec_diluvio(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    ja_chovia = normalizar(getattr(partida, "clima_atual", "")) == "chuva"
    mult = _param(ctx, "mult_se_ja_chuva", 2.0) if ja_chovia else 1.0
    amp = _param(ctx, "amp", 3.0) * mult
    energia = _param(ctx, "energia", 10.0) * mult
    aliados = []
    inimigos = []
    for pokemon in _ativos_vivos(ctx):
        if _lado(pokemon) == _lado(usuario):
            aliados.append({
                "pokemon_id": pokemon.id_batalha,
                "amp": aplicar_mod_atributo(ctx, pokemon, "Diluvio", "Amp", amp, negativo=False),
                "energia": pokemon.GanharEnergia(energia, dados={"ataque": "Diluvio", "motivo": "Diluvio", "reativos_acao": ctx.get("reativos_acao")}),
            })
        else:
            inimigos.append({
                "pokemon_id": pokemon.id_batalha,
                "amp": aplicar_mod_atributo(ctx, pokemon, "Diluvio", "Amp", -amp, negativo=True),
                "energia": _perder_energia(ctx, pokemon, energia, "Diluvio"),
            })
    clima = executar_danca_clima(ctx, "Chuva")
    return {"aplicado": True, "ja_chovia": ja_chovia, "multiplicador": mult, "aliados": aliados, "inimigos": inimigos, "clima": clima}


def _coluna_area(area_id):
    area = str(area_id or "").strip().upper()
    try:
        idx = int(area[1:]) - 1
    except (TypeError, ValueError, IndexError):
        return 2
    return max(0, min(2, idx % 3))


def _exec_tsunami(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    base = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.85)
    bonus_max = _param(ctx, "bonus_esquerda_max", 0.35)
    chance = _param(ctx, "chance_encharcar", 0.35)
    resultados = []
    for pokemon in _ativos_vivos(ctx):
        coluna = _coluna_area(getattr(pokemon, "area_id", None))
        mult = 1.0 + bonus_max * max(0.0, (2 - coluna) / 2.0)
        ret = dano_generico(ctx, pokemon, base, "especial", multiplicadores_condicionais=[{"label": "Tsunami coluna visual", "multiplicador": mult}])
        if _lado(pokemon) != _lado(usuario) and pokemon.esta_vivo():
            rolagem = rng.random() if rng is not None else 1.0
            ret["rolagem_encharcar"] = round(rolagem, 4)
            if rolagem <= chance:
                ret["encharcado"] = aplicar_status(ctx, pokemon, "Encharcado", negativo=True)
        resultados.append({"pokemon_id": pokemon.id_batalha, "area_id": getattr(pokemon, "area_id", None), "coluna": coluna, "multiplicador": round(mult, 4), "resultado": ret})
    return {"aplicado": True, "alvos": len(resultados), "resultados": resultados}


def _exec_martelo_caranguejo(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 1.00), "normal")


def _exec_golpe_abissal(ctx, alvo):
    usuario = ctx.get("usuario")
    vida_max = max(1.0, alvo.obter_atributo("Vida", 1.0)) if alvo is not None else 1.0
    alvo_baixo = alvo is not None and (alvo.VidaAtual / vida_max) < _param(ctx, "limite_vida", 0.40)
    extras = {}
    if alvo_baixo:
        extras["multiplicadores_condicionais"] = [{"label": "Alvo com vida baixa", "multiplicador": _param(ctx, "mult_alvo_baixo", 1.35)}]
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.75), "normal", **extras)
    if alvo is not None:
        removidos = alvo.RemoverEfeito("Provocando")
        ret["provocando_removido"] = int(removidos)
        if removidos:
            _registrar_log(ctx, "pokemon_removeu_efeito", {"pokemon_id": alvo.id_batalha, "pokemon_nome": alvo.nome, "efeito_nome": "Provocando", "motivo": "Golpe Abissal"})
    return ret


def _exec_controle_do_oceano(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    area_id = area_alvo_contexto(ctx) or getattr(alvo, "area_id", None)
    area_id = str(area_id or "").strip().upper()
    if partida is None or usuario is None or len(area_id) < 2 or area_id[0] not in {"A", "I"}:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    try:
        linha = (int(area_id[1:]) - 1) // 3
    except (TypeError, ValueError):
        return {"falha": True, "motivo": "area_alvo_invalida"}
    lado_area = int((getattr(partida, "areas", {}).get(area_id) or {}).get("lado_id", -1))
    prefixo = area_id[0]
    destinos = [f"{prefixo}{linha * 3 + coluna + 1}" for coluna in range(3)]
    candidatos = [
        p
        for p in list((getattr(partida, "pokemons_por_lado", {}) or {}).get(lado_area, []))
        if p is not None and p.esta_vivo() and getattr(p, "ativo", False) and not getattr(p, "reserva", False)
        and (not hasattr(p, "pode_ser_movido_por_ataque") or p.pode_ser_movido_por_ataque())
    ]
    candidatos.sort(key=lambda p: (_coluna_area(getattr(p, "area_id", None)), str(getattr(p, "id_batalha", ""))))
    candidatos_ids = {p.id_batalha for p in candidatos}
    livres = [dest for dest in destinos if getattr(partida, "ocupacao_areas", {}).get(dest) in {None, *candidatos_ids}]
    movimentos = []
    for pokemon, destino in zip(candidatos, livres):
        origem = pokemon.area_id
        if origem == destino:
            movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": destino, "moveu": False})
            continue
        if origem in getattr(partida, "ocupacao_areas", {}) and partida.ocupacao_areas.get(origem) == pokemon.id_batalha:
            partida.ocupacao_areas[origem] = None
            partida.areas[origem]["ocupante_id"] = None
        pokemon.area_id = destino
        pokemon.ativo = True
        pokemon.reserva = False
        partida.ocupacao_areas[destino] = pokemon.id_batalha
        partida.areas[destino]["ocupante_id"] = pokemon.id_batalha
        movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": destino, "moveu": True})
        _registrar_log(ctx, "pokemon_moveu", {"pokemon_id": pokemon.id_batalha, "pokemon_nome": pokemon.nome, "area_origem": origem, "area_destino": destino, **_ataque_id_nome(ctx, "Controle do Oceano")})
        if hasattr(partida, "disparar_flag"):
            partida.disparar_flag("AoMover", {"partida": partida, "pokemon_evento": pokemon, "pokemon": pokemon, "area_antes": origem, "area_depois": destino, "origem": usuario, "dados": {"ataque": "Controle do Oceano"}, "reativos_acao": ctx.get("reativos_acao")}, reativos=ctx.get("reativos_acao"))
    return {"aplicado": True, "lado_id": lado_area, "linha": linha, "movimentos": movimentos}


def _exec_surfar(ctx, alvo):
    usuario = ctx.get("usuario")
    vivo_antes = alvo is not None and alvo.esta_vivo()
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.85), "especial")
    if vivo_antes and alvo is not None and not alvo.esta_vivo():
        energia = fnum(ctx.get("custo_real"), 0.0)
        ret["energia_recuperada"] = usuario.GanharEnergia(energia, dados={"ataque": "Surfar", "motivo": "Surfar", "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_correnteza(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "mult_mag", _param(ctx, "percentual_mag", 0.20))
    valor += usuario.obter_atributo("Vel") * _param(ctx, "mult_vel", _param(ctx, "percentual_usuario_atributo", 0.10))
    return aplicar_mod_atributo(ctx, usuario, "Correnteza", "Vel", valor, 6, False)


def _exec_danca_da_chuva(ctx, alvo):
    return executar_danca_clima(ctx, "Chuva")


def _passiva_pele_aquatica(ctx):
    dono = ctx.get("dono_passiva")
    partida = ctx.get("partida")
    if dono is None or not dono.esta_vivo() or not getattr(dono, "ativo", False) or getattr(dono, "reserva", False):
        return {}
    stacks = (1 if dono.possui_efeito("Encharcado") else 0) + (1 if normalizar(getattr(partida, "clima_atual", "")) == "chuva" else 0)
    if stacks <= 0:
        return {}
    vida_max = max(1.0, dono.obter_atributo("Vida", 1.0))
    faltante = max(0.0, vida_max - dono.VidaAtual)
    cura = faltante * _param_passiva(ctx, "percentual_vida_perdida", 0.05) * stacks
    ret = dono.ReceberCura(cura, origem=dono, dados={**_ataque_id_nome(_ctx_passiva(ctx, dono, "Pele Aquatica"), "Pele Aquatica"), "passiva": "Pele Aquatica"})
    return {"passiva": "Pele Aquatica", "stacks": stacks, "cura": ret}


def _passiva_drenagem_hidrica(ctx):
    dono = ctx.get("dono_passiva")
    alvo = ctx.get("alvo")
    resultado = ctx.get("resultado") if isinstance(ctx.get("resultado"), dict) else {}
    if dono is None or alvo is None or not alvo.possui_efeito("Encharcado"):
        return {}
    dano_vida = fnum(resultado.get("dano_vida"), 0.0)
    if dano_vida <= 0:
        return {}
    pctx = _ctx_passiva(ctx, dono, "Drenagem Hidrica")
    cura = dono.ReceberCura(dano_vida * _param_passiva(ctx, "percentual_cura", 0.30), origem=dono, dados={**_ataque_id_nome(pctx, "Drenagem Hidrica"), "passiva": "Drenagem Hidrica"})
    energia = None
    estado = ctx.get("estado_execucao_ataque") if isinstance(ctx.get("estado_execucao_ataque"), dict) else {}
    chave = f"drenagem_hidrica_energia_{getattr(dono, 'id_batalha', '')}"
    if not estado.get(chave):
        estado[chave] = True
        energia = dono.GanharEnergia(fnum(ctx.get("custo_real"), 0.0) * _param_passiva(ctx, "percentual_energia", 0.20), dados={"ataque": "Drenagem Hidrica", "motivo": "Drenagem Hidrica", "passiva": True})
    return {"passiva": "Drenagem Hidrica", "cura": cura, "energia": energia}


def _passiva_nadador(ctx):
    return {"passiva": "Nadador", "condicional": "Chuva"}


def _passiva_reservatorio(ctx):
    dono = ctx.get("dono_passiva")
    partida = ctx.get("partida")
    if dono is None or not dono.esta_vivo() or not getattr(dono, "ativo", False) or getattr(dono, "reserva", False):
        return {}
    if normalizar(getattr(partida, "clima_atual", "")) != "chuva":
        return {}
    pctx = _ctx_passiva(ctx, dono, "Reservatorio")
    amp = aplicar_mod_atributo(pctx, dono, "Reservatorio", "Amp", _param_passiva(ctx, "amp_por_turno", 1.0), negativo=False)
    return {"passiva": "Reservatorio", "amp": amp}


_EXECUTES = {
    "boladeagua": _exec_bola_de_agua,
    "gotapesada": _exec_gota_pesada,
    "splash": _exec_splash,
    "bolhas": _exec_bolhas,
    "esguichosuave": _exec_esguicho_suave,
    "jatodeagua": _exec_jato_de_agua,
    "jatoduplo": _exec_jato_duplo,
    "jatotriplo": _exec_jato_triplo,
    "golpedeconcha": _exec_golpe_de_concha,
    "chuvacurativa": _exec_chuva_curativa,
    "lancadeagua": _exec_lanca_de_agua,
    "torrentevital": _exec_torrente_vital,
    "esferahidrocaotica": _exec_esfera_hidrocaotica,
    "cachoeira": _exec_cachoeira,
    "aguasmagicas": _exec_aguas_magicas,
    "fontetermal": _exec_fonte_termal,
    "absorcaototal": _exec_absorcao_total,
    "redemoinho": _exec_redemoinho,
    "geiser": _exec_geiser,
    "peleaquatica": execute_passiva_nao_manual,
    "mergulho": _exec_mergulho,
    "diluvio": _exec_diluvio,
    "tsunami": _exec_tsunami,
    "martelocaranguejo": _exec_martelo_caranguejo,
    "golpeabissal": _exec_golpe_abissal,
    "nadador": execute_passiva_nao_manual,
    "drenagemhidrica": execute_passiva_nao_manual,
    "controledooceano": _exec_controle_do_oceano,
    "surfar": _exec_surfar,
    "reservatorio": execute_passiva_nao_manual,
    "correnteza": _exec_correnteza,
    "dancadachuva": _exec_danca_da_chuva,
}

_ALIASES = {
    "26": "boladeagua",
    "27": "gotapesada",
    "28": "splash",
    "29": "bolhas",
    "30": "esguichosuave",
    "31": "jatodeagua",
    "32": "jatoduplo",
    "33": "jatotriplo",
    "34": "golpedeconcha",
    "35": "chuvacurativa",
    "36": "lancadeagua",
    "37": "torrentevital",
    "38": "esferahidrocaotica",
    "39": "cachoeira",
    "40": "aguasmagicas",
    "41": "fontetermal",
    "42": "absorcaototal",
    "43": "redemoinho",
    "44": "geiser",
    "45": "peleaquatica",
    "46": "mergulho",
    "47": "diluvio",
    "48": "tsunami",
    "49": "martelocaranguejo",
    "50": "golpeabissal",
    "51": "nadador",
    "52": "drenagemhidrica",
    "53": "controledooceano",
    "54": "surfar",
    "55": "reservatorio",
    "56": "correnteza",
    "57": "dancadachuva",
}


def obter_executes_agua():
    return dict(_EXECUTES)


def obter_passivas_ataques_agua():
    return [
        {"nome": "Pele Aquatica", "flag": "AoFimDaRodada", "grupo": "self", "func": _passiva_pele_aquatica, "origem": "ataque", "code": "45"},
        {"nome": "Nadador", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_nadador, "origem": "ataque", "code": "51"},
        {"nome": "Drenagem Hidrica", "flag": "AoAplicarDano", "grupo": "self", "func": _passiva_drenagem_hidrica, "origem": "ataque", "code": "52"},
        {"nome": "Reservatorio", "flag": "AoFimDaRodada", "grupo": "self", "func": _passiva_reservatorio, "origem": "ataque", "code": "55"},
    ]


def obter_aliases_executes_agua():
    return dict(_ALIASES)
