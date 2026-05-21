from __future__ import annotations

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import fnum


def dano_generico(ctx, alvo, bruto, categoria="normal", **extra):
    usuario = (ctx or {}).get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    dados = {
        "dano_bruto": max(0.0, float(bruto or 0.0)),
        "tipo": parametros.get("tipo") or props.get("tipo") or "normal",
        "categoria": categoria,
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
        "reativos_acao": (ctx or {}).get("reativos_acao"),
        "bonus_critico_acerto": (ctx or {}).get("bonus_critico_acerto", 0.0),
        **extra,
    }
    return usuario.AplicarDano(alvo, dados, contexto=ctx)

def dano_puro_ignorando_barreira(ctx, alvo, valor, reducao_dur=True):
    usuario = (ctx or {}).get("usuario")
    if alvo is None or not alvo.esta_vivo():
        return {"aplicado": False, "motivo": "alvo_invalido", "dano_vida": 0.0}
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    dano_base = max(0.0, fnum(valor, 0.0))
    dano = dano_base
    calculo = [f"Dano puro base = {round(dano_base, 4)}"]
    dur = fnum(alvo.obter_atributo("Dur") if hasattr(alvo, "obter_atributo") else 0.0, 0.0)
    if reducao_dur and dur > 0:
        mult = max(0.0, 1.0 - (dur / 100.0))
        antes = dano
        dano *= mult
        calculo.append(f"Durabilidade: {round(antes, 4)} * {round(mult, 4)} = {round(dano, 4)}")
    antes_vida = fnum(getattr(alvo, "VidaAtual", 0.0), 0.0)
    alvo.VidaAtual = max(0.0, antes_vida - dano)
    dano_vida = max(0.0, antes_vida - alvo.VidaAtual)
    alvo.estatisticas_batalha["dano_recebido"] = fnum(alvo.estatisticas_batalha.get("dano_recebido"), 0.0) + dano_vida
    if usuario is not None:
        usuario.estatisticas_batalha["dano_causado"] = fnum(usuario.estatisticas_batalha.get("dano_causado"), 0.0) + dano_vida
    partida = (ctx or {}).get("partida") or getattr(alvo, "partida", None)
    dados = {
        "alvo_id": getattr(alvo, "id_batalha", None),
        "alvo_nome": getattr(alvo, "nome", None),
        "pokemon_id": getattr(alvo, "id_batalha", None),
        "pokemon_nome": getattr(alvo, "nome", None),
        "origem_id": getattr(usuario, "id_batalha", None),
        "origem_nome": getattr(usuario, "nome", None),
        "valor": round(dano_vida, 4),
        "vida_antes": round(antes_vida, 4),
        "vida_depois": round(alvo.VidaAtual, 4),
        "critico": False,
        "tipo": (props.get("parametros") if isinstance(props.get("parametros"), dict) else {}).get("tipo") or props.get("tipo"),
        "categoria": "puro",
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
        "detalhes": {"dano_base": round(dano_base, 4), "durabilidade": round(dur, 4), "ignora_barreira": True},
        "calculo": calculo,
    }
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log("pokemon_sofreu_dano", dados)
    retorno = {"aplicado": True, "dano_vida": round(dano_vida, 4), "dano_barreira": 0.0, "dano_puro": True, "critico": False}
    letalidade = False
    if dano_vida > 0 and usuario is not None and hasattr(alvo, "_aplicar_letalidade"):
        letalidade = bool(alvo._aplicar_letalidade(usuario, dano_vida, {"origem": usuario, "ataque_nome": dados.get("ataque_nome"), "reativos_acao": (ctx or {}).get("reativos_acao")}))
    if letalidade:
        retorno["letalidade"] = True
    if alvo.VidaAtual <= 0:
        alvo.Morrer({"origem_id": getattr(usuario, "id_batalha", None), "origem": usuario, "ataque_nome": dados.get("ataque_nome"), "reativos_acao": (ctx or {}).get("reativos_acao")})
    if partida is not None and hasattr(partida, "disparar_flag") and dano_vida > 0:
        flag_ctx = {
            "partida": partida,
            "usuario": usuario,
            "origem": usuario,
            "alvo": alvo,
            "pokemon_evento": alvo,
            "dano_vida": round(dano_vida, 4),
            "resultado": dict(retorno),
            "dados_dano": dict(dados),
            "reativos_acao": (ctx or {}).get("reativos_acao"),
        }
        partida.disparar_flag("AoReceberDano", flag_ctx, reativos=(ctx or {}).get("reativos_acao"))
        partida.disparar_flag("AoAplicarDano", {**flag_ctx, "pokemon_evento": usuario}, reativos=(ctx or {}).get("reativos_acao"))
    return retorno

