from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_selar_arcano(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Selar Arcano", "Mag", -alvo.obter_atributo("Mag") * 0.07, 6, True)


def _exec_desorientar(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Desorientar", "Int", -alvo.obter_atributo("Int") * 0.07, 6, True)


def _exec_azar(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Azar", "CrC", -alvo.obter_atributo("CrC") * 0.06, 6, True)


_EXECUTES = {"selararcano": _exec_selar_arcano, "desorientar": _exec_desorientar, "azar": _exec_azar}
_ALIASES = {"44": "selararcano", "50": "desorientar", "53": "azar"}


def obter_executes_fantasma():
    return dict(_EXECUTES)


def obter_passivas_ataques_fantasma():
    return []


def obter_aliases_executes_fantasma():
    return dict(_ALIASES)
