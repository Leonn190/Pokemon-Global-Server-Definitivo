from __future__ import annotations

import copy

from SimuladorServerJogo.Batalha.PropriedadesAtaques import carregar_propriedades_ataques
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    ATRIBUTOS_REGULARES,
    adjacentes_mesmo_lado,
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    dano_generico,
    execute_passiva_nao_manual,
    fnum,
    normalizar,
)


EFEITOS_NEGATIVOS_FORMAIS = {
    "queimado", "envenenado", "intoxicado", "congelado", "dormindo", "paralisado",
    "enraizado", "cauterizado", "descarregado", "encharcado", "atordoado",
    "quebrado", "enfraquecido", "confuso", "bloqueado", "amaldicoado",
}

_COORDS = {
    "A1": (0, 0), "A2": (0, 1), "A3": (0, 2),
    "A4": (1, 0), "A5": (1, 1), "A6": (1, 2),
    "A7": (2, 0), "A8": (2, 1), "A9": (2, 2),
    "I1": (0, 0), "I2": (0, 1), "I3": (0, 2),
    "I4": (1, 0), "I5": (1, 1), "I6": (1, 2),
    "I7": (2, 0), "I8": (2, 1), "I9": (2, 2),
}

def _param(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    if _esta_aprimorado(ctx):
        aprimoramento = parametros.get("aprimoramento") if isinstance(parametros.get("aprimoramento"), dict) else {}
        if chave in aprimoramento:
            return fnum(aprimoramento.get(chave), default)
    return fnum(parametros.get(chave), default)


def _param_lista(ctx, chave, default):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    valor = parametros.get(chave, default)
    return list(valor) if isinstance(valor, (list, tuple)) else list(default)


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


def _ataque_passivo_aprimorado(dono, code):
    for ataque in list(getattr(dono, "ataques", []) or []):
        if str((ataque or {}).get("Code") or (ataque or {}).get("ID") or "") != str(code):
            continue
        try:
            if int(float((ataque or {}).get("Nivel", (ataque or {}).get("nivel", 1)) or 1)) >= 2:
                return True
        except (TypeError, ValueError):
            pass
        return bool((ataque or {}).get("aprimorado") or (ataque or {}).get("Aprimorado"))
    return False


def _param_passiva(code, chave, default):
    props = carregar_propriedades_ataques().get(str(code))
    parametros = props.get("parametros") if isinstance(props, dict) and isinstance(props.get("parametros"), dict) else {}
    aprimoramento = parametros.get("aprimoramento") if isinstance(parametros.get("aprimoramento"), dict) else {}
    return fnum(aprimoramento.get(chave, parametros.get(chave, default)), default)


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


def _area_valida_mesmo_lado_vazia(partida, pokemon, area_id):
    area_id = str(area_id or "").upper()
    if partida is None or pokemon is None or not getattr(partida, "area_existe", lambda _: False)(area_id):
        return False
    try:
        mesmo_lado = int(_area_lado(partida, area_id)) == int(getattr(pokemon, "lado_id", -1))
    except (TypeError, ValueError):
        mesmo_lado = False
    if not mesmo_lado:
        return False
    ocupante = partida.pokemon_na_area(area_id)
    return ocupante is None or ocupante is pokemon


def _areas_vazias_mesmo_lado(partida, pokemon):
    if partida is None or pokemon is None:
        return []
    lado = int(getattr(pokemon, "lado_id", -1))
    saida = []
    for area_id, area in sorted((getattr(partida, "areas", {}) or {}).items()):
        try:
            if int((area or {}).get("lado_id")) != lado:
                continue
        except (TypeError, ValueError):
            continue
        if partida.pokemon_na_area(area_id) is None:
            saida.append(str(area_id).upper())
    return saida


def _mover_aleatorio_mesmo_lado(ctx, alvo):
    partida = (ctx or {}).get("partida")
    rng = (ctx or {}).get("rng") or getattr(partida, "rng", None)
    usuario = (ctx or {}).get("usuario")
    if alvo is None or not alvo.esta_vivo() or getattr(alvo, "reserva", False) or not getattr(alvo, "area_id", None):
        return {"aplicado": False, "motivo": "alvo_invalido_para_movimento"}
    if hasattr(alvo, "pode_ser_movido_por_ataque") and not alvo.pode_ser_movido_por_ataque():
        return {"aplicado": False, "motivo": "imparavel"}
    destinos = _areas_vazias_mesmo_lado(partida, alvo)
    if not destinos:
        return {"aplicado": False, "motivo": "sem_area_valida"}
    destino = rng.choice(destinos) if rng is not None else destinos[0]
    movido = partida.mover_pokemon_para_area(alvo, destino, dados={"origem": usuario, "ataque": "Lancamento", "reativos_acao": (ctx or {}).get("reativos_acao")})
    return {"aplicado": bool(movido), "area_destino": destino, "motivo": None if movido else "movimento_falhou"}


def _area_para_tras(alvo):
    area = str(getattr(alvo, "area_id", "") or "").upper()
    if area not in _COORDS:
        return None
    linha, coluna = _COORDS[area]
    prefixo = area[0]
    try:
        lado = int(getattr(alvo, "lado_id", -1))
    except (TypeError, ValueError):
        lado = -1
    nova_coluna = coluna - 1 if lado == 50 else coluna + 1
    if nova_coluna < 0 or nova_coluna > 2:
        return None
    return f"{prefixo}{linha * 3 + nova_coluna + 1}"


def _pode_mover_para_tras(ctx, alvo):
    partida = (ctx or {}).get("partida")
    if partida is None or alvo is None or not alvo.esta_vivo() or getattr(alvo, "reserva", False):
        return {"pode": False, "motivo": "alvo_invalido"}
    if hasattr(alvo, "pode_ser_movido_por_ataque") and not alvo.pode_ser_movido_por_ataque():
        return {"pode": False, "motivo": "imparavel"}
    destino = _area_para_tras(alvo)
    if not destino or not partida.area_existe(destino):
        return {"pode": False, "motivo": "sem_area_para_tras", "area_destino": destino}
    if partida.pokemon_na_area(destino) is not None:
        return {"pode": False, "motivo": "area_ocupada", "area_destino": destino}
    return {"pode": True, "area_destino": destino}


def _resolver_critico_pre_dano(usuario, ctx):
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    chance_bruta = fnum(usuario.obter_atributo("CrC", 0.0) if usuario is not None else 0.0, 0.0)
    chance_bruta += fnum((ctx or {}).get("bonus_critico_acerto"), 0.0)
    chance_bruta = min(chance_bruta, fnum(parametros.get("chance_critico_max", 999.0), 999.0))
    excedente = max(0.0, chance_bruta - 100.0)
    chance_real = max(0.0, min(100.0, chance_bruta))
    rng = (ctx or {}).get("rng") or getattr((ctx or {}).get("partida"), "rng", None)
    rolagem = rng.random() * 100.0 if rng is not None else 100.0
    cauterizado = usuario is not None and hasattr(usuario, "possui_efeito") and usuario.possui_efeito("Cauterizado")
    critico = bool((not cauterizado) and chance_real > 0 and rolagem <= chance_real)
    return {"critico": critico, "chance_critico": round(chance_real, 4), "excedente_critico": round(excedente, 4), "rolagem": round(rolagem, 4)}


def _efeito_negativo_formal(efeito):
    if not isinstance(efeito, dict):
        return False
    tipo = str(efeito.get("tipo") or "").strip().lower()
    nome = normalizar(efeito.get("nome") or efeito.get("code"))
    return tipo == "negativo" or bool(efeito.get("negativo")) or nome in EFEITOS_NEGATIVOS_FORMAIS


def _aliados_adjacentes(ctx, usuario):
    partida = (ctx or {}).get("partida")
    if partida is None or usuario is None or not getattr(usuario, "area_id", None):
        return []
    areas = set(adjacentes_mesmo_lado(usuario.area_id))
    aliados = []
    for area_id in areas:
        pokemon = partida.pokemon_na_area(area_id)
        if pokemon is None or pokemon is usuario or not pokemon.esta_vivo() or getattr(pokemon, "reserva", False) or not getattr(pokemon, "ativo", False):
            continue
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            aliados.append(pokemon)
    return aliados


def _areas_adjacentes(area_a, area_b):
    return str(area_b or "").upper() in set(adjacentes_mesmo_lado(area_a))


def _exec_grito_de_guerra(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * _param(ctx, "mult_mag_atk", 0.20)
    valor += usuario.obter_atributo("Atk") * _param(ctx, "mult_atk_atk", 0.10)
    return aplicar_mod_atributo(ctx, usuario, "Grito de Guerra", "Atk", valor, negativo=False)


def _passiva_implacavel(ctx):
    dono = (ctx or {}).get("dono_passiva") or (ctx or {}).get("pokemon_evento")
    ret = {"imparavel": aplicar_passiva_permanente(ctx, "Imparavel")}
    if _ataque_passivo_aprimorado(dono, "125"):
        ret["dur"] = aplicar_mod_atributo(ctx, dono, "Implacavel", "Dur", _param_passiva("125", "bonus_dur", 5.0), negativo=False)
    return ret


def _exec_soco(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.90), "normal")


def _exec_treinar(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng")
    atributos = _param_lista(ctx, "atributos_regulares", ATRIBUTOS_REGULARES)
    atributo = rng.choice(atributos) if rng is not None else atributos[0]
    bonus = usuario.obter_atributo(atributo) * _param(ctx, "percentual_bonus", 0.10)
    ret = aplicar_mod_atributo(ctx, usuario, "Treinar", atributo, bonus, negativo=False)
    critico = _resolver_critico_pre_dano(usuario, ctx)
    ret["critico_buff"] = critico
    if critico.get("critico"):
        ret["focado"] = aplicar_status(ctx, usuario, "Focado", negativo=False)
    return ret


def _exec_acrobacia(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    areas_aliadas = _areas_selecionadas(ctx, grupo=0)
    areas_inimigas = _areas_selecionadas(ctx, grupo=1)
    area_aliada = areas_aliadas[0] if areas_aliadas else None
    area_inimiga = areas_inimigas[0] if areas_inimigas else None
    if not _area_valida_mesmo_lado_vazia(partida, usuario, area_aliada):
        return {"falha": True, "motivo": "area_aliada_invalida"}
    if not partida.mover_pokemon_para_area(usuario, area_aliada, dados={"origem": usuario, "ataque": "Acrobacia", "reativos_acao": ctx.get("reativos_acao")}):
        return {"falha": True, "motivo": "movimento_falhou"}
    alvo_real = partida.pokemon_na_area(area_inimiga)
    if alvo_real is None or not alvo_real.esta_vivo() or int(getattr(alvo_real, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
        return {"falha": True, "motivo": "sem_alvo_real"}
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.65)
    bruto += usuario.obter_atributo("Vel") * _param(ctx, "mult_vel", 0.25)
    ret = dano_generico(ctx, alvo_real, bruto, "normal")
    ret["area_aliada"] = area_aliada
    ret["area_inimiga"] = area_inimiga
    return ret


def _exec_concentracao(ctx, alvo):
    usuario = ctx.get("usuario")
    antes = list(getattr(usuario, "efeitos_formais", []) or [])
    removidos = [copy.deepcopy(efeito) for efeito in antes if _efeito_negativo_formal(efeito)]
    usuario.efeitos_formais = [efeito for efeito in antes if not _efeito_negativo_formal(efeito)]
    if removidos and hasattr(usuario, "recalcular_atributos"):
        usuario.recalcular_atributos()
    for efeito in removidos:
        _registrar_log(ctx, "pokemon_removeu_efeito", {"pokemon_id": usuario.id_batalha, "pokemon_nome": usuario.nome, "efeito_nome": efeito.get("nome") or efeito.get("code"), "motivo": "Concentracao", **_ataque_id_nome(ctx, "Concentracao")})
    ret = {"aplicado": True, "efeitos_negativos_removidos": len(removidos), "focado": aplicar_status(ctx, usuario, "Focado", negativo=False)}
    energia = _param(ctx, "energia_aprimorado", 10.0) if _esta_aprimorado(ctx) else 0.0
    if energia > 0:
        ret["energia"] = usuario.GanharEnergia(energia, dados={**_ataque_id_nome(ctx, "Concentracao"), "motivo": "Concentracao", "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_lancamento(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.55), "normal")
    ret["movimento"] = _mover_aleatorio_mesmo_lado(ctx, alvo)
    return ret


def _exec_treino_em_grupo(ctx, alvo):
    usuario = ctx.get("usuario")
    rng = ctx.get("rng")
    adjacentes = _aliados_adjacentes(ctx, usuario)
    quantidade = len(adjacentes)
    if quantidade <= 0:
        return {"aplicado": True, "sem_beneficio": True, "aliados_adjacentes": 0}
    atributos = _param_lista(ctx, "atributos_regulares", ATRIBUTOS_REGULARES)
    percentual = _param(ctx, "percentual_por_aliado", 0.05) * quantidade
    resultados = []
    for beneficiado in [usuario, *adjacentes]:
        atributo = rng.choice(atributos) if rng is not None else atributos[0]
        bonus = beneficiado.obter_atributo(atributo) * percentual
        resultados.append({"pokemon_id": beneficiado.id_batalha, "atributo": atributo, "bonus": bonus, "resultado": aplicar_mod_atributo(ctx, beneficiado, "Treino em Grupo", atributo, bonus, negativo=False)})
    return {"aplicado": True, "aliados_adjacentes": quantidade, "beneficiados": resultados}


def _exec_karate(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.70)
    bruto += usuario.obter_atributo("CrC") * _param(ctx, "mult_crc", 0.40)
    extras = {}
    if usuario.possui_efeito("Focado"):
        extras["multiplicadores_condicionais"] = [{"label": "Usuario Focado", "multiplicador": _param(ctx, "mult_focado", 1.25)}]
    ret = dano_generico(ctx, alvo, bruto, "normal", **extras)
    if ret.get("critico") and hasattr(alvo, "receber_recuo"):
        ret["recuo"] = alvo.receber_recuo(origem=usuario, dados={**_ataque_id_nome(ctx, "Karate"), "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_soco_carregado(ctx, alvo):
    usuario = ctx.get("usuario")
    energia_atual = fnum(getattr(usuario, "EnergiaAtual", 0.0), 0.0)
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.55)
    bruto += energia_atual * _param(ctx, "mult_energia_atual", 0.45)
    critico = _resolver_critico_pre_dano(usuario, ctx)
    extras = {"bonus_critico_acerto": 0.0}
    movimento = {"aplicado": False, "motivo": "sem_critico"}
    if critico.get("critico"):
        movimento = _pode_mover_para_tras(ctx, alvo)
        # O critico foi rolado antes do dano para decidir o movimento; aqui forcamos o mesmo resultado no calculo central.
        extras["chance_critico"] = 100.0 + fnum(critico.get("excedente_critico"), 0.0)
        if not movimento.get("pode"):
            extras["multiplicadores_condicionais"] = [{"label": "Sem movimento para tras", "multiplicador": _param(ctx, "mult_sem_movimento", 1.25)}]
    else:
        extras["chance_critico"] = 0.0
    ret = dano_generico(ctx, alvo, bruto, "normal", **extras)
    ret["critico_pre_dano"] = critico
    ret["movimento_planejado"] = copy.deepcopy(movimento)
    if critico.get("critico"):
        recupera = fnum(ctx.get("custo_real"), 0.0) * _param(ctx, "percentual_recupera_critico", 0.25)
        ret["energia_recuperada"] = usuario.GanharEnergia(recupera, dados={**_ataque_id_nome(ctx, "Soco Carregado"), "motivo": "Soco Carregado", "reativos_acao": ctx.get("reativos_acao")})
        if movimento.get("pode") and alvo is not None and alvo.esta_vivo():
            movido = ctx.get("partida").mover_pokemon_para_area(alvo, movimento.get("area_destino"), dados={"origem": usuario, "ataque": "Soco Carregado", "reativos_acao": ctx.get("reativos_acao")})
            ret["movimento"] = {"aplicado": bool(movido), "area_destino": movimento.get("area_destino")}
        else:
            ret["movimento"] = movimento
    return ret


def _exec_socos_multiplos(ctx, alvo):
    usuario = ctx.get("usuario")
    hits = max(1, int(_param(ctx, "hits", 4)))
    resultados = []
    ultimo = {}
    for idx in range(hits):
        if alvo is None or not alvo.esta_vivo():
            break
        bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.22)
        bruto += usuario.obter_atributo("Ene") * _param(ctx, "mult_ene", 0.12)
        ultimo = dano_generico(ctx, alvo, bruto, "normal", indice_hit=idx + 1, hits=hits)
        resultados.append(ultimo)
    return {"aplicado": True, "hits_planejados": hits, "hits_aplicados": len(resultados), "resultados": resultados, "ultimo_retorno": ultimo}


def _exec_missil_de_punho(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.80), "especial")


def _exec_chamar_para_briga(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = {
        "provocando": aplicar_status(ctx, usuario, "Provocando", negativo=False),
        "preparado": aplicar_status(ctx, usuario, "Preparado", negativo=False),
    }
    energia = _param(ctx, "energia_aprimorado", 5.0) if _esta_aprimorado(ctx) else 0.0
    if energia > 0:
        ret["energia"] = usuario.GanharEnergia(energia, dados={**_ataque_id_nome(ctx, "Chamar para Briga"), "motivo": "Chamar para Briga", "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_chute_pirueta_aereo(ctx, alvo):
    usuario = ctx.get("usuario")
    extras = {}
    if alvo is not None and (alvo.possui_efeito("Flutuando") or alvo.possui_efeito("Voando")):
        extras["multiplicadores_condicionais"] = [{"label": "Alvo aereo", "multiplicador": _param(ctx, "mult_alvo_aereo", 1.40)}]
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.80), "normal", **extras)


def _exec_chute_duplo(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    areas = _areas_selecionadas(ctx)
    atingiveis = []
    vistos = set()
    for area_id in areas:
        ocupante = partida.pokemon_na_area(area_id) if partida is not None else None
        if ocupante is None or not ocupante.esta_vivo() or getattr(ocupante, "reserva", False):
            continue
        if int(getattr(ocupante, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        if ocupante.id_batalha in vistos:
            continue
        vistos.add(ocupante.id_batalha)
        atingiveis.append((area_id, ocupante))
    bonus = len(atingiveis) == 2 and _areas_adjacentes(atingiveis[0][0], atingiveis[1][0])
    resultados = []
    for area_id, alvo_real in atingiveis:
        extras = {}
        if bonus:
            extras["multiplicadores_condicionais"] = [{"label": "Alvos adjacentes", "multiplicador": _param(ctx, "mult_adjacentes", 1.25)}]
        bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.65)
        resultados.append({"area_id": area_id, "alvo_id": alvo_real.id_batalha, "dano": dano_generico(ctx, alvo_real, bruto, "normal", **extras)})
    return {"aplicado": True, "areas_selecionadas": areas, "alvos_atingidos": len(resultados), "bonus_adjacentes": bonus, "resultados": resultados}


def _exec_contra_ataque(ctx, alvo):
    usuario = ctx.get("usuario")
    historico = getattr(ctx.get("partida"), "historico_ataques_batalha", {}) or {}
    contra = historico.get("ultimo_contra_alvo") if isinstance(historico.get("ultimo_contra_alvo"), dict) else {}
    atacou_usuario = bool(alvo is not None and (getattr(alvo, "id_batalha", None), getattr(usuario, "id_batalha", None)) in contra)
    extras = {}
    if atacou_usuario:
        extras["multiplicadores_condicionais"] = [{"label": "Alvo ja atacou usuario", "multiplicador": _param(ctx, "mult_contra", 1.45)}]
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.70), "normal", **extras)
    ret["alvo_ja_atacou_usuario"] = atacou_usuario
    return ret


def _exec_submissao(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.85), "normal")
    if ret.get("critico"):
        ret["enfraquecido_alvo"] = aplicar_status(ctx, alvo, "Enfraquecido", negativo=True)
    else:
        ret["enfraquecido_usuario"] = aplicar_status(ctx, usuario, "Enfraquecido", negativo=True)
        ret["enfraquecido_alvo"] = aplicar_status(ctx, alvo, "Enfraquecido", negativo=True)
    return ret


_EXECUTES = {
    "gritodeguerra": _exec_grito_de_guerra,
    "implacavel": execute_passiva_nao_manual,
    "soco": _exec_soco,
    "treinar": _exec_treinar,
    "acrobacia": _exec_acrobacia,
    "concentracao": _exec_concentracao,
    "lancamento": _exec_lancamento,
    "treinoemgrupo": _exec_treino_em_grupo,
    "karate": _exec_karate,
    "sococarregado": _exec_soco_carregado,
    "socosmultiplos": _exec_socos_multiplos,
    "missildepunho": _exec_missil_de_punho,
    "chamarparabriga": _exec_chamar_para_briga,
    "chutepiruetaaereo": _exec_chute_pirueta_aereo,
    "chuteduplo": _exec_chute_duplo,
    "contraataque": _exec_contra_ataque,
    "submissao": _exec_submissao,
}

_PASSIVAS_ATAQUE = [
    {"nome": "Implacavel", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_implacavel, "origem": "ataque", "code": "125"},
]

_ALIASES = {
    "124": "gritodeguerra",
    "125": "implacavel",
    "126": "soco",
    "127": "treinar",
    "128": "acrobacia",
    "129": "concentracao",
    "130": "lancamento",
    "131": "treinoemgrupo",
    "132": "karate",
    "133": "sococarregado",
    "134": "socosmultiplos",
    "135": "missildepunho",
    "136": "chamarparabriga",
    "137": "chutepiruetaaereo",
    "138": "chuteduplo",
    "139": "contraataque",
    "140": "submissao",
}


def obter_executes_lutador():
    return dict(_EXECUTES)


def obter_passivas_ataques_lutador():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_lutador():
    return dict(_ALIASES)
