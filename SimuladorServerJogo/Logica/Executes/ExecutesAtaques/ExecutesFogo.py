from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    alvos_linha_inimigos_area,
    aplicar_efeito,
    aplicar_mod_atributo,
    aplicar_status,
    area_selecionada_da_acao,
    dano_generico,
    dano_puro_ignorando_barreira,
    efeito_formal,
    executar_bola,
    executar_danca_clima,
    executar_raio,
    fnum,
    inimigos_vivos_adjacentes_ao_alvo,
    linha_ordenada_por_direcao,
    normalizar,
    obter_passos_efeito,
    pokemons_ativos_em_campo,
    remover_efeitos_contando_passos,
    resolver_critico_contextual,
)


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


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


def _lado(pokemon):
    try:
        return int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        return -1


def _inimigos_ativos(ctx):
    usuario = (ctx or {}).get("usuario")
    return [p for p in pokemons_ativos_em_campo((ctx or {}).get("partida")) if usuario is not None and _lado(p) != _lado(usuario)]


def _todos_ativos(ctx):
    return pokemons_ativos_em_campo((ctx or {}).get("partida"))


def _clima_sol_forte(ctx):
    return normalizar(getattr((ctx or {}).get("partida"), "clima_atual", "")) == "solforte"


def _exec_bola_de_fogo(ctx, alvo):
    return executar_bola(ctx, alvo, "fogo")


def _exec_queimar(ctx, alvo):
    return aplicar_status(ctx, alvo, "Queimado", duracao=_param(ctx, "duracao", 6), negativo=True)


def _exec_chama_interior(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None:
        return {"falha": True, "motivo": "usuario_invalido"}
    valor = usuario.obter_atributo("Mag") * _param(ctx, "mult_mag", 0.20)
    valor += usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Chama Interior", "SpA", valor, negativo=False)


def _exec_foguinho(ctx, alvo):
    usuario = ctx.get("usuario")
    passos = min(int(_param(ctx, "limite_passos", 12)), obter_passos_efeito(alvo, "Queimado"))
    mult = _param(ctx, "mult_spa", 0.35) + _param(ctx, "bonus_por_passo", 0.04) * passos
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    ret["passos_queimado_considerados"] = passos
    return ret


def _exec_investida_flamejante(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.85), "normal")
    if usuario is not None:
        ret["queimado_usuario"] = aplicar_status(ctx, usuario, "Queimado", duracao=_param(ctx, "duracao", 6), negativo=True)
    if alvo is not None and alvo.esta_vivo():
        ret["queimado_alvo"] = aplicar_status(ctx, alvo, "Queimado", duracao=_param(ctx, "duracao", 6), negativo=True)
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if usuario is not None and dano_vida > 0:
        ret["recuo"] = usuario.ReceberDano(
            dano_vida * _param(ctx, "percentual_recuo", 0.20),
            origem=usuario,
            dados={"recuo": "Investida Flamejante", "ignorar_defensivos": True, "reativos_acao": ctx.get("reativos_acao"), **_ataque_id_nome(ctx, "Investida Flamejante")},
        )
    return ret


def _exec_incendiar(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx)
    if partida is None or not area_id:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    if hasattr(partida, "mudar_terreno"):
        aplicado = partida.mudar_terreno(area_id, "Incendiada", origem=usuario, dados={**_ataque_id_nome(ctx, "Incendiar"), "reativos_acao": ctx.get("reativos_acao")})
        return {"aplicado": bool(aplicado), "area_id": area_id, "terreno": "Incendiada"}
    return {"falha": True, "motivo": "partida_sem_terreno"}


def _exec_estouro_solar(ctx, alvo):
    usuario = ctx.get("usuario")
    mult = _param(ctx, "multiplicador_sol_forte", 1.15) if _clima_sol_forte(ctx) else _param(ctx, "mult_spa", 0.85)
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")


def _aquecer_um(ctx, pokemon):
    usuario = ctx.get("usuario")
    info = remover_efeitos_contando_passos(pokemon, ["Encharcado", "Congelado"], origem=usuario, dados={**_ataque_id_nome(ctx, "Aquecer"), "motivo": "Aquecer"})
    passos = int(info.get("passos") or 0)
    mag = pokemon.obter_atributo("Mag") if pokemon is not None else 0.0
    cura = min(passos * mag * _param(ctx, "cura_por_passo", 0.03), mag * _param(ctx, "limite_cura", 0.30))
    ret_cura = pokemon.ReceberCura(cura, origem=usuario, dados={**_ataque_id_nome(ctx, "Aquecer"), "reativos_acao": ctx.get("reativos_acao")}) if pokemon is not None else {"aplicado": False}
    return {"pokemon_id": getattr(pokemon, "id_batalha", None), "passos_removidos": passos, "efeitos_removidos": info.get("removidos", 0), "cura": ret_cura}


def _exec_aquecer(ctx, alvo):
    usuario = ctx.get("usuario")
    alvos = []
    vistos = set()
    for pokemon in (alvo, usuario):
        pid = getattr(pokemon, "id_batalha", None)
        if pokemon is None or pid in vistos:
            continue
        vistos.add(pid)
        alvos.append(_aquecer_um(ctx, pokemon))
    return {"aplicado": True, "resultados": alvos}


