from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_selar_arcano(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Mag") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Selar Arcano", "Mag", -valor, 6, True)


def _exec_desorientar(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Int") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Desorientar", "Int", -valor, 6, True)


def _exec_azar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, alvo, "Azar", "CrC", -(5.0 + usuario.obter_atributo("Mag") * 0.10), 6, True)


_EXECUTES = {"selararcano": _exec_selar_arcano, "desorientar": _exec_desorientar, "azar": _exec_azar}
_ALIASES = {"60": "selararcano", "61": "desorientar", "62": "azar"}


def obter_executes_fantasma():
    return dict(_EXECUTES)


def obter_passivas_ataques_fantasma():
    return []


def obter_aliases_executes_fantasma():
    return dict(_ALIASES)
