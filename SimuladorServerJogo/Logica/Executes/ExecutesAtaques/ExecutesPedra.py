from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_casca_de_pedra(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Casca de Pedra", "Def", usuario.obter_atributo("Mag") * 0.15, 6, False)


_EXECUTES = {"cascadepedra": _exec_casca_de_pedra}
_ALIASES = {"39": "cascadepedra"}


def obter_executes_pedra():
    return dict(_EXECUTES)


def obter_passivas_ataques_pedra():
    return []


def obter_aliases_executes_pedra():
    return dict(_ALIASES)
