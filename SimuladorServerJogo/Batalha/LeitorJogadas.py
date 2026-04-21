from __future__ import annotations

from typing import Dict, List

from SimuladorServerJogo.Batalha.Combate.ExecutorTurno import ExecutorTurno
from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha


class LeitorJogadas:
    def __init__(self) -> None:
        self._executor_turno = ExecutorTurno()

    def executar_turno(self, sistema: SistemaBatalha, client_id: str, jogadas: List[Dict[str, object]] | None = None) -> Dict[str, object]:
        return self._executor_turno.executar_turno(sistema, client_id=client_id, jogadas=jogadas)
