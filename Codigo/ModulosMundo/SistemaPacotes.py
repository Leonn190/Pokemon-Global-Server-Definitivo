"""Sistema de rede por pacotes de tick (thread única)."""

from __future__ import annotations

import threading
import time
from collections import deque
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
        self._modo_manual = False
        self._proximo_ciclo_manual = 0.0
        self._intervalo_s = 1.0 / 30.0
        self._pendentes_reenvio: List[Dict[str, object]] = []
        self._tempo_mundo: Dict[str, object] = {}
        self._diffs_seq_recentes = deque(maxlen=4096)
        self._diffs_seq_cache = set()

    def configurar_conexao(self, server_link: str, client_id: str) -> None:
        self._server_link = str(server_link or "")
        self._client_id = str(client_id or "anon")
        self._objetos.definir_autor_local(self._client_id)
        self._player.definir_identidade_cliente(self._client_id)

    def iniciar(self) -> None:
        if self._modo_manual:
            self._ativo = True
            self._proximo_ciclo_manual = time.perf_counter()
            return
        if self._thread and self._thread.is_alive():
            return
        self._ativo = True
        self._thread = threading.Thread(target=self._loop_rede, name="SistemaPacotesTickThread", daemon=True)
        self._thread.start()

    def parar(self, timeout: float = 2.0) -> None:
        self._ativo = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def ativar_bombeamento_manual(self, ativo: bool) -> None:
        thread = None
        self._modo_manual = bool(ativo)
        self._proximo_ciclo_manual = time.perf_counter()
        if self._modo_manual:
            self._ativo = False
            thread = self._thread
            self._thread = None
        if thread and thread.is_alive():
            thread.join(timeout=0.2)
        self._ativo = True

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

    def _ja_aplicou_seq(self, seq: int) -> bool:
        return int(seq or 0) in self._diffs_seq_cache

    def _registrar_seq_aplicada(self, seq: int) -> None:
        seq_int = int(seq or 0)
        if seq_int <= 0 or seq_int in self._diffs_seq_cache:
            return
        if len(self._diffs_seq_recentes) >= self._diffs_seq_recentes.maxlen:
            antigo = int(self._diffs_seq_recentes[0])
            self._diffs_seq_cache.discard(antigo)
        self._diffs_seq_recentes.append(seq_int)
        self._diffs_seq_cache.add(seq_int)

    def _distribuir_pacote_tick(self, pacote: Dict[str, object]) -> None:
        diffs = pacote.get("diffs", []) if isinstance(pacote.get("diffs"), list) else []
        for diff in diffs:
            if not isinstance(diff, dict):
                continue
            seq = int(diff.get("seq", 0) or 0)
            if seq > 0 and self._ja_aplicou_seq(seq):
                continue
            if not self._deve_aplicar_diff(diff):
                continue
            if self._player.is_diff_player_local(diff):
                self._player.aplicar_diff_player(diff)
            else:
                self._objetos.aplicar_diff(diff)
            self._registrar_seq_aplicada(seq)

    def _posicao_referencia_envio(self) -> tuple[float, float]:
        try:
            pos = self._leitor.posicao_referencia()
            return (float(pos[0]), float(pos[1]))
        except Exception:
            try:
                pos = getattr(self._camera, "PosicaoTiles", (0.0, 0.0))
                return (float(pos[0]), float(pos[1]))
            except Exception:
                return (0.0, 0.0)

    def _loop_rede(self) -> None:
        proximo_ciclo = time.perf_counter()
        while self._ativo:
            proximo_ciclo += self._intervalo_s
            if not self._server_link:
                agora = time.perf_counter()
                time.sleep(max(0.0, proximo_ciclo - agora))
                continue

            if not self._executar_ciclo_rede():
                agora = time.perf_counter()
                if proximo_ciclo < agora - self._intervalo_s:
                    proximo_ciclo = agora
                time.sleep(max(0.0, proximo_ciclo - agora))
                continue

            agora = time.perf_counter()
            if proximo_ciclo < agora - self._intervalo_s:
                proximo_ciclo = agora
            time.sleep(max(0.0, proximo_ciclo - agora))

    def bombear(self, max_ciclos: int = 4) -> None:
        if not self._modo_manual or not self._ativo:
            return
        if not self._server_link:
            self._proximo_ciclo_manual = time.perf_counter()
            return
        if self._proximo_ciclo_manual <= 0.0:
            self._proximo_ciclo_manual = time.perf_counter()
        agora = time.perf_counter()
        ciclos = 0
        while ciclos < max(1, int(max_ciclos or 1)) and agora >= self._proximo_ciclo_manual:
            self._executar_ciclo_rede()
            self._proximo_ciclo_manual += self._intervalo_s
            ciclos += 1
            agora = time.perf_counter()
        if ciclos >= max(1, int(max_ciclos or 1)) and agora > self._proximo_ciclo_manual:
            self._proximo_ciclo_manual = agora

    def _executar_ciclo_rede(self) -> bool:
        self._player.supervisionar_envio()
        envio_atual = self._objetos.ColetarDiffsRapidas()
        lote_envio = list(self._pendentes_reenvio) + list(envio_atual)
        posicao_ref = self._posicao_referencia_envio()

        resposta = None
        sucesso_envio = False
        try:
            resposta = enviar_pacote_cliente_mundo(
                self._server_link,
                self._client_id,
                ultimo_tick_recebido=int(self._ultimo_tick_recebido),
                diffs=lote_envio,
                tick_cliente=int(self._tick_cliente),
                posicao_camera=posicao_ref,
            )
            sucesso_envio = isinstance(resposta, dict) and str(resposta.get("status", "")).strip().lower() == "ok"
        except Exception:
            sucesso_envio = False
        self._tick_cliente += 1

        if not sucesso_envio:
            self._pendentes_reenvio = lote_envio
            return False

        self._pendentes_reenvio = []
        self.aplicar_meta_servidor(resposta.get("meta"))
        if isinstance(resposta.get("chunks"), list):
            self._leitor.processar_pacote_chunks({"chunks": resposta.get("chunks", []), "meta": resposta.get("meta", {})})

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
        return True

    def tempo_mundo_atual(self) -> Dict[str, object]:
        return dict(self._tempo_mundo)

    def aplicar_meta_servidor(self, meta: object) -> None:
        dados = meta if isinstance(meta, dict) else {}
        tempo_mundo = dados.get("tempo_mundo") if isinstance(dados.get("tempo_mundo"), dict) else None
        if isinstance(tempo_mundo, dict):
            self._tempo_mundo = dict(tempo_mundo)
