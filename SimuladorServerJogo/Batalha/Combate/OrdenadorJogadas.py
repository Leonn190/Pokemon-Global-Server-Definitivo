from __future__ import annotations

from typing import Any



def _fnum(valor: object, padrao: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


class OrdenadorJogadas:
    def chave_ordenacao_jogada(self, jogada: dict[str, Any], contexto: dict[str, Any] | None = None) -> tuple:
        _ = contexto
        prioridade = int(_fnum(jogada.get("prioridade", 0), 0))
        inteligencia = _fnum(jogada.get("inteligencia", 0.0), 0.0)
        velocidade = _fnum(jogada.get("velocidade", 0.0), 0.0)
        indice_entrada = int(_fnum(jogada.get("indice_entrada", 0), 0))
        custo = _fnum(jogada.get("custo", jogada.get("custo_base", 0.0)), 0.0)
        executor_id = str(jogada.get("executor_id") or "")
        jogada_id = str(jogada.get("id") or "")
        chave = (-prioridade, -inteligencia, -velocidade, custo, indice_entrada, executor_id, jogada_id)
        return chave

    def ordenar(self, jogadas, contexto: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        normalizadas = [dict(j) for j in list(jogadas or []) if isinstance(j, dict)]
        ordenadas = sorted(normalizadas, key=lambda item: self.chave_ordenacao_jogada(item, contexto=contexto))
        for ordem, jogada in enumerate(ordenadas):
            jogada["dados_ordenacao"] = {
                "ordem": ordem,
                "executor_id": str(jogada.get("executor_id") or ""),
                "inteligencia": _fnum(jogada.get("inteligencia", 0.0), 0.0),
                "prioridade": int(_fnum(jogada.get("prioridade", 0), 0)),
                "velocidade": _fnum(jogada.get("velocidade", 0.0), 0.0),
                "criterios": {
                    "prioridade": int(_fnum(jogada.get("prioridade", 0), 0)),
                    "inteligencia": _fnum(jogada.get("inteligencia", 0.0), 0.0),
                    "velocidade": _fnum(jogada.get("velocidade", 0.0), 0.0),
                    "custo": _fnum(jogada.get("custo", jogada.get("custo_base", 0.0)), 0.0),
                    "indice_entrada": int(_fnum(jogada.get("indice_entrada", 0), 0)),
                    "id": str(jogada.get("id") or ""),
                },
            }
        return ordenadas
