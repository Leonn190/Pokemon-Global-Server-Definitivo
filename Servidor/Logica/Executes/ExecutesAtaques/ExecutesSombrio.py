from __future__ import annotations

import copy

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    ATRIBUTOS_REGULARES,
    alvos_linha_inimigos_area,
    aplicar_mod_atributo,
    aplicar_status,
    aplicar_status_mag_efetiva,
    area_selecionada_da_acao,
    dano_direto_vida,
    dano_generico,
    adjacentes_mesmo_lado,
    executar_bola,
    executar_danca_clima,
    fnum,
    normalizar,
    parametros_execute,
    pokemons_ativos_em_campo,
    resolver_critico_contextual,
)


def _clima_normalizado(partida):
    return normalizar(getattr(partida, "clima_atual", ""))


def _ja_atacou_usuario_neste_turno(ctx, atacante, usuario):
    partida = ctx.get("partida")
    historico = getattr(partida, "historico_ataques_batalha", {}) if partida is not None else {}
    registro = (historico.get("ultimo_contra_alvo") or {}).get((getattr(atacante, "id_batalha", None), getattr(usuario, "id_batalha", None)))
    if not isinstance(registro, dict):
        return False
    rodada_atual = getattr(partida, "rodada_atual", None)
    if rodada_atual is not None and registro.get("rodada") != rodada_atual:
        return False
    return True


def _efeitos_negativos(pokemon):
    return [
        efeito
        for efeito in list(getattr(pokemon, "efeitos_formais", []) or [])
        if str((efeito or {}).get("tipo") or "").strip().lower() == "negativo"
    ]


def _chave_efeito(efeito):
    return normalizar((efeito or {}).get("code") or (efeito or {}).get("nome"))


def _registrar_evento(ctx, tipo, dados):
    partida = ctx.get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _exec_bola_sombria(ctx, alvo):
    parametros = parametros_execute(ctx)
    ctx_bola = dict(ctx)
    props = copy.deepcopy(ctx.get("propriedades") or {})
    params = props.setdefault("parametros", {})
    params["escala_spa"] = fnum(parametros.get("multiplicador_spa", parametros.get("escala_spa")), 0.80)
    params["splash_frac"] = fnum(parametros.get("percentual_dano_adjacente", parametros.get("splash_frac")), 0.50)
    ctx_bola["propriedades"] = props
    return executar_bola(ctx_bola, alvo, "sombrio")


def _exec_nas_sombras(ctx, alvo):
    return aplicar_status(ctx, ctx.get("usuario"), parametros_execute(ctx).get("efeito", "Furtivo"), negativo=False)


def _exec_confronto_trevoso(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * fnum(p.get("multiplicador_atk"), 0.55), "normal")
    efeito = p.get("efeito", "Provocando")
    if usuario is not None and usuario.esta_vivo():
        aplicar_status(ctx, usuario, efeito, negativo=True)
    if alvo is not None and alvo.esta_vivo():
        aplicar_status(ctx, alvo, efeito, negativo=True)
    return ret


