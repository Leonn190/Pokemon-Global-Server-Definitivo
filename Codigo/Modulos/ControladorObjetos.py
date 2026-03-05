"""Controlador de objetos do mundo (entidades + estruturas)."""

from __future__ import annotations

from typing import Dict, List
import math
import os

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Modulos.Player.Player import Player
from Codigo.Prefabs.Texto import Texto
from Codigo.Modulos.ConfigEstruturasNaturais import tipo_estrutura_natural_por_codigo


class ControladorObjetos:
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PlayerLocal = None
        self._fila_diffs_envio: List[Dict[str, object]] = []
        self._cache_nome_texto: Dict[str, Texto] = {}
        self._cache_sprites: Dict[str, pygame.Surface] = {}

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
        ator.Nome = str(dados.get("nome") or dados.get("usuario") or "Player")

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
                    "posicao": [ator.Posicao[0], ator.Posicao[1]],
                    "raio_colisao": getattr(ator, "RaioColisao", 0.35),
                },
            }
        )

    def atualizar_player_local(self, eventos, dt, mouse_pos_mundo_tiles) -> None:
        if self.PlayerLocal is None:
            return
        self.PlayerLocal.Controle.atualizar(eventos, dt, mouse_pos_mundo_tiles)
        self._sincronizar_player_local()

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
        self._desenhar_nome_jogador(tela, pos_tela, getattr(ator, "Nome", "Player"))

    def _desenhar_objeto_generico(self, tela, camera, obj, cor):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))

        codigo_natural = obj.get("codigo_natural")
        if codigo_natural is None and isinstance(obj.get("estado"), dict):
            codigo_natural = obj["estado"].get("codigo_natural")
        cfg_natural = tipo_estrutura_natural_por_codigo(codigo_natural)

        sprite_path = str(obj.get("sprite", "")).strip()
        if not sprite_path and cfg_natural:
            sprite_path = str(cfg_natural.get("sprite", "")).strip()
        sprite = self._obter_sprite(sprite_path)
        if sprite is not None:
            sprite_rect = sprite.get_rect(midbottom=(int(px), int(py) + int(camera.TilePx * 0.2)))
            tela.blit(sprite, sprite_rect)
        else:
            raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
            if raio_raw > 4.0:
                raio_px = int(raio_raw)
            else:
                raio_px = int(raio_raw * camera.TilePx)
            raio_px = max(3, min(80, raio_px))
            pygame.draw.circle(tela, cor, (int(px), int(py)), raio_px)

        if str(obj.get("tipo", "")).startswith("entidade"):
            nome_obj = obj.get("nome") or obj.get("usuario") or f"Player {obj.get('id', '')}"
            self._desenhar_nome_jogador(tela, (px, py), nome_obj)

    def _obter_sprite(self, caminho):
        if not caminho:
            return None
        if caminho in self._cache_sprites:
            return self._cache_sprites[caminho]
        if not os.path.exists(caminho):
            self._cache_sprites[caminho] = None
            return None
        try:
            sprite = pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            sprite = None
        self._cache_sprites[caminho] = sprite
        return sprite

    def _desenhar_nome_jogador(self, tela, pos_tela, nome):
        nome_str = str(nome or "Player")
        texto = self._cache_nome_texto.get(nome_str)
        if texto is None:
            texto = Texto(
                nome_str,
                pos=(0, 0),
                style={
                    "size": 16,
                    "align": "midbottom",
                    "outline": True,
                    "outline_thickness": 1,
                    "shadow": False,
                    "color": (250, 250, 255),
                },
            )
            self._cache_nome_texto[nome_str] = texto
        else:
            texto.set_text(nome_str)

        tempo = pygame.time.get_ticks() * 0.004
        fase = (abs(hash(nome_str)) % 360) * 0.0174533
        oscilacao = math.sin(tempo + fase) * 2.0
        texto.set_pos((int(pos_tela[0]), int(pos_tela[1]) - 43 + int(round(oscilacao))))
        texto.draw(tela)
