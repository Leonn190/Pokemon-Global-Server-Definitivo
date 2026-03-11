"""Sistema de rede por pacotes de tick (thread única)."""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from Codigo.Server.ServerMundo import enviar_pacote_cliente_mundo


class SistemaPacotes:
    def __init__(self, controlador_objetos, controlador_player, leitor_mundo, camera) -> None:
        self._objetos = controlador_objetos
        self._player = controlador_player
        self._leitor = leitor_mundo
        self._camera = camera
        self._server_link: Optional[str] = None
        self._client_id = "anon"
        self._ultimo_tick_recebido = 0
        self._tick_cliente = 0
        self._thread: Optional[threading.Thread] = None
        self._ativo = False
        self._intervalo_s = 0.05
        self._pendentes_reenvio: List[Dict[str, object]] = []

    def configurar_conexao(self, server_link: str, client_id: str) -> None:
        self._server_link = str(server_link or "")
        self._client_id = str(client_id or "anon")

    def iniciar(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ativo = True
        self._thread = threading.Thread(target=self._loop_rede, name="SistemaPacotesTickThread", daemon=True)
        self._thread.start()

    def parar(self, timeout: float = 2.0) -> None:
        self._ativo = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _deduplicar_pacotes(self, pacotes: List[Dict[str, object]]) -> List[Dict[str, object]]:
        por_tick: Dict[int, Dict[str, object]] = {}
        sinteticos: List[Dict[str, object]] = []
        for p in pacotes:
            if not isinstance(p, dict):
                continue
            diffs = p.get("diffs", []) if isinstance(p.get("diffs"), list) else []
            if bool(p.get("sintetico", False)):
                base = dict(p)
                base["diffs"] = list(diffs)
                sinteticos.append(base)
                continue
            tick = int(p.get("tick", 0) or 0)
            if tick <= 0:
                continue
            if tick not in por_tick:
                base = dict(p)
                base["diffs"] = list(diffs)
                por_tick[tick] = base
                continue
            acumulado = por_tick[tick]
            diffs_existentes = acumulado.get("diffs", []) if isinstance(acumulado.get("diffs"), list) else []
            acumulado["diffs"] = list(diffs_existentes) + list(diffs)
        return [por_tick[t] for t in sorted(por_tick.keys())] + sinteticos

    def _obter_raio_chunks(self) -> int:
        if hasattr(self._leitor, "RaioChunks"):
            return max(1, int(getattr(self._leitor, "RaioChunks", 4) or 4))
        return max(1, int(getattr(self._leitor, "raio_chunks", 4) or 4))

    def _separar_eventos_updates(self, diffs: List[Dict[str, object]]):
        eventos = [d for d in diffs if isinstance(d, dict) and str(d.get("tipo", "")).strip().lower() == "evento"]
        updates = [d for d in diffs if isinstance(d, dict) and str(d.get("tipo", "")).strip().lower() != "evento"]
        return eventos, updates

    def _loop_rede(self) -> None:
        while self._ativo:
            if not self._server_link:
                time.sleep(self._intervalo_s)
                continue

            self._player.supervisionar_envio()
            envio_atual = self._objetos.ColetarDiffsRapidas()
            lote_envio = list(self._pendentes_reenvio) + list(envio_atual)
            eventos, updates = self._separar_eventos_updates(lote_envio)

            resposta = None
            sucesso_envio = False
            try:
                resposta = enviar_pacote_cliente_mundo(
                    self._server_link,
                    self._client_id,
                    ultimo_tick_recebido=int(self._ultimo_tick_recebido),
                    eventos=eventos,
                    updates=updates,
                    tick_cliente=int(self._tick_cliente),
                    posicao_camera=tuple(self._camera.PosicaoTiles),
                    raio_chunks=self._obter_raio_chunks(),
                )
                sucesso_envio = isinstance(resposta, dict) and str(resposta.get("status", "")).strip().lower() == "ok"
            except Exception:
                sucesso_envio = False
            self._tick_cliente += 1

            if not sucesso_envio:
                self._pendentes_reenvio = lote_envio
                time.sleep(self._intervalo_s)
                continue

            self._pendentes_reenvio = []
            if isinstance(resposta.get("chunks"), list):
                self._leitor.processar_pacote_chunks({"chunks": resposta.get("chunks", []), "meta": resposta.get("meta", {})})
            pacotes = resposta.get("pacotes", []) if isinstance(resposta.get("pacotes"), list) else []
            for pacote in self._deduplicar_pacotes(pacotes):
                if bool(pacote.get("sintetico", False)):
                    self._objetos.aplicar_pacote_tick(pacote)
                    continue
                tick = int(pacote.get("tick", 0) or 0)
                if tick <= 0 or tick <= self._ultimo_tick_recebido:
                    continue
                self._objetos.aplicar_pacote_tick(pacote)
                self._ultimo_tick_recebido = tick

            time.sleep(self._intervalo_s)
