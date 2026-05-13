from __future__ import annotations

import copy

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    ATRIBUTOS_REGULARES,
    adjacentes_mesmo_lado,
    alvos_linha_inimigos_area,
    aplicar_mod_atributo,
    aplicar_status,
    area_selecionada_da_acao,
    dano_generico,
    fnum,
    normalizar,
    resolver_critico_contextual,
)


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    if _esta_aprimorado(ctx):
        aprimoramento = parametros.get("aprimoramento") if isinstance(parametros.get("aprimoramento"), dict) else {}
        if chave in aprimoramento:
            return fnum(aprimoramento.get(chave), default)
    return fnum(parametros.get(chave), default)


def _esta_aprimorado(ctx):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    usuario = (ctx or {}).get("usuario")
    nivel = ataque.get("Nivel", ataque.get("nivel", acao.get("nivel_ataque", 1)))
    try:
        if int(float(nivel or 1)) >= 2:
            return True
    except (TypeError, ValueError):
        pass
    if bool(ataque.get("aprimorado") or ataque.get("Aprimorado") or acao.get("aprimorado")):
        return True
    return bool(usuario is not None and hasattr(usuario, "possui_efeito") and usuario.possui_efeito("Aprimorado"))


def _ataque_id_nome(ctx, fallback):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return {
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or fallback,
    }


def _clima_sol_forte(ctx):
    return normalizar(getattr((ctx or {}).get("partida"), "clima_atual", "")) == "solforte"


def _selecoes_area(ctx):
    alvo = ((ctx or {}).get("acao") or {}).get("alvo") if isinstance((ctx or {}).get("acao"), dict) else {}
    if not isinstance(alvo, dict):
        return []
    if str(alvo.get("tipo") or "").strip().lower() == "multi":
        return [str(item.get("area_id") or "").strip().upper() for item in list(alvo.get("alvos") or []) if isinstance(item, dict) and item.get("area_id")]
    area_id = str(alvo.get("area_id") or "").strip().upper()
    return [area_id] if area_id else []


def _inimigos_vivos_adjacentes_area(ctx, area_id):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or usuario is None:
        return []
    saida = []
    for area_adjacente in adjacentes_mesmo_lado(area_id):
        pokemon = partida.pokemon_na_area(area_adjacente)
        if pokemon is None or not pokemon.esta_vivo():
            continue
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        saida.append(pokemon)
    return saida


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _exec_raizes(ctx, alvo):
    return aplicar_status(ctx, alvo, "Enraizado", negativo=True)


def _exec_casco_vivo(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Casco Vivo", "Dur", usuario.obter_atributo("Mag") * _param(ctx, "escala_mag_dur", 0.25), negativo=False)


def _exec_chicote_de_vinhas(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("Atk") * _param(ctx, "escala_atk", 0.75),
        "normal",
        bonus_critico_acerto=_param(ctx, "bonus_crc", 20.0),
    )


def _exec_sintese(ctx, alvo):
    usuario = ctx.get("usuario")
    mult = _param(ctx, "recuperacao_energia_sol_forte_mult", 3.00) if _clima_sol_forte(ctx) else _param(ctx, "recuperacao_energia_mult", 1.80)
    ganho = fnum(ctx.get("custo_real"), 0.0) * mult
    return usuario.GanharEnergia(ganho, dados={**_ataque_id_nome(ctx, "Sintese"), "motivo": "Sintese", "sol_forte": _clima_sol_forte(ctx), "reativos_acao": ctx.get("reativos_acao")})


def _exec_trevo_da_sorte(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Trevo da Sorte", "CrC", usuario.obter_atributo("Mag") * _param(ctx, "escala_mag_crc", 0.20), negativo=False)


def _exec_dreno(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "escala_spa_dano", 0.65), "especial")
    ret["cura_usuario"] = usuario.ReceberCura(
        usuario.obter_atributo("SpA") * _param(ctx, "escala_spa_cura", 0.35),
        origem=usuario,
        dados={**_ataque_id_nome(ctx, "Dreno"), "reativos_acao": ctx.get("reativos_acao")},
    )
    return ret


def _exec_seiva_misteriosa(ctx, alvo):
    usuario = ctx.get("usuario")
    envenenado = alvo is not None and (alvo.possui_efeito("Envenenado") or alvo.possui_efeito("Intoxicado"))
    extras = {}
    if envenenado:
        extras["multiplicadores_condicionais"] = [{"label": "Alvo envenenado ou intoxicado", "multiplicador": 1.0 + _param(ctx, "bonus_dano_envenenado", 0.35)}]
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "escala_spa", 0.75), "especial", **extras)
    ret["alvo_envenenado_ou_intoxicado"] = envenenado
    return ret


