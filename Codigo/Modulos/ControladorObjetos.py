"""Controlador de objetos do mundo (entidades + estruturas)."""

from __future__ import annotations

from typing import Dict, List

import pygame


class ControladorObjetos:
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PlayerLocal = None
        self._fila_diffs_envio: List[Dict[str, object]] = []


    def definir_player_local(self, player) -> None:
        self.PlayerLocal = player

    def atualizar_player_local(self, eventos, dt, mouse_pos_mundo_tiles) -> None:
        if self.PlayerLocal is None:
            return
        self.PlayerLocal.Controle.atualizar(eventos, dt, mouse_pos_mundo_tiles)

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
            return

        if tipo == "despawn":
            self.ObjetosPorId.pop(oid, None)

    def sincronizar_objetos(self, objetos):
        if not isinstance(objetos, dict):
            return
        self.ObjetosPorId = {int(k): dict(v) for k, v in objetos.items()}

    def _iter_tipos(self, prefixo):
        return [obj for obj in self.ObjetosPorId.values() if str(obj.get("tipo", "")).startswith(prefixo)]

    def RenderizarEntidades(self, tela, camera, ignorar_id=None):
        for obj in self._iter_tipos("entidade"):
            if ignorar_id is not None and int(obj.get("id", -1)) == int(ignorar_id):
                continue
            self._desenhar_objeto_generico(tela, camera, obj, (222, 233, 245))

    def RenderizarEstruturas(self, tela, camera):
        for obj in self._iter_tipos("estrutura"):
            self._desenhar_objeto_generico(tela, camera, obj, (125, 86, 54))

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        self.RenderizarEntidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self.RenderizarEstruturas(tela, camera)

    def _desenhar_objeto_generico(self, tela, camera, obj, cor):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))

        # Compatibilidade de unidade:
        # - clientes novos usam raio em TILES
        # - simulador antigo enviava raio em PIXELS (ex.: 12.0)
        # Se tratarmos 12.0 como tile, viram círculos gigantes (12 * TilePx).
        raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
        if raio_raw > 4.0:
            raio_px = int(raio_raw)
        else:
            raio_px = int(raio_raw * camera.TilePx)

        raio_px = max(3, min(80, raio_px))
        pygame.draw.circle(tela, cor, (int(px), int(py)), raio_px)
