from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    execute_passiva_nao_manual,
)


def _exec_voar(ctx, alvo):
    return aplicar_status(ctx, ctx.get("usuario"), "Voando", duracao=6, negativo=False)


def _exec_olho_de_aguia(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Olho de \u00c1guia", "Acuracia", usuario.obter_atributo("Mag") * 0.15, 6, False)


def _passiva_voador(ctx):
    return aplicar_passiva_permanente(ctx, "Voando")


_EXECUTES = {
    "voar": _exec_voar,
    "olhodeaguia": _exec_olho_de_aguia,
    "voador": execute_passiva_nao_manual,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Voador", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_voador, "origem": "ataque", "code": "74"},
]
_ALIASES = {"30": "voar", "64": "olhodeaguia", "74": "voador"}


def obter_executes_voador():
    return dict(_EXECUTES)


def obter_passivas_ataques_voador():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_voador():
    return dict(_ALIASES)
