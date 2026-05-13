from __future__ import annotations

import copy

from SimuladorServerJogo.Batalha.PropriedadesAtaques import carregar_propriedades_ataques
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    dano_generico,
    execute_passiva_nao_manual,
    fnum,
    normalizar,
    resolver_critico_contextual,
)


EFEITOS_NEGATIVOS_FORMAIS = {
    "queimado", "envenenado", "intoxicado", "congelado", "dormindo", "paralisado",
    "enraizado", "cauterizado", "descarregado", "encharcado", "atordoado",
    "quebrado", "enfraquecido", "confuso", "bloqueado", "amaldicoado",
}


def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


def _param_passiva(code, chave, default):
    props = carregar_propriedades_ataques().get(str(code))
    parametros = props.get("parametros") if isinstance(props, dict) and isinstance(props.get("parametros"), dict) else {}
    return fnum(parametros.get(chave), default)


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


def _selecoes(ctx, grupo=None):
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo.get("tipo") or "").strip().lower() == "multi":
        itens = [item for item in list(alvo.get("alvos") or []) if isinstance(item, dict)]
    else:
        itens = [alvo] if alvo else []
    if grupo is None:
        return itens
    saida = []
    for item in itens:
        try:
            item_grupo = int(item.get("grupo", 0))
        except (TypeError, ValueError):
            item_grupo = 0
        if item_grupo == int(grupo):
            saida.append(item)
    return saida


def _areas_selecionadas(ctx, grupo=None):
    saida = []
    for selecao in _selecoes(ctx, grupo=grupo):
        area_id = str(selecao.get("area_id") or "").strip().upper()
        if area_id:
            saida.append(area_id)
    return saida


def _area_lado(partida, area_id):
    area = (getattr(partida, "areas", {}) or {}).get(str(area_id or "").upper())
    try:
        return int((area or {}).get("lado_id"))
    except (TypeError, ValueError):
        return None


def _efeito_negativo_formal(efeito):
    if not isinstance(efeito, dict):
        return False
    tipo = str(efeito.get("tipo") or "").strip().lower()
    nome = normalizar(efeito.get("nome") or efeito.get("code"))
    return tipo == "negativo" or bool(efeito.get("negativo")) or nome in EFEITOS_NEGATIVOS_FORMAIS


def _efeito_temporario(efeito):
    if not isinstance(efeito, dict) or bool(efeito.get("permanente")):
        return False
    return fnum(efeito.get("passos_restantes"), 0.0) > 0


def _efeitos_formais_por_tipo(pokemon, positivo=None, temporario=None):
    efeitos = []
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        if positivo is not None and _efeito_negativo_formal(efeito) == bool(positivo):
            continue
        if temporario is not None and _efeito_temporario(efeito) != bool(temporario):
            continue
        efeitos.append(efeito)
    return efeitos


def _remover_efeito_formal(ctx, pokemon, efeito, motivo):
    if pokemon is None or not isinstance(efeito, dict):
        return None
    alvo_norm = normalizar(efeito.get("nome") or efeito.get("code"))
    removido = None
    restantes = []
    for atual in list(getattr(pokemon, "efeitos_formais", []) or []):
        if removido is None and normalizar((atual or {}).get("nome") or (atual or {}).get("code")) == alvo_norm:
            removido = copy.deepcopy(atual)
            continue
        restantes.append(atual)
    if removido is None:
        return None
    pokemon.efeitos_formais = restantes
    if hasattr(pokemon, "recalcular_atributos"):
        pokemon.recalcular_atributos()
    _registrar_log(
        ctx,
        "pokemon_removeu_efeito",
        {
            "pokemon_id": getattr(pokemon, "id_batalha", None),
            "pokemon_nome": getattr(pokemon, "nome", None),
            "efeito_nome": removido.get("nome") or removido.get("code"),
            "motivo": motivo,
            **_ataque_id_nome(ctx, motivo),
        },
    )
    return removido