def dano_direto_vida(ctx, alvo, valor, motivo=None, respeitar_imortal=True):
    usuario = (ctx or {}).get("usuario")
    if alvo is None or not alvo.esta_vivo():
        return {"aplicado": False, "motivo": "alvo_invalido", "dano_vida": 0.0}
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    dano = max(0.0, fnum(valor, 0.0))
    antes = fnum(getattr(alvo, "VidaAtual", 0.0), 0.0)
    vida_depois = max(0.0, antes - dano)
    imortal_bloqueou = False
    if respeitar_imortal and vida_depois <= 0 and hasattr(alvo, "possui_efeito") and alvo.possui_efeito("Imortal"):
        vida_depois = min(max(1.0, vida_depois), max(1.0, alvo.obter_atributo("Vida", 1.0)))
        imortal_bloqueou = True
    alvo.VidaAtual = vida_depois
    dano_vida = max(0.0, antes - alvo.VidaAtual)
    if hasattr(alvo, "estatisticas_batalha"):
        alvo.estatisticas_batalha["dano_recebido"] = fnum(alvo.estatisticas_batalha.get("dano_recebido"), 0.0) + dano_vida
    partida = (ctx or {}).get("partida") or getattr(alvo, "partida", None)
    dados = {
        "alvo_id": getattr(alvo, "id_batalha", None),
        "alvo_nome": getattr(alvo, "nome", None),
        "pokemon_id": getattr(alvo, "id_batalha", None),
        "pokemon_nome": getattr(alvo, "nome", None),
        "origem_id": getattr(usuario, "id_batalha", None),
        "origem_nome": getattr(usuario, "nome", None),
        "valor": round(dano_vida, 4),
        "vida_antes": round(antes, 4),
        "vida_depois": round(alvo.VidaAtual, 4),
        "critico": False,
        "tipo": (props.get("parametros") if isinstance(props.get("parametros"), dict) else {}).get("tipo") or props.get("tipo"),
        "categoria": "direto",
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
        "motivo": motivo or "dano_direto_vida",
        "ignora_barreira": True,
        "ignora_defesa": True,
        "imortal_bloqueou": imortal_bloqueou,
    }
    if partida is not None and hasattr(partida, "registrar_evento_log") and (dano_vida > 0 or dano > 0):
        partida.registrar_evento_log("pokemon_sofreu_dano", dados)
    if alvo.VidaAtual <= 0 and getattr(alvo, "vivo", False):
        alvo.Morrer({"origem_id": getattr(usuario, "id_batalha", None), "origem": usuario, "ataque_nome": dados.get("ataque_nome"), "reativos_acao": (ctx or {}).get("reativos_acao")})
    return {"aplicado": True, "dano_vida": round(dano_vida, 4), "dano_barreira": 0.0, "direto_vida": True, "imortal_bloqueou": imortal_bloqueou}

