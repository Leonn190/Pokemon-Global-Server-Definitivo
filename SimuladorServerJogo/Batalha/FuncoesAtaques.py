from __future__ import annotations

from typing import Dict


_REGISTRO_ATAQUES: dict[str, dict[str, object]] = {}


def _normalizar(valor: object) -> str:
    return str(valor or "").strip().casefold()


def registrar_funcao_ataque(nome_ataque: str, ponto_analise: str, funcao) -> None:
    nome = _normalizar(nome_ataque)
    ponto = _normalizar(ponto_analise)
    if not nome or not ponto or not callable(funcao):
        return
    _REGISTRO_ATAQUES.setdefault(nome, {})[ponto] = funcao


def executar_ponto_ataque(nome_ataque: object, ponto_analise: str, contexto: Dict[str, object] | None = None) -> Dict[str, object]:
    nome = _normalizar(nome_ataque)
    ponto = _normalizar(ponto_analise)
    if not nome or not ponto:
        return {}
    funcao = _REGISTRO_ATAQUES.get(nome, {}).get(ponto)
    if not callable(funcao):
        return {}
    retorno = funcao(dict(contexto or {}))
    return dict(retorno) if isinstance(retorno, dict) else {}