def _exec_labareda(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial")
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["queimado"] = aplicar_status(ctx, alvo, "Queimado", duracao=_param(ctx, "duracao", 6), negativo=True)
    return ret


def _exec_ondas_de_calor(ctx, alvo):
    usuario = ctx.get("usuario")
    total_passos = sum(obter_passos_efeito(p, "Queimado") for p in _todos_ativos(ctx))
    passos = min(int(_param(ctx, "limite_passos", 25)), total_passos)
    mult = _param(ctx, "mult_spa", 0.45) + _param(ctx, "bonus_por_passo", 0.02) * passos
    extras = {}
    if _clima_sol_forte(ctx):
        extras["multiplicadores_condicionais"] = [{"label": "Ondas de Calor em Sol Forte", "multiplicador": 1.0 + _param(ctx, "bonus_sol_forte", 0.20)}]
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        resultados.append({"pokemon_id": inimigo.id_batalha, "resultado": dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * mult, "especial", **extras)})
    return {"aplicado": True, "alvos_atingidos": len(resultados), "passos_queimado_total": total_passos, "passos_queimado_considerados": passos, "resultados": resultados}


def _exec_fluxo_infernal(ctx, alvo):
    percentual = _param(ctx, "percentual_vida_atual", 0.50)
    valor = fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) * percentual
    return dano_puro_ignorando_barreira(ctx, alvo, valor, reducao_dur=True)


def _exec_inferno(ctx, alvo):
    usuario = ctx.get("usuario")
    resultados = []
    for pokemon in _todos_ativos(ctx):
        ret = dano_generico(ctx, pokemon, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.70), "especial")
        efeito = aplicar_status(ctx, pokemon, "Queimado", duracao=_param(ctx, "duracao", 6), negativo=True) if pokemon.esta_vivo() else None
        resultados.append({"pokemon_id": pokemon.id_batalha, "dano": ret, "queimado": efeito})
    return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_laser_de_fogo(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    if usuario is None or not area_id:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    resultados = []
    for idx, inimigo in enumerate(alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)):
        bruto = max(0.0, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.90) - usuario.obter_atributo("SpA") * _param(ctx, "reducao_por_alvo", 0.15) * idx)
        ret = dano_generico(ctx, inimigo, bruto, "especial")
        removidos = remover_efeitos_contando_passos(inimigo, ["Congelado", "Encharcado"], origem=usuario, dados={**_ataque_id_nome(ctx, "Laser de Fogo"), "motivo": "Laser de Fogo"})
        resultados.append({"pokemon_id": inimigo.id_batalha, "indice_hit": idx, "dano": ret, "efeitos_removidos": removidos})
    return {"aplicado": True, "area_id": area_id, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_ferver(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo_queimado = alvo is not None and alvo.possui_efeito("Queimado")
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.45)
    if alvo_queimado:
        bruto += usuario.obter_atributo("Mag") * _param(ctx, "mult_mag", 0.35)
    ret = dano_generico(ctx, alvo, bruto, "especial")
    ret["alvo_queimado"] = alvo_queimado
    return ret


def _exec_superaquecer(ctx, alvo):
    usuario = ctx.get("usuario")
    efeito = efeito_formal(alvo, "Queimado")
    if efeito is None:
        return {"aplicado": True, "sem_efeito": True, "motivo": "alvo_sem_queimado"}
    antes = max(0, int(fnum(efeito.get("passos_restantes"), 0.0)))
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="efeito")
    depois = antes * 2
    extra = int(_param(ctx, "passos_extra_critico", 2)) if critico_ctx.get("critico") else 0
    depois += extra
    efeito["passos_restantes"] = depois
    efeito["passos_totais"] = max(int(fnum(efeito.get("passos_totais"), 0.0)), depois)
    _registrar_log(
        ctx,
        "efeito_passos_alterados",
        {
            "pokemon_id": getattr(alvo, "id_batalha", None),
            "pokemon_nome": getattr(alvo, "nome", None),
            "efeito_nome": "Queimado",
            "passos_antes": antes,
            "passos_depois": depois,
            "passos_extra_critico": extra,
            "critico": bool(critico_ctx.get("critico")),
            **_ataque_id_nome(ctx, "Superaquecer"),
        },
    )
    return {"aplicado": True, "critico_contextual": critico_ctx, "passos_antes": antes, "passos_depois": depois, "passos_extra_critico": extra}


def _exec_queimadura_eterna(ctx, alvo):
    usuario = ctx.get("usuario")
    passos = int(_param(ctx, "queimado_passos_equivalentes", _param(ctx, "passos_equivalentes", 10)))
    return aplicar_efeito(
        usuario,
        alvo,
        "Queimado",
        duracao=passos,
        negativo=True,
        dados={
            "permanente": True,
            "passos_equivalentes": passos,
            "queimado_passos_equivalentes": passos,
            **_ataque_id_nome(ctx, "Queimadura Eterna"),
        },
    )


