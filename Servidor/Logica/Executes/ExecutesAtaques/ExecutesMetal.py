from __future__ import annotations

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    adjacentes_mesmo_lado,
    aplicar_mod_atributo,
    dano_direto_vida,
    dano_generico,
    fnum,
    linha_ordenada_por_direcao,
    resolver_critico_contextual,
)


def _param(ctx, chave, default=0.0):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _ataque_id_nome(ctx, fallback):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return {
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or fallback,
        "reativos_acao": (ctx or {}).get("reativos_acao"),
    }


def _lado(pokemon):
    try:
        return int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        return -1


def _area_alvo(ctx, alvo=None):
    if alvo is not None and getattr(alvo, "area_id", None):
        return str(alvo.area_id).upper()
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    alvo_acao = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo_acao.get("tipo") or "").strip().lower() == "multi":
        for item in list(alvo_acao.get("alvos") or []):
            if isinstance(item, dict) and item.get("area_id"):
                return str(item.get("area_id")).upper()
        return None
    return str(alvo_acao.get("area_id") or "").upper() or None


def _areas_selecionadas(ctx):
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo.get("tipo") or "").strip().lower() == "multi":
        return [str(item.get("area_id")).upper() for item in list(alvo.get("alvos") or []) if isinstance(item, dict) and item.get("area_id")]
    area_id = alvo.get("area_id")
    return [str(area_id).upper()] if area_id else []


def _aliados_adjacentes(ctx, usuario):
    partida = (ctx or {}).get("partida")
    if partida is None or usuario is None or not getattr(usuario, "area_id", None):
        return []
    aliados = []
    for area_id in adjacentes_mesmo_lado(usuario.area_id):
        pokemon = partida.pokemon_na_area(area_id)
        if pokemon is None or pokemon is usuario or not pokemon.esta_vivo() or getattr(pokemon, "reserva", False) or not getattr(pokemon, "ativo", False):
            continue
        if _lado(pokemon) == _lado(usuario):
            aliados.append(pokemon)
    return aliados


def _exec_ferrugem(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Def") * _param(ctx, "percentual_def_alvo", 0.10)
    valor += usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag_usuario", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Ferrugem", "Def", -valor, negativo=True)


