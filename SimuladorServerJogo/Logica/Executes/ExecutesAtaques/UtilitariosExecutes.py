from __future__ import annotations

import unicodedata


def normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def fnum(valor: object, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def resolver_critico_contextual(usuario, ctx, maximo=None, tipo="generico"):
    chance_bruta = float(usuario.obter_atributo("CrC", 0.0)) if usuario is not None else 0.0
    if maximo is not None:
        chance_bruta = min(chance_bruta, float(maximo))
    excedente = max(0.0, chance_bruta - 100.0)
    chance_real = max(0.0, min(100.0, chance_bruta))
    rng = (ctx or {}).get("rng") or getattr((ctx or {}).get("partida"), "rng", None)
    tem_rng = rng is not None
    rolagem = rng.random() * 100.0 if rng is not None else 100.0
    cauterizado = usuario is not None and hasattr(usuario, "possui_efeito") and usuario.possui_efeito("Cauterizado")
    return {
        "critico": bool((not cauterizado) and tem_rng and chance_real > 0 and rolagem <= chance_real),
        "chance_critico": round(chance_real, 4),
        "bonus_crd_excedente": round(excedente / 2.0, 4),
        "rolagem": round(rolagem, 4),
        "tipo": str(tipo or "generico"),
    }


def critico_simples(usuario, ctx, maximo=None):
    return bool(resolver_critico_contextual(usuario, ctx, maximo=maximo).get("critico"))


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


def aplicar_efeito(usuario, alvo, nome, duracao=3, dados=None, valor=0.0, negativo=None):
    efeito = {"nome": nome, "duracao": duracao, "valor": valor}
    if negativo is not None:
        efeito["negativo"] = bool(negativo)
    return usuario.AplicarEfeito(alvo, efeito, dados=dados or {})


_AREAS_BATALHA = {
    "A1": (0, 0), "A2": (0, 1), "A3": (0, 2),
    "A4": (1, 0), "A5": (1, 1), "A6": (1, 2),
    "A7": (2, 0), "A8": (2, 1), "A9": (2, 2),
    "I1": (0, 0), "I2": (0, 1), "I3": (0, 2),
    "I4": (1, 0), "I5": (1, 1), "I6": (1, 2),
    "I7": (2, 0), "I8": (2, 1), "I9": (2, 2),
}


def adjacentes_mesmo_lado(area_id):
    area = str(area_id or "").upper()
    if area not in _AREAS_BATALHA:
        return []
    prefixo = area[0]
    linha_base, coluna_base = _AREAS_BATALHA[area]
    saida = []
    for idx in range(1, 10):
        chave = f"{prefixo}{idx}"
        if chave == area or chave not in _AREAS_BATALHA:
            continue
        linha, coluna = _AREAS_BATALHA[chave]
        if abs(linha - linha_base) <= 1 and abs(coluna - coluna_base) <= 1:
            saida.append(chave)
    return saida


def linha_ordenada_por_direcao(area_id, lado_usuario):
    area = str(area_id or "").upper()
    if area not in _AREAS_BATALHA:
        return [area] if area else []
    prefixo = area[0]
    linha_base, _ = _AREAS_BATALHA[area]
    linha = [
        f"{prefixo}{idx}"
        for idx in range(1, 10)
        if f"{prefixo}{idx}" in _AREAS_BATALHA and _AREAS_BATALHA[f"{prefixo}{idx}"][0] == linha_base
    ]
    if int(lado_usuario) == 51:
        linha.sort(key=lambda item: _AREAS_BATALHA[item][1], reverse=True)
    else:
        linha.sort(key=lambda item: _AREAS_BATALHA[item][1])
    return linha


def inimigos_vivos_adjacentes_ao_alvo(ctx, alvo):
    return inimigos_vivos_adjacentes_area(ctx, getattr(alvo, "area_id", None), ignorar=alvo)


def area_alvo_contexto(ctx):
    alvo = (ctx or {}).get("acao", {}).get("alvo") if isinstance((ctx or {}).get("acao"), dict) else {}
    if not isinstance(alvo, dict):
        return None
    if str(alvo.get("tipo") or "").strip().lower() == "multi":
        for selecao in list(alvo.get("alvos") or []):
            if isinstance(selecao, dict) and selecao.get("area_id"):
                return str(selecao.get("area_id")).upper()
        return None
    return str(alvo.get("area_id") or "").upper() or None


def area_selecionada_da_acao(ctx):
    return area_alvo_contexto(ctx)


def obter_passos_efeito(pokemon, nome):
    alvo = normalizar(nome)
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        if normalizar((efeito or {}).get("nome") or (efeito or {}).get("code")) == alvo:
            return max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0)))
    return 0


