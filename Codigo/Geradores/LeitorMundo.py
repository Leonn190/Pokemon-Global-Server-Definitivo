"""Leitor de mundo do cliente para sincronizar chunks e objetos remotos."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from Codigo.Geradores.EstruturaNaturais import EstruturaNatural

Vector2 = Tuple[float, float]
PacoteMundo = Dict[str, object]


class LeitorMundo:
    """Thread que busca atualizações do servidor e popula o mundo do cliente."""

    def __init__(
        self,
        jogo,
        entidade_main,
        callback_atualizacao: Callable[[str, Vector2], Optional[PacoteMundo]],
        intervalo_poll: float = 0.20,
    ) -> None:
        self.JOGO = jogo
        self.EntidadeMain = entidade_main
        self.CallbackAtualizacao = callback_atualizacao
        self.IntervaloPoll = max(0.05, float(intervalo_poll))

        self.ServerLink: Optional[str] = None
        self.Chunks: Dict[Tuple[int, int], List[List[int]]] = {}
        self.ObjetosMundo: Dict[int, object] = {}
        self.Entidades: List[object] = []
        self.Estruturas: List[EstruturaNatural] = []

        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._ativo = False

    def conectar_servidor(self, link_servidor: str) -> None:
        """Conecta leitor ao servidor e registra link no controlador de cenas."""
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

    def _loop(self) -> None:
        while self._ativo:
            if self.ServerLink is None:
                time.sleep(self.IntervaloPoll)
                continue

            pacote = self._coletar_estado_servidor()
            if pacote:
                self._aplicar_pacote(pacote)
            time.sleep(self.IntervaloPoll)

    def _coletar_estado_servidor(self) -> Optional[PacoteMundo]:
        pos_main = getattr(self.EntidadeMain, "Posicao", (0.0, 0.0))
        try:
            return self.CallbackAtualizacao(self.ServerLink, pos_main)
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

            self.Entidades = [obj for obj in pacote.get("entidades", [])]

            estruturas = []
            for dados in pacote.get("estruturas", []):
                estrutura = EstruturaNatural(
                    tipo=dados.get("tipo", "estrutura"),
                    posicao=tuple(dados.get("posicao", (0.0, 0.0))),
                    recursos=dados.get("recursos", {}),
                    raio_colisao=float(dados.get("raio_colisao", 16.0)),
                    raio_interacao=float(dados.get("raio_interacao", 20.0)),
                    id_objeto=dados.get("id"),
                )
                estruturas.append(estrutura)

            self.Estruturas = estruturas
            self.ObjetosMundo = {}
            for entidade in self.Entidades:
                entidade_id = getattr(entidade, "Id", None)
                if entidade_id is not None:
                    self.ObjetosMundo[entidade_id] = entidade
            for estrutura in self.Estruturas:
                self.ObjetosMundo[estrutura.Id] = estrutura

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "chunks": dict(self.Chunks),
                "entidades": list(self.Entidades),
                "estruturas": list(self.Estruturas),
                "objetos": dict(self.ObjetosMundo),
            }
