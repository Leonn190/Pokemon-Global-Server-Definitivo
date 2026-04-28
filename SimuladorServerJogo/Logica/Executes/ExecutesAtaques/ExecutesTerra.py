from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_rachar_terra(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Rachar Terra", "Dur", -alvo.obter_atributo("Dur") * 0.06, 6, True)


def _exec_poeira_nos_olhos(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Poeira nos Olhos", "Acuracia", -alvo.obter_atributo("Acuracia") * 0.08, 6, True)


_EXECUTES = {"racharterra": _exec_rachar_terra, "poeiranosolhos": _exec_poeira_nos_olhos}
_ALIASES = {"57": "racharterra", "65": "poeiranosolhos"}


def obter_executes_terra():
    return dict(_EXECUTES)


def obter_passivas_ataques_terra():
    return []


def obter_aliases_executes_terra():
    return dict(_ALIASES)
