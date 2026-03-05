"""Controlador de objetos do mundo (entidades + estruturas)."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
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
        posicao_antes = tuple(self.PlayerLocal.Ator.Posicao)
        self.PlayerLocal.Controle.atualizar(eventos, dt, mouse_pos_mundo_tiles)
        self._resolver_colisao_player_local(posicao_antes, dt)
        self._sincronizar_player_local()

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

    @staticmethod
    def _intersecao_segmento_circulo(
        origem: Tuple[float, float],
        destino: Tuple[float, float],
        centro: Tuple[float, float],
        raio: float,
    ) -> Optional[float]:
        ox, oy = origem
        dx = destino[0] - ox
        dy = destino[1] - oy
        fx = ox - centro[0]
        fy = oy - centro[1]

        a = dx * dx + dy * dy
        if a <= 1e-10:
            return None

        b = 2.0 * (fx * dx + fy * dy)
        c = (fx * fx + fy * fy) - (raio * raio)
        delta = b * b - 4.0 * a * c
        if delta < 0.0:
            return None

        raiz = math.sqrt(delta)
        inv = 1.0 / (2.0 * a)
        t1 = (-b - raiz) * inv
        t2 = (-b + raiz) * inv

        candidatos = [t for t in (t1, t2) if 0.0 <= t <= 1.0]
        if not candidatos:
            return None
        return min(candidatos)

    def _resolver_colisao_player_local(self, posicao_antes: Tuple[float, float], dt: float) -> None:
        if self.PlayerLocal is None or getattr(self.PlayerLocal, "Ator", None) is None:
            return
        ator = self.PlayerLocal.Ator
        posicao_depois = tuple(ator.Posicao)
        player_id = getattr(ator, "Id", None)
        raio_ator = max(0.0, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))

        if raio_ator <= 0.0:
            return

        melhor_t = None
        colisores_proximos = [c for c in self._iter_colisores_proximos(posicao_depois) if c[0] != player_id]

        for _, sx, sy, raio_obj, _, _, _ in colisores_proximos:
            t = self._intersecao_segmento_circulo(posicao_antes, posicao_depois, (sx, sy), raio_ator + raio_obj)
            if t is None:
                continue
            if melhor_t is None or t < melhor_t:
                melhor_t = t

        if melhor_t is not None:
            dx = posicao_depois[0] - posicao_antes[0]
            dy = posicao_depois[1] - posicao_antes[1]
            t_seguro = max(0.0, melhor_t - 0.02)
            ator.definir_posicao(posicao_antes[0] + dx * t_seguro, posicao_antes[1] + dy * t_seguro)

        px, py = ator.Posicao
        for _ in range(3):
            ajustou = False
            for _, sx, sy, raio_obj, _, _, _ in colisores_proximos:
                vx = px - sx
                vy = py - sy
                dist = math.hypot(vx, vy)
                limite = raio_ator + raio_obj
                if dist >= limite or limite <= 0.0:
                    continue

                if dist <= 1e-8:
                    vx, vy, dist = 1.0, 0.0, 1.0

                nx = vx / dist
                ny = vy / dist
                sobreposicao = limite - dist
                px += nx * (sobreposicao + 1e-4)
                py += ny * (sobreposicao + 1e-4)
                ajustou = True

            if not ajustou:
                break

        dt = max(0.0, float(dt))
        if dt > 0.0:
            for _, sx, sy, raio_obj, tipo_obj, campo, intensidade in colisores_proximos:
                if not tipo_obj.startswith("estrutura"):
                    continue
                if campo <= 0.0 or intensidade <= 0.0:
                    continue

                vx = px - sx
                vy = py - sy
                dist = math.hypot(vx, vy)
                limite = raio_ator + raio_obj + campo
                if limite <= 0.0 or dist >= limite:
                    continue

                if dist <= 1e-8:
                    vx, vy, dist = 1.0, 0.0, 1.0

                dirx = vx / dist
                diry = vy / dist
                t = max(0.0, min(1.0, 1.0 - (dist / max(limite, 1e-6))))
                push = intensidade * t * dt
                px += dirx * push
                py += diry * push

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