def _exec_vinganca(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    bruto = usuario.obter_atributo("Atk") * fnum(p.get("multiplicador_atk"), 0.75)
    if _ja_atacou_usuario_neste_turno(ctx, alvo, usuario):
        bruto *= 1.0 + fnum(p.get("bonus_dano_se_ja_atacou_usuario"), 0.65)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_correntes_eternas(ctx, alvo):
    p = parametros_execute(ctx)
    return aplicar_status_mag_efetiva(ctx, alvo, p.get("efeito", "Enraizado"), p.get("percentual_mag_efeito", 2.0), True)


def _exec_nevoa_sombria(ctx, alvo):
    return executar_danca_clima(ctx, parametros_execute(ctx).get("clima", "Nevoa"))


def _exec_expurgo_dos_fracos(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    p = parametros_execute(ctx)
    vivos = pokemons_ativos_em_campo(partida)
    if not vivos:
        return {"falha": True, "motivo": "sem_alvos_em_campo"}
    menor = min(fnum(getattr(pokemon, "atributos_base", {}).get("Vida"), pokemon.obter_atributo("Vida", 1.0)) for pokemon in vivos)
    empatados = [pokemon for pokemon in vivos if fnum(getattr(pokemon, "atributos_base", {}).get("Vida"), pokemon.obter_atributo("Vida", 1.0)) == menor]
    rng = ctx.get("rng") or getattr(partida, "rng", None)
    escolhido = rng.choice(empatados) if rng is not None and len(empatados) > 1 else empatados[0]
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="expurgo_dos_fracos")
    critico = bool(critico_ctx.get("critico"))
    percentual = fnum(p.get("percentual_vida_atual_critico"), 0.55) if critico else fnum(p.get("percentual_vida_atual"), 0.50)
    ret = dano_direto_vida(ctx, escolhido, fnum(getattr(escolhido, "VidaAtual", 0.0), 0.0) * percentual, motivo="expurgo_dos_fracos")
    ret["critico"] = critico
    ret["critico_contextual"] = critico_ctx
    ret["alvo_id"] = getattr(escolhido, "id_batalha", None)
    return ret


def _exec_olhar_cruel(ctx, alvo):
    p = parametros_execute(ctx)
    incremento = int(fnum(p.get("incremento_passos"), 1))
    alterados = 0
    for efeito in _efeitos_negativos(alvo):
        if bool(efeito.get("permanente")) or int(fnum(efeito.get("passos_restantes"), 0)) < 0:
            continue
        efeito["passos_restantes"] = int(fnum(efeito.get("passos_restantes"), 0)) + incremento
        efeito["passos_totais"] = max(int(fnum(efeito.get("passos_totais"), 0)), efeito["passos_restantes"])
        alterados += 1
    _registrar_evento(ctx, "efeitos_negativos_estendidos", {"alvo_id": getattr(alvo, "id_batalha", None), "quantidade": alterados, "incremento": incremento})
    return {"aplicado": True, "efeitos_alterados": alterados}


def _exec_execucao_massiva(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * fnum(p.get("multiplicador_atk"), 0.45), "normal")
    vida_max = alvo.obter_atributo("Vida", 1.0) if alvo is not None else 1.0
    limite = fnum(p.get("percentual_execucao_vida"), 0.10)
    if alvo is not None and alvo.esta_vivo() and int(getattr(alvo, "lado_id", -1)) != int(getattr(usuario, "lado_id", -1)) and vida_max > 0 and (alvo.VidaAtual / vida_max) < limite:
        alvo.Morrer({"origem_id": getattr(usuario, "id_batalha", None), "origem": usuario, "ataque_nome": (ctx.get("propriedades") or {}).get("nome"), "execucao": True})
        ret["executou"] = True
    return ret


def _exec_corredor_escuro(ctx, alvo):
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    alvos = alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)
    if not alvos:
        alvos = [pokemon for pokemon in list(ctx.get("alvos") or []) if pokemon is not None and pokemon.esta_vivo()]
    uniao = {}
    for pokemon in alvos:
        for efeito in _efeitos_negativos(pokemon):
            chave = _chave_efeito(efeito)
            if not chave:
                continue
            atual = uniao.get(chave)
            if atual is None or fnum(efeito.get("passos_restantes"), 0) > fnum(atual.get("passos_restantes"), 0):
                uniao[chave] = copy.deepcopy(efeito)
    compartilhados = 0
    for pokemon in alvos:
        por_chave = {_chave_efeito(efeito): efeito for efeito in list(getattr(pokemon, "efeitos_formais", []) or [])}
        for chave, efeito in uniao.items():
            existente = por_chave.get(chave)
            if existente is not None:
                if not bool(existente.get("permanente")) and fnum(efeito.get("passos_restantes"), 0) > fnum(existente.get("passos_restantes"), 0):
                    existente["passos_restantes"] = int(fnum(efeito.get("passos_restantes"), 0))
                    existente["passos_totais"] = max(int(fnum(existente.get("passos_totais"), 0)), int(fnum(efeito.get("passos_totais"), efeito.get("passos_restantes", 0))))
                continue
            temporarios = [e for e in getattr(pokemon, "efeitos_formais", []) if not bool((e or {}).get("permanente"))]
            if not bool(efeito.get("permanente")) and len(temporarios) >= 4:
                continue
            pokemon.efeitos_formais.append(copy.deepcopy(efeito))
            compartilhados += 1
        if hasattr(pokemon, "recalcular_atributos"):
            pokemon.recalcular_atributos()
    _registrar_evento(ctx, "efeitos_negativos_compartilhados", {"alvos": [getattr(p, "id_batalha", None) for p in alvos], "efeitos": list(uniao), "aplicacoes": compartilhados})
    return {"aplicado": True, "alvos": len(alvos), "efeitos_unicos": len(uniao), "aplicacoes": compartilhados}


