from __future__ import annotations

from typing import Dict, List


class MontadorJogada:
    def __init__(self) -> None:
        self._jogadas: List[Dict[str, object]] = []

    def adicionar(self, jogada: Dict[str, object]) -> None:
        if isinstance(jogada, dict):
            self._jogadas.append(dict(jogada))

    def listar(self) -> List[Dict[str, object]]:
        return [dict(item) for item in self._jogadas]

    def limpar(self) -> None:
        self._jogadas.clear()

    def custo_reservado(self, combatente_id: str) -> float:
        chave = str(combatente_id or "")
        total = 0.0
        for item in self._jogadas:
            if str(item.get("executor_id") or "") != chave:
                continue
            try:
                total += float(item.get("custo") or 0.0)
            except (TypeError, ValueError):
                continue
        return total
