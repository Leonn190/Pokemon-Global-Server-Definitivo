from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_ferrugem(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Def") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Ferrugem", "Def", -valor, 6, True)


def _exec_afiar(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("Per") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Afiar", "Per", valor, 6, False)


_EXECUTES = {"ferrugem": _exec_ferrugem, "afiar": _exec_afiar}
_ALIASES = {"71": "ferrugem", "72": "afiar"}


def obter_executes_metal():
    return dict(_EXECUTES)


def obter_passivas_ataques_metal():
    return []


def obter_aliases_executes_metal():
    return dict(_ALIASES)
