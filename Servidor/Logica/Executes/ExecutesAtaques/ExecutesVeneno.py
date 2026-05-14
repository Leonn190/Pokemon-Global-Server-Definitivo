from __future__ import annotations

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    area_selecionada_da_acao,
    dano_generico,
    efeito_formal,
    execute_passiva_nao_manual,
    executar_danca_clima,
    fnum,
    inimigos_vivos_adjacentes_ao_alvo,
    normalizar,
    obter_passos_efeito,
    remover_efeitos_contando_passos,
    resolver_critico_contextual,
)


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _param_str(ctx, chave, default=""):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return str(parametros.get(chave, default) or default)


def _param_lista(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    valor = parametros.get(chave, default)
    return list(valor) if isinstance(valor, (list, tuple)) else list(default)


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


def _tem_veneno(alvo):
    return bool(alvo is not None and (alvo.possui_efeito("Envenenado") or alvo.possui_efeito("Intoxicado")))


def _passos_veneno(alvo):
    if alvo is None:
        return 0
    return obter_passos_efeito(alvo, "Envenenado") + obter_passos_efeito(alvo, "Intoxicado")


def _dobrar_passos_efeito(ctx, alvo, nomes):
    alterados = []
    for nome in nomes:
        efeito = efeito_formal(alvo, nome)
        if not isinstance(efeito, dict):
            continue
        passos = int(fnum(efeito.get("passos_restantes"), 0.0))
        if passos < 0 or bool(efeito.get("permanente")):
            continue
        novo = passos * 2
        efeito["passos_restantes"] = novo
        efeito["passos_totais"] = max(int(fnum(efeito.get("passos_totais"), 0.0)), novo)
        alterados.append({"efeito": efeito.get("nome") or efeito.get("code") or nome, "antes": passos, "depois": novo})
    if alterados:
        _registrar_log(
            ctx,
            "efeito_passos_alterados",
            {
                "pokemon_id": getattr(alvo, "id_batalha", None),
                "pokemon_nome": getattr(alvo, "nome", None),
                "alteracoes": alterados,
                **_ataque_id_nome(ctx, "Gas Venenoso"),
            },
        )
    return alterados


def _exec_envenenar(ctx, alvo):
    return aplicar_status(ctx, alvo, "Envenenado", negativo=True)


def _exec_farpa(ctx, alvo):
    usuario = ctx.get("usuario")
    extras = {}
    if _tem_veneno(alvo):
        extras["chance_critico"] = _param(ctx, "chance_critico_forcado", 100.0)
        extras["chance_critico_max"] = _param(ctx, "chance_critico_forcado", 100.0)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.45), "normal", **extras)
    if ret.get("critico"):
        ret["envenenado"] = aplicar_status(ctx, alvo, "Envenenado", negativo=True)
    return ret


def _exec_poluicao(ctx, alvo):
    clima_origem = _param_str(ctx, "clima_origem", "Chuva")
    clima_destino = _param_str(ctx, "clima_destino", "Chuva Acida")
    atual = getattr(ctx.get("partida"), "clima_atual", None)
    if normalizar(atual) != normalizar(clima_origem):
        return {"aplicado": True, "sem_efeito": True, "clima_atual": atual}
    return executar_danca_clima(ctx, clima_destino)


def _exec_acido(ctx, alvo):
    usuario = ctx.get("usuario")
    atributo = "Def" if alvo.obter_atributo("Def") >= alvo.obter_atributo("SpD") else "SpD"
    valor = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa_reducao", 0.15)
    return aplicar_mod_atributo(ctx, alvo, "Acido", atributo, -valor, negativo=True)


def _exec_esporos_conectados(ctx, alvo):
    usuario = ctx.get("usuario")
    candidatos = [p for p in list((ctx or {}).get("alvos") or []) if p is not None and p.esta_vivo() and _tem_veneno(p)]
    if not candidatos:
        return {"aplicado": True, "sem_efeito": True, "alvos_validos": 0}
    mult = _param(ctx, "mult_spa", 0.55) * (1.0 + _param(ctx, "bonus_por_inimigo_atingido", 0.10) * len(candidatos))
    resultados = []
    for alvo_real in candidatos:
        resultados.append({"alvo_id": alvo_real.id_batalha, "dano": dano_generico(ctx, alvo_real, usuario.obter_atributo("SpA") * mult, "especial")})
    return {"aplicado": True, "alvos_validos": len(candidatos), "multiplicador_final": mult, "resultados": resultados}


def _exec_fumaca_toxica(ctx, alvo):
    usuario = ctx.get("usuario")
    critico = resolver_critico_contextual(usuario, ctx, tipo="efeito")
    if alvo.possui_efeito("Envenenado") or critico.get("critico"):
        efeito = aplicar_status(ctx, alvo, "Intoxicado", negativo=True)
        return {"aplicado": True, "critico_contextual": critico, "intoxicado": efeito}
    efeito = aplicar_status(ctx, alvo, "Envenenado", negativo=True)
    return {"aplicado": True, "critico_contextual": critico, "envenenado": efeito}


def _exec_contaminar(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx)
    terreno = _param_str(ctx, "terreno", "Contaminada")
    if partida is None or not area_id:
        return {"falha": True, "motivo": "area_invalida"}
    if hasattr(partida, "mudar_terreno"):
        aplicado = partida.mudar_terreno(area_id, terreno, origem=usuario, dados=_ataque_id_nome(ctx, "Contaminar"))
        return {"aplicado": bool(aplicado), "area_id": area_id, "terreno": terreno}
    return {"falha": True, "motivo": "partida_sem_terreno"}


