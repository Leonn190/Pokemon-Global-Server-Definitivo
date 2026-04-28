from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    executar_raio,
)


def _exec_raizes(ctx, alvo):
    return aplicar_status(ctx, alvo, "Enraizado", duracao=6, negativo=True)


def _exec_casco_vivo(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Casco Vivo", "Dur", usuario.obter_atributo("Mag") * 0.12, 6, False)


def _exec_murchar(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "Murchar", "Vida", -alvo.obter_atributo("Vida") * 0.06, 6, True)


def _exec_raio_solar(ctx, alvo):
    return executar_raio(ctx, alvo, 1.30, 0.15, "planta", escala_sol_forte=1.60)


_EXECUTES = {
    "raizes": _exec_raizes,
    "cascovivo": _exec_casco_vivo,
    "murchar": _exec_murchar,
    "raiosolar": _exec_raio_solar,
}
_ALIASES = {"34": "raizes", "56": "cascovivo", "61": "murchar", "68": "raiosolar"}


def obter_executes_planta():
    return dict(_EXECUTES)


def obter_passivas_ataques_planta():
    return []


def obter_aliases_executes_planta():
    return dict(_ALIASES)
