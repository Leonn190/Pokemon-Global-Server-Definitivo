"""Controlador de objetos do mundo (entidades + estruturas).

Nova arquitetura:
- Loop rápido (20Hz) para diffs visuais/dinâmicas.
- Loop lento (0.2Hz / 5s) para diffs persistentes.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple
import math
import threading
import time

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.GameObjeto import GameObjeto
from Codigo.Modulos.Colisor import Colisor
from Codigo.Geradores.Player.Player import Player
from Codigo.Geradores.PokemonMundo import PokemonMundo
from Codigo.Geradores.Baus import Bau


class ControladorObjetos:
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PlayerLocal = None
        self.PokemonsPorId: Dict[int, PokemonMundo] = {}
        self.BausPorId: Dict[int, Bau] = {}
        self._lock_objetos = threading.RLock()

        # Índice espacial local para colisão de proximidade.
        self._chunk_tamanho_tiles = 32
        self._objetos_colisao_por_chunk: Dict[Tuple[int, int], set[int]] = {}
        self._chunk_por_objeto: Dict[int, Tuple[int, int]] = {}

        # Separação das filas de diffs por categoria.
        self._fila_diffs_rapidas_envio: List[Dict[str, object]] = []
        self._fila_diffs_lentas_envio: List[Dict[str, object]] = []
        self._lock_diffs = threading.Lock()

        # Callbacks de rede por categoria.
        self._callback_loop_rapido: Optional[Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None]] = None
        self._callback_loop_lento: Optional[Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None]] = None

        # Threads independentes: rápida e lenta.
        self._thread_rapida: Optional[threading.Thread] = None
        self._thread_lenta: Optional[threading.Thread] = None
        self._thread_rapida_ativa = False
        self._thread_lenta_ativa = False
        self._intervalo_rapido = 0.05
        self._intervalo_lento = 5.0

        # Snapshots separados para detectar deltas por categoria.
        self._snapshot_player_anterior_rapido: Optional[Dict[str, object]] = None
        self._snapshot_player_anterior_lento: Optional[Dict[str, object]] = None

        self._ultimo_render_pokemons_ms = pygame.time.get_ticks()

    def definir_player_local(self, player) -> None:
        self.PlayerLocal = player
        self._snapshot_player_anterior_rapido = None
        self._snapshot_player_anterior_lento = None
        self._sincronizar_player_local()

    def montar_player_local(self, dados_player) -> Player:
        dados = dados_player if isinstance(dados_player, dict) else {}
        nome_skin = str(dados.get("skin", "S1.png"))
        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)

        ator = Ator(nome_skin=nome_skin, posicao=(float(pos[0]), float(pos[1])), escala_skin_tiles=1.0, tile_px=50)
        if dados.get("id") is not None:
            ator.Id = int(dados.get("id"))
        ator.Nome = str(dados.get("nome") or dados.get("usuario") or "")

        player = Player(
            ator=ator,
            velocidade_tiles=4.8,
        )
        player.Perfil.aplicar_serializado(dados)
        self.definir_player_local(player)
        return player

    def _sincronizar_player_local(self) -> None:
        if self.PlayerLocal is None or getattr(self.PlayerLocal, "Ator", None) is None:
            return
        ator = self.PlayerLocal.Ator
        player_id = getattr(ator, "Id", None)
        if player_id is None:
            return
        self.aplicar_diff(
            {
                "tipo": "update",
                "objeto_id": int(player_id),
                "payload": {
                    "id": int(player_id),
                    "tipo": "entidade_player",
                    "nome": getattr(ator, "Nome", ""),
                    "posicao": [ator.Posicao[0], ator.Posicao[1]],
                    "raio_colisao": getattr(ator.Colisor, "raio_colisao", 0.35),
                },
            }
        )

    def atualizar_player_local(self, eventos, dt, mouse_pos_mundo_tiles, gerenciador_fps=None) -> None:
        if self.PlayerLocal is None:
            return
        posicao_antes = tuple(self.PlayerLocal.Ator.Posicao)
        self.PlayerLocal.Controle.atualizar(eventos, dt, mouse_pos_mundo_tiles)
        self._resolver_colisao_player_local(posicao_antes, dt, gerenciador_fps=gerenciador_fps)
        self._processar_colisao_baus_local()

    def _chunk_posicao(self, x: float, y: float) -> Tuple[int, int]:
        return (int(math.floor(float(x) / self._chunk_tamanho_tiles)), int(math.floor(float(y) / self._chunk_tamanho_tiles)))

    def _dados_colisao_objeto(self, obj: Dict[str, object]) -> Optional[Tuple[int, float, float, float, str, float, float]]:
        pos = obj.get("posicao")
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return None

        tipo = str(obj.get("tipo", ""))
        if not (tipo.startswith("estrutura") or tipo.startswith("entidade")):
            return None

        try:
            oid = int(obj.get("id"))
            sx = float(pos[0])
            sy = float(pos[1])
            raio = max(0.0, float(obj.get("raio_colisao", 0.0)))
        except (TypeError, ValueError):
            return None

        if raio <= 0.0:
            return None

        try:
            campo = max(0.0, float(obj.get("campo", 0.0)))
        except (TypeError, ValueError):
            campo = 0.0
        try:
            intensidade = max(0.0, float(obj.get("intensidade", 0.0)))
        except (TypeError, ValueError):
            intensidade = 0.0

        return (oid, sx, sy, raio, tipo, campo, intensidade)

    def _atualizar_indice_objeto_colisivo(self, obj: Dict[str, object]) -> None:
        dados = self._dados_colisao_objeto(obj)
        obj_id_raw = obj.get("id")
        if obj_id_raw is None:
            return
        oid = int(obj_id_raw)

        chunk_antigo = self._chunk_por_objeto.pop(oid, None)
        if chunk_antigo is not None:
            bucket_antigo = self._objetos_colisao_por_chunk.get(chunk_antigo)
            if bucket_antigo is not None:
                bucket_antigo.discard(oid)
                if not bucket_antigo:
                    self._objetos_colisao_por_chunk.pop(chunk_antigo, None)

        if dados is None:
            return

        _, sx, sy, _, _, _, _ = dados
        chunk = self._chunk_posicao(sx, sy)
        self._chunk_por_objeto[oid] = chunk
        self._objetos_colisao_por_chunk.setdefault(chunk, set()).add(oid)

    def _reindexar_objetos_colisivos(self) -> None:
        with self._lock_objetos:
            self._objetos_colisao_por_chunk.clear()
            self._chunk_por_objeto.clear()
            for obj in self.ObjetosPorId.values():
                if isinstance(obj, dict):
                    self._atualizar_indice_objeto_colisivo(obj)

    def _iter_colisores_proximos_por_raio(self, posicao_player: Tuple[float, float], raio_tiles: float = 10.0):
        """Busca colisores locais por raio fixo de 10 tiles (sem depender de chunks vizinhos fixos)."""
        px, py = float(posicao_player[0]), float(posicao_player[1])
        raio = max(0.1, float(raio_tiles))
        chunk_cx, chunk_cy = self._chunk_posicao(px, py)
        alcance_chunks = max(1, int(math.ceil(raio / float(self._chunk_tamanho_tiles))))

        with self._lock_objetos:
            ids = set()
            for dx in range(-alcance_chunks, alcance_chunks + 1):
                for dy in range(-alcance_chunks, alcance_chunks + 1):
                    ids.update(self._objetos_colisao_por_chunk.get((chunk_cx + dx, chunk_cy + dy), set()))
            objetos_snapshot = [self.ObjetosPorId.get(oid) for oid in ids]

        raio2 = raio * raio
        for obj in objetos_snapshot:
            if not isinstance(obj, dict):
                continue
            dados = self._dados_colisao_objeto(obj)
            if dados is None:
                continue
            _, sx, sy, _, _, _, _ = dados
            if ((sx - px) ** 2 + (sy - py) ** 2) <= raio2:
                yield dados

    def _resolver_colisao_player_local(self, posicao_antes: Tuple[float, float], dt: float, gerenciador_fps=None) -> None:
        if self.PlayerLocal is None or getattr(self.PlayerLocal, "Ator", None) is None:
            return

        ator = self.PlayerLocal.Ator
        posicao_depois = tuple(ator.Posicao)
        player_id = getattr(ator, "Id", None)
        raio_ator = max(0.0, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))

        if gerenciador_fps is not None:
            gerenciador_fps.iniciar_trecho("carregar_objetos_proximos_colidir")
        colisores_proximos = [c for c in self._iter_colisores_proximos_por_raio(posicao_depois, raio_tiles=10.0) if c[0] != player_id]
        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("carregar_objetos_proximos_colidir")

        if gerenciador_fps is not None:
            gerenciador_fps.iniciar_trecho("sistema_colisao")
        px, py = Colisor.resolver_movimento_com_colisores(
            posicao_antes=posicao_antes,
            posicao_depois=posicao_depois,
            raio_entidade=raio_ator,
            colisores=colisores_proximos,
            dt=dt,
        )
        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("sistema_colisao")
        ator.definir_posicao(px, py)

    def _processar_colisao_baus_local(self) -> None:
        if self.PlayerLocal is None or getattr(self.PlayerLocal, "Ator", None) is None:
            return
        ator = self.PlayerLocal.Ator
        player_pos = tuple(ator.Posicao)
        raio_player = max(0.1, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))
        inventario = getattr(self.PlayerLocal, "Inventario", None)
        if inventario is None:
            return

        with self._lock_objetos:
            baus = list(self.BausPorId.values())

        for bau in baus:
            if bau.Aberto:
                continue
            dx = float(bau.Posicao[0]) - float(player_pos[0])
            dy = float(bau.Posicao[1]) - float(player_pos[1])
            limite = raio_player + float(bau.Colisor.raio_colisao)
            if (dx * dx + dy * dy) > (limite * limite):
                continue

            for item in bau.Itens:
                inventario.adicionar_item(dict(item))

            if bau.abrir_localmente():
                self.EnfileirarDiffRapida({"tipo": "abrir_bau", "objeto_id": int(bau.Id), "payload": {}})

    def _snapshot_player_supervisao(self) -> Optional[Dict[str, object]]:
        player = self.PlayerLocal
        if player is None or getattr(player, "Ator", None) is None:
            return None

        ator = player.Ator
        controle = getattr(player, "Controle", None)
        inventario = getattr(player, "Inventario", None)
        perfil = getattr(player, "Perfil", None)
        player_id = getattr(ator, "Id", None)
        if player_id is None:
            return None

        estado = {
            "angulo": float(getattr(ator, "AnguloOlhar", 0.0)),
            "tapa": bool(ator.esta_tapando()),
        }

        return {
            "objeto_id": int(player_id),
            "nome": str(getattr(ator, "Nome", "")),
            "tipo": "entidade_player",
            "posicao": [float(ator.Posicao[0]), float(ator.Posicao[1])],
            "raio_colisao": float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)),
            "estado": estado,
            "perfil": dict(perfil.serializar()) if perfil is not None else {},
            "inventario": dict(inventario.serializar()) if inventario is not None else {},
            "controle": {
                "inventario_aberto": bool(getattr(controle, "InventarioAberto", False)),
                "batendo": bool(getattr(controle, "_batendo", False)),
            },
        }

    def _comparar_snapshot_rapido(self, anterior: Optional[Dict[str, object]], atual: Dict[str, object]) -> Optional[Dict[str, object]]:
        """Compara apenas dados de sync rápida (posição, ângulo, tapa e estado dinâmico)."""
        payload: Dict[str, object] = {}
        if anterior is None:
            payload = {
                "tipo": atual.get("tipo"),
                "nome": atual.get("nome"),
                "raio_colisao": atual.get("raio_colisao"),
                "posicao": list(atual.get("posicao", [0.0, 0.0])),
                "estado": dict(atual.get("estado", {})),
            }
        else:
            for chave in ("nome", "tipo", "raio_colisao"):
                if anterior.get(chave) != atual.get(chave):
                    payload[chave] = atual.get(chave)
            if anterior.get("posicao") != atual.get("posicao"):
                payload["posicao"] = list(atual.get("posicao", [0.0, 0.0]))

            estado_novo = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
            estado_antigo = anterior.get("estado") if isinstance(anterior.get("estado"), dict) else {}
            estado_delta = {}
            for chave, valor in estado_novo.items():
                if estado_antigo.get(chave) != valor:
                    estado_delta[chave] = valor
            if estado_delta:
                payload["estado"] = estado_delta

        if not payload:
            return None
        return {"tipo": "update", "objeto_id": int(atual["objeto_id"]), "payload": payload}

    def _comparar_snapshot_lento(self, anterior: Optional[Dict[str, object]], atual: Dict[str, object]) -> Optional[Dict[str, object]]:
        """Compara apenas dados persistentes/lentos (perfil + inventário)."""
        payload: Dict[str, object] = {}
        if anterior is None:
            payload = {
                "perfil": dict(atual.get("perfil", {})),
                "inventario": dict(atual.get("inventario", {})),
                "controle": dict(atual.get("controle", {})),
            }
        else:
            if anterior.get("perfil") != atual.get("perfil"):
                payload["perfil"] = dict(atual.get("perfil", {}))
            if anterior.get("inventario") != atual.get("inventario"):
                payload["inventario"] = dict(atual.get("inventario", {}))
            if anterior.get("controle") != atual.get("controle"):
                payload["controle"] = dict(atual.get("controle", {}))

        if not payload:
            return None
        return {"tipo": "update", "objeto_id": int(atual["objeto_id"]), "payload": payload}

    def EnfileirarDiffRapida(self, diff: Dict[str, object]) -> None:
        with self._lock_diffs:
            self._fila_diffs_rapidas_envio.append(diff)

    def EnfileirarDiffLenta(self, diff: Dict[str, object]) -> None:
        with self._lock_diffs:
            self._fila_diffs_lentas_envio.append(diff)

    def ColetarDiffsRapidas(self) -> List[Dict[str, object]]:
        with self._lock_diffs:
            lote = list(self._fila_diffs_rapidas_envio)
            self._fila_diffs_rapidas_envio.clear()
            return lote

    def ColetarDiffsLentas(self) -> List[Dict[str, object]]:
        with self._lock_diffs:
            lote = list(self._fila_diffs_lentas_envio)
            self._fila_diffs_lentas_envio.clear()
            return lote

    def AplicarDiffRapida(self, diff: Dict[str, object]) -> None:
        self.aplicar_diff(diff)

    def AplicarDiffLenta(self, diff: Dict[str, object]) -> None:
        self.aplicar_diff(diff)

    def _supervisionar_player_e_enfileirar_diff_rapida(self) -> None:
        snapshot_atual = self._snapshot_player_supervisao()
        if snapshot_atual is None:
            self._snapshot_player_anterior_rapido = None
            return
        diff = self._comparar_snapshot_rapido(self._snapshot_player_anterior_rapido, snapshot_atual)
        self._snapshot_player_anterior_rapido = snapshot_atual
        if diff is None:
            return
        self.aplicar_diff(diff)
        self.EnfileirarDiffRapida(diff)

    def _supervisionar_player_e_enfileirar_diff_lenta(self) -> None:
        snapshot_atual = self._snapshot_player_supervisao()
        if snapshot_atual is None:
            self._snapshot_player_anterior_lento = None
            return
        diff = self._comparar_snapshot_lento(self._snapshot_player_anterior_lento, snapshot_atual)
        self._snapshot_player_anterior_lento = snapshot_atual
        if diff is None:
            return
        self.aplicar_diff(diff)
        self.EnfileirarDiffLenta(diff)

    def iniciar_threads_diffs(
        self,
        callback_loop_rapido: Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None],
        callback_loop_lento: Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None],
        intervalo_rapido: float = 0.05,
        intervalo_lento: float = 5.0,
    ) -> None:
        """Inicia os 2 loops independentes de diffs (rápido e lento)."""
        self._callback_loop_rapido = callback_loop_rapido if callable(callback_loop_rapido) else None
        self._callback_loop_lento = callback_loop_lento if callable(callback_loop_lento) else None
        self._intervalo_rapido = max(0.02, float(intervalo_rapido))
        self._intervalo_lento = max(1.0, float(intervalo_lento))

        if not (self._thread_rapida and self._thread_rapida.is_alive()):
            self._thread_rapida_ativa = True
            self._thread_rapida = threading.Thread(target=self._loop_diffs_rapidas, name="ControladorObjetosDiffRapidaThread", daemon=True)
            self._thread_rapida.start()

        if not (self._thread_lenta and self._thread_lenta.is_alive()):
            self._thread_lenta_ativa = True
            self._thread_lenta = threading.Thread(target=self._loop_diffs_lentas, name="ControladorObjetosDiffLentaThread", daemon=True)
            self._thread_lenta.start()

    def parar_threads_diffs(self, timeout: float = 2.0) -> None:
        self._thread_rapida_ativa = False
        self._thread_lenta_ativa = False
        if self._thread_rapida and self._thread_rapida.is_alive():
            self._thread_rapida.join(timeout=timeout)
        if self._thread_lenta and self._thread_lenta.is_alive():
            self._thread_lenta.join(timeout=timeout)

    # Compatibilidade com API antiga.
    def iniciar_thread_envio_diffs(self, callback_envio_diffs: Callable[[List[Dict[str, object]]], None], intervalo: float = 0.05) -> None:
        def _legacy_cb_rapido(lote):
            if callable(callback_envio_diffs) and lote:
                callback_envio_diffs(lote)
            return []

        def _legacy_cb_lento(_lote):
            return []

        self.iniciar_threads_diffs(_legacy_cb_rapido, _legacy_cb_lento, intervalo_rapido=intervalo, intervalo_lento=5.0)

    def parar_thread_envio_diffs(self, timeout: float = 2.0) -> None:
        self.parar_threads_diffs(timeout=timeout)

    def _loop_diffs_rapidas(self) -> None:
        while self._thread_rapida_ativa:
            self._supervisionar_player_e_enfileirar_diff_rapida()
            envio = self.ColetarDiffsRapidas()
            callback = self._callback_loop_rapido
            remotas = []
            if callback is not None:
                try:
                    resposta = callback(envio)
                    if isinstance(resposta, list):
                        remotas = resposta
                except Exception:
                    if envio:
                        with self._lock_diffs:
                            self._fila_diffs_rapidas_envio = envio + self._fila_diffs_rapidas_envio
            for diff in remotas:
                if isinstance(diff, dict):
                    self.AplicarDiffRapida(diff)
            time.sleep(self._intervalo_rapido)

    def _loop_diffs_lentas(self) -> None:
        while self._thread_lenta_ativa:
            self._supervisionar_player_e_enfileirar_diff_lenta()
            envio = self.ColetarDiffsLentas()
            callback = self._callback_loop_lento
            remotas = []
            if callback is not None:
                try:
                    resposta = callback(envio)
                    if isinstance(resposta, list):
                        remotas = resposta
                except Exception:
                    if envio:
                        with self._lock_diffs:
                            self._fila_diffs_lentas_envio = envio + self._fila_diffs_lentas_envio
            for diff in remotas:
                if isinstance(diff, dict):
                    self.AplicarDiffLenta(diff)
            time.sleep(self._intervalo_lento)

    def _eh_payload_pokemon(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", "")).strip().lower()
        if tipo in ("entidade_pokemon", "pokemon"):
            return True
        estado = payload.get("estado")
        if isinstance(estado, dict):
            subtipo = str(estado.get("subtipo", "")).strip().lower()
            if subtipo == "pokemon":
                return True
        return False

    def _sincronizar_pokemon(self, oid: int, payload: Dict[str, object], criar_se_ausente: bool = True) -> None:
        if not self._eh_payload_pokemon(payload):
            return

        with self._lock_objetos:
            pokemon = self.PokemonsPorId.get(oid)
            if pokemon is None:
                if not criar_se_ausente:
                    return
                pokemon = PokemonMundo(payload)
                self.PokemonsPorId[oid] = pokemon
            pokemon.aplicar_snapshot(payload)

    def aplicar_diff(self, diff):
        if not isinstance(diff, dict):
            return
        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload", {}), dict) else {}

        if tipo == "spawn":
            dados_obj = dict(payload)
            oid = int(dados_obj.get("id", objeto_id))
            dados_obj["id"] = oid
            estado_spawn = dados_obj.get("estado") if isinstance(dados_obj.get("estado"), dict) else {}
            eh_bau = str(estado_spawn.get("subtipo", "")).lower() == "bau" and str(dados_obj.get("tipo", "")).startswith("entidade")
            if eh_bau and bool(estado_spawn.get("aberto", False)):
                return

            with self._lock_objetos:
                self.ObjetosPorId[oid] = dados_obj
                self._atualizar_indice_objeto_colisivo(dados_obj)
                if eh_bau:
                    self.BausPorId[oid] = Bau(
                        id_objeto=oid,
                        posicao=tuple(dados_obj.get("posicao", [0.0, 0.0])),
                        tipo_bau=str(estado_spawn.get("tipo_bau", "Comum")),
                        itens=list(estado_spawn.get("itens", [])),
                        aberto=bool(estado_spawn.get("aberto", False)),
                        raio_colisao=float(dados_obj.get("raio_colisao", 0.42)),
                    )
            self._sincronizar_pokemon(oid, dados_obj, criar_se_ausente=True)
            return

        if objeto_id is None:
            return
        oid = int(objeto_id)

        if tipo == "update":
            with self._lock_objetos:
                atual = self.ObjetosPorId.get(oid, {"id": oid})
                estado = payload.get("estado")
                if isinstance(estado, dict):
                    base_estado = atual.get("estado", {}) if isinstance(atual.get("estado", {}), dict) else {}
                    base_estado.update(estado)
                    atual["estado"] = base_estado
                for chave, valor in payload.items():
                    if chave != "estado":
                        atual[chave] = valor
                self.ObjetosPorId[oid] = atual
                self._atualizar_indice_objeto_colisivo(atual)

                bau = self.BausPorId.get(oid)
                estado_atual = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
                eh_bau = str(estado_atual.get("subtipo", "")).lower() == "bau" and str(atual.get("tipo", "")).startswith("entidade")
                if bau is None and eh_bau and not bool(estado_atual.get("aberto", False)):
                    bau = Bau(
                        id_objeto=oid,
                        posicao=tuple(atual.get("posicao", [0.0, 0.0])),
                        tipo_bau=str(estado_atual.get("tipo_bau", "Comum")),
                        itens=list(estado_atual.get("itens", [])),
                        aberto=False,
                        raio_colisao=float(atual.get("raio_colisao", 0.42)),
                    )
                    self.BausPorId[oid] = bau
                if bau is not None:
                    pos = atual.get("posicao") if isinstance(atual.get("posicao"), (list, tuple)) else [bau.Posicao[0], bau.Posicao[1]]
                    bau.definir_posicao(float(pos[0]), float(pos[1]))
                    if bool(estado_atual.get("aberto", False)):
                        bau.marcar_aberto_por_sync()
            self._sincronizar_pokemon(oid, atual, criar_se_ausente=True)
            return

        if tipo == "despawn":
            with self._lock_objetos:
                self.ObjetosPorId.pop(oid, None)
                self.PokemonsPorId.pop(oid, None)
                self.BausPorId.pop(oid, None)
                chunk = self._chunk_por_objeto.pop(oid, None)
                if chunk is not None:
                    bucket = self._objetos_colisao_por_chunk.get(chunk)
                    if bucket is not None:
                        bucket.discard(oid)
                        if not bucket:
                            self._objetos_colisao_por_chunk.pop(chunk, None)

    def sincronizar_objetos(self, objetos):
        if not isinstance(objetos, dict):
            return
        with self._lock_objetos:
            self.ObjetosPorId = {int(k): dict(v) for k, v in objetos.items()}
            self._reindexar_objetos_colisivos()
            self.PokemonsPorId = {}
            self.BausPorId = {}
            snapshot_objetos = list(self.ObjetosPorId.items())
        for oid, payload in snapshot_objetos:
            if isinstance(payload, dict):
                self._sincronizar_pokemon(int(oid), payload, criar_se_ausente=True)
                estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                if str(estado.get("subtipo", "")).lower() == "bau" and str(payload.get("tipo", "")).startswith("entidade") and not bool(estado.get("aberto", False)):
                    self.BausPorId[int(oid)] = Bau(
                        id_objeto=int(oid),
                        posicao=tuple(payload.get("posicao", [0.0, 0.0])),
                        tipo_bau=str(estado.get("tipo_bau", "Comum")),
                        itens=list(estado.get("itens", [])),
                        aberto=False,
                        raio_colisao=float(payload.get("raio_colisao", 0.42)),
                    )

    def _iter_tipos(self, prefixo):
        with self._lock_objetos:
            return [dict(obj) for obj in self.ObjetosPorId.values() if str(obj.get("tipo", "")).startswith(prefixo)]

    def _objeto_posicao_tela_se_visivel(self, obj: Dict[str, object], camera, margem_px: int = 120):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return None

        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        if px < -margem_px or py < -margem_px or px > (tela_w + margem_px) or py > (tela_h + margem_px):
            return None
        return px, py

    def RenderizarEntidades(self, tela, camera, ignorar_id=None):
        agora = pygame.time.get_ticks()
        dt_pokemons = max(0.0, (agora - self._ultimo_render_pokemons_ms) / 1000.0)
        self._ultimo_render_pokemons_ms = agora

        for obj in self._iter_tipos("entidade"):
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue

            with self._lock_objetos:
                pokemon = self.PokemonsPorId.get(oid)
                bau = self.BausPorId.get(oid)
            if pokemon is not None:
                if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                    continue
                pokemon.desenhar(tela, camera, dt_pokemons)
                continue
            if bau is not None:
                if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                    continue
                bau.desenhar(tela, camera)
                continue

            pos_tela = self._objeto_posicao_tela_se_visivel(obj, camera)
            if pos_tela is None:
                continue
            GameObjeto.desenhar_snapshot(tela, camera, obj, cor_fallback=(222, 233, 245))
            nome_obj = obj.get("nome") or obj.get("usuario")
            if nome_obj:
                Ator.desenhar_nome(tela, pos_tela, nome_obj)

    def RenderizarEstruturas(self, tela, camera):
        for obj in self._iter_tipos("estrutura"):
            if self._objeto_posicao_tela_se_visivel(obj, camera, margem_px=220) is None:
                continue
            GameObjeto.desenhar_snapshot(tela, camera, obj, cor_fallback=(125, 86, 54))

    def renderizar_player(self, tela, camera, ignorar_entidade_id=None):
        if ignorar_entidade_id is None and self.PlayerLocal is not None and getattr(self.PlayerLocal, "Ator", None) is not None:
            ignorar_entidade_id = getattr(self.PlayerLocal.Ator, "Id", None)
        self.RenderizarEntidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self._renderizar_player_local(tela, camera)

    def renderizar_estruturas(self, tela, camera):
        self.RenderizarEstruturas(tela, camera)

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        if ignorar_entidade_id is None and self.PlayerLocal is not None and getattr(self.PlayerLocal, "Ator", None) is not None:
            ignorar_entidade_id = getattr(self.PlayerLocal.Ator, "Id", None)
        self.RenderizarEntidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self._renderizar_player_local(tela, camera)
        self.RenderizarEstruturas(tela, camera)

    def _renderizar_player_local(self, tela, camera):
        if self.PlayerLocal is None or getattr(self.PlayerLocal, "Ator", None) is None:
            return
        ator = self.PlayerLocal.Ator
        ator.set_tile_px(getattr(camera, "TilePx", 50))
        pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        respiracao_tempo = getattr(getattr(self.PlayerLocal, "Controle", None), "_tempo_respiracao", 0.0)
        ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=respiracao_tempo)
        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)
