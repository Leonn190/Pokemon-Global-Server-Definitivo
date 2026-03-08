"""Leitor de mundo do cliente para sincronizar chunks do anel ativo.

Neste novo modelo, o LeitorMundo ficou responsável APENAS por chunks.
As diffs de objetos agora ficam no ControladorObjetos.
"""

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

        # Thread dedicada SOMENTE ao fluxo de chunks.
        self._thread_chunks: Optional[threading.Thread] = None
        self._ativo_chunks = False

        # Mantido por compatibilidade de API, mas sem uso no novo fluxo.
        self._diffs_recebidas: List[Dict[str, object]] = []

        self._versao_chunks = 0
        self.MetaMundo: Dict[str, object] = {}
        self.TamanhoChunkBlocos = 10
        self.CoresBlocos = {
            0: (14, 40, 92),
            1: (72, 162, 231),
            2: (230, 210, 146),
            3: (124, 204, 108),
            4: (56, 128, 64),
        }

        # Cache visual por chunk: precisa ser limpo quando o anel muda.
        self._cache_superficies_chunks: Dict[Tuple[int, int], pygame.Surface] = {}
        self._cache_tile_px: int = max(1, int(getattr(self.Camera, "TilePx", 50)))

        # Controle de mudança de chunk do player.
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

    def consumir_diffs_recebidas(self) -> List[Dict[str, object]]:
        """Compatibilidade com chamadas antigas; diffs ficam no ControladorObjetos."""
        with self._lock:
            diffs = list(self._diffs_recebidas)
            self._diffs_recebidas.clear()
            return diffs

    def _chunk_atual_player(self) -> Tuple[int, int]:
        pos_camera = getattr(self.Camera, "PosicaoTiles", (0.0, 0.0))
        tamanho = max(1, int(self.TamanhoChunkBlocos))
        try:
            return (int(float(pos_camera[0]) // tamanho), int(float(pos_camera[1]) // tamanho))
        except Exception:
            return (0, 0)

    def _loop_chunks(self) -> None:
        """Loop condicional de chunks: só consulta quando o player muda de chunk."""
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
            return self.CallbackAtualizacao(self.ServerLink, self.ClientId, pos_camera, self.RaioChunks)
        except Exception:
            return None

    def _chaves_anel_atual(self) -> set[Tuple[int, int]]:
        """Calcula o anel de chunks válido em volta do chunk atual do player."""
        chunk_player_x, chunk_player_y = self._chunk_atual_player()
        chaves = set()
        for dy in range(-self.RaioChunks, self.RaioChunks + 1):
            for dx in range(-self.RaioChunks, self.RaioChunks + 1):
                chaves.add((chunk_player_x + dx, chunk_player_y + dy))
        return chaves

    def descartar_chunks_fora_do_anel(self) -> None:
        """Remove chunks/caches fora do anel atual para evitar histórico acumulado."""
        anel = self._chaves_anel_atual()
        with self._lock:
            for chave in list(self.Chunks.keys()):
                if chave not in anel:
                    self.Chunks.pop(chave, None)
                    self._cache_superficies_chunks.pop(chave, None)

    def processar_pacote_chunks(self, pacote: PacoteMundo) -> None:
        """Aplica pacote de chunks descartando completamente o conjunto antigo."""
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

            # Troca total do conjunto carregado: sem histórico de chunks.
            self.Chunks = chunks_atuais
            self._cache_superficies_chunks.clear()
            self._versao_chunks += 1

        # Garantia extra: mantém somente o anel atual.
        self.descartar_chunks_fora_do_anel()

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

        tile_px = max(1, int(getattr(self.Camera, "TilePx", 50)))

        player = getattr(self.Camera, "EntidadeMain", None)
        pos_player = getattr(player, "Posicao", (0.0, 0.0))

        with self._lock:
            tamanho_chunk = max(1, int(self.TamanhoChunkBlocos))
            meta = dict(self.MetaMundo)
            chunks_ref = self.Chunks

        try:
            chunk_player_x = int(float(pos_player[0]) // tamanho_chunk)
            chunk_player_y = int(float(pos_player[1]) // tamanho_chunk)
        except Exception:
            chunk_player_x = 0
            chunk_player_y = 0

        if not chunks_ref:
            if gerenciador_fps is not None:
                gerenciador_fps.finalizar_trecho("carregar_chunks")
            return

        limites = getattr(self.Camera, "LimitesMundoTiles", None)
        repeticoes_x = (0.0,)
        repeticoes_y = (0.0,)

        tela_w, tela_h = tela.get_size()
        if limites:
            largura_mundo, altura_mundo = (float(limites[0]), float(limites[1]))
            largura_mundo_px = largura_mundo * tile_px
            altura_mundo_px = altura_mundo * tile_px
            if largura_mundo_px <= tela_w:
                repeticoes_x = (-largura_mundo, 0.0, largura_mundo)
            if altura_mundo_px <= tela_h:
                repeticoes_y = (-altura_mundo, 0.0, altura_mundo)

        try:
            raio_render_chunks = max(1, int(meta.get("raio_chunks_ativo", self.RaioChunks)))
        except Exception:
            raio_render_chunks = max(1, int(self.RaioChunks))

        chaves_visiveis = []
        for dy in range(-raio_render_chunks, raio_render_chunks + 1):
            chunk_raw_y = chunk_player_y + dy
            for dx in range(-raio_render_chunks, raio_render_chunks + 1):
                chunk_raw_x = chunk_player_x + dx
                chaves_visiveis.append(((chunk_raw_x, chunk_raw_y), chunk_raw_x, chunk_raw_y))

        with self._lock:
            grids_visiveis = [(chave, chunks_ref.get(chave), raw_x, raw_y) for chave, raw_x, raw_y in chaves_visiveis]

        draw_ops = []
        for chave_chunk, grid, chunk_raw_x, chunk_raw_y in grids_visiveis:
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

        pos_camera = getattr(self.Camera, "PosicaoTiles", (0.0, 0.0))
        cam_x = float(pos_camera[0])
        cam_y = float(pos_camera[1])
        limites_validos = bool(limites)
        largura_mundo = float(limites[0]) if limites_validos else 0.0
        altura_mundo = float(limites[1]) if limites_validos else 0.0
        for superficie_chunk, origem_x, origem_y in draw_ops:
            largura_px = superficie_chunk.get_width()
            altura_px = superficie_chunk.get_height()
            for off_x in repeticoes_x:
                for off_y in repeticoes_y:
                    dx_tiles = (origem_x + off_x) - cam_x
                    dy_tiles = (origem_y + off_y) - cam_y
                    if limites_validos:
                        dx_tiles -= round(dx_tiles / largura_mundo) * largura_mundo
                        dy_tiles -= round(dy_tiles / altura_mundo) * altura_mundo

                    px = dx_tiles * tile_px
                    py = dy_tiles * tile_px
                    if px > tela_w or py > tela_h or (px + largura_px) < 0 or (py + altura_px) < 0:
                        continue
                    tela.blit(superficie_chunk, (int(px), int(py)))

        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("renderizar_tiles")
