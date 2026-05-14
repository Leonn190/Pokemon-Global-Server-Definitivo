from __future__ import annotations

import copy

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    adicionar_efeito_formal_preservado,
    aplicar_mod_atributo,
    aplicar_status,
    ctx_passiva_ataque,
    dano_direto_vida,
    dano_generico,
    dados_ataque_contexto,
    efeito_eh_negativo,
    efeito_eh_positivo,
    execute_passiva_nao_manual,
    fnum,
    inicio_fileira_area,
    inimigos_vivos_adjacentes_ao_alvo,
    numero_area_batalha,
    normalizar,
    parametro_execute,
    parametro_passiva_ataque,
    parametro_str_execute,
    passos_positivos_efeito,
    registrar_log_execute,
    remover_efeito_formal,
    remover_efeitos_negativos,
)


try:
    from Servidor.Batalha.PokemonBatalha import EFEITOS_NEGATIVOS
except Exception:
    EFEITOS_NEGATIVOS = {
        "queimado", "envenenado", "intoxicado", "congelado", "dormindo", "paralisado",
        "enraizado", "cauterizado", "descarregado", "encharcado", "atordoado",
        "quebrado", "enfraquecido", "confuso", "bloqueado", "amaldicoado",
    }


_NOMES_EFEITOS_NEGATIVOS = {
    "queimado": "Queimado",
    "envenenado": "Envenenado",
    "intoxicado": "Intoxicado",
    "congelado": "Congelado",
    "dormindo": "Dormindo",
    "paralisado": "Paralisado",
    "enraizado": "Enraizado",
    "cauterizado": "Cauterizado",
    "descarregado": "Descarregado",
    "encharcado": "Encharcado",
    "atordoado": "Atordoado",
    "quebrado": "Quebrado",
    "enfraquecido": "Enfraquecido",
    "confuso": "Confuso",
    "bloqueado": "Bloqueado",
    "amaldicoado": "Amaldiçoado",
}

def _exec_selar_arcano(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Mag") * parametro_execute(ctx, "mag_alvo_pct", 0.10) + usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_usuario_pct", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Selar Arcano", "Mag", -valor, negativo=True)


def _exec_desorientar(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Int") * parametro_execute(ctx, "int_alvo_pct", 0.10) + usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_usuario_pct", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Desorientar", "Int", -valor, negativo=True)


def _exec_atravessar(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.40), "especial")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    positivos = [efeito for efeito in list(getattr(alvo, "efeitos_formais", []) or []) if efeito_eh_positivo(efeito)]
    qtd = max(1, int(parametro_execute(ctx, "qtd_efeitos_roubar", 1)))
    roubados = []
    for _ in range(min(qtd, len(positivos))):
        idx = rng.randrange(len(positivos)) if rng is not None else 0
        efeito = positivos.pop(idx)
        copia = copy.deepcopy(efeito)
        if remover_efeito_formal(ctx, alvo, efeito, origem=usuario, motivo="Atravessar"):
            roubados.append(adicionar_efeito_formal_preservado(ctx, usuario, copia, origem=usuario))
    ret["efeitos_roubados"] = roubados
    return ret


def _exec_lambida(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 0.65), "normal")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    vamp = usuario.obter_atributo("Vamp", 0.0)
    if dano_vida > 0 and vamp > 0 and parametro_execute(ctx, "vamp_mult", 2.0) > 1.0:
        ret["cura_vamp_extra"] = usuario.ReceberCura(
            dano_vida * (vamp / 100.0) * (parametro_execute(ctx, "vamp_mult", 2.0) - 1.0),
            origem=usuario,
            dados={**dados_ataque_contexto(ctx, "Lambida"), "vampirismo_extra": True, "reativos_acao": ctx.get("reativos_acao")},
        )
    return ret


def _exec_toque_do_medo(ctx, alvo):
    usuario = ctx.get("usuario")
    mult = parametro_execute(ctx, "mult_alvo_paralisado", 2.0) if alvo is not None and alvo.possui_efeito("Paralisado") else 1.0
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.40), "especial", multiplicadores_condicionais=[{"label": "Alvo paralisado", "multiplicador": mult}])


