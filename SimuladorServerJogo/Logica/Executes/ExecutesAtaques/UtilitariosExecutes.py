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


def critico_simples(usuario, ctx, maximo=None):
    chance = float(usuario.obter_atributo("CrC", 0.0))
    if maximo is not None:
        chance = min(chance, float(maximo))
    rng = (ctx or {}).get("rng")
    return bool(chance > 0 and rng is not None and rng.random() * 100.0 <= chance)


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
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or alvo is None or usuario is None:
        return []
    saida = []
    for area_id in adjacentes_mesmo_lado(getattr(alvo, "area_id", None)):
        pokemon = partida.pokemon_na_area(area_id)
        if pokemon is None or pokemon is alvo or not pokemon.esta_vivo():
            continue
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        saida.append(pokemon)
    return saida


def alvos_linha_inimigos(ctx, alvo_inicial):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    if partida is None or usuario is None or alvo_inicial is None:
        return []
    linha = linha_ordenada_por_direcao(getattr(alvo_inicial, "area_id", None), getattr(usuario, "lado_id", 50))
    if not linha:
        return [alvo_inicial] if alvo_inicial is not None else []
    try:
        idx_inicial = linha.index(str(getattr(alvo_inicial, "area_id", "")).upper())
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
    valor = fnum(valor, 0.0)
    alvo.variacoes_permanentes[atributo] = fnum(alvo.variacoes_permanentes.get(atributo), 0.0) + valor
    if hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    return {
        "aplicado": True,
        "variacao_permanente": True,
        "ataque": nome_efeito,
        "atributo": atributo,
        "valor": valor,
        "valor_total": alvo.variacoes_permanentes.get(atributo),
    }


def executar_bola(ctx, alvo, tipo):
    usuario = (ctx or {}).get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * 1.05, "especial", tipo=tipo)
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida <= 0:
        return ret
    for adjacente in inimigos_vivos_adjacentes_ao_alvo(ctx, alvo):
        dano_generico(ctx, adjacente, dano_vida * 0.5, "especial", tipo=tipo)
    return ret


def executar_raio(ctx, alvo, escala_inicial, reducao_spa, tipo, escala_sol_forte=None):
    usuario = (ctx or {}).get("usuario")
    partida = (ctx or {}).get("partida")
    spa = usuario.obter_atributo("SpA")
    base = spa * escala_inicial
    if escala_sol_forte is not None and str(getattr(partida, "clima_atual", "")) == "Sol Forte":
        base = spa * escala_sol_forte
    alvos_ctx = [a for a in list((ctx or {}).get("alvos") or []) if a is not None and a.esta_vivo()]
    if alvos_ctx and alvo is not None:
        idx = next((i for i, item in enumerate(alvos_ctx) if item is alvo), 0)
        bruto = max(0.0, base - (spa * reducao_spa * idx))
        return dano_generico(ctx, alvo, bruto, "especial", tipo=tipo)
    alvos = alvos_linha_inimigos(ctx, alvo) or ([alvo] if alvo is not None else [])
    ultimo = {}
    for idx, alvo_linha in enumerate(alvos):
        bruto = max(0.0, base - (spa * reducao_spa * idx))
        ultimo = dano_generico(ctx, alvo_linha, bruto, "especial", tipo=tipo)
    return ultimo


def executar_danca_clima(ctx, clima):
    partida = (ctx or {}).get("partida")
    usuario = (ctx or {}).get("usuario")
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    if partida is None:
        return {"falha": True, "motivo": "partida_invalida"}
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
