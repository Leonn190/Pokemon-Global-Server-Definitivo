from __future__ import annotations

import math

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    alvos_linha_inimigos_area,
    aplicar_mod_atributo,
    aplicar_status,
    area_selecionada_da_acao,
    dano_generico,
    efeito_formal,
    executar_danca_clima,
    fnum,
    normalizar,
    pokemons_ativos_em_campo,
    remover_efeitos_contando_passos,
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


def _registrar_log(ctx, tipo, dados):
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(tipo, dados)


def _clima_nevasca(ctx):
    return normalizar(getattr((ctx or {}).get("partida"), "clima_atual", "")) == "nevasca"


def _lado(pokemon):
    try:
        return int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        return -1


def _inimigos_ativos(ctx):
    usuario = (ctx or {}).get("usuario")
    return [p for p in pokemons_ativos_em_campo((ctx or {}).get("partida")) if usuario is not None and _lado(p) != _lado(usuario)]


def _esta_em_ponta(pokemon, parametros):
    areas = parametros.get("areas_ponta") if isinstance(parametros, dict) else None
    if not isinstance(areas, (list, tuple, set)):
        areas = ["A1", "A3", "A7", "A9", "I1", "I3", "I7", "I9"]
    return str(getattr(pokemon, "area_id", "") or "").upper() in {str(area).upper() for area in areas}


def _alterar_passos_efeito(ctx, alvo, efeito, nome, depois, fallback):
    antes = max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0)))
    depois = max(0, int(depois))
    efeito["passos_restantes"] = depois
    efeito["passos_totais"] = max(int(fnum(efeito.get("passos_totais"), 0.0)), depois)
    _registrar_log(
        ctx,
        "efeito_passos_alterados",
        {
            "pokemon_id": getattr(alvo, "id_batalha", None),
            "pokemon_nome": getattr(alvo, "nome", None),
            "efeito_nome": nome,
            "passos_antes": antes,
            "passos_depois": depois,
            **_ataque_id_nome(ctx, fallback),
        },
    )
    return {"passos_antes": antes, "passos_depois": depois}


