"""Gerador/renderer de estádios no cliente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pygame
from Codigo.Modulos.Colisor import Colisor

Vector2 = Tuple[float, float]


@dataclass
class Estadio:
    id_objeto: int
    tipo: str
    dimensao_destino: str
    posicao: Vector2
    estadio_id: int = 0
    chunk_tamanho_tiles: int = 10
    chunk_largura: int = 5
    chunk_altura: int = 5
    entrada_offset_tiles: Vector2 = (0.0, 0.0)

    def __post_init__(self) -> None:
        self.id_objeto = int(self.id_objeto)
        self.estadio_id = int(self.estadio_id or 0)
        self.tipo = str(self.tipo or "Normal")
        self.dimensao_destino = str(self.dimensao_destino or "EstadioNormal")
        self.posicao = (float(self.posicao[0]), float(self.posicao[1]))
        self.chunk_tamanho_tiles = max(1, int(self.chunk_tamanho_tiles or 10))
        self.chunk_largura = max(1, int(self.chunk_largura or 5))
        self.chunk_altura = max(1, int(self.chunk_altura or 5))
        self.entrada_offset_tiles = (float(self.entrada_offset_tiles[0]), float(self.entrada_offset_tiles[1]))
        self._cache_surface: Dict[Tuple[int, str], pygame.Surface] = {}
        self.Colisor = Colisor(
            x=self.posicao[0],
            y=self.posicao[1],
            raio_colisao=max(self.semi_eixo_x_tiles, self.semi_eixo_y_tiles),
            raio_interacao=max(self.semi_eixo_x_tiles, self.semi_eixo_y_tiles) + 1.0,
            tipo_colisao="elipse",
            semi_eixo_x=self.semi_eixo_x_tiles,
            semi_eixo_y=self.semi_eixo_y_tiles,
            campo_semi_eixo_x=self.semi_eixo_x_tiles,
            campo_semi_eixo_y=self.semi_eixo_y_tiles,
        )

    @property
    def semi_eixo_x_tiles(self) -> float:
        return max(2.0, (self.chunk_largura * self.chunk_tamanho_tiles) * 0.50)

    @property
    def semi_eixo_y_tiles(self) -> float:
        return max(2.0, (self.chunk_altura * self.chunk_tamanho_tiles) * 0.50)

    @property
    def entrada_posicao(self) -> Vector2:
        base = (self.posicao[0] + self.entrada_offset_tiles[0], self.posicao[1] + self.entrada_offset_tiles[1])
        if self.entrada_offset_tiles != (0.0, 0.0):
            return base
        return (self.posicao[0], self.posicao[1] + self.semi_eixo_y_tiles - 1.2)

    def ponto_na_elipse(self, ponto: Vector2, margem: float = 0.0) -> bool:
        return Colisor.ponto_em_elipse(
            ponto=(float(ponto[0]), float(ponto[1])),
            centro=self.posicao,
            semi_eixo_x=self.semi_eixo_x_tiles,
            semi_eixo_y=self.semi_eixo_y_tiles,
            margem=float(margem),
        )

    def pode_interagir_entrada(self, ponto: Vector2, raio: float = 1.8) -> bool:
        ex, ey = self.entrada_posicao
        dx = float(ponto[0]) - ex
        dy = float(ponto[1]) - ey
        return (dx * dx + dy * dy) <= float(raio * raio)

    def colide_externo(self, ponto: Vector2, raio: float = 0.45) -> bool:
        if not self.ponto_na_elipse(ponto, margem=float(raio)):
            return False
        if self.pode_interagir_entrada(ponto, raio=max(1.0, float(raio) + 0.95)):
            return False
        return True

    def _surface_mundo(self, tile_px: int) -> pygame.Surface:
        chave = (int(tile_px), str(self.tipo).lower())
        surf = self._cache_surface.get(chave)
        if surf is not None:
            return surf

        w = max(40, int(self.semi_eixo_x_tiles * 2.0 * tile_px))
        h = max(30, int(self.semi_eixo_y_tiles * 2.0 * tile_px))
        surf = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
        c = surf.get_rect().center

        outer = pygame.Rect(12, 12, w, h)
        pygame.draw.ellipse(surf, (0, 0, 0, 72), outer.move(0, 8))
        pygame.draw.ellipse(surf, (188, 194, 210), outer)
        pygame.draw.ellipse(surf, (64, 72, 88), outer, width=max(2, tile_px // 7))

        inner1 = outer.inflate(int(-w * 0.20), int(-h * 0.22))
        pygame.draw.ellipse(surf, (140, 144, 158), inner1)

        field = inner1.inflate(int(-w * 0.34), int(-h * 0.36))
        pygame.draw.ellipse(surf, (82, 150, 96), field)
        pygame.draw.ellipse(surf, (245, 245, 245), field, width=max(2, tile_px // 8))

        for i in range(3):
            rr = inner1.inflate(-i * max(8, tile_px // 3), -i * max(6, tile_px // 3))
            pygame.draw.ellipse(surf, (112, 118, 132), rr, width=1)

        pygame.draw.line(surf, (240, 240, 240), (field.left + 8, c[1]), (field.right - 8, c[1]), width=max(1, tile_px // 10))

        porta_w = max(14, int(w * 0.12))
        porta_h = max(10, int(h * 0.08))
        porta = pygame.Rect(0, 0, porta_w, porta_h)
        porta.midtop = (c[0], outer.bottom - porta_h // 3)
        pygame.draw.rect(surf, (232, 204, 96), porta, border_radius=max(2, tile_px // 8))

        self._cache_surface[chave] = surf
        return surf

    def renderizar_mundo(self, tela, camera) -> None:
        tile_px = max(16, int(getattr(camera, "TilePx", 50) or 50))
        surf = self._surface_mundo(tile_px)
        px, py = camera.mundo_para_tela_px(self.posicao)
        rect = surf.get_rect(center=(int(px), int(py)))
        tela.blit(surf, rect)
