from __future__ import annotations

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    ATRIBUTOS_REGULARES,
    aplicar_mod_atributo,
    aplicar_status,
    dano_generico,
    execute_passiva_nao_manual,
    fnum,
    resolver_critico_contextual,
)


_CACHE_PROPS = None


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return parametros.get(chave, default)


def _fparam(ctx, chave, default):
    return fnum(_param(ctx, chave, default), default)


def _props_por_code(code):
    global _CACHE_PROPS
    if _CACHE_PROPS is None:
        try:
            from Servidor.Batalha.PropriedadesAtaques import carregar_propriedades_ataques

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


def _vida_perdida(pokemon):
    if pokemon is None:
        return 0.0
    vida_max = max(1.0, fnum(pokemon.obter_atributo("Vida", 1.0), 1.0))
    return max(0.0, vida_max - fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0))


def _contador_alvo(alvo, chave):
    return int(fnum(getattr(alvo, "contadores_especiais", {}).get(chave), 0.0))


def _incrementar_contador_alvo(alvo, chave):
    alvo.contadores_especiais[chave] = _contador_alvo(alvo, chave) + 1
    return alvo.contadores_especiais[chave]


def _chance_forcar_critico(critico_ctx):
    excedente = fnum((critico_ctx or {}).get("bonus_crd_excedente"), 0.0) * 2.0
    return 100.0 + excedente if (critico_ctx or {}).get("critico") else 0.0


def _areas_tesoura_x(ctx):
    usuario = (ctx or {}).get("usuario")
    posicoes = list(_param(ctx, "posicoes_inimigas", [1, 3, 5, 7, 9]) or [1, 3, 5, 7, 9])
    prefixo = "I" if int(getattr(usuario, "lado_id", 50)) == 50 else "A"
    return [f"{prefixo}{int(posicao)}" for posicao in posicoes]


def _exec_regeneracao(ctx, alvo):
    return aplicar_status(ctx, alvo, "Regeneração", negativo=False)


def _passiva_regenerador(ctx):
    dono = (ctx or {}).get("dono_passiva") or (ctx or {}).get("pokemon_evento")
    if dono is None or not dono.esta_vivo():
        return {}
    pctx = _ctx_passiva(ctx, dono, "Regenerador")
    cura = dono.obter_atributo("Mag") * _param_passiva(ctx, "mag_pct", 0.06)
    cura += _vida_perdida(dono) * _param_passiva(ctx, "vida_perdida_pct", 0.02)
    ret = dono.ReceberCura(cura, origem=dono, dados={**_ataque_id_nome(pctx, "Regenerador"), "passiva": "Regenerador"})
    return {"passiva": "Regenerador", "cura": ret}


def _exec_seda(ctx, alvo):
    usuario = ctx.get("usuario")
    usos_anteriores = _contador_alvo(alvo, "seda_usos")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _fparam(ctx, "spa_pct", 0.35), "especial")
    perda_vel = alvo.obter_atributo("Vel") * (
        _fparam(ctx, "vel_base_pct", 0.03) + usos_anteriores * _fparam(ctx, "vel_stack_pct", 0.01)
    )
    ret["velocidade"] = aplicar_mod_atributo(ctx, alvo, "Seda", "Vel", -perda_vel, negativo=True)
    ret["usos_anteriores_seda"] = usos_anteriores
    ret["usos_seda"] = _incrementar_contador_alvo(alvo, "seda_usos")
    return ret


def _exec_casulo_improvisado(ctx, alvo):
    usuario = ctx.get("usuario")
    barreira = _vida_perdida(usuario) * _fparam(ctx, "vida_perdida_pct", 0.75)
    barreira += usuario.obter_atributo("Mag") * _fparam(ctx, "mag_pct", 0.05)
    ret = {
        "barreira": usuario.AplicarBarreira(
            usuario,
            barreira,
            dados={
                **_ataque_id_nome(ctx, "Casulo Improvisado"),
                "reativos_acao": ctx.get("reativos_acao"),
                "calculo": [
                    f"Vida perdida * vida_perdida_pct = {round(_vida_perdida(usuario), 4)} * {round(_fparam(ctx, 'vida_perdida_pct', 0.75), 4)}",
                    f"Mag * mag_pct = {round(usuario.obter_atributo('Mag'), 4)} * {round(_fparam(ctx, 'mag_pct', 0.05), 4)}",
                    f"Barreira final = {round(barreira, 4)}",
                ],
            },
        )
    }
    ret["enraizado"] = aplicar_status(ctx, usuario, "Enraizado", negativo=True)
    return ret


def _exec_mordida_de_inseto(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _fparam(ctx, "atk_pct", 0.80), "normal")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    vamp_atual = usuario.obter_atributo("Vamp")
    if ret.get("critico") and dano_vida > 0 and vamp_atual > 0:
        ret["cura_vamp_extra_critico"] = usuario.ReceberCura(
            dano_vida * (vamp_atual / 100.0) * max(0.0, _fparam(ctx, "vamp_crit_mult", 2.0) - 1.0),
            origem=usuario,
            dados={**_ataque_id_nome(ctx, "Mordida de Inseto"), "critico": True, "motivo": "Mordida de Inseto", "reativos_acao": ctx.get("reativos_acao")},
        )
    return ret