def efeito_formal(pokemon, nome):
    alvo = normalizar(nome)
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        if normalizar((efeito or {}).get("nome") or (efeito or {}).get("code")) == alvo:
            return efeito
    return None


def remover_efeitos_contando_passos(pokemon, nomes, origem=None, dados=None):
    if pokemon is None:
        return {"removidos": 0, "passos": 0, "efeitos": []}
    alvos = {normalizar(nome) for nome in list(nomes or [])}
    removidos = []
    restantes = []
    passos = 0
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        nome_norm = normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
        if nome_norm in alvos:
            removidos.append(efeito)
            passos += max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0)))
        else:
            restantes.append(efeito)
    pokemon.efeitos_formais = restantes
    if removidos and hasattr(pokemon, "recalcular_atributos"):
        pokemon.recalcular_atributos()
    partida = getattr(pokemon, "partida", None)
    if removidos and partida is not None and hasattr(partida, "registrar_evento_log"):
        for efeito in removidos:
            partida.registrar_evento_log(
                "pokemon_removeu_efeito",
                {
                    "pokemon_id": getattr(pokemon, "id_batalha", None),
                    "pokemon_nome": getattr(pokemon, "nome", None),
                    "efeito_nome": (efeito or {}).get("nome") or (efeito or {}).get("code"),
                    "passos_removidos": max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0))),
                    "origem_id": getattr(origem, "id_batalha", None),
                    "origem_nome": getattr(origem, "nome", None),
                    **dict(dados or {}),
                },
            )
    return {"removidos": len(removidos), "passos": passos, "efeitos": removidos}


def pokemons_ativos_em_campo(partida, filtro_lado=None):
    if partida is None:
        return []
    saida = []
    for pokemon in list(getattr(partida, "pokemons_por_id", {}).values()):
        if pokemon is None or not pokemon.esta_vivo() or not getattr(pokemon, "ativo", False) or getattr(pokemon, "reserva", False):
            continue
        if filtro_lado is not None:
            try:
                if int(getattr(pokemon, "lado_id", -1)) != int(filtro_lado):
                    continue
            except (TypeError, ValueError):
                continue
        saida.append(pokemon)
    return saida


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


def inimigos_vivos_adjacentes_area(ctx, area_id, ignorar=None):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or area_id is None or usuario is None:
        return []
    saida = []
    for area_adjacente in adjacentes_mesmo_lado(area_id):
        pokemon = partida.pokemon_na_area(area_adjacente)
        if pokemon is None or pokemon is ignorar or not pokemon.esta_vivo():
            continue
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        saida.append(pokemon)
    return saida


def alvos_linha_inimigos(ctx, alvo_inicial):
    return alvos_linha_inimigos_area(ctx, getattr(alvo_inicial, "area_id", None), alvo_inicial=alvo_inicial)


def alvos_linha_inimigos_area(ctx, area_id, alvo_inicial=None):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or usuario is None or not area_id:
        return []
    linha = linha_ordenada_por_direcao(area_id, getattr(usuario, "lado_id", 50))
    if not linha:
        return [alvo_inicial] if alvo_inicial is not None else []
    try:
        idx_inicial = linha.index(str(area_id or "").upper())
    except ValueError:
        idx_inicial = 0
    saida = []
    for area_id in linha[idx_inicial:]:
        pokemon = partida.pokemon_na_area(area_id)
        if pokemon is None or not pokemon.esta_vivo():
            continue
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        saida.append(pokemon)
    return saida


