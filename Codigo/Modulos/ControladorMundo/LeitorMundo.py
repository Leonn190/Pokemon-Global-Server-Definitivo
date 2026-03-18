"""Leitor de mundo do cliente para sincronizar chunks do anel ativo."""

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
        intervalo_poll: float = 0.20,
        raio_chunks: int = 3,
    ) -> None:
        self.JOGO = jogo
        self.Camera = camera
        self.CallbackAtualizacao = callback_atualizacao
        self.IntervaloPoll = max(0.05, float(intervalo_poll))
        self.RaioChunks = max(1, int(raio_chunks))

        self.ServerLink: Optional[str] = None
        self.ClientId = str(getattr(jogo, "INFO", {}).get("UsuarioLogado", "anon"))
        self.Chunks: Dict[Tuple[int, int], List[List[int]]] = {}
        self._lock = threading.Lock()

        self._thread_chunks: Optional[threading.Thread] = None
        self._ativo_chunks = False
        self._versao_chunks = 0
        self.MetaMundo: Dict[str, object] = {}
        self.TamanhoChunkBlocos = 10
        self.CoresBlocos = {0: (24, 72, 145), 1: (64, 156, 255), 2: (106, 190, 48), 3: (46, 125, 50), 4: (230, 210, 140), 5: (217, 179, 92), 6: (245, 248, 252), 7: (140, 82, 255), 8: (88, 70, 70), 9: (110, 92, 68)}

        self._cache_superficies_chunks: Dict[Tuple[int, int], pygame.Surface] = {}
        self._cache_assinaturas_chunks: Dict[Tuple[int, int], Tuple[Tuple[int, ...], ...]] = {}
        self._cache_tile_px: int = max(1, int(getattr(self.Camera, "TilePx", 50)))
        self._ultimo_chunk_player: Optional[Tuple[int, int]] = None
        self._ultima_versao_chunks_regras = -1

    def atualizar_regras_mundo(self, player_controle=None) -> None:
        with self._lock:
            meta = dict(self.MetaMundo)
            versao_chunks = int(self._versao_chunks)
            chunk_tamanho = int(self.TamanhoChunkBlocos)
            chunks_atualizados = None
            if player_controle is not None and versao_chunks != self._ultima_versao_chunks_regras:
                chunks_atualizados = dict(self.Chunks)
                self._ultima_versao_chunks_regras = versao_chunks

        largura = meta.get("largura_blocos")
        altura = meta.get("altura_blocos")
        if largura is not None and altura is not None:
            if player_controle is not None:
                player_controle.definir_limites_mundo(largura, altura)
            if self.Camera is not None:
                self.Camera.definir_limites_mundo(largura, altura)

        if player_controle is not None and chunks_atualizados is not None:
            player_controle.definir_grid_chunks(chunks_atualizados, chunk_tamanho)

    def conectar_servidor(self, link_servidor: str) -> None:
        self.ServerLink = str(link_servidor)
        if hasattr(self.JOGO, "INFO") and isinstance(self.JOGO.INFO, dict):
            self.JOGO.INFO["ServerLink"] = self.ServerLink

    def iniciar(self) -> None:
        if self._thread_chunks and self._thread_chunks.is_alive():
            return
        self._ativo_chunks = True
        self._thread_chunks = threading.Thread(target=self._loop_chunks, name="LeitorMundoChunksThread", daemon=True)
        self._thread_chunks.start()

    def parar(self, timeout: float = 2.0) -> None:
        self._ativo_chunks = False
        if self._thread_chunks and self._thread_chunks.is_alive():
            self._thread_chunks.join(timeout=timeout)

    def _chunk_atual_player(self) -> Tuple[int, int]:
        pos_camera = getattr(self.Camera, "PosicaoTiles", (0.0, 0.0))
        tamanho = max(1, int(self.TamanhoChunkBlocos))
        try:
            return (int(float(pos_camera[0]) // tamanho), int(float(pos_camera[1]) // tamanho))
        except Exception:
            return (0, 0)

    def _loop_chunks(self) -> None:
        while self._ativo_chunks:
            if self.ServerLink is None:
                time.sleep(self.IntervaloPoll)
                continue
            chunk_player = self._chunk_atual_player()
            if self._ultimo_chunk_player is not None and chunk_player == self._ultimo_chunk_player:
                time.sleep(self.IntervaloPoll)
                continue
            pacote = self._coletar_chunks_servidor()
            if pacote:
                self.processar_pacote_chunks(pacote)
                self._ultimo_chunk_player = chunk_player
            time.sleep(self.IntervaloPoll)

    def _coletar_chunks_servidor(self) -> Optional[PacoteMundo]:
        pos_camera = getattr(self.Camera, "PosicaoTiles", (0.0, 0.0))
        try:
            return self.CallbackAtualizacao(self.ServerLink, self.ClientId, tuple(pos_camera), int(self.RaioChunks))
        except Exception:
            return None

    def descartar_chunks_fora_do_anel(self) -> None:
        with self._lock:
            chaves_anel = set(self.Chunks.keys())
            for chave in list(self._cache_superficies_chunks.keys()):
                if chave not in chaves_anel:
                    self._cache_superficies_chunks.pop(chave, None)
            for chave in list(self._cache_assinaturas_chunks.keys()):
                if chave not in chaves_anel:
                    self._cache_assinaturas_chunks.pop(chave, None)

    def processar_pacote_chunks(self, pacote: PacoteMundo) -> None:
        if not isinstance(pacote, dict):
            return
        with self._lock:
            meta_alterada = False
            meta = pacote.get("meta") if isinstance(pacote.get("meta"), dict) else {}
            for chave_meta in ("largura_blocos", "altura_blocos", "raio_chunks_ativo"):
                valor_meta = meta.get(chave_meta)
                if valor_meta is not None and self.MetaMundo.get(chave_meta) != valor_meta:
                    self.MetaMundo[chave_meta] = valor_meta
                    meta_alterada = True
            chunk_tamanho = meta.get("chunk_tamanho", meta.get("chunk_blocos"))
            if chunk_tamanho is not None:
                chunk_tamanho_novo = max(1, int(chunk_tamanho))
                if chunk_tamanho_novo != self.TamanhoChunkBlocos:
                    self.TamanhoChunkBlocos = chunk_tamanho_novo
                    self._cache_superficies_chunks.clear()
                    self._cache_assinaturas_chunks.clear()
                    meta_alterada = True

            chunks_atuais: Dict[Tuple[int, int], List[List[int]]] = {}
            chunks_recebidos = pacote.get("chunks", [])
            if isinstance(chunks_recebidos, dict):
                for chave, grid in chunks_recebidos.items():
                    if not isinstance(chave, (list, tuple)) or len(chave) != 2:
                        continue
                    try:
                        chunk_x = int(chave[0]); chunk_y = int(chave[1])
                    except (TypeError, ValueError):
                        continue
                    chunks_atuais[(chunk_x, chunk_y)] = [list(linha) for linha in (grid or [])]
            else:
                for chunk in chunks_recebidos:
                    if not isinstance(chunk, dict):
                        continue
                    pos = chunk.get("pos"); grid = chunk.get("grid", [])
                    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                        continue
                    try:
                        chunk_x = int(pos[0]); chunk_y = int(pos[1])
                    except (TypeError, ValueError):
                        continue
                    chunks_atuais[(chunk_x, chunk_y)] = [list(linha) for linha in grid]

            chaves_atuais = set(self.Chunks.keys())
            chaves_novas = set(chunks_atuais.keys())
            houve_alteracao_chunks = bool(chaves_atuais != chaves_novas)
            for chave in (chaves_atuais - chaves_novas):
                self._cache_superficies_chunks.pop(chave, None)
                self._cache_assinaturas_chunks.pop(chave, None)
            for chave in chaves_novas:
                grid_novo = chunks_atuais[chave]
                assinatura_nova = tuple(tuple(int(bloco) for bloco in linha) for linha in grid_novo)
                assinatura_antiga = self._cache_assinaturas_chunks.get(chave)
                if assinatura_antiga != assinatura_nova:
                    self._cache_superficies_chunks.pop(chave, None)
                    self._cache_assinaturas_chunks[chave] = assinatura_nova
                    houve_alteracao_chunks = True
            self.Chunks = chunks_atuais
            if houve_alteracao_chunks or meta_alterada:
                self._versao_chunks += 1
        self.descartar_chunks_fora_do_anel()

    def _obter_superficie_chunk(self, chave_chunk: Tuple[int, int], grid: List[List[int]], tile_px: int) -> Optional[pygame.Surface]:
        if not grid:
            return None
        largura_chunk = max((len(linha) for linha in grid), default=0)
        altura_chunk = len(grid)
        if largura_chunk <= 0 or altura_chunk <= 0:
            return None
        if tile_px != self._cache_tile_px:
            self._cache_superficies_chunks.clear(); self._cache_assinaturas_chunks.clear(); self._cache_tile_px = tile_px
        superficie = self._cache_superficies_chunks.get(chave_chunk)
        if superficie is not None:
            return superficie
        superficie = pygame.Surface((largura_chunk * tile_px, altura_chunk * tile_px)).convert()
        for by, linha in enumerate(grid):
            for bx, bloco in enumerate(linha):
                pygame.draw.rect(superficie, self.CoresBlocos.get(int(bloco), (255, 0, 255)), (bx * tile_px, by * tile_px, tile_px, tile_px))
        self._cache_superficies_chunks[chave_chunk] = superficie
        return superficie

    def renderizar_mundo(self, tela) -> None:
        tile_px = max(1, int(getattr(self.Camera, "TilePx", 50)))
        player = getattr(self.Camera, "EntidadeMain", None)
        pos_player = getattr(player, "Posicao", (0.0, 0.0))
        with self._lock:
            tamanho_chunk = max(1, int(self.TamanhoChunkBlocos)); meta = dict(self.MetaMundo); chunks_ref = self.Chunks
        try:
            chunk_player_x = int(float(pos_player[0]) // tamanho_chunk); chunk_player_y = int(float(pos_player[1]) // tamanho_chunk)
        except Exception:
            chunk_player_x = 0; chunk_player_y = 0
        if not chunks_ref:
            return
        try:
            raio_render_chunks = max(1, int(meta.get("raio_chunks_ativo", self.RaioChunks)))
        except Exception:
            raio_render_chunks = max(1, int(self.RaioChunks))

        chaves_visiveis = [((chunk_player_x + dx, chunk_player_y + dy), chunk_player_x + dx, chunk_player_y + dy)
                           for dy in range(-raio_render_chunks, raio_render_chunks + 1)
                           for dx in range(-raio_render_chunks, raio_render_chunks + 1)]
        draw_ops = []
        for chave, raw_x, raw_y in chaves_visiveis:
            grid = chunks_ref.get(chave)
            if not grid:
                continue
            superficie = self._obter_superficie_chunk(chave, grid, tile_px)
            if superficie is not None:
                draw_ops.append((superficie, raw_x * tamanho_chunk, raw_y * tamanho_chunk))

        cam_x, cam_y = map(float, getattr(self.Camera, "PosicaoTiles", (0.0, 0.0)))
        tela_w, tela_h = tela.get_size()
        for superficie_chunk, origem_x, origem_y in draw_ops:
            px = (origem_x - cam_x) * tile_px
            py = (origem_y - cam_y) * tile_px
            if px > tela_w or py > tela_h or (px + superficie_chunk.get_width()) < 0 or (py + superficie_chunk.get_height()) < 0:
                continue
            tela.blit(superficie_chunk, (int(px), int(py)))
