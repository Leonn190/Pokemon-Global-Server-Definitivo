from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    execute_passiva_nao_manual,
    executar_raio,
)


def _exec_confusao(ctx, alvo):
    return aplicar_status(ctx, alvo, "Confuso", duracao=6, negativo=True)


def _exec_flutuar(ctx, alvo):
    return aplicar_status(ctx, ctx.get("usuario"), "Flutuando", duracao=6, negativo=False)


def _exec_instinto(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("Int") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Instinto", "Int", valor, 6, False)


def _exec_raio_psiquico(ctx, alvo):
    return executar_raio(ctx, alvo, 1.00, 0.15, "psiquico")


def _exec_veu_arcano(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = max(0.0, usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("SpA") * 0.12)
    return usuario.AplicarBarreira(alvo, valor, dados={"ataque": "Véu Arcano", "ataque_id": 59, "ataque_nome": "Véu Arcano", "reativos_acao": ctx.get("reativos_acao")})


def _exec_mente_protetora(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = max(0.0, usuario.obter_atributo("Mag") * 0.18 + usuario.obter_atributo("Int") * 0.10)
    return usuario.AplicarBarreira(alvo, valor, dados={"ataque": "Mente Protetora", "ataque_id": 60, "ataque_nome": "Mente Protetora", "reativos_acao": ctx.get("reativos_acao")})


def _passiva_flutuante(ctx):
    return aplicar_passiva_permanente(ctx, "Flutuando")


_EXECUTES = {
    "confusao": _exec_confusao,
    "flutuar": _exec_flutuar,
    "instinto": _exec_instinto,
    "raiopsiquico": _exec_raio_psiquico,
    "flutuante": execute_passiva_nao_manual,
    "veuarcano": _exec_veu_arcano,
    "menteprotetora": _exec_mente_protetora,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Flutuante", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_flutuante, "origem": "ataque", "code": "56"},
]
_ALIASES = {"52": "confusao", "53": "flutuar", "54": "instinto", "55": "raiopsiquico", "56": "flutuante"}


def obter_executes_psiquicos():
    return dict(_EXECUTES)


def obter_passivas_ataques_psiquicas():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_psiquicos():
    return dict(_ALIASES)
