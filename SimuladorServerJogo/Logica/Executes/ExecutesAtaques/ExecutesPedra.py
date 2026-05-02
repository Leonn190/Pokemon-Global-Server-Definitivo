from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_casca_de_pedra(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("Def") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Casca de Pedra", "Def", valor, 6, False)


def _exec_muralha_rochosa(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = max(0.0, usuario.obter_atributo("Mag") * 0.18 + usuario.obter_atributo("Def") * 0.15)
    return usuario.AplicarBarreira(alvo, valor, dados={"ataque": "Muralha Rochosa", "ataque_id": 64, "ataque_nome": "Muralha Rochosa", "reativos_acao": ctx.get("reativos_acao")})


_EXECUTES = {"cascadepedra": _exec_casca_de_pedra, "muralharochosa": _exec_muralha_rochosa}
_ALIASES = {"59": "cascadepedra"}


def obter_executes_pedra():
    return dict(_EXECUTES)


def obter_passivas_ataques_pedra():
    return []


def obter_aliases_executes_pedra():
    return dict(_ALIASES)
