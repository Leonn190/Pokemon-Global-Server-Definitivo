"""Renderizacao dos chunks visiveis do mundo."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


class RenderizadorChunksMundo:
    def __init__(self, leitor):
        self.leitor = leitor

    def __getattr__(self, nome):
        return getattr(self.leitor, nome)

    @staticmethod
    def intervalo_chunks_visiveis(
        cam_tile: float,
        tela_px: float,
        tile_px: int,
        tamanho_chunk: int,
        margem_chunks: int = 0,
    ) -> range:
        alcance_tiles = float(tela_px) / max(1.0, float(tile_px))
        tamanho_chunk = max(1, int(tamanho_chunk))
        margem = max(0, int(margem_chunks))
        inicio = int(math.floor(float(cam_tile) / float(tamanho_chunk))) - margem
        limite_fim = float(cam_tile) + max(0.0, alcance_tiles) - 1e-6
        fim = int(math.floor(limite_fim / float(tamanho_chunk))) + margem
        return range(inicio, fim + 1)

    def chaves_chunks_visiveis(
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
        intervalo_x = self.intervalo_chunks_visiveis(cam_x, tela_w, tile_px, tamanho_chunk, margem_chunks=margem_chunks)
        intervalo_y = self.intervalo_chunks_visiveis(cam_y, tela_h, tile_px, tamanho_chunk, margem_chunks=margem_chunks)
        if toroidal and chunks_x > 0 and chunks_y > 0:
            vistos = set()
            chaves = []
            for chunk_x in intervalo_x:
                for chunk_y in intervalo_y:
                    chave = (int(chunk_x) % chunks_x, int(chunk_y) % chunks_y)
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    chaves.append(chave)
            return chaves
        return [
            (int(chunk_x), int(chunk_y))
            for chunk_x in intervalo_x
            for chunk_y in intervalo_y
            if (int(chunk_x), int(chunk_y)) in chunks_ref
        ]

    def renderizar_mundo(self, tela) -> None:
        tile_px = max(1, int(getattr(self.Camera, "TilePx", 50)))
        with self._lock:
            tamanho_chunk = max(1, int(self.TamanhoChunkBlocos)); meta = self.MetaMundo; chunks_ref = self.Chunks
            dimensao_meta = str(meta.get("dimensao") or "Mundo")
            largura_blocos = int(meta.get("largura_blocos", 0) or 0) if isinstance(meta, dict) else 0
            altura_blocos = int(meta.get("altura_blocos", 0) or 0) if isinstance(meta, dict) else 0
        if dimensao_meta.startswith("Estadio"):
            return
        if not chunks_ref:
            return

        largura_mundo = float(largura_blocos)
        altura_mundo = float(altura_blocos)
        chunks_x = max(1, int((largura_blocos + tamanho_chunk - 1) // tamanho_chunk)) if largura_blocos > 0 else 0
        chunks_y = max(1, int((altura_blocos + tamanho_chunk - 1) // tamanho_chunk)) if altura_blocos > 0 else 0
        toroidal = bool(getattr(self.Camera, "LimitesToroidais", False)) and chunks_x > 0 and chunks_y > 0

        cam_x, cam_y = map(float, getattr(self.Camera, "PosicaoTiles", (0.0, 0.0)))
        if toroidal:
            if largura_mundo > 0.0:
                cam_x %= largura_mundo
            if altura_mundo > 0.0:
                cam_y %= altura_mundo

        tela_w, tela_h = tela.get_size()
        fila_blits = []
        intervalo_x = self.intervalo_chunks_visiveis(cam_x, tela_w, tile_px, tamanho_chunk, margem_chunks=0)
        intervalo_y = self.intervalo_chunks_visiveis(cam_y, tela_h, tile_px, tamanho_chunk, margem_chunks=0)
        for chunk_x in intervalo_x:
            origem_base_x = int(chunk_x) * tamanho_chunk
            chave_x = (int(chunk_x) % chunks_x) if toroidal and chunks_x > 0 else int(chunk_x)
            for chunk_y in intervalo_y:
                origem_base_y = int(chunk_y) * tamanho_chunk
                chave_real = (
                    chave_x,
                    (int(chunk_y) % chunks_y) if toroidal and chunks_y > 0 else int(chunk_y),
                )
                grid = chunks_ref.get(chave_real)
                if not grid:
                    continue
                superficie = self.leitor._obter_superficie_chunk(chave_real, grid, tile_px)
                if superficie is None:
                    continue

                largura_superficie = superficie.get_width()
                altura_superficie = superficie.get_height()
                px = (float(origem_base_x) - cam_x) * tile_px
                py = (float(origem_base_y) - cam_y) * tile_px
                if px > tela_w or py > tela_h or (px + largura_superficie) < 0 or (py + altura_superficie) < 0:
                    continue
                destino_x = int(px)
                destino_y = int(py)
                clip_x = max(0, -destino_x)
                clip_y = max(0, -destino_y)
                largura_visivel = min(largura_superficie - clip_x, int(tela_w) - max(0, destino_x))
                altura_visivel = min(altura_superficie - clip_y, int(tela_h) - max(0, destino_y))
                if largura_visivel <= 0 or altura_visivel <= 0:
                    continue
                if clip_x > 0 or clip_y > 0 or largura_visivel != largura_superficie or altura_visivel != altura_superficie:
                    fila_blits.append((
                        superficie,
                        (destino_x + clip_x, destino_y + clip_y),
                        (clip_x, clip_y, largura_visivel, altura_visivel),
                    ))
                else:
                    fila_blits.append((superficie, (destino_x, destino_y)))
        if not fila_blits:
            return
        blits = getattr(tela, "blits", None)
        if callable(blits):
            try:
                blits(fila_blits, doreturn=False)
            except TypeError:
                blits(fila_blits)
            return
        for item in fila_blits:
            if len(item) >= 3:
                tela.blit(item[0], item[1], item[2])
            else:
                tela.blit(item[0], item[1])
