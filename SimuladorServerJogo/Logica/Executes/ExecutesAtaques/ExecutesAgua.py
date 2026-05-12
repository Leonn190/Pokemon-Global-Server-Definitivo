from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    area_alvo_contexto,
    alvos_linha_inimigos_area,
    dano_generico,
    executar_bola,
    executar_danca_clima,
    fnum,
    inimigos_vivos_adjacentes_area,
    inimigos_vivos_adjacentes_ao_alvo,
    normalizar,
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


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _exec_bola_de_agua(ctx, alvo):
    return executar_bola(ctx, alvo, "agua")


def _exec_gota_pesada(ctx, alvo):
    return aplicar_status(ctx, alvo, "Encharcado", duracao=_param(ctx, "duracao", 6), negativo=True)


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
    mult = _param(ctx, "base_spa", 0.35) + usos_anteriores * _param(ctx, "bonus_spa_por_uso", 0.08)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    usuario.contadores_especiais[chave] = usos_anteriores + 1
    ret["usos_anteriores_bolhas"] = usos_anteriores
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
        ret["encharcado"] = aplicar_status(ctx, alvo, "Encharcado", duracao=_param(ctx, "duracao", 6), negativo=True)
    return ret


def _exec_jato_multiplo(ctx, alvo, fallback_hits, fallback_mult):
    usuario = ctx.get("usuario")
    mult = _param(ctx, "mult_spa", fallback_mult)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["encharcado"] = aplicar_status(ctx, alvo, "Encharcado", duracao=_param(ctx, "duracao", 6), negativo=True)
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
        efeito = aplicar_status(ctx, alvo, "Encharcado", duracao=_param(ctx, "duracao", 6), negativo=True)
    cura = usuario.AplicarCura(alvo, usuario.obter_atributo("Mag") * _param(ctx, "cura_mag", 0.30), dados={**_ataque_id_nome(ctx, "Fonte Termal"), "reativos_acao": ctx.get("reativos_acao")})
    return {"aplicado": True, "efeitos_removidos": len(removidos), "encharcado": efeito, "cura": cura}


def _exec_correnteza(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("Vel") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Correnteza", "Vel", valor, 6, False)


def _exec_danca_da_chuva(ctx, alvo):
    return executar_danca_clima(ctx, "Chuva")


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
    "56": "correnteza",
    "57": "dancadachuva",
}


def obter_executes_agua():
    return dict(_EXECUTES)


def obter_passivas_ataques_agua():
    return []


def obter_aliases_executes_agua():
    return dict(_ALIASES)