def _exec_erupcao(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 1.25),
        "especial",
        chance_critico=0,
        chance_critico_max=0,
    )


def _exec_explosao_ardente(ctx, alvo):
    usuario = ctx.get("usuario")
    base = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.85)
    splash = base * _param(ctx, "splash_pct", 0.60)
    adjacentes = inimigos_vivos_adjacentes_ao_alvo(ctx, alvo)
    alvo_principal_id = getattr(alvo, "id_batalha", None)
    secundarios_ids = [getattr(p, "id_batalha", None) for p in adjacentes if p is not None]
    ret = dano_generico(
        ctx,
        alvo,
        base,
        "especial",
        alvo_principal_id=alvo_principal_id,
        alvos_secundarios_ids=secundarios_ids,
        impacto_principal=True,
    )
    if alvo is not None and not alvo.esta_vivo():
        resultados = []
        for adjacente in adjacentes:
            resultados.append(
                {
                    "pokemon_id": adjacente.id_batalha,
                    "resultado": dano_generico(
                        ctx,
                        adjacente,
                        splash,
                        "especial",
                        alvo_principal_id=alvo_principal_id,
                        alvos_secundarios_ids=secundarios_ids,
                        impacto_secundario=True,
                    ),
                }
            )
        ret["splash"] = {"dano_bruto": round(splash, 4), "alvos_atingidos": len(resultados), "resultados": resultados}
    return ret


def _exec_jato_de_lava(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    if partida is None or usuario is None or not area_id:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    terreno = str((ctx.get("propriedades") or {}).get("parametros", {}).get("terreno_nome") or "Incendiada")
    linha = linha_ordenada_por_direcao(area_id, getattr(usuario, "lado_id", 50))
    terrenos = []
    for area_linha in linha:
        aplicado = partida.mudar_terreno(area_linha, terreno, origem=usuario, dados={**_ataque_id_nome(ctx, "Jato de Lava"), "reativos_acao": ctx.get("reativos_acao")})
        terrenos.append({"area_id": area_linha, "aplicado": bool(aplicado), "terreno": terreno})
    resultados = []
    for area_linha in linha:
        pokemon = partida.pokemon_na_area(area_linha)
        if pokemon is None or not pokemon.esta_vivo() or int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        resultados.append({"pokemon_id": pokemon.id_batalha, "area_id": area_linha, "resultado": dano_generico(ctx, pokemon, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.75), "especial")})
    return {"aplicado": True, "area_id": area_id, "linha": linha, "terrenos": terrenos, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_raio_de_fogo(ctx, alvo):
    return executar_raio(ctx, alvo, _param(ctx, "mult_spa", 1.00), _param(ctx, "reducao_por_alvo", 0.15), "fogo")


def _exec_danca_do_sol(ctx, alvo):
    return executar_danca_clima(ctx, "Sol Forte")


_EXECUTES = {
    "boladefogo": _exec_bola_de_fogo,
    "queimar": _exec_queimar,
    "chamainterior": _exec_chama_interior,
    "foguinho": _exec_foguinho,
    "investidaflamejante": _exec_investida_flamejante,
    "incendiar": _exec_incendiar,
    "estourosolar": _exec_estouro_solar,
    "aquecer": _exec_aquecer,
    "labareda": _exec_labareda,
    "ondasdecalor": _exec_ondas_de_calor,
    "fluxoinfernal": _exec_fluxo_infernal,
    "inferno": _exec_inferno,
    "laserdefogo": _exec_laser_de_fogo,
    "raiodefogo": _exec_laser_de_fogo,
    "ferver": _exec_ferver,
    "superaquecer": _exec_superaquecer,
    "queimaduraeterna": _exec_queimadura_eterna,
    "erupcao": _exec_erupcao,
    "explosaoardente": _exec_explosao_ardente,
    "jatodelava": _exec_jato_de_lava,
    "raiodefogo": _exec_raio_de_fogo,
    "dancadosol": _exec_danca_do_sol,
}

_ALIASES = {
    "25": "boladefogo",
    "26": "queimar",
    "27": "chamainterior",
    "28": "laserdefogo",
    "29": "dancadosol",
    "61": "foguinho",
    "62": "investidaflamejante",
    "63": "incendiar",
    "64": "estourosolar",
    "65": "aquecer",
    "66": "labareda",
    "67": "ondasdecalor",
    "68": "fluxoinfernal",
    "69": "inferno",
    "70": "laserdefogo",
    "71": "ferver",
    "72": "superaquecer",
    "73": "queimaduraeterna",
    "74": "erupcao",
    "75": "explosaoardente",
    "76": "jatodelava",
    "77": "raiodefogo",
    "78": "dancadosol",
    "queimaduraeterna": "queimaduraeterna",
    "erupcao": "erupcao",
    "explosaoardente": "explosaoardente",
    "jatodelava": "jatodelava",
    "raiodefogo": "raiodefogo",
    "dancadosol": "dancadosol",
}


def obter_executes_fogo():
    return dict(_EXECUTES)


def obter_passivas_ataques_fogo():
    return []


def obter_aliases_executes_fogo():
    return dict(_ALIASES)