def _remover_efeitos_por_predicado(ctx, pokemon, predicado, motivo):
    removidos = []
    restantes = []
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        if predicado(efeito):
            removidos.append(copy.deepcopy(efeito))
        else:
            restantes.append(efeito)
    if not removidos:
        return []
    pokemon.efeitos_formais = restantes
    if hasattr(pokemon, "recalcular_atributos"):
        pokemon.recalcular_atributos()
    for efeito in removidos:
        _registrar_log(
            ctx,
            "pokemon_removeu_efeito",
            {
                "pokemon_id": getattr(pokemon, "id_batalha", None),
                "pokemon_nome": getattr(pokemon, "nome", None),
                "efeito_nome": efeito.get("nome") or efeito.get("code"),
                "motivo": motivo,
                **_ataque_id_nome(ctx, motivo),
            },
        )
    return removidos


def _escolher_efeito(ctx, efeitos):
    efeitos = list(efeitos or [])
    rng = (ctx or {}).get("rng")
    if not efeitos:
        return None
    return rng.choice(efeitos) if rng is not None else efeitos[0]


def _destino_pode_receber_efeito(destino, efeito):
    positivo = not _efeito_negativo_formal(efeito)
    if positivo and hasattr(destino, "possui_efeito") and destino.possui_efeito("Bloqueado"):
        return False, "bloqueado"
    if (not positivo) and hasattr(destino, "possui_efeito") and destino.possui_efeito("Imune"):
        return False, "imune"
    if _efeito_temporario(efeito):
        chave = normalizar(efeito.get("code") or efeito.get("nome"))
        temporarios = [e for e in list(getattr(destino, "efeitos_formais", []) or []) if not bool((e or {}).get("permanente"))]
        existe = any(normalizar((e or {}).get("code") or (e or {}).get("nome")) == chave for e in temporarios)
        if not existe and len(temporarios) >= 4:
            return False, "limite_efeitos_formais"
    return True, None


def _transferir_efeito_temporario(ctx, origem, destino, efeito, bonus_passos, motivo):
    if origem is None or destino is None or not _efeito_temporario(efeito):
        return {"aplicado": False, "motivo": "efeito_invalido"}
    pode, motivo_bloqueio = _destino_pode_receber_efeito(destino, efeito)
    if not pode:
        return {"aplicado": False, "motivo": motivo_bloqueio}
    chave = normalizar(efeito.get("code") or efeito.get("nome"))
    passos = max(1, int(fnum(efeito.get("passos_restantes"), 1.0))) + max(0, int(bonus_passos))
    destino_efeito = next((e for e in getattr(destino, "efeitos_formais", []) or [] if normalizar((e or {}).get("code") or (e or {}).get("nome")) == chave), None)
    if destino_efeito is not None and not bool(destino_efeito.get("permanente")):
        destino_efeito["passos_restantes"] = max(0, int(fnum(destino_efeito.get("passos_restantes"), 0.0))) + passos
        destino_efeito["passos_totais"] = max(int(fnum(destino_efeito.get("passos_totais"), 0.0)), int(fnum(destino_efeito.get("passos_restantes"), 0.0)))
        destino_efeito["tipo"] = "negativo" if _efeito_negativo_formal(efeito) else "positivo"
    else:
        destino_efeito = copy.deepcopy(efeito)
        destino_efeito["passos_restantes"] = passos
        destino_efeito["passos_totais"] = max(passos, int(fnum(destino_efeito.get("passos_totais"), passos)))
        destino_efeito["permanente"] = False
        destino_efeito["tipo"] = "negativo" if _efeito_negativo_formal(efeito) else "positivo"
        destino.efeitos_formais.append(destino_efeito)
    removido = _remover_efeito_formal(ctx, origem, efeito, motivo)
    if hasattr(destino, "recalcular_atributos"):
        destino.recalcular_atributos()
    _registrar_log(
        ctx,
        "efeito_transferido",
        {
            "origem_id": getattr(origem, "id_batalha", None),
            "origem_nome": getattr(origem, "nome", None),
            "destino_id": getattr(destino, "id_batalha", None),
            "destino_nome": getattr(destino, "nome", None),
            "efeito_nome": destino_efeito.get("nome") or destino_efeito.get("code"),
            "passos_restantes": destino_efeito.get("passos_restantes"),
            "bonus_passos": int(bonus_passos),
            **_ataque_id_nome(ctx, motivo),
        },
    )
    return {"aplicado": removido is not None, "efeito": copy.deepcopy(destino_efeito), "bonus_passos": int(bonus_passos)}


