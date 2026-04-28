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
    return aplicar_mod_atributo(ctx, usuario, "Instinto", "Int", usuario.obter_atributo("Mag") * 0.15, 6, False)


def _exec_raio_psiquico(ctx, alvo):
    return executar_raio(ctx, alvo, 1.30, 0.15, "psiquico")


def _passiva_flutuante(ctx):
    return aplicar_passiva_permanente(ctx, "Flutuando")


_EXECUTES = {
    "confusao": _exec_confusao,
    "flutuar": _exec_flutuar,
    "instinto": _exec_instinto,
    "raiopsiquico": _exec_raio_psiquico,
    "flutuante": execute_passiva_nao_manual,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Flutuante", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_flutuante, "origem": "ataque", "code": "75"},
]
_ALIASES = {"28": "confusao", "31": "flutuar", "49": "instinto", "69": "raiopsiquico", "75": "flutuante"}


def obter_executes_psiquicos():
    return dict(_EXECUTES)


def obter_passivas_ataques_psiquicas():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_psiquicos():
    return dict(_ALIASES)
