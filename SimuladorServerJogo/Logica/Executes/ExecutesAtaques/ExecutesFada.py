from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    adjacentes_mesmo_lado,
    alvos_linha_inimigos_area,
    aplicar_mod_atributo,
    dano_generico,
    fnum,
    normalizar,
    parametros_execute,
    pokemons_ativos_em_campo,
    remover_efeitos_contando_passos,
    remover_efeitos_negativos,
)


EFEITOS_NEGATIVOS_FORMAIS = [
    "Queimado",
    "Envenenado",
    "Intoxicado",
    "Congelado",
    "Dormindo",
    "Paralisado",
    "Enraizado",
    "Cauterizado",
    "Descarregado",
    "Encharcado",
    "Atordoado",
    "Quebrado",
    "Enfraquecido",
    "Confuso",
    "Bloqueado",
    "Amaldiçoado",
]


def _param(ctx, chave, default):
    return fnum(parametros_execute(ctx).get(chave), default)


def _param_lista(ctx, chave, default):
    valor = parametros_execute(ctx).get(chave)
    if isinstance(valor, list):
        return [item for item in valor if str(item or "").strip()]
    return list(default or [])


def _param_str(ctx, chave, default=""):
    return str(parametros_execute(ctx).get(chave, default) or default)


def _ataque_id_nome(ctx, fallback):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return {
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or fallback,
        "reativos_acao": (ctx or {}).get("reativos_acao"),
    }


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _aplicar_efeito_padrao(ctx, alvo, efeito, negativo=False):
    usuario = (ctx or {}).get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    return usuario.AplicarEfeito(
        alvo,
        {"nome": efeito, "negativo": bool(negativo)},
        dados={**_ataque_id_nome(ctx, efeito), "origem_ataque": ((ctx or {}).get("propriedades") or {}).get("nome")},
    )


def _aliados_vivos_em_campo(ctx, incluir_usuario=True):
    usuario = (ctx or {}).get("usuario")
    if usuario is None:
        return []
    aliados = [
        pokemon
        for pokemon in pokemons_ativos_em_campo((ctx or {}).get("partida"), filtro_lado=getattr(usuario, "lado_id", None))
        if pokemon is not None and pokemon.esta_vivo()
    ]
    if incluir_usuario and usuario not in aliados and usuario.esta_vivo() and getattr(usuario, "ativo", False) and not getattr(usuario, "reserva", False):
        aliados.append(usuario)
    if not incluir_usuario:
        aliados = [pokemon for pokemon in aliados if pokemon is not usuario]
    return aliados


def _inimigos_vivos_em_campo(ctx):
    usuario = (ctx or {}).get("usuario")
    if usuario is None:
        return []
    return [
        pokemon
        for pokemon in pokemons_ativos_em_campo((ctx or {}).get("partida"))
        if pokemon is not None and pokemon.esta_vivo() and int(getattr(pokemon, "lado_id", -1)) != int(getattr(usuario, "lado_id", -2))
    ]


def _tem_efeito(pokemon, efeitos):
    return pokemon is not None and any(pokemon.possui_efeito(efeito) for efeito in list(efeitos or []))


def _tipo_fada(pokemon):
    return any(normalizar(tipo) == "fada" for tipo in list(getattr(pokemon, "tipos", []) or []))


def _vida_max(pokemon):
    return max(1.0, fnum(pokemon.obter_atributo("Vida", 1.0), 1.0))


def _exec_bencao(ctx, alvo):
    return _aplicar_efeito_padrao(ctx, alvo, _param_str(ctx, "efeito_aplicado", "Abençoado"), negativo=False)


