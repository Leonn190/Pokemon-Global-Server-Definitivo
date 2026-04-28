from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    executar_bola,
    executar_danca_clima,
    executar_raio,
)


def _exec_bola_de_fogo(ctx, alvo):
    return executar_bola(ctx, alvo, "fogo")


def _exec_queimar(ctx, alvo):
    return aplicar_status(ctx, alvo, "Queimado", duracao=6, negativo=True)


def _exec_chama_interior(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Chama Interior", "SpA", usuario.obter_atributo("Mag") * 0.15, 6, False)


def _exec_raio_de_fogo(ctx, alvo):
    return executar_raio(ctx, alvo, 1.30, 0.15, "fogo")


def _exec_danca_do_sol(ctx, alvo):
    return executar_danca_clima(ctx, "Sol Forte")


_EXECUTES = {
    "boladefogo": _exec_bola_de_fogo,
    "queimar": _exec_queimar,
    "chamainterior": _exec_chama_interior,
    "raiodefogo": _exec_raio_de_fogo,
    "dancadosol": _exec_danca_do_sol,
}
_ALIASES = {"19": "boladefogo", "25": "queimar", "37": "chamainterior", "66": "raiodefogo", "72": "dancadosol"}


def obter_executes_fogo():
    return dict(_EXECUTES)


def obter_passivas_ataques_fogo():
    return []


def obter_aliases_executes_fogo():
    return dict(_ALIASES)
