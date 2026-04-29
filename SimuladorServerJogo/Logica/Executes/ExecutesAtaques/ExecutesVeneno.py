from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    execute_passiva_nao_manual,
)


def _exec_envenenar(ctx, alvo):
    return aplicar_status(ctx, alvo, "Envenenado", duracao=6, negativo=True)


def _exec_armadura_mole(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Per") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Armadura Mole", "Per", -valor, 6, True)


def _passiva_imunizado(ctx):
    return aplicar_passiva_permanente(ctx, "Imune")


_EXECUTES = {
    "envenenar": _exec_envenenar,
    "armaduramole": _exec_armadura_mole,
    "imunizado": execute_passiva_nao_manual,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Imunizado", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_imunizado, "origem": "ataque", "code": "46"},
]
_ALIASES = {"44": "envenenar", "45": "armaduramole", "46": "imunizado"}


def obter_executes_veneno():
    return dict(_EXECUTES)


def obter_passivas_ataques_veneno():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_veneno():
    return dict(_ALIASES)
