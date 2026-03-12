"""Loop de tick do servidor (30 TPS)."""

from __future__ import annotations

import threading
import time

from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK


class TiqueServidor:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ativo = False
        self._rodando = False
        self._thread = None
        self._tps = 30.0
        self._ativado_por = ""

    def definir_ativo(self, ativo: bool) -> None:
        with self._lock:
            self._ativo = bool(ativo)
            if self._ativo and not self._rodando:
                self._iniciar_thread()

    def ativar_por_usuario(self, client_id: str) -> None:
        with self._lock:
            self._ativado_por = str(client_id or self._ativado_por)
            self._ativo = True
            if not self._rodando:
                self._iniciar_thread()

    def _iniciar_thread(self) -> None:
        self._rodando = True
        self._thread = threading.Thread(target=self._loop_ticks, name="TiqueServidor30TPS", daemon=True)
        self._thread.start()


    def _loop_ticks(self) -> None:
        from SimuladorServerJogo.Controle.CerebroCentral import CEREBRO
        while True:
            with self._lock:
                rodando = self._rodando
                ativo = self._ativo
                tps = max(1.0, float(self._tps))
            if not rodando:
                return
            if not ativo:
                time.sleep(0.05)
                continue

            inicio = time.perf_counter()
            CEREBRO.executar_tick_servidor()
            PACOTES_TICK.fechar_tick()
            alvo = 1.0 / tps
            elapsed = time.perf_counter() - inicio
            time.sleep(max(0.0, alvo - elapsed))

    def parar(self) -> None:
        with self._lock:
            self._ativo = False
            self._rodando = False

    def info(self) -> dict:
        with self._lock:
            return {"ativo": bool(self._ativo), "rodando": bool(self._rodando), "tps": float(self._tps), "ativado_por": str(self._ativado_por or "")}


TIQUE_SERVIDOR = TiqueServidor()