def _exec_tiro_de_semente(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "escala_atk", 0.75), "normal")
    removidos = int(alvo.RemoverEfeito("Regeneracao") or 0) + int(alvo.RemoverEfeito("Regeneração") or 0)
    ret["regeneracao_removida"] = removidos
    if removidos:
        _registrar_log(ctx, "pokemon_removeu_efeito", {"pokemon_id": alvo.id_batalha, "pokemon_nome": alvo.nome, "efeito_nome": "Regeneracao", "motivo": "Tiro de Semente", **_ataque_id_nome(ctx, "Tiro de Semente")})
    return ret


def _efeitos_positivos_roubaveis(alvo):
    saida = []
    for efeito in list(getattr(alvo, "efeitos_formais", []) or []):
        if not isinstance(efeito, dict) or bool(efeito.get("permanente")):
            continue
        if int(fnum(efeito.get("passos_restantes"), 0.0)) < 0:
            continue
        tipo = str(efeito.get("tipo") or "").strip().lower()
        nome = normalizar(efeito.get("nome") or efeito.get("code"))
        negativo = tipo == "negativo" or nome in {"queimado", "envenenado", "intoxicado", "congelado", "dormindo", "paralisado", "enraizado", "cauterizado", "descarregado", "encharcado", "atordoado", "quebrado", "enfraquecido", "confuso", "bloqueado", "amaldicoado"}
        if not negativo:
            saida.append(efeito)
    return saida


def _roubar_efeito_positivo(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    candidatos = _efeitos_positivos_roubaveis(alvo)
    if not candidatos:
        return {"aplicado": False, "motivo": "sem_efeito_positivo_roubavel"}
    escolhido = rng.choice(candidatos) if rng is not None else candidatos[0]
    alvo.efeitos_formais = [efeito for efeito in list(getattr(alvo, "efeitos_formais", []) or []) if efeito is not escolhido]
    transferido = copy.deepcopy(escolhido)
    transferido["tipo"] = "positivo"
    transferido["permanente"] = False
    usuario.efeitos_formais.append(transferido)
    alvo.recalcular_atributos()
    usuario.recalcular_atributos()
    _registrar_log(
        ctx,
        "efeito_roubado",
        {
            "origem_id": getattr(usuario, "id_batalha", None),
            "origem_nome": getattr(usuario, "nome", None),
            "alvo_id": getattr(alvo, "id_batalha", None),
            "alvo_nome": getattr(alvo, "nome", None),
            "efeito_nome": transferido.get("nome") or transferido.get("code"),
            **_ataque_id_nome(ctx, "Absorver"),
        },
    )
    return {"aplicado": True, "efeito": transferido}


def _exec_absorver(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "escala_spa", 0.35), "especial")
    roubos = []
    for _ in range(max(0, int(_param(ctx, "qtd_efeitos_roubados", 1)))):
        roubos.append(_roubar_efeito_positivo(ctx, alvo))
    ret["efeitos_roubados"] = roubos
    return ret


def _exec_folha_navalha(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    base = usuario.obter_atributo("Atk") * _param(ctx, "escala_atk", 0.80)
    percentual = max(_param(ctx, "minimo_proximo", 0.20), min(_param(ctx, "maximo_proximo", 0.80), (usuario.obter_atributo("Per") * _param(ctx, "fator_per_proximo", 0.50)) / 100.0))
    resultados = []
    for idx, inimigo in enumerate(alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)):
        bruto = base if idx == 0 else base * percentual
        resultados.append({"pokemon_id": inimigo.id_batalha, "indice_hit": idx, "dano": dano_generico(ctx, inimigo, bruto, "normal")})
    return {"aplicado": True, "area_id": area_id, "percentual_proximo": round(percentual, 4), "alvos_atingidos": len(resultados), "resultados": resultados}


def _distancia_areas(origem, destino):
    try:
        idx_origem = int(str(origem or "")[1:]) - 1
        idx_destino = int(str(destino or "")[1:]) - 1
    except (TypeError, ValueError, IndexError):
        return 0
    return max(0, abs((idx_destino % 3) - (idx_origem % 3)))