def _exec_nevoa_fria(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("SpA") * _param(ctx, "mult_spa_alvo", 0.10)
    valor += usuario.obter_atributo("Mag") * _param(ctx, "mult_mag_usuario", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Nevoa Fria", "SpA", -valor, negativo=True)


def _exec_cristalizar(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is not None and alvo.possui_efeito("Encharcado"):
        removido = remover_efeitos_contando_passos(alvo, ["Encharcado"], origem=usuario, dados={**_ataque_id_nome(ctx, "Cristalizar"), "motivo": "Cristalizar"})
        congelado = aplicar_status(ctx, alvo, "Congelado", negativo=True)
        ret = {"aplicado": True, "encharcado_removido": removido, "congelado": congelado}
        if _esta_aprimorado(ctx) and alvo.esta_vivo():
            ret["dano"] = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa_encharcado", 0.35), "especial")
        return ret
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa_dano", 0.45), "especial")


def _exec_gelinho(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.65), "especial")


def _exec_olhar_frio(ctx, alvo):
    atributos = ((ctx.get("propriedades") or {}).get("parametros") or {}).get("atributos_regulares")
    if not isinstance(atributos, list):
        atributos = ["Atk", "SpA", "Def", "SpD", "Mag", "Ene", "Vel", "Per", "Int"]
    atributo, maior = max(((atributo, alvo.obter_atributo(atributo)) for atributo in atributos), key=lambda item: item[1])
    valor = maior * _param(ctx, "percentual_reducao", 0.15)
    return aplicar_mod_atributo(ctx, alvo, "Olhar Frio", atributo, -valor, negativo=True)


def _exec_congelamento_tatico(ctx, alvo):
    ret = {
        "aplicado": True,
        "congelado": aplicar_status(ctx, alvo, "Congelado", duracao=_param(ctx, "duracao", 6), negativo=True),
        "regeneracao": aplicar_status(ctx, alvo, "Regeneracao", duracao=_param(ctx, "duracao", 6), negativo=False),
    }
    if _esta_aprimorado(ctx):
        usuario = ctx.get("usuario")
        valor = usuario.obter_atributo("Mag") * _param(ctx, "barreira_mult_mag", 0.20)
        if hasattr(usuario, "AplicarBarreira"):
            ret["barreira"] = usuario.AplicarBarreira(alvo, valor, dados={**_ataque_id_nome(ctx, "Congelamento Tatico"), "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_gelo_verdadeiro(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial", ignorar_defesa=True)


def _exec_raio_aurora(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    if usuario is None or not area_id:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    resultados = []
    for idx, inimigo in enumerate(alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)):
        ret = dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.85), "especial")
        if ret.get("critico") and inimigo.esta_vivo():
            ret["congelado"] = aplicar_status(ctx, inimigo, "Congelado", negativo=True)
        resultados.append({"pokemon_id": inimigo.id_batalha, "indice_hit": idx, "dano": ret})
    return {"aplicado": True, "area_id": area_id, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_nevasca(ctx, alvo):
    return executar_danca_clima(ctx, "Nevasca")


def _exec_tumba_de_gelo(ctx, alvo):
    usuario = ctx.get("usuario")
    efeito = efeito_formal(alvo, "Congelado")
    if efeito is not None:
        antes = max(0, int(fnum(efeito.get("passos_restantes"), 0.0)))
        passos = _alterar_passos_efeito(ctx, alvo, efeito, "Congelado", antes * 2, "Tumba de Gelo")
        ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa_congelado", 0.70), "especial")
        ret["congelado_passos"] = passos
        return ret
    if _clima_nevasca(ctx):
        congelado = aplicar_status(ctx, alvo, "Congelado", duracao=_param(ctx, "duracao", 6), negativo=True)
        ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa_nevasca", 0.35), "especial")
        ret["congelado"] = congelado
        return ret
    return {"aplicado": True, "sem_dano": True, "motivo": "alvo_sem_congelado_sem_nevasca"}


def _exec_quebra_gelo(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo_congelado = alvo is not None and alvo.possui_efeito("Congelado")
    multiplicadores = []
    if alvo_congelado:
        multiplicadores.append({"label": "Quebra-Gelo contra Congelado", "multiplicador": 1.0 + _param(ctx, "bonus_dano_congelado", 0.70)})
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.70), "normal", multiplicadores_condicionais=multiplicadores)
    if alvo_congelado:
        efeito = efeito_formal(alvo, "Congelado")
        if ret.get("critico") and efeito is not None:
            antes = max(0, int(fnum(efeito.get("passos_restantes"), 0.0)))
            ret["congelado_passos"] = _alterar_passos_efeito(ctx, alvo, efeito, "Congelado", math.ceil(antes / 2.0), "Quebra-Gelo")
        else:
            ret["congelado_removido"] = remover_efeitos_contando_passos(alvo, ["Congelado"], origem=usuario, dados={**_ataque_id_nome(ctx, "Quebra-Gelo"), "motivo": "Quebra-Gelo"})
    return ret


def _exec_ataque_polar(ctx, alvo):
    usuario = ctx.get("usuario")
    parametros = (ctx.get("propriedades") or {}).get("parametros") if isinstance((ctx.get("propriedades") or {}).get("parametros"), dict) else {}
    multiplicadores = []
    if _esta_em_ponta(usuario, parametros):
        multiplicadores.append({"label": "Ataque Polar usuario em ponta", "multiplicador": 1.0 + _param(ctx, "bonus_ponta_usuario", 0.25)})
    if _esta_em_ponta(alvo, parametros):
        multiplicadores.append({"label": "Ataque Polar alvo em ponta", "multiplicador": 1.0 + _param(ctx, "bonus_ponta_alvo", 0.25)})
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.75), "normal", multiplicadores_condicionais=multiplicadores)


