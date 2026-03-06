"""Leitor de mundo do cliente para sincronizar chunks e objetos remotos via diffs."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

import pygame

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
        self.TamanhoChunkBlocos = 32
        self.CoresBlocos = {
            0: (14, 40, 92),
            1: (72, 162, 231),
            2: (230, 210, 146),
            3: (124, 204, 108),
            4: (56, 128, 64),
        }
        self._cache_superficies_chunks: Dict[Tuple[int, int], pygame.Surface] = {}
        self._cache_tile_px: int = max(1, int(getattr(self.Camera, "TilePx", 50)))

    def atualizar_regras_mundo(self, player_controle=None) -> None:
        estado = self.snapshot()
        meta = estado.get("meta", {}) if isinstance(estado, dict) else {}
        if not isinstance(meta, dict):
            meta = {}

        largura = meta.get("largura_blocos")
        altura = meta.get("altura_blocos")

        if largura is not None and altura is not None:
            if player_controle is not None:
                player_controle.definir_limites_mundo(largura, altura)
            if self.Camera is not None:
                self.Camera.definir_limites_mundo(largura, altura)

        if player_controle is not None:
            chunks = estado.get("chunks", {}) if isinstance(estado, dict) else {}
            if not isinstance(chunks, dict):
                chunks = {}
            player_controle.definir_grid_chunks(chunks, self.TamanhoChunkBlocos)

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
                chunk_tamanho = meta.get("chunk_tamanho", meta.get("chunk_blocos"))
                if chunk_tamanho is not None:
                    self.TamanhoChunkBlocos = max(1, int(chunk_tamanho))

            chunks_atuais: Dict[Tuple[int, int], List[List[int]]] = {}
            chunks_recebidos = pacote.get("chunks", [])

            if isinstance(chunks_recebidos, dict):
                for chave, grid in chunks_recebidos.items():
                    if not isinstance(chave, (list, tuple)) or len(chave) != 2:
                        continue
                    try:
                        chunk_x = int(chave[0])
                        chunk_y = int(chave[1])
                    except (TypeError, ValueError):
                        continue
                    chunks_atuais[(chunk_x, chunk_y)] = [list(linha) for linha in (grid or [])]
            else:
                for chunk in chunks_recebidos:
                    if not isinstance(chunk, dict):
                        continue
                    pos = chunk.get("pos")
                    grid = chunk.get("grid", [])
                    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                        continue
                    try:
                        chunk_x = int(pos[0])
                        chunk_y = int(pos[1])
                    except (TypeError, ValueError):
                        continue
                    chunks_atuais[(chunk_x, chunk_y)] = [list(linha) for linha in grid]
            if chunks_atuais:
                self.Chunks.update(chunks_atuais)
                for chave_chunk in chunks_atuais:
                    self._cache_superficies_chunks.pop(chave_chunk, None)
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

    def _obter_superficie_chunk(self, chave_chunk: Tuple[int, int], grid: List[List[int]], tile_px: int) -> Optional[pygame.Surface]:
        if not grid:
            return None

        largura_chunk = max((len(linha) for linha in grid), default=0)
        altura_chunk = len(grid)
        if largura_chunk <= 0 or altura_chunk <= 0:
            return None

        if tile_px != self._cache_tile_px:
            self._cache_superficies_chunks.clear()
            self._cache_tile_px = tile_px

        superficie = self._cache_superficies_chunks.get(chave_chunk)
        if superficie is not None:
            return superficie

        largura_px = largura_chunk * tile_px
        altura_px = altura_chunk * tile_px
        superficie = pygame.Surface((largura_px, altura_px)).convert()

        for by, linha in enumerate(grid):
            for bx, bloco in enumerate(linha):
                cor = self.CoresBlocos.get(int(bloco), (255, 0, 255))
                pygame.draw.rect(superficie, cor, (bx * tile_px, by * tile_px, tile_px, tile_px))

        self._cache_superficies_chunks[chave_chunk] = superficie
        return superficie

    def renderizar_mundo(self, tela, gerenciador_fps=None) -> None:
        if gerenciador_fps is not None:
            gerenciador_fps.iniciar_trecho("carregar_chunks")

        estado = self.snapshot()
        chunks = estado.get("chunks", {}) if isinstance(estado, dict) else {}
        if not isinstance(chunks, dict) or not chunks:
            if gerenciador_fps is not None:
                gerenciador_fps.finalizar_trecho("carregar_chunks")
            return

        tile_px = max(1, int(getattr(self.Camera, "TilePx", 50)))
        tamanho_chunk = max(1, int(self.TamanhoChunkBlocos))

        player = getattr(self.Camera, "EntidadeMain", None)
        pos_player = getattr(player, "Posicao", (0.0, 0.0))
        try:
            chunk_player_x = int(float(pos_player[0]) // tamanho_chunk)
            chunk_player_y = int(float(pos_player[1]) // tamanho_chunk)
        except Exception:
            chunk_player_x = 0
            chunk_player_y = 0

        meta = estado.get("meta", {}) if isinstance(estado, dict) else {}
        if not isinstance(meta, dict):
            meta = {}
        largura_blocos = meta.get("largura_blocos")
        altura_blocos = meta.get("altura_blocos")
        try:
            total_chunks_x = max(1, int(float(largura_blocos) / float(tamanho_chunk))) if largura_blocos is not None else None
        except Exception:
            total_chunks_x = None
        try:
            total_chunks_y = max(1, int(float(altura_blocos) / float(tamanho_chunk))) if altura_blocos is not None else None
        except Exception:
            total_chunks_y = None

        limites = getattr(self.Camera, "LimitesMundoTiles", None)
        repeticoes_x = (0.0,)
        repeticoes_y = (0.0,)
        if limites:
            largura, altura = limites
            repeticoes_x = (-float(largura), 0.0, float(largura))
            repeticoes_y = (-float(altura), 0.0, float(altura))

        draw_ops = []
        for dy in range(-2, 3):
            chunk_raw_y = chunk_player_y + dy
            chunk_busca_y = (chunk_raw_y % total_chunks_y) if total_chunks_y else chunk_raw_y
            for dx in range(-2, 3):
                chunk_raw_x = chunk_player_x + dx
                chunk_busca_x = (chunk_raw_x % total_chunks_x) if total_chunks_x else chunk_raw_x

                chave_chunk = (chunk_busca_x, chunk_busca_y)
                grid = chunks.get(chave_chunk)
                if not grid:
                    continue

                superficie_chunk = self._obter_superficie_chunk(chave_chunk, grid, tile_px)
                if superficie_chunk is None:
                    continue

                origem_x = chunk_raw_x * tamanho_chunk
                origem_y = chunk_raw_y * tamanho_chunk
                draw_ops.append((superficie_chunk, origem_x, origem_y))

        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("carregar_chunks")
            gerenciador_fps.iniciar_trecho("renderizar_tiles")

        tela_w, tela_h = tela.get_size()
        for superficie_chunk, origem_x, origem_y in draw_ops:
            largura_px = superficie_chunk.get_width()
            altura_px = superficie_chunk.get_height()
            for off_x in repeticoes_x:
                for off_y in repeticoes_y:
                    px, py = self.Camera.mundo_para_tela_px((origem_x + off_x, origem_y + off_y))
                    if px > tela_w or py > tela_h or (px + largura_px) < 0 or (py + altura_px) < 0:
                        continue
                    tela.blit(superficie_chunk, (int(px), int(py)))

        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("renderizar_tiles")
