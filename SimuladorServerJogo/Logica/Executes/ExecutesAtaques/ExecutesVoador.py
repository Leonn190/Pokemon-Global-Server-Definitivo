from __future__ import annotations

import copy

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    area_selecionada_da_acao,
    dano_generico,
    execute_passiva_nao_manual,
    fnum,
    linha_ordenada_por_direcao,
    normalizar,
    pokemons_ativos_em_campo,
    resolver_critico_contextual,
)


def _params(ctx):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    return props.get("parametros") if isinstance(props.get("parametros"), dict) else {}


def _param(ctx, chave, default):
    return fnum(_params(ctx).get(chave), default)


def _param_str(ctx, chave, default):
    valor = _params(ctx).get(chave)
    return str(valor if valor not in (None, "") else default)


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


def _lado(pokemon):
    try:
        return int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        return -1


def _inimigos_ativos(ctx):
    usuario = (ctx or {}).get("usuario")
    return [p for p in pokemons_ativos_em_campo((ctx or {}).get("partida")) if usuario is not None and _lado(p) != _lado(usuario)]


def _area_lado(partida, area_id):
    area = (getattr(partida, "areas", {}) or {}).get(str(area_id or "").upper())
    try:
        return int((area or {}).get("lado_id"))
    except (TypeError, ValueError):
        return None


def _destino_movimento(ctx):
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
    area_alvo = area_selecionada_da_acao(ctx)
    return str(area_alvo or destino.get("area_id") or "").strip().upper()


def _destino_valido_mesmo_lado(ctx, pokemon, area_id):
    partida = (ctx or {}).get("partida")
    area_id = str(area_id or "").strip().upper()
    if partida is None or pokemon is None or not area_id:
        return False
    if not hasattr(partida, "area_existe") or not partida.area_existe(area_id):
        return False
    if _area_lado(partida, area_id) != _lado(pokemon):
        return False
    ocupante = partida.pokemon_na_area(area_id) if hasattr(partida, "pokemon_na_area") else None
    return ocupante is None


def _mover_para_destino(ctx, pokemon, area_id, ataque_nome):
    partida = (ctx or {}).get("partida")
    if not _destino_valido_mesmo_lado(ctx, pokemon, area_id):
        return {"falha": True, "motivo": "destino_invalido"}
    movido = partida.mover_pokemon_para_area(
        pokemon,
        area_id,
        dados={"origem": pokemon, "ataque": ataque_nome, "reativos_acao": (ctx or {}).get("reativos_acao")},
    )
    if not movido:
        return {"falha": True, "motivo": "movimento_falhou"}
    return {"aplicado": True, "moveu": True, "area_destino": area_id}


def _selecoes_area(ctx):
    acao = (ctx or {}).get("acao") if isinstance((ctx or {}).get("acao"), dict) else {}
    alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo.get("tipo") or "").strip().lower() == "multi":
        return [str(item.get("area_id") or "").strip().upper() for item in list(alvo.get("alvos") or []) if isinstance(item, dict) and item.get("area_id")]
    area_id = str(alvo.get("area_id") or "").strip().upper()
    return [area_id] if area_id else []


def _linha_area(ctx):
    usuario = (ctx or {}).get("usuario")
    area_id = area_selecionada_da_acao(ctx)
    return linha_ordenada_por_direcao(area_id, getattr(usuario, "lado_id", 50)) if area_id else []


def _efeito_temporario(efeito):
    if not isinstance(efeito, dict) or bool(efeito.get("permanente")):
        return False
    return int(fnum(efeito.get("passos_restantes"), 0.0)) >= 0


def _recalcular(pokemon):
    if pokemon is not None and hasattr(pokemon, "recalcular_atributos"):
        pokemon.recalcular_atributos()