def _exec_barragem_arcana(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    valor = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag_barreira", 0.20)
    valor += usuario.obter_atributo("SpA") * _param(ctx, "percentual_spa_barreira", 0.12)
    return usuario.AplicarBarreira(alvo, valor, dados=_ataque_id_nome(ctx, "Barragem Arcana"))


def _exec_canalizar(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None:
        return {"falha": True, "motivo": "usuario_invalido"}
    ganho = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag_total", 0.30)
    return aplicar_mod_atributo(ctx, usuario, "Canalizar", "Mag", ganho, negativo=False)


def _exec_amolecer(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    reducao = _param(ctx, "reducao_base_crd", 5.0) + usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag_usuario", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Amolecer", "CrD", -reducao, negativo=True)


def _exec_brilho(ctx, alvo):
    usuario = ctx.get("usuario")
    efeito_requerido = _param_str(ctx, "efeito_requerido", "Furtivo")
    efeito_remover = _param_str(ctx, "efeito_remover", efeito_requerido)
    resultados = []
    for inimigo in _inimigos_vivos_em_campo(ctx):
        if not inimigo.possui_efeito(efeito_requerido):
            continue
        dano = usuario.obter_atributo("Mag") * _param(ctx, "multiplicador_mag", 0.80)
        ret = dano_generico(ctx, inimigo, dano, "especial")
        removidos = remover_efeitos_contando_passos(
            inimigo,
            [efeito_remover],
            origem=usuario,
            dados={**_ataque_id_nome(ctx, "Brilho"), "motivo": "Brilho"},
        )
        resultados.append({"pokemon_id": inimigo.id_batalha, "dano": ret, "efeitos_removidos": removidos})
    if not resultados:
        _registrar_log(ctx, "ataque_sem_alvo_real", {**_ataque_id_nome(ctx, "Brilho"), "motivo": "sem_inimigos_furtivos"})
    return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_salvamento(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    aliados = _aliados_vivos_em_campo(ctx, incluir_usuario=True)
    if not aliados:
        return {"falha": True, "motivo": "sem_aliado_vivo"}
    menor = min(fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0) / _vida_max(pokemon) for pokemon in aliados)
    empatados = [pokemon for pokemon in aliados if abs((fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0) / _vida_max(pokemon)) - menor) <= 0.0001]
    escolhido = rng.choice(empatados) if rng is not None and empatados else empatados[0]
    resultados = {}
    for efeito in _param_lista(ctx, "efeitos_aplicados", ["Regeneração", "Imune"]):
        resultados[efeito] = _aplicar_efeito_padrao(ctx, escolhido, efeito, negativo=False)
    return {
        "aplicado": True,
        "alvo_id": getattr(escolhido, "id_batalha", None),
        "percentual_vida": round(menor, 6),
        "empatados": [getattr(pokemon, "id_batalha", None) for pokemon in empatados],
        "efeitos": resultados,
    }


def _exec_toque_fabuloso(ctx, alvo):
    usuario = ctx.get("usuario")
    efeitos = _param_lista(ctx, "efeitos_critico_garantido", ["Encantado", "Abençoado", "Amplificado"])
    critico_forcado = _tem_efeito(usuario, efeitos) or _tem_efeito(alvo, efeitos)
    extras = {"chance_critico": 100.0, "chance_critico_max": 100.0} if critico_forcado else {}
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.75), "especial", **extras)
    ret["critico_garantido_condicional"] = critico_forcado
    return ret


def _exec_corte_das_fadas(ctx, alvo):
    aliados = _aliados_vivos_em_campo(ctx, incluir_usuario=True)
    soma_mag = sum(pokemon.obter_atributo("Mag") for pokemon in aliados)
    qtd_fada = sum(1 for pokemon in aliados if _tipo_fada(pokemon))
    multiplicador = _param(ctx, "percentual_soma_mag_base", 0.50)
    multiplicador += _param(ctx, "percentual_soma_mag_extra_por_aliado_fada", 0.10) * qtd_fada
    ret = dano_generico(ctx, alvo, soma_mag * multiplicador, "especial")
    ret["soma_mag_aliados"] = round(soma_mag, 4)
    ret["aliados_fada"] = qtd_fada
    return ret


def _exec_chuva_cintilante(ctx, alvo):
    usuario = ctx.get("usuario")
    efeito = _param_str(ctx, "efeito_aplicado", "Furtivo")
    pct = _param(ctx, "percentual_vida_perdida_cura", 0.10)
    resultados = []
    for aliado in _aliados_vivos_em_campo(ctx, incluir_usuario=False):
        efeito_ret = _aplicar_efeito_padrao(ctx, aliado, efeito, negativo=False)
        vida_perdida = max(0.0, _vida_max(aliado) - fnum(getattr(aliado, "VidaAtual", 0.0), 0.0))
        cura = usuario.AplicarCura(aliado, vida_perdida * pct, dados=_ataque_id_nome(ctx, "Chuva Cintilante"))
        resultados.append({"pokemon_id": aliado.id_batalha, "efeito": efeito_ret, "cura": cura})
    return {"aplicado": True, "alvos_afetados": len(resultados), "resultados": resultados}


