from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo, aplicar_status


def _exec_regeneracao(ctx, alvo):
    return aplicar_status(ctx, alvo, "Regenera\u00e7\u00e3o", duracao=6, negativo=False)


def _exec_teia_pegajosa(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = alvo.obter_atributo("Vel") * 0.10 + usuario.obter_atributo("Mag") * 0.10
    return aplicar_mod_atributo(ctx, alvo, "Teia Pegajosa", "Vel", -valor, 6, True)


_EXECUTES = {"regeneracao": _exec_regeneracao, "teiapegajosa": _exec_teia_pegajosa}
_ALIASES = {"57": "regeneracao", "58": "teiapegajosa"}


def obter_executes_inseto():
    return dict(_EXECUTES)


def obter_passivas_ataques_inseto():
    return []


def obter_aliases_executes_inseto():
    return dict(_ALIASES)
