from __future__ import annotations

import copy
import math

from Servidor.Batalha.ResolvedorFlags import ExecuteReativo
from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_efeito,
    aplicar_mod_atributo,
    dano_generico,
    execute_passiva_nao_manual,
    fnum,
    inimigos_vivos_adjacentes_ao_alvo,
    normalizar,
    resolver_critico_contextual,
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


def _peso(pokemon):
    dados = getattr(pokemon, "dados_originais", {}) if pokemon is not None else {}
    for chave in ("Peso", "peso", "PesoKg", "peso_kg", "weight"):
        if isinstance(dados, dict) and chave in dados:
            return fnum(dados.get(chave), 0.0)
    return fnum(getattr(pokemon, "Peso", getattr(pokemon, "peso", 0.0)), 0.0)


def _exec_investida(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.90), "normal")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida > 0:
        usuario.ReceberDano(
            dano_vida * _param(ctx, "percentual_recuo", 0.20),
            origem=usuario,
            dados={"recuo": "Investida", "ignorar_defensivos": True, "reativos_acao": ctx.get("reativos_acao")},
        )
    return ret


def _exec_biscoito(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    stacks = int(fnum(alvo.contadores_especiais.get("Biscoito"), 0.0))
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="cura")
    critico = bool(critico_ctx.get("critico"))
    mag = usuario.obter_atributo("Mag")
    cura_base = mag * _param(ctx, "percentual_cura", 0.50)
    valor_stack = mag * (_param(ctx, "percentual_stack_critico", 0.15) if critico else _param(ctx, "percentual_stack", 0.10))
    ret = usuario.AplicarCura(
        alvo,
        cura_base,
        dados={
            **_ataque_id_nome(ctx, "Biscoito"),
            "ataque": "Biscoito",
            "critico": critico,
            "critico_contextual": critico_ctx,
            "reativos_acao": ctx.get("reativos_acao"),
            "ajustes_condicionais": [
                {"label": "Stacks de Biscoito", "valor": stacks * valor_stack, "op": "add"}
            ],
        },
    )
    alvo.contadores_especiais["Biscoito"] = stacks + 1
    usuario.contadores_especiais["Biscoito"] = int(fnum(usuario.contadores_especiais.get("Biscoito"), 0.0)) + 1
    return ret


def _exec_enraivecer(ctx, alvo):
    usuario = ctx.get("usuario")
    vida_max = max(1.0, usuario.obter_atributo("Vida", 1.0))
    if usuario.VidaAtual / vida_max < _param(ctx, "limite_vida", 0.40):
        return aplicar_efeito(usuario, usuario, "Amplificado", duracao=3, negativo=False)
    return {"aplicado": True, "sem_efeito": True}


def _exec_provocar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_efeito(usuario, usuario, "Provocando", duracao=3, negativo=False)


def _exec_proteger(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    alvo.adicionar_estado_transitorio("protegido", {"passo": ctx.get("passo"), "ataque": "Proteger"})
    return {"aplicado": True, "estado": "protegido"}


def _exec_arranhar(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 1.00), "normal")


def _exec_recarga(ctx, alvo):
    usuario = ctx.get("usuario")
    ganho = fnum(ctx.get("custo_real"), 0.0) * _param(ctx, "multiplicador_custo_real", 1.50)
    return usuario.GanharEnergia(ganho, dados={"ataque": "Recarga", "motivo": "Recarga", "reativos_acao": ctx.get("reativos_acao")})


def _exec_energia(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * _param(ctx, "mult_spa", 0.85), "especial")


def _exec_hiper_raio(ctx, alvo):
    usuario = ctx.get("usuario")
    estado = ctx.setdefault("estado_execucao_ataque", {})
    acertos_anteriores = int(fnum(estado.get("hiper_raio_acertos"), 0.0))
    spa = usuario.obter_atributo("SpA")
    bruto = max(0.0, spa * _param(ctx, "mult_spa", 1.20) - spa * _param(ctx, "reducao_por_alvo", 0.20) * acertos_anteriores)
    estado["hiper_raio_acertos"] = acertos_anteriores + 1
    return dano_generico(ctx, alvo, bruto, "especial")