def aplicar_status(ctx, alvo, nome, duracao=6, negativo=True):
    usuario = (ctx or {}).get("usuario")
    props = (ctx or {}).get("propriedades") or {}
    return aplicar_efeito(
        usuario,
        alvo,
        nome,
        duracao=duracao,
        negativo=negativo,
        dados={"origem_ataque": props.get("nome")},
    )


def aplicar_mod_atributo(ctx, alvo, nome_efeito, atributo, valor, duracao=6, negativo=False):
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    if not hasattr(alvo, "variacoes_permanentes"):
        return {"falha": True, "motivo": "alvo_sem_variacoes"}
    usuario = (ctx or {}).get("usuario")
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    valor = fnum(valor, 0.0)
    if hasattr(alvo, "modificar_atributo_permanente"):
        return alvo.modificar_atributo_permanente(
            alvo,
            atributo,
            valor,
            origem=usuario,
            dados={
                "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
                "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or nome_efeito,
                "positivo": valor >= 0,
                "negativo": bool(negativo) or valor < 0,
            },
        )
    antes = fnum(alvo.obter_atributo(atributo) if hasattr(alvo, "obter_atributo") else 0.0, 0.0)
    variacao_antes = fnum(alvo.variacoes_permanentes.get(atributo), 0.0)
    alvo.variacoes_permanentes[atributo] = fnum(alvo.variacoes_permanentes.get(atributo), 0.0) + valor
    if hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    depois = fnum(alvo.obter_atributo(atributo) if hasattr(alvo, "obter_atributo") else antes + valor, antes + valor)
    variacao_total = fnum(alvo.variacoes_permanentes.get(atributo), 0.0)
    calculo = [
        f"Valor inicial = {round(antes, 4)}",
        f"Variacao = {round(valor, 4)}",
        f"Valor final = {round(depois, 4)}",
    ]
    partida = (ctx or {}).get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(
            "pokemon_variou_atributo",
            {
                "pokemon_id": getattr(alvo, "id_batalha", None),
                "pokemon_nome": getattr(alvo, "nome", None),
                "alvo_id": getattr(alvo, "id_batalha", None),
                "alvo_nome": getattr(alvo, "nome", None),
                "origem_id": getattr(usuario, "id_batalha", None),
                "origem_nome": getattr(usuario, "nome", None),
                "usuario_id": getattr(usuario, "id_batalha", None),
                "usuario_nome": getattr(usuario, "nome", None),
                "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
                "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or nome_efeito,
                "atributo": atributo,
                "valor": round(valor, 4),
                "variacao": round(valor, 4),
                "valor_antes": round(antes, 4),
                "valor_depois": round(depois, 4),
                "variacao_antes": round(variacao_antes, 4),
                "variacao_total": round(variacao_total, 4),
                "positivo": valor >= 0,
                "negativo": bool(negativo) or valor < 0,
                "calculo": calculo,
            },
        )
    return {
        "aplicado": True,
        "variacao_permanente": True,
        "ataque": nome_efeito,
        "atributo": atributo,
        "valor": valor,
        "valor_total": alvo.variacoes_permanentes.get(atributo),
        "valor_antes": antes,
        "valor_depois": depois,
    }


def executar_bola(ctx, alvo, tipo):
    usuario = (ctx or {}).get("usuario")
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    escala_spa = fnum(parametros.get("escala_spa"), 0.80)
    splash_frac = fnum(parametros.get("splash_frac"), 0.50)
    if alvo is None:
        area_id = area_alvo_contexto(ctx)
        secundarios = inimigos_vivos_adjacentes_area(ctx, area_id)
        ultimo = {"aplicado": True, "area_alvo": area_id, "impacto_area_vazia": True, "alvos_secundarios": len(secundarios)}
        for adjacente in secundarios:
            ultimo = dano_generico(ctx, adjacente, usuario.obter_atributo("SpA") * escala_spa * splash_frac, "especial", tipo=tipo, impacto_secundario=True, area_alvo=area_id)
        return ultimo
    secundarios = inimigos_vivos_adjacentes_ao_alvo(ctx, alvo)
    alvo_principal_id = getattr(alvo, "id_batalha", None)
    secundarios_ids = [getattr(p, "id_batalha", None) for p in secundarios if p is not None]
    ret = dano_generico(
        ctx,
        alvo,
        usuario.obter_atributo("SpA") * escala_spa,
        "especial",
        tipo=tipo,
        alvo_principal_id=alvo_principal_id,
        alvos_secundarios_ids=secundarios_ids,
        impacto_principal=True,
    )
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida <= 0:
        return ret
    for adjacente in secundarios:
        dano_generico(
            ctx,
            adjacente,
                dano_vida * splash_frac,
            "especial",
            tipo=tipo,
            alvo_principal_id=alvo_principal_id,
            alvos_secundarios_ids=secundarios_ids,
            impacto_secundario=True,
        )
    return ret


