"""Prefabs para desenho de fluxos simples da batalha."""

from __future__ import annotations

import math

import pygame


class Fluxo:
    def __init__(self, estilo: str = "orb"):
        self.Estilo = str(estilo or "orb").strip().lower()
        self._tempo = 0.0

    def atualizar(self, dt: float) -> None:
        self._tempo += max(0.0, float(dt))

    @staticmethod
    def _limitar_alpha(alpha: int) -> int:
        return max(0, min(255, int(alpha)))

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
        animado: bool = True,
        estilo: str | None = None,
    ) -> None:
        estilo_fluxo = str(estilo or self.Estilo or "orb").strip().lower()
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

        min_x = int(min(x1, x2) - 48)
        min_y = int(min(y1, y2) - 48)
        max_x = int(max(x1, x2) + 48)
        max_y = int(max(y1, y2) + 48)

        camada = pygame.Surface((max(2, max_x - min_x), max(2, max_y - min_y)), pygame.SRCALPHA)

        def local(x, y):
            return int(x - min_x), int(y - min_y)

        trilha_alpha = self._limitar_alpha(alpha_trilha)
        pygame.draw.line(
            camada,
            (*cor_principal, max(16, trilha_alpha // 2)),
            local(x1, y1),
            local(x2, y2),
            max(1, int(largura_trilha + 4)),
        )
        pygame.draw.line(
            camada,
            (*cor_principal, trilha_alpha),
            local(x1, y1),
            local(x2, y2),
            max(1, int(largura_trilha)),
        )

        if not animado and estilo_fluxo == "linha":
            pygame.draw.line(
                camada,
                (*cor_secundaria, self._limitar_alpha(alpha)),
                local(x1, y1),
                local(x2, y2),
                max(1, int(max(2.0, raio_base))),
            )
            tela.blit(camada, (min_x, min_y))
            return

        deslocamento = ((self._tempo * vel) % passo) if animado else 0.0
        p = -deslocamento
        idx = 0

        while p <= dist + passo:
            t = max(0.0, min(1.0, p / dist if dist > 0 else 0.0))
            onda = math.sin(self._tempo * 5.0 + idx * 0.65) * 2.4 if animado else 0.0
            tx = x1 + ux * p + px * onda
            ty = y1 + uy * p + py * onda

            brilho = 0.55 + 0.45 * math.sin(self._tempo * 7.0 + idx * 0.45) if animado else 0.85
            brilho = max(0.15, brilho)
            raio = raio_base * (0.75 + 0.45 * brilho)

            fade_borda = math.sin(t * math.pi)
            fade_borda = max(0.18, fade_borda)
            alpha_atual = self._limitar_alpha(alpha * fade_borda * (0.65 + 0.35 * brilho))
            alpha_sec = self._limitar_alpha(alpha_atual * 0.55)

            if estilo_fluxo == "seta":
                ponta_x = tx + ux * raio * 2.3
                ponta_y = ty + uy * raio * 2.3
                base_x = tx - ux * raio * 0.6
                base_y = ty - uy * raio * 0.6
                esq = (base_x + px * raio * 1.15, base_y + py * raio * 1.15)
                dir_ = (base_x - px * raio * 1.15, base_y - py * raio * 1.15)
                pygame.draw.polygon(camada, (*cor_principal, alpha_atual), [local(ponta_x, ponta_y), local(*esq), local(*dir_)])
            elif estilo_fluxo == "linha":
                seg = min(dist, p + passo * 0.85)
                ex = x1 + ux * seg
                ey = y1 + uy * seg
                pygame.draw.line(
                    camada,
                    (*cor_principal, alpha_sec),
                    local(tx, ty),
                    local(ex, ey),
                    max(1, int(max(2.0, raio * 1.8))),
                )
                pygame.draw.line(
                    camada,
                    (*cor_secundaria, alpha_atual),
                    local(tx, ty),
                    local(ex, ey),
                    max(1, int(max(1.0, raio * 0.8))),
                )
            elif estilo_fluxo == "faixa":
                seg = min(dist, p + passo * 0.8)
                ex = x1 + ux * seg
                ey = y1 + uy * seg
                pygame.draw.line(
                    camada,
                    (*cor_principal, alpha_sec),
                    local(tx, ty),
                    local(ex, ey),
                    max(1, int(raio * 2.2)),
                )
                pygame.draw.line(
                    camada,
                    (*cor_secundaria, alpha_atual),
                    local(tx, ty),
                    local(ex, ey),
                    max(1, int(raio)),
                )
            else:
                pygame.draw.circle(camada, (*cor_principal, alpha_sec), local(tx, ty), max(1, int(raio * 1.9)))
                pygame.draw.circle(camada, (*cor_secundaria, alpha_atual), local(tx, ty), max(1, int(raio)))

            idx += 1
            p += passo

        tela.blit(camada, (min_x, min_y))
