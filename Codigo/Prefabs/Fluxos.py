"""Prefabs para desenho de fluxo animado entre dois pontos."""

from __future__ import annotations

import math
import pygame


class Fluxo:
    def __init__(self, estilo: str = "bolinhas"):
        self.Estilo = str(estilo or "bolinhas").strip().lower()
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += max(0.0, float(dt))

    def desenhar(
        self,
        tela,
        inicio,
        fim,
        *,
        velocidade: float = 220.0,
        espacamento: float = 16.0,
        tamanho: float = 4.0,
        cor_principal=(84, 180, 255),
        cor_secundaria=(220, 240, 255),
        alpha: int = 180,
        pulso: float = 0.25,
    ) -> None:
        x1, y1 = float(inicio[0]), float(inicio[1])
        x2, y2 = float(fim[0]), float(fim[1])
        dx, dy = (x2 - x1), (y2 - y1)
        dist = math.hypot(dx, dy)
        if dist <= 1.0:
            return

        ux, uy = dx / dist, dy / dist
        passo = max(6.0, float(espacamento))
        deslocamento = (self._tempo * max(0.0, float(velocidade))) % passo

        camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        idx = 0
        p = -deslocamento
        while p <= dist + passo:
            tx = x1 + ux * p
            ty = y1 + uy * p
            fase = self._tempo * 6.0 + idx * 0.35
            ganho = 1.0 + math.sin(fase) * max(0.0, min(1.0, float(pulso)))
            raio = max(1, int(float(tamanho) * ganho))
            cor = cor_principal if (idx % 2 == 0) else cor_secundaria

            if self.Estilo == "seta":
                ponta = (int(tx + ux * raio * 2.2), int(ty + uy * raio * 2.2))
                esq = (int(tx - uy * raio), int(ty + ux * raio))
                dir_ = (int(tx + uy * raio), int(ty - ux * raio))
                pygame.draw.polygon(camada, (*cor, alpha), (ponta, esq, dir_))
            elif self.Estilo == "faixa":
                prox = min(dist, p + passo * 0.9)
                ex = x1 + ux * prox
                ey = y1 + uy * prox
                pygame.draw.line(camada, (*cor, alpha), (tx, ty), (ex, ey), max(1, raio))
            else:
                pygame.draw.circle(camada, (*cor, alpha), (int(tx), int(ty)), raio)

            idx += 1
            p += passo

        tela.blit(camada, (0, 0))