def _exec_afiar(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag_usuario", 0.20)
    valor += usuario.obter_atributo("Per") * _param(ctx, "percentual_per_usuario", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Afiar", "Per", valor, negativo=False)


def _exec_metalurgia(ctx, alvo):
    usuario = ctx.get("usuario")
    critico = resolver_critico_contextual(usuario, ctx, tipo="metalurgia")
    percentual_per = _param(ctx, "percentual_mag_per_critico", 0.20) if critico.get("critico") else _param(ctx, "percentual_mag_per_normal", 0.15)
    ganho = usuario.obter_atributo("Mag") * percentual_per
    perda_pct = _param(ctx, "percentual_vida_maxima_perdida", 0.04)
    resultados = []
    for aliado in _aliados_adjacentes(ctx, usuario):
        perda = aliado.obter_atributo("Vida") * perda_pct
        resultados.append(
            {
                "pokemon_id": aliado.id_batalha,
                "area_id": aliado.area_id,
                "perda_vida": dano_direto_vida(ctx, aliado, perda, motivo="Metalurgia", respeitar_imortal=True),
                "per": aplicar_mod_atributo(ctx, aliado, "Metalurgia", "Per", ganho, negativo=False),
            }
        )
    return {"aplicado": True, "critico_contextual": critico, "aliados_adjacentes": len(resultados), "resultados": resultados}


def _exec_corte_e_recorte(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "multiplicador_atk", 0.55)
    bruto += usuario.obter_atributo("Per") * _param(ctx, "multiplicador_per", 0.25)
    bruto += usuario.obter_atributo("Vamp") * _param(ctx, "multiplicador_vamp", 0.25)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_barreira_ofensiva(ctx, alvo):
    usuario = ctx.get("usuario")
    ganho = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag_barreira", 0.15)
    barreira = usuario.AplicarBarreira(usuario, ganho, dados=_ataque_id_nome(ctx, "Barreira Ofensiva"))
    base_barreira = fnum(getattr(usuario, "BarreiraAtual", 0.0), 0.0) * _param(ctx, "percentual_barreira_atual_dano", 0.80)
    limite = usuario.obter_atributo("Mag") * _param(ctx, "limite_percentual_mag_dano", 1.20)
    dano = min(base_barreira, limite)
    ret = dano_generico(ctx, alvo, dano, "normal")
    ret["barreira_ganha"] = barreira
    ret["dano_base_barreira"] = round(base_barreira, 4)
    ret["limite_dano"] = round(limite, 4)
    return ret


def _exec_ima(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    areas = _areas_selecionadas(ctx)
    area_id = areas[0] if areas else _area_alvo(ctx, alvo)
    linha = linha_ordenada_por_direcao(area_id, getattr(usuario, "lado_id", 50))
    if partida is None or not linha:
        return {"falha": True, "motivo": "linha_invalida"}
    limite_puxao = linha[0]
    atingidos = []
    resultados = []
    for area_linha in linha:
        alvo_linha = partida.pokemon_na_area(area_linha)
        if alvo_linha is None or not alvo_linha.esta_vivo() or _lado(alvo_linha) == _lado(usuario):
            continue
        em_limite = str(area_linha).upper() == str(limite_puxao).upper()
        mult = 1.0 + _param(ctx, "bonus_dano_ultima_area", 0.30) if em_limite else 1.0
        ret = dano_generico(
            ctx,
            alvo_linha,
            usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.65),
            "especial",
            multiplicadores_condicionais=[{"label": "Alvo na ultima area possivel", "multiplicador": mult}],
        )
        resultados.append({"pokemon_id": alvo_linha.id_batalha, "area_id": area_linha, "multiplicador": mult, "dano": ret})
        if ret.get("aplicado"):
            atingidos.append(alvo_linha)
    deslocamento = max(1, int(_param(ctx, "deslocamento_puxao", 1)))
    movimentos = []
    for pokemon in sorted([p for p in atingidos if p.esta_vivo()], key=lambda p: linha.index(getattr(p, "area_id", "")) if getattr(p, "area_id", "") in linha else 999):
        origem = getattr(pokemon, "area_id", None)
        try:
            idx = linha.index(str(origem or "").upper())
        except ValueError:
            movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": origem, "moveu": False, "motivo": "fora_da_linha"})
            continue
        destino_idx = idx - deslocamento
        if destino_idx < 0:
            movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": origem, "moveu": False, "motivo": "ultima_area_possivel"})
            continue
        destino = linha[destino_idx]
        if partida.pokemon_na_area(destino) is not None:
            movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": destino, "moveu": False, "motivo": "destino_ocupado"})
            continue
        moveu = partida.mover_pokemon_para_area(pokemon, destino, dados={"origem": usuario, "ataque": "Ima", "reativos_acao": ctx.get("reativos_acao")})
        movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": destino, "moveu": bool(moveu)})
    return {"aplicado": True, "alvos_atingidos": len(atingidos), "resultados": resultados, "movimentos": movimentos}


def _exec_impacto_de_aco(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Def") * _param(ctx, "multiplicador_def", 0.55)
    bruto += usuario.obter_atributo("SpD") * _param(ctx, "multiplicador_spd", 0.55)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_cabecada_de_ferro(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "multiplicador_atk", 1.15)
    return dano_generico(ctx, alvo, bruto, "normal", usar_per_no_dano=False)


def _exec_cauda_de_ferro(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "multiplicador_atk", 0.80), "normal")
    def_base = fnum(getattr(alvo, "atributos_base", {}).get("Def"), 0.0)
    ret["reducao_def_base"] = aplicar_mod_atributo(ctx, alvo, "Cauda de Ferro", "Def", -(def_base * _param(ctx, "percentual_def_base_removida", 0.15)), negativo=True)
    return ret


def _exec_britadeira(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Per") * _param(ctx, "multiplicador_per", 1.60), "normal")


def _exec_super_fincada(ctx, alvo):
    usuario = ctx.get("usuario")
    per = usuario.obter_atributo("Per")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "multiplicador_atk", 0.60)
    bruto += per * _param(ctx, "multiplicador_per_dano", 0.25)
    ret = dano_generico(ctx, alvo, bruto, "normal")
    reducao = per * _param(ctx, "percentual_per_reducao_def_spd", 0.25)
    ret["reducao_def"] = aplicar_mod_atributo(ctx, alvo, "Super Fincada", "Def", -reducao, negativo=True)
    ret["reducao_spd"] = aplicar_mod_atributo(ctx, alvo, "Super Fincada", "SpD", -reducao, negativo=True)
    return ret


def _exec_liga_metalica(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    alvos = []
    vistos = set()
    for area_id in _areas_selecionadas(ctx):
        pokemon = partida.pokemon_na_area(area_id) if partida is not None else None
        if pokemon is None or not pokemon.esta_vivo() or _lado(pokemon) == _lado(usuario) or pokemon.id_batalha in vistos:
            continue
        vistos.add(pokemon.id_batalha)
        alvos.append((area_id, pokemon))
    soma_def = sum(pokemon.obter_atributo("Def") for _, pokemon in alvos)
    bonus = usuario.obter_atributo("Def") > soma_def
    mult = 1.0 + _param(ctx, "bonus_dano_se_def_maior_soma", 0.45) if bonus else 1.0
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "multiplicador_atk", 0.65)
    bruto += usuario.obter_atributo("Def") * _param(ctx, "multiplicador_def", 0.35)
    resultados = []
    for area_id, alvo_real in alvos:
        extras = {}
        if bonus:
            extras["multiplicadores_condicionais"] = [{"label": "Def do usuario maior que soma dos alvos", "multiplicador": mult}]
        resultados.append({"area_id": area_id, "alvo_id": alvo_real.id_batalha, "dano": dano_generico(ctx, alvo_real, bruto, "normal", **extras)})
    return {"aplicado": True, "areas_selecionadas": _areas_selecionadas(ctx), "alvos_atingidos": len(resultados), "soma_def_alvos": round(soma_def, 4), "bonus_def": bonus, "resultados": resultados}


def _exec_treinamento_de_metal(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng")
    opcoes = [("CrD", _param(ctx, "bonus_crd", 12)), ("CrC", _param(ctx, "bonus_crc", 12))]
    atributo, bonus = rng.choice(opcoes) if rng is not None else opcoes[0]
    ret = aplicar_mod_atributo(ctx, usuario, "Treinamento de Metal", atributo, bonus, negativo=False)
    ret["atributo_sorteado"] = atributo
    return ret


_EXECUTES = {
    "ferrugem": _exec_ferrugem,
    "afiar": _exec_afiar,
    "metalurgia": _exec_metalurgia,
    "corteerecorte": _exec_corte_e_recorte,
    "barreiraofensiva": _exec_barreira_ofensiva,
    "ima": _exec_ima,
    "impactodeaco": _exec_impacto_de_aco,
    "cabecadadeferro": _exec_cabecada_de_ferro,
    "caudadeferro": _exec_cauda_de_ferro,
    "britadeira": _exec_britadeira,
    "superfincada": _exec_super_fincada,
    "ligametalica": _exec_liga_metalica,
    "treinamentodemetal": _exec_treinamento_de_metal,
}

_ALIASES = {
    "286": "ferrugem",
    "287": "afiar",
    "288": "metalurgia",
    "289": "corteerecorte",
    "290": "barreiraofensiva",
    "291": "ima",
    "292": "impactodeaco",
    "293": "cabecadadeferro",
    "294": "caudadeferro",
    "295": "britadeira",
    "296": "superfincada",
    "297": "ligametalica",
    "298": "treinamentodemetal",
}


def obter_executes_metal():
    return dict(_EXECUTES)


def obter_passivas_ataques_metal():
    return []


def obter_aliases_executes_metal():
    return dict(_ALIASES)
