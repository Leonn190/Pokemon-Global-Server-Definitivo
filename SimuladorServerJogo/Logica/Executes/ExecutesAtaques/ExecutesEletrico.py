from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    dano_generico,
    executar_bola,
    executar_danca_clima,
    fnum,
)


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _ataque_id_nome(ctx, fallback):
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return {
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or fallback,
    }


def _exec_bola_eletrica(ctx, alvo):
    return executar_bola(ctx, alvo, "eletrico")


def _exec_energizar(ctx, alvo):
    if alvo is None:
        return {"aplicado": True, "sem_alvo": True}
    return aplicar_status(ctx, alvo, "Energizado", negativo=False)


def _exec_choque_duplo(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.70), "especial")


def _exec_descarga_total(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None:
        return {"falha": True, "motivo": "usuario_invalido"}
    energia = fnum(getattr(usuario, "EnergiaAtual", 0.0), 0.0)
    if energia <= 0:
        return {"falha": True, "motivo": "energia_zerada"}
    gasto = usuario.GastarEnergia(energia, dados={**_ataque_id_nome(ctx, "Descarga Total"), "motivo": "Descarga Total", "reativos_acao": ctx.get("reativos_acao")})
    if not gasto.get("aplicado"):
        return {"falha": True, "motivo": gasto.get("motivo") or "energia_insuficiente"}
    if alvo is None:
        return {"aplicado": True, "energia_gasta": gasto.get("valor", energia), "area_vazia": True}
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.45) + fnum(gasto.get("valor"), energia) * _param(ctx, "mult_energia", 1.20)
    ret = dano_generico(ctx, alvo, bruto, "especial")
    ret["energia_gasta"] = gasto
    return ret


def _exec_vampirismo_energetico(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.45), "especial")
    energia_atual = fnum(getattr(alvo, "EnergiaAtual", 0.0), 0.0)
    roubo = energia_atual * _param(ctx, "roubo_pct_energia", 0.25)
    if ret.get("critico"):
        roubo += usuario.obter_atributo("Vamp") * _param(ctx, "roubo_crit_vamp_pct", 0.15)
    roubo = min(energia_atual, max(0.0, roubo))
    gasto = alvo.GastarEnergia(roubo, dados={**_ataque_id_nome(ctx, "Vampirismo Energetico"), "motivo": "Vampirismo Energetico", "reativos_acao": ctx.get("reativos_acao")}) if roubo > 0 else {"aplicado": False, "valor": 0.0}
    ganho = usuario.GanharEnergia(fnum(gasto.get("valor"), 0.0), dados={**_ataque_id_nome(ctx, "Vampirismo Energetico"), "motivo": "Vampirismo Energetico", "reativos_acao": ctx.get("reativos_acao")}) if gasto.get("aplicado") else {"aplicado": False, "valor": 0.0}
    ret["roubo_energia"] = {"valor_planejado": round(roubo, 4), "gasto_alvo": gasto, "ganho_usuario": ganho}
    return ret


def _areas_lado_oposto(ctx):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    if partida is None or usuario is None:
        return []
    return [
        str(area_id)
        for area_id, area in (getattr(partida, "areas", {}) or {}).items()
        if int((area or {}).get("lado_id", -1)) != int(getattr(usuario, "lado_id", -2))
    ]


def _exec_eletrochoque(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    base = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.65)
    usos_anteriores = int(fnum(getattr(alvo, "contadores_especiais", {}).get("eletrochoque_usos"), 0.0))
    ret = dano_generico(ctx, alvo, base, "especial")
    alvo.contadores_especiais["eletrochoque_usos"] = usos_anteriores + 1
    areas = _areas_lado_oposto(ctx)
    resultados = []
    rng = ctx.get("rng") or getattr(partida, "rng", None)
    for _ in range(max(0, usos_anteriores)):
        area_id = rng.choice(areas) if rng is not None and areas else None
        pokemon = partida.pokemon_na_area(area_id) if partida is not None and area_id else None
        resultado = {"aplicado": True, "area_id": area_id, "area_vazia": pokemon is None}
        if pokemon is not None and pokemon.esta_vivo() and int(getattr(pokemon, "lado_id", -1)) != int(getattr(usuario, "lado_id", -2)):
            resultado = dano_generico(ctx, pokemon, base * _param(ctx, "replica_pct_base", 0.50), "especial", impacto_secundario=True, area_alvo=area_id)
            resultado["area_id"] = area_id
        resultados.append(resultado)
    ret["eletrochoque_usos_anteriores"] = usos_anteriores
    ret["replicas"] = resultados
    return ret