def _exec_susto(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    forcar = bool(alvo is not None and alvo.possui_efeito("Dormindo")) or normalizar(getattr(partida, "clima_atual", "")) == normalizar(parametro_str_execute(ctx, "critico_se_clima", "Nevoa"))
    extras = {"chance_critico": 100.0, "chance_critico_max": 100.0} if forcar else {}
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 0.60), "normal", **extras)
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["efeito_critico"] = aplicar_status(ctx, alvo, parametro_str_execute(ctx, "efeito_critico", "Paralisado"), negativo=True)
    ret["critico_forcado_condicional"] = forcar
    return ret


def _exec_maldade(ctx, alvo):
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    nomes = [_NOMES_EFEITOS_NEGATIVOS.get(nome, str(nome).title()) for nome in sorted(set(EFEITOS_NEGATIVOS))]
    if not nomes:
        return {"falha": True, "motivo": "lista_efeitos_negativos_vazia"}
    escolhido = nomes[rng.randrange(len(nomes))] if rng is not None else nomes[0]
    return aplicar_status(ctx, alvo, escolhido, negativo=True)


def _exec_golpe_espelhado(ctx, alvo):
    usuario = ctx.get("usuario")
    numero_usuario = numero_area_batalha(getattr(usuario, "area_id", None))
    numero_alvo = numero_area_batalha(getattr(alvo, "area_id", None))
    espelhos = {1: 3, 2: 2, 3: 1, 4: 6, 5: 5, 6: 4, 7: 9, 8: 8, 9: 7}
    area_espelhada = numero_alvo == espelhos.get(numero_usuario)
    mult = parametro_execute(ctx, "mult_mesmo_numero_area", 1.50) if area_espelhada else 1.0
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.75), "especial", multiplicadores_condicionais=[{"label": "Area espelhada", "multiplicador": mult}])


def _exec_mao_espectral(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    dano_base = usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.70)
    ret = dano_generico(ctx, alvo, dano_base, "especial")
    origem = getattr(alvo, "area_id", None)
    destino = inicio_fileira_area(origem)
    if partida is None or alvo is None or not alvo.esta_vivo() or not destino or destino == origem:
        ret["movimento"] = {"aplicado": False, "motivo": "sem_movimento", "destino": destino}
        return ret
    prefixo = str(origem or "")[:1].upper()
    numero_origem = numero_area_batalha(origem)
    numero_destino = numero_area_batalha(destino)
    caminho = [f"{prefixo}{numero}" for numero in range(numero_origem - 1, numero_destino - 1, -1)]
    atingidos = []
    for area_id in caminho:
        ocupante_caminho = partida.pokemon_na_area(area_id)
        if ocupante_caminho is None or ocupante_caminho is alvo or not ocupante_caminho.esta_vivo():
            continue
        if int(getattr(ocupante_caminho, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        atingidos.append(
            {
                "area_id": area_id,
                "pokemon_id": getattr(ocupante_caminho, "id_batalha", None),
                "dano": dano_generico(ctx, ocupante_caminho, dano_base * parametro_execute(ctx, "mult_dano_ocupante_destino", 1.20), "especial", impacto_secundario=True),
            }
        )
    ret["dano_ocupantes_caminho"] = atingidos
    ocupante = partida.pokemon_na_area(destino)
    if ocupante is None:
        ret["movimento"] = {"aplicado": bool(partida.mover_pokemon_para_area(alvo, destino, dados={"origem": usuario, "ataque": "Mao Espectral", "reativos_acao": ctx.get("reativos_acao")})), "area_destino": destino}
        return ret
    if ocupante is alvo:
        ret["movimento"] = {"aplicado": False, "motivo": "alvo_no_destino", "area_destino": destino}
        return ret
    trocou = partida.trocar_posicao(alvo, ocupante, dados={"origem": usuario, "ataque": "Mao Espectral", "reativos_acao": ctx.get("reativos_acao")})
    ret["movimento"] = {"aplicado": bool(trocou), "tipo": "troca", "area_destino": destino, "ocupante_id": getattr(ocupante, "id_batalha", None)}
    return ret


def _exec_pulso_de_plasma(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.85), "especial")
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        ret["efeito_critico"] = aplicar_status(ctx, alvo, parametro_str_execute(ctx, "efeito_critico", "Enfraquecido"), negativo=True)
    return ret


def _exec_devorador_de_pecados(ctx, alvo):
    usuario = ctx.get("usuario")
    removidos = remover_efeitos_negativos(ctx, alvo, EFEITOS_NEGATIVOS, origem=usuario, motivo="Devorador de Pecados")
    ganho = min(parametro_execute(ctx, "vamp_max", 30.0), removidos.get("passos", 0) * parametro_execute(ctx, "vamp_por_passo", 3.0))
    vamp = aplicar_mod_atributo(ctx, usuario, "Devorador de Pecados", "Vamp", ganho, negativo=False) if ganho > 0 else {"aplicado": True, "valor": 0.0}
    return {"aplicado": True, "efeitos_removidos": removidos, "vamp_ganho": vamp}


def _exec_maldicao(ctx, alvo):
    return aplicar_status(ctx, alvo, parametro_str_execute(ctx, "efeito", "Amaldiçoado"), negativo=True)


def _exec_jogada_de_sorte(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    chance = parametro_execute(ctx, "chance_nao_fazer_nada", 0.70)
    rolagem = rng.random() if rng is not None else 1.0
    if rolagem < chance:
        registrar_log_execute(
            ctx,
            "ataque_sem_efeito",
            {
                "pokemon_id": getattr(usuario, "id_batalha", None),
                "pokemon_nome": getattr(usuario, "nome", None),
                "alvo_id": getattr(alvo, "id_batalha", None),
                "alvo_nome": getattr(alvo, "nome", None),
                "motivo": "jogada_de_sorte_nao_fez_nada",
                "chance_falha": round(chance, 4),
                "rolagem": round(rolagem, 4),
                **dados_ataque_contexto(ctx, "Jogada de Sorte"),
            },
        )
        return {"aplicado": True, "sem_efeito": True, "motivo": "jogada_de_sorte_nao_fez_nada", "rolagem": round(rolagem, 4)}
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 1.60), "normal")


