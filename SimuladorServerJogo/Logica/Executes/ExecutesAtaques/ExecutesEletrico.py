from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    executar_bola,
    executar_danca_clima,
)


def _exec_bola_eletrica(ctx, alvo):
    return executar_bola(ctx, alvo, "eletrico")


def _exec_energizar(ctx, alvo):
    return aplicar_status(ctx, alvo, "Energizado", duracao=6, negativo=False)


def _exec_amplificar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Amplificar", "Amp", usuario.obter_atributo("Mag") * 0.08, 6, False)


def _exec_danca_eletrica(ctx, alvo):
    return executar_danca_clima(ctx, "Tempestade de Raios")


_EXECUTES = {
    "bolaeletrica": _exec_bola_eletrica,
    "energizar": _exec_energizar,
    "amplificar": _exec_amplificar,
    "dancaeletrica": _exec_danca_eletrica,
}
_ALIASES = {"21": "bolaeletrica", "27": "energizar", "58": "amplificar", "73": "dancaeletrica"}


def obter_executes_eletricos():
    return dict(_EXECUTES)


def obter_passivas_ataques_eletricas():
    return []


def obter_aliases_executes_eletricos():
    return dict(_ALIASES)
