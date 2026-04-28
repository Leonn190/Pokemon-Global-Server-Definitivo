from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import aplicar_mod_atributo, executar_raio


def _exec_nevoa_fria(ctx, alvo):
    return aplicar_mod_atributo(ctx, alvo, "N\u00e9voa Fria", "SpA", -alvo.obter_atributo("SpA") * 0.08, 6, True)


def _exec_sangue_frio(ctx, alvo):
    usuario = ctx.get("usuario")
    return aplicar_mod_atributo(ctx, usuario, "Sangue Frio", "CrC", usuario.obter_atributo("Mag") * 0.06, 6, False)


def _exec_raio_de_gelo(ctx, alvo):
    return executar_raio(ctx, alvo, 1.30, 0.15, "gelo")


_EXECUTES = {"nevoafria": _exec_nevoa_fria, "sanguefrio": _exec_sangue_frio, "raiodegelo": _exec_raio_de_gelo}
_ALIASES = {"38": "nevoafria", "52": "sanguefrio", "67": "raiodegelo"}


def obter_executes_gelo():
    return dict(_EXECUTES)


def obter_passivas_ataques_gelo():
    return []


def obter_aliases_executes_gelo():
    return dict(_ALIASES)
