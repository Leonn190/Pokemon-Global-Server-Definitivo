from __future__ import annotations

from Servidor.Batalha.ResolvedorFlags import ExecuteReativo
from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    adicionar_efeito_formal_preservado,
    aplicar_mod_atributo,
    area_selecionada_da_acao,
    dano_direto_vida,
    dano_fixo_respeitando_barreira,
    dano_generico,
    dados_ataque_contexto,
    efeito_eh_positivo,
    fnum,
    parametro_execute,
    parametros_execute,
    remover_efeito_formal,
    resolver_critico_contextual,
)


def _ataque_id_nome(ctx, fallback):
    return {**dados_ataque_contexto(ctx, fallback), "reativos_acao": ctx.get("reativos_acao")}


def _exec_escama_mistica(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_pct", 0.20) + usuario.obter_atributo("SpD") * parametro_execute(ctx, "spd_pct", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Escama Mistica", "SpD", valor, negativo=False)


def _exec_barragem_draconica(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_pct", 0.18) + usuario.obter_atributo("SpD") * parametro_execute(ctx, "spd_pct", 0.15)
    return usuario.AplicarBarreira(alvo, valor, dados=_ataque_id_nome(ctx, "Barragem Draconica"))


def _exec_rugido(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Atk") * parametro_execute(ctx, "atk_alvo_pct", 0.10) + usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_usuario_pct", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Rugido", "Atk", -valor, negativo=True)


def _exec_garra_do_dragao(ctx, alvo):
    usuario = ctx.get("usuario")
    snapshot_def = alvo.obter_atributo("Def")
    snapshot_spd = alvo.obter_atributo("SpD")
    if snapshot_def < snapshot_spd:
        ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 0.85), "normal")
        ret["perda_def"] = aplicar_mod_atributo(ctx, alvo, "Garra do Dragao", "Def", -(snapshot_def * parametro_execute(ctx, "perda_def_pct", 0.20)), negativo=True)
        ret["caminho"] = "normal_def"
        return ret
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.85), "especial")
    ret["perda_spd"] = aplicar_mod_atributo(ctx, alvo, "Garra do Dragao", "SpD", -(snapshot_spd * parametro_execute(ctx, "perda_spd_pct", 0.20)), negativo=True)
    ret["caminho"] = "especial_spd"
    return ret


def _exec_ultraje(ctx, alvo):
    return dano_fixo_respeitando_barreira(ctx, alvo, parametro_execute(ctx, "dano_fixo", 27.0), motivo="Ultraje")


def _exec_sopro_do_dragao(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.70), "especial")
    qtd = int(parametro_execute(ctx, "remover_efeitos_positivos_critico", 2) if ret.get("critico") else parametro_execute(ctx, "remover_efeitos_positivos", 1))
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    positivos = [efeito for efeito in list(getattr(alvo, "efeitos_formais", []) or []) if efeito_eh_positivo(efeito)]
    removidos = []
    for _ in range(min(qtd, len(positivos))):
        idx = rng.randrange(len(positivos)) if rng is not None else 0
        efeito = positivos.pop(idx)
        if remover_efeito_formal(ctx, alvo, efeito, origem=usuario, motivo="Sopro do Dragao"):
            removidos.append({"nome": efeito.get("nome") or efeito.get("code")})
    ret["efeitos_positivos_removidos"] = removidos
    return ret


def _exec_tiro_de_escamas(ctx, alvo):
    usuario = ctx.get("usuario")
    chave = "tiro_de_escamas_usos_recebidos"
    usos_anteriores = int(fnum(getattr(alvo, "contadores_especiais", {}).get(chave), 0.0))
    multiplicador = 1.0 + parametro_execute(ctx, "bonus_dano_por_uso", 0.15) * usos_anteriores
    bruto = usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 0.55)
    ret = dano_generico(ctx, alvo, bruto, "normal", multiplicadores_condicionais=[{"label": "Tiro de Escamas recebido anteriormente", "multiplicador": multiplicador}])
    ret["bonus_def"] = aplicar_mod_atributo(ctx, alvo, "Tiro de Escamas", "Def", alvo.obter_atributo("Def") * parametro_execute(ctx, "bonus_def_alvo_pct", 0.02), negativo=False)
    alvo.contadores_especiais[chave] = usos_anteriores + 1
    ret["usos_anteriores_no_alvo"] = usos_anteriores
    return ret


def _exec_sem_fraquezas(ctx, alvo):
    usuario = ctx.get("usuario")
    atributos = parametros_execute(ctx).get("atributos_regulares")
    if not isinstance(atributos, list) or not atributos:
        atributos = ["Atk", "SpA", "Def", "SpD", "Mag", "Ene", "Vel", "Per", "Int"]
    snapshot = {atributo: usuario.obter_atributo(atributo) for atributo in atributos}
    escolhido = min(atributos, key=lambda atributo: snapshot.get(atributo, 0.0))
    bonus = snapshot.get(escolhido, 0.0) * parametro_execute(ctx, "ganho_pct", 0.25)
    ret = aplicar_mod_atributo(ctx, usuario, "Sem Fraquezas", escolhido, bonus, negativo=False)
    ret["atributo_escolhido"] = escolhido
    ret["snapshot"] = snapshot
    return ret