def executar_confusao(ctx, alvo):
    return aplicar_status(ctx, alvo, "Confuso", negativo=True)


def executar_teleporte(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    areas = _areas_selecionadas(ctx)
    destino = areas[0] if areas else None
    if partida is None or usuario is None or not destino or not partida.area_existe(destino):
        return {"falha": True, "motivo": "area_destino_invalida"}
    if _area_lado(partida, destino) != int(getattr(usuario, "lado_id", -1)):
        return {"falha": True, "motivo": "area_destino_invalida"}
    ocupante = partida.pokemon_na_area(destino)
    if ocupante is None:
        if not partida.mover_pokemon_para_area(usuario, destino, dados={"origem": usuario, "ataque": "Teleporte", "reativos_acao": ctx.get("reativos_acao")}):
            return {"falha": True, "motivo": "movimento_falhou"}
        resultado = {"aplicado": True, "area_destino": destino, "movimento": "moveu"}
    elif ocupante is usuario:
        resultado = {"aplicado": True, "area_destino": destino, "movimento": "mesma_area"}
    elif int(getattr(ocupante, "lado_id", -2)) == int(getattr(usuario, "lado_id", -1)):
        if not partida.trocar_posicao(usuario, ocupante, dados={"origem": usuario, "ataque": "Teleporte", "reativos_acao": ctx.get("reativos_acao")}):
            return {"falha": True, "motivo": "troca_posicao_falhou"}
        resultado = {"aplicado": True, "area_destino": destino, "movimento": "trocou", "ocupante_id": ocupante.id_batalha}
    else:
        return {"falha": True, "motivo": "area_destino_invalida"}
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="energia")
    resultado["critico_contextual"] = critico_ctx
    if critico_ctx.get("critico"):
        custo = fnum(ctx.get("custo_real"), _param(ctx, "custo", 25.0))
        ganho = custo * _param(ctx, "percentual_recupera_critico", 0.50)
        resultado["energia_recuperada"] = usuario.GanharEnergia(ganho, dados={**_ataque_id_nome(ctx, "Teleporte"), "motivo": "Teleporte", "reativos_acao": ctx.get("reativos_acao")})
    return resultado


def executar_toque_mental(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.75), "normal")
    if ret.get("critico") and alvo is not None:
        efeito = _escolher_efeito(ctx, _efeitos_formais_por_tipo(alvo, positivo=True, temporario=True))
        if efeito is not None:
            ret["efeito_removido"] = _remover_efeito_formal(ctx, alvo, efeito, "Toque Mental")
    return ret


def executar_cabecada_zen(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.85), "normal")
    if alvo is not None:
        ret["imune_removido"] = _remover_efeito_formal(ctx, alvo, {"nome": "Imune"}, "Cabeçada Zen")
    return ret


def executar_super_meditacao(ctx, alvo):
    usuario = ctx.get("usuario")
    removidos = _remover_efeitos_por_predicado(ctx, usuario, lambda efeito: _efeito_negativo_formal(efeito) and not bool((efeito or {}).get("permanente")), "Super Meditação")
    ganho = usuario.obter_atributo("Int") * _param(ctx, "percentual_int_energia", 0.20)
    return {
        "aplicado": True,
        "efeitos_negativos_removidos": len(removidos),
        "energia": usuario.GanharEnergia(ganho, dados={**_ataque_id_nome(ctx, "Super Meditação"), "motivo": "Super Meditação", "reativos_acao": ctx.get("reativos_acao")}),
    }


