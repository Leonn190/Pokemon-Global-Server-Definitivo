"""Controlador de objetos NÃO-player do mundo."""

from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple
import math
import os
import threading

import pygame

from Codigo.Geradores.Baus import Bau
from Codigo.Geradores.EstruturaNaturais import (
    EstruturaNatural,
    limitar_escala_estrutura_natural,
    prioridade_estrutura_natural,
    tipo_estrutura_natural_por_codigo,
)
from Codigo.Geradores.Estadio import GeradorEstadio, EstadioInterno
from Codigo.Geradores.PokemonMundo import Pokemon
from Codigo.Geradores.Projetil import Projetil
from Codigo.ModulosMundo.ControladorAtores import ControladorAtores
from Codigo.ModulosMundo.ControladorCriaveis import ControladorCriaveis


class ControladorObjetos:
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

        self._cache_sprites_fallback: Dict[str, Optional[pygame.Surface]] = {}
        self._cache_sprites_fallback_escalados: Dict[Tuple[str, int, int], pygame.Surface] = {}
        self._ultimo_render_pokemons_ms = pygame.time.get_ticks()
        self._pokemon_alvo_local_id: Optional[int] = None
        self._capturas_por_token: Dict[str, Dict[str, object]] = {}
        self._criaveis = ControladorCriaveis(objetos_por_id=self.ObjetosPorId, remover_indice_cb=self._remover_indice_chunk_objeto)

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

            objs.sort(
                key=lambda o: (
                    prioridade_estrutura_natural(
                        codigo=o.get("codigo_natural"),
                        subtipo=(o.get("estado", {}) if isinstance(o.get("estado"), dict) else {}).get("subtipo"),
                    ),
                    float((o.get("posicao") or [0.0, 0.0])[1] if isinstance(o.get("posicao"), (list, tuple)) and len(o.get("posicao")) == 2 else 0.0),
                    int(o.get("id", 0) or 0),
                )
            )
            if len(self._cache_estruturas_visiveis) >= 16:
                self._cache_estruturas_visiveis.clear()
            self._cache_estruturas_visiveis[chave_cache] = objs
            return objs


    def _payload_tem_colisao_solida(self, payload: Dict[str, object]) -> bool:
        if not isinstance(payload, dict):
            return False
        tipo = str(payload.get("tipo", "")).strip().lower()
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        subtipo = str(estado.get("subtipo", "")).strip().lower()

        if tipo == "entidade_player":
            return True
        if self._eh_payload_pokemon(payload):
            return True
        if self._eh_payload_ator(payload):
            return True
        if self._eh_payload_bau(payload):
            return True
        if self._eh_payload_estrutura(payload):
            return True
        if self._eh_payload_estadio(payload):
            return True

        if tipo in {"entidade_item_mundo", "item_mundo", "entidade_projetil", "projetil", "entidade_xp_mundo", "xp_mundo"}:
            return False
        if subtipo in {"item_mundo", "projetil", "xp_mundo"}:
            return False
        return False

    def iter_colisores_proximos_por_raio(self, posicao: Tuple[float, float], raio_tiles: float = 10.0):
        px, py = float(posicao[0]), float(posicao[1])
        chunk_cx, chunk_cy = self._chunk_posicao(px, py)
        alcance = max(1, int(math.ceil(float(raio_tiles) / float(self._chunk_tamanho_tiles))))

        with self._lock_objetos:
            ids = set()
            for dx in range(-alcance, alcance + 1):
                for dy in range(-alcance, alcance + 1):
                    ids.update(self._ids_por_chunk.get((chunk_cx + dx, chunk_cy + dy), set()))
            objs = [self.ObjetosPorId.get(oid) for oid in ids]

        r2 = raio_tiles * raio_tiles
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            if not self._payload_na_dimensao_local(obj):
                continue
            if not self._payload_tem_colisao_solida(obj):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            if ((sx - px) ** 2 + (sy - py) ** 2) > r2:
                continue
            raio = float(obj.get("raio_colisao", 0.0) or 0.0)
            if raio <= 0.0:
                continue
            tipo_obj = str(obj.get("tipo", ""))
            if self._eh_payload_bau(obj):
                tipo_obj = "estrutura_bau"
            if self._eh_payload_estadio(obj):
                estado_obj = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
                rx_visual = float(estado_obj.get("raio_elipse_x", raio) or raio)
                ry_visual = float(estado_obj.get("raio_elipse_y", raio) or raio)
                rx_casco, ry_casco = GeradorEstadio.raios_casco_colisao(rx_visual, ry_visual)
                off_casco_x, off_casco_y = GeradorEstadio.deslocamento_casco_colisao(ry_visual)
                yield (
                    int(obj.get("id", 0)), sx + off_casco_x, sy + off_casco_y, raio, "estrutura_estadio",
                    float(obj.get("campo", 0.0) or 0.0), float(obj.get("intensidade", 0.0) or 0.0),
                    "elipse", rx_casco, ry_casco,
                )
                continue
            yield (int(obj.get("id", 0)), sx, sy, raio, tipo_obj, float(obj.get("campo", 0.0) or 0.0), float(obj.get("intensidade", 0.0) or 0.0))

    def estrutura_colidindo(self, posicao: Tuple[float, float], raio: float) -> Optional[Dict[str, object]]:
        colisoes = self.estruturas_colidindo(posicao, raio)
        return colisoes[0] if colisoes else None

    def estruturas_colidindo(self, posicao: Tuple[float, float], raio: float) -> List[Dict[str, object]]:
        px, py = float(posicao[0]), float(posicao[1])
        encontrados: List[Tuple[float, Dict[str, object]]] = []
        with self._lock_objetos:
            estruturas = [self.ObjetosPorId.get(oid) for oid in self.EstruturasPorId.keys()]
        for obj in estruturas:
            if not isinstance(obj, dict):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            rr = float(obj.get("raio_colisao", 0.0) or 0.0) + max(0.0, float(raio))
            d2 = (sx - px) ** 2 + (sy - py) ** 2
            if d2 > (rr * rr):
                continue
            encontrados.append((d2, obj))
        encontrados.sort(key=lambda par: par[0])
        return [obj for _, obj in encontrados]

    def baus_colidindo(self, posicao: Tuple[float, float], raio: float) -> List[Dict[str, object]]:
        px, py = float(posicao[0]), float(posicao[1])
        encontrados: List[Tuple[float, Dict[str, object]]] = []
        with self._lock_objetos:
            baus = [self.ObjetosPorId.get(oid) for oid in self.BausPorId.keys()]
        for obj in baus:
            if not isinstance(obj, dict):
                continue
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            if bool(estado.get("aberto", False)):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            rr = float(obj.get("raio_colisao", 0.0) or 0.0) + max(0.0, float(raio))
            d2 = (sx - px) ** 2 + (sy - py) ** 2
            if d2 > (rr * rr):
                continue
            encontrados.append((d2, obj))
        encontrados.sort(key=lambda par: par[0])
        return [obj for _, obj in encontrados]

    def _marcar_diff_local(self, diff: Dict[str, object]) -> Dict[str, object]:
        if "autor" not in diff:
            diff["autor"] = self.autor_local() or "anon"
        return diff

    def EnfileirarDiffRapida(self, diff: Dict[str, object]) -> None:
        with self._lock_diffs:
            self._fila_saida_envio.append(self._marcar_diff_local(dict(diff)))

    def EnfileirarDiffLenta(self, diff: Dict[str, object]) -> None:
        self.EnfileirarDiffRapida(diff)

    def ColetarDiffsRapidas(self) -> List[Dict[str, object]]:
        with self._lock_diffs:
            lote = self._fila_saida_envio
            self._fila_saida_envio = []
        return lote

    def snapshot_objeto_por_id(self, objeto_id: int) -> Optional[Dict[str, object]]:
        oid = int(objeto_id or 0)
        if oid <= 0:
            return None
        with self._lock_objetos:
            payload = self.ObjetosPorId.get(oid)
            return copy.deepcopy(payload) if isinstance(payload, dict) else None

    def _eh_payload_pokemon(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", "")).strip().lower()
        if tipo in ("entidade_pokemon", "pokemon"):
            return True
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return str(estado.get("subtipo", "")).strip().lower() == "pokemon"

    def _eh_payload_bau(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", ""))
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return tipo.startswith("entidade") and str(estado.get("subtipo", "")).strip().lower() == "bau"

    def _eh_payload_ator(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", "")).strip().lower()
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        if tipo in {"entidade_player", "player"}:
            return True
        subtipo = str(estado.get("subtipo", "")).strip().lower()
        return subtipo == "player" or ControladorAtores._eh_npc_estado(estado)

    def _eh_payload_projetil(self, payload: Dict[str, object]) -> bool:
        return self._criaveis.eh_payload_projetil(payload)

    def _eh_payload_estrutura(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"estrutura_natural", "estrutura"}

    def _eh_payload_estadio(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"entidade_estadio", "estadio"}

    def _reconciliar_projetil_predito_por_token(self, oid_oficial: int, payload: Dict[str, object]) -> None:
        self._criaveis.reconciliar_projetil_predito_por_token(oid_oficial, payload)

    def _upsert_especializado(self, oid: int, payload: Dict[str, object]) -> None:
        if self._eh_payload_pokemon(payload):
            poke = self.PokemonsPorId.get(oid)
            if poke is None:
                self.PokemonsPorId[oid] = Pokemon(payload)
            else:
                poke.update(payload) if hasattr(poke, "update") else poke.aplicar_snapshot(payload)
        else:
            self.PokemonsPorId.pop(oid, None)

        if self._eh_payload_bau(payload):
            bau = self.BausPorId.get(oid)
            if bau is None:
                self.BausPorId[oid] = Bau.from_snapshot(payload)
            else:
                aberto_antes = bool(getattr(bau, "Aberto", False))
                bau.update(payload) if hasattr(bau, "update") else bau.aplicar_snapshot(payload)
                if (not aberto_antes) and bool(getattr(bau, "Aberto", False)):
                    perfil = getattr(self._player_local_ref, "Perfil", None) if self._player_local_ref is not None else None
                    if perfil is not None:
                        perfil.registrar_bau_aberto(1)
        else:
            self.BausPorId.pop(oid, None)

        self._atores.upsert(oid, payload, id_player_local=self.id_player_local())

        self._criaveis.upsert_criavel(oid, payload)

        if self._eh_payload_estrutura(payload):
            est = self.EstruturasPorId.get(oid)
            if est is None:
                estado_payload = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                est = EstruturaNatural(tipo=str(estado_payload.get("subtipo", "natural")), posicao=tuple(payload.get("posicao", [0.0, 0.0])), id_objeto=oid, raio_colisao=float(payload.get("raio_colisao", 0.8)), raio_interacao=float(payload.get("raio_interacao", 0.8)), campo=float(payload.get("campo", 0.0)), intensidade=float(payload.get("intensidade", 0.0)), quantidade=int(estado_payload.get("quantidade", 0) or 0), material=str(estado_payload.get("material", "") or ""), estilo=str(estado_payload.get("estilo", "") or ""), dureza=int(estado_payload.get("dureza", 1) or 1))
                self.EstruturasPorId[oid] = est
            est.update(payload)
        else:
            self.EstruturasPorId.pop(oid, None)

        if self._eh_payload_estadio(payload):
            self.EstadiosPorId[oid] = payload
        else:
            self.EstadiosPorId.pop(oid, None)


    def aplicar_diff(self, diff):
        if not isinstance(diff, dict):
            return

        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}

        categoria = str(diff.get("categoria", "")).strip().lower()

        if tipo == "spawn" and self._criaveis.aplicar_spawn_especial(categoria, payload, self.aplicar_diff):
            return

        if tipo == "spawn":
            oid = int(payload.get("id", objeto_id or 0))
            dados = dict(payload)
            dados["id"] = oid
            with self._lock_objetos:
                self.ObjetosPorId[oid] = dados
                self._upsert_indice_chunk_objeto(oid, dados)
                self._upsert_especializado(oid, dados)
                self._invalidar_cache_objetos_visiveis_locked()
                if self._eh_payload_estrutura(dados) or self._eh_payload_estadio(dados):
                    self._invalidar_cache_estruturas_visiveis_locked()
            return

        if objeto_id is None:
            return
        oid = int(objeto_id)

        if tipo == "update":
            with self._lock_objetos:
                atual = self.ObjetosPorId.get(oid, {"id": oid})
                estado_novo = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                if estado_novo:
                    estado = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
                    estado.update(estado_novo)
                    atual["estado"] = estado
                for chave, valor in payload.items():
                    if chave != "estado":
                        atual[chave] = valor
                self.ObjetosPorId[oid] = atual
                self._upsert_indice_chunk_objeto(oid, atual)
                self._upsert_especializado(oid, atual)
                self._invalidar_cache_objetos_visiveis_locked()
                if self._eh_payload_estrutura(atual) or self._eh_payload_estadio(atual):
                    self._invalidar_cache_estruturas_visiveis_locked()
                estado_atual = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
                captura_atual = estado_atual.get("captura") if isinstance(estado_atual.get("captura"), dict) else {}
                if str(estado_atual.get("subtipo", "")).strip().lower() == "pokemon" and captura_atual:
                    self._registrar_confirmacao_servidor_captura(atual)
            return

        if tipo == "despawn":
            with self._lock_objetos:
                payload_atual = self.ObjetosPorId.get(oid, {})
                remover_cache_estruturas = (
                    oid in self.EstruturasPorId
                    or oid in self.EstadiosPorId
                    or (isinstance(payload_atual, dict) and (self._eh_payload_estrutura(payload_atual) or self._eh_payload_estadio(payload_atual)))
                )
                poke = self.PokemonsPorId.get(oid)
                if poke is not None and hasattr(poke, "deve_adiar_despawn") and poke.deve_adiar_despawn():
                    if hasattr(poke, "solicitar_despawn_apos_animacao"):
                        poke.solicitar_despawn_apos_animacao()
                    return
                self.ObjetosPorId.pop(oid, None)
                self.PokemonsPorId.pop(oid, None)
                self.BausPorId.pop(oid, None)
                self._atores.remover(oid)
                self._criaveis.remover_criavel(oid)
                self.EstruturasPorId.pop(oid, None)
                self.EstadiosPorId.pop(oid, None)
                self._remover_indice_chunk_objeto(oid)
                self._invalidar_cache_objetos_visiveis_locked()
                if remover_cache_estruturas:
                    self._invalidar_cache_estruturas_visiveis_locked()

    def aplicar_pacote_tick(self, pacote_tick: Dict[str, object]) -> None:
        diffs = pacote_tick.get("diffs", []) if isinstance(pacote_tick, dict) else []
        if not isinstance(diffs, list):
            return
        for diff in diffs:
            if isinstance(diff, dict):
                self.aplicar_diff(diff)

    def _detectar_colisao_visual_local_projetil(self, proj: Projetil, objetos_snapshot: Dict[int, Dict[str, object]]):
        raio_busca = 4.0
        for oid, obj in objetos_snapshot.items():
            if not isinstance(obj, dict):
                continue
            if int(oid) == int(getattr(proj, "Id", 0) or 0):
                continue
            if int(oid) == int(getattr(proj, "DonoId", 0) or 0):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            dx = float(pos[0]) - float(proj.Posicao[0])
            dy = float(pos[1]) - float(proj.Posicao[1])
            d2 = (dx * dx) + (dy * dy)
            if d2 > (raio_busca * raio_busca):
                continue
            tipo = str(obj.get("tipo", "")).strip().lower()
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            subtipo = str(estado.get("subtipo", "")).strip().lower()
            if not (subtipo in {"pokemon", "player", "bau"} or tipo.startswith("estrutura")):
                continue
            raio_alvo = float(obj.get("raio_colisao", 0.2) or 0.2)
            limite = float(getattr(getattr(proj, "Colisor", None), "raio_colisao", 0.18)) + raio_alvo
            if d2 <= (limite * limite):
                return obj
        return None

    def _token_info(self, token: str) -> Dict[str, object]:
        token = str(token or "").strip()
        if not token:
            return {}
        return self._capturas_por_token.setdefault(token, {
            "server_confirmou": False,
            "server_confirmou_ms": 0,
            "colidiu_local": False,
            "colidiu_local_ms": 0,
        })

    def _registrar_colisao_local_projetil_pokemon(self, proj: Projetil, poke: Pokemon) -> None:
        token = str(getattr(proj, "TokenArremesso", "") or "").strip()
        if not token:
            return
        info = self._token_info(token)
        agora_ms = pygame.time.get_ticks()
        info["colidiu_local"] = True
        info["colidiu_local_ms"] = agora_ms
        if hasattr(poke, "registrar_colisao_projetil_local"):
            poke.registrar_colisao_projetil_local(token, nome_bola=str(getattr(proj, "ItemNome", "") or getattr(proj, "Subtipo", "pokeball")), tempo_espera_confirmacao_ms=1500)
        if bool(info.get("server_confirmou", False)) and hasattr(poke, "confirmar_captura_por_token"):
            poke.confirmar_captura_por_token(token, esperar_colisao=False, atraso_ms=0)

    def _registrar_confirmacao_servidor_captura(self, payload: Dict[str, object]) -> None:
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        if not bool(captura.get("captura_pendente", False)):
            return
        token = str(captura.get("token_arremesso") or "").strip()
        if not token:
            return
        info = self._token_info(token)
        info["server_confirmou"] = True
        info["server_confirmou_ms"] = pygame.time.get_ticks()
        poke = self.PokemonsPorId.get(int(payload.get("id", 0) or 0))
        if poke is None:
            return
        payload_captura = dict(captura)
        colidiu_local = bool(info.get("colidiu_local", False))
        if hasattr(poke, "aplicar_resultado_servidor_captura"):
            poke.aplicar_resultado_servidor_captura(payload_captura, esperar_colisao=not colidiu_local)
        elif hasattr(poke, "confirmar_captura_por_token"):
            poke.confirmar_captura_por_token(token, esperar_colisao=not colidiu_local, atraso_ms=0)

    def atualizar_projeteis_visuais(self, dt: float) -> None:
        with self._lock_objetos:
            objetos_snapshot = dict(self.ObjetosPorId)

        def _registrar_colisao(p, alvo_obj):
            if not isinstance(alvo_obj, dict):
                return
            poke = self.PokemonsPorId.get(int(alvo_obj.get("id", 0) or 0))
            if poke is not None:
                self._registrar_colisao_local_projetil_pokemon(p, poke)

        self._criaveis.atualizar_visuais(
            dt=dt,
            objetos_snapshot=objetos_snapshot,
            detectar_colisao_projetil_cb=self._detectar_colisao_visual_local_projetil,
            registrar_colisao_pokemon_cb=_registrar_colisao,
            aplicar_despawn_cb=lambda oid: self.aplicar_diff({"tipo": "despawn", "objeto_id": int(oid)}),
        )

    def _atualizar_alvo_local_captura(self, camera, player_pos: Optional[Tuple[float, float]] = None) -> None:
        if camera is None:
            self._pokemon_alvo_local_id = None
            return
        mouse_mundo = camera.tela_para_mundo_tiles(pygame.mouse.get_pos())
        mx, my = float(mouse_mundo[0]), float(mouse_mundo[1])
        px, py = (float(player_pos[0]), float(player_pos[1])) if player_pos is not None else (mx, my)

        melhor_id = None
        melhor_score = None
        with self._lock_objetos:
            itens = list(self.PokemonsPorId.items())
        for oid, poke in itens:
            fase = str(getattr(poke, "CapturaEstado", {}).get("fase", "nenhuma") or "nenhuma")
            pendente = bool(getattr(poke, "CapturaEstado", {}).get("captura_pendente", False))
            invalido = pendente or fase in {"captura", "checagem", "fuga", "volta"}
            if invalido:
                continue
            dxm, dym = float(poke.Posicao[0]) - mx, float(poke.Posicao[1]) - my
            dmouse = math.hypot(dxm, dym)
            if dmouse > 1.35:
                continue
            dplayer = math.hypot(float(poke.Posicao[0]) - px, float(poke.Posicao[1]) - py)
            if dplayer > 8.5:
                continue
            score = dmouse + (dplayer * 0.12)
            if melhor_score is None or score < melhor_score:
                melhor_score = score
                melhor_id = int(oid)

        self._pokemon_alvo_local_id = melhor_id
        for oid, poke in itens:
            poke.definir_alvo_local_captura(int(oid) == int(melhor_id) if melhor_id is not None else False)

    def _obter_sprite_fallback(self, caminho):
        caminho = str(caminho or "").strip()
        if not caminho:
            return None
        if caminho in self._cache_sprites_fallback:
            return self._cache_sprites_fallback[caminho]
        if not os.path.exists(caminho):
            self._cache_sprites_fallback[caminho] = None
            return None
        try:
            sprite = pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            sprite = None
        self._cache_sprites_fallback[caminho] = sprite
        return sprite

    def _obter_sprite_fallback_escalado(self, caminho: str, sprite: pygame.Surface, escala: float) -> pygame.Surface:
        largura = max(1, int(sprite.get_width() * escala))
        altura = max(1, int(sprite.get_height() * escala))
        chave = (str(caminho or ""), largura, altura)
        sprite_escalado = self._cache_sprites_fallback_escalados.get(chave)
        if sprite_escalado is not None:
            return sprite_escalado
        sprite_escalado = pygame.transform.smoothscale(sprite, (largura, altura))
        self._cache_sprites_fallback_escalados[chave] = sprite_escalado
        return sprite_escalado

    def _render_fallback_objeto(self, tela, camera, obj: Dict[str, object], cor_fallback=(222, 233, 245), escala: float = 1.0, pos_tela: Optional[Tuple[float, float]] = None, fila_blits: Optional[List[tuple]] = None):
        if pos_tela is None:
            pos = obj.get("posicao", [0.0, 0.0])
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                return
            px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
        else:
            px, py = pos_tela
        px_int = int(px)
        py_int = int(py)

        codigo_natural = obj.get("codigo_natural")
        if codigo_natural is None and isinstance(obj.get("estado"), dict):
            codigo_natural = obj["estado"].get("codigo_natural")
        cfg_natural = tipo_estrutura_natural_por_codigo(codigo_natural)

        sprite_path = str(obj.get("sprite", "")).strip()
        if not sprite_path and cfg_natural:
            sprite_path = str(cfg_natural.get("sprite", "")).strip()

        sprite = self._obter_sprite_fallback(sprite_path)
        if sprite is not None:
            escala = limitar_escala_estrutura_natural(float(escala or 1.0))
            if abs(escala - 1.0) > 0.001:
                sprite = self._obter_sprite_fallback_escalado(sprite_path, sprite, escala)
            largura_sprite = sprite.get_width()
            altura_sprite = sprite.get_height()
            destino_x = px_int - (largura_sprite // 2)
            destino_y = py_int - (altura_sprite // 2)
            tela_w, tela_h = tela.get_size()
            clip_x = max(0, -destino_x)
            clip_y = max(0, -destino_y)
            largura_visivel = min(largura_sprite - clip_x, int(tela_w) - max(0, destino_x))
            altura_visivel = min(altura_sprite - clip_y, int(tela_h) - max(0, destino_y))
            if largura_visivel <= 0 or altura_visivel <= 0:
                return
            destino = (destino_x, destino_y)
            area = None
            if clip_x > 0 or clip_y > 0 or largura_visivel != largura_sprite or altura_visivel != altura_sprite:
                destino = (destino_x + clip_x, destino_y + clip_y)
                area = (clip_x, clip_y, largura_visivel, altura_visivel)
            if fila_blits is not None:
                if area is not None:
                    fila_blits.append((sprite, destino, area))
                else:
                    fila_blits.append((sprite, destino))
                return
            if area is not None:
                tela.blit(sprite, destino, area)
            else:
                tela.blit(sprite, destino)
            return

        raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
        raio_px = int(raio_raw if raio_raw > 4.0 else raio_raw * camera.TilePx)
        raio_px = int(max(1.0, raio_px * limitar_escala_estrutura_natural(float(escala or 1.0))))
        raio_px = max(3, min(80, raio_px))
        pygame.draw.circle(tela, cor_fallback, (px_int, py_int), raio_px)

    @staticmethod
    def _aplicar_blits_batch(tela, fila_blits: List[tuple]) -> None:
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

    def _objeto_posicao_tela_se_visivel(self, obj: Dict[str, object], camera, margem_px: int = 120):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return None
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        if px < -margem_px or py < -margem_px or px > (tela_w + margem_px) or py > (tela_h + margem_px):
            return None
        return px, py

    def atualizar_visuais(self, dt: float, camera, ignorar_id=None, player_pos=None):
        dt = max(0.0, float(dt))
        self._atualizar_alvo_local_captura(camera, player_pos=player_pos)
        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue
            if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                continue
            poke = self.PokemonsPorId.get(oid)
            if poke is not None and hasattr(poke, "atualizar_visual"):
                poke.atualizar_visual(dt)
                continue
            bau = self.BausPorId.get(oid)
            if bau is not None and hasattr(bau, "atualizar_visual"):
                bau.atualizar_visual(dt)
                continue
            self._atores.atualizar_visual(oid, dt)

        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            if not str(obj.get("tipo", "")).startswith("estrutura"):
                continue
            est = self.EstruturasPorId.get(int(obj.get("id", 0) or 0))
            if est is not None and hasattr(est, "atualizar_visual"):
                est.atualizar_visual(dt)

    def renderizar_entidades(self, tela, camera, ignorar_id=None, player_pos=None):
        _ = player_pos

        remover_pokemons: List[int] = []
        fila_blits: List[Tuple[pygame.Surface, Tuple[int, int]]] = []
        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=1):
            if not isinstance(obj, dict):
                continue
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue
            if self._eh_payload_estrutura(obj) or self._eh_payload_estadio(obj):
                continue
            pos_tela = self._objeto_posicao_tela_se_visivel(obj, camera)
            if pos_tela is None:
                continue

            poke = self.PokemonsPorId.get(oid)
            if poke is not None:
                if fila_blits:
                    self._aplicar_blits_batch(tela, fila_blits)
                    fila_blits.clear()
                poke.render(tela, camera)
                if hasattr(poke, "pronto_para_remover_local") and poke.pronto_para_remover_local():
                    remover_pokemons.append(oid)
                continue

            bau = self.BausPorId.get(oid)
            if bau is not None:
                if fila_blits:
                    self._aplicar_blits_batch(tela, fila_blits)
                    fila_blits.clear()
                bau.render(tela, camera)
                continue

            if fila_blits:
                self._aplicar_blits_batch(tela, fila_blits)
                fila_blits.clear()
            if self._criaveis.renderizar_criavel(oid, tela, camera):
                continue

            if self._atores.renderizar(oid, tela, camera):
                continue

            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(222, 233, 245), pos_tela=pos_tela, fila_blits=fila_blits)

        self._aplicar_blits_batch(tela, fila_blits)
        for oid in remover_pokemons:
            with self._lock_objetos:
                self.ObjetosPorId.pop(int(oid), None)
                self.PokemonsPorId.pop(int(oid), None)
                self._remover_indice_chunk_objeto(int(oid))
                self._invalidar_cache_objetos_visiveis_locked()

    def renderizar_estruturas(self, tela, camera):
        objs = self._estruturas_visiveis_ordenadas(camera, margem_chunks=1)
        fila_blits: List[tuple] = []
        for obj in objs:
            if self._eh_payload_estadio(obj):
                if fila_blits:
                    self._aplicar_blits_batch(tela, fila_blits)
                    fila_blits.clear()
                estado_obj = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
                rx = float(estado_obj.get("raio_elipse_x", 24.0) or 24.0)
                ry = float(estado_obj.get("raio_elipse_y", 24.0) or 24.0)
                margem_estadio_px = int(max(220.0, max(rx, ry) * float(getattr(camera, "TilePx", 50) or 50) * 1.35))
                if self._objeto_posicao_tela_se_visivel(obj, camera, margem_px=margem_estadio_px) is None:
                    continue
                GeradorEstadio.renderizar(tela, camera, obj)
                continue
            pos_tela = self._objeto_posicao_tela_se_visivel(obj, camera, margem_px=220)
            if pos_tela is None:
                continue
            est = self.EstruturasPorId.get(int(obj.get("id", 0) or 0))
            escala = est.escala_render() if est is not None else 1.0
            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(125, 86, 54), escala=escala, pos_tela=pos_tela, fila_blits=fila_blits)
        self._aplicar_blits_batch(tela, fila_blits)


    def renderizar_estadio_interior(self, tela, camera):
        dim_local = self._dimensao_player_local()
        if dim_local == "Mundo":
            return
        player_payload = self.ObjetosPorId.get(int(self.id_player_local() or -1), {})
        estado_p = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        est_id = int(estado_p.get("estadio_atual_id", player_payload.get("estadio_atual_id", 0)) or 0)
        estadio_payload = self.EstadiosPorId.get(est_id, {})
        if not isinstance(estadio_payload, dict) or not estadio_payload:
            for candidato in self.EstadiosPorId.values():
                if not isinstance(candidato, dict):
                    continue
                estado_c = candidato.get("estado") if isinstance(candidato.get("estado"), dict) else {}
                if str(estado_c.get("dimensao_destino") or "EstadioNormal") == dim_local:
                    estadio_payload = candidato
                    break
        estado_est = estadio_payload.get("estado") if isinstance(estadio_payload.get("estado"), dict) else {}
        EstadioInterno.renderizar(tela, camera, estado_estadio=estado_est)

    @staticmethod
    def _saida_interna_estadio(estado: dict) -> List[float]:
        if isinstance(estado.get("saida_interna_pos"), (list, tuple)) and len(estado.get("saida_interna_pos")) == 2:
            return [float(estado.get("saida_interna_pos")[0]), float(estado.get("saida_interna_pos")[1])]
        largura = float(estado.get("largura_interna", 60.0) or 60.0)
        altura = float(estado.get("altura_interna", 40.0) or 40.0)
        return [largura * 0.5, max(1.0, altura - 3.0)]

    @staticmethod
    def _entrada_externa_estadio(payload_estadio: dict) -> List[float]:
        estado = payload_estadio.get("estado") if isinstance(payload_estadio.get("estado"), dict) else {}
        pos = payload_estadio.get("posicao") if isinstance(payload_estadio.get("posicao"), (list, tuple)) and len(payload_estadio.get("posicao")) == 2 else None
        if pos is not None:
            raio_y = float(estado.get("raio_elipse_y", payload_estadio.get("raio_colisao", 24.0)) or 24.0)
            off_x, off_y = GeradorEstadio.offset_porta_externa(raio_y)
            return [float(pos[0]) + off_x, float(pos[1]) + off_y]
        if isinstance(estado.get("entrada_pos"), (list, tuple)) and len(estado.get("entrada_pos")) == 2:
            return [float(estado.get("entrada_pos")[0]), float(estado.get("entrada_pos")[1])]
        if isinstance(estado.get("entrada_offset"), (list, tuple)) and len(estado.get("entrada_offset")) == 2:
            return [float(estado.get("entrada_offset")[0]), float(estado.get("entrada_offset")[1])]
        return [0.0, 0.0]

    def alvo_interagivel_atual(self, pos_player: Tuple[float, float], dimensao_player: str, estadio_atual_id: int = 0) -> Optional[Dict[str, object]]:
        px, py = float(pos_player[0]), float(pos_player[1])
        dim = str(dimensao_player or self._dimensao_player_local() or "Mundo")
        player_payload = self.ObjetosPorId.get(int(self.id_player_local() or -1), {})
        estado_p = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        estadio_real_id = int(estado_p.get("estadio_atual_id", player_payload.get("estadio_atual_id", estadio_atual_id)) or 0)

        candidatos: List[Tuple[float, Dict[str, object]]] = []

        if dim != "Mundo":
            estadio = self.EstadiosPorId.get(estadio_real_id, {})
            if not isinstance(estadio, dict) or not estadio:
                for candidato in self.EstadiosPorId.values():
                    if not isinstance(candidato, dict):
                        continue
                    estado_c = candidato.get("estado") if isinstance(candidato.get("estado"), dict) else {}
                    if str(estado_c.get("dimensao_destino") or "EstadioNormal") == dim:
                        estadio = candidato
                        break
            estado = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}
            porta = self._saida_interna_estadio(estado)
            d2 = (float(porta[0]) - px) ** 2 + (float(porta[1]) - py) ** 2
            if d2 <= (2.0 * 2.0):
                candidatos.append((d2, {"tipo": "estadio_saida", "estadio": estadio, "posicao": porta}))
        else:
            for estadio in list(self.EstadiosPorId.values()):
                if not isinstance(estadio, dict):
                    continue
                entrada = self._entrada_externa_estadio(estadio)
                d2 = (float(entrada[0]) - px) ** 2 + (float(entrada[1]) - py) ** 2
                if d2 <= (2.0 * 2.0):
                    candidatos.append((d2, {"tipo": "estadio_entrada", "estadio": estadio, "posicao": [float(entrada[0]), float(entrada[1])] }))

        npc_alvo = self.npc_interagivel_proximo((px, py), raio=2.3)
        if isinstance(npc_alvo, dict):
            npc_obj = npc_alvo.get("obj") if isinstance(npc_alvo.get("obj"), dict) else {}
            npc_pos = npc_obj.get("posicao") if isinstance(npc_obj.get("posicao"), (list, tuple)) and len(npc_obj.get("posicao")) == 2 else None
            if npc_pos is not None:
                d2_npc = (float(npc_pos[0]) - px) ** 2 + (float(npc_pos[1]) - py) ** 2
                candidatos.append((d2_npc, {"tipo": "npc", "npc": dict(npc_obj), "posicao": [float(npc_pos[0]), float(npc_pos[1])]}))

        if not candidatos:
            return None
        candidatos.sort(key=lambda item: float(item[0]))
        return candidatos[0][1]

    def mensagem_interacao_estadio(self, pos_player: Tuple[float, float], dimensao_player: str, estadio_atual_id: int = 0) -> str:
        alvo = self.alvo_interagivel_atual(pos_player=pos_player, dimensao_player=dimensao_player, estadio_atual_id=estadio_atual_id)
        if not isinstance(alvo, dict):
            return ""
        tipo = str(alvo.get("tipo") or "").strip().lower()
        if tipo == "estadio_entrada":
            return "Pressione F para entrar no estádio"
        if tipo == "estadio_saida":
            return "Pressione F para sair do estádio"
        if tipo == "npc":
            return "Pressione F para interagir"
        return "Pressione F para interagir"

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        self.renderizar_entidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self.renderizar_estruturas(tela, camera)

    def npc_interagivel_proximo(self, posicao: Tuple[float, float], raio: float = 2.2) -> Optional[Dict[str, object]]:
        with self._lock_objetos:
            snapshot = dict(self.ObjetosPorId)
        return self._atores.npc_proximo(snapshot, posicao=posicao, raio=raio, dimensao_local=self._dimensao_player_local())