def _adicionar_efeito_transferido(receptor, efeito):
    transferido = copy.deepcopy(efeito)
    transferido["permanente"] = False
    chave = normalizar(transferido.get("code") or transferido.get("nome"))
    existente = next(
        (
            e
            for e in list(getattr(receptor, "efeitos_formais", []) or [])
            if _efeito_temporario(e) and normalizar((e or {}).get("code") or (e or {}).get("nome")) == chave
        ),
        None,
    )
    if existente is None:
        receptor.efeitos_formais.append(transferido)
        return "anexado"
    existente["passos_restantes"] = max(0, int(fnum(existente.get("passos_restantes"), 0.0))) + max(0, int(fnum(transferido.get("passos_restantes"), 0.0)))
    existente["passos_totais"] = max(int(fnum(existente.get("passos_totais"), 0.0)), int(fnum(transferido.get("passos_totais"), 0.0)), existente["passos_restantes"])
    existente["stacks"] = max(1, int(fnum(existente.get("stacks"), 1.0))) + max(1, int(fnum(transferido.get("stacks"), 1.0)))
    existente["valor"] = transferido.get("valor", existente.get("valor", 0.0))
    existente["tipo"] = transferido.get("tipo", existente.get("tipo"))
    existente["dados"] = {**dict(existente.get("dados") or {}), **dict(transferido.get("dados") or {})}
    return "mesclado"


def _transferir_efeitos_temporarios(ctx, origem, receptor, motivo):
    if origem is None or receptor is None or origem is receptor:
        return []
    transferidos = []
    restantes = []
    for efeito in list(getattr(origem, "efeitos_formais", []) or []):
        if _efeito_temporario(efeito):
            modo = _adicionar_efeito_transferido(receptor, efeito)
            transferidos.append({"efeito": copy.deepcopy(efeito), "modo": modo})
        else:
            restantes.append(efeito)
    if not transferidos:
        return []
    origem.efeitos_formais = restantes
    _recalcular(origem)
    _recalcular(receptor)
    usuario = (ctx or {}).get("usuario")
    _registrar_log(
        ctx,
        "efeitos_transferidos",
        {
            "origem_id": getattr(origem, "id_batalha", None),
            "origem_nome": getattr(origem, "nome", None),
            "receptor_id": getattr(receptor, "id_batalha", None),
            "receptor_nome": getattr(receptor, "nome", None),
            "usuario_id": getattr(usuario, "id_batalha", None),
            "usuario_nome": getattr(usuario, "nome", None),
            "motivo": motivo,
            "quantidade": len(transferidos),
            "efeitos": [
                {
                    "nome": (item["efeito"] or {}).get("nome") or (item["efeito"] or {}).get("code"),
                    "passos_restantes": (item["efeito"] or {}).get("passos_restantes"),
                    "tipo": (item["efeito"] or {}).get("tipo"),
                    "modo": item.get("modo"),
                }
                for item in transferidos
            ],
            **_ataque_id_nome(ctx, motivo),
        },
    )
    return transferidos


def _remover_efeitos_temporarios(ctx, pokemon, motivo, somente_nome=None):
    if pokemon is None:
        return []
    alvo_nome = normalizar(somente_nome) if somente_nome else None
    removidos = []
    restantes = []
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        nome = normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
        if _efeito_temporario(efeito) and (alvo_nome is None or nome == alvo_nome):
            removidos.append(efeito)
        else:
            restantes.append(efeito)
    if not removidos:
        return []
    pokemon.efeitos_formais = restantes
    _recalcular(pokemon)
    for efeito in removidos:
        _registrar_log(
            ctx,
            "pokemon_removeu_efeito",
            {
                "pokemon_id": getattr(pokemon, "id_batalha", None),
                "pokemon_nome": getattr(pokemon, "nome", None),
                "efeito_nome": (efeito or {}).get("nome") or (efeito or {}).get("code"),
                "passos_removidos": max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0))),
                "motivo": motivo,
                **_ataque_id_nome(ctx, motivo),
            },
        )
    return removidos


