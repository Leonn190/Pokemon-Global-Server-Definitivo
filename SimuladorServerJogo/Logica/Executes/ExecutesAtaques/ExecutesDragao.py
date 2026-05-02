from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo


def _exec_escama_mistica(ctx, alvo):
    usuario = ctx.get("usuario")
    valor = usuario.obter_atributo("Mag") * 0.20 + usuario.obter_atributo("SpD") * 0.10
    return aplicar_mod_atributo(ctx, usuario, "Escama M\u00edstica", "SpD", valor, 6, False)


def _exec_escudo_draconico(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    valor = max(0.0, usuario.obter_atributo("Mag") * 0.18 + usuario.obter_atributo("SpD") * 0.15)
    return usuario.AplicarBarreira(alvo, valor, dados={"ataque": "Escudo Draconico", "ataque_id": 69, "ataque_nome": "Escudo Draconico", "reativos_acao": ctx.get("reativos_acao")})


_EXECUTES = {"escamamistica": _exec_escama_mistica, "escudodraconico": _exec_escudo_draconico}
_ALIASES = {"63": "escamamistica"}


def obter_executes_dragao():
    return dict(_EXECUTES)


def obter_passivas_ataques_dragao():
    return []


def obter_aliases_executes_dragao():
    return dict(_ALIASES)
