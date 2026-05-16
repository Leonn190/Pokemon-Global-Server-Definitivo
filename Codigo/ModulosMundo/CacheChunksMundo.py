"""Cache e pre-aquecimento de superficies de chunks do mundo."""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple

import pygame


class CacheChunksMundo:
    def __init__(self, leitor):
        object.__setattr__(self, "leitor", leitor)

    def __getattr__(self, nome):
        return getattr(self.leitor, nome)

    def __setattr__(self, nome, valor):
        if nome == "leitor":
            object.__setattr__(self, nome, valor)
            return
        setattr(self.leitor, nome, valor)

    def descartar_chunks_fora_do_anel(self) -> None:
        with self._lock:
            chaves_anel = set(self.Chunks.keys())
            for chave in list(self._cache_superficies_chunks.keys()):
                if chave not in chaves_anel:
                    self._cache_superficies_chunks.pop(chave, None)
            for chave in list(self._cache_assinaturas_chunks.keys()):
                if chave not in chaves_anel:
                    self._cache_assinaturas_chunks.pop(chave, None)
            self._fila_preaquecimento_chunks = deque(chave for chave in self._fila_preaquecimento_chunks if chave in chaves_anel)
            self._fila_preaquecimento_set = set(self._fila_preaquecimento_chunks)

    def obter_superficie_chunk(self, chave_chunk: Tuple[int, int], grid: List[List[int]], tile_px: int) -> Optional[pygame.Surface]:
        if not grid:
            return None
        largura_chunk = max((len(linha) for linha in grid), default=0)
        altura_chunk = len(grid)
        if largura_chunk <= 0 or altura_chunk <= 0:
            return None
        if tile_px != self._cache_tile_px:
            self._cache_superficies_chunks.clear()
            self.RenderizadorTiles.limpar_cache()
            self._cache_tile_px = tile_px
        superficie = self._cache_superficies_chunks.get(chave_chunk)
        if superficie is not None:
            return superficie
        superficie = self.RenderizadorTiles.renderizar_chunk(
            chave_chunk=chave_chunk,
            grid=grid,
            tile_px=tile_px,
            tamanho_chunk=self.TamanhoChunkBlocos,
        )
        if superficie is None:
            return None
        superficie = superficie.convert()
        self._cache_superficies_chunks[chave_chunk] = superficie
        return superficie

    def preaquecer_chunks_visiveis(self) -> None:
        tile_px = max(1, int(getattr(self.Camera, "TilePx", 50)))
        with self._lock:
            tamanho_chunk = max(1, int(self.TamanhoChunkBlocos))
            meta = dict(self.MetaMundo)
            chunks_ref = dict(self.Chunks)
        dimensao_meta = str(meta.get("dimensao") or "Mundo")
        if dimensao_meta.startswith("Estadio") or not chunks_ref:
            return

        largura_blocos = int(meta.get("largura_blocos", 0) or 0)
        altura_blocos = int(meta.get("altura_blocos", 0) or 0)
        chunks_x = max(1, int((largura_blocos + tamanho_chunk - 1) // tamanho_chunk)) if largura_blocos > 0 else 0
        chunks_y = max(1, int((altura_blocos + tamanho_chunk - 1) // tamanho_chunk)) if altura_blocos > 0 else 0
        toroidal = bool(getattr(self.Camera, "LimitesToroidais", False)) and chunks_x > 0 and chunks_y > 0

        cam_x, cam_y = map(float, getattr(self.Camera, "PosicaoTiles", (0.0, 0.0)))
        if toroidal:
            if largura_blocos > 0:
                cam_x %= float(largura_blocos)
            if altura_blocos > 0:
                cam_y %= float(altura_blocos)

        tela_w, tela_h = getattr(self.Camera, "TamanhoTelaPx", (1280.0, 720.0))
        chaves_visiveis = self.leitor._chaves_chunks_visiveis(
            cam_x=cam_x,
            cam_y=cam_y,
            tela_w=float(tela_w),
            tela_h=float(tela_h),
            tile_px=tile_px,
            tamanho_chunk=tamanho_chunk,
            chunks_ref=chunks_ref,
            toroidal=toroidal,
            chunks_x=chunks_x,
            chunks_y=chunks_y,
            margem_chunks=0,
        )
        chaves_margem = self.leitor._chaves_chunks_visiveis(
            cam_x=cam_x,
            cam_y=cam_y,
            tela_w=float(tela_w),
            tela_h=float(tela_h),
            tile_px=tile_px,
            tamanho_chunk=tamanho_chunk,
            chunks_ref=chunks_ref,
            toroidal=toroidal,
            chunks_x=chunks_x,
            chunks_y=chunks_y,
            margem_chunks=1,
        )
        chaves_visiveis_set = set(chaves_visiveis)

        for chave_chunk in chaves_visiveis:
            grid = chunks_ref.get(chave_chunk, [])
            if grid:
                self.obter_superficie_chunk(chave_chunk, grid, tile_px)
        for chave_chunk in chaves_margem:
            if (
                chave_chunk in chaves_visiveis_set
                or chave_chunk not in chunks_ref
                or chave_chunk in self._cache_superficies_chunks
                or chave_chunk in self._fila_preaquecimento_set
            ):
                continue
            self._fila_preaquecimento_chunks.append(chave_chunk)
            self._fila_preaquecimento_set.add(chave_chunk)

    def bombear_preaquecimento(self, max_chunks: int = 1) -> None:
        limite = max(0, int(max_chunks or 0))
        if limite <= 0:
            return
        tile_px = max(1, int(getattr(self.Camera, "TilePx", 50)))
        processados = 0
        while processados < limite and self._fila_preaquecimento_chunks:
            chave_chunk = self._fila_preaquecimento_chunks.popleft()
            self._fila_preaquecimento_set.discard(chave_chunk)
            processados += 1
            with self._lock:
                grid = self.Chunks.get(chave_chunk, [])
            if not grid or chave_chunk in self._cache_superficies_chunks:
                continue
            self.obter_superficie_chunk(chave_chunk, grid, tile_px)