def _calcular_acerto(ctx, usuario, alvo):
    parametros = _params(ctx)
    if alvo is not None and bool(parametros.get("sempre_acerta", False)):
        return {"acertou": True, "chance_final": 100.0, "chance_real": 100.0, "rolagem": None, "sempre_acerta": True, "bonus_critico_acerto": 0.0}
    acuracia_ataque = fnum(parametros.get("acuracia"), 100.0) / 100.0
    acuracia = (usuario.obter_atributo("Acu", 100.0) / 100.0) * acuracia_ataque
    assertividade = alvo.obter_atributo("Ass", 100.0) / 100.0
    chance = acuracia * assertividade
    vel_usuario = usuario.obter_atributo("Vel", 0.0)
    vel_alvo = alvo.obter_atributo("Vel", 0.0)
    media = (vel_usuario + vel_alvo) / 2.0
    escudo = 10.0
    if vel_usuario > media + escudo:
        chance += (vel_usuario - media - escudo) / 100.0
    elif vel_usuario < media - escudo:
        chance -= (media - escudo - vel_usuario) / 100.0
    if vel_alvo > media + escudo:
        chance -= (vel_alvo - media - escudo) / 100.0
    elif vel_alvo < media - escudo:
        chance += (media - escudo - vel_alvo) / 100.0
    tipo_ataque = parametros.get("tipo") or "voador"
    if alvo.possui_efeito("Flutuando") and str(tipo_ataque).strip().lower() == "normal":
        chance -= 0.40
    chance_percentual = max(0.0, chance * 100.0)
    chance_real = min(100.0, chance_percentual)
    rng = (ctx or {}).get("rng") or getattr((ctx or {}).get("partida"), "rng", None)
    sorte = rng.random() * 100.0 if rng is not None else 100.0
    return {
        "acertou": sorte <= chance_real,
        "chance_final": round(chance_percentual, 4),
        "chance_real": round(chance_real, 4),
        "bonus_critico_acerto": round(max(0.0, chance_percentual - 100.0) / 2.0, 4),
        "rolagem": round(sorte, 4),
    }


def _exec_voar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_status(ctx, usuario, _param_str(ctx, "efeito", "Voando"), negativo=False)


