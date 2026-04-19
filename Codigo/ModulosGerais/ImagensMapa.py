from __future__ import annotations

import math
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pygame

TILE_COLORS: Dict[int, Tuple[int, int, int]] = {
    0: (18, 74, 156),   # WATER_DEEP
    1: (95, 176, 232),  # WATER_SHALLOW
    2: (110, 186, 72),  # FIELD_GRASS
    3: (48, 126, 54),   # FOREST_GRASS
    4: (228, 214, 149), # BEACH_SAND
    5: (218, 188, 100), # DESERT_SAND
    6: (235, 242, 248), # SNOW
    7: (138, 72, 192),  # MAGIC_SOIL
    8: (112, 74, 44),   # VOLCANIC_ROCK
    9: (132, 132, 132), # DEAD_SOIL
}
WATER_TILES = {0, 1}


@dataclass
class AtlasMapa:
    atlas_x: int
    atlas_y: int
    path_base: Path
    path_regioes: Path
    surface_base: pygame.Surface
    surface_regioes: pygame.Surface
    chunks_explorados: set[Tuple[int, int]] = field(default_factory=set)
    dirty_base: bool = False
    dirty_regioes: bool = False
    versao: int = 0


class GerenciadorImagensMapa:
    def __init__(self, pasta_ram: Path | str = "RAM/ImagensMapa", atlas_chunks_lado: int = 100, chunk_blocos: int = 10):
        self._lock = threading.RLock()
        self.pasta_ram = Path(pasta_ram)
        self.atlas_chunks_lado = int(atlas_chunks_lado)
        self.chunk_blocos = int(chunk_blocos)
        self.atlas_px = self.atlas_chunks_lado * self.chunk_blocos
        self.meta: Dict[str, object] = {}
        self._atlas: Dict[Tuple[int, int], AtlasMapa] = {}
        self._explorados_mundo: Dict[int, set[int]] = {}
        self._regioes: List[dict] = []
        self._regioes_idx: Dict[int, dict] = {}
        self._prepared = False

    def preparar(self, meta: dict, explorados: dict | None = None, regioes: list | None = None) -> None:
        with self._lock:
            self.meta = dict(meta or {})
            self.chunk_blocos = int(self.meta.get("chunk_blocos", self.chunk_blocos) or self.chunk_blocos)
            self.atlas_chunks_lado = int(self.meta.get("atlas_chunks_lado", self.atlas_chunks_lado) or self.atlas_chunks_lado)
            self.atlas_px = int(self.meta.get("atlas_px", self.atlas_chunks_lado * self.chunk_blocos) or (self.atlas_chunks_lado * self.chunk_blocos))
            self.pasta_ram.mkdir(parents=True, exist_ok=True)
            self._atlas.clear()
            self._explorados_mundo = self._normalizar_explorados(explorados)
            self._regioes = [dict(r) for r in (regioes or []) if isinstance(r, dict)]
            self._regioes_idx = {int(r.get("id", -1)): r for r in self._regioes if r.get("id") is not None}
            self._prepared = True

    def limpar(self) -> None:
        with self._lock:
            self._atlas.clear()
            self._explorados_mundo.clear()
            self._prepared = False
        try:
            if self.pasta_ram.exists():
                shutil.rmtree(self.pasta_ram, ignore_errors=True)
        except Exception:
            pass

    def flush(self) -> None:
        payloads: list[tuple[pygame.Surface, Path, pygame.Surface, Path]] = []
        with self._lock:
            for atlas in self._atlas.values():
                if not atlas.chunks_explorados:
                    continue
                if not (atlas.dirty_base or atlas.dirty_regioes):
                    continue
                payloads.append((atlas.surface_base.copy(), atlas.path_base, atlas.surface_regioes.copy(), atlas.path_regioes))
                atlas.dirty_base = False
                atlas.dirty_regioes = False
        for base, path_base, reg, path_reg in payloads:
            pygame.image.save(base, str(path_base))
            pygame.image.save(reg, str(path_reg))

    def _normalizar_explorados(self, explorados: dict | None) -> Dict[int, set[int]]:
        bruto = {}
        if isinstance(explorados, dict):
            bruto = explorados.get("Mundo") if isinstance(explorados.get("Mundo"), dict) else explorados
        out: Dict[int, set[int]] = {}
        for sx, ys in (bruto or {}).items():
            try:
                x = int(sx)
            except Exception:
                continue
            conjunto: set[int] = set()
            if isinstance(ys, (list, tuple, set)):
                for y in ys:
                    try:
                        conjunto.add(int(y))
                    except Exception:
                        continue
            if conjunto:
                out[x] = conjunto
        return out

    def posicao_player_mundo(self, estado_player: dict | None, fallback_pos: Tuple[float, float]) -> Tuple[float, float]:
        estado = dict(estado_player or {})
        ultima = estado.get("ultima_pos_mundo")
        if isinstance(ultima, (list, tuple)) and len(ultima) == 2:
            return (float(ultima[0]), float(ultima[1]))
        pos_dim = estado.get("posicoes_por_dimensao") if isinstance(estado.get("posicoes_por_dimensao"), dict) else {}
        pos_mundo = pos_dim.get("Mundo") if isinstance(pos_dim.get("Mundo"), (list, tuple)) and len(pos_dim.get("Mundo")) == 2 else None
        if pos_mundo is not None:
            return (float(pos_mundo[0]), float(pos_mundo[1]))
        return (float(fallback_pos[0]), float(fallback_pos[1]))

    def chunk_explorado(self, chunk_x: int, chunk_y: int) -> bool:
        with self._lock:
            return int(chunk_y) in self._explorados_mundo.get(int(chunk_x), set())

    def explorados_snapshot(self) -> Dict[int, set[int]]:
        with self._lock:
            return {x: set(ys) for x, ys in self._explorados_mundo.items()}

    def registrar_explorados(self, chunks: Iterable[Tuple[int, int]]) -> None:
        with self._lock:
            for cx, cy in chunks:
                self._explorados_mundo.setdefault(int(cx), set()).add(int(cy))

    def _atlas_key(self, chunk_x: int, chunk_y: int) -> Tuple[int, int]:
        return (int(chunk_x) // self.atlas_chunks_lado, int(chunk_y) // self.atlas_chunks_lado)

    def _atlas_for_chunk(self, chunk_x: int, chunk_y: int) -> AtlasMapa:
        ax, ay = self._atlas_key(chunk_x, chunk_y)
        chave = (ax, ay)
        atlas = self._atlas.get(chave)
        if atlas is not None:
            return atlas
        base_path = self.pasta_ram / f"atlas_{ax}_{ay}_base.png"
        reg_path = self.pasta_ram / f"atlas_{ax}_{ay}_regioes.png"
        sbase = pygame.Surface((self.atlas_px, self.atlas_px))
        sbase.fill((0, 0, 0))
        sreg = pygame.Surface((self.atlas_px, self.atlas_px))
        sreg.fill((0, 0, 0))
        atlas = AtlasMapa(ax, ay, base_path, reg_path, sbase, sreg)
        self._atlas[chave] = atlas
        return atlas

    def obter_atlas(self, atlas_x: int, atlas_y: int) -> AtlasMapa | None:
        with self._lock:
            return self._atlas.get((int(atlas_x), int(atlas_y)))

    def atlas_keys_no_rect(self, x: int, y: int, largura: int, altura: int) -> list[tuple[int, int]]:
        if largura <= 0 or altura <= 0:
            return []
        ax0 = int(math.floor(float(x) / self.atlas_px))
        ay0 = int(math.floor(float(y) / self.atlas_px))
        ax1 = int(math.floor(float(x + largura - 1) / self.atlas_px))
        ay1 = int(math.floor(float(y + altura - 1) / self.atlas_px))
        chaves = []
        for ay in range(ay0, ay1 + 1):
            for ax in range(ax0, ax1 + 1):
                chaves.append((ax, ay))
        return chaves

    def _cor_regiao(self, regiao_id: int) -> Tuple[int, int, int]:
        reg = self._regioes_idx.get(int(regiao_id))
        if not isinstance(reg, dict):
            return (90, 90, 90)
        cor = reg.get("cor") if isinstance(reg.get("cor"), (list, tuple)) else reg.get("cor_rgb")
        if isinstance(cor, (list, tuple)) and len(cor) == 3:
            return (int(cor[0]), int(cor[1]), int(cor[2]))
        return (90, 90, 90)

    def _regiao_mais_proxima(self, gx: int, gy: int) -> int:
        melhor_id = -1
        melhor_d2 = 10**18
        for reg in self._regioes:
            centro = reg.get("centro") if isinstance(reg.get("centro"), (list, tuple)) and len(reg.get("centro")) == 2 else [0, 0]
            try:
                dx = float(gx) - float(centro[0])
                dy = float(gy) - float(centro[1])
            except Exception:
                continue
            d2 = (dx * dx) + (dy * dy)
            if d2 < melhor_d2:
                melhor_d2 = d2
                melhor_id = int(reg.get("id", -1) or -1)
        return melhor_id

    def ponto_explorado_regiao(self, regiao_id: int, preferencia: Tuple[float, float], area_visivel: pygame.Rect | None = None) -> Tuple[float, float] | None:
        if int(regiao_id) < 0:
            return None
        melhor = None
        melhor_d2 = 10**18
        px, py = float(preferencia[0]), float(preferencia[1])
        with self._lock:
            for cx, ys in self._explorados_mundo.items():
                for cy in ys:
                    gx = (int(cx) * self.chunk_blocos) + (self.chunk_blocos * 0.5)
                    gy = (int(cy) * self.chunk_blocos) + (self.chunk_blocos * 0.5)
                    if area_visivel is not None and not area_visivel.collidepoint(int(gx), int(gy)):
                        continue
                    if self._regiao_mais_proxima(int(gx), int(gy)) != int(regiao_id):
                        continue
                    d2 = ((gx - px) ** 2) + ((gy - py) ** 2)
                    if d2 < melhor_d2:
                        melhor_d2 = d2
                        melhor = (gx, gy)
        if melhor is not None:
            return melhor
        with self._lock:
            for cx, ys in self._explorados_mundo.items():
                for cy in ys:
                    gx = (int(cx) * self.chunk_blocos) + (self.chunk_blocos * 0.5)
                    gy = (int(cy) * self.chunk_blocos) + (self.chunk_blocos * 0.5)
                    if self._regiao_mais_proxima(int(gx), int(gy)) != int(regiao_id):
                        continue
                    d2 = ((gx - px) ** 2) + ((gy - py) ** 2)
                    if d2 < melhor_d2:
                        melhor_d2 = d2
                        melhor = (gx, gy)
        return melhor

    def aplicar_chunks(self, atlas_payload: list | None) -> int:
        if not self._prepared or not isinstance(atlas_payload, list):
            return 0
        alterados = 0
        with self._lock:
            for grupo in atlas_payload:
                if not isinstance(grupo, dict):
                    continue
                chunks = grupo.get("chunks") if isinstance(grupo.get("chunks"), list) else []
                for chunk in chunks:
                    if not isinstance(chunk, dict):
                        continue
                    pos = chunk.get("pos")
                    grid = chunk.get("grid")
                    if not (isinstance(pos, (list, tuple)) and len(pos) == 2 and isinstance(grid, list)):
                        continue
                    cx, cy = int(pos[0]), int(pos[1])
                    atlas = self._atlas_for_chunk(cx, cy)
                    self._desenhar_chunk_no_atlas(atlas, cx, cy, grid)
                    atlas.chunks_explorados.add((cx, cy))
                    self._explorados_mundo.setdefault(cx, set()).add(cy)
                    alterados += 1
        return alterados

    def _desenhar_chunk_no_atlas(self, atlas: AtlasMapa, cx: int, cy: int, grid: List[List[int]]) -> None:
        inicio_x = (int(cx) % self.atlas_chunks_lado) * self.chunk_blocos
        inicio_y = (int(cy) % self.atlas_chunks_lado) * self.chunk_blocos
        for ly, linha in enumerate(grid[: self.chunk_blocos]):
            if not isinstance(linha, list):
                continue
            for lx, tile in enumerate(linha[: self.chunk_blocos]):
                gx = int(cx) * self.chunk_blocos + int(lx)
                gy = int(cy) * self.chunk_blocos + int(ly)
                cor_base = TILE_COLORS.get(int(tile), (255, 0, 255))
                atlas.surface_base.set_at((inicio_x + lx, inicio_y + ly), cor_base)
                if int(tile) in WATER_TILES:
                    cor_reg = cor_base
                else:
                    rid = self._regiao_mais_proxima(gx, gy)
                    cor_reg = self._cor_regiao(rid)
                atlas.surface_regioes.set_at((inicio_x + lx, inicio_y + ly), cor_reg)
        atlas.dirty_base = True
        atlas.dirty_regioes = True
        atlas.versao += 1

    def atlas_visiveis(self, camera_rect_mundo_px: pygame.Rect) -> List[AtlasMapa]:
        if camera_rect_mundo_px.width <= 0 or camera_rect_mundo_px.height <= 0:
            return []
        with self._lock:
            out: List[AtlasMapa] = []
            for atlas in self._atlas.values():
                if not atlas.chunks_explorados:
                    continue
                rect = pygame.Rect(atlas.atlas_x * self.atlas_px, atlas.atlas_y * self.atlas_px, self.atlas_px, self.atlas_px)
                if rect.colliderect(camera_rect_mundo_px):
                    out.append(atlas)
            return out

    def all_atlas(self) -> List[AtlasMapa]:
        with self._lock:
            return list(self._atlas.values())

    def mundo_tamanho_px(self) -> Tuple[int, int]:
        largura_blocos = int(self.meta.get("largura_blocos", 0) or 0)
        altura_blocos = int(self.meta.get("altura_blocos", 0) or 0)
        return (max(1, largura_blocos), max(1, altura_blocos))
