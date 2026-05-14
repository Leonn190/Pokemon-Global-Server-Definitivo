from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    dano_generico,
    dano_puro_ignorando_barreira,
    execute_passiva_nao_manual,
    executar_danca_clima,
    fnum,
    inimigos_vivos_adjacentes_ao_alvo,
    pokemons_ativos_em_campo,
    propriedades_ataque_por_code,
    remover_efeitos_contando_passos,
    resolver_critico_contextual,
)


def _params(ctx):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return props.get("parametros") if isinstance(props.get("parametros"), dict) else {}


def _param(ctx, chave, default):
    return fnum(_params(ctx).get(chave), default)


def _param_str(ctx, chave, default=""):
    valor = _params(ctx).get(chave)
    return str(valor if valor not in (None, "") else default)


def _param_lista(ctx, chave, default):
    valor = _params(ctx).get(chave)
    if isinstance(valor, list):
        return list(valor)
    if isinstance(valor, tuple):
        return list(valor)
    if valor in (None, ""):
        return list(default)
    return [valor]


def _aplicar_efeito_base(ctx, alvo, nome, negativo=None):
    usuario = (ctx or {}).get("usuario")
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    if usuario is None or alvo is None:
        return {"aplicado": False, "motivo": "alvo_invalido"}
    efeito = {"nome": nome}
    if negativo is not None:
        efeito["negativo"] = bool(negativo)
    return usuario.AplicarEfeito(alvo, efeito, dados={"origem_ataque": props.get("nome"), "reativos_acao": (ctx or {}).get("reativos_acao")})


def _exec_flutuar(ctx, alvo):
    usuario = ctx.get("usuario")
    return _aplicar_efeito_base(ctx, usuario, _param_str(ctx, "efeito_aplicado", "Flutuando"), negativo=False)


def _exec_raio_cosmico(ctx, alvo):
    usuario = ctx.get("usuario")
    alvos = [item for item in list(ctx.get("alvos") or []) if item is not None and item.esta_vivo()]
    idx = next((i for i, item in enumerate(alvos) if item is alvo), 0)
    mult = max(0.0, _param(ctx, "multiplicador_spa_inicial", 1.00) - _param(ctx, "reducao_multiplicador_por_alvo", 0.15) * idx)
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial", indice_alvo_linha=idx, multiplicador_spa=mult)


def _exec_gravidade(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    efeitos = _param_lista(ctx, "efeitos_bonus_remover", ["Flutuando", "Voando"])
    base = usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.25)
    bonus = _param(ctx, "bonus_dano_contra_flutuando_voando", 2.00)
    resultados = []
    for pokemon in pokemons_ativos_em_campo(partida):
        possuia = [efeito for efeito in efeitos if pokemon.possui_efeito(efeito)]
        mult = 1.0 + bonus if possuia else 1.0
        dano = dano_generico(ctx, pokemon, base, "especial", multiplicadores_condicionais=[{"label": "Gravidade contra Flutuando/Voando", "multiplicador": mult}])
        removidos = remover_efeitos_contando_passos(pokemon, possuia, origem=usuario, dados={"motivo": "Gravidade"}) if possuia else {"removidos": 0, "efeitos": []}
        resultados.append({"alvo_id": getattr(pokemon, "id_batalha", None), "efeitos_antes": possuia, "dano": dano, "remocao": removidos})
    return {"aplicado": True, "alvos": resultados}


