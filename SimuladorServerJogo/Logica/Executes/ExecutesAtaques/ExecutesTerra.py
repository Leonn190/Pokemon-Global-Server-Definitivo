from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_rachar_terra(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, alvo, "Rachar Terra", "Dur", -(5.0 + usuario.obter_atributo("Mag") * 0.10), 6, True)


def _exec_poeira_nos_olhos(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Acuracia") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Poeira nos Olhos", "Acuracia", -valor, 6, True)


_EXECUTES = {"racharterra": _exec_rachar_terra, "poeiranosolhos": _exec_poeira_nos_olhos}
_ALIASES = {"47": "racharterra", "48": "poeiranosolhos"}


def obter_executes_terra():
    return dict(_EXECUTES)


def obter_passivas_ataques_terra():
    return []


def obter_aliases_executes_terra():
    return dict(_ALIASES)