def _exec_olho_de_aguia(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag", 0.20)
    valor += usuario.obter_atributo("Acu") * _param(ctx, "percentual_acuracia", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Olho de Aguia", _param_str(ctx, "atributo", "Acuracia"), valor, negativo=False)


def _exec_ventinho(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    atingidos = []
    resultados = []
    for area_id in _linha_area(ctx):
        alvo_linha = partida.pokemon_na_area(area_id) if partida is not None else None
        if alvo_linha is None or not alvo_linha.esta_vivo() or _lado(alvo_linha) == _lado(usuario):
            continue
        ret = dano_generico(ctx, alvo_linha, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.30), "especial")
        resultados.append({"pokemon_id": alvo_linha.id_batalha, "area_id": area_id, "dano": ret})
        if ret.get("aplicado"):
            atingidos.append(alvo_linha)
    receptor = atingidos[-1] if atingidos else None
    transferencias = []
    if receptor is not None and receptor.esta_vivo():
        for origem in atingidos[:-1]:
            transferencias.extend(_transferir_efeitos_temporarios(ctx, origem, receptor, "Ventinho"))
    return {"aplicado": True, "alvos_atingidos": len(atingidos), "receptor_id": getattr(receptor, "id_batalha", None), "resultados": resultados, "efeitos_transferidos": len(transferencias)}


def _exec_voo_alto(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng") or getattr(ctx.get("partida"), "rng", None)
    rolagem = rng.random() * 100.0 if rng is not None else 100.0
    chance_erro = _param(ctx, "chance_erro_natural", 15.0)
    if rolagem < chance_erro:
        _registrar_log(ctx, "ataque_errou", {"usuario_id": getattr(usuario, "id_batalha", None), "usuario_nome": getattr(usuario, "nome", None), "motivo": "erro_natural", "rolagem": round(rolagem, 4), **_ataque_id_nome(ctx, "Voo Alto")})
        return {"falha": True, "motivo": "ataque_errou", "rolagem": round(rolagem, 4), "chance_erro_natural": chance_erro}
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="efeito")
    efeito_condicao = _param_str(ctx, "efeito_condicao", "Voando")
    efeito_ganho = _param_str(ctx, "efeito_ganho", "Evasivo")
    condicao = usuario.possui_efeito(efeito_condicao)
    efeito = None
    if condicao or critico_ctx.get("critico"):
        efeito = aplicar_status(ctx, usuario, efeito_ganho, negativo=False)
    return {"aplicado": True, "condicao_ativa": condicao, "critico_contextual": critico_ctx, "efeito": efeito}


def _exec_asas_protetoras(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Vel") * _param(ctx, "percentual_vel", 0.20)
    return {
        "aplicado": True,
        "vel": aplicar_mod_atributo(ctx, usuario, "Asas Protetoras", "Vel", -valor, negativo=True),
        "def": aplicar_mod_atributo(ctx, usuario, "Asas Protetoras", "Def", valor, negativo=False),
        "spd": aplicar_mod_atributo(ctx, usuario, "Asas Protetoras", "SpD", valor, negativo=False),
    }


def _exec_vendaval(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    linha = _linha_area(ctx)
    ultimo_fundo = linha[-1] if linha else None
    atingidos = []
    resultados = []
    for area_id in linha:
        alvo_linha = partida.pokemon_na_area(area_id) if partida is not None else None
        if alvo_linha is None or not alvo_linha.esta_vivo() or _lado(alvo_linha) == _lado(usuario):
            continue
        mult = 1.0 + _param(ctx, "bonus_dano_ultima_area", 0.35) if str(area_id).upper() == str(ultimo_fundo).upper() else 1.0
        ret = dano_generico(ctx, alvo_linha, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.65), "especial", multiplicadores_condicionais=[{"label": "Alvo na ultima area possivel", "multiplicador": mult}])
        resultados.append({"pokemon_id": alvo_linha.id_batalha, "area_id": area_id, "multiplicador": mult, "dano": ret})
        if ret.get("aplicado"):
            atingidos.append(alvo_linha)
    movimentos = []
    for pokemon in sorted([p for p in atingidos if p.esta_vivo()], key=lambda p: linha.index(getattr(p, "area_id", "")) if getattr(p, "area_id", "") in linha else -1, reverse=True):
        origem = getattr(pokemon, "area_id", None)
        destino = None
        for area_id in reversed(linha):
            if area_id == origem:
                break
            if partida.pokemon_na_area(area_id) is None:
                destino = area_id
                break
        if destino:
            moveu = partida.mover_pokemon_para_area(pokemon, destino, dados={"origem": usuario, "ataque": "Vendaval", "reativos_acao": ctx.get("reativos_acao")})
            movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": destino, "moveu": bool(moveu)})
        else:
            movimentos.append({"pokemon_id": pokemon.id_batalha, "area_origem": origem, "area_destino": origem, "moveu": False})
    return {"aplicado": True, "alvos_atingidos": len(atingidos), "resultados": resultados, "movimentos": movimentos}


def _exec_tornadinho_amigo(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is None or getattr(alvo, "id_batalha", None) == getattr(usuario, "id_batalha", None):
        return {"falha": True, "motivo": "alvo_usuario_nao_permitido"}
    return aplicar_status(ctx, alvo, _param_str(ctx, "efeito", "Voando"), negativo=False)


def _exec_voo_estrategico(ctx, alvo):
    usuario = ctx.get("usuario")
    area_destino = _destino_movimento(ctx)
    if not _destino_valido_mesmo_lado(ctx, usuario, area_destino):
        return {"falha": True, "motivo": "destino_invalido"}
    efeito = aplicar_status(ctx, usuario, _param_str(ctx, "efeito", "Voando"), negativo=False)
    movimento = _mover_para_destino(ctx, usuario, area_destino, "Voo Estrategico")
    if movimento.get("falha"):
        return movimento
    movimento["efeito"] = efeito
    return movimento


def _exec_impulso_aereo(ctx, alvo):
    return _mover_para_destino(ctx, ctx.get("usuario"), _destino_movimento(ctx), "Impulso Aereo")


def _exec_bico_broca(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.45)
    bruto += usuario.obter_atributo("Per") * _param(ctx, "mult_per", 2.00)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_golpe_de_asa(ctx, alvo):
    usuario = ctx.get("usuario")
    mult = _param(ctx, "mult_voando", 0.75) if usuario.possui_efeito(_param_str(ctx, "efeito_condicao", "Voando")) else 1.0
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.85), "normal", multiplicadores_condicionais=[{"label": "Usuario Voando", "multiplicador": mult}])


def _exec_ataque_aereo(ctx, alvo):
    usuario = ctx.get("usuario")
    multiplicadores = []
    if usuario.possui_efeito(_param_str(ctx, "efeito_usuario", "Voando")):
        multiplicadores.append({"label": "Usuario Voando", "multiplicador": 1.0 + _param(ctx, "bonus_usuario_voando", 0.30)})
    if alvo is not None and alvo.possui_efeito(_param_str(ctx, "efeito_alvo", "Voando")):
        multiplicadores.append({"label": "Alvo Voando", "multiplicador": 1.0 + _param(ctx, "bonus_alvo_voando", 0.30)})
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.80), "normal", multiplicadores_condicionais=multiplicadores)