def _exec_guilhotina(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.60), "normal")


def _reativo_guilhotina(ctx):
    resultado = ctx.get("resultado") if isinstance(ctx.get("resultado"), dict) else {}
    if not bool(resultado.get("critico")):
        return {}
    usuario = ctx.get("usuario")
    alvo = ctx.get("alvo")
    if usuario is None or alvo is None or not alvo.esta_vivo() or int(alvo.lado_id) == int(usuario.lado_id):
        return {}
    if alvo.VidaAtual >= alvo.obter_atributo("Vida", 1.0) * 0.30:
        return {}
    ativou = alvo.Morrer({"origem_id": usuario.id_batalha, "ataque": "Guilhotina", "ataque_nome": "Guilhotina", "reativos_acao": ctx.get("reativos_acao")})
    return {"execucao_guilhotina": bool(ativou), "limite_vida": 0.30} if ativou else {}


def _exec_disparo(ctx, alvo):
    usuario = ctx.get("usuario")
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.75), "normal")


def _exec_chifrada(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.70)
    bruto += usuario.obter_atributo("Per") * _param(ctx, "mult_per", 0.30)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_golpe_precavido(ctx, alvo):
    usuario = ctx.get("usuario")
    estado = ctx.setdefault("estado_execucao_ataque", {})
    acertos_anteriores = int(fnum(estado.get("golpe_precavido_acertos"), 0.0))
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.80) * (0.5 ** acertos_anteriores)
    estado["golpe_precavido_acertos"] = acertos_anteriores + 1
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_pancada_seca(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.65), "normal")
    if alvo is None or not ret.get("aplicado") or ret.get("protegido"):
        return ret
    perda = max(0.0, usuario.obter_atributo("Ene") * _param(ctx, "percentual_ene_usuario", 0.25))
    antes = fnum(getattr(alvo, "EnergiaAtual", 0.0), 0.0)
    alvo.EnergiaAtual = max(0.0, antes - perda)
    real = max(0.0, antes - alvo.EnergiaAtual)
    partida = ctx.get("partida")
    if real > 0 and partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(
            "pokemon_perdeu_energia",
            {
                "pokemon_id": alvo.id_batalha,
                "pokemon_nome": alvo.nome,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "origem_id": usuario.id_batalha,
                "origem_nome": usuario.nome,
                "valor": round(real, 4),
                "energia_antes": round(antes, 4),
                "energia_depois": round(alvo.EnergiaAtual, 4),
                **_ataque_id_nome(ctx, "Pancada Seca"),
            },
        )
    ret["energia_removida"] = round(real, 4)
    return ret


def _exec_esmagar(ctx, alvo):
    usuario = ctx.get("usuario")
    base = _peso(usuario) * _param(ctx, "mult_peso", 0.40)
    blocos = max(0, int(math.floor(_peso(alvo) / _param(ctx, "kg_por_bloco", 40.0)))) if alvo is not None else 0
    mult = max(_param(ctx, "minimo_dano", 0.10), 1.0 - blocos * _param(ctx, "reducao_por_bloco", 0.15))
    return dano_generico(ctx, alvo, base, "normal", multiplicadores_condicionais=[{"label": "Reducao por peso do alvo", "multiplicador": mult}])


