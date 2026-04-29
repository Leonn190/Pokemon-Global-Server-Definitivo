from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_status


def _exec_som_atordoante(ctx, alvo):
    return aplicar_status(ctx, alvo, "Atordoado", duracao=6, negativo=True)


_EXECUTES = {"somatordoante": _exec_som_atordoante}
_ALIASES = {"76": "somatordoante"}


def obter_executes_sonoro():
    return dict(_EXECUTES)


def obter_passivas_ataques_sonoro():
    return []


def obter_aliases_executes_sonoro():
    return dict(_ALIASES)
