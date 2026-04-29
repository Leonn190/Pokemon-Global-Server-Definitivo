from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_escama_mistica(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("SpD") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Escama M\u00edstica", "SpD", valor, 6, False)


_EXECUTES = {"escamamistica": _exec_escama_mistica}
_ALIASES = {"63": "escamamistica"}


def obter_executes_dragao():
    return dict(_EXECUTES)


def obter_passivas_ataques_dragao():
    return []


def obter_aliases_executes_dragao():
    return dict(_ALIASES)