def _exec_flecha_de_madeira(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    dano_atual = usuario.obter_atributo("Atk") * (
        _param(ctx, "escala_atk", 0.70)
        + min(_distancia_areas(getattr(usuario, "area_id", None), area_id) * _param(ctx, "bonus_atk_por_area", 0.05), _param(ctx, "bonus_atk_max", 0.40))
    )
    resultados = []
    for idx, inimigo in enumerate(alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)):
        critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="flecha_de_madeira")
        ret = dano_generico(ctx, inimigo, dano_atual, "normal", chance_critico=100.0 if critico_ctx.get("critico") else 0.0, chance_critico_max=100.0 if critico_ctx.get("critico") else 0.0)
        resultados.append({"pokemon_id": inimigo.id_batalha, "indice_hit": idx, "critico_contextual": critico_ctx, "dano": ret})
        if not critico_ctx.get("critico"):
            break
        dano_atual *= 1.0 - _param(ctx, "reducao_apos_atravessar", 0.40)
    return {"aplicado": True, "area_id": area_id, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_crescimento(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    percentual = _param(ctx, "percentual_sol_forte", 0.05) if _clima_sol_forte(ctx) else _param(ctx, "percentual", 0.04)
    quantidade = int(_param(ctx, "quantidade_sol_forte", 4) if _clima_sol_forte(ctx) else _param(ctx, "quantidade", 3))
    atributos = list(ATRIBUTOS_REGULARES)
    sorteados = rng.sample(atributos, k=min(quantidade, len(atributos))) if rng is not None else atributos[:quantidade]
    resultados = []
    for atributo in sorteados:
        resultados.append(aplicar_mod_atributo(ctx, usuario, "Crescimento", atributo, usuario.obter_atributo(atributo) * percentual, negativo=False))
    return {"aplicado": True, "sol_forte": _clima_sol_forte(ctx), "atributos": sorteados, "resultados": resultados}


def _exec_danca_das_petalas(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    alvos = [usuario]
    vistos = {getattr(usuario, "id_batalha", None)}
    if partida is not None and usuario is not None:
        for area_id in adjacentes_mesmo_lado(getattr(usuario, "area_id", None)):
            pokemon = partida.pokemon_na_area(area_id)
            pid = getattr(pokemon, "id_batalha", None)
            if pokemon is None or pid in vistos or not pokemon.esta_vivo() or not getattr(pokemon, "ativo", False) or getattr(pokemon, "reserva", False):
                continue
            if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
                vistos.add(pid)
                alvos.append(pokemon)
    valor = usuario.obter_atributo("Mag") * _param(ctx, "escala_mag_vel", 0.18)
    return {"aplicado": True, "alvos": [p.id_batalha for p in alvos], "resultados": [aplicar_mod_atributo(ctx, p, "Danca das Petalas", "Vel", valor, negativo=False) for p in alvos]}


def _exec_tornado_de_folhas(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    resultados = []
    for inimigo in alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo):
        dano = dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * _param(ctx, "escala_spa", 0.65), "especial")
        perda = inimigo.obter_atributo("Vel") * _param(ctx, "escala_vel_alvo_debuff", 0.10) + usuario.obter_atributo("Mag") * _param(ctx, "escala_mag_usuario_debuff", 0.10)
        resultados.append({"pokemon_id": inimigo.id_batalha, "dano": dano, "vel": aplicar_mod_atributo(ctx, inimigo, "Tornado de Folhas", "Vel", -perda, negativo=True)})
    return {"aplicado": True, "area_id": area_id, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_bomba_de_sementes(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    base = usuario.obter_atributo("Atk") * _param(ctx, "escala_atk", 0.75)
    splash = base * _param(ctx, "splash_frac", 0.25)
    resultados = []
    for area_id in _selecoes_area(ctx)[: int(_param(ctx, "quantidade_areas", 2))]:
        principal = partida.pokemon_na_area(area_id) if partida is not None else None
        item = {"area_id": area_id, "principal": None, "splashes": []}
        if principal is not None and principal.esta_vivo() and int(getattr(principal, "lado_id", -1)) != int(getattr(usuario, "lado_id", -2)):
            item["principal"] = dano_generico(ctx, principal, base, "normal", impacto_principal=True, area_alvo=area_id)
        for adjacente in _inimigos_vivos_adjacentes_area(ctx, area_id):
            item["splashes"].append({"pokemon_id": adjacente.id_batalha, "dano": dano_generico(ctx, adjacente, splash, "normal", impacto_secundario=True, area_alvo=area_id)})
        resultados.append(item)
    return {"aplicado": True, "impactos": len(resultados), "resultados": resultados}


def _exec_flor_magica(ctx, alvo):
    usuario = ctx.get("usuario")
    spa_antes = usuario.obter_atributo("SpA")
    mag_antes = usuario.obter_atributo("Mag")
    ret = dano_generico(ctx, alvo, spa_antes * _param(ctx, "escala_spa_dano", 0.50) + mag_antes * _param(ctx, "escala_mag_dano", 0.50), "especial")
    ret["buff_spa"] = aplicar_mod_atributo(ctx, usuario, "Flor Magica", "SpA", mag_antes * _param(ctx, "escala_mag_para_spa", 0.06), negativo=False)
    ret["buff_mag"] = aplicar_mod_atributo(ctx, usuario, "Flor Magica", "Mag", spa_antes * _param(ctx, "escala_spa_para_mag", 0.06), negativo=False)
    return ret


def _exec_murchar(ctx, alvo):
    usuario = ctx.get("usuario")
    vida_antes = max(1.0, alvo.obter_atributo("Vida", 1.0))
    percentual_atual = max(0.0, min(1.0, fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) / vida_antes))
    valor = vida_antes * _param(ctx, "escala_vida_alvo", 0.06) + usuario.obter_atributo("Mag") * _param(ctx, "escala_mag_usuario", 0.08)
    ret = aplicar_mod_atributo(ctx, alvo, "Murchar", "Vida", -valor, negativo=True)
    alvo.VidaAtual = max(0.0, min(alvo.obter_atributo("Vida", 1.0), alvo.obter_atributo("Vida", 1.0) * percentual_atual))
    ret["percentual_vida_preservado"] = round(percentual_atual, 4)
    return ret


def _exec_raio_solar(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    escala = _param(ctx, "escala_spa_sol_forte", 1.25) if _clima_sol_forte(ctx) else _param(ctx, "escala_spa", 1.00)
    reducao = _param(ctx, "reducao_spa_por_alvo", 0.15)
    resultados = []
    for idx, inimigo in enumerate(alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)):
        bruto = max(0.0, usuario.obter_atributo("SpA") * escala - usuario.obter_atributo("SpA") * reducao * idx)
        resultados.append({"pokemon_id": inimigo.id_batalha, "indice_hit": idx, "dano": dano_generico(ctx, inimigo, bruto, "especial")})
    return {"aplicado": True, "area_id": area_id, "sol_forte": _clima_sol_forte(ctx), "alvos_atingidos": len(resultados), "resultados": resultados}


_EXECUTES = {
    "raizes": _exec_raizes,
    "cascovivo": _exec_casco_vivo,
    "chicotedevinhas": _exec_chicote_de_vinhas,
    "sintese": _exec_sintese,
    "trevodasorte": _exec_trevo_da_sorte,
    "dreno": _exec_dreno,
    "seivamisteriosa": _exec_seiva_misteriosa,
    "tirodesemente": _exec_tiro_de_semente,
    "absorver": _exec_absorver,
    "folhanavalha": _exec_folha_navalha,
    "flechademadeira": _exec_flecha_de_madeira,
    "crescimento": _exec_crescimento,
    "dancadaspetalas": _exec_danca_das_petalas,
    "tornadodefolhas": _exec_tornado_de_folhas,
    "bombadesementes": _exec_bomba_de_sementes,
    "flormagica": _exec_flor_magica,
    "murchar": _exec_murchar,
    "raiosolar": _exec_raio_solar,
}

_ALIASES = {
    "91": "raizes",
    "92": "cascovivo",
    "93": "chicotedevinhas",
    "94": "sintese",
    "95": "trevodasorte",
    "96": "dreno",
    "97": "seivamisteriosa",
    "98": "tirodesemente",
    "99": "absorver",
    "100": "folhanavalha",
    "101": "flechademadeira",
    "102": "crescimento",
    "103": "dancadaspetalas",
    "104": "tornadodefolhas",
    "105": "bombadesementes",
    "106": "flormagica",
    "107": "murchar",
    "108": "raiosolar",
}


def obter_executes_planta():
    return dict(_EXECUTES)


def obter_passivas_ataques_planta():
    return []


def obter_aliases_executes_planta():
    return dict(_ALIASES)