def executar_raio(ctx, alvo, escala_inicial, reducao_spa, tipo, escala_sol_forte=None):
    usuario = (ctx or {}).get("usuario")
    partida = (ctx or {}).get("partida")
    spa = usuario.obter_atributo("SpA")
    base_padrao = spa * escala_inicial
    base = base_padrao
    multiplicadores = []
    if escala_sol_forte is not None and str(getattr(partida, "clima_atual", "")) == "Sol Forte":
        mult_clima = float(escala_sol_forte) / float(escala_inicial or 1.0)
        base = base_padrao * mult_clima
        multiplicadores.append({"label": "Multiplicador Condicional (Sol Forte)", "multiplicador": mult_clima})
    alvos_ctx = [a for a in list((ctx or {}).get("alvos") or []) if a is not None and a.esta_vivo()]
    if alvos_ctx and alvo is not None:
        idx = next((i for i, item in enumerate(alvos_ctx) if item is alvo), 0)
        reducao = spa * reducao_spa * idx
        ajustes = [{"label": "Reducao Condicional por alvo anterior", "valor": reducao, "op": "sub"}] if reducao > 0 else []
        return dano_generico(ctx, alvo, base_padrao, "especial", tipo=tipo, multiplicadores_condicionais=multiplicadores, ajustes_condicionais=ajustes)
    alvos = alvos_linha_inimigos(ctx, alvo) or ([alvo] if alvo is not None else [])
    ultimo = {}
    for idx, alvo_linha in enumerate(alvos):
        reducao = spa * reducao_spa * idx
        ajustes = [{"label": "Reducao Condicional por alvo anterior", "valor": reducao, "op": "sub"}] if reducao > 0 else []
        ultimo = dano_generico(ctx, alvo_linha, base_padrao, "especial", tipo=tipo, multiplicadores_condicionais=multiplicadores, ajustes_condicionais=ajustes)
    return ultimo


def executar_danca_clima(ctx, clima):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    if partida is None:
        return {"falha": True, "motivo": "partida_invalida"}
    if hasattr(partida, "mudar_clima"):
        return partida.mudar_clima(clima, origem=usuario, dados={"ataque_nome": props.get("nome")})
    antes = getattr(partida, "clima_atual", None)
    partida.clima_atual = clima
    if hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log("clima_mudou", {
            "clima_antes": antes,
            "clima_depois": clima,
            "usuario_id": getattr(usuario, "id_batalha", None),
            "usuario_nome": getattr(usuario, "nome", None),
            "ataque_nome": props.get("nome"),
        })
    if hasattr(partida, "disparar_flag"):
        partida.disparar_flag("AoMudarClima", {
            "partida": partida,
            "usuario": usuario,
            "pokemon_evento": usuario,
            "alvo": usuario,
            "clima_antes": antes,
            "clima_depois": clima,
        })
    return {"aplicado": True, "clima_antes": antes, "clima_depois": clima}


def execute_passiva_nao_manual(ctx, alvo):
    return {"falha": True, "motivo": "passiva_nao_manual"}


def aplicar_passiva_permanente(ctx, nome_efeito):
    alvo = (ctx or {}).get("dono_passiva") or (ctx or {}).get("pokemon_evento")
    if alvo is None:
        return {}
    efeito = {"nome": nome_efeito, "permanente": True, "dados": {"permanente": True}}
    return alvo.ReceberEfeito(efeito, origem=alvo, dados={"permanente": True})
