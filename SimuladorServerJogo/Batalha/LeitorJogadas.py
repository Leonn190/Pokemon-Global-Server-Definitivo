from __future__ import annotations

from typing import Dict, List

from SimuladorServerJogo.Batalha.Combate.ExecutorTurno import ExecutorTurno
from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha
from SimuladorServerJogo.Batalha.Combate.DebugCombate import dbg_combate


class LeitorJogadas:
    def __init__(self) -> None:
        self._executor_turno = ExecutorTurno()

    def executar_turno(self, sistema: SistemaBatalha, client_id: str, jogadas: List[Dict[str, object]] | None = None) -> Dict[str, object]:
        dbg_combate("LeitorJogadas", "executar_turno chamado", client_id=client_id, quantidade=len(jogadas or []))
        retorno = self._executor_turno.executar_turno(sistema, client_id=client_id, jogadas=jogadas)
        dbg_combate("LeitorJogadas", "retorno do ExecutorTurno", status=str((retorno or {}).get("status")))
        return retorno