def _exec_gas_venenoso(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.45), "especial")
    ret["passos_alterados"] = _dobrar_passos_efeito(ctx, alvo, _param_lista(ctx, "efeitos_dobrados", ["Envenenado", "Intoxicado"]))
    return ret


def _exec_gas_corrosivo(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.45), "especial")
    reducoes = []
    for atributo in _param_lista(ctx, "atributos_reducao_dobrada", ["Def", "SpD"]):
        atual = fnum(getattr(alvo, "variacoes_permanentes", {}).get(atributo), 0.0)
        if atual < 0:
            reducoes.append(aplicar_mod_atributo(ctx, alvo, "Gas Corrosivo", atributo, atual, negativo=True))
    ret["reducoes_dobradas"] = reducoes
    return ret


def _exec_bomba_de_lodo(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial")
    ret["envenenado_alvo"] = aplicar_status(ctx, alvo, "Envenenado", negativo=True)
    adjacentes = []
    for adjacente in inimigos_vivos_adjacentes_ao_alvo(ctx, alvo):
        adjacentes.append({"alvo_id": adjacente.id_batalha, "envenenado": aplicar_status(ctx, adjacente, "Envenenado", negativo=True)})
    ret["adjacentes_envenenados"] = adjacentes
    return ret


def _exec_vortex_venenoso(ctx, alvo):
    usuario = ctx.get("usuario")
    passos = min(int(_param(ctx, "limite_passos", 15)), _passos_veneno(alvo))
    mult = _param(ctx, "mult_spa_base", 0.60) + _param(ctx, "bonus_spa_por_passo", 0.04) * passos
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial")
    ret["passos_considerados"] = passos
    ret["multiplicador_final"] = mult
    return ret


def _exec_poco(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.35), "especial")
    if _tem_veneno(alvo):
        antes = fnum(getattr(alvo, "EnergiaAtual", 0.0), 0.0)
        alvo.EnergiaAtual = max(0.0, antes * (1.0 - _param(ctx, "percentual_energia_atual", 1.00)))
        perda = max(0.0, antes - alvo.EnergiaAtual)
        dados = {
            "pokemon_id": getattr(alvo, "id_batalha", None),
            "pokemon_nome": getattr(alvo, "nome", None),
            "valor": round(perda, 4),
            "energia_antes": round(antes, 4),
            "energia_depois": round(alvo.EnergiaAtual, 4),
            **_ataque_id_nome(ctx, "Poco"),
        }
        _registrar_log(ctx, "pokemon_perdeu_energia", dados)
        ret["energia_removida"] = dados
    return ret


def _exec_extracao(ctx, alvo):
    usuario = ctx.get("usuario")
    passos = _passos_veneno(alvo)
    ganho = min(_param(ctx, "vamp_max", 20.0), _param(ctx, "vamp_por_passo", 2.0) * passos)
    vamp = aplicar_mod_atributo(ctx, usuario, "Extracao", "Vamp", ganho, negativo=False)
    removidos = remover_efeitos_contando_passos(alvo, ["Envenenado", "Intoxicado"], origem=usuario, dados=_ataque_id_nome(ctx, "Extracao"))
    dano = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.75), "normal")
    dano["vamp_ganho"] = vamp
    dano["efeitos_removidos"] = removidos
    return dano


def _exec_armadura_mole(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Per") * _param(ctx, "mult_per_alvo", 0.10) + usuario.obter_atributo("Mag") * _param(ctx, "mult_mag_usuario", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Armadura Mole", "Per", -valor, negativo=True)


def _passiva_imunizado(ctx):
    return aplicar_passiva_permanente(ctx, "Imune")


_EXECUTES = {
    "envenenar": _exec_envenenar,
    "farpa": _exec_farpa,
    "poluicao": _exec_poluicao,
    "acido": _exec_acido,
    "esporosconectados": _exec_esporos_conectados,
    "fumacatoxica": _exec_fumaca_toxica,
    "contaminar": _exec_contaminar,
    "gasvenenoso": _exec_gas_venenoso,
    "gascorrosivo": _exec_gas_corrosivo,
    "bombadelodo": _exec_bomba_de_lodo,
    "vortexvenenoso": _exec_vortex_venenoso,
    "poco": _exec_poco,
    "extracao": _exec_extracao,
    "armaduramole": _exec_armadura_mole,
    "imunizado": execute_passiva_nao_manual,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Imunizado", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_imunizado, "origem": "ataque", "code": "158"},
]
_ALIASES = {
    "144": "envenenar",
    "145": "farpa",
    "146": "poluicao",
    "147": "acido",
    "148": "esporosconectados",
    "149": "fumacatoxica",
    "150": "contaminar",
    "151": "gasvenenoso",
    "152": "gascorrosivo",
    "153": "bombadelodo",
    "154": "vortexvenenoso",
    "155": "poco",
    "156": "extracao",
    "157": "armaduramole",
    "158": "imunizado",
}


def obter_executes_veneno():
    return dict(_EXECUTES)


def obter_passivas_ataques_veneno():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_veneno():
    return dict(_ALIASES)