def executar_disturbio(ctx, alvo):
    usuario = ctx.get("usuario")
    removidos = _remover_efeitos_por_predicado(ctx, usuario, lambda efeito: (not _efeito_negativo_formal(efeito)) and not bool((efeito or {}).get("permanente")), "Distúrbio")
    extra = min(len(removidos) * _param(ctx, "bonus_por_efeito", 0.20), _param(ctx, "bonus_maximo", 0.80))
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.65) * (1.0 + extra)
    ret = dano_generico(ctx, alvo, bruto, "especial")
    ret["efeitos_positivos_removidos"] = len(removidos)
    ret["bonus_disturbio"] = round(extra, 4)
    return ret


def executar_protecao_mental(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario.possui_efeito("Imune"):
        usuario.adicionar_estado_transitorio("protegido", {"passo": ctx.get("passo"), "ataque": "Proteção Mental"})
        ret = {"aplicado": True, "estado": "protegido"}
        energia_extra = _param(ctx, "energia_se_imune", 0.0)
        if energia_extra > 0:
            ret["energia"] = usuario.GanharEnergia(energia_extra, dados={**_ataque_id_nome(ctx, "Proteção Mental"), "motivo": "Proteção Mental", "reativos_acao": ctx.get("reativos_acao")})
        return ret
    return aplicar_status(ctx, usuario, "Imune", duracao=int(_param(ctx, "duracao_imune", 6)), negativo=False)


def executar_teletransporte(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    origem = (_areas_selecionadas(ctx, grupo=0) or [None])[0]
    destino = (_areas_selecionadas(ctx, grupo=1) or [None])[0]
    if partida is None or not origem or not destino or not partida.area_existe(origem) or not partida.area_existe(destino):
        return {"falha": True, "motivo": "area_invalida"}
    lado_origem = _area_lado(partida, origem)
    lado_destino = _area_lado(partida, destino)
    if lado_origem is None or lado_destino is None or lado_origem != lado_destino:
        return {"falha": True, "motivo": "areas_de_lados_diferentes"}
    pokemon_origem = partida.pokemon_na_area(origem)
    if pokemon_origem is None or not pokemon_origem.esta_vivo() or getattr(pokemon_origem, "reserva", False) or not getattr(pokemon_origem, "ativo", False):
        return {"falha": True, "motivo": "origem_sem_pokemon_ativo"}
    pokemon_destino = partida.pokemon_na_area(destino)
    if pokemon_destino is not None and (not pokemon_destino.esta_vivo() or getattr(pokemon_destino, "reserva", False) or not getattr(pokemon_destino, "ativo", False)):
        return {"falha": True, "motivo": "destino_ocupado_invalido"}
    dados = {"origem": usuario, "ataque": "Teletransporte", "reativos_acao": ctx.get("reativos_acao")}
    if pokemon_destino is None:
        movido = partida.mover_pokemon_para_area(pokemon_origem, destino, dados=dados)
        return {"aplicado": bool(movido), "movimento": "moveu", "area_origem": origem, "area_destino": destino} if movido else {"falha": True, "motivo": "movimento_falhou"}
    trocou = partida.trocar_posicao(pokemon_origem, pokemon_destino, dados=dados)
    return {"aplicado": bool(trocou), "movimento": "trocou", "area_origem": origem, "area_destino": destino} if trocou else {"falha": True, "motivo": "troca_posicao_falhou"}


def executar_transferencia_mental(ctx, alvo):
    aliado = (_areas_selecionadas(ctx, grupo=0) or [None])[0]
    inimigo = (_areas_selecionadas(ctx, grupo=1) or [None])[0]
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    aliado_pokemon = partida.pokemon_na_area(aliado) if partida is not None and aliado else None
    inimigo_pokemon = partida.pokemon_na_area(inimigo) if partida is not None and inimigo else None
    if aliado_pokemon is None or inimigo_pokemon is None:
        return {"falha": True, "motivo": "alvos_invalidos"}
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="transferencia")
    bonus = int(_param(ctx, "bonus_passos_critico", 2) if critico_ctx.get("critico") else _param(ctx, "bonus_passos", 1))
    positivo_inimigo = _escolher_efeito(ctx, _efeitos_formais_por_tipo(inimigo_pokemon, positivo=True, temporario=True))
    negativo_aliado = _escolher_efeito(ctx, _efeitos_formais_por_tipo(aliado_pokemon, positivo=False, temporario=True))
    return {
        "aplicado": True,
        "critico_contextual": critico_ctx,
        "bonus_passos": bonus,
        "positivo_para_aliado": _transferir_efeito_temporario(ctx, inimigo_pokemon, aliado_pokemon, positivo_inimigo, bonus, "Transferência Mental") if positivo_inimigo is not None else {"aplicado": False, "motivo": "sem_positivo_no_inimigo"},
        "negativo_para_inimigo": _transferir_efeito_temporario(ctx, aliado_pokemon, inimigo_pokemon, negativo_aliado, bonus, "Transferência Mental") if negativo_aliado is not None else {"aplicado": False, "motivo": "sem_negativo_no_aliado"},
    }


def executar_ataque_psicologico(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.35)
    bruto += usuario.obter_atributo("Int") * _param(ctx, "mult_int", 0.90)
    return dano_generico(ctx, alvo, bruto, "especial")


def executar_ultrapsiquico(ctx, alvo):
    usuario = ctx.get("usuario")
    total_passos = sum(max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0))) for efeito in list(getattr(alvo, "efeitos_formais", []) or []) if _efeito_temporario(efeito))
    passos_considerados = min(total_passos, int(_param(ctx, "limite_passos", 25)))
    bruto = usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.60)
    bruto += usuario.obter_atributo("SpA") * _param(ctx, "bonus_spa_por_passo", 0.03) * passos_considerados
    ret = dano_generico(ctx, alvo, bruto, "especial")
    ret["passos_efeitos_alvo"] = total_passos
    ret["passos_considerados"] = passos_considerados
    return ret