def _exec_vento_fada(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = getattr(alvo, "area_id", None)
    if not area_id:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    resultados = []
    for inimigo in alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo):
        bruto = usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.70)
        bruto += usuario.obter_atributo("Mag") * _param(ctx, "multiplicador_mag", 0.20)
        resultados.append({"pokemon_id": inimigo.id_batalha, "dano": dano_generico(ctx, inimigo, bruto, "especial")})
    return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_bondade(ctx, alvo):
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    efeitos = _param_lista(ctx, "efeitos_positivos_possiveis", ["Abençoado", "Amplificado", "Fortificado", "Focado", "Energizado", "Preparado", "Regeneração", "Imune", "Furtivo"])
    if not efeitos:
        return {"falha": True, "motivo": "lista_efeitos_positivos_vazia"}
    efeito = rng.choice(efeitos) if rng is not None else efeitos[0]
    ret = _aplicar_efeito_padrao(ctx, alvo, efeito, negativo=False)
    ret["efeito_sorteado"] = efeito
    return ret


def _exec_luz_purificadora(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    if usuario is None:
        return {"falha": True, "motivo": "usuario_invalido"}
    alvos = [usuario]
    for area_id in adjacentes_mesmo_lado(getattr(usuario, "area_id", None)):
        pokemon = partida.pokemon_na_area(area_id) if partida is not None else None
        if pokemon is None or not pokemon.esta_vivo() or int(getattr(pokemon, "lado_id", -1)) != int(getattr(usuario, "lado_id", -2)):
            continue
        alvos.append(pokemon)
    resultados = []
    lista_negativos = _param_lista(ctx, "efeitos_negativos", EFEITOS_NEGATIVOS_FORMAIS)
    for pokemon in alvos:
        resultados.append(
            {
                "pokemon_id": pokemon.id_batalha,
                "remocao": remover_efeitos_negativos(ctx, pokemon, lista_negativos, origem=usuario, motivo="Luz Purificadora"),
            }
        )
    return {"aplicado": True, "alvos_afetados": len(resultados), "resultados": resultados}


def _exec_ataque_de_positividade(ctx, alvo):
    usuario = ctx.get("usuario")
    passos = 0
    for efeito in list(getattr(usuario, "efeitos_formais", []) or []):
        if str((efeito or {}).get("tipo") or "").strip().lower() != "positivo":
            continue
        restantes = int(fnum((efeito or {}).get("passos_restantes"), 0.0))
        if restantes > 0:
            passos += restantes
    passos = min(passos, int(_param(ctx, "max_passos_considerados", 25)))
    multiplicador = 1.0 + passos * _param(ctx, "bonus_dano_por_passo_positivo", 0.03)
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.65)
    ret = dano_generico(ctx, alvo, bruto, "especial", multiplicadores_condicionais=[{"multiplicador": multiplicador}])
    ret["passos_positivos_considerados"] = passos
    return ret


def _exec_encanto(ctx, alvo):
    return _aplicar_efeito_padrao(ctx, alvo, _param_str(ctx, "efeito_aplicado", "Encantado"), negativo=False)


_EXECUTES = {
    "bencao": _exec_bencao,
    "barragemarcana": _exec_barragem_arcana,
    "canalizar": _exec_canalizar,
    "amolecer": _exec_amolecer,
    "brilho": _exec_brilho,
    "salvamento": _exec_salvamento,
    "toquefabuloso": _exec_toque_fabuloso,
    "cortedasfadas": _exec_corte_das_fadas,
    "chuvacintilante": _exec_chuva_cintilante,
    "ventofada": _exec_vento_fada,
    "bondade": _exec_bondade,
    "luzpurificadora": _exec_luz_purificadora,
    "depositividade": _exec_ataque_de_positividade,
    "encanto": _exec_encanto,
}

_ALIASES = {
    "299": "bencao",
    "300": "barragemarcana",
    "301": "canalizar",
    "302": "amolecer",
    "303": "brilho",
    "304": "salvamento",
    "305": "toquefabuloso",
    "306": "cortedasfadas",
    "307": "chuvacintilante",
    "308": "ventofada",
    "309": "bondade",
    "310": "luzpurificadora",
    "311": "depositividade",
    "312": "encanto",
}


def obter_executes_fada():
    return dict(_EXECUTES)


def obter_passivas_ataques_fada():
    return []


def obter_aliases_executes_fada():
    return dict(_ALIASES)
