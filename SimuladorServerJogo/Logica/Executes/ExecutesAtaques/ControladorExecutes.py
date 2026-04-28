from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesNormal import (
    obter_executes_normais,
    obter_executes_reativos_normais,
    obter_passivas_ataques_normais,
    resolver_chave,
)
from SimuladorServerJogo.Batalha.ResolvedorFlags import ExecuteReativo

_EXECUTES = obter_executes_normais()
_REATIVOS = obter_executes_reativos_normais()


def obter_execute_principal(nome_ou_code):
    return _EXECUTES.get(resolver_chave(nome_ou_code))


def executar_execute_principal(nome_ou_code, contexto, alvo=None):
    func = obter_execute_principal(nome_ou_code)
    if not callable(func):
        return {"falha": True, "motivo": "execute_nao_encontrado"}
    return dict(func(dict(contexto or {}), alvo) or {})


def executar_alvificacao(nome_ou_code, contexto):
    props = (contexto or {}).get("propriedades") if isinstance((contexto or {}).get("propriedades"), dict) else {}
    estilo = str(props.get("estilo_logico") or "").strip().lower()
    if estilo == "ativo":
        return []
    partida = (contexto or {}).get("partida")
    acao = (contexto or {}).get("acao") if isinstance((contexto or {}).get("acao"), dict) else {}
    alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo.get("tipo") or "").strip().lower() == "pokemon" and alvo.get("pokemon_id"):
        pokemon = partida.obter_pokemon(alvo.get("pokemon_id"))
        return [pokemon] if pokemon is not None else []
    area_id = alvo.get("area_id")
    ocupante = partida.pokemon_na_area(area_id) if partida is not None and area_id else None
    return [ocupante] if ocupante is not None else []


def registrar_execute_reativo(nome, flag, func, origem_ataque=None, code=None, grupo=None):
    _REATIVOS.append(
        ExecuteReativo(
            nome=str(nome),
            flag=str(flag),
            func=func,
            origem_ataque=origem_ataque,
            code=code,
            grupo=grupo,
            ordem=len(_REATIVOS) + 1,
        )
    )


def obter_executes_reativos(nome_ou_code, flag=None):
    chave = resolver_chave(nome_ou_code)
    origem = str(nome_ou_code)
    saida = [r for r in _REATIVOS if str((r.origem_ataque or "")).lower() in {str(origem).lower(), chave}]
    if flag:
        saida = [r for r in saida if str(r.flag) == str(flag)]
    return saida


def obter_passivas_ataque():
    return obter_passivas_ataques_normais()
