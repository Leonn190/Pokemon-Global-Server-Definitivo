from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_ferrugem(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Ferrugem", "Def", -alvo.obter_atributo("Def") * 0.08, 6, True)


def _exec_afiar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Afiar", "Per", usuario.obter_atributo("Mag") * 0.15, 6, False)


_EXECUTES = {"ferrugem": _exec_ferrugem, "afiar": _exec_afiar}
_ALIASES = {"40": "ferrugem", "45": "afiar"}


def obter_executes_metal():
    return dict(_EXECUTES)


def obter_passivas_ataques_metal():
    return []


def obter_aliases_executes_metal():
    return dict(_ALIASES)
