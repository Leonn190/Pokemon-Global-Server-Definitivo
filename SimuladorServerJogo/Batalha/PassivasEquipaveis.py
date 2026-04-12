from __future__ import annotations

from typing import Dict


_REGISTRO_PASSIVAS_EQUIPAVEIS: dict[str, dict[str, object]] = {}


def _normalizar(valor: object) -> str:
    return str(valor or "").strip().casefold()


def registrar_passiva_equipavel(nome_equipavel: str, ativacao: str, funcao) -> None:
    nome = _normalizar(nome_equipavel)
    gatilho = _normalizar(ativacao)
    if not nome or not gatilho or not callable(funcao):
        return
    _REGISTRO_PASSIVAS_EQUIPAVEIS.setdefault(nome, {})[gatilho] = funcao


def executar_passivas_equipaveis(passivas: list[object] | None, ativacao: str, contexto: Dict[str, object] | None = None) -> list[Dict[str, object]]:
    resultados: list[Dict[str, object]] = []
    gatilho = _normalizar(ativacao)
    if not gatilho:
        return resultados
    for passiva in list(passivas or []):
        nome = _normalizar(passiva)
        funcao = _REGISTRO_PASSIVAS_EQUIPAVEIS.get(nome, {}).get(gatilho)
        if not callable(funcao):
            continue
        retorno = funcao(dict(contexto or {}))
        if isinstance(retorno, dict):
            resultados.append(dict(retorno))
    return resultados
