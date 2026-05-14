from __future__ import annotations

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_efeito,
    aplicar_mod_atributo,
    aplicar_status,
    dano_direto_vida,
    dano_generico,
    fnum,
    linha_ordenada_por_direcao,
    pokemons_vivos_adjacentes_todos_lados,
    remover_equipavel_temporario_batalha,
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


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _area_alvo(ctx, alvo=None):
    if alvo is not None and getattr(alvo, "area_id", None):
        return str(alvo.area_id).upper()
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    alvo_acao = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo_acao.get("tipo") or "").strip().lower() == "multi":
        for item in list(alvo_acao.get("alvos") or []):
            if isinstance(item, dict) and item.get("area_id"):
                return str(item.get("area_id")).upper()
    return str(alvo_acao.get("area_id") or "").upper() or None


def _lado(pokemon):
    try:
        return int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        return -1


def _exec_casca_de_pedra(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "mag_pct", 0.20)
    valor += usuario.obter_atributo("Def") * _param(ctx, "def_pct", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Casca de Pedra", "Def", valor, negativo=False)


def _exec_barragem_rochosa(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = usuario.obter_atributo("Mag") * _param(ctx, "mag_pct", 0.18)
    valor += usuario.obter_atributo("Def") * _param(ctx, "def_pct", 0.15)
    return usuario.AplicarBarreira(alvo, valor, dados=_ataque_id_nome(ctx, "Barragem Rochosa"))


def _exec_pedregulho(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 1.00)
    mult_def = _param(ctx, "def_alvo_reducao_mult", 1.50)
    defesa_original = alvo.atributos_finais.get("Def") if hasattr(alvo, "atributos_finais") else None
    if defesa_original is None:
        return dano_generico(ctx, alvo, bruto, "normal")
    alvo.atributos_finais["Def"] = alvo.obter_atributo("Def") * mult_def
    try:
        return dano_generico(ctx, alvo, bruto, "normal", def_alvo_reducao_mult=mult_def)
    finally:
        alvo.atributos_finais["Def"] = defesa_original


def _exec_polida_estrategica(ctx, alvo):
    usuario = ctx.get("usuario")
    from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import resolver_critico_contextual

    critico = resolver_critico_contextual(usuario, ctx, tipo="polida_estrategica")
    pct = _param(ctx, "perda_vida_pct_critico", 0.03) if critico.get("critico") else _param(ctx, "perda_vida_pct", 0.05)
    perda = usuario.obter_atributo("Vida") * pct
    ret = dano_direto_vida(ctx, usuario, perda, motivo="Polida Estrategica", respeitar_imortal=True)
    ret["critico_contextual"] = critico
    ret["bonus_vel"] = aplicar_mod_atributo(ctx, usuario, "Polida Estrategica", "Vel", usuario.obter_atributo("Vel") * _param(ctx, "vel_pct", 0.15), negativo=False)
    return ret


def _exec_chuva_aspera(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    rng = ctx.get("rng") or getattr(partida, "rng", None)
    if partida is None or usuario is None:
        return {"falha": True, "motivo": "partida_invalida"}
    areas = [
        str(area_id).upper()
        for area_id, area in sorted((getattr(partida, "areas", {}) or {}).items())
        if int((area or {}).get("lado_id", -1)) != _lado(usuario)
    ]
    qtd = min(len(areas), int(_param(ctx, "qtd_areas", 3)))
    sorteadas = rng.sample(areas, qtd) if rng is not None and qtd > 0 else areas[:qtd]
    resultados = []
    for area_id in sorteadas:
        alvo_area = partida.pokemon_na_area(area_id)
        item = {"area_id": area_id, "pokemon_id": getattr(alvo_area, "id_batalha", None), "dano": None}
        if alvo_area is not None and alvo_area.esta_vivo() and _lado(alvo_area) != _lado(usuario):
            item["dano"] = dano_generico(ctx, alvo_area, usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 0.65), "normal", area_alvo=area_id)
        resultados.append(item)
    _registrar_log(ctx, "areas_sorteadas_ataque", {**_ataque_id_nome(ctx, "Chuva Aspera"), "areas": sorteadas, "resultados": resultados})
    return {"aplicado": True, "areas_sorteadas": sorteadas, "resultados": resultados}


def _exec_fragmento_incisivo(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 0.65), "normal")
    if not ret.get("falha"):
        ret["efeito"] = aplicar_status(ctx, alvo, "Quebrado")
    return ret


def _exec_pedra_especial(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "spa_pct", 0.70)
    bruto += usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 0.20)
    return dano_generico(ctx, alvo, bruto, "especial")


