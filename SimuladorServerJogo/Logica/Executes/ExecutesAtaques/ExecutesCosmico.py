from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import executar_raio


def _exec_raio_cosmico(ctx, alvo):
    return executar_raio(ctx, alvo, 1.45, 0.12, "cosmico")


_EXECUTES = {"raiocosmico": _exec_raio_cosmico}
_ALIASES = {"77": "raiocosmico"}


def obter_executes_cosmicos():
    return dict(_EXECUTES)


def obter_passivas_ataques_cosmicas():
    return []


def obter_aliases_executes_cosmicos():
    return dict(_ALIASES)