def _exec_estrela_cadente(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng")
    percentuais = _param_lista(ctx, "atributos_percentuais_possiveis", ["SpD", "SpA", "Mag"])
    fixo = _param_str(ctx, "atributo_fixo_possivel", "CrC")
    opcoes = [str(item) for item in percentuais] + [fixo]
    atributo = opcoes[rng.randrange(len(opcoes))] if rng is not None and opcoes else fixo
    critico = resolver_critico_contextual(usuario, ctx, tipo="estrela_cadente")
    if atributo == fixo:
        valor = _param(ctx, "ganho_crc_critico", 30.0) if critico.get("critico") else _param(ctx, "ganho_crc_normal", 25.0)
    else:
        percentual = _param(ctx, "percentual_ganho_critico", 0.30) if critico.get("critico") else _param(ctx, "percentual_ganho_normal", 0.25)
        valor = usuario.obter_atributo(atributo) * percentual
    ret = aplicar_mod_atributo(ctx, usuario, "Estrela Cadente", atributo, valor, negativo=False)
    ret["critico"] = critico
    ret["atributo_sorteado"] = atributo
    return ret


def _exec_radiacao(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is None or usuario is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    cond_alvo = alvo.possui_efeito(_param_str(ctx, "efeito_condicional_alvo", "Envenenado"))
    cond_usuario = usuario.possui_efeito(_param_str(ctx, "efeito_condicional_usuario", "Flutuando"))
    percentual = _param(ctx, "percentual_vida_atual_condicional", 0.15) if (cond_alvo or cond_usuario) else _param(ctx, "percentual_vida_atual_base", 0.10)
    critico = resolver_critico_contextual(usuario, ctx, tipo="radiacao")
    if critico.get("critico"):
        percentual += _param(ctx, "bonus_percentual_critico", 0.05)
    ret = dano_puro_ignorando_barreira(ctx, alvo, fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) * percentual, reducao_dur=False)
    ret["percentual_vida_atual"] = percentual
    ret["critico"] = critico
    ret["condicional"] = {"alvo_envenenado": cond_alvo, "usuario_flutuando": cond_usuario}
    return ret


def _exec_danca_gravitacional(ctx, alvo):
    return executar_danca_clima(ctx, _param_str(ctx, "clima", "Gravidade Anomala"))


def _exec_supernova(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 1.70), "especial", chance_critico=0.0, chance_critico_max=0.0)
    if not ret.get("falha"):
        ret["efeito_pos_uso"] = _aplicar_efeito_base(ctx, usuario, _param_str(ctx, "efeito_pos_uso", "Descarregado"), negativo=True)
    return ret


def _exec_explosao_lunar(ctx, alvo):
    usuario = ctx.get("usuario")
    dano_base = usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.85)
    adjacentes = inimigos_vivos_adjacentes_ao_alvo(ctx, alvo)
    ret = dano_generico(
        ctx,
        alvo,
        dano_base,
        "especial",
        impacto_principal=True,
        alvo_principal_id=getattr(alvo, "id_batalha", None),
        alvos_secundarios_ids=[getattr(p, "id_batalha", None) for p in adjacentes],
    )
    ret["dano_base_principal"] = dano_base
    ret["adjacentes"] = []
    dano_adjacente = dano_base * _param(ctx, "percentual_dano_base_adjacentes", 1.20)
    for adjacente in adjacentes:
        dano = dano_generico(
            ctx,
            adjacente,
            dano_adjacente,
            "especial",
            impacto_secundario=True,
            alvo_principal_id=getattr(alvo, "id_batalha", None),
            alvos_secundarios_ids=[getattr(p, "id_batalha", None) for p in adjacentes],
        )
        ret["adjacentes"].append({"alvo_id": getattr(adjacente, "id_batalha", None), "dano": dano})
    return ret


def _passiva_flutuante(ctx):
    props = propriedades_ataque_por_code("320")
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return aplicar_passiva_permanente(ctx, str(parametros.get("efeito_permanente") or "Flutuando"))


_EXECUTES = {
    "flutuante": execute_passiva_nao_manual,
    "flutuar": _exec_flutuar,
    "raiocosmico": _exec_raio_cosmico,
    "gravidade": _exec_gravidade,
    "estrelacadente": _exec_estrela_cadente,
    "radiacao": _exec_radiacao,
    "dancagravitacional": _exec_danca_gravitacional,
    "supernova": _exec_supernova,
    "explosaolunar": _exec_explosao_lunar,
}

_PASSIVAS_ATAQUE = [
    {"nome": "Flutuante", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_flutuante, "origem": "ataque", "code": "320"},
]

_ALIASES = {
    "320": "flutuante",
    "321": "flutuar",
    "322": "raiocosmico",
    "323": "gravidade",
    "324": "estrelacadente",
    "325": "radiacao",
    "326": "dancagravitacional",
    "327": "supernova",
    "328": "explosaolunar",
}


def obter_executes_cosmicos():
    return dict(_EXECUTES)


def obter_passivas_ataques_cosmicas():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_cosmicos():
    return dict(_ALIASES)
