"""Módulo de colisão/interação genérico para entidades e estruturas."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


Vector2 = Tuple[float, float]
RectData = Tuple[float, float, float, float]


@dataclass
class Colisor:
    """Componente de colisão/interação com raios separados.

    - raio_colisao: contato físico.
    - raio_interacao: detecção/ação em área.
    """

    x: float
    y: float
    raio_colisao: float
    raio_interacao: Optional[float] = None
    ativo: bool = True

    def __post_init__(self) -> None:
        if self.raio_interacao is None:
            self.raio_interacao = self.raio_colisao
        self.raio_colisao = max(0.0, float(self.raio_colisao))
        self.raio_interacao = max(float(self.raio_colisao), float(self.raio_interacao))

    @property
    def centro(self) -> Vector2:
        return (self.x, self.y)

    def mover_para(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def deslocar(self, dx: float, dy: float) -> None:
        self.x += float(dx)
        self.y += float(dy)

    def distancia_para(self, outro: "Colisor") -> float:
        return math.hypot(self.x - outro.x, self.y - outro.y)

    def testa_com(self, outro: "Colisor") -> dict:
        """Retorna um dicionário com estado de colisão/interação."""
        if not self.ativo or not outro.ativo:
            return {
                "colidiu": False,
                "interagiu": False,
                "distancia": float("inf"),
                "profundidade_colisao": 0.0,
                "profundidade_interacao": 0.0,
                "direcao": (0.0, 0.0),
            }

        dx = outro.x - self.x
        dy = outro.y - self.y
        dist = math.hypot(dx, dy)
        direcao = (1.0, 0.0) if dist == 0 else (dx / dist, dy / dist)

        limite_colisao = self.raio_colisao + outro.raio_colisao
        limite_interacao = self.raio_interacao + outro.raio_interacao

        profundidade_colisao = max(0.0, limite_colisao - dist)
        profundidade_interacao = max(0.0, limite_interacao - dist)

        return {
            "colidiu": profundidade_colisao > 0,
            "interagiu": profundidade_interacao > 0,
            "distancia": dist,
            "profundidade_colisao": profundidade_colisao,
            "profundidade_interacao": profundidade_interacao,
            "direcao": direcao,
        }

    def resolver_empurrao(
        self,
        alvo: "Colisor",
        fator: float = 1.0,
        empurrar_ambos: bool = False,
    ) -> Vector2:
        """Resolve sobreposição física entre `self` e `alvo`."""
        info = self.testa_com(alvo)
        if not info["colidiu"]:
            return (0.0, 0.0)

        dx, dy = info["direcao"]
        correcao = info["profundidade_colisao"] * max(0.0, fator)

        if empurrar_ambos:
            meio = correcao * 0.5
            self.deslocar(-dx * meio, -dy * meio)
            alvo.deslocar(dx * meio, dy * meio)
            return (dx * meio, dy * meio)

        alvo.deslocar(dx * correcao, dy * correcao)
        return (dx * correcao, dy * correcao)

    def dentro_da_area(self, ponto: Vector2, usar_interacao: bool = True) -> bool:
        px, py = ponto
        raio = self.raio_interacao if usar_interacao else self.raio_colisao
        return math.hypot(px - self.x, py - self.y) <= raio

    @staticmethod
    def circle_rect_collide(center: Vector2, raio: float, rect: RectData) -> bool:
        """Teste círculo-retângulo sem dependência de pygame."""
        cx, cy = center
        rx, ry, rw, rh = rect

        closest_x = min(max(cx, rx), rx + rw)
        closest_y = min(max(cy, ry), ry + rh)

        dx = cx - closest_x
        dy = cy - closest_y
        return (dx * dx + dy * dy) <= (raio * raio)
