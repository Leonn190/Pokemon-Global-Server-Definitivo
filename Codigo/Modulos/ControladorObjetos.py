"""Controlador de objetos do mundo (entidades + estruturas)."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.GameObjeto import GameObjeto
from Codigo.Modulos.Colisor import Colisor
from Codigo.Modulos.Player.Player import Player


class ControladorObjetos:
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PlayerLocal = None
        self._fila_diffs_envio: List[Dict[str, object]] = []
        self._chunk_tamanho_tiles = 32
        self._objetos_colisao_por_chunk: Dict[Tuple[int, int], set[int]] = {}
        self._chunk_por_objeto: Dict[int, Tuple[int, int]] = {}

    def definir_player_local(self, player) -> None:
        self.PlayerLocal = player
        self._sincronizar_player_local()

    def montar_player_local(self, dados_player) -> Player:
        dados = dados_player if isinstance(dados_player, dict) else {}
        nome_skin = str(dados.get("skin", "S1.png"))
        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)

        ator = Ator(nome_skin=nome_skin, posicao=(float(pos[0]), float(pos[1])), escala_skin=1.45)
        if dados.get("id") is not None:
            ator.Id = int(dados.get("id"))
        ator.Nome = str(dados.get("nome") or dados.get("usuario") or "")

        player = Player(
            ator=ator,
            callback_diff=self.registrar_diff_local,
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
        self._objetos_colisao_por_chunk.clear()
        self._chunk_por_objeto.clear()
        for obj in self.ObjetosPorId.values():
            if isinstance(obj, dict):
                self._atualizar_indice_objeto_colisivo(obj)

    def _iter_colisores_proximos(self, posicao_player: Tuple[float, float]):
        px, py = posicao_player
        chunk_cx, chunk_cy = self._chunk_posicao(px, py)
        ids = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ids.update(self._objetos_colisao_por_chunk.get((chunk_cx + dx, chunk_cy + dy), set()))

        for oid in ids:
            obj = self.ObjetosPorId.get(oid)
            if not isinstance(obj, dict):
                continue
            dados = self._dados_colisao_objeto(obj)
            if dados is not None:
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
        colisores_proximos = [c for c in self._iter_colisores_proximos(posicao_depois) if c[0] != player_id]
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

    def registrar_diff_local(self, diff) -> None:
        if not isinstance(diff, dict):
            return
        self.aplicar_diff(diff)
        self._fila_diffs_envio.append(dict(diff))

    def enviar_diffs_pendentes(self, callback_envio) -> None:
        if not callable(callback_envio):
            return
        while self._fila_diffs_envio:
            callback_envio(self._fila_diffs_envio.pop(0))

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
            self.ObjetosPorId[oid] = dados_obj
            self._atualizar_indice_objeto_colisivo(dados_obj)
            return

        if objeto_id is None:
            return
        oid = int(objeto_id)

        if tipo == "update":
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
            return

        if tipo == "despawn":
            self.ObjetosPorId.pop(oid, None)
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
        self.ObjetosPorId = {int(k): dict(v) for k, v in objetos.items()}
        self._reindexar_objetos_colisivos()

    def _iter_tipos(self, prefixo):
        return [obj for obj in self.ObjetosPorId.values() if str(obj.get("tipo", "")).startswith(prefixo)]

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
        for obj in self._iter_tipos("entidade"):
            if ignorar_id is not None and int(obj.get("id", -1)) == int(ignorar_id):
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
        pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        respiracao_tempo = getattr(getattr(self.PlayerLocal, "Controle", None), "_tempo_respiracao", 0.0)
        ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=respiracao_tempo)
        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)
