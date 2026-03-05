"""Leitor de mundo do cliente para sincronizar chunks e objetos remotos via diffs."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from Codigo.Geradores.EstruturaNaturais import EstruturaNatural

Vector2 = Tuple[float, float]
PacoteMundo = Dict[str, object]


class LeitorMundo:
    """Thread que busca atualizações do servidor e popula o mundo do cliente."""

    def __init__(
        self,
        jogo,
        entidade_main,
        callback_atualizacao: Callable[[str, str, Vector2], Optional[PacoteMundo]],
        callback_envio_diffs: Optional[Callable[[str, str, List[Dict[str, object]]], Optional[Dict[str, object]]]] = None,
        intervalo_poll: float = 0.20,
    ) -> None:
        self.JOGO = jogo
        self.EntidadeMain = entidade_main
        self.CallbackAtualizacao = callback_atualizacao
        self.CallbackEnvioDiffs = callback_envio_diffs
        self.IntervaloPoll = max(0.05, float(intervalo_poll))

        self.ServerLink: Optional[str] = None
        self.ClientId = str(getattr(jogo, "INFO", {}).get("UsuarioLogado", "anon"))
        self.Chunks: Dict[Tuple[int, int], List[List[int]]] = {}
        self.ObjetosMundo: Dict[int, Dict[str, object]] = {}
        self.Entidades: List[Dict[str, object]] = []
        self.Estruturas: List[Dict[str, object]] = []

        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._ativo = False
        self._fila_diffs_envio: List[Dict[str, object]] = []

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
        pos_main = getattr(self.EntidadeMain, "Posicao", (0.0, 0.0))
        try:
            return self.CallbackAtualizacao(self.ServerLink, self.ClientId, pos_main)
        except Exception:
            return None

    def _aplicar_pacote(self, pacote: PacoteMundo) -> None:
        with self._lock:
            for chunk in pacote.get("chunks", []):
                pos = chunk.get("pos")
                grid = chunk.get("grid", [])
                if pos is None:
                    continue
                self.Chunks[(int(pos[0]), int(pos[1]))] = [list(linha) for linha in grid]

            for diff in pacote.get("diffs", []):
                self._aplicar_diff(diff)

            self.Entidades = [o for o in self.ObjetosMundo.values() if str(o.get("tipo", "")).startswith("entidade")]
            self.Estruturas = [o for o in self.ObjetosMundo.values() if str(o.get("tipo", "")).startswith("estrutura")]

    def _aplicar_diff(self, diff: Dict[str, object]) -> None:
        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload", {}), dict) else {}

        if tipo == "spawn":
            dados_obj = payload
            oid = int(dados_obj.get("id", objeto_id))
            self.ObjetosMundo[oid] = dict(dados_obj)
            return

        if objeto_id is None:
            return

        oid = int(objeto_id)
        if tipo == "update":
            atual = self.ObjetosMundo.get(oid, {"id": oid})
            if "estado" in payload and isinstance(payload.get("estado"), dict):
                base_estado = atual.get("estado", {}) if isinstance(atual.get("estado"), dict) else {}
                base_estado.update(payload["estado"])
                atual["estado"] = base_estado
            for chave, valor in payload.items():
                if chave == "estado":
                    continue
                atual[chave] = valor
            self.ObjetosMundo[oid] = atual
            return

        if tipo == "despawn":
            self.ObjetosMundo.pop(oid, None)

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "chunks": dict(self.Chunks),
                "entidades": list(self.Entidades),
                "estruturas": list(self.Estruturas),
                "objetos": dict(self.ObjetosMundo),
            }
