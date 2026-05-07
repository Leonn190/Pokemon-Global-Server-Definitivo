from __future__ import annotations

from SimuladorServerJogo.Batalha.ResolvedorFlags import ExecuteReativo
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_efeito,
    aplicar_mod_atributo,
    critico_simples,
    dano_generico,
    fnum,
    inimigos_vivos_adjacentes_ao_alvo,
    normalizar,
    resolver_critico_contextual,
)


def _exec_investida(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("Atk") * 0.90, "normal")
    dano_vida = float(ret.get("dano_vida") or 0.0)
    if dano_vida > 0:
        usuario.ReceberDano(dano_vida * 0.20, origem=usuario, dados={"recuo": "Investida", "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_biscoito(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    stacks = int(alvo.contadores_especiais.get("Biscoito", 0) or 0)
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="cura")
    critico = bool(critico_ctx.get("critico"))
    cura = usuario.obter_atributo("Mag") * 0.55
    mult_stacks = 1.0 + (stacks * ((0.15 if critico else 0.10) / 0.55))
    ret = usuario.AplicarCura(
        alvo,
        cura,
        dados={
            "ataque": "Biscoito",
            "ataque_id": 2,
            "ataque_nome": "Biscoito",
            "critico": critico,
            "critico_contextual": critico_ctx,
            "reativos_acao": ctx.get("reativos_acao"),
            "multiplicadores_condicionais": [
                {"label": "Multiplicador Condicional (stacks de Biscoito)", "multiplicador": mult_stacks}
            ],
        },
    )
    alvo.contadores_especiais["Biscoito"] = stacks + 1
    if usuario is not alvo:
        usuario.contadores_especiais["Biscoito"] = int(usuario.contadores_especiais.get("Biscoito", 0) or 0) + 1
    return ret


def _exec_enraivecer(ctx, alvo):
    usuario = ctx.get("usuario")
    vida_max = max(1.0, usuario.obter_atributo("Vida", 1.0))
    if usuario.VidaAtual / vida_max < 0.40:
        return aplicar_efeito(usuario, usuario, "Amplificado", duracao=3, negativo=False)
    return {"aplicado": True, "sem_efeito": True}


def _exec_provocar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_efeito(usuario, usuario, "Provocando", duracao=3, negativo=False)


def _exec_proteger(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    alvo.adicionar_estado_transitorio("protegido", {"passo": ctx.get("passo")})
    return {"aplicado": True, "estado": "protegido"}


def _exec_arranhar(ctx, alvo):
    return dano_generico(ctx, alvo, ctx.get("usuario").obter_atributo("Atk") * 1.00, "normal")


def _exec_recarga(ctx, alvo):
    usuario = ctx.get("usuario")
    return usuario.GanharEnergia(float(ctx.get("custo_real") or 0.0) * 2.0, dados={"ataque": "Recarga", "motivo": "Recarga", "reativos_acao": ctx.get("reativos_acao")})


def _exec_energia(ctx, alvo):
    return dano_generico(ctx, alvo, ctx.get("usuario").obter_atributo("SpA") * 0.85, "especial")


def _exec_hiper_raio(ctx, alvo):
    usuario = ctx.get("usuario")
    alvos = [a for a in list(ctx.get("alvos") or []) if a is not None and a.esta_vivo()]
    bruto = max(0.0, usuario.obter_atributo("SpA") * 1.10 - ((max(1, len(alvos)) - 1) * usuario.obter_atributo("SpA") * 0.15))
    return dano_generico(ctx, alvo, bruto, "especial")


def _exec_guilhotina(ctx, alvo):
    return dano_generico(ctx, alvo, ctx.get("usuario").obter_atributo("Atk") * 0.60, "normal")


def _reativo_guilhotina(ctx):
    resultado = ctx.get("resultado") if isinstance(ctx.get("resultado"), dict) else {}
    if not bool(resultado.get("critico")):
        return {}
    usuario = ctx.get("usuario")
    alvo = ctx.get("alvo")
    if usuario is None or alvo is None or (not alvo.esta_vivo()) or int(alvo.lado_id) == int(usuario.lado_id):
        return {}
    if alvo.VidaAtual >= alvo.obter_atributo("Vida", 1.0) * 0.25:
        return {}
    ativou = alvo.Morrer({"origem_id": usuario.id_batalha, "ataque": "Guilhotina", "ataque_nome": "Guilhotina", "reativos_acao": ctx.get("reativos_acao")})
    return {"execucao_guilhotina": bool(ativou)} if ativou else {}


def _exec_disparo(ctx, alvo):
    return dano_generico(ctx, alvo, ctx.get("usuario").obter_atributo("Atk") * 0.75, "normal")


def _exec_chifrada(ctx, alvo):
    u = ctx.get("usuario")
    return dano_generico(ctx, alvo, u.obter_atributo("Atk") * 0.70 + u.obter_atributo("Per") * 0.25, "normal")


def _exec_resetar(ctx, alvo):
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    usuario = ctx.get("usuario")
    ataque = ctx.get("ataque") if isinstance(ctx.get("ataque"), dict) else {}
    props = ctx.get("propriedades") if isinstance(ctx.get("propriedades"), dict) else {}
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
            valor = -variacao_anterior
            partida.registrar_evento_log(
                "pokemon_variou_atributo",
                {
                    "pokemon_id": alvo.id_batalha,
                    "pokemon_nome": alvo.nome,
                    "alvo_id": alvo.id_batalha,
                    "alvo_nome": alvo.nome,
                    "origem_id": getattr(usuario, "id_batalha", None),
                    "origem_nome": getattr(usuario, "nome", None),
                    "usuario_id": getattr(usuario, "id_batalha", None),
                    "usuario_nome": getattr(usuario, "nome", None),
                    "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
                    "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome") or "Resetar",
                    "atributo": atributo,
                    "valor": round(valor, 4),
                    "variacao": round(valor, 4),
                    "valor_antes": round(fnum(atributos_antes.get(atributo, depois), 0.0), 4),
                    "valor_depois": round(fnum(depois, 0.0), 4),
                    "variacao_antes": round(variacao_anterior, 4),
                    "variacao_total": 0.0,
                    "positivo": valor >= 0,
                    "negativo": valor < 0,
                },
            )
    return {"aplicado": True, "resetou_variacoes": True}


def _exec_tankar(ctx, alvo):
    usuario = ctx.get("usuario")
    bonus = usuario.obter_atributo("Mag") * 0.20
    ret = aplicar_efeito(usuario, usuario, "Fortificado", duracao=3, negativo=False)
    critico_ctx = resolver_critico_contextual(usuario, ctx, tipo="efeito")
    if critico_ctx.get("critico"):
        usuario.ReceberBarreira(bonus, origem=usuario, dados={"ataque": "Tankar", "ataque_id": 14, "ataque_nome": "Tankar", "critico": True, "critico_contextual": critico_ctx})
        ret["barreira_critica"] = bonus
    ret["critico_contextual"] = critico_ctx
    return ret


def _exec_estocada(ctx, alvo):
    bruto = ctx.get("usuario").obter_atributo("Atk") * 0.80
    extras = {}
    if bool(ctx.get("primeiro_ataque_da_rodada")):
        extras["multiplicadores_condicionais"] = [
            {"label": "Multiplicador Condicional (primeiro ataque do turno)", "multiplicador": 1.20}
        ]
    return dano_generico(ctx, alvo, bruto, "normal", **extras)


def _exec_bola_climatica(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    bruto = usuario.obter_atributo("SpA") * (1.00 if getattr(partida, "clima_atual", None) else 0.80)
    ret = dano_generico(ctx, alvo, bruto, "especial")
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida > 0:
        for adjacente in inimigos_vivos_adjacentes_ao_alvo(ctx, alvo):
            dano_generico(ctx, adjacente, dano_vida * 0.5, "especial", tipo="normal")
    return ret


def _exec_hiper_presa(ctx, alvo):
    ret = dano_generico(ctx, alvo, ctx.get("usuario").obter_atributo("Atk") * 1.00, "normal", chance_critico_max=80.0)
    if ret.get("critico") and alvo is not None:
        alvo.receber_recuo(origem=ctx.get("usuario"), dados={"ataque": "Hiper Presa", "reativos_acao": ctx.get("reativos_acao")})
    return ret


def _exec_acumulador(ctx, alvo):
    return {"falha": True, "motivo": "passiva_nao_manual"}


def _exec_rugido(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Atk") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Rugido", "Atk", -valor, 6, True)


def _exec_inflar(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.25 + usuario.obter_atributo("Vida") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Inflar", "Vida", valor, 6, False)


def _passiva_acumulador(ctx):
    alvo = ctx.get("dono_passiva") or ctx.get("pokemon_evento")
    if alvo is None:
        return {}
    alvo.variacoes_permanentes["Amp"] = float(alvo.variacoes_permanentes.get("Amp", 0.0) or 0.0) + 4.0
    alvo.recalcular_atributos()
    return {"passiva": "Acumulador", "pokemon_id": alvo.id_batalha, "atributo": "Amp", "valor": 4.0, "Amp": alvo.variacoes_permanentes["Amp"], "positivo": True}

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
    "resetar": _exec_resetar,
    "tankar": _exec_tankar,
    "estocada": _exec_estocada,
    "bolaclimatica": _exec_bola_climatica,
    "hiperpresa": _exec_hiper_presa,
    "acumulador": _exec_acumulador,
    "rugido": _exec_rugido,
    "inflar": _exec_inflar,
}

_EXECUTES_REATIVOS = [
    ExecuteReativo(nome="GuilhotinaExecucao", flag="AoAplicarDano", func=_reativo_guilhotina, origem_ataque="Guilhotina", code="10", ordem=1),
]

_PASSIVAS_ATAQUE = [
    {"nome": "Acumulador", "flag": "AntesReceberAtaque", "grupo": "self", "func": _passiva_acumulador, "origem": "ataque", "code": "18"},
]

_ALIASES = {
    "1": "investida", "2": "biscoito", "3": "enraivecer", "4": "provocar", "5": "proteger", "6": "arranhar", "7": "recarga", "8": "energia", "9": "hiperraio", "10": "guilhotina", "11": "disparo", "12": "chifrada", "13": "resetar", "14": "tankar", "15": "estocada", "16": "bolaclimatica", "17": "hiperpresa", "18": "acumulador", "19": "rugido", "20": "inflar",
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