def _exec_ataque_fantasmagorico(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    bonus = 0.0
    if alvo is not None and alvo.possui_efeito("Amaldiçoado"):
        bonus += parametro_execute(ctx, "bonus_alvo_amaldicoado", 0.35)
    if normalizar(getattr(partida, "clima_atual", "")) == "nevoa":
        bonus += parametro_execute(ctx, "bonus_clima_nevoa", 0.25)
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.85), "especial", multiplicadores_condicionais=[{"label": "Condicoes fantasmagoricas", "multiplicador": 1.0 + bonus}])


def _exec_sede_de_sangue_fantasma(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Sede de Sangue", "Vamp", usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_pct", 0.25), negativo=False)


def _exec_explosao_fantasma(ctx, alvo):
    usuario = ctx.get("usuario")
    adjacentes = inimigos_vivos_adjacentes_ao_alvo(ctx, alvo)
    alvo_principal_id = getattr(alvo, "id_batalha", None)
    secundarios_ids = [getattr(p, "id_batalha", None) for p in adjacentes if p is not None]
    ret = dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("SpA") * parametro_execute(ctx, "spa_pct", 0.90),
        "especial",
        alvo_principal_id=alvo_principal_id,
        alvos_secundarios_ids=secundarios_ids,
        impacto_principal=True,
    )
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    splashes = []
    if dano_vida > 0:
        for adjacente in adjacentes:
            if adjacente is None or not adjacente.esta_vivo():
                continue
            splash = dano_direto_vida(ctx, adjacente, dano_vida * parametro_execute(ctx, "splash_dano_real_pct", 0.10), motivo="Explosao Fantasma")
            efeito = aplicar_status(ctx, adjacente, parametro_str_execute(ctx, "efeito_adjacentes", "Vampirico"), negativo=False) if adjacente.esta_vivo() else None
            splashes.append({"pokemon_id": adjacente.id_batalha, "dano": splash, "efeito": efeito})
    ret["splashes"] = splashes
    return ret