def _exec_juramento_do_dracomante(ctx, alvo):
    usuario = ctx.get("usuario")
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="barreira")
    critico = bool(critico_ctx.get("critico"))
    duracao = max(1, int(parametro_execute(ctx, "duracao_imortal_passos", 1)))
    efeito = adicionar_efeito_formal_preservado(
        ctx,
        usuario,
        {"nome": "Imortal", "code": "Imortal", "passos_restantes": duracao, "passos_totais": duracao, "dados": {}, "valor": 0.0, "stacks": 1, "tipo": "positivo", "permanente": False},
        origem=usuario,
    )
    pct = parametro_execute(ctx, "mag_barreira_pct_critico", 1.50) if critico else parametro_execute(ctx, "mag_barreira_pct", 1.20)
    barreira = usuario.AplicarBarreira(usuario, usuario.obter_atributo("Mag") * pct, dados={**_ataque_id_nome(ctx, "Juramento do Dracomante"), "critico": critico, "critico_contextual": critico_ctx})
    return {"aplicado": True, "critico": critico, "critico_contextual": critico_ctx, "efeito": efeito, "barreira": barreira}


def _exec_golpe_destrutivo(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    area_alvo = getattr(alvo, "area_id", None)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 0.90), "normal")
    if ret.get("critico") and partida is not None and hasattr(partida, "mudar_terreno") and area_alvo:
        ret["area_critico"] = partida.mudar_terreno(area_alvo, "Destruida", origem=usuario, dados=_ataque_id_nome(ctx, "Golpe Destrutivo"))
    return ret


def _exec_investida_draconica(ctx, alvo):
    usuario = ctx.get("usuario")
    dano_base = usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 1.10)
    ret = dano_generico(ctx, alvo, dano_base, "normal")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    recoil = dano_vida * parametro_execute(ctx, "recoil_dano_causado_pct", 0.20)
    ret["recoil"] = dano_direto_vida(ctx, usuario, recoil, motivo="Recoil Investida Draconica", respeitar_imortal=True) if recoil > 0 else {"aplicado": True, "dano_vida": 0.0}
    return ret


def _reativo_investida_draconica_erro(ctx):
    usuario = ctx.get("usuario")
    if usuario is None:
        return {}
    props = ctx.get("propriedades") if isinstance(ctx.get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    dano_base = usuario.obter_atributo("Atk") * fnum(parametros.get("atk_pct"), 1.10)
    recoil = dano_base * fnum(parametros.get("recoil_erro_dano_base_pct"), 0.30)
    return dano_direto_vida(ctx, usuario, recoil, motivo="Recoil Erro Investida Draconica", respeitar_imortal=True)


def _exec_territorio_sagrado(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    area_id = area_selecionada_da_acao(ctx)
    if partida is None or usuario is None or not area_id:
        return {"falha": True, "motivo": "area_invalida"}
    area = getattr(partida, "areas", {}).get(str(area_id).upper())
    if not isinstance(area, dict) or int(area.get("lado_id", -1)) != int(getattr(usuario, "lado_id", -2)):
        return {"falha": True, "motivo": "area_aliada_invalida"}
    if not hasattr(partida, "mudar_terreno"):
        return {"falha": True, "motivo": "sem_suporte_terreno"}
    aplicado = partida.mudar_terreno(area_id, "Sagrada", origem=usuario, dados=_ataque_id_nome(ctx, "Territorio Sagrado"))
    return {"aplicado": bool(aplicado), "area_id": str(area_id).upper(), "terreno": "Sagrada"}


def _exec_lanca_eterea(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpD") * parametro_execute(ctx, "spd_pct", 1.10), "especial")


_EXECUTES = {
    "escamamistica": _exec_escama_mistica,
    "barragemdraconica": _exec_barragem_draconica,
    "rugido": _exec_rugido,
    "garradodragao": _exec_garra_do_dragao,
    "ultraje": _exec_ultraje,
    "soprododragao": _exec_sopro_do_dragao,
    "tirodeescamas": _exec_tiro_de_escamas,
    "semfraquezas": _exec_sem_fraquezas,
    "juramentododracomante": _exec_juramento_do_dracomante,
    "golpedestrutivo": _exec_golpe_destrutivo,
    "investidadraconica": _exec_investida_draconica,
    "territoriosagrado": _exec_territorio_sagrado,
    "lancaeterea": _exec_lanca_eterea,
}

_ALIASES = {
    "256": "escamamistica",
    "257": "barragemdraconica",
    "258": "rugido",
    "259": "garradodragao",
    "260": "ultraje",
    "261": "soprododragao",
    "262": "tirodeescamas",
    "263": "semfraquezas",
    "264": "juramentododracomante",
    "265": "golpedestrutivo",
    "266": "investidadraconica",
    "267": "territoriosagrado",
    "268": "lancaeterea",
}

_EXECUTES_REATIVOS = [
    ExecuteReativo(nome="InvestidaDraconicaErro", flag="AoErrarAtaque", func=_reativo_investida_draconica_erro, origem_ataque="Investida Draconica", code="266", ordem=1),
]


def obter_executes_dragao():
    return dict(_EXECUTES)


def obter_executes_reativos_dragao():
    return list(_EXECUTES_REATIVOS)


def obter_passivas_ataques_dragao():
    return []


def obter_aliases_executes_dragao():
    return dict(_ALIASES)
