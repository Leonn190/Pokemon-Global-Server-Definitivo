from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_mod_atributo,
    aplicar_passiva_permanente,
    aplicar_status,
    execute_passiva_nao_manual,
)


def _exec_voar(ctx, alvo):
    return aplicar_status(ctx, ctx.get("usuario"), "Voando", duracao=6, negativo=False)


def _exec_olho_de_aguia(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("Acuracia") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Olho de \u00c1guia", "Acuracia", valor, 6, False)


def _exec_cortina_de_vento(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = max(0.0, usuario.obter_atributo("Mag") * 0.18 + usuario.obter_atributo("Vel") * 0.10)
    return usuario.AplicarBarreira(alvo, valor, dados={"ataque": "Cortina de Vento", "ataque_id": 53, "ataque_nome": "Cortina de Vento", "reativos_acao": ctx.get("reativos_acao")})


def _passiva_voador(ctx):
    return aplicar_passiva_permanente(ctx, "Voando")


_EXECUTES = {
    "voar": _exec_voar,
    "olhodeaguia": _exec_olho_de_aguia,
    "cortinadevento": _exec_cortina_de_vento,
    "voador": execute_passiva_nao_manual,
}
_PASSIVAS_ATAQUE = [
    {"nome": "Voador", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_voador, "origem": "ataque", "code": "51"},
]
_ALIASES = {"49": "voar", "50": "olhodeaguia", "51": "voador"}


def obter_executes_voador():
    return dict(_EXECUTES)


def obter_passivas_ataques_voador():
    return list(_PASSIVAS_ATAQUE)


def obter_aliases_executes_voador():
    return dict(_ALIASES)
