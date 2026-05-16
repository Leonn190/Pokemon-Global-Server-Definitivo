"""Leitor de mundo do cliente para sincronizar chunks do anel ativo."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Dict, List, Optional, Tuple

import pygame

from Codigo.ModulosGerais.GerenciadorTiles import GerenciadorTiles
from Codigo.ModulosMundo.CacheChunksMundo import CacheChunksMundo
from Codigo.ModulosMundo.Geradores.EstruturaNaturais import definir_limites_escala_estrutura_natural
from Codigo.ModulosMundo.RenderizadorChunksMundo import RenderizadorChunksMundo

Vector2 = Tuple[float, float]
PacoteMundo = Dict[str, object]


class LeitorMundo:
    def __init__(
        self,
        jogo,
        camera,
        callback_atualizacao: Callable[[str, str, Vector2, int], Optional[PacoteMundo]],
        callback_dimensao_atual: Optional[Callable[[str], None]] = None,
        intervalo_poll: float = 0.20,
        raio_chunks: int = 3,
    ) -> None:
        self.JOGO = jogo
        self.Camera = camera
        self.CallbackAtualizacao = callback_atualizacao
        self.CallbackDimensaoAtual = callback_dimensao_atual
        self.IntervaloPoll = max(0.05, float(intervalo_poll))
        self.RaioChunks = max(1, int(raio_chunks))

        self.ServerLink: Optional[str] = None
        self.ClientId = str(getattr(jogo, "INFO", {}).get("UsuarioLogado", "anon"))
        self.Chunks: Dict[Tuple[int, int], List[List[int]]] = {}
        self._lock = threading.Lock()

        self._thread_chunks: Optional[threading.Thread] = None
        self._ativo_chunks = False
        self._modo_manual = False
        self._versao_chunks = 0
        self.MetaMundo: Dict[str, object] = {}
        self.TamanhoChunkBlocos = 10
        self.CoresBlocosBase = {0: (24, 72, 145), 1: (64, 156, 255), 2: (106, 190, 48), 3: (46, 125, 50), 4: (230, 210, 140), 5: (217, 179, 92), 6: (245, 248, 252), 7: (140, 82, 255), 8: (88, 70, 70), 9: (110, 92, 68), 10: (226, 238, 252), 11: (206, 224, 243)}
        self.CoresBlocosDungeon = {**self.CoresBlocosBase, 0: (14, 34, 64), 1: (32, 74, 122), 8: (38, 39, 43), 9: (74, 75, 82), 10: (0, 0, 0), 11: (88, 90, 98)}
        self.CoresBlocos = dict(self.CoresBlocosBase)
        self._modo_cores_tiles = "mundo"

        self._cache_superficies_chunks: Dict[Tuple[int, int], pygame.Surface] = {}
        self._cache_assinaturas_chunks: Dict[Tuple[int, int], Tuple[Tuple[int, ...], ...]] = {}
        self._cache_tile_px: int = max(1, int(getattr(self.Camera, "TilePx", 50)))
        self._fila_preaquecimento_chunks = deque()
        self._fila_preaquecimento_set = set()
        self._ultimo_chunk_player: Optional[Tuple[int, int]] = None
        self._ultima_versao_chunks_regras = -1
        self._ultimo_seed_tiles: Optional[int] = None
        self.RenderizadorTiles = GerenciadorTiles(cores_blocos=self.CoresBlocos)
        self.CacheChunks = CacheChunksMundo(self)
        self.RenderizadorChunks = RenderizadorChunksMundo(self)

    def _aplicar_paleta_dimensao(self, dimensao: str) -> None:
        modo = "dungeon" if str(dimensao or "").startswith("Dungeon_") else "mundo"
        if modo == self._modo_cores_tiles:
            return
        self._modo_cores_tiles = modo
        self.CoresBlocos = dict(self.CoresBlocosDungeon if modo == "dungeon" else self.CoresBlocosBase)
        self.RenderizadorTiles.atualizar_cores(self.CoresBlocos)
        self._cache_superficies_chunks.clear()

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
            dimensao = str(meta.get("dimensao") or "Mundo")
            self._aplicar_paleta_dimensao(dimensao)
            eh_mundo = dimensao == "Mundo"
            if player_controle is not None:
                player_controle.definir_limites_mundo(largura, altura, toroidal=eh_mundo)
            if self.Camera is not None:
                self.Camera.definir_limites_mundo(largura, altura, toroidal=eh_mundo)

        if player_controle is not None and chunks_atualizados is not None:
            player_controle.definir_grid_chunks(chunks_atualizados, chunk_tamanho)

        regras_mundo = getattr(self.JOGO, "INFO", {}).get("RegrasMundo", {}) if isinstance(getattr(self.JOGO, "INFO", {}), dict) else {}
        bloco_mundo = regras_mundo.get("mundo") if isinstance(regras_mundo.get("mundo"), dict) else {}
        try:
            seed_tiles = int(bloco_mundo.get("seed", 0) or 0)
        except (TypeError, ValueError):
            seed_tiles = 0
        if self._ultimo_seed_tiles != seed_tiles:
            self.RenderizadorTiles.definir_seed(seed_tiles)
            self._ultimo_seed_tiles = seed_tiles
        definir_limites_escala_estrutura_natural(
            bloco_mundo.get("escala_estrutura_min", 0.90),
            bloco_mundo.get("escala_estrutura_max", 1.10),
        )

    def conectar_servidor(self, link_servidor: str) -> None:
        self.ServerLink = str(link_servidor)
        if hasattr(self.JOGO, "INFO") and isinstance(self.JOGO.INFO, dict):
            self.JOGO.INFO["ServerLink"] = self.ServerLink

    def iniciar(self) -> None:
        if self._modo_manual:
            self._ativo_chunks = True
            return
        if self._thread_chunks and self._thread_chunks.is_alive():
            return
        self._ativo_chunks = True
        self._thread_chunks = threading.Thread(target=self._loop_chunks, name="LeitorMundoChunksThread", daemon=True)
        self._thread_chunks.start()

    def parar(self, timeout: float = 2.0) -> None:
        self._ativo_chunks = False
        if self._thread_chunks and self._thread_chunks.is_alive():
            self._thread_chunks.join(timeout=timeout)

    def ativar_bombeamento_manual(self, ativo: bool) -> None:
        thread = None
        self._modo_manual = bool(ativo)
        if self._modo_manual:
            self._ativo_chunks = False
            thread = self._thread_chunks
            self._thread_chunks = None
            self._ultimo_chunk_player = None
        if thread and thread.is_alive():
            thread.join(timeout=0.2)
        if self._modo_manual:
            self._ativo_chunks = True


    def posicao_referencia(self) -> Vector2:
        """Posição de referência para consulta de chunks.

        Usa o player local quando disponível para evitar buracos visuais
        nas bordas toroidais (a câmera pode ficar negativa/offset por
        centralização antes do player realmente cruzar a borda).
        """
        entidade = getattr(self.Camera, "EntidadeMain", None)
        pos_entidade = getattr(entidade, "Posicao", None)
        if isinstance(pos_entidade, (list, tuple)) and len(pos_entidade) == 2:
            try:
                return (float(pos_entidade[0]), float(pos_entidade[1]))
            except Exception:
                pass
        pos_camera = getattr(self.Camera, "PosicaoTiles", (0.0, 0.0))
        try:
            return (float(pos_camera[0]), float(pos_camera[1]))
        except Exception:
            return (0.0, 0.0)

    def _normalizar_chunk_referencia(self, chunk: Tuple[int, int]) -> Tuple[int, int]:
        with self._lock:
            meta = dict(self.MetaMundo)
        largura_blocos = int(meta.get("largura_blocos", 0) or 0)
        altura_blocos = int(meta.get("altura_blocos", 0) or 0)
        tamanho = max(1, int(self.TamanhoChunkBlocos))
        if largura_blocos <= 0 or altura_blocos <= 0:
            return (int(chunk[0]), int(chunk[1]))
        total_x = max(1, int((largura_blocos + tamanho - 1) // tamanho))
        total_y = max(1, int((altura_blocos + tamanho - 1) // tamanho))
        if bool(getattr(self.Camera, "LimitesToroidais", False)):
            return (int(chunk[0]) % total_x, int(chunk[1]) % total_y)
        return (max(0, min(total_x - 1, int(chunk[0]))), max(0, min(total_y - 1, int(chunk[1]))))

    def _chunk_atual_player(self) -> Tuple[int, int]:
        pos_ref = self.posicao_referencia()
        tamanho = max(1, int(self.TamanhoChunkBlocos))
        try:
            bruto = (int(float(pos_ref[0]) // tamanho), int(float(pos_ref[1]) // tamanho))
            return self._normalizar_chunk_referencia(bruto)
        except Exception:
            return (0, 0)

    def _loop_chunks(self) -> None:
        while self._ativo_chunks:
            if self.ServerLink is None:
                time.sleep(self.IntervaloPoll)
                continue
            self._tentar_refresh_chunks()
            time.sleep(self.IntervaloPoll)

    def bombear(self) -> None:
        if not self._modo_manual or not self._ativo_chunks or self.ServerLink is None:
            return
        self._tentar_refresh_chunks()

    def _tentar_refresh_chunks(self) -> bool:
        chunk_player = self._chunk_atual_player()
        if self._ultimo_chunk_player is not None and chunk_player == self._ultimo_chunk_player:
            return False
        pacote = self._coletar_chunks_servidor()
        if not pacote:
            return False
        self.processar_pacote_chunks(pacote)
        self._ultimo_chunk_player = chunk_player
        return True

    def forcar_refresh_chunks(self) -> None:
        with self._lock:
            self._ultimo_chunk_player = None

    def _coletar_chunks_servidor(self) -> Optional[PacoteMundo]:
        pos_ref = self.posicao_referencia()
        try:
            return self.CallbackAtualizacao(self.ServerLink, self.ClientId, tuple(pos_ref), int(self.RaioChunks))
        except Exception:
            return None

    def descartar_chunks_fora_do_anel(self) -> None:
        return self.CacheChunks.descartar_chunks_fora_do_anel()

    def processar_pacote_chunks(self, pacote: PacoteMundo) -> None:
        if not isinstance(pacote, dict):
            return
        dimensao_callback: str | None = None
        with self._lock:
            meta_alterada = False
            meta = pacote.get("meta") if isinstance(pacote.get("meta"), dict) else {}
            for chave_meta in ("largura_blocos", "altura_blocos", "raio_chunks_ativo", "dimensao", "layout_dungeon", "tipo_dimensao", "tamanho_bloco_sala_tiles", "largura_bloco_sala_tiles", "altura_bloco_sala_tiles"):
                if chave_meta not in meta:
                    continue
                valor_meta = meta.get(chave_meta)
                if self.MetaMundo.get(chave_meta) != valor_meta:
                    self.MetaMundo[chave_meta] = valor_meta
                    meta_alterada = True
            if meta.get("dimensao") is not None and self.CallbackDimensaoAtual is not None:
                dimensao_callback = str(meta.get("dimensao") or "Mundo")
            chunk_tamanho = meta.get("chunk_tamanho", meta.get("chunk_blocos"))
            if chunk_tamanho is not None:
                chunk_tamanho_novo = max(1, int(chunk_tamanho))
                if chunk_tamanho_novo != self.TamanhoChunkBlocos:
                    self.TamanhoChunkBlocos = chunk_tamanho_novo
                    self._cache_superficies_chunks.clear()
                    self._cache_assinaturas_chunks.clear()
                    self.RenderizadorTiles.limpar_cache()
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
                self._ultimo_chunk_player = None
        if dimensao_callback is not None and self.CallbackDimensaoAtual is not None:
            self.CallbackDimensaoAtual(dimensao_callback)
        self.descartar_chunks_fora_do_anel()
        if houve_alteracao_chunks or meta_alterada:
            self.preaquecer_chunks_visiveis()

    def _obter_superficie_chunk(self, chave_chunk: Tuple[int, int], grid: List[List[int]], tile_px: int) -> Optional[pygame.Surface]:
        return self.CacheChunks.obter_superficie_chunk(chave_chunk, grid, tile_px)

    @staticmethod
    def _intervalo_chunks_visiveis(
        cam_tile: float,
        tela_px: float,
        tile_px: int,
        tamanho_chunk: int,
        margem_chunks: int = 0,
    ) -> range:
        return RenderizadorChunksMundo.intervalo_chunks_visiveis(cam_tile, tela_px, tile_px, tamanho_chunk, margem_chunks)

    def _chaves_chunks_visiveis(
        self,
        cam_x: float,
        cam_y: float,
        tela_w: float,
        tela_h: float,
        tile_px: int,
        tamanho_chunk: int,
        chunks_ref: Dict[Tuple[int, int], List[List[int]]],
        toroidal: bool,
        chunks_x: int,
        chunks_y: int,
        margem_chunks: int = 1,
    ) -> List[Tuple[int, int]]:
        return self.RenderizadorChunks.chaves_chunks_visiveis(
            cam_x,
            cam_y,
            tela_w,
            tela_h,
            tile_px,
            tamanho_chunk,
            chunks_ref,
            toroidal,
            chunks_x,
            chunks_y,
            margem_chunks,
        )

    def preaquecer_chunks_visiveis(self) -> None:
        return self.CacheChunks.preaquecer_chunks_visiveis()

    def bombear_preaquecimento(self, max_chunks: int = 1) -> None:
        return self.CacheChunks.bombear_preaquecimento(max_chunks)

    def renderizar_mundo(self, tela) -> None:
        return self.RenderizadorChunks.renderizar_mundo(tela)