def _exec_pedra_dupla(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 0.75), "normal", chance_critico=0.0)


def _exec_poder_anciao(ctx, alvo):
    usuario = ctx.get("usuario")
    bonus = usuario.obter_atributo("Mag") * _param(ctx, "mag_pct", 0.05)
    resultados = {}
    for atributo in ["Atk", "SpA", "Def", "SpD"]:
        resultados[atributo] = aplicar_mod_atributo(ctx, usuario, "Poder Anciao", atributo, bonus, negativo=False)
    return {"aplicado": True, "bonus": bonus, "atributos": resultados}


def _zerar_variacao_positiva(ctx, alvo, atributo):
    anterior = fnum(getattr(alvo, "variacoes_permanentes", {}).get(atributo), 0.0)
    if anterior <= 0:
        return {"aplicado": False, "atributo": atributo, "variacao_antes": anterior}
    alvo.variacoes_permanentes[atributo] = 0.0
    if hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    _registrar_log(
        ctx,
        "pokemon_variou_atributo",
        {
            "pokemon_id": getattr(alvo, "id_batalha", None),
            "pokemon_nome": getattr(alvo, "nome", None),
            "alvo_id": getattr(alvo, "id_batalha", None),
            "alvo_nome": getattr(alvo, "nome", None),
            "origem_id": getattr(ctx.get("usuario"), "id_batalha", None),
            "origem_nome": getattr(ctx.get("usuario"), "nome", None),
            "atributo": atributo,
            "valor": round(-anterior, 4),
            "variacao": round(-anterior, 4),
            "variacao_antes": round(anterior, 4),
            "variacao_total": 0.0,
            **_ataque_id_nome(ctx, "Lamina de Cristal"),
        },
    )
    return {"aplicado": True, "atributo": atributo, "variacao_zerada": anterior}


def _exec_lamina_de_cristal(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 0.45)
    bruto += usuario.obter_atributo("SpA") * _param(ctx, "spa_pct", 0.45)
    if alvo.obter_atributo("SpD") < alvo.obter_atributo("Def"):
        reset = _zerar_variacao_positiva(ctx, alvo, "SpD")
        ret = dano_generico(ctx, alvo, bruto, "especial")
        ret["atributo_zerado"] = reset
        return ret
    reset = _zerar_variacao_positiva(ctx, alvo, "Def")
    ret = dano_generico(ctx, alvo, bruto, "normal")
    ret["atributo_zerado"] = reset
    return ret


def _exec_escudo_de_pedra(ctx, alvo):
    usuario = ctx.get("usuario")
    atual = max(0.0, fnum(getattr(usuario, "BarreiraAtual", 0.0), 0.0))
    ganho = atual if atual > 0 else usuario.obter_atributo("Def") * _param(ctx, "barreira_sem_barreira_def_pct", 0.10)
    ret = usuario.AplicarBarreira(usuario, ganho, dados=_ataque_id_nome(ctx, "Escudo de Pedra"))
    ret["barreira_antes"] = atual
    return ret