def executar_instinto(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag", 0.20)
    valor += usuario.obter_atributo("Int") * _param(ctx, "percentual_int", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Instinto", "Int", valor, negativo=False)


def executar_raio_psiquico(ctx, alvo):
    usuario = ctx.get("usuario")
    estado = ctx.setdefault("estado_execucao_ataque", {})
    acertos_anteriores = int(fnum(estado.get("raio_psiquico_acertos"), 0.0))
    spa = usuario.obter_atributo("SpA")
    bruto = max(0.0, spa * _param(ctx, "escala_inicial_spa", 1.0) - spa * _param(ctx, "reducao_spa_por_alvo", 0.15) * acertos_anteriores)
    estado["raio_psiquico_acertos"] = acertos_anteriores + 1
    ret = dano_generico(ctx, alvo, bruto, "especial")
    ret["indice_alvo_linha"] = acertos_anteriores + 1
    return ret


def executar_barragem_mental(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag", 0.18)
    valor += usuario.obter_atributo("Int") * _param(ctx, "percentual_int", 0.10)
    dados = {
        **_ataque_id_nome(ctx, "Barragem Mental"),
        "ataque": "Barragem Mental",
        "reativos_acao": ctx.get("reativos_acao"),
        "calculo": [
            f"Mag * percentual_mag = {round(usuario.obter_atributo('Mag'), 4)} * {round(_param(ctx, 'percentual_mag', 0.18), 4)}",
            f"Int * percentual_int = {round(usuario.obter_atributo('Int'), 4)} * {round(_param(ctx, 'percentual_int', 0.10), 4)}",
            f"Barreira final = {round(valor, 4)}",
        ],
    }
    return usuario.AplicarBarreira(alvo, valor, dados=dados)


def _passiva_olho_que_tudo_ve(ctx):
    dono = (ctx or {}).get("dono_passiva") or (ctx or {}).get("pokemon_evento")
    partida = (ctx or {}).get("partida")
    if dono is None or partida is None:
        return {}
    visibilidade = getattr(partida, "visibilidade_furtivo_por_lado", None)
    if not isinstance(visibilidade, dict):
        visibilidade = {}
        partida.visibilidade_furtivo_por_lado = visibilidade
    visibilidade[int(getattr(dono, "lado_id", -1))] = True
    return {"olho_que_tudo_ve": True, "lado_id": int(getattr(dono, "lado_id", -1))}


def _passiva_turbomente(ctx):
    dono = (ctx or {}).get("dono_passiva") or (ctx or {}).get("pokemon_evento")
    if dono is None:
        return {}
    chave = "passiva_turbomente_aplicada"
    if bool(getattr(dono, "contadores_especiais", {}).get(chave)):
        return {}
    dono.contadores_especiais[chave] = 1
    valor = dono.obter_atributo("Int") * _param_passiva("200", "percentual_int_amp", 0.15)
    return aplicar_mod_atributo(ctx, dono, "Turbomente", "Amp", valor, negativo=False)


_EXECUTES = {
    "confusao": executar_confusao,
    "executarconfusao": executar_confusao,
    "teleporte": executar_teleporte,
    "executarteleporte": executar_teleporte,
    "olhoquetudove": execute_passiva_nao_manual,
    "executarolhoquetudove": execute_passiva_nao_manual,
    "toquemental": executar_toque_mental,
    "executartoquemental": executar_toque_mental,
    "cabecadazen": executar_cabecada_zen,
    "executarcabecadazen": executar_cabecada_zen,
    "supermeditacao": executar_super_meditacao,
    "executarsupermeditacao": executar_super_meditacao,
    "disturbio": executar_disturbio,
    "executardisturbio": executar_disturbio,
    "protecaomental": executar_protecao_mental,
    "executarprotecaomental": executar_protecao_mental,
    "turbomente": execute_passiva_nao_manual,
    "executarturbomente": execute_passiva_nao_manual,
    "teletransporte": executar_teletransporte,
    "executarteletransporte": executar_teletransporte,
    "transferenciamental": executar_transferencia_mental,
    "executartransferenciamental": executar_transferencia_mental,
    "ataquepsicologico": executar_ataque_psicologico,
    "executarataquepsicologico": executar_ataque_psicologico,
    "ultrapsiquico": executar_ultrapsiquico,
    "executarultrapsiquico": executar_ultrapsiquico,
    "instinto": executar_instinto,
    "executarinstinto": executar_instinto,
    "raiopsiquico": executar_raio_psiquico,
    "executarraiopsiquico": executar_raio_psiquico,
    "barragemmental": executar_barragem_mental,
    "executarbarragemmental": executar_barragem_mental,
}

_PASSIVAS_ATAQUE = [
    {"nome": "Olho Que Tudo Vê", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_olho_que_tudo_ve, "origem": "ataque", "code": "194"},
    {"nome": "Turbomente", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_turbomente, "origem": "ataque", "code": "200"},
]

_ALIASES = {
    "192": "confusao",
    "193": "teleporte",
    "194": "olhoquetudove",
    "195": "toquemental",
    "196": "cabecadazen",
    "197": "supermeditacao",
    "198": "disturbio",
    "199": "protecaomental",
    "200": "turbomente",
    "201": "teletransporte",
    "202": "transferenciamental",
    "203": "ataquepsicologico",
    "204": "ultrapsiquico",
    "205": "instinto",
    "206": "raiopsiquico",
    "207": "barragemmental",
}


def obter_executes_psiquicos():
    return dict(_EXECUTES)


def obter_passivas_ataques_psiquicas():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_psiquicos():
    return dict(_ALIASES)