def _exec_doacao_de_energia(ctx, alvo):
    usuario = ctx.get("usuario")
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="energia")
    energia = fnum(ctx.get("custo_real"), 0.0) * (
        _fparam(ctx, "energia_pct_critico", 0.85) if critico_ctx.get("critico") else _fparam(ctx, "energia_pct", 0.60)
    )
    ret = alvo.GanharEnergia(
        energia,
        dados={**_ataque_id_nome(ctx, "Doação de Energia"), "motivo": "Doação de Energia", "critico": bool(critico_ctx.get("critico")), "reativos_acao": ctx.get("reativos_acao")},
    )
    return {"aplicado": True, "energia": ret, "critico_contextual": critico_ctx}


def _exec_corte_serrilhado(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _fparam(ctx, "atk_pct", 0.55)
    bruto += usuario.obter_atributo("Per") * _fparam(ctx, "per_pct", 0.25)
    bruto += alvo.obter_atributo("Dur") * _fparam(ctx, "dur_alvo_pct", 2.00)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_carcomer(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _fparam(ctx, "atk_pct", 0.70), "normal")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    vida_max_alvo = max(1.0, alvo.obter_atributo("Vida", 1.0))
    percentual = min(
        _fparam(ctx, "cura_pct_max", 0.80),
        max(0.0, (vida_max_alvo - fnum(getattr(alvo, "VidaAtual", 0.0), 0.0)) / vida_max_alvo),
    )
    ret["cura"] = usuario.ReceberCura(
        dano_vida * percentual,
        origem=usuario,
        dados={**_ataque_id_nome(ctx, "Carcomer"), "motivo": "Carcomer", "reativos_acao": ctx.get("reativos_acao")},
    )
    ret["percentual_cura"] = round(percentual, 4)
    return ret


def _exec_evolucao_incerta(ctx, alvo):
    usuario = ctx.get("usuario")
    atributos = list(_param(ctx, "atributos_regulares", ATRIBUTOS_REGULARES) or ATRIBUTOS_REGULARES)
    snapshot = {atributo: usuario.obter_atributo(atributo) for atributo in atributos}
    ordem = {atributo: idx for idx, atributo in enumerate(atributos)}
    menores = sorted(atributos, key=lambda atributo: (snapshot[atributo], ordem[atributo]))[: int(_fparam(ctx, "qtd_menores", 2))]
    maiores = sorted(atributos, key=lambda atributo: (-snapshot[atributo], ordem[atributo]))[: int(_fparam(ctx, "qtd_maiores", 2))]
    resultados = {"menores": [], "maiores": [], "snapshot": snapshot}
    for atributo in menores:
        valor = -snapshot[atributo] * _fparam(ctx, "perda_pct", 0.20)
        resultados["menores"].append({"atributo": atributo, "valor": valor, "resultado": aplicar_mod_atributo(ctx, usuario, "Evolução Incerta", atributo, valor, negativo=True)})
    for atributo in maiores:
        valor = snapshot[atributo] * _fparam(ctx, "ganho_pct", 0.25)
        resultados["maiores"].append({"atributo": atributo, "valor": valor, "resultado": aplicar_mod_atributo(ctx, usuario, "Evolução Incerta", atributo, valor, negativo=False)})
    resultados["aplicado"] = True
    return resultados


def _exec_infestacao(ctx, alvo):
    usuario = ctx.get("usuario")
    usos_anteriores = _contador_alvo(alvo, "infestacao_usos")
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="infestacao")
    multiplicadores = []
    if critico_ctx.get("critico") and usos_anteriores > 0:
        multiplicadores.append(
            {
                "label": "Bônus por Infestação anterior",
                "multiplicador": 1.0 + usos_anteriores * _fparam(ctx, "crit_stack_dano_pct", 0.15),
            }
        )
    chance_critico = _chance_forcar_critico(critico_ctx)
    ret = dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("SpA") * _fparam(ctx, "spa_pct", 0.65),
        "especial",
        multiplicadores_condicionais=multiplicadores,
        chance_critico=chance_critico,
        chance_critico_max=chance_critico,
    )
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if critico_ctx.get("critico") and dano_vida > 0:
        ret["cura_critica"] = usuario.ReceberCura(
            dano_vida * _fparam(ctx, "crit_cura_dano_pct", 0.10),
            origem=usuario,
            dados={**_ataque_id_nome(ctx, "Infestação"), "critico": True, "motivo": "Infestação", "reativos_acao": ctx.get("reativos_acao")},
        )
    ret["critico_contextual"] = critico_ctx
    ret["usos_anteriores_infestacao"] = usos_anteriores
    ret["usos_infestacao"] = _incrementar_contador_alvo(alvo, "infestacao_usos")
    return ret