def _exec_rasante(ctx, alvo):
    usuario = ctx.get("usuario")
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    acerto = _calcular_acerto(ctx, usuario, alvo)
    if not acerto.get("acertou"):
        _registrar_log(ctx, "ataque_errou", {"alvo_id": alvo.id_batalha, "alvo_nome": alvo.nome, "usuario_id": usuario.id_batalha, "usuario_nome": usuario.nome, "acerto": acerto, **_ataque_id_nome(ctx, "Rasante")})
        aplicar_status(ctx, usuario, _param_str(ctx, "efeito_erro", "Descarregado"), duracao=_param(ctx, "duracao_erro", 6), negativo=True)
        return {"falha": True, "motivo": "ataque_errou", "acerto": acerto}
    ctx = {**dict(ctx or {}), "bonus_critico_acerto": acerto.get("bonus_critico_acerto", 0.0)}
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.45)
    bruto += usuario.obter_atributo("Vel") * _param(ctx, "mult_vel", 0.60)
    ret = dano_generico(ctx, alvo, bruto, "normal")
    ret["acerto"] = acerto
    return ret


def _exec_as_dos_ares(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.55), "normal")
    if alvo is not None:
        removidos = _remover_efeitos_temporarios(ctx, alvo, "As dos Ares", somente_nome=_param_str(ctx, "efeito_removido", "Voando"))
        ret["voando_removido"] = len(removidos)
    return ret


def _exec_tornado(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    rng = ctx.get("rng") or getattr(partida, "rng", None)
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        ret = dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.60), "especial")
        item = {"pokemon_id": inimigo.id_batalha, "dano": ret, "movimento": None}
        if ret.get("aplicado") and inimigo.esta_vivo():
            areas = [
                area_id
                for area_id, area in (getattr(partida, "areas", {}) or {}).items()
                if int((area or {}).get("lado_id", -1)) == _lado(inimigo)
                and area_id != getattr(inimigo, "area_id", None)
                and partida.pokemon_na_area(area_id) is None
            ]
            if areas:
                destino = rng.choice(areas) if rng is not None else areas[0]
                origem = inimigo.area_id
                moveu = partida.mover_pokemon_para_area(inimigo, destino, dados={"origem": usuario, "ataque": "Tornado", "reativos_acao": ctx.get("reativos_acao")})
                item["movimento"] = {"area_origem": origem, "area_destino": destino, "moveu": bool(moveu)}
        resultados.append(item)
    return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_ciclone(ctx, alvo):
    usuario = ctx.get("usuario")
    resultados = []
    for inimigo in _inimigos_ativos(ctx):
        ret = dano_generico(ctx, inimigo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.65), "especial")
        removidos = _remover_efeitos_temporarios(ctx, inimigo, "Ciclone")
        resultados.append({"pokemon_id": inimigo.id_batalha, "dano": ret, "efeitos_removidos": len(removidos)})
    return {"aplicado": True, "alvos_atingidos": len(resultados), "resultados": resultados}