def _exec_avalanche(ctx, alvo):
    usuario = ctx.get("usuario")
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        multiplicadores = []
        if _clima_nevasca(ctx):
            multiplicadores.append({"label": "Avalanche em Nevasca", "multiplicador": 1.0 + _param(ctx, "bonus_nevasca", 0.25)})
        if inimigo.possui_efeito("Encharcado"):
            multiplicadores.append({"label": "Avalanche contra Encharcado", "multiplicador": 1.0 + _param(ctx, "bonus_encharcado", 0.25)})
        resultados.append({"pokemon_id": inimigo.id_batalha, "resultado": dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.60), "especial", multiplicadores_condicionais=multiplicadores)})
    return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_bola_de_neve(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is not None and alvo.possui_efeito("Congelado"):
        return {"aplicado": True, "sem_dano": True, "motivo": "alvo_congelado"}
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.45), "especial")
    nome_contador = str(((ctx.get("propriedades") or {}).get("parametros") or {}).get("nome_contador") or "Bola de Neve")
    alvo.contadores_especiais[nome_contador] = int(fnum(alvo.contadores_especiais.get(nome_contador), 0.0)) + int(_param(ctx, "stacks_por_uso", 1))
    ret["stacks_bola_de_neve"] = alvo.contadores_especiais[nome_contador]
    if alvo.contadores_especiais[nome_contador] >= int(_param(ctx, "stacks_para_congelar", 3)):
        alvo.contadores_especiais[nome_contador] = 0
        ret["congelado"] = aplicar_status(ctx, alvo, "Congelado", duracao=_param(ctx, "duracao", 6), negativo=True)
        if _esta_aprimorado(ctx) and alvo.esta_vivo():
            ret["dano_extra"] = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa_extra_ao_congelar", 0.20), "especial", impacto_secundario=True)
    return ret


def _exec_reinado_de_gelo(ctx, alvo):
    usuario = ctx.get("usuario")
    qtd = sum(1 for pokemon in pokemons_ativos_em_campo(ctx.get("partida")) if pokemon.possui_efeito("Congelado"))
    bonus = min(qtd * _param(ctx, "bonus_por_congelado", 0.10), _param(ctx, "bonus_max", 0.60))
    multiplicadores = [{"label": "Reinado de Gelo por Congelados", "multiplicador": 1.0 + bonus}] if bonus > 0 else []
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial", multiplicadores_condicionais=multiplicadores)
    ret["congelados_em_campo"] = qtd
    return ret


def _exec_raio_de_gelo(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    if usuario is None or not area_id:
        return {"falha": True, "motivo": "area_alvo_invalida"}
    resultados = []
    for idx, inimigo in enumerate(alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)):
        bruto = max(0.0, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 1.00) - usuario.obter_atributo("SpA") * _param(ctx, "reducao_spa_por_alvo", 0.15) * idx)
        resultados.append({"pokemon_id": inimigo.id_batalha, "indice_hit": idx, "dano": dano_generico(ctx, inimigo, bruto, "especial")})
    return {"aplicado": True, "area_id": area_id, "alvos_atingidos": len(resultados), "resultados": resultados}


_EXECUTES = {
    "nevoafria": _exec_nevoa_fria,
    "cristalizar": _exec_cristalizar,
    "gelinho": _exec_gelinho,
    "olharfrio": _exec_olhar_frio,
    "congelamentotatico": _exec_congelamento_tatico,
    "geloverdadeiro": _exec_gelo_verdadeiro,
    "raioaurora": _exec_raio_aurora,
    "nevasca": _exec_nevasca,
    "tumbadegelo": _exec_tumba_de_gelo,
    "quebragelo": _exec_quebra_gelo,
    "ataquepolar": _exec_ataque_polar,
    "avalanche": _exec_avalanche,
    "boladeneve": _exec_bola_de_neve,
    "reinadodegelo": _exec_reinado_de_gelo,
    "raiodegelo": _exec_raio_de_gelo,
}

_ALIASES = {
    "109": "nevoafria",
    "110": "cristalizar",
    "111": "gelinho",
    "112": "olharfrio",
    "113": "congelamentotatico",
    "114": "geloverdadeiro",
    "115": "raioaurora",
    "116": "nevasca",
    "117": "tumbadegelo",
    "118": "quebragelo",
    "119": "ataquepolar",
    "polar": "ataquepolar",
    "120": "avalanche",
    "121": "boladeneve",
    "122": "reinadodegelo",
    "123": "raiodegelo",
}


def obter_executes_gelo():
    return dict(_EXECUTES)


def obter_passivas_ataques_gelo():
    return []


def obter_aliases_executes_gelo():
    return dict(_ALIASES)
