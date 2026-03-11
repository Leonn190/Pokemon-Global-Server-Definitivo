"""Armazenador simples de pacotes por tick."""

from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Dict, List


class ArmazenadorPacotesTick:
    def __init__(self, max_pacotes: int = 600) -> None:
        self._lock = threading.RLock()
        self._max_pacotes = max(60, int(max_pacotes))
        self._tick_atual = 0
        self._pendentes: List[Dict[str, object]] = []
        self._pacotes: Deque[Dict[str, object]] = deque(maxlen=self._max_pacotes)

    def tick_atual(self) -> int:
        with self._lock:
            return int(self._tick_atual)

    def registrar_diff_pendente(self, diff: Dict[str, object]) -> None:
        if not isinstance(diff, dict):
            return
        with self._lock:
            self._pendentes.append(dict(diff))

    def fechar_tick(self, tick: int | None = None) -> Dict[str, object]:
        with self._lock:
            if tick is None:
                self._tick_atual += 1
            else:
                self._tick_atual = max(self._tick_atual + 1, int(tick))
            pacote = {"tick": int(self._tick_atual), "diffs": list(self._pendentes)}
            self._pendentes.clear()
            self._pacotes.append(pacote)
            return pacote

    def obter_pacotes_desde(self, ultimo_tick: int, limite: int = 60) -> List[Dict[str, object]]:
        with self._lock:
            ultimo = int(ultimo_tick or 0)
            saida = [dict(p) for p in self._pacotes if int(p.get("tick", 0)) > ultimo]
            if len(saida) > int(limite):
                saida = saida[-int(limite):]
            return saida


PACOTES_TICK = ArmazenadorPacotesTick(max_pacotes=900)