def _exec_curto(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.55)
    bruto += fnum(getattr(alvo, "EnergiaAtual", 0.0), 0.0) * _param(ctx, "mult_energia_alvo", 0.25)
    return dano_generico(ctx, alvo, bruto, "especial")


def _exec_choque_do_trovao(ctx, alvo):
    usuario = ctx.get("usuario")
    encharcado = alvo is not None and alvo.possui_efeito("Encharcado")
    extras = {"chance_critico": 100} if encharcado else {}
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial", **extras)
    ret["alvo_encharcado"] = encharcado
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["paralisado"] = aplicar_status(ctx, alvo, "Paralisado", negativo=True)
    return ret


def _exec_ultra_raio_aleatorio(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(partida, "rng", None)
    areas = list((getattr(partida, "areas", {}) or {}).keys()) if partida is not None else []
    if usuario is None or partida is None or not areas:
        return {"falha": True, "motivo": "arena_invalida"}
    area_id = rng.choice(areas) if rng is not None else areas[0]
    pokemon = partida.pokemon_na_area(area_id)
    ret = {"aplicado": True, "area_sorteada": area_id, "area_vazia": pokemon is None}
    partida.registrar_evento_log(
        "ultra_raio_area_sorteada",
        {**_ataque_id_nome(ctx, "Ultra Raio Aleatorio"), "area_sorteada": area_id, "area_vazia": pokemon is None, "alvo_id": getattr(pokemon, "id_batalha", None)},
    )
    if pokemon is not None and pokemon.esta_vivo():
        ret["dano"] = dano_generico(ctx, pokemon, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 1.35), "especial", area_alvo=area_id)
    return ret


def _exec_amplificar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Amplificar", "Amp", usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag", 0.25), 6, False)


def _exec_danca_eletrica(ctx, alvo):
    return executar_danca_clima(ctx, "Tempestade de Raios")


def _exec_campo_condutor(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is None:
        return {"aplicado": True, "sem_alvo": True}
    valor = max(0.0, usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag", 0.18) + usuario.obter_atributo("Ene") * _param(ctx, "percentual_ene", 0.12))
    return usuario.AplicarBarreira(alvo, valor, dados={**_ataque_id_nome(ctx, "Campo Condutor"), "reativos_acao": ctx.get("reativos_acao")})


_EXECUTES = {
    "bolaeletrica": _exec_bola_eletrica,
    "energizar": _exec_energizar,
    "choqueduplo": _exec_choque_duplo,
    "descargatotal": _exec_descarga_total,
    "vampirismoenergetico": _exec_vampirismo_energetico,
    "eletrochoque": _exec_eletrochoque,
    "curto": _exec_curto,
    "choquedotrovao": _exec_choque_do_trovao,
    "ultraraioaleatorio": _exec_ultra_raio_aleatorio,
    "amplificar": _exec_amplificar,
    "dancaeletrica": _exec_danca_eletrica,
    "barragemenergetica": _exec_campo_condutor,
}
_ALIASES = {
    "79": "bolaeletrica",
    "80": "energizar",
    "81": "choqueduplo",
    "82": "descargatotal",
    "83": "vampirismoenergetico",
    "84": "eletrochoque",
    "85": "curto",
    "86": "choquedotrovao",
    "87": "ultraraioaleatorio",
    "88": "amplificar",
    "89": "dancaeletrica",
    "90": "barragemenergetica",
    "bolaeletrica": "bolaeletrica",
    "energizar": "energizar",
    "choqueduplo": "choqueduplo",
    "descargatotal": "descargatotal",
    "vampirismoenergetico": "vampirismoenergetico",
    "eletrochoque": "eletrochoque",
    "curto": "curto",
    "choquedotrovao": "choquedotrovao",
    "ultraraioaleatorio": "ultraraioaleatorio",
    "amplificar": "amplificar",
    "dancaeletrica": "dancaeletrica",
    "barragemenergetica": "barragemenergetica",
}


def obter_executes_eletricos():
    return dict(_EXECUTES)


def obter_passivas_ataques_eletricas():
    return []


def obter_aliases_executes_eletricos():
    return dict(_ALIASES)
