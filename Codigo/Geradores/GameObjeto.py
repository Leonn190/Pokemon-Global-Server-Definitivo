"""Classe mãe com funcionalidades comuns entre Entidade e Estrutura."""

from __future__ import annotations

import math
import os
from typing import Dict, Optional, Tuple

import pygame

from Codigo.Modulos.Colisor import Colisor
from Codigo.Modulos.ConfigEstruturasNaturais import tipo_estrutura_natural_por_codigo

Vector2 = Tuple[float, float]


class GameObjeto:
    """Base de objetos do jogo com id, posição, colisor, nome e visual."""

    _next_id = 1
    _cache_sprites: Dict[str, Optional[pygame.Surface]] = {}

    def __init__(
        self,
        posicao: Vector2 = (0.0, 0.0),
        raio_colisao: float = 12.0,
        raio_interacao: Optional[float] = None,
        campo: float = 0.0,
        intensidade: float = 0.0,
        hitbox=None,
        id_objeto: Optional[int] = None,
        nome: Optional[str] = None,
        sprite: Optional[str] = None,
    ) -> None:
        if id_objeto is None:
            id_objeto = GameObjeto._next_id
            GameObjeto._next_id += 1

        self.Id = int(id_objeto)
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Colisor = Colisor(
            x=self.Posicao[0],
            y=self.Posicao[1],
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
        )

        self.Campo = float(campo)
        self.Intensidade = float(intensidade)
        self.HitBox = hitbox
        self.Nome = None if nome is None else str(nome)
        self.Sprite = None if sprite is None else str(sprite)

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    @classmethod
    def _obter_sprite(cls, caminho):
        caminho = str(caminho or "").strip()
        if not caminho:
            return None
        if caminho in cls._cache_sprites:
            return cls._cache_sprites[caminho]
        if not os.path.exists(caminho):
            cls._cache_sprites[caminho] = None
            return None
        try:
            sprite = pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            sprite = None
        cls._cache_sprites[caminho] = sprite
        return sprite

    @classmethod
    def desenhar_snapshot(cls, tela, camera, obj: Dict[str, object], cor_fallback=(222, 233, 245)):
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

        sprite = cls._obter_sprite(sprite_path)
        if sprite is not None:
            sprite_rect = sprite.get_rect(center=(int(px), int(py)))
            tela.blit(sprite, sprite_rect)
        else:
            raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
            raio_px = int(raio_raw if raio_raw > 4.0 else raio_raw * camera.TilePx)
            raio_px = max(3, min(80, raio_px))
            pygame.draw.circle(tela, cor_fallback, (int(px), int(py)), raio_px)


    @staticmethod
    def _rect_props(rect) -> Tuple[float, float, float, float, float, float]:
        if hasattr(rect, "left"):
            left = float(rect.left)
            top = float(rect.top)
            right = float(rect.right)
            bottom = float(rect.bottom)
            center = rect.center
            return left, top, right, bottom, float(center[0]), float(center[1])

        x, y, w, h = rect
        left = float(x)
        top = float(y)
        right = left + float(w)
        bottom = top + float(h)
        return left, top, right, bottom, left + float(w) * 0.5, top + float(h) * 0.5

    @staticmethod
    def _rect_collide(rect_a, rect_b) -> bool:
        if hasattr(rect_a, "colliderect"):
            return rect_a.colliderect(rect_b)

        ax, ay, aw, ah = rect_a
        bx, by, bw, bh = rect_b
        return not (ax + aw < bx or bx + bw < ax or ay + ah < by or by + bh < ay)

    def _circle_rect_collide(self, center, raio, rect) -> bool:
        rect_data = (float(rect.x), float(rect.y), float(rect.width), float(rect.height)) if hasattr(rect, "x") else rect
        return Colisor.circle_rect_collide(center, raio, rect_data)

    def aplicar_campo_forca(self, player_rect_tela, move_tiles_vec, tile_px, delta_time):
        """Ajusta (dx,dy) em TILES/frame com base no CAMPO."""
        if not self.HitBox or self.Campo <= 0:
            return move_tiles_vec

        dx_tiles, dy_tiles = move_tiles_vec
        mvx_px = dx_tiles * tile_px
        mvy_px = dy_tiles * tile_px

        tipo = self.HitBox[0]

        def _rect_core_push(core_rect):
            if hasattr(core_rect, "inflate"):
                zona = core_rect.inflate(self.Campo * 2, self.Campo * 2)
            else:
                x, y, w, h = core_rect
                zona = (x - self.Campo, y - self.Campo, w + self.Campo * 2, h + self.Campo * 2)

            if not self._rect_collide(zona, player_rect_tela):
                return None

            pcx, pcy = player_rect_tela.center
            left, top, right, bottom, cx, cy = self._rect_props(core_rect)
            nx = min(max(pcx, left), right)
            ny = min(max(pcy, top), bottom)
            vx = pcx - nx
            vy = pcy - ny
            dist = math.hypot(vx, vy)
            if dist == 0:
                vx = (pcx - cx) or 1.0
                vy = (pcy - cy) or 0.0
                dist = math.hypot(vx, vy)

            dirx = vx / dist
            diry = vy / dist
            t = max(0.0, min(1.0, 1.0 - (dist / max(self.Campo, 1))))
            return (dirx, diry, t)

        if tipo == "rect":
            core = self.HitBox[1]
            out = _rect_core_push(core)
            if out is not None:
                dirx, diry, t = out
                towardx, towardy = -dirx, -diry
                comp_toward = mvx_px * towardx + mvy_px * towardy
                if comp_toward > 0:
                    atenuacao = 0.7 * t
                    mvx_px -= towardx * (comp_toward * atenuacao)
                    mvy_px -= towardy * (comp_toward * atenuacao)

                push_tiles = self.Intensidade * t * delta_time
                mvx_px += dirx * (push_tiles * tile_px)
                mvy_px += diry * (push_tiles * tile_px)
        else:
            center, raio = self.HitBox[1], self.HitBox[2]
            cx, cy = center
            raio_zona = raio + self.Campo
            if not self._circle_rect_collide((cx, cy), raio_zona, player_rect_tela):
                return (mvx_px / tile_px, mvy_px / tile_px)

            pcx, pcy = player_rect_tela.center
            vx = pcx - cx
            vy = pcy - cy
            dist = math.hypot(vx, vy)
            if dist == 0:
                vx, vy, dist = 1.0, 0.0, 1.0

            dirx = vx / dist
            diry = vy / dist
            limite = float(raio_zona)
            t = max(0.0, min(1.0, 1.0 - (dist / limite)))

            towardx, towardy = -dirx, -diry
            comp_toward = mvx_px * towardx + mvy_px * towardy
            if comp_toward > 0:
                atenuacao = 0.7 * t
                mvx_px -= towardx * (comp_toward * atenuacao)
                mvy_px -= towardy * (comp_toward * atenuacao)

            push_tiles = self.Intensidade * t * delta_time
            mvx_px += dirx * (push_tiles * tile_px)
            mvy_px += diry * (push_tiles * tile_px)

        return (mvx_px / tile_px, mvy_px / tile_px)
