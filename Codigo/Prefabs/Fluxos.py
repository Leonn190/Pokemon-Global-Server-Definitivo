"""Prefabs para desenho de fluxo animado entre dois pontos."""

from __future__ import annotations

import math
import pygame


class Fluxo:
    def __init__(self, estilo: str = "orb"):
        self.Estilo = str(estilo or "orb").strip().lower()
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += max(0.0, float(dt))

    def desenhar(
        self,
        tela,
        inicio,
        fim,
        *,
        velocidade: float = 180.0,
        espacamento: float = 22.0,
        tamanho: float = 5.0,
        cor_principal=(90, 190, 255),
        cor_secundaria=(220, 245, 255),
        alpha: int = 170,
        largura_trilha: int = 3,
        alpha_trilha: int = 60,
    ) -> None:
        x1, y1 = float(inicio[0]), float(inicio[1])
        x2, y2 = float(fim[0]), float(fim[1])

        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist <= 2.0:
            return

        ux = dx / dist
        uy = dy / dist
        px = -uy
        py = ux

        passo = max(10.0, float(espacamento))
        vel = max(0.0, float(velocidade))
        raio_base = max(1.0, float(tamanho))

        min_x = int(min(x1, x2) - 40)
        min_y = int(min(y1, y2) - 40)
        max_x = int(max(x1, x2) + 40)
        max_y = int(max(y1, y2) + 40)

        w = max(2, max_x - min_x)
        h = max(2, max_y - min_y)

        camada = pygame.Surface((w, h), pygame.SRCALPHA)

        def local(x, y):
            return (int(x - min_x), int(y - min_y))

        # trilha de fundo
        pygame.draw.line(
            camada,
            (*cor_principal, max(20, int(alpha_trilha * 0.45))),
            local(x1, y1),
            local(x2, y2),
            max(1, int(largura_trilha + 4)),
        )
        pygame.draw.line(
            camada,
            (*cor_principal, alpha_trilha),
            local(x1, y1),
            local(x2, y2),
            max(1, int(largura_trilha)),
        )

        # fluxo principal
        deslocamento = (self._tempo * vel) % passo
        p = -deslocamento
        idx = 0

        while p <= dist + passo:
            t = max(0.0, min(1.0, p / dist if dist > 0 else 0.0))

            # leve ondulação lateral
            onda = math.sin(self._tempo * 5.0 + idx * 0.65) * 2.6
            tx = x1 + ux * p + px * onda
            ty = y1 + uy * p + py * onda

            # cabeça mais brilhante, cauda mais suave
            brilho = 0.55 + 0.45 * math.sin(self._tempo * 7.0 + idx * 0.45)
            brilho = max(0.15, brilho)

            raio = raio_base * (0.75 + 0.45 * brilho)

            # fade pelas pontas
            fade_borda = math.sin(t * math.pi)
            fade_borda = max(0.18, fade_borda)

            a = int(alpha * fade_borda * (0.65 + 0.35 * brilho))
            a2 = min(255, int(a * 0.55))

            if self.Estilo == "seta":
                ponta_x = tx + ux * raio * 2.2
                ponta_y = ty + uy * raio * 2.2
                base_x = tx - ux * raio * 0.6
                base_y = ty - uy * raio * 0.6

                esq = (base_x + px * raio * 1.15, base_y + py * raio * 1.15)
                dir_ = (base_x - px * raio * 1.15, base_y - py * raio * 1.15)

                pygame.draw.polygon(
                    camada,
                    (*cor_principal, a),
                    [local(ponta_x, ponta_y), local(*esq), local(*dir_)],
                )
            elif self.Estilo == "faixa":
                seg = min(dist, p + passo * 0.8)
                ex = x1 + ux * seg
                ey = y1 + uy * seg

                pygame.draw.line(
                    camada,
                    (*cor_principal, a2),
                    local(tx, ty),
                    local(ex, ey),
                    max(1, int(raio * 2.2)),
                )
                pygame.draw.line(
                    camada,
                    (*cor_secundaria, a),
                    local(tx, ty),
                    local(ex, ey),
                    max(1, int(raio)),
                )
            else:
                # glow externo
                pygame.draw.circle(
                    camada,
                    (*cor_principal, a2),
                    local(tx, ty),
                    max(1, int(raio * 1.9)),
                )
                # núcleo
                pygame.draw.circle(
                    camada,
                    (*cor_secundaria, a),
                    local(tx, ty),
                    max(1, int(raio)),
                )

            idx += 1
            p += passo

        tela.blit(camada, (min_x, min_y))