def _exec_transformar(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    vida_max_antes = max(1.0, usuario.obter_atributo("Vida", 1.0))
    pct_vida = max(0.0, min(1.0, usuario.VidaAtual / vida_max_antes))
    energia_atual = fnum(getattr(usuario, "EnergiaAtual", 0.0), 0.0)
    alvo_nome = str(getattr(alvo, "nome", "") or getattr(alvo, "especie", "") or usuario.nome)
    alvo_especie = str(getattr(alvo, "especie", "") or alvo_nome)
    usuario.nome = alvo_nome
    usuario.especie = alvo_especie
    if isinstance(getattr(usuario, "dados_originais", None), dict):
        usuario.dados_originais["nome"] = alvo_nome
        usuario.dados_originais["Nome"] = alvo_nome
        usuario.dados_originais["especie"] = alvo_especie
        usuario.dados_originais["Especie"] = alvo_especie
        dados_alvo = getattr(alvo, "dados_originais", {}) if isinstance(getattr(alvo, "dados_originais", None), dict) else {}
        for chave in ("CaminhoFrames", "caminho_frames", "FramesPath", "frames_path", "SpriteFrames", "sprite_frames"):
            if chave in dados_alvo:
                usuario.dados_originais[chave] = copy.deepcopy(dados_alvo[chave])
    usuario.tipos = copy.deepcopy(getattr(alvo, "tipos", []) or [])
    usuario.atributos_base = copy.deepcopy(getattr(alvo, "atributos_base", {}) or {})
    usuario.variacoes_permanentes = copy.deepcopy(getattr(alvo, "variacoes_permanentes", {}) or {})
    usuario.variacoes_temporarias = {chave: 0.0 for chave in usuario.variacoes_temporarias}
    usuario.ataques = copy.deepcopy(getattr(alvo, "ataques", []) or [])
    if hasattr(usuario, "_instanciar_ids_ataques"):
        usuario._instanciar_ids_ataques()
    usuario.recalcular_atributos()
    usuario.VidaAtual = max(0.0, min(usuario.obter_atributo("Vida", 1.0), usuario.obter_atributo("Vida", 1.0) * pct_vida))
    usuario.EnergiaAtual = max(0.0, min(usuario.obter_atributo("EneM", 1.0), energia_atual))
    partida = ctx.get("partida")
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log(
            "pokemon_transformou",
            {
                "pokemon_id": usuario.id_batalha,
                "pokemon_nome": usuario.nome,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "vida_percentual_mantida": round(pct_vida, 4),
                "energia_mantida": round(usuario.EnergiaAtual, 4),
                **_ataque_id_nome(ctx, "Transformar"),
            },
        )
    return {"aplicado": True, "transformou": True, "alvo_id": alvo.id_batalha}


def _exec_ataque_rapido(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.50)
    bruto += usuario.obter_atributo("Vel") * _param(ctx, "mult_vel", 0.30)
    return dano_generico(ctx, alvo, bruto, "normal")


def _exec_mimica(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    if usuario is None or alvo is None or partida is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    historico = getattr(partida, "historico_ataques_batalha", {}) or {}
    registro = (historico.get("ultimo_contra_alvo") or {}).get((alvo.id_batalha, usuario.id_batalha))
    if not registro:
        registro = (historico.get("ultimo_por_usuario") or {}).get(alvo.id_batalha)
    props_copiadas = copy.deepcopy((registro or {}).get("propriedades") if isinstance((registro or {}).get("propriedades"), dict) else {})
    ataque_copiado = copy.deepcopy((registro or {}).get("ataque") if isinstance((registro or {}).get("ataque"), dict) else {})
    if not props_copiadas:
        return {"falha": True, "motivo": "mimica_sem_ataque_copiavel"}
    if normalizar(props_copiadas.get("nome")) == "mimica" or str(props_copiadas.get("estilo_logico") or "").strip().lower() == "passivo":
        return {"falha": True, "motivo": "mimica_ataque_nao_copiavel"}
    from Servidor.Logica.Executes.ExecutesAtaques.ControladorExecutes import executar_execute_principal

    ctx_copia = dict(ctx)
    ctx_copia["propriedades"] = props_copiadas
    ctx_copia["ataque"] = ataque_copiado
    ctx_copia["alvos"] = [alvo]
    ctx_copia["alvo"] = alvo
    ctx_copia["mimica"] = True
    chave = props_copiadas.get("execute_principal") or props_copiadas.get("nome") or props_copiadas.get("ID") or ataque_copiado.get("ID") or ataque_copiado.get("Code")
    ret = executar_execute_principal(chave, ctx_copia, alvo=alvo)
    ret["mimica_copiou"] = props_copiadas.get("nome")
    return ret


def _passiva_normalizar(ctx):
    dados = ctx.get("dados_dano") if isinstance(ctx.get("dados_dano"), dict) else None
    if dados is None:
        return {}
    tipo_antes = dados.get("tipo")
    dados["tipo"] = "normal"
    return {"passiva": "Normalizar", "tipo_antes": tipo_antes, "tipo_depois": "normal"}


def _exec_resetar(ctx, alvo):
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    variacoes_antes = dict(getattr(alvo, "variacoes_permanentes", {}) or {})
    atributos_antes = {chave: alvo.obter_atributo(chave) for chave, valor in variacoes_antes.items() if abs(fnum(valor, 0.0)) > 0.001}
    alvo.variacoes_permanentes = {k: 0.0 for k in alvo.variacoes_permanentes}
    alvo.recalcular_atributos()
    if partida is not None and hasattr(partida, "registrar_evento_log"):
        for atributo, variacao_anterior in variacoes_antes.items():
            variacao_anterior = fnum(variacao_anterior, 0.0)
            if abs(variacao_anterior) <= 0.001:
                continue
            depois = alvo.obter_atributo(atributo)
            partida.registrar_evento_log(
                "pokemon_variou_atributo",
                {
                    "pokemon_id": alvo.id_batalha,
                    "pokemon_nome": alvo.nome,
                    "alvo_id": alvo.id_batalha,
                    "alvo_nome": alvo.nome,
                    "origem_id": getattr(usuario, "id_batalha", None),
                    "origem_nome": getattr(usuario, "nome", None),
                    "atributo": atributo,
                    "valor": round(-variacao_anterior, 4),
                    "variacao": round(-variacao_anterior, 4),
                    "valor_antes": round(fnum(atributos_antes.get(atributo, depois), 0.0), 4),
                    "valor_depois": round(fnum(depois, 0.0), 4),
                    "variacao_antes": round(variacao_anterior, 4),
                    "variacao_total": 0.0,
                    **_ataque_id_nome(ctx, "Resetar"),
                },
            )
    return {"aplicado": True, "resetou_variacoes_permanentes": True}


def _exec_tankar(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = aplicar_efeito(usuario, usuario, "Fortificado", duracao=3, negativo=False)
    atributo = "Def" if usuario.obter_atributo("Def") <= usuario.obter_atributo("SpD") else "SpD"
    bonus = usuario.obter_atributo("Mag") * _param(ctx, "mult_mag_defesa", 0.20)
    ret["bonus_defesa"] = aplicar_mod_atributo(ctx, usuario, "Tankar", atributo, bonus, negativo=False)
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="barreira")
    if critico_ctx.get("critico"):
        barreira = usuario.obter_atributo("Mag") * _param(ctx, "mult_mag_barreira_critico", 0.30)
        usuario.ReceberBarreira(barreira, origem=usuario, dados={**_ataque_id_nome(ctx, "Tankar"), "ataque": "Tankar", "critico": True, "critico_contextual": critico_ctx})
        ret["barreira_critica"] = barreira
    ret["critico_contextual"] = critico_ctx
    return ret


def _exec_estocada(ctx, alvo):
    usuario = ctx.get("usuario")
    extras = {}
    if bool(ctx.get("primeiro_ataque_da_rodada")):
        extras["multiplicadores_condicionais"] = [
            {"label": "Primeiro ataque do turno", "multiplicador": 1.0 + _param(ctx, "bonus_primeiro_ataque", 0.25)}
        ]
    return dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 0.80), "normal", **extras)


