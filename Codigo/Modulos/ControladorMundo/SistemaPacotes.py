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
        self._intervalo_s = 1.0 / 30.0
        self._pendentes_reenvio: List[Dict[str, object]] = []

    def configurar_conexao(self, server_link: str, client_id: str) -> None:
        self._server_link = str(server_link or "")
        self._client_id = str(client_id or "anon")
        self._objetos.definir_autor_local(self._client_id)
        self._player.definir_identidade_cliente(self._client_id)

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
                pacote_norm = dict(p)
                pacote_norm["diffs"] = list(diffs)
                sinteticos.append(pacote_norm)
                continue
            tick = int(p.get("tick", 0) or 0)
            if tick <= 0:
                continue
            if tick not in por_tick:
                pacote_norm = dict(p)
                pacote_norm["diffs"] = list(diffs)
                por_tick[tick] = pacote_norm
                continue
            acumulado = por_tick[tick]
            diffs_existentes = acumulado.get("diffs", []) if isinstance(acumulado.get("diffs"), list) else []
            acumulado["diffs"] = list(diffs_existentes) + list(diffs)
        return [por_tick[t] for t in sorted(por_tick.keys())] + sinteticos

    def _deve_aplicar_diff(self, diff: Dict[str, object]) -> bool:
        autor = str(diff.get("autor", "")).strip()
        if not autor:
            return True
        if autor.lower() == "server":
            return True
        return autor != self._client_id

    def _distribuir_pacote_tick(self, pacote: Dict[str, object]) -> None:
        diffs = pacote.get("diffs", []) if isinstance(pacote.get("diffs"), list) else []
        for diff in diffs:
            if not isinstance(diff, dict):
                continue
            if not self._deve_aplicar_diff(diff):
                continue
            if self._player.is_diff_player_local(diff):
                self._player.aplicar_diff_player(diff)
            else:
                self._objetos.aplicar_diff(diff)

    def _loop_rede(self) -> None:
        while self._ativo:
            if not self._server_link:
                time.sleep(self._intervalo_s)
                continue

            self._player.supervisionar_envio()
            envio_atual = self._objetos.ColetarDiffsRapidas()
            lote_envio = list(self._pendentes_reenvio) + list(envio_atual)

            resposta = None
            sucesso_envio = False
            try:
                resposta = enviar_pacote_cliente_mundo(
                    self._server_link,
                    self._client_id,
                    ultimo_tick_recebido=int(self._ultimo_tick_recebido),
                    diffs=lote_envio,
                    tick_cliente=int(self._tick_cliente),
                    posicao_camera=tuple(self._camera.PosicaoTiles),
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
            meta_resposta = resposta.get("meta") if isinstance(resposta.get("meta"), dict) else {}
            dimensao_meta = str(meta_resposta.get("dimensao") or "").strip()
            if dimensao_meta:
                self._player.forcar_dimensao_local(dimensao_meta)
            if isinstance(resposta.get("chunks"), list):
                self._leitor.processar_pacote_chunks({"chunks": resposta.get("chunks", []), "meta": meta_resposta})

            pacotes = resposta.get("pacotes", []) if isinstance(resposta.get("pacotes"), list) else []
            for pacote in self._deduplicar_pacotes(pacotes):
                if bool(pacote.get("sintetico", False)):
                    self._distribuir_pacote_tick(pacote)
                    continue
                tick = int(pacote.get("tick", 0) or 0)
                if tick <= 0 or tick <= self._ultimo_tick_recebido:
                    continue
                self._distribuir_pacote_tick(pacote)
                self._ultimo_tick_recebido = tick

            time.sleep(self._intervalo_s)