def _exec_golpe_noturno(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    bruto = usuario.obter_atributo("Atk") * fnum(p.get("multiplicador_atk"), 0.80)
    multiplicadores = []
    if _clima_normalizado(ctx.get("partida")) == normalizar(p.get("clima_bonus", "Noite Densa")):
        multiplicadores.append({"multiplicador": 1.0 + fnum(p.get("bonus_noite_densa"), 0.30)})
    if alvo is not None and alvo.possui_efeito(p.get("efeito_alvo_bonus", "Furtivo")):
        multiplicadores.append({"multiplicador": 1.0 + fnum(p.get("bonus_alvo_furtivo"), 0.30)})
    return dano_generico(ctx, alvo, bruto, "normal", multiplicadores_condicionais=multiplicadores)


def _exec_dominacao(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    atributos = p.get("atributos_regulares")
    if not isinstance(atributos, list):
        atributos = ATRIBUTOS_REGULARES
    superiores = sum(1 for atributo in atributos if usuario.obter_atributo(atributo) > alvo.obter_atributo(atributo))
    mult = 1.0 + superiores * fnum(p.get("bonus_por_atributo_superior"), 0.08)
    bruto = usuario.obter_atributo("Atk") * fnum(p.get("multiplicador_atk"), 0.65)
    return dano_generico(ctx, alvo, bruto, "normal", multiplicadores_condicionais=[{"multiplicador": mult}])


def _exec_inveja(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * fnum(p.get("multiplicador_spa"), 1.25), "especial")


def _exec_breu(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    p = parametros_execute(ctx)
    clima = p.get("clima", "Noite Densa")
    ja_noite = _clima_normalizado(partida) == normalizar(clima)
    ret = executar_danca_clima(ctx, clima)
    percentual_mag = p.get("percentual_mag_furtivo_noite_densa", 0.80) if ja_noite else p.get("percentual_mag_furtivo_normal", 0.50)
    alvos = [usuario]
    areas_adjacentes = set(adjacentes_mesmo_lado(getattr(usuario, "area_id", None)))
    for aliado in pokemons_ativos_em_campo(partida, filtro_lado=getattr(usuario, "lado_id", None)):
        if aliado is usuario or not aliado.esta_vivo():
            continue
        if getattr(aliado, "area_id", None) in areas_adjacentes:
            alvos.append(aliado)
    vistos = set()
    for alvo_furtivo in alvos:
        chave = getattr(alvo_furtivo, "id_batalha", None) or id(alvo_furtivo)
        if chave in vistos:
            continue
        vistos.add(chave)
        aplicar_status_mag_efetiva(ctx, alvo_furtivo, p.get("efeito", "Furtivo"), percentual_mag, False)
    ret["furtivo_alvos"] = len(vistos)
    return ret


def _exec_adaga_das_trevas(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * fnum(p.get("multiplicador_atk"), 0.70), "normal")
    percentual = fnum(p.get("percentual_reducao_critico"), 0.25) if ret.get("critico") else fnum(p.get("percentual_reducao"), 0.15)
    alterados = 0
    for atributo, valor in list(getattr(alvo, "variacoes_permanentes", {}).items()):
        valor = fnum(valor, 0.0)
        if valor >= 0:
            continue
        alvo.variacoes_permanentes[atributo] = valor * (1.0 + percentual)
        alterados += 1
    if alterados and hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    _registrar_evento(ctx, "reducoes_permanentes_ampliadas", {"alvo_id": getattr(alvo, "id_batalha", None), "percentual": percentual, "atributos": alterados})
    ret["reducoes_ampliadas"] = alterados
    return ret


def _exec_sombra(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    return aplicar_mod_atributo(ctx, usuario, "Sombra", p.get("atributo", "CrD"), usuario.obter_atributo("Mag") * fnum(p.get("percentual_mag"), 0.25), negativo=False)


def _exec_silenciar(ctx, alvo):
    usuario = ctx.get("usuario")
    p = parametros_execute(ctx)
    valor = fnum(p.get("valor_base"), 5.0) + usuario.obter_atributo("Mag") * fnum(p.get("percentual_mag"), 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Silenciar", p.get("atributo", "Amp"), -valor, negativo=True)


_EXECUTES = {
    "bolasombria": _exec_bola_sombria,
    "nassombras": _exec_nas_sombras,
    "confrontotrevoso": _exec_confronto_trevoso,
    "vinganca": _exec_vinganca,
    "correnteseternas": _exec_correntes_eternas,
    "nevoasombria": _exec_nevoa_sombria,
    "expurgodosfracos": _exec_expurgo_dos_fracos,
    "olharcruel": _exec_olhar_cruel,
    "execucaomassiva": _exec_execucao_massiva,
    "corredorescuro": _exec_corredor_escuro,
    "golpenoturno": _exec_golpe_noturno,
    "dominacao": _exec_dominacao,
    "inveja": _exec_inveja,
    "breu": _exec_breu,
    "adagadastrevas": _exec_adaga_das_trevas,
    "sombra": _exec_sombra,
    "silenciar": _exec_silenciar,
}

_ALIASES = {
    "269": "bolasombria",
    "270": "nassombras",
    "271": "confrontotrevoso",
    "272": "vinganca",
    "273": "correnteseternas",
    "274": "nevoasombria",
    "275": "expurgodosfracos",
    "276": "olharcruel",
    "277": "execucaomassiva",
    "278": "corredorescuro",
    "279": "golpenoturno",
    "280": "dominacao",
    "281": "inveja",
    "282": "breu",
    "283": "adagadastrevas",
    "284": "sombra",
    "285": "silenciar",
}


def obter_executes_sombrio():
    return dict(_EXECUTES)


def obter_passivas_ataques_sombrio():
    return []


def obter_aliases_executes_sombrio():
    return dict(_ALIASES)