def _exec_bola_climatica(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    mult = _param(ctx, "mult_spa_clima", 1.00) if getattr(partida, "clima_atual", None) else _param(ctx, "mult_spa", 0.75)
    secundarios = inimigos_vivos_adjacentes_ao_alvo(ctx, alvo)
    alvo_principal_id = getattr(alvo, "id_batalha", None)
    secundarios_ids = [getattr(p, "id_batalha", None) for p in secundarios if p is not None]
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * mult, "especial", alvo_principal_id=alvo_principal_id, alvos_secundarios_ids=secundarios_ids, impacto_principal=True)
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida > 0:
        for adjacente in secundarios:
            dano_generico(ctx, adjacente, dano_vida * _param(ctx, "dano_adjacente", 0.50), "especial", alvo_principal_id=alvo_principal_id, alvos_secundarios_ids=secundarios_ids, impacto_secundario=True)
    return ret


def _exec_hiper_presa(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * _param(ctx, "mult_atk", 1.05), "normal", chance_critico_max=_param(ctx, "limite_critico", 80.0))
    if ret.get("critico") and alvo is not None and alvo.esta_vivo():
        alvo.receber_recuo(origem=usuario, dados={"ataque": "Hiper Presa", "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_inflar(ctx, alvo):
    usuario = ctx.get("usuario")
    vida_antes = max(1.0, usuario.obter_atributo("Vida", 1.0))
    pct_vida = max(0.0, min(1.0, usuario.VidaAtual / vida_antes))
    valor = usuario.obter_atributo("Mag") * _param(ctx, "mult_mag", 0.25)
    valor += vida_antes * _param(ctx, "mult_vida_max", 0.10)
    ret = aplicar_mod_atributo(ctx, usuario, "Inflar", "Vida", valor, negativo=False)
    vida_depois = max(1.0, usuario.obter_atributo("Vida", 1.0))
    usuario.VidaAtual = max(0.0, min(vida_depois, vida_depois * pct_vida))
    ret["vida_percentual_mantida"] = round(pct_vida, 4)
    ret["vida_atual_ajustada"] = round(usuario.VidaAtual, 4)
    return ret


_EXECUTES = {
    "investida": _exec_investida,
    "biscoito": _exec_biscoito,
    "enraivecer": _exec_enraivecer,
    "provocar": _exec_provocar,
    "proteger": _exec_proteger,
    "arranhar": _exec_arranhar,
    "recarga": _exec_recarga,
    "energia": _exec_energia,
    "hiperraio": _exec_hiper_raio,
    "guilhotina": _exec_guilhotina,
    "disparo": _exec_disparo,
    "chifrada": _exec_chifrada,
    "golpeprecavido": _exec_golpe_precavido,
    "pancadaseca": _exec_pancada_seca,
    "esmagar": _exec_esmagar,
    "transformar": _exec_transformar,
    "ataquerapido": _exec_ataque_rapido,
    "mimica": _exec_mimica,
    "normalizar": execute_passiva_nao_manual,
    "resetar": _exec_resetar,
    "tankar": _exec_tankar,
    "estocada": _exec_estocada,
    "bolaclimatica": _exec_bola_climatica,
    "hiperpresa": _exec_hiper_presa,
    "inflar": _exec_inflar,
}

_EXECUTES_REATIVOS = [
    ExecuteReativo(nome="GuilhotinaExecucao", flag="AoAplicarDano", func=_reativo_guilhotina, origem_ataque="Guilhotina", code="10", ordem=1),
]

_PASSIVAS_ATAQUE = [
    {"nome": "Normalizar", "flag": "AntesAplicarDano", "grupo": "self", "func": _passiva_normalizar, "origem": "ataque", "code": "19"},
]

_ALIASES = {
    "1": "investida",
    "2": "biscoito",
    "3": "enraivecer",
    "4": "provocar",
    "5": "proteger",
    "6": "arranhar",
    "7": "recarga",
    "8": "energia",
    "9": "hiperraio",
    "10": "guilhotina",
    "11": "disparo",
    "12": "chifrada",
    "13": "golpeprecavido",
    "14": "pancadaseca",
    "15": "esmagar",
    "16": "transformar",
    "17": "ataquerapido",
    "ataquerapido": "ataquerapido",
    "18": "mimica",
    "19": "normalizar",
    "20": "resetar",
    "21": "tankar",
    "22": "estocada",
    "23": "bolaclimatica",
    "24": "hiperpresa",
    "25": "inflar",
}


def obter_executes_normais():
    return dict(_EXECUTES)


def obter_executes_reativos_normais():
    return list(_EXECUTES_REATIVOS)


def obter_passivas_ataques_normais():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_normais():
    return dict(_ALIASES)


def resolver_chave(nome_ou_code):
    bruto = str(nome_ou_code or "").strip()
    if bruto in _ALIASES:
        return _ALIASES.get(bruto)
    chave = normalizar(bruto)
    chave_sem_prefixo = chave[6:] if chave.startswith("ataque") else chave
    if chave in _ALIASES:
        return _ALIASES.get(chave)
    if chave_sem_prefixo in _ALIASES:
        return _ALIASES.get(chave_sem_prefixo)
    return chave_sem_prefixo