def dano_fixo_respeitando_barreira(ctx, alvo, valor, motivo=None):
    usuario = (ctx or {}).get("usuario")
    if alvo is None or not alvo.esta_vivo():
        return {"aplicado": False, "motivo": "alvo_invalido", "dano_vida": 0.0, "dano_barreira": 0.0}
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    dano = max(0.0, fnum(valor, 0.0))
    antes_barreira = fnum(getattr(alvo, "BarreiraAtual", 0.0), 0.0)
    dano_barreira = min(antes_barreira, dano)
    alvo.BarreiraAtual = max(0.0, antes_barreira - dano_barreira)
    restante = max(0.0, dano - dano_barreira)
    antes_vida = fnum(getattr(alvo, "VidaAtual", 0.0), 0.0)
    alvo.VidaAtual = max(0.0, antes_vida - restante)
    dano_vida = max(0.0, antes_vida - alvo.VidaAtual)
    if hasattr(alvo, "estatisticas_batalha"):
        alvo.estatisticas_batalha["dano_recebido"] = fnum(alvo.estatisticas_batalha.get("dano_recebido"), 0.0) + dano_vida
    if usuario is not None and hasattr(usuario, "estatisticas_batalha"):
        usuario.estatisticas_batalha["dano_causado"] = fnum(usuario.estatisticas_batalha.get("dano_causado"), 0.0) + dano_vida
    partida = (ctx or {}).get("partida") or getattr(alvo, "partida", None)
    base_evento = {
        "alvo_id": getattr(alvo, "id_batalha", None),
        "alvo_nome": getattr(alvo, "nome", None),
        "pokemon_id": getattr(alvo, "id_batalha", None),
        "pokemon_nome": getattr(alvo, "nome", None),
        "origem_id": getattr(usuario, "id_batalha", None),
        "origem_nome": getattr(usuario, "nome", None),
        "critico": False,
        "tipo": (props.get("parametros") if isinstance(props.get("parametros"), dict) else {}).get("tipo") or props.get("tipo"),
        "categoria": "fixo",
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
        "motivo": motivo or "dano_fixo_respeitando_barreira",
        "detalhes": {
            "dano_fixo": round(dano, 4),
            "ignora_modificadores": True,
            "respeita_barreira": True,
        },
        "calculo": [
            f"Dano fixo = {round(dano, 4)}",
            f"Barreira absorvida = {round(dano_barreira, 4)}",
            f"Dano em vida = {round(dano_vida, 4)}",
        ],
    }
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        if dano_barreira > 0:
            partida.registrar_evento_log(
                "barreira_absorveu",
                {
                    **base_evento,
                    "dano_original": round(dano, 4),
                    "dano_barreira": round(dano_barreira, 4),
                    "barreira_antes": round(antes_barreira, 4),
                    "barreira_depois": round(alvo.BarreiraAtual, 4),
                },
            )
        if dano_vida > 0 or dano <= 0.001:
            partida.registrar_evento_log(
                "pokemon_sofreu_dano",
                {
                    **base_evento,
                    "valor": round(dano_vida, 4),
                    "vida_antes": round(antes_vida, 4),
                    "vida_depois": round(alvo.VidaAtual, 4),
                    "dano_barreira": round(dano_barreira, 4),
                },
            )
    retorno = {
        "aplicado": True,
        "dano_vida": round(dano_vida, 4),
        "dano_barreira": round(dano_barreira, 4),
        "dano_fixo": True,
        "critico": False,
    }
    if alvo.VidaAtual <= 0 and getattr(alvo, "vivo", False):
        alvo.Morrer({"origem_id": getattr(usuario, "id_batalha", None), "origem": usuario, "ataque_nome": base_evento.get("ataque_nome"), "reativos_acao": (ctx or {}).get("reativos_acao")})
    if partida is not None and hasattr(partida, "disparar_flag") and dano_vida > 0:
        flag_ctx = {
            "partida": partida,
            "usuario": usuario,
            "origem": usuario,
            "alvo": alvo,
            "pokemon_evento": alvo,
            "dano_vida": round(dano_vida, 4),
            "resultado": dict(retorno),
            "dados_dano": dict(base_evento),
            "reativos_acao": (ctx or {}).get("reativos_acao"),
        }
        partida.disparar_flag("AoReceberDano", flag_ctx, reativos=(ctx or {}).get("reativos_acao"))
        partida.disparar_flag("AoAplicarDano", {**flag_ctx, "pokemon_evento": usuario}, reativos=(ctx or {}).get("reativos_acao"))
    return retorno