def _exec_rolagem(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    area_id = _area_alvo(ctx, alvo)
    linha = linha_ordenada_por_direcao(area_id, getattr(usuario, "lado_id", 50))
    alvos = []
    for area_linha in linha:
        alvo_linha = partida.pokemon_na_area(area_linha) if partida is not None else None
        if alvo_linha is not None and alvo_linha.esta_vivo() and _lado(alvo_linha) != _lado(usuario):
            alvos.append(alvo_linha)
    base = usuario.obter_atributo("Def") * _param(ctx, "def_pct", 0.80)
    mult = 1.0
    soma = 0.0
    resultados = []
    for alvo_linha in alvos:
        ret = dano_generico(ctx, alvo_linha, base * mult, "normal", multiplicador_rolagem=mult)
        soma += fnum(ret.get("dano_vida"), 0.0)
        resultados.append({"pokemon_id": alvo_linha.id_batalha, "area_id": alvo_linha.area_id, "multiplicador": mult, "dano": ret})
        mult *= _param(ctx, "reducao_por_alvo_mult", 0.75)
    recoil = soma * _param(ctx, "recoil_dano_causado_pct", 0.08)
    recoil_ret = dano_direto_vida(ctx, usuario, recoil, motivo="Recoil Rolagem", respeitar_imortal=True)
    return {"aplicado": True, "area_id": area_id, "alvos_atingidos": len(resultados), "resultados": resultados, "dano_vida_total": soma, "recoil": recoil_ret}


def _exec_impacto_rochoso(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Def") * _param(ctx, "def_pct", 1.30), "normal")
    ret["perda_def"] = aplicar_mod_atributo(ctx, usuario, "Impacto Rochoso", "Def", -(usuario.obter_atributo("Def") * _param(ctx, "perda_def_pct", 0.10)), negativo=True)
    return ret


def _exec_pedra_colossal(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 0.80), "normal")
    ret["equipavel_removido"] = remover_equipavel_temporario_batalha(ctx, alvo, quantidade=_param(ctx, "qtd_equipaveis_remover", 1))
    return ret


def _exec_autodestruicao(ctx, alvo):
    usuario = ctx.get("usuario")
    duracao = int(_param(ctx, "duracao_imortal_passos", 1))
    efeito = aplicar_efeito(usuario, usuario, "Imortal", duracao=duracao, negativo=False)
    _forcar_duracao_efeito(usuario, "Imortal", duracao)
    adjacentes = pokemons_vivos_adjacentes_todos_lados(ctx, getattr(usuario, "area_id", None), ignorar=usuario)
    resultados = []
    soma = 0.0
    for alvo_adj in adjacentes:
        ret = dano_generico(ctx, alvo_adj, usuario.obter_atributo("Atk") * _param(ctx, "atk_pct", 1.50), "normal")
        soma += fnum(ret.get("dano_vida"), 0.0)
        resultados.append({"pokemon_id": alvo_adj.id_batalha, "area_id": alvo_adj.area_id, "dano": ret})
    recoil = soma * _param(ctx, "recoil_dano_causado_pct", 0.80)
    recoil_ret = dano_direto_vida(ctx, usuario, recoil, motivo="Recoil Autodestruicao", respeitar_imortal=True)
    return {"aplicado": True, "efeito_usuario": efeito, "alvos_atingidos": len(resultados), "resultados": resultados, "dano_vida_total": soma, "recoil": recoil_ret}


def _forcar_duracao_efeito(pokemon, nome, duracao):
    alvo = str(nome or "").strip().casefold()
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        chave = str((efeito or {}).get("nome") or (efeito or {}).get("code") or "").strip().casefold()
        if chave == alvo:
            efeito["passos_restantes"] = max(1, int(duracao or 1))
            efeito["passos_totais"] = max(1, int(duracao or 1))
            efeito["permanente"] = False
            return efeito
    return None


_EXECUTES = {
    "cascadepedra": _exec_casca_de_pedra,
    "barragemrochosa": _exec_barragem_rochosa,
    "pedregulho": _exec_pedregulho,
    "polidaestrategica": _exec_polida_estrategica,
    "chuvaaspera": _exec_chuva_aspera,
    "fragmentoincisivo": _exec_fragmento_incisivo,
    "pedraespecial": _exec_pedra_especial,
    "pedradupla": _exec_pedra_dupla,
    "poderanciao": _exec_poder_anciao,
    "laminadecristal": _exec_lamina_de_cristal,
    "escudodepedra": _exec_escudo_de_pedra,
    "rolagem": _exec_rolagem,
    "impactorochoso": _exec_impacto_rochoso,
    "pedracolossal": _exec_pedra_colossal,
    "autodestruicao": _exec_autodestruicao,
}

_ALIASES = {
    "222": "cascadepedra",
    "223": "barragemrochosa",
    "224": "pedregulho",
    "225": "polidaestrategica",
    "226": "chuvaaspera",
    "227": "fragmentoincisivo",
    "228": "pedraespecial",
    "229": "pedradupla",
    "230": "poderanciao",
    "231": "laminadecristal",
    "232": "escudodepedra",
    "233": "rolagem",
    "234": "impactorochoso",
    "235": "pedracolossal",
    "236": "autodestruicao",
}


def obter_executes_pedra():
    return dict(_EXECUTES)


def obter_passivas_ataques_pedra():
    return []


def obter_aliases_executes_pedra():
    return dict(_ALIASES)
