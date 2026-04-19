from __future__ import annotations

import threading
import time
from typing import Dict, List, Tuple

from Codigo.ModulosGerais.ImagensMapa import GerenciadorImagensMapa
from Codigo.Server.ServerMundo import atualizar_mapa_mundo, coletar_mapa_mundo


class ServicoMapaMundo:
    def __init__(self, jogo, server_ip: str, client_id: str):
        self.jogo = jogo
        self.server_ip = str(server_ip or "")
        self.client_id = str(client_id or "anon")
        self.gerenciador = GerenciadorImagensMapa()
        self.meta: Dict[str, object] = {}
        self.vilas: List[dict] = []
        self.estadios: List[dict] = []
        self.regioes: List[dict] = []
        self._lock = threading.RLock()
        self._ultimo_delta = 0.0
        self.intervalo_delta_s = 2.0
        self._ativo = False
        self._worker = None
        self._worker_ativo = False
        self._worker_lock = threading.RLock()
        self._delta_pendente: list | None = None
        self._request_em_andamento = False

    def _posicao_camera(self) -> Tuple[float, float]:
        cena = getattr(self.jogo, "Cena", None)
        camera = getattr(cena, "Camera", None)
        pos = getattr(camera, "PosicaoTiles", (0.0, 0.0))
        return (float(pos[0]), float(pos[1]))

    def preparar_bootstrap(self, bootstrap: dict | None = None) -> dict:
        resp = bootstrap if isinstance(bootstrap, dict) else coletar_mapa_mundo(self.server_ip, self.client_id, self._posicao_camera())
        if not isinstance(resp, dict) or str(resp.get("status", "")) != "ok":
            return {"status": "erro"}
        with self._lock:
            self.meta = dict(resp.get("meta") or {})
            self.vilas = list(resp.get("vilas") or [])
            self.estadios = list(resp.get("estadios") or [])
            self.regioes = list(resp.get("regioes") or [])
            self.gerenciador.preparar(self.meta, explorados=resp.get("explorados"), regioes=self.regioes)
            self.gerenciador.aplicar_chunks(resp.get("atlas") if isinstance(resp.get("atlas"), list) else [])
            self._ativo = True
            self._ultimo_delta = time.monotonic()
            self._iniciar_worker()
        return resp

    def tick(self) -> None:
        if not self._ativo or not self.server_ip:
            return
        self._consumir_delta_pronto()
        agora = time.monotonic()
        if (agora - self._ultimo_delta) < self.intervalo_delta_s:
            return
        with self._worker_lock:
            if self._request_em_andamento:
                return
            self._request_em_andamento = True
            self._ultimo_delta = agora

    def _iniciar_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker_ativo = True
        self._worker = threading.Thread(target=self._loop_worker_delta, name="ServicoMapaDeltaWorker", daemon=True)
        self._worker.start()

    def _loop_worker_delta(self) -> None:
        while self._worker_ativo:
            precisa = False
            with self._worker_lock:
                precisa = bool(self._request_em_andamento)
            if not precisa:
                time.sleep(0.08)
                continue
            pos = self._posicao_camera()
            resp = atualizar_mapa_mundo(self.server_ip, self.client_id, pos, conhecidos=None)
            atlas = resp.get("atlas") if isinstance(resp, dict) and isinstance(resp.get("atlas"), list) else []
            with self._worker_lock:
                self._delta_pendente = atlas
                self._request_em_andamento = False

    def _consumir_delta_pronto(self) -> None:
        atlas = None
        with self._worker_lock:
            if self._delta_pendente is not None:
                atlas = self._delta_pendente
                self._delta_pendente = None
        if isinstance(atlas, list) and atlas:
            self.gerenciador.aplicar_chunks(atlas)

    def encerrar(self) -> None:
        self._consumir_delta_pronto()
        with self._lock:
            self._ativo = False
            self._worker_ativo = False
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=1.5)
        self._worker = None
        self.gerenciador.flush()
        with self._lock:
            self.gerenciador.limpar()
