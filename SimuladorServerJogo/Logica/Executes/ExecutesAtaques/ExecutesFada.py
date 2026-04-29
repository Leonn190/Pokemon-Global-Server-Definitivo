from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo, aplicar_status


def _exec_bencao(ctx, alvo):
    return aplicar_status(ctx, alvo, "Aben\u00e7oado", duracao=6, negativo=False)


def _exec_canalizar(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Canalizar", "Mag", usuario.obter_atributo("Mag") * 0.30, 6, False)


def _exec_amolecer(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, alvo, "Amolecer", "CrD", -(5.0 + usuario.obter_atributo("Mag") * 0.10), 6, True)


_EXECUTES = {"bencao": _exec_bencao, "canalizar": _exec_canalizar, "amolecer": _exec_amolecer}
_ALIASES = {"73": "bencao", "74": "canalizar", "75": "amolecer"}


def obter_executes_fada():
    return dict(_EXECUTES)


def obter_passivas_ataques_fada():
    return []


def obter_aliases_executes_fada():
    return dict(_ALIASES)
