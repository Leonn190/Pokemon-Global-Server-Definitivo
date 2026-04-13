"""Loop de tick do servidor (30 TPS)."""

from __future__ import annotations

import threading
import time

from SimuladorServerJogo.Mundo.PacotesTick import PACOTES_TICK


class TiqueServidor:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ativo = False
        self._rodando = False
        self._thread = None
        self._tps = 30.0
        self._ativado_por = ""
        self._modo_manual = False
        self._proximo_tick_manual = None

    def usar_bombeamento_manual(self, ativo: bool) -> None:
        thread = None
        with self._lock:
            self._modo_manual = bool(ativo)
            self._proximo_tick_manual = time.perf_counter()
            if self._modo_manual:
                self._rodando = False
                thread = self._thread
                self._thread = None
        if thread and thread.is_alive():
            thread.join(timeout=0.2)

    def modo_manual(self) -> bool:
        with self._lock:
            return bool(self._modo_manual)

    def definir_ativo(self, ativo: bool) -> None:
        with self._lock:
            self._ativo = bool(ativo)
            if self._modo_manual:
                self._proximo_tick_manual = time.perf_counter()
                return
            if self._ativo and not self._rodando:
                self._iniciar_thread()

    def ativar_por_usuario(self, client_id: str) -> None:
        with self._lock:
            self._ativado_por = str(client_id or self._ativado_por)
            self._ativo = True
            if self._modo_manual:
                if self._proximo_tick_manual is None:
                    self._proximo_tick_manual = time.perf_counter()
                return
            if not self._rodando:
                self._iniciar_thread()

    def _iniciar_thread(self) -> None:
        self._rodando = True
        self._thread = threading.Thread(target=self._loop_ticks, name="TiqueServidor30TPS", daemon=True)
        self._thread.start()


    def _loop_ticks(self) -> None:
        from SimuladorServerJogo.Mundo.Cerebros.CerebroCentral import CEREBRO
        proximo_tick = time.perf_counter()
        while True:
            with self._lock:
                rodando = self._rodando
                ativo = self._ativo
                tps = max(1.0, float(self._tps))
                modo_manual = self._modo_manual
            if not rodando:
                return
            if modo_manual:
                return
            if not ativo:
                proximo_tick = time.perf_counter()
                time.sleep(0.05)
                continue
            if not CEREBRO.tem_players_ativos():
                proximo_tick = time.perf_counter()
                time.sleep(0.05)
                continue

            alvo = 1.0 / tps
            agora = time.perf_counter()
            if agora < proximo_tick:
                time.sleep(max(0.0, proximo_tick - agora))
                continue

            ticks_recuperacao = 0
            while ticks_recuperacao < 4 and agora >= proximo_tick:
                CEREBRO.executar_tick_servidor()
                PACOTES_TICK.fechar_tick()
                proximo_tick += alvo
                ticks_recuperacao += 1
                agora = time.perf_counter()

            if ticks_recuperacao >= 4 and agora > proximo_tick:
                proximo_tick = agora
            time.sleep(max(0.0, proximo_tick - time.perf_counter()))

    def bombear_ate_agora(self, max_ticks: int = 8) -> int:
        from SimuladorServerJogo.Mundo.Cerebros.CerebroCentral import CEREBRO

        with self._lock:
            if not self._modo_manual:
                return 0
            ativo = bool(self._ativo)
            tps = max(1.0, float(self._tps))
            if self._proximo_tick_manual is None:
                self._proximo_tick_manual = time.perf_counter()
            proximo_tick = float(self._proximo_tick_manual)

        agora = time.perf_counter()
        if not ativo or not CEREBRO.tem_players_ativos():
            with self._lock:
                self._proximo_tick_manual = agora
            return 0

        alvo = 1.0 / tps
        ticks_processados = 0
        while ticks_processados < max(1, int(max_ticks or 1)) and agora >= proximo_tick:
            CEREBRO.executar_tick_servidor()
            PACOTES_TICK.fechar_tick()
            proximo_tick += alvo
            ticks_processados += 1
            agora = time.perf_counter()

        if ticks_processados >= max(1, int(max_ticks or 1)) and agora > proximo_tick:
            proximo_tick = agora

        with self._lock:
            self._proximo_tick_manual = proximo_tick
        return ticks_processados

    def parar(self) -> None:
        with self._lock:
            self._ativo = False
            self._rodando = False
            self._proximo_tick_manual = None

    def info(self) -> dict:
        with self._lock:
            return {
                "ativo": bool(self._ativo),
                "rodando": bool(self._rodando),
                "tps": float(self._tps),
                "ativado_por": str(self._ativado_por or ""),
                "modo_manual": bool(self._modo_manual),
            }


TIQUE_SERVIDOR = TiqueServidor()