def _exec_golpe_cruel(ctx, alvo):
    usuario = ctx.get("usuario")
    passos = sum(passos_positivos_efeito(efeito) for efeito in list(getattr(alvo, "efeitos_formais", []) or []) if efeito_eh_negativo(efeito, EFEITOS_NEGATIVOS))
    passos_limitados = min(int(parametro_execute(ctx, "max_passos_considerados", 25)), passos)
    mult = 1.0 + passos_limitados * parametro_execute(ctx, "bonus_por_passo_negativo", 0.03)
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * parametro_execute(ctx, "atk_pct", 0.70), "normal", multiplicadores_condicionais=[{"label": "Passos negativos", "multiplicador": mult}])
    ret["passos_negativos_considerados"] = passos_limitados
    return ret


def _passiva_fantasma(ctx):
    dono = ctx.get("dono_passiva")
    if dono is None:
        return {}
    chave = "passiva_fantasma_254_aplicada"
    if getattr(dono, "contadores_especiais", {}).get(chave):
        return {}
    dono.contadores_especiais[chave] = True
    pctx = ctx_passiva_ataque(ctx, dono, "Fantasma")
    acu = aplicar_mod_atributo(pctx, dono, "Fantasma", "Acu", -parametro_passiva_ataque(ctx, "perda_acuracia", 25.0), negativo=True)
    amp = aplicar_mod_atributo(pctx, dono, "Fantasma", "Amp", -parametro_passiva_ataque(ctx, "perda_amp", 25.0), negativo=True)
    efeito_nome = parametro_str_execute(pctx, "efeito_permanente", "Furtivo")
    efeito = None
    if not dono.possui_efeito(efeito_nome):
        efeito = adicionar_efeito_formal_preservado(
            pctx,
            dono,
            {
                "nome": efeito_nome,
                "code": efeito_nome,
                "passos_restantes": -1,
                "passos_totais": -1,
                "dados": {"permanente": True},
                "valor": 0.0,
                "stacks": 1,
                "tipo": "positivo",
                "permanente": True,
            },
            origem=dono,
        )
    return {"passiva": "Fantasma", "acuracia": acu, "amp": amp, "furtivo": efeito, "aplicada_uma_vez": True}


def _exec_azar(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = parametro_execute(ctx, "perda_fixa_crc", 5.0) + usuario.obter_atributo("Mag") * parametro_execute(ctx, "mag_usuario_pct", 0.10)
    return aplicar_mod_atributo(ctx, alvo, "Azar", "CrC", -valor, negativo=True)


_EXECUTES = {
    "selararcano": _exec_selar_arcano,
    "desorientar": _exec_desorientar,
    "atravessar": _exec_atravessar,
    "lambida": _exec_lambida,
    "toquedomedo": _exec_toque_do_medo,
    "susto": _exec_susto,
    "maldade": _exec_maldade,
    "golpeespelhado": _exec_golpe_espelhado,
    "maoespectral": _exec_mao_espectral,
    "pulsodeplasma": _exec_pulso_de_plasma,
    "devoradordepecados": _exec_devorador_de_pecados,
    "maldicao": _exec_maldicao,
    "jogadadesorte": _exec_jogada_de_sorte,
    "ataquefantasmagorico": _exec_ataque_fantasmagorico,
    "sededesanguefantasma": _exec_sede_de_sangue_fantasma,
    "explosaofantasma": _exec_explosao_fantasma,
    "golpecruel": _exec_golpe_cruel,
    "fantasma": execute_passiva_nao_manual,
    "azar": _exec_azar,
}

_PASSIVAS_ATAQUE = [
    {"nome": "Fantasma", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_fantasma, "origem": "ataque", "code": "254"},
]

_ALIASES = {
    "237": "selararcano",
    "238": "desorientar",
    "239": "atravessar",
    "240": "lambida",
    "241": "toquedomedo",
    "242": "susto",
    "243": "maldade",
    "244": "golpeespelhado",
    "245": "maoespectral",
    "246": "pulsodeplasma",
    "247": "devoradordepecados",
    "248": "maldicao",
    "249": "jogadadesorte",
    "250": "ataquefantasmagorico",
    "251": "sededesanguefantasma",
    "252": "explosaofantasma",
    "253": "golpecruel",
    "254": "fantasma",
    "255": "azar",
    "ataquesededesanguefantasma": "sededesanguefantasma",
}


def obter_executes_fantasma():
    return dict(_EXECUTES)


def obter_passivas_ataques_fantasma():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_fantasma():
    return dict(_ALIASES)