def _exec_tiro_de_penas(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    vistos = set()
    resultados = []
    for area_id in _selecoes_area(ctx)[: int(_param(ctx, "quantidade_areas", 5))]:
        if area_id in vistos:
            continue
        vistos.add(area_id)
        alvo_area = partida.pokemon_na_area(area_id) if partida is not None else None
        item = {"area_id": area_id, "pokemon_id": getattr(alvo_area, "id_batalha", None), "dano": None}
        if alvo_area is not None and alvo_area.esta_vivo():
            item["dano"] = dano_generico(ctx, alvo_area, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.35), "normal", area_alvo=area_id)
        resultados.append(item)
    return {"aplicado": True, "areas": len(resultados), "resultados": resultados}


def _exec_barragem_de_vento(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = max(0.0, usuario.obter_atributo("Mag") * _param(ctx, "percentual_mag", 0.18) + usuario.obter_atributo("Vel") * _param(ctx, "percentual_vel", 0.10))
    return usuario.AplicarBarreira(alvo, valor, dados={**_ataque_id_nome(ctx, "Barragem de Vento"), "ataque": "Barragem de Vento", "reativos_acao": ctx.get("reativos_acao")})


def _passiva_voador(ctx):
    return aplicar_passiva_permanente(ctx, "Voando")


_EXECUTES = {
    "voar": _exec_voar,
    "olhodeaguia": _exec_olho_de_aguia,
    "ventinho": _exec_ventinho,
    "vooalto": _exec_voo_alto,
    "asasprotetoras": _exec_asas_protetoras,
    "vendaval": _exec_vendaval,
    "tornadinhoamigo": _exec_tornadinho_amigo,
    "vooestrategico": _exec_voo_estrategico,
    "impulsoaereo": _exec_impulso_aereo,
    "bicobroca": _exec_bico_broca,
    "golpedeasa": _exec_golpe_de_asa,
    "ataqueaereo": _exec_ataque_aereo,
    "rasante": _exec_rasante,
    "asdosares": _exec_as_dos_ares,
    "tornado": _exec_tornado,
    "ciclone": _exec_ciclone,
    "tirodepenas": _exec_tiro_de_penas,
    "voador": execute_passiva_nao_manual,
    "barragemdevento": _exec_barragem_de_vento,
}

_PASSIVAS_ATAQUE = [
    {"nome": "Voador", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_voador, "origem": "ataque", "code": "190"},
]

_ALIASES = {
    "173": "voar",
    "174": "olhodeaguia",
    "175": "ventinho",
    "176": "vooalto",
    "177": "asasprotetoras",
    "178": "vendaval",
    "179": "tornadinhoamigo",
    "180": "vooestrategico",
    "181": "impulsoaereo",
    "182": "bicobroca",
    "183": "golpedeasa",
    "184": "ataqueaereo",
    "185": "rasante",
    "186": "asdosares",
    "187": "tornado",
    "188": "ciclone",
    "189": "tirodepenas",
    "190": "voador",
    "191": "barragemdevento",
}


def obter_executes_voador():
    return dict(_EXECUTES)


def obter_executes_reativos_voador():
    return []


def obter_passivas_ataques_voador():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_voador():
    return dict(_ALIASES)
