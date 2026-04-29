from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    execute_passiva_nao_manual,
)


def _exec_grito_de_guerra(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("Atk") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Grito de Guerra", "Atk", valor, 6, False)


def _passiva_implacavel(ctx):
    return aplicar_passiva_permanente(ctx, "Imparavel")


_EXECUTES = {
    "gritodeguerra": _exec_grito_de_guerra,
    "implacavel": execute_passiva_nao_manual,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Implac\u00e1vel", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_implacavel, "origem": "ataque", "code": "43"},
]
_ALIASES = {"41": "gritodeguerra", "43": "implacavel"}


def obter_executes_lutador():
    return dict(_EXECUTES)


def obter_passivas_ataques_lutador():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_lutador():
    return dict(_ALIASES)
