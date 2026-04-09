from __future__ import annotations

from typing import Any, Dict, List


class MontadorJogada:
    """Acumula jogadas preparadas até o envio do turno."""

    def __init__(self) -> None:
        self._acoes: List[Dict[str, Any]] = []

    @property
    def acoes(self) -> List[Dict[str, Any]]:
        return list(self._acoes)

    def limpar(self) -> None:
        self._acoes.clear()

    def adicionar(self, acao: Dict[str, Any]) -> None:
        if not isinstance(acao, dict):
            return
        self._acoes.append(dict(acao))

    def custo_reservado(self, combatente_id: int) -> float:
        alvo = int(combatente_id)
        total = 0.0
        for acao in self._acoes:
            if int(acao.get("combatente_id", -1) or -1) != alvo:
                continue
            try:
                total += max(0.0, float(acao.get("custo", 0.0) or 0.0))
            except Exception:
                continue
        return total
