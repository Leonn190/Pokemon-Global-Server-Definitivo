from __future__ import annotations

import math
import threading
import json
import time
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
OBJETO_CORES = {
    "vegetacao": (24, 96, 38),
    "mineral": (126, 112, 92),
    "bau": (230, 164, 34),
    "estrutura": (158, 104, 58),
}


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
    def __init__(
        self,
        server_id: str = "default",
        client_id: str = "anon",
        pasta_base: Path | str = "Saves/MapaCache",
        atlas_chunks_lado: int = 100,
        chunk_blocos: int = 10,
    ):
        self._lock = threading.RLock()
        self.server_id = self._normalizar_id(server_id, "default")
        self.client_id = self._normalizar_id(client_id, "anon")
        self.pasta_base = Path(pasta_base)
        self.pasta_cache = self.pasta_base / self.server_id / self.client_id
        self.path_manifest = self.pasta_cache / "manifest.json"
        self.atlas_chunks_lado = int(atlas_chunks_lado)
        self.chunk_blocos = int(chunk_blocos)
        self.atlas_px = self.atlas_chunks_lado * self.chunk_blocos
        self.meta: Dict[str, object] = {}
        self._atlas: Dict[Tuple[int, int], AtlasMapa] = {}
        self._atlas_manifest: Dict[Tuple[int, int], dict] = {}
        self._explorados_mundo: Dict[int, set[int]] = {}
        self._regioes: List[dict] = []
        self._regioes_idx: Dict[int, dict] = {}
        self._manifest: Dict[str, object] = {}
        self._manifest_carregado = False
        self._manifest_dirty = False
        self._versao_mapa = 0
        self._ultimo_flush_s = 0.0
        self._chunks_pendentes_flush = 0
        self._flush_intervalo_s = 5.0
        self._flush_chunks_limite = 50
        self._prepared = False
        self._garantir_manifest_carregado()

    def preparar(self, meta: dict, explorados: dict | None = None, regioes: list | None = None) -> None:
        with self._lock:
            self.meta = dict(meta or {})
            self.chunk_blocos = int(self.meta.get("chunk_blocos", self.chunk_blocos) or self.chunk_blocos)
            self.atlas_chunks_lado = int(self.meta.get("atlas_chunks_lado", self.atlas_chunks_lado) or self.atlas_chunks_lado)
            self.atlas_px = int(self.meta.get("atlas_px", self.atlas_chunks_lado * self.chunk_blocos) or (self.atlas_chunks_lado * self.chunk_blocos))
            self.pasta_cache.mkdir(parents=True, exist_ok=True)
            self._atlas.clear()
            self._atlas_manifest.clear()
            self._explorados_mundo = self._normalizar_explorados(explorados)
            self._regioes = [dict(r) for r in (regioes or []) if isinstance(r, dict)]
            for idx, reg in enumerate(self._regioes):
                if reg.get("id") in (None, ""):
                    reg["id"] = int(idx + 1)
            self._regioes_idx = {int(r.get("id", -1)): r for r in self._regioes if r.get("id") is not None}
            self._carregar_manifest()
            self._sincronizar_manifest_meta()
            self._mesclar_explorados_manifest()
            self._prepared = True

    def limpar(self) -> None:
        with self._lock:
            self._atlas.clear()
            self._explorados_mundo.clear()
            self._prepared = False

    def apagar_cache_persistente(self) -> None:
        with self._lock:
            self._atlas.clear()
            self._atlas_manifest.clear()
            self._explorados_mundo.clear()
            self._manifest = {}
            self._manifest_dirty = False
        try:
            if self.pasta_cache.exists():
                for item in self.pasta_cache.glob("*"):
                    if item.is_file():
                        item.unlink(missing_ok=True)
        except Exception:
            pass

    def flush(self) -> None:
        payloads: list[tuple[pygame.Surface, Path, pygame.Surface, Path]] = []
        salvar_manifest = False
        manifest_payload: Dict[str, object] = {}
        houve_salvamento = False
        with self._lock:
            for atlas in self._atlas.values():
                if not atlas.chunks_explorados:
                    continue
                if not (atlas.dirty_base or atlas.dirty_regioes):
                    continue
                payloads.append((atlas.surface_base.copy(), atlas.path_base, atlas.surface_regioes.copy(), atlas.path_regioes))
                atlas.dirty_base = False
                atlas.dirty_regioes = False
            if self._manifest_dirty:
                manifest_payload = self._manifest_payload()
                salvar_manifest = True
                self._manifest_dirty = False
                houve_salvamento = True
        for base, path_base, reg, path_reg in payloads:
            pygame.image.save(base, str(path_base))
            pygame.image.save(reg, str(path_reg))
            houve_salvamento = True
        if salvar_manifest:
            try:
                self.path_manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        if houve_salvamento:
            with self._lock:
                self._ultimo_flush_s = time.monotonic()
                self._chunks_pendentes_flush = 0

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
        return self._obter_ou_carregar_atlas(ax, ay)

    def obter_atlas(self, atlas_x: int, atlas_y: int) -> AtlasMapa | None:
        with self._lock:
            ax, ay = int(atlas_x), int(atlas_y)
            if (ax, ay) in self._atlas_manifest or (ax, ay) in self._atlas:
                return self._obter_ou_carregar_atlas(ax, ay)
            return None

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
            return self._cor_fallback_regiao(int(regiao_id))
        cor = reg.get("cor") if isinstance(reg.get("cor"), (list, tuple)) else reg.get("cor_rgb")
        if isinstance(cor, (list, tuple)) and len(cor) == 3:
            return (int(cor[0]), int(cor[1]), int(cor[2]))
        return self._cor_fallback_regiao(int(regiao_id), nome=str(reg.get("nome") or ""))

    @staticmethod
    def _cor_fallback_regiao(regiao_id: int, nome: str = "") -> Tuple[int, int, int]:
        h = (int(regiao_id) * 1103515245 + 12345 + (sum(ord(c) for c in str(nome)) * 97)) & 0xFFFFFFFF
        r = 70 + ((h >> 16) & 0x7F)
        g = 70 + ((h >> 8) & 0x7F)
        b = 70 + (h & 0x7F)
        return (int(r), int(g), int(b))

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
                rid = reg.get("id", -1)
                try:
                    melhor_id = int(rid)
                except Exception:
                    melhor_id = -1
        if melhor_id < 0 and self._regioes:
            try:
                melhor_id = int(self._regioes[0].get("id", 1) or 1)
            except Exception:
                melhor_id = 1
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
                    objetos = chunk.get("objetos") if isinstance(chunk.get("objetos"), list) else []
                    self._desenhar_chunk_no_atlas(atlas, cx, cy, grid, objetos=objetos)
                    atlas.chunks_explorados.add((cx, cy))
                    self._explorados_mundo.setdefault(cx, set()).add(cy)
                    self._registrar_chunk_manifest(cx, cy, atlas)
                    alterados += 1
            if alterados > 0:
                self._versao_mapa += 1
                self._chunks_pendentes_flush += int(alterados)
                precisa_flush = (self._chunks_pendentes_flush >= self._flush_chunks_limite) or (
                    (time.monotonic() - float(self._ultimo_flush_s or 0.0)) >= self._flush_intervalo_s
                )
            else:
                precisa_flush = False
        if precisa_flush:
            self.flush()
        return alterados

    def _desenhar_chunk_no_atlas(self, atlas: AtlasMapa, cx: int, cy: int, grid: List[List[int]], objetos: list | None = None) -> None:
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
        self._desenhar_objetos_chunk(atlas, cx, cy, objetos or [])
        atlas.dirty_base = True
        atlas.dirty_regioes = True
        atlas.versao += 1

    def _desenhar_objetos_chunk(self, atlas: AtlasMapa, cx: int, cy: int, objetos: list) -> None:
        if not objetos:
            return
        inicio_x = (int(cx) % self.atlas_chunks_lado) * self.chunk_blocos
        inicio_y = (int(cy) % self.atlas_chunks_lado) * self.chunk_blocos
        for obj in objetos:
            if not isinstance(obj, dict):
                continue
            pos = obj.get("pos")
            if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                continue
            lx = int(float(pos[0])) - (int(cx) * self.chunk_blocos)
            ly = int(float(pos[1])) - (int(cy) * self.chunk_blocos)
            if lx < 0 or ly < 0 or lx >= self.chunk_blocos or ly >= self.chunk_blocos:
                continue
            categoria = str(obj.get("categoria") or obj.get("subtipo") or obj.get("tipo") or "").lower()
            if any(ch in categoria for ch in ("tree", "arvore", "bush", "planta", "folha", "veget")):
                cor = OBJETO_CORES["vegetacao"]
            elif any(ch in categoria for ch in ("rock", "pedra", "ore", "miner", "metal", "crist")):
                cor = OBJETO_CORES["mineral"]
            elif any(ch in categoria for ch in ("bau", "chest", "loot", "item")):
                cor = OBJETO_CORES["bau"]
            else:
                cor = OBJETO_CORES["estrutura"]
            px = inicio_x + lx
            py = inicio_y + ly
            atlas.surface_base.set_at((px, py), cor)
            atlas.surface_regioes.set_at((px, py), cor)

    def salvar_debug_atlas(self) -> None:
        self.flush()

    def atlas_visiveis(self, camera_rect_mundo_px: pygame.Rect) -> List[AtlasMapa]:
        if camera_rect_mundo_px.width <= 0 or camera_rect_mundo_px.height <= 0:
            return []
        with self._lock:
            out: List[AtlasMapa] = []
            candidatos = set(self.atlas_keys_no_rect(camera_rect_mundo_px.x, camera_rect_mundo_px.y, camera_rect_mundo_px.width, camera_rect_mundo_px.height))
            candidatos.update(self._atlas.keys())
            for key in candidatos:
                if key not in self._atlas_manifest and key not in self._atlas:
                    continue
                atlas = self._obter_ou_carregar_atlas(*key)
                if not atlas.chunks_explorados:
                    continue
                rect = pygame.Rect(atlas.atlas_x * self.atlas_px, atlas.atlas_y * self.atlas_px, self.atlas_px, self.atlas_px)
                if rect.colliderect(camera_rect_mundo_px):
                    out.append(atlas)
            return out

    def all_atlas(self) -> List[AtlasMapa]:
        with self._lock:
            return list(self._atlas.values())

    def conhecidos_payload(self) -> Dict[str, object]:
        with self._lock:
            self._garantir_manifest_carregado()
            atlas = []
            for (ax, ay), reg in self._atlas_manifest.items():
                chunks = [[int(cx), int(cy)] for cx, cy in sorted(reg.get("chunks", set()))]
                atlas.append({"atlas": [int(ax), int(ay)], "versao": int(reg.get("versao", 0) or 0), "chunks": chunks})
            return {"atlas": atlas}

    def garantir_manifest_carregado(self) -> None:
        with self._lock:
            self._garantir_manifest_carregado()

    def versao_mapa(self) -> int:
        with self._lock:
            return int(self._versao_mapa)

    def mundo_tamanho_px(self) -> Tuple[int, int]:
        largura_blocos = int(self.meta.get("largura_blocos", 0) or 0)
        altura_blocos = int(self.meta.get("altura_blocos", 0) or 0)
        return (max(1, largura_blocos), max(1, altura_blocos))

    @staticmethod
    def _normalizar_id(valor: str, fallback: str) -> str:
        base = "".join(ch if (ch.isalnum() or ch in ("-", "_", ".")) else "_" for ch in str(valor or "").strip())
        return base or fallback

    def _surface_preta(self) -> pygame.Surface:
        surf = pygame.Surface((self.atlas_px, self.atlas_px))
        surf.fill((0, 0, 0))
        return surf

    def _path_atlas(self, ax: int, ay: int) -> Tuple[Path, Path]:
        return (
            self.pasta_cache / f"atlas_{ax}_{ay}_base.png",
            self.pasta_cache / f"atlas_{ax}_{ay}_regioes.png",
        )

    def _obter_ou_carregar_atlas(self, ax: int, ay: int) -> AtlasMapa:
        chave = (int(ax), int(ay))
        atlas = self._atlas.get(chave)
        if atlas is not None:
            return atlas
        base_path, reg_path = self._path_atlas(*chave)
        sbase = self._surface_preta()
        sreg = self._surface_preta()
        if base_path.exists():
            try:
                img = pygame.image.load(str(base_path))
                if img.get_size() == (self.atlas_px, self.atlas_px):
                    sbase = img
            except Exception:
                pass
        if reg_path.exists():
            try:
                img = pygame.image.load(str(reg_path))
                if img.get_size() == (self.atlas_px, self.atlas_px):
                    sreg = img
            except Exception:
                pass
        atlas = AtlasMapa(chave[0], chave[1], base_path, reg_path, sbase, sreg)
        reg = self._atlas_manifest.get(chave, {})
        atlas.chunks_explorados = set(reg.get("chunks", set()))
        atlas.versao = int(reg.get("versao", 0) or 0)
        self._atlas[chave] = atlas
        return atlas

    def _carregar_manifest(self) -> None:
        self._manifest = {}
        self._manifest_carregado = True
        bruto = {}
        try:
            if self.path_manifest.exists():
                bruto = json.loads(self.path_manifest.read_text(encoding="utf-8"))
        except Exception:
            bruto = {}
        self._manifest = bruto if isinstance(bruto, dict) else {}
        atlas_entries = self._manifest.get("atlas") if isinstance(self._manifest.get("atlas"), list) else []
        for item in atlas_entries:
            if not isinstance(item, dict):
                continue
            atlas_pos = item.get("atlas")
            if not (isinstance(atlas_pos, (list, tuple)) and len(atlas_pos) == 2):
                continue
            ax, ay = int(atlas_pos[0]), int(atlas_pos[1])
            chunks_raw = item.get("chunks") if isinstance(item.get("chunks"), list) else []
            chunks = set()
            for pos in chunks_raw:
                if isinstance(pos, (list, tuple)) and len(pos) == 2:
                    chunks.add((int(pos[0]), int(pos[1])))
            self._atlas_manifest[(ax, ay)] = {
                "chunks": chunks,
                "versao": int(item.get("versao", 0) or 0),
            }
        for base_path in self.pasta_cache.glob("atlas_*_*_base.png"):
            partes = base_path.stem.split("_")
            if len(partes) < 4:
                continue
            try:
                ax, ay = int(partes[1]), int(partes[2])
            except Exception:
                continue
            self._atlas_manifest.setdefault((ax, ay), {"chunks": set(), "versao": 0})

    def _garantir_manifest_carregado(self) -> None:
        if self._manifest_carregado:
            return
        self._carregar_manifest()

    def _manifest_payload(self) -> Dict[str, object]:
        atlas = []
        for (ax, ay), reg in sorted(self._atlas_manifest.items(), key=lambda it: (it[0][1], it[0][0])):
            chunks = [[int(cx), int(cy)] for cx, cy in sorted(reg.get("chunks", set()))]
            atlas.append({"atlas": [int(ax), int(ay)], "versao": int(reg.get("versao", 0) or 0), "chunks": chunks})
        return {
            "server_id": self.server_id,
            "client_id": self.client_id,
            "chunk_blocos": int(self.chunk_blocos),
            "atlas_chunks_lado": int(self.atlas_chunks_lado),
            "atlas_px": int(self.atlas_px),
            "atlas": atlas,
        }

    def _sincronizar_manifest_meta(self) -> None:
        mudou = False
        if int(self._manifest.get("chunk_blocos", 0) or 0) != int(self.chunk_blocos):
            mudou = True
        if int(self._manifest.get("atlas_chunks_lado", 0) or 0) != int(self.atlas_chunks_lado):
            mudou = True
        if int(self._manifest.get("atlas_px", 0) or 0) != int(self.atlas_px):
            mudou = True
        if str(self._manifest.get("server_id", "")) != self.server_id:
            mudou = True
        if str(self._manifest.get("client_id", "")) != self.client_id:
            mudou = True
        if mudou:
            self._manifest_dirty = True

    def _mesclar_explorados_manifest(self) -> None:
        for reg in self._atlas_manifest.values():
            for cx, cy in reg.get("chunks", set()):
                self._explorados_mundo.setdefault(int(cx), set()).add(int(cy))

    def _registrar_chunk_manifest(self, cx: int, cy: int, atlas: AtlasMapa) -> None:
        chave = (int(atlas.atlas_x), int(atlas.atlas_y))
        reg = self._atlas_manifest.setdefault(chave, {"chunks": set(), "versao": 0})
        if (int(cx), int(cy)) not in reg["chunks"]:
            reg["chunks"].add((int(cx), int(cy)))
            self._manifest_dirty = True
        reg["versao"] = max(int(reg.get("versao", 0) or 0), int(atlas.versao))
        self._manifest_dirty = True
