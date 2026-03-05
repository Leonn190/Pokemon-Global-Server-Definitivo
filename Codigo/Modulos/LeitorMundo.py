"""Leitor de mundo do cliente para sincronizar chunks e objetos remotos via diffs."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

Vector2 = Tuple[float, float]
PacoteMundo = Dict[str, object]


class LeitorMundo:
    def __init__(
        self,
        jogo,
        camera,
        callback_atualizacao: Callable[[str, str, Vector2, int], Optional[PacoteMundo]],
        callback_envio_diffs: Optional[Callable[[str, str, List[Dict[str, object]]], Optional[Dict[str, object]]]] = None,
        intervalo_poll: float = 0.20,
        raio_chunks: int = 2,
    ) -> None:
        self.JOGO = jogo
        self.Camera = camera
        self.CallbackAtualizacao = callback_atualizacao
        self.CallbackEnvioDiffs = callback_envio_diffs
        self.IntervaloPoll = max(0.05, float(intervalo_poll))
        self.RaioChunks = max(1, int(raio_chunks))

        self.ServerLink: Optional[str] = None
        self.ClientId = str(getattr(jogo, "INFO", {}).get("UsuarioLogado", "anon"))
        self.Chunks: Dict[Tuple[int, int], List[List[int]]] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._ativo = False
        self._fila_diffs_envio: List[Dict[str, object]] = []
        self._diffs_recebidas: List[Dict[str, object]] = []
        self._versao_chunks = 0
        self.MetaMundo: Dict[str, object] = {}

    def conectar_servidor(self, link_servidor: str) -> None:
        self.ServerLink = str(link_servidor)
        if hasattr(self.JOGO, "INFO") and isinstance(self.JOGO.INFO, dict):
            self.JOGO.INFO["ServerLink"] = self.ServerLink

    def iniciar(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ativo = True
        self._thread = threading.Thread(target=self._loop, name="LeitorMundoThread", daemon=True)
        self._thread.start()

    def parar(self, timeout: float = 2.0) -> None:
        self._ativo = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def enfileirar_diff(self, diff: Dict[str, object]) -> None:
        if not isinstance(diff, dict):
            return
        with self._lock:
            self._fila_diffs_envio.append(diff)

    def consumir_diffs_recebidas(self) -> List[Dict[str, object]]:
        with self._lock:
            diffs = list(self._diffs_recebidas)
            self._diffs_recebidas.clear()
            return diffs

    def _loop(self) -> None:
        while self._ativo:
            if self.ServerLink is None:
                time.sleep(self.IntervaloPoll)
                continue

            self._enviar_diffs_pendentes()
            pacote = self._coletar_estado_servidor()
            if pacote:
                self._aplicar_pacote(pacote)
            time.sleep(self.IntervaloPoll)

    def _enviar_diffs_pendentes(self) -> None:
        if self.CallbackEnvioDiffs is None or self.ServerLink is None:
            return
        with self._lock:
            if not self._fila_diffs_envio:
                return
            diffs = list(self._fila_diffs_envio)
            self._fila_diffs_envio.clear()
        try:
            self.CallbackEnvioDiffs(self.ServerLink, self.ClientId, diffs)
        except Exception:
            with self._lock:
                self._fila_diffs_envio = diffs + self._fila_diffs_envio

    def _coletar_estado_servidor(self) -> Optional[PacoteMundo]:
        pos_camera = getattr(self.Camera, "PosicaoTiles", (0.0, 0.0))
        try:
            return self.CallbackAtualizacao(self.ServerLink, self.ClientId, pos_camera, self.RaioChunks)
        except Exception:
            return None

    def _aplicar_pacote(self, pacote: PacoteMundo) -> None:
        with self._lock:
            meta = pacote.get("meta", {})
            if isinstance(meta, dict):
                self.MetaMundo.update(meta)

            for chunk in pacote.get("chunks", []):
                pos = chunk.get("pos")
                grid = chunk.get("grid", [])
                if pos is None:
                    continue
                self.Chunks[(int(pos[0]), int(pos[1]))] = [list(linha) for linha in grid]
                self._versao_chunks += 1

            for diff in pacote.get("diffs", []):
                if not isinstance(diff, dict):
                    continue
                if str(diff.get("tipo", "")).lower() == "chunk":
                    continue
                self._diffs_recebidas.append(dict(diff))

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "chunks": dict(self.Chunks),
                "versao_chunks": int(self._versao_chunks),
                "meta": dict(self.MetaMundo),
            }
