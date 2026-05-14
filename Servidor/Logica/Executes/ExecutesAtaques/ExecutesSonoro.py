from __future__ import annotations

import math

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    adjacentes_mesmo_lado,
    alvos_linha_inimigos_area,
    aplicar_mod_atributo,
    area_selecionada_da_acao,
    dano_generico,
    fnum,
)


def _params(ctx):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return props.get("parametros") if isinstance(props.get("parametros"), dict) else {}


def _param(ctx, chave, default):
    return fnum(_params(ctx).get(chave), default)


def _param_str(ctx, chave, default=""):
    valor = _params(ctx).get(chave)
    return str(valor if valor not in (None, "") else default)


def _aplicar_efeito_base(ctx, alvo, nome, negativo=None):
    usuario = (ctx or {}).get("usuario")
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    if usuario is None or alvo is None:
        return {"aplicado": False, "motivo": "alvo_invalido"}
    efeito = {"nome": nome}
    if negativo is not None:
        efeito["negativo"] = bool(negativo)
    return usuario.AplicarEfeito(alvo, efeito, dados={"origem_ataque": props.get("nome"), "reativos_acao": (ctx or {}).get("reativos_acao")})


def _aliados_vivos_adjacentes_usuario(ctx):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or usuario is None:
        return []
    saida = []
    for area_id in adjacentes_mesmo_lado(getattr(usuario, "area_id", None)):
        pokemon = partida.pokemon_na_area(area_id) if hasattr(partida, "pokemon_na_area") else None
        if pokemon is None or pokemon is usuario or not pokemon.esta_vivo():
            continue
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            saida.append(pokemon)
    return saida


def _exec_som_atordoante(ctx, alvo):
    return _aplicar_efeito_base(ctx, alvo, _param_str(ctx, "efeito_aplicado", "Atordoado"), negativo=True)


def _exec_voz_desarmadora(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.55), "especial")
    if bool(_params(ctx).get("aplica_recuo", True)) and alvo is not None and hasattr(alvo, "receber_recuo"):
        ret["recuo"] = alvo.receber_recuo(origem=usuario, dados={"ataque": "Voz Desarmadora"})
    return ret


def _exec_grito(ctx, alvo):
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx) or getattr(alvo, "area_id", None)
    alvos = alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=alvo)
    resultados = []
    for alvo_linha in alvos:
        ret = dano_generico(ctx, alvo_linha, usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.60), "especial")
        if ret.get("critico"):
            reducao = abs(_param(ctx, "reducao_amp_critico", 3.0))
            ret["reducao_amp"] = aplicar_mod_atributo(ctx, alvo_linha, "Grito", "Amp", -reducao, negativo=True)
        resultados.append({"pokemon_id": getattr(alvo_linha, "id_batalha", None), "dano": ret})
    if resultados:
        return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}
    if alvo is None:
        return {"aplicado": True, "alvos_atingidos": 0, "resultados": []}
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.60), "especial")
    if ret.get("critico") and alvo is not None:
        reducao = abs(_param(ctx, "reducao_amp_critico", 3.0))
        ret["reducao_amp"] = aplicar_mod_atributo(ctx, alvo, "Grito", "Amp", -reducao, negativo=True)
    return ret


def _exec_ataque_hipersonico(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 0.70)
    bruto += usuario.obter_atributo("Vel") * _param(ctx, "multiplicador_vel", 0.25)
    return dano_generico(ctx, alvo, bruto, "especial")


def _exec_canto_prolongador(ctx, alvo):
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    percentual = _param(ctx, "percentual_aumento_passos", 0.50)
    alterados = []
    for efeito in list(getattr(alvo, "efeitos_formais", []) or []):
        if bool((efeito or {}).get("permanente")) or int(fnum((efeito or {}).get("passos_restantes"), 0)) < 0:
            continue
        antes_restantes = max(0, int(fnum((efeito or {}).get("passos_restantes"), 0)))
        if antes_restantes <= 0:
            continue
        antes_totais = max(0, int(fnum((efeito or {}).get("passos_totais"), antes_restantes)))
        efeito["passos_restantes"] = max(antes_restantes, math.ceil(antes_restantes * (1.0 + percentual)))
        efeito["passos_totais"] = max(efeito["passos_restantes"], math.ceil(antes_totais * (1.0 + percentual)))
        alterados.append(
            {
                "efeito": efeito.get("nome") or efeito.get("code"),
                "passos_restantes_antes": antes_restantes,
                "passos_restantes_depois": efeito["passos_restantes"],
                "passos_totais_antes": antes_totais,
                "passos_totais_depois": efeito["passos_totais"],
            }
        )
    if alterados and hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(
            "efeitos_prolongados",
            {
                "alvo_id": getattr(alvo, "id_batalha", None),
                "alvo_nome": getattr(alvo, "nome", None),
                "usuario_id": getattr((ctx or {}).get("usuario"), "id_batalha", None),
                "percentual": percentual,
                "efeitos": alterados,
            },
        )
    return {"aplicado": True, "efeitos_alterados": alterados}


def _exec_melodia_anticlimatica(ctx, alvo):
    partida = ctx.get("partida")
    if partida is None:
        return {"falha": True, "motivo": "partida_invalida"}
    if hasattr(partida, "limpar_clima"):
        aplicado = partida.limpar_clima(motivo="Melodia Anticlimatica")
        return {"aplicado": True, "clima_removido": bool(aplicado)}
    antes = getattr(partida, "clima_atual", None)
    partida.clima_atual = None
    return {"aplicado": True, "clima_antes": antes, "clima_depois": None}


def _exec_volume_maximo(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "multiplicador_spa", 1.15), "especial", impacto_principal=True)
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    percentual = _param(ctx, "percentual_dano_causado_aliados_adjacentes", 0.25)
    ret["aliados_adjacentes"] = []
    if dano_vida <= 0 or percentual <= 0:
        return ret
    for aliado in _aliados_vivos_adjacentes_usuario(ctx):
        dano = dano_generico(ctx, aliado, dano_vida * percentual, "especial", impacto_secundario=True, alvo_principal_id=getattr(alvo, "id_batalha", None))
        ret["aliados_adjacentes"].append({"alvo_id": getattr(aliado, "id_batalha", None), "dano": dano})
    return ret


_EXECUTES = {
    "somatordoante": _exec_som_atordoante,
    "vozdesarmadora": _exec_voz_desarmadora,
    "grito": _exec_grito,
    "ataquehipersonico": _exec_ataque_hipersonico,
    "cantoprolongador": _exec_canto_prolongador,
    "melodiaanticlimatica": _exec_melodia_anticlimatica,
    "volumemaximo": _exec_volume_maximo,
}

_ALIASES = {
    "313": "somatordoante",
    "314": "vozdesarmadora",
    "315": "grito",
    "316": "ataquehipersonico",
    "ataquehipersonico": "ataquehipersonico",
    "317": "cantoprolongador",
    "318": "melodiaanticlimatica",
    "319": "volumemaximo",
}


def obter_executes_sonoro():
    return dict(_EXECUTES)


def obter_passivas_ataques_sonoro():
    return []


def obter_aliases_executes_sonoro():
    return dict(_ALIASES)