def _exec_tesoura_x(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    if usuario is None or partida is None:
        return {"falha": True, "motivo": "partida_invalida"}
    bruto = usuario.obter_atributo("Atk") * _fparam(ctx, "atk_pct", 0.65)
    resultados = []
    for area_id in _areas_tesoura_x(ctx):
        alvo_area = partida.pokemon_na_area(area_id)
        if alvo_area is None or not alvo_area.esta_vivo() or int(getattr(alvo_area, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            resultados.append({"area_id": area_id, "area_vazia": alvo_area is None, "aplicado": False})
            continue
        extras = {}
        if str(area_id).upper().endswith("5"):
            extras["multiplicadores_condicionais"] = [{"label": "Posição 5", "multiplicador": _fparam(ctx, "mult_posicao_5", 1.35)}]
        ret = dano_generico(ctx, alvo_area, bruto, "normal", area_alvo=area_id, **extras)
        resultados.append({"area_id": area_id, "pokemon_id": alvo_area.id_batalha, "dano": ret})
    return {"aplicado": True, "areas": _areas_tesoura_x(ctx), "resultados": resultados}


def _exec_canibalismo_filial(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    if int(getattr(alvo, "lado_id", -1)) != int(getattr(usuario, "lado_id", -2)):
        return {"falha": True, "motivo": "alvo_nao_aliado"}
    if str(getattr(alvo, "id_batalha", "")) == str(getattr(usuario, "id_batalha", "")):
        return {"falha": True, "motivo": "alvo_nao_pode_ser_o_proprio_usuario"}
    vida_max = max(1.0, alvo.obter_atributo("Vida", 1.0))
    if fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) / vida_max > _fparam(ctx, "limite_vida_alvo_pct", 0.30):
        return {"falha": True, "motivo": "alvo_com_vida_acima_do_limite"}
    matou = alvo.Morrer({"origem_id": usuario.id_batalha, "origem": usuario, "ataque": "Canibalismo Filial", "ataque_nome": "Canibalismo Filial", "reativos_acao": ctx.get("reativos_acao")})
    if not matou:
        return {"falha": True, "motivo": "morte_falhou"}
    cura = _vida_perdida(usuario) * _fparam(ctx, "cura_vida_perdida_usuario_pct", 0.85)
    return {
        "aplicado": True,
        "alvo_abatido": alvo.id_batalha,
        "cura": usuario.ReceberCura(cura, origem=usuario, dados={**_ataque_id_nome(ctx, "Canibalismo Filial"), "motivo": "Canibalismo Filial", "reativos_acao": ctx.get("reativos_acao")}),
    }


def _exec_devorar(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _fparam(ctx, "atk_pct", 0.85), "normal")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    nocauteou = alvo is not None and not alvo.esta_vivo()
    percentual = _fparam(ctx, "cura_dano_pct_nocaute", 0.50) if nocauteou else _fparam(ctx, "cura_dano_pct", 0.25)
    ret["cura"] = usuario.ReceberCura(
        dano_vida * percentual,
        origem=usuario,
        dados={**_ataque_id_nome(ctx, "Devorar"), "motivo": "Devorar", "reativos_acao": ctx.get("reativos_acao")},
    )
    ret["nocauteou"] = nocauteou
    if nocauteou:
        ret["vamp_bonus"] = aplicar_mod_atributo(ctx, usuario, "Devorar", "Vamp", _fparam(ctx, "vamp_bonus_nocaute", 10.0), negativo=False)
    return ret


def _exec_teia_pegajosa(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Vel") * _fparam(ctx, "vel_alvo_pct", 0.10)
    valor += usuario.obter_atributo("Mag") * _fparam(ctx, "mag_usuario_pct", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Teia Pegajosa", "Vel", -valor, negativo=True)


_EXECUTES = {
    "regeneracao": _exec_regeneracao,
    "regenerador": execute_passiva_nao_manual,
    "seda": _exec_seda,
    "casuloimprovisado": _exec_casulo_improvisado,
    "mordidadeinseto": _exec_mordida_de_inseto,
    "doacaodeenergia": _exec_doacao_de_energia,
    "corteserrilhado": _exec_corte_serrilhado,
    "carcomer": _exec_carcomer,
    "evolucaoincerta": _exec_evolucao_incerta,
    "infestacao": _exec_infestacao,
    "tesourax": _exec_tesoura_x,
    "canibalismofilial": _exec_canibalismo_filial,
    "devorar": _exec_devorar,
    "teiapegajosa": _exec_teia_pegajosa,
}

_PASSIVAS_ATAQUE = [
    {"nome": "Regenerador", "flag": "AoFimDoPasso", "grupo": "todos", "func": _passiva_regenerador, "origem": "ataque", "code": "209"},
]

_ALIASES = {
    "208": "regeneracao",
    "209": "regenerador",
    "210": "seda",
    "211": "casuloimprovisado",
    "212": "mordidadeinseto",
    "213": "doacaodeenergia",
    "214": "corteserrilhado",
    "215": "carcomer",
    "216": "evolucaoincerta",
    "217": "infestacao",
    "218": "tesourax",
    "219": "canibalismofilial",
    "220": "devorar",
    "221": "teiapegajosa",
}


def obter_executes_inseto():
    return dict(_EXECUTES)


def obter_passivas_ataques_inseto():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_inseto():
    return dict(_ALIASES)
