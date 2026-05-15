"""Controlador de objetos NÃO-player do mundo."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math
import threading

import pygame

from Codigo.ModulosMundo.AtualizadorObjetos import AtualizadorObjetosMixin
from Codigo.ModulosMundo.RenderizadorObjetos import RenderizadorObjetosMixin
from Codigo.ModulosMundo.InteracoesObjetos import InteracoesObjetosMixin
from Codigo.ModulosMundo.Geradores.Baus import Bau
from Codigo.ModulosMundo.Geradores.Armadilhas import ArmadilhasDungeon
from Codigo.ModulosMundo.Geradores.EstruturaNaturais import EstruturaNatural
from Codigo.ModulosMundo.Geradores.PokemonMundo import Pokemon
from Codigo.ModulosMundo.ControladorAtores import ControladorAtores
from Codigo.ModulosMundo.ControladorCriaveis import ControladorCriaveis


class ControladorObjetos(
    AtualizadorObjetosMixin,
    RenderizadorObjetosMixin,
    InteracoesObjetosMixin,
):
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PokemonsPorId: Dict[int, Pokemon] = {}
        self.BausPorId: Dict[int, Bau] = {}
        self._atores = ControladorAtores()
        self.AtoresRemotosPorId = self._atores.AtoresRemotosPorId
        self.EstruturasPorId: Dict[int, EstruturaNatural] = {}
        self.EstadiosPorId: Dict[int, Dict[str, object]] = {}

        self._player_local_id: Optional[int] = None
        self._player_local_ref = None
        self._autor_local_id: str = ""
        self._dimensao_atual_client: str = "Mundo"
        self._lock_objetos = threading.RLock()
        self._lock_diffs = threading.Lock()
        self._fila_saida_envio: List[Dict[str, object]] = []

        self._chunk_tamanho_tiles = 10
        self._ids_por_chunk: Dict[Tuple[int, int], set[int]] = {}
        self._chunk_por_objeto: Dict[int, Tuple[int, int]] = {}
        self._cache_objetos_visiveis: Dict[Tuple[object, ...], List[Dict[str, object]]] = {}
        self._versao_objetos_visiveis = 0
        self._cache_estruturas_visiveis: Dict[Tuple[object, ...], List[Dict[str, object]]] = {}
        self._versao_estruturas_visiveis = 0
        self._cache_cfg_natural: Dict[object, Optional[Dict[str, object]]] = {}

        self._cache_sprites_fallback: Dict[str, Optional[pygame.Surface]] = {}
        self._cache_sprites_fallback_escalados: Dict[Tuple[object, ...], pygame.Surface] = {}
        self._ultimo_render_pokemons_ms = pygame.time.get_ticks()
        self._pokemon_alvo_local_id: Optional[int] = None
        self._capturas_por_token: Dict[str, Dict[str, object]] = {}
        self._criaveis = ControladorCriaveis(objetos_por_id=self.ObjetosPorId, remover_indice_cb=self._remover_indice_chunk_objeto)
        self.LayoutDungeonAtual: Dict[str, object] = {}
        self.ArmadilhasDungeon = ArmadilhasDungeon()

    @property
    def ProjeteisPorId(self):
        return self._criaveis.ProjeteisPorId

    @property
    def ItensMundoPorId(self):
        return self._criaveis.ItensMundoPorId

    def definir_player_local_info(self, player) -> None:
        self._player_local_id = int(getattr(player, "Id", -1) or -1) if player is not None else None
        self._player_local_ref = player

    def definir_autor_local(self, autor_id: str) -> None:
        self._autor_local_id = str(autor_id or "").strip()

    def autor_local(self) -> str:
        return str(self._autor_local_id or "")

    def id_player_local(self) -> int:
        return int(self._player_local_id or -1)

    def definir_dimensao_atual_client(self, dimensao: str) -> None:
        self._dimensao_atual_client = str(dimensao or "Mundo")
        with self._lock_objetos:
            self._invalidar_cache_objetos_visiveis_locked()
            self._invalidar_cache_estruturas_visiveis_locked()

    def dimensao_atual_client(self) -> str:
        return str(self._dimensao_atual_client or "Mundo")

    def definir_layout_dungeon_atual(self, layout) -> None:
        anterior = self.LayoutDungeonAtual if isinstance(self.LayoutDungeonAtual, dict) else {}
        novo = dict(layout) if isinstance(layout, dict) else {}
        if "estado_armadilhas" not in novo and isinstance(anterior.get("estado_armadilhas"), dict):
            novo["estado_armadilhas"] = anterior.get("estado_armadilhas")
        self.LayoutDungeonAtual = novo

    def _dimensao_player_local(self) -> str:
        return self.dimensao_atual_client()

    def _payload_na_dimensao_local(self, payload: Dict[str, object]) -> bool:
        dim_local = self._dimensao_player_local()
        if self._eh_payload_estadio(payload):
            estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
            dim_obj = str(estado.get("dimensao") or payload.get("dimensao") or "Mundo")
            return dim_local == "Mundo" and dim_obj == "Mundo"
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        dim = str(estado.get("dimensao") or payload.get("dimensao") or "Mundo")
        return dim == dim_local

    def _chunk_posicao(self, x: float, y: float) -> Tuple[int, int]:
        return (int(math.floor(float(x) / self._chunk_tamanho_tiles)), int(math.floor(float(y) / self._chunk_tamanho_tiles)))

    def _invalidar_cache_objetos_visiveis_locked(self) -> None:
        self._cache_objetos_visiveis.clear()
        self._versao_objetos_visiveis += 1

    def _invalidar_cache_estruturas_visiveis_locked(self) -> None:
        self._cache_estruturas_visiveis.clear()
        self._versao_estruturas_visiveis += 1

    def _upsert_indice_chunk_objeto(self, oid: int, payload: Dict[str, object]) -> None:
        chunk_antigo = self._chunk_por_objeto.pop(oid, None)
        if chunk_antigo is not None:
            bucket = self._ids_por_chunk.get(chunk_antigo)
            if bucket is not None:
                bucket.discard(oid)
                if not bucket:
                    self._ids_por_chunk.pop(chunk_antigo, None)

        pos = payload.get("posicao")
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return
        chunk = self._chunk_posicao(float(pos[0]), float(pos[1]))
        self._chunk_por_objeto[oid] = chunk
        self._ids_por_chunk.setdefault(chunk, set()).add(oid)

    def _remover_indice_chunk_objeto(self, oid: int) -> None:
        chunk = self._chunk_por_objeto.pop(int(oid), None)
        if chunk is None:
            return
        bucket = self._ids_por_chunk.get(chunk)
        if bucket is not None:
            bucket.discard(int(oid))
            if not bucket:
                self._ids_por_chunk.pop(chunk, None)

    def _iter_objetos_visiveis_por_chunk(self, camera, margem_chunks: int = 1):
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        tile_px = max(1.0, float(getattr(camera, "TilePx", 50) or 50))
        centro_tiles = (float(camera.PosicaoTiles[0]) + (float(tela_w) * 0.5) / tile_px, float(camera.PosicaoTiles[1]) + (float(tela_h) * 0.5) / tile_px)
        cx, cy = self._chunk_posicao(*centro_tiles)
        alcance_x = max(1, int(math.ceil((float(tela_w) / tile_px) / (2.0 * self._chunk_tamanho_tiles)))) + int(margem_chunks)
        alcance_y = max(1, int(math.ceil((float(tela_h) / tile_px) / (2.0 * self._chunk_tamanho_tiles)))) + int(margem_chunks)
        dim_local = self._dimensao_player_local()
        chave_cache = (self._versao_objetos_visiveis, dim_local, int(margem_chunks), int(cx), int(cy), int(alcance_x), int(alcance_y))
        with self._lock_objetos:
            cache = self._cache_objetos_visiveis.get(chave_cache)
            if cache is not None:
                return cache
            ids: set[int] = set()
            for dx in range(-alcance_x, alcance_x + 1):
                for dy in range(-alcance_y, alcance_y + 1):
                    ids.update(self._ids_por_chunk.get((cx + dx, cy + dy), set()))
            objetos: List[Dict[str, object]] = []
            for oid in ids:
                payload = self.ObjetosPorId.get(oid)
                if not isinstance(payload, dict):
                    continue
                estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                if self._eh_payload_estadio(payload):
                    dim_obj = str(estado.get("dimensao") or payload.get("dimensao") or "Mundo")
                    if dim_local != "Mundo" or dim_obj != "Mundo":
                        continue
                else:
                    dim_obj = str(estado.get("dimensao") or payload.get("dimensao") or "Mundo")
                    if dim_obj != dim_local:
                        continue
                objetos.append(payload)
            if len(self._cache_objetos_visiveis) >= 16:
                self._cache_objetos_visiveis.clear()
            self._cache_objetos_visiveis[chave_cache] = objetos
            return objetos

    def _estruturas_visiveis_ordenadas(self, camera, margem_chunks: int = 1) -> List[Dict[str, object]]:
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        tile_px = max(1.0, float(getattr(camera, "TilePx", 50) or 50))
        centro_tiles = (
            float(camera.PosicaoTiles[0]) + (float(tela_w) * 0.5) / tile_px,
            float(camera.PosicaoTiles[1]) + (float(tela_h) * 0.5) / tile_px,
        )
        cx, cy = self._chunk_posicao(*centro_tiles)
        alcance_x = max(1, int(math.ceil((float(tela_w) / tile_px) / (2.0 * self._chunk_tamanho_tiles)))) + int(margem_chunks)
        alcance_y = max(1, int(math.ceil((float(tela_h) / tile_px) / (2.0 * self._chunk_tamanho_tiles)))) + int(margem_chunks)
        dim_local = self._dimensao_player_local()
        chave_cache = (
            self._versao_estruturas_visiveis,
            dim_local,
            int(margem_chunks),
            int(cx),
            int(cy),
            int(alcance_x),
            int(alcance_y),
        )
        with self._lock_objetos:
            cache = self._cache_estruturas_visiveis.get(chave_cache)
            if cache is not None:
                return cache

            ids: set[int] = set()
            for dx in range(-alcance_x, alcance_x + 1):
                for dy in range(-alcance_y, alcance_y + 1):
                    ids.update(self._ids_por_chunk.get((cx + dx, cy + dy), set()))

            objs: List[Dict[str, object]] = []
            vistos_ids: set[int] = set()
            for oid in ids:
                payload = self.ObjetosPorId.get(oid)
                if not isinstance(payload, dict):
                    continue
                if not (self._eh_payload_estrutura(payload) or self._eh_payload_estadio(payload)):
                    continue
                if not self._payload_na_dimensao_local(payload):
                    continue
                oid_payload = int(payload.get("id", oid) or oid)
                vistos_ids.add(oid_payload)
                objs.append(payload)

            if dim_local == "Mundo":
                for estadio in list(self.EstadiosPorId.values()):
                    if not isinstance(estadio, dict):
                        continue
                    estado_estadio = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}
                    dim_estadio = str(estado_estadio.get("dimensao") or estadio.get("dimensao") or "Mundo")
                    if dim_estadio != "Mundo":
                        continue
                    oid_estadio = int(estadio.get("id", 0) or 0)
                    if oid_estadio in vistos_ids:
                        continue
                    objs.append(estadio)

            if len(self._cache_estruturas_visiveis) >= 16:
                self._cache_estruturas_visiveis.clear()
            self._cache_estruturas_visiveis[chave_cache] = objs
            return objs
