"""Controlador de objetos do mundo (player + entidades + estruturas)."""

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

        # Entidades/estruturas especializadas (lógica interna de cada classe).
        self.PokemonsPorId: Dict[int, PokemonMundo] = {}
        self.BausPorId: Dict[int, Bau] = {}

        self._lock_objetos = threading.RLock()
        self._lock_diffs = threading.Lock()

        self._fila_diffs_rapidas_envio: List[Dict[str, object]] = []
        self._fila_diffs_lentas_envio: List[Dict[str, object]] = []

        self._callback_loop_rapido: Optional[Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None]] = None
        self._callback_loop_lento: Optional[Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None]] = None

        self._thread_rapida: Optional[threading.Thread] = None
        self._thread_lenta: Optional[threading.Thread] = None
        self._thread_rapida_ativa = False
        self._thread_lenta_ativa = False
        self._intervalo_rapido = 0.05
        self._intervalo_lento = 5.0

        self._snapshot_player_anterior_rapido: Optional[Dict[str, object]] = None
        self._snapshot_player_anterior_lento: Optional[Dict[str, object]] = None

        self._chunk_tamanho_tiles = 10
        self._objetos_colisao_por_chunk: Dict[Tuple[int, int], set[int]] = {}
        self._chunk_por_objeto: Dict[int, Tuple[int, int]] = {}

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

        player = Player(ator=ator)
        player.Perfil.aplicar_serializado(dados)
        inventario_serializado = dados.get("inventario", dados) if isinstance(dados.get("inventario", dados), dict) else {}
        player.Inventario.aplicar_serializado(inventario_serializado)
        self.definir_player_local(player)
        return player

    def _sincronizar_player_local(self) -> None:
        if self.PlayerLocal is None or getattr(self.PlayerLocal, "Ator", None) is None:
            return
        ator = self.PlayerLocal.Ator
        if getattr(ator, "Id", None) is None:
            return
        self.aplicar_diff({
            "tipo": "update",
            "objeto_id": int(ator.Id),
            "payload": {
                "id": int(ator.Id),
                "tipo": "entidade_player",
                "nome": getattr(ator, "Nome", ""),
                "posicao": [ator.Posicao[0], ator.Posicao[1]],
                "raio_colisao": getattr(ator.Colisor, "raio_colisao", 0.35),
            },
        })

    def atualizar_player_local(self, eventos, dt, mouse_pos_mundo_tiles, gerenciador_fps=None) -> None:
        if self.PlayerLocal is None:
            return
        posicao_antes = tuple(self.PlayerLocal.Ator.Posicao)
        self.PlayerLocal.Controle.atualizar(eventos, dt, mouse_pos_mundo_tiles)
        self._resolver_colisao_player_local(posicao_antes, dt, gerenciador_fps=gerenciador_fps)
        self._processar_interacoes_player()

    def _chunk_posicao(self, x: float, y: float) -> Tuple[int, int]:
        return (int(math.floor(float(x) / self._chunk_tamanho_tiles)), int(math.floor(float(y) / self._chunk_tamanho_tiles)))

    def _dados_colisao_objeto(self, obj: Dict[str, object]) -> Optional[Tuple[int, float, float, float, str, float, float]]:
        pos = obj.get("posicao")
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return None
        try:
            oid = int(obj.get("id"))
            sx, sy = float(pos[0]), float(pos[1])
            raio = max(0.0, float(obj.get("raio_colisao", 0.0)))
            campo = max(0.0, float(obj.get("campo", 0.0)))
            intensidade = max(0.0, float(obj.get("intensidade", 0.0)))
        except (TypeError, ValueError):
            return None

        tipo = str(obj.get("tipo", ""))
        if not (tipo.startswith("estrutura") or tipo.startswith("entidade")) or raio <= 0.0:
            return None
        return (oid, sx, sy, raio, tipo, campo, intensidade)

    def _atualizar_indice_objeto_colisivo(self, obj: Dict[str, object]) -> None:
        obj_id = obj.get("id")
        if obj_id is None:
            return
        oid = int(obj_id)

        chunk_antigo = self._chunk_por_objeto.pop(oid, None)
        if chunk_antigo is not None:
            bucket = self._objetos_colisao_por_chunk.get(chunk_antigo)
            if bucket is not None:
                bucket.discard(oid)
                if not bucket:
                    self._objetos_colisao_por_chunk.pop(chunk_antigo, None)

        dados = self._dados_colisao_objeto(obj)
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
        px, py = float(posicao_player[0]), float(posicao_player[1])
        chunk_cx, chunk_cy = self._chunk_posicao(px, py)
        alcance = max(1, int(math.ceil(float(raio_tiles) / float(self._chunk_tamanho_tiles))))

        with self._lock_objetos:
            ids = set()
            for dx in range(-alcance, alcance + 1):
                for dy in range(-alcance, alcance + 1):
                    ids.update(self._objetos_colisao_por_chunk.get((chunk_cx + dx, chunk_cy + dy), set()))
            objetos_snapshot = [self.ObjetosPorId.get(oid) for oid in ids]

        raio2 = float(raio_tiles) * float(raio_tiles)
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
        colisores = [c for c in self._iter_colisores_proximos_por_raio(posicao_depois, raio_tiles=10.0) if c[0] != player_id]
        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("carregar_objetos_proximos_colidir")

        if gerenciador_fps is not None:
            gerenciador_fps.iniciar_trecho("sistema_colisao")
        px, py = Colisor.resolver_movimento_com_colisores(
            posicao_antes=posicao_antes,
            posicao_depois=posicao_depois,
            raio_entidade=raio_ator,
            colisores=colisores,
            dt=dt,
        )
        if gerenciador_fps is not None:
            gerenciador_fps.finalizar_trecho("sistema_colisao")
        ator.definir_posicao(px, py)

    def _processar_interacoes_player(self) -> None:
        if self.PlayerLocal is None:
            return
        with self._lock_objetos:
            interativos = list(self.BausPorId.values())
        for obj in interativos:
            diff = obj.processar_interacao_player(self.PlayerLocal)
            if isinstance(diff, dict):
                self.EnfileirarDiffRapida(diff)

    def _snapshot_player_supervisao(self) -> Optional[Dict[str, object]]:
        player = self.PlayerLocal
        if player is None or getattr(player, "Ator", None) is None:
            return None

        ator = player.Ator
        if getattr(ator, "Id", None) is None:
            return None

        controle = getattr(player, "Controle", None)
        inventario = getattr(player, "Inventario", None)
        perfil = getattr(player, "Perfil", None)

        return {
            "objeto_id": int(ator.Id),
            "nome": str(getattr(ator, "Nome", "")),
            "tipo": "entidade_player",
            "posicao": [float(ator.Posicao[0]), float(ator.Posicao[1])],
            "raio_colisao": float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)),
            "estado": {
                "angulo": float(getattr(ator, "AnguloOlhar", 0.0)),
                "tapa": bool(ator.esta_tapando()),
            },
            "perfil": dict(perfil.serializar()) if perfil is not None else {},
            "inventario": dict(inventario.serializar()) if inventario is not None else {},
            "controle": {
                "inventario_aberto": bool(getattr(controle, "InventarioAberto", False)),
                "batendo": bool(getattr(controle, "_batendo", False)),
            },
        }

    def _comparar_snapshot_rapido(self, anterior: Optional[Dict[str, object]], atual: Dict[str, object]) -> Optional[Dict[str, object]]:
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
            delta_estado = {k: v for k, v in estado_novo.items() if estado_antigo.get(k) != v}
            if delta_estado:
                payload["estado"] = delta_estado

        if not payload:
            return None
        return {"tipo": "update", "objeto_id": int(atual["objeto_id"]), "payload": payload}

    def _comparar_snapshot_lento(self, anterior: Optional[Dict[str, object]], atual: Dict[str, object]) -> Optional[Dict[str, object]]:
        payload: Dict[str, object] = {}
        if anterior is None:
            payload = {
                "perfil": dict(atual.get("perfil", {})),
                "inventario": dict(atual.get("inventario", {})),
                "controle": dict(atual.get("controle", {})),
            }
        else:
            for chave in ("perfil", "inventario", "controle"):
                if anterior.get(chave) != atual.get(chave):
                    payload[chave] = dict(atual.get(chave, {}))

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
        snap = self._snapshot_player_supervisao()
        if snap is None:
            self._snapshot_player_anterior_rapido = None
            return
        diff = self._comparar_snapshot_rapido(self._snapshot_player_anterior_rapido, snap)
        self._snapshot_player_anterior_rapido = snap
        if diff is not None:
            self.aplicar_diff(diff)
            self.EnfileirarDiffRapida(diff)

    def _supervisionar_player_e_enfileirar_diff_lenta(self) -> None:
        snap = self._snapshot_player_supervisao()
        if snap is None:
            self._snapshot_player_anterior_lento = None
            return
        diff = self._comparar_snapshot_lento(self._snapshot_player_anterior_lento, snap)
        self._snapshot_player_anterior_lento = snap
        if diff is not None:
            self.aplicar_diff(diff)
            self.EnfileirarDiffLenta(diff)

    def iniciar_threads_diffs(
        self,
        callback_loop_rapido: Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None],
        callback_loop_lento: Callable[[List[Dict[str, object]]], List[Dict[str, object]] | None],
        intervalo_rapido: float = 0.05,
        intervalo_lento: float = 5.0,
    ) -> None:
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

    def iniciar_thread_envio_diffs(self, callback_envio_diffs: Callable[[List[Dict[str, object]]], None], intervalo: float = 0.05) -> None:
        def _legacy_cb_rapido(lote):
            if callable(callback_envio_diffs) and lote:
                callback_envio_diffs(lote)
            return []

        self.iniciar_threads_diffs(_legacy_cb_rapido, lambda _lote: [], intervalo_rapido=intervalo, intervalo_lento=5.0)

    def parar_thread_envio_diffs(self, timeout: float = 2.0) -> None:
        self.parar_threads_diffs(timeout=timeout)

    def _loop_diffs_rapidas(self) -> None:
        while self._thread_rapida_ativa:
            self._supervisionar_player_e_enfileirar_diff_rapida()
            envio = self.ColetarDiffsRapidas()
            remotas = []
            if self._callback_loop_rapido is not None:
                try:
                    resposta = self._callback_loop_rapido(envio)
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
            remotas = []
            if self._callback_loop_lento is not None:
                try:
                    resposta = self._callback_loop_lento(envio)
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
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return str(estado.get("subtipo", "")).strip().lower() == "pokemon"

    def _eh_payload_bau(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", ""))
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return tipo.startswith("entidade") and str(estado.get("subtipo", "")).strip().lower() == "bau"

    def _upsert_especializado(self, oid: int, payload: Dict[str, object]) -> None:
        if self._eh_payload_pokemon(payload):
            pokemon = self.PokemonsPorId.get(oid)
            if pokemon is None:
                self.PokemonsPorId[oid] = PokemonMundo(payload)
            else:
                pokemon.aplicar_snapshot(payload)
        elif oid in self.PokemonsPorId:
            self.PokemonsPorId.pop(oid, None)

        if self._eh_payload_bau(payload):
            bau = self.BausPorId.get(oid)
            if bau is None:
                self.BausPorId[oid] = Bau.from_snapshot(payload)
            else:
                bau.aplicar_snapshot(payload)
        elif oid in self.BausPorId:
            self.BausPorId.pop(oid, None)

    def aplicar_diff(self, diff):
        if not isinstance(diff, dict):
            return
        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}

        if tipo == "spawn":
            dados = dict(payload)
            oid = int(dados.get("id", objeto_id or 0))
            dados["id"] = oid
            with self._lock_objetos:
                self.ObjetosPorId[oid] = dados
                self._atualizar_indice_objeto_colisivo(dados)
                self._upsert_especializado(oid, dados)
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
                self._atualizar_indice_objeto_colisivo(atual)
                self._upsert_especializado(oid, atual)
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
            self.PokemonsPorId = {}
            self.BausPorId = {}
            self._reindexar_objetos_colisivos()
            snapshot = list(self.ObjetosPorId.items())
        for oid, payload in snapshot:
            if isinstance(payload, dict):
                with self._lock_objetos:
                    self._upsert_especializado(int(oid), payload)

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
            if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                continue

            with self._lock_objetos:
                pokemon = self.PokemonsPorId.get(oid)
                bau = self.BausPorId.get(oid)
            if pokemon is not None:
                pokemon.desenhar(tela, camera, dt_pokemons)
                continue
            if bau is not None:
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

    def renderizar_player(self, tela, camera, ignorar_entidade_id=None):
        self._renderizar_player_local(tela, camera)

    def renderizar_estruturas(self, tela, camera):
        self.RenderizarEstruturas(tela, camera)

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        if ignorar_entidade_id is None and self.PlayerLocal is not None and getattr(self.PlayerLocal, "Ator", None) is not None:
            ignorar_entidade_id = getattr(self.PlayerLocal.Ator, "Id", None)
        self.RenderizarEntidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self._renderizar_player_local(tela, camera)
        self.RenderizarEstruturas(tela, camera)
