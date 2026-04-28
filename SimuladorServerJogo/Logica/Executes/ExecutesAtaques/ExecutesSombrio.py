from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    executar_bola,
)


def _exec_bola_sombria(ctx, alvo):
    return executar_bola(ctx, alvo, "sombrio")


def _exec_nas_sombras(ctx, alvo):
    return aplicar_status(ctx, ctx.get("usuario"), "Furtivo", duracao=6, negativo=False)


def _exec_sussurro_sombrio(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Sussurro Sombrio", "SpD", -alvo.obter_atributo("SpD") * 0.08, 6, True)


def _exec_sede_de_sangue(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Sede de Sangue", "Vamp", usuario.obter_atributo("Mag") * 0.08, 6, False)


def _exec_golpe_letal(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Golpe Letal", "CrD", usuario.obter_atributo("Mag") * 0.10, 6, False)


def _exec_silenciar(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Silenciar", "Amp", -alvo.obter_atributo("Amp") * 0.06, 6, True)


def _exec_intimidar(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Intimidar", "Assertividade", -alvo.obter_atributo("Assertividade") * 0.08, 6, True)


_EXECUTES = {
    "bolasombria": _exec_bola_sombria,
    "nassombras": _exec_nas_sombras,
    "sussurrosombrio": _exec_sussurro_sombrio,
    "sededesangue": _exec_sede_de_sangue,
    "golpeletal": _exec_golpe_letal,
    "silenciar": _exec_silenciar,
    "intimidar": _exec_intimidar,
}
_ALIASES = {
    "22": "bolasombria", "23": "nassombras", "42": "sussurrosombrio", "51": "sededesangue",
    "54": "golpeletal", "59": "silenciar", "63": "intimidar",
}


def obter_executes_sombrio():
    return dict(_EXECUTES)


def obter_passivas_ataques_sombrio():
    return []


def obter_aliases_executes_sombrio():
    return dict(_ALIASES)
