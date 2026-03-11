"""Controlador de objetos do mundo (client): input, predição visual e sincronização autoritativa."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple
import math
import os
import threading
import time
import uuid

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.Baus import Bau
from Codigo.Geradores.Player.Controle import Controle
from Codigo.Geradores.Player.Inventario import Inventario
from Codigo.Geradores.Player.Perfil import Perfil
from Codigo.Geradores.PokemonMundo import Pokemon
from Codigo.Geradores.Projetil import Projetil
from Codigo.Modulos.Colisor import Colisor
from Codigo.Geradores.EstruturaNaturais import tipo_estrutura_natural_por_codigo
from Codigo.Prefabs.Fluxos import Fluxo


class ControladorObjetos:
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PlayerLocal = None

        self.PokemonsPorId: Dict[int, Pokemon] = {}
        self.BausPorId: Dict[int, Bau] = {}
        self.AtoresRemotosPorId: Dict[int, Ator] = {}
        self.ProjeteisPorId: Dict[int, Projetil] = {}

        self._lock_objetos = threading.RLock()
        self._lock_diffs = threading.Lock()

        self._fila_saida_envio: List[Dict[str, object]] = []
        self._callback_loop_rede: Optional[Callable[[Dict[str, object]], Dict[str, object] | None]] = None
        self._thread_rede: Optional[threading.Thread] = None
        self._thread_rede_ativa = False
        self._intervalo_rede = 0.05
        self._tick_cliente = 0
        self._ultimo_tick_recebido = 0

        # Índice espacial por chunk (performance de visibilidade/consulta local)
        self._chunk_tamanho_tiles = 10
        self._ids_por_chunk: Dict[Tuple[int, int], set[int]] = {}
        self._chunk_por_objeto: Dict[int, Tuple[int, int]] = {}

        self._origem_cliente = "client"
        self._fluxo_mira = Fluxo("bolinhas")
        self._ultimo_render_pokemons_ms = pygame.time.get_ticks()
        self._seq_id_projetil_predito = -1
        self._pokemon_alvo_local_id: Optional[int] = None
        self._bloqueio_sync_autoritario_ate = 0.0
        self._tokens_colisao_candidata_enviados: set[str] = set()
        self._janela_bloqueio_sync_autoritario_s = 0.12
        self._cache_sprites_fallback: Dict[str, Optional[pygame.Surface]] = {}
        self._snapshot_player_supervisao_rapida: Optional[Dict[str, object]] = None
        self._snapshot_player_supervisao_lenta: Optional[Dict[str, object]] = None
        self._ultimo_envio_supervisao_rapida = 0.0
        self._ultimo_envio_supervisao_lenta = 0.0
        self._intervalo_supervisao_rapida_s = 0.05
        self._intervalo_supervisao_lenta_s = 1.5

    # ---------------------------------------------------------------------
    # Player local
    # ---------------------------------------------------------------------
    def definir_player_local(self, player) -> None:
        self.PlayerLocal = player
        self._snapshot_player_supervisao_rapida = None
        self._snapshot_player_supervisao_lenta = None
        self._ultimo_envio_supervisao_rapida = 0.0
        self._ultimo_envio_supervisao_lenta = 0.0
        self._sincronizar_player_local()

    def montar_player_local(self, dados_player):
        dados = dados_player if isinstance(dados_player, dict) else {}
        ator = self._hidratar_ator_payload(None, dados, com_controle=True)
        self.definir_player_local(ator)
        return ator

    def _hidratar_ator_payload(self, ator: Optional[Ator], dados: Dict[str, object], com_controle: bool) -> Ator:
        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)

        if ator is None:
            ator = Ator(nome_skin=str(dados.get("skin", "S1")), posicao=(float(pos[0]), float(pos[1])), escala_skin_tiles=1.0, tile_px=50)

        if dados.get("id") is not None:
            ator.Id = int(dados.get("id"))
        ator.definir_posicao(float(pos[0]), float(pos[1]))

        nome = dados.get("nome") or dados.get("usuario")
        if nome:
            ator.Nome = str(nome)

        skin = dados.get("skin")
        if skin and str(skin) != str(getattr(ator, "NomeSkin", "")):
            ator.set_nome_skin(str(skin))

        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        if "angulo" in estado:
            ator.definir_angulo_olhar(float(estado.get("angulo", 0.0)))
        if bool(estado.get("tapa")):
            ator.iniciar_tapa()

        if ator.Perfil is None:
            ator.Perfil = Perfil()
        if ator.Inventario is None:
            ator.Inventario = Inventario()
        if isinstance(dados.get("perfil"), dict):
            ator.Perfil.aplicar_serializado(dados.get("perfil"))
        if isinstance(dados.get("inventario"), dict):
            ator.Inventario.aplicar_serializado(dados.get("inventario"))

        ator.Controle = Controle(ator=ator, velocidade_tiles=getattr(ator.Perfil, "VelocidadeBaseTiles", 5.0)) if com_controle else None
        return ator

    def atualizar_player_local(self, eventos, dt, mouse_pos_mundo_tiles, gerenciador_fps=None) -> None:
        if self.PlayerLocal is None:
            return

        if self._sync_autoritario_ativo():
            if self.PlayerLocal.Controle is not None:
                self.PlayerLocal.Controle.atualizar_bloqueado(dt)
            self._atualizar_projeteis_visuais(dt)
            self._fluxo_mira.atualizar(dt)
            return

        posicao_antes = tuple(self.PlayerLocal.Posicao)
        self.PlayerLocal.Controle.atualizar(eventos, dt, mouse_pos_mundo_tiles)
        self._resolver_colisao_player_local(posicao_antes, dt)
        self._processar_interacoes_player()

        self._processar_intencao_arremesso_local()
        self._atualizar_projeteis_visuais(dt)
        self._fluxo_mira.atualizar(dt)

    def _processar_intencao_arremesso_local(self) -> None:
        if self.PlayerLocal is None or self.PlayerLocal.Controle is None:
            return
        acao = self.PlayerLocal.Controle.consumir_acao_arremesso()
        if not isinstance(acao, dict):
            return

        item = dict(acao.get("item") or {})
        origem = acao.get("origem") if isinstance(acao.get("origem"), (list, tuple)) else tuple(self.PlayerLocal.Posicao)
        destino = acao.get("destino") if isinstance(acao.get("destino"), (list, tuple)) else tuple(self.PlayerLocal.Posicao)

        dx, dy = float(destino[0]) - float(origem[0]), float(destino[1]) - float(origem[1])
        n = math.hypot(dx, dy) or 1.0
        direcao = (dx / n, dy / n)
        estilo = str(item.get("Estilo") or item.get("estilo") or "item").lower()
        alcance = 5.0 if estilo == "fruta" else (8.0 if "sniperball" in str(item.get("Nome", "")).lower() else 6.0)
        token = str(uuid.uuid4())

        # Spawn preditivo local (somente visual)
        self._seq_id_projetil_predito -= 1
        oid = self._seq_id_projetil_predito
        payload_pred = {
            "id": oid,
            "tipo": "entidade_projetil",
            "tipo_projetil": estilo,
            "subtipo": str(item.get("Nome") or "item"),
            "item_base_id": str(item.get("Code") or ""),
            "dono_id": int(getattr(self.PlayerLocal, "Id", 0) or 0),
            "posicao": [float(origem[0]), float(origem[1])],
            "estado": {
                "direcao": [direcao[0], direcao[1]],
                "velocidade": 11.0,
                "alcance": alcance,
                "distancia_conferencia_inicial": 4.0,
                "predito_local": True,
                "autoritativo": False,
                "token_arremesso": token,
            },
            "token_arremesso": token,
        }
        self.aplicar_diff({"tipo": "spawn", "objeto_id": oid, "payload": payload_pred})

        # Evento para servidor (server autoritativo resolve projétil/colisão/captura)
        self.EnfileirarDiffRapida({
            "tipo": "evento",
            "evento": "projetil_arremesso_intencao",
            "payload": {
                "token_arremesso": token,
                "dono_id": int(getattr(self.PlayerLocal, "Id", 0) or 0),
                "item": item,
                "origem": [float(origem[0]), float(origem[1])],
                "destino": [float(destino[0]), float(destino[1])],
                "direcao": [direcao[0], direcao[1]],
                "alcance": alcance,
                "velocidade": 11.0,
                "distancia_conferencia_inicial": 4.0,
            },
        })

    def _atualizar_projeteis_visuais(self, dt: float) -> None:
        with self._lock_objetos:
            projeteis = list(self.ProjeteisPorId.values())
            objetos_snapshot = dict(self.ObjetosPorId)

        for p in projeteis:
            p.atualizar_visual(dt)
            if (not p.Terminado) and (not p.AguardandoConfirmacaoColisao) and (not p.ColisaoConfirmada):
                alvo = self._detectar_colisao_candidata_local_projetil(p, objetos_snapshot)
                if alvo is not None:
                    p.AguardandoConfirmacaoColisao = True
                    p.ColisaoCandidata = int(alvo.get("id", 0) or 0)
                    self._enviar_colisao_candidata_projetil(p, p.ColisaoCandidata)
            if p.Terminado and p.PreditoLocal and not p.Autoritativo:
                self.aplicar_diff({"tipo": "despawn", "objeto_id": int(p.Id)})

    def _detectar_colisao_candidata_local_projetil(self, proj: Projetil, objetos_snapshot: Dict[int, Dict[str, object]]):
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
            if subtipo == "pokemon":
                cap = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
                cap_fase = str(cap.get("fase", "nenhuma") or "nenhuma")
                if bool(cap.get("captura_pendente", False)) or cap_fase in {"iniciada", "absorcao", "bola_no_chao", "tremida1", "tremida2", "tremida3", "retorno_bola", "sucesso"}:
                    continue
            candidato = subtipo == "pokemon" or subtipo == "player" or subtipo == "bau" or tipo.startswith("estrutura")
            if not candidato:
                continue
            raio_alvo = float(obj.get("raio_colisao", 0.2) or 0.2)
            limite = float(getattr(proj, "Colisor", None).raio_colisao if getattr(proj, "Colisor", None) is not None else 0.18) + raio_alvo
            if d2 <= (limite * limite):
                return obj
        return None

    def _enviar_colisao_candidata_projetil(self, proj: Projetil, alvo_id: int) -> None:
        token = str(getattr(proj, "TokenArremesso", "") or "")
        if not token or token in self._tokens_colisao_candidata_enviados:
            return
        self._tokens_colisao_candidata_enviados.add(token)
        self.EnfileirarDiffRapida({
            "tipo": "evento",
            "evento": "projetil_colisao_candidata",
            "payload": {
                "token_arremesso": token,
                "projetil_id": int(getattr(proj, "Id", 0) or 0),
                "alvo_id": int(alvo_id or 0),
                "ponto_estimado": [float(proj.Posicao[0]), float(proj.Posicao[1])],
            },
        })

    # ---------------------------------------------------------------------
    # Índice espacial
    # ---------------------------------------------------------------------
    def _chunk_posicao(self, x: float, y: float) -> Tuple[int, int]:
        return (int(math.floor(float(x) / self._chunk_tamanho_tiles)), int(math.floor(float(y) / self._chunk_tamanho_tiles)))

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

    def _reindexar_tudo(self) -> None:
        self._ids_por_chunk.clear()
        self._chunk_por_objeto.clear()
        for oid, payload in self.ObjetosPorId.items():
            if isinstance(payload, dict):
                self._upsert_indice_chunk_objeto(int(oid), payload)

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
        ids: set[int] = set()
        with self._lock_objetos:
            for dx in range(-alcance_x, alcance_x + 1):
                for dy in range(-alcance_y, alcance_y + 1):
                    ids.update(self._ids_por_chunk.get((cx + dx, cy + dy), set()))
            return [self.ObjetosPorId.get(oid) for oid in ids if oid in self.ObjetosPorId]

    # ---------------------------------------------------------------------
    # Diffs e eventos
    # ---------------------------------------------------------------------
    def _marcar_diff_local(self, diff: Dict[str, object]) -> Dict[str, object]:
        meta = dict(diff.get("meta", {})) if isinstance(diff.get("meta"), dict) else {}
        meta["origem"] = self._origem_cliente
        if self.PlayerLocal is not None:
            meta["autor"] = str(getattr(self.PlayerLocal, "Nome", "") or "")
        diff["meta"] = meta
        return diff

    def _origem_diff(self, diff: Dict[str, object]) -> str:
        meta = diff.get("meta") if isinstance(diff.get("meta"), dict) else {}
        return str(meta.get("origem", "")).strip().lower()

    def _id_player_local(self) -> int:
        if self.PlayerLocal is None:
            return -1
        return int(getattr(self.PlayerLocal, "Id", -1))

    def _eh_diff_player_local(self, diff: Dict[str, object]) -> bool:
        return int(diff.get("objeto_id", -1)) == self._id_player_local()

    def _eh_diff_autoritativa_server(self, diff: Dict[str, object]) -> bool:
        meta = diff.get("meta") if isinstance(diff.get("meta"), dict) else {}
        if bool(meta.get("autoritativo", False)):
            return True
        return self._origem_diff(diff) == "server"

    def _ativar_bloqueio_sync_autoritario(self) -> None:
        self._bloqueio_sync_autoritario_ate = time.monotonic() + float(self._janela_bloqueio_sync_autoritario_s)

    def _sync_autoritario_ativo(self) -> bool:
        return time.monotonic() < float(self._bloqueio_sync_autoritario_ate)

    def _deve_ignorar_diff(self, diff: Dict[str, object]) -> bool:
        if self.PlayerLocal is None or not self._eh_diff_player_local(diff):
            return False
        if self._eh_diff_autoritativa_server(diff):
            return False
        return self._origem_diff(diff) == self._origem_cliente

    def EnfileirarDiffRapida(self, diff: Dict[str, object]) -> None:
        with self._lock_diffs:
            self._fila_saida_envio.append(self._marcar_diff_local(diff))

    def EnfileirarDiffLenta(self, diff: Dict[str, object]) -> None:
        self.EnfileirarDiffRapida(diff)

    def ColetarDiffsRapidas(self) -> List[Dict[str, object]]:
        with self._lock_diffs:
            lote = self._fila_saida_envio
            self._fila_saida_envio = []
        return lote

    def ColetarDiffsLentas(self) -> List[Dict[str, object]]:
        return self.ColetarDiffsRapidas()

    def _supervisionar_player_e_enfileirar_saida(self) -> None:
        if self.PlayerLocal is None:
            return
        agora = time.monotonic()
        if (agora - self._ultimo_envio_supervisao_rapida) >= self._intervalo_supervisao_rapida_s:
            self._coletar_supervisao_player_local(rapida=True)
            self._ultimo_envio_supervisao_rapida = agora
        if (agora - self._ultimo_envio_supervisao_lenta) >= self._intervalo_supervisao_lenta_s:
            self._coletar_supervisao_player_local(rapida=False)
            self._ultimo_envio_supervisao_lenta = agora

    def iniciar_threads_diffs(self, callback_loop_rapido=None, callback_loop_lento=None, intervalo_rapido=0.05, intervalo_lento=5.0, callback_loop_rede=None) -> None:
        callback = callback_loop_rede if callable(callback_loop_rede) else (callback_loop_rapido if callable(callback_loop_rapido) else None)
        self._callback_loop_rede = callback
        self._intervalo_rede = max(0.02, float(intervalo_rapido))
        if not (self._thread_rede and self._thread_rede.is_alive()):
            self._thread_rede_ativa = True
            self._thread_rede = threading.Thread(target=self._loop_rede, name="ControladorObjetosRedeThread", daemon=True)
            self._thread_rede.start()

    def parar_threads_diffs(self, timeout=2.0) -> None:
        self._thread_rede_ativa = False
        if self._thread_rede and self._thread_rede.is_alive():
            self._thread_rede.join(timeout=timeout)

    def _loop_rede(self) -> None:
        while self._thread_rede_ativa:
            self._supervisionar_player_e_enfileirar_saida()
            envio = self.ColetarDiffsRapidas()
            eventos = [d for d in envio if str(d.get("tipo", "")).strip().lower() == "evento"]
            updates = [d for d in envio if str(d.get("tipo", "")).strip().lower() != "evento"]
            envelope = {
                "tick_cliente": int(self._tick_cliente),
                "ultimo_tick_recebido": int(self._ultimo_tick_recebido),
                "eventos": eventos,
                "updates": updates,
            }
            self._tick_cliente += 1
            resposta = {}
            if self._callback_loop_rede is not None:
                try:
                    resp = self._callback_loop_rede(envelope)
                    if isinstance(resp, dict):
                        resposta = resp
                except Exception:
                    if envio:
                        with self._lock_diffs:
                            self._fila_saida_envio = envio + self._fila_saida_envio
            pacotes = resposta.get("pacotes", []) if isinstance(resposta.get("pacotes"), list) else []
            for pacote in pacotes:
                if not isinstance(pacote, dict):
                    continue
                tick = int(pacote.get("tick", 0) or 0)
                if tick <= 0 or tick <= self._ultimo_tick_recebido:
                    continue
                diffs = pacote.get("diffs", []) if isinstance(pacote.get("diffs"), list) else []
                for diff in diffs:
                    if isinstance(diff, dict) and not self._deve_ignorar_diff(diff):
                        self.aplicar_diff(diff)
                self._ultimo_tick_recebido = tick
            time.sleep(self._intervalo_rede)

    # ---------------------------------------------------------------------
    # Aplicação de snapshot/diff/evento
    # ---------------------------------------------------------------------
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

    def _eh_payload_projetil(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"entidade_projetil", "projetil"}

    def _upsert_especializado(self, oid: int, payload: Dict[str, object]) -> None:
        if self._eh_payload_pokemon(payload):
            poke = self.PokemonsPorId.get(oid)
            if poke is None:
                self.PokemonsPorId[oid] = Pokemon(payload)
            else:
                poke.aplicar_snapshot(payload)
        else:
            self.PokemonsPorId.pop(oid, None)

        if self._eh_payload_bau(payload):
            bau = self.BausPorId.get(oid)
            if bau is None:
                self.BausPorId[oid] = Bau.from_snapshot(payload)
            else:
                bau.aplicar_snapshot(payload)
        else:
            self.BausPorId.pop(oid, None)

        if str(payload.get("tipo", "")).strip().lower() == "entidade_player":
            if self.PlayerLocal is None or int(getattr(self.PlayerLocal, "Id", -1)) != int(oid):
                dados = dict(payload)
                dados["id"] = oid
                self.AtoresRemotosPorId[oid] = self._hidratar_ator_payload(self.AtoresRemotosPorId.get(oid), dados, com_controle=False)
        else:
            self.AtoresRemotosPorId.pop(oid, None)

        if self._eh_payload_projetil(payload):
            estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
            token = str(payload.get("token_arremesso") or estado.get("token_arremesso") or "")
            if token:
                self._reconciliar_projetil_predito_por_token(token, int(payload.get("id", oid)))

            proj = self.ProjeteisPorId.get(oid)
            if proj is None:
                self.ProjeteisPorId[oid] = Projetil(payload)
            else:
                proj.aplicar_snapshot(payload)
        else:
            self.ProjeteisPorId.pop(oid, None)

    def _aplicar_payload_no_player_local(self, payload: Dict[str, object]) -> None:
        if self.PlayerLocal is None:
            return
        ator = self.PlayerLocal

        pos = payload.get("posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            ator.definir_posicao(float(pos[0]), float(pos[1]))

        nome = payload.get("nome") or payload.get("usuario")
        if nome:
            ator.Nome = str(nome)

        skin = payload.get("skin")
        if skin and str(skin) != str(getattr(ator, "NomeSkin", "")):
            ator.set_nome_skin(str(skin))

        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        if "angulo" in estado:
            ator.definir_angulo_olhar(float(estado.get("angulo", 0.0)))
        if bool(estado.get("tapa")):
            ator.iniciar_tapa()

        if ator.Perfil is not None and isinstance(payload.get("perfil"), dict):
            ator.Perfil.aplicar_serializado(payload.get("perfil"))
        if ator.Inventario is not None and isinstance(payload.get("inventario"), dict):
            ator.Inventario.aplicar_serializado(payload.get("inventario"))

        self._ativar_bloqueio_sync_autoritario()

    def _reconciliar_projetil_predito_por_token(self, token: str, oid_autoritativo: int) -> None:
        alvo = self.ProjeteisPorId.get(int(oid_autoritativo))
        for oid_local, proj in list(self.ProjeteisPorId.items()):
            if oid_local == int(oid_autoritativo):
                continue
            if not proj.PreditoLocal:
                continue
            if str(getattr(proj, "TokenArremesso", "")) != str(token):
                continue
            if alvo is None:
                proj.Id = int(oid_autoritativo)
                proj.Autoritativo = True
                self.ProjeteisPorId[int(oid_autoritativo)] = proj
                self.ProjeteisPorId.pop(oid_local, None)
                payload = self.ObjetosPorId.pop(oid_local, None)
                if isinstance(payload, dict):
                    payload["id"] = int(oid_autoritativo)
                    est = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                    est["autoritativo"] = True
                    est["predito_local"] = True
                    payload["estado"] = est
                    self.ObjetosPorId[int(oid_autoritativo)] = payload
                    self._remover_indice_chunk_objeto(oid_local)
                    self._upsert_indice_chunk_objeto(int(oid_autoritativo), payload)
            else:
                alvo.PreditoLocal = True
                alvo.Autoritativo = True
                alvo.TokenArremesso = str(token)
                self.ProjeteisPorId.pop(oid_local, None)
                self.ObjetosPorId.pop(oid_local, None)
                self._remover_indice_chunk_objeto(oid_local)
            break

    def aplicar_diff(self, diff):
        if not isinstance(diff, dict):
            return

        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}

        if tipo == "evento":
            self._aplicar_evento_rapido(str(diff.get("evento", "")), payload)
            return

        if tipo == "spawn":
            oid = int(payload.get("id", objeto_id or 0))
            dados = dict(payload)
            dados["id"] = oid
            with self._lock_objetos:
                self.ObjetosPorId[oid] = dados
                self._upsert_indice_chunk_objeto(oid, dados)
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
                self._upsert_indice_chunk_objeto(oid, atual)
                self._upsert_especializado(oid, atual)

            if self._eh_diff_player_local(diff) and self._eh_diff_autoritativa_server(diff):
                self._aplicar_payload_no_player_local(atual)
            return

        if tipo == "despawn":
            with self._lock_objetos:
                self.ObjetosPorId.pop(oid, None)
                self.PokemonsPorId.pop(oid, None)
                self.BausPorId.pop(oid, None)
                self.AtoresRemotosPorId.pop(oid, None)
                self.ProjeteisPorId.pop(oid, None)
                self._remover_indice_chunk_objeto(oid)

    def _aplicar_evento_rapido(self, evento: str, payload: Dict[str, object]) -> None:
        if evento == "projetil_colisao_negada":
            self._aplicar_evento_colisao_projetil(payload, confirmada=False)
            return
        if evento == "projetil_colisao_confirmada":
            self._aplicar_evento_colisao_projetil(payload, confirmada=True)
            return
        if evento.startswith("projetil_"):
            return

        if evento == "pokemon_frutificado":
            self._aplicar_evento_pokemon_frutificado(payload)
            return

        if evento.startswith("pokemon_captura_"):
            self._aplicar_evento_captura(payload, evento)
            return

    def _aplicar_evento_pokemon_frutificado(self, payload: Dict[str, object]) -> None:
        poke = self.PokemonsPorId.get(int(payload.get("pokemon_id", -1)))
        if poke is None:
            return
        estado = payload.get("estado_frutificacao") if isinstance(payload.get("estado_frutificacao"), dict) else None
        frutas = payload.get("frutas_aplicadas") if isinstance(payload.get("frutas_aplicadas"), list) else None
        if estado is not None:
            poke.EstadoFrutificacao = dict(estado)
        if frutas is not None:
            poke.FrutasAplicadas = list(frutas)

    def _aplicar_evento_captura(self, payload: Dict[str, object], nome_evento: str) -> None:
        poke = self.PokemonsPorId.get(int(payload.get("pokemon_id", -1)))
        if poke is None:
            return
        captura = payload.get("captura") if isinstance(payload.get("captura"), dict) else {}
        if "fase" not in captura:
            captura["fase"] = nome_evento.replace("pokemon_captura_", "")
        poke.capturar(captura)

    def _aplicar_evento_colisao_projetil(self, payload: Dict[str, object], confirmada: bool) -> None:
        token = str(payload.get("token_arremesso") or "")
        if token:
            self._tokens_colisao_candidata_enviados.discard(token)
        proj = None
        for p in self.ProjeteisPorId.values():
            if token and str(getattr(p, "TokenArremesso", "")) == token:
                proj = p
                break
        if proj is None:
            pid = int(payload.get("projetil_id", -1) or -1)
            proj = self.ProjeteisPorId.get(pid)
        if proj is None:
            return
        proj.AguardandoConfirmacaoColisao = False
        if confirmada:
            proj.ColisaoConfirmada = True
            proj.Colidiu = True
            proj.Terminado = True
            proj.Ativo = False
        else:
            proj.ColisaoCandidata = None

    def sincronizar_objetos(self, objetos):
        if not isinstance(objetos, dict):
            return
        with self._lock_objetos:
            self.ObjetosPorId = {int(k): dict(v) for k, v in objetos.items()}
            self.PokemonsPorId = {}
            self.BausPorId = {}
            self.AtoresRemotosPorId = {}
            self.ProjeteisPorId = {}
            self._reindexar_tudo()
            snapshot = list(self.ObjetosPorId.items())
        for oid, payload in snapshot:
            if isinstance(payload, dict):
                with self._lock_objetos:
                    self._upsert_especializado(int(oid), payload)

    def AplicarDiffRapida(self, diff):
        self.aplicar_diff(diff)

    def AplicarDiffLenta(self, diff):
        self.aplicar_diff(diff)

    def _snapshot_player_local_rapido(self) -> Dict[str, object]:
        ator = self.PlayerLocal
        controle = getattr(ator, "Controle", None)
        return {
            "id": int(getattr(ator, "Id", 0) or 0),
            "tipo": "entidade_player",
            "posicao": [float(ator.Posicao[0]), float(ator.Posicao[1])],
            "raio_colisao": float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35) or 0.35),
            "estado": {
                "angulo": float(getattr(ator, "AnguloOlhar", 0.0) or 0.0),
                "tapa": bool(ator.esta_tapando() if hasattr(ator, "esta_tapando") else False),
                "mirando": bool(getattr(controle, "_mirando", False)) if controle is not None else False,
                "inventario_aberto": bool(getattr(controle, "InventarioAberto", False)) if controle is not None else False,
                "correndo": bool(getattr(controle, "_tentando_correr", False)) if controle is not None else False,
            },
        }

    def _snapshot_player_local_lento(self) -> Dict[str, object]:
        ator = self.PlayerLocal
        perfil = getattr(ator, "Perfil", None)
        inventario = getattr(ator, "Inventario", None)
        return {
            "id": int(getattr(ator, "Id", 0) or 0),
            "tipo": "entidade_player",
            "nome": str(getattr(ator, "Nome", "") or ""),
            "skin": str(getattr(ator, "NomeSkin", "S1") or "S1"),
            "perfil": perfil.serializar() if perfil is not None else {},
            "inventario": inventario.serializar() if inventario is not None else {},
        }

    def _delta_snapshot(self, anterior: Optional[Dict[str, object]], atual: Dict[str, object]) -> Dict[str, object]:
        if not isinstance(anterior, dict):
            return dict(atual)
        delta: Dict[str, object] = {}
        for k, v in atual.items():
            if k not in anterior:
                delta[k] = v
                continue
            av = anterior.get(k)
            if isinstance(v, dict) and isinstance(av, dict):
                if v != av:
                    delta[k] = dict(v)
                continue
            if v != av:
                delta[k] = v
        return delta

    def _coletar_supervisao_player_local(self, rapida: bool) -> None:
        if self.PlayerLocal is None:
            return
        ator_id = int(getattr(self.PlayerLocal, "Id", 0) or 0)
        if ator_id <= 0:
            return
        if rapida:
            snapshot = self._snapshot_player_local_rapido()
            delta = self._delta_snapshot(self._snapshot_player_supervisao_rapida, snapshot)
            self._snapshot_player_supervisao_rapida = snapshot
        else:
            snapshot = self._snapshot_player_local_lento()
            delta = self._delta_snapshot(self._snapshot_player_supervisao_lenta, snapshot)
            self._snapshot_player_supervisao_lenta = snapshot
        if not delta:
            return
        delta.setdefault("id", ator_id)
        delta.setdefault("tipo", "entidade_player")
        self.EnfileirarDiffRapida({"tipo": "update", "objeto_id": ator_id, "payload": delta})

    def _sincronizar_player_local(self) -> None:
        if self.PlayerLocal is None:
            return
        ator = self.PlayerLocal
        if getattr(ator, "Id", None) is None:
            return
        self.aplicar_diff({
            "tipo": "update",
            "objeto_id": int(ator.Id),
            "payload": {
                "id": int(ator.Id),
                "tipo": "entidade_player",
                "nome": getattr(ator, "Nome", ""),
                "skin": str(getattr(ator, "NomeSkin", "S1")),
                "posicao": [ator.Posicao[0], ator.Posicao[1]],
                "raio_colisao": getattr(ator.Colisor, "raio_colisao", 0.35),
            },
        })

    def _iter_colisores_proximos_por_raio(self, posicao: Tuple[float, float], raio_tiles: float = 10.0):
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
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            if ((sx - px) ** 2 + (sy - py) ** 2) > r2:
                continue
            raio = float(obj.get("raio_colisao", 0.0) or 0.0)
            if raio <= 0.0:
                continue
            yield (int(obj.get("id", 0)), sx, sy, raio, str(obj.get("tipo", "")), float(obj.get("campo", 0.0) or 0.0), float(obj.get("intensidade", 0.0) or 0.0))

    def _resolver_colisao_player_local(self, posicao_antes: Tuple[float, float], dt: float) -> None:
        if self.PlayerLocal is None:
            return
        ator = self.PlayerLocal
        depois = tuple(ator.Posicao)
        player_id = getattr(ator, "Id", None)
        raio_ator = max(0.0, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))
        colisores = [c for c in self._iter_colisores_proximos_por_raio(depois, raio_tiles=10.0) if c[0] != player_id]
        px, py = Colisor.resolver_movimento_com_colisores(
            posicao_antes=posicao_antes,
            posicao_depois=depois,
            raio_entidade=raio_ator,
            colisores=colisores,
            dt=dt,
        )
        ator.definir_posicao(px, py)

    def _processar_interacoes_player(self) -> None:
        if self.PlayerLocal is None:
            return
        with self._lock_objetos:
            interativos = list(self.BausPorId.values())
        for obj in interativos:
            diff = obj.processar_interacao_player(self.PlayerLocal)
            if isinstance(diff, dict):
                payload = diff.get("payload") if isinstance(diff.get("payload"), dict) else {}
                payload["dono_id"] = int(getattr(self.PlayerLocal, "Id", 0) or 0)
                diff["payload"] = payload
                self.EnfileirarDiffRapida(diff)

    def _atualizar_alvo_local_captura(self, camera) -> None:
        if self.PlayerLocal is None or camera is None:
            self._pokemon_alvo_local_id = None
            return
        mouse_mundo = camera.tela_para_mundo_tiles(pygame.mouse.get_pos())
        mx, my = float(mouse_mundo[0]), float(mouse_mundo[1])
        px, py = self.PlayerLocal.Posicao

        melhor_id = None
        melhor_score = None
        with self._lock_objetos:
            itens = list(self.PokemonsPorId.items())
        for oid, poke in itens:
            fase = str(getattr(poke, "CapturaEstado", {}).get("fase", "nenhuma") or "nenhuma")
            pendente = bool(getattr(poke, "CapturaEstado", {}).get("captura_pendente", False))
            invalido = pendente or fase in {"iniciada", "absorcao", "bola_no_chao", "tremida1", "tremida2", "tremida3", "retorno_bola", "sucesso", "finalizada"}
            if invalido:
                continue
            dxm, dym = float(poke.Posicao[0]) - mx, float(poke.Posicao[1]) - my
            dmouse = math.hypot(dxm, dym)
            if dmouse > 1.35:
                continue
            dplayer = math.hypot(float(poke.Posicao[0]) - float(px), float(poke.Posicao[1]) - float(py))
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

    def _render_fallback_objeto(self, tela, camera, obj: Dict[str, object], cor_fallback=(222, 233, 245)):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))

        codigo_natural = obj.get("codigo_natural")
        if codigo_natural is None and isinstance(obj.get("estado"), dict):
            codigo_natural = obj["estado"].get("codigo_natural")
        cfg_natural = tipo_estrutura_natural_por_codigo(codigo_natural)

        sprite_path = str(obj.get("sprite", "")).strip()
        if not sprite_path and cfg_natural:
            sprite_path = str(cfg_natural.get("sprite", "")).strip()

        sprite = self._obter_sprite_fallback(sprite_path)
        if sprite is not None:
            sprite_rect = sprite.get_rect(center=(int(px), int(py)))
            tela.blit(sprite, sprite_rect)
            return

        raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
        raio_px = int(raio_raw if raio_raw > 4.0 else raio_raw * camera.TilePx)
        raio_px = max(3, min(80, raio_px))
        pygame.draw.circle(tela, cor_fallback, (int(px), int(py)), raio_px)

    # ---------------------------------------------------------------------
    # Render
    # ---------------------------------------------------------------------
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
        self._atualizar_alvo_local_captura(camera)
        agora = pygame.time.get_ticks()
        dt_pokemons = max(0.0, (agora - self._ultimo_render_pokemons_ms) / 1000.0)
        self._ultimo_render_pokemons_ms = agora

        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue
            if str(obj.get("tipo", "")).startswith("estrutura"):
                continue
            if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                continue

            poke = self.PokemonsPorId.get(oid)
            if poke is not None:
                poke.render(tela, camera, dt_pokemons)
                continue

            bau = self.BausPorId.get(oid)
            if bau is not None:
                bau.render(tela, camera)
                continue

            proj = self.ProjeteisPorId.get(oid)
            if proj is not None:
                proj.desenhar(tela, camera)
                continue

            ator_remoto = self.AtoresRemotosPorId.get(oid)
            if ator_remoto is not None:
                ator_remoto.set_tile_px(getattr(camera, "TilePx", 50))
                pos_tela = camera.mundo_para_tela_px(ator_remoto.Posicao)
                ator_remoto.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=0.0)
                if getattr(ator_remoto, "Nome", ""):
                    Ator.desenhar_nome(tela, pos_tela, ator_remoto.Nome)
                continue

            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(222, 233, 245))

    def RenderizarEstruturas(self, tela, camera):
        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            if not str(obj.get("tipo", "")).startswith("estrutura"):
                continue
            if self._objeto_posicao_tela_se_visivel(obj, camera, margem_px=220) is None:
                continue
            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(125, 86, 54))

    def _renderizar_player_local(self, tela, camera):
        if self.PlayerLocal is None:
            return
        ator = self.PlayerLocal
        ator.set_tile_px(getattr(camera, "TilePx", 50))
        pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        respiracao_tempo = getattr(getattr(ator, "Controle", None), "_tempo_respiracao", 0.0)
        ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=respiracao_tempo)

        estado_mira = ator.Controle.estado_mira(camera.tela_para_mundo_tiles(pygame.mouse.get_pos())) if ator.Controle else None
        if estado_mira:
            ini = camera.mundo_para_tela_px(estado_mira["inicio"])
            fim = camera.mundo_para_tela_px(estado_mira["fim"])
            self._fluxo_mira.desenhar(tela, ini, fim)

        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        if ignorar_entidade_id is None and self.PlayerLocal is not None:
            ignorar_entidade_id = getattr(self.PlayerLocal, "Id", None)
        self.RenderizarEntidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self._renderizar_player_local(tela, camera)
        self.RenderizarEstruturas(tela, camera)

    def renderizar_player(self, tela, camera, ignorar_entidade_id=None):
        self._renderizar_player_local(tela, camera)

    def renderizar_estruturas(self, tela, camera):
        self.RenderizarEstruturas(tela, camera)
