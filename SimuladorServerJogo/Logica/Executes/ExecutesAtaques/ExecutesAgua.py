from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_status,
    executar_bola,
    executar_danca_clima,
)


def _exec_bola_de_agua(ctx, alvo):
    return executar_bola(ctx, alvo, "agua")


def _exec_gota_pesada(ctx, alvo):
    return aplicar_status(ctx, alvo, "Encharcado", duracao=6, negativo=True)


def _exec_correnteza(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Correnteza", "Vel", usuario.obter_atributo("Mag") * 0.15, 6, False)


def _exec_danca_da_chuva(ctx, alvo):
    return executar_danca_clima(ctx, "Chuva")


_EXECUTES = {
    "boladeagua": _exec_bola_de_agua,
    "gotapesada": _exec_gota_pesada,
    "correnteza": _exec_correnteza,
    "dancadachuva": _exec_danca_da_chuva,
}

_ALIASES = {"20": "boladeagua", "24": "gotapesada", "47": "correnteza", "71": "dancadachuva"}


def obter_executes_agua():
    return dict(_EXECUTES)


def obter_passivas_ataques_agua():
    return []


def obter_aliases_executes_agua():
    return dict(_ALIASES)
