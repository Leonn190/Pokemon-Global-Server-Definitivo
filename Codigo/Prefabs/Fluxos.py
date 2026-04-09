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


class FluxoTiro:
    def desenhar(self, tela, inicio, angulo_rad: float, alcance_px: float, grossura_px: float, diametro_px: float = 0.0, *, alpha: int = 110):
        alcance = max(4.0, float(alcance_px))
        grossura = max(3.0, float(grossura_px))
        fim = (inicio[0] + math.cos(angulo_rad) * alcance, inicio[1] + math.sin(angulo_rad) * alcance)
        area = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        dx = fim[0] - inicio[0]
        dy = fim[1] - inicio[1]
        dist = max(1.0, math.hypot(dx, dy))
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux
        a = (inicio[0] + px * grossura * 0.5, inicio[1] + py * grossura * 0.5)
        b = (inicio[0] - px * grossura * 0.5, inicio[1] - py * grossura * 0.5)
        c = (fim[0] - px * grossura * 0.5, fim[1] - py * grossura * 0.5)
        d = (fim[0] + px * grossura * 0.5, fim[1] + py * grossura * 0.5)
        pygame.draw.polygon(area, (230, 233, 238, max(36, alpha)), [a, b, c, d])
        pygame.draw.polygon(area, (200, 206, 216, min(255, alpha + 45)), [a, b, c, d], 2)
        diam = max(0.0, float(diametro_px))
        if diam > 0.5:
            pygame.draw.circle(area, (224, 230, 240, max(28, alpha - 10)), (int(fim[0]), int(fim[1])), int(diam * 0.5))
            pygame.draw.circle(area, (210, 216, 228, min(255, alpha + 45)), (int(fim[0]), int(fim[1])), int(diam * 0.5), 2)
        tela.blit(area, (0, 0))


class FluxoArea:
    def desenhar(self, tela, inicio, raio_px: float, angulo_rad: float, base_pct: float, altura_pct: float, teto_pct: float | None = None, *, alpha: int = 95):
        raio = max(2.0, float(raio_px))
        circ = 2.0 * math.pi * raio
        base_ang = (max(0.0, float(base_pct)) / 100.0) * (circ / raio)
        altura = (max(0.0, float(altura_pct)) / 100.0) * circ
        teto_ang = None if teto_pct is None else (max(0.0, float(teto_pct)) / 100.0) * (circ / raio)

        base_ang = max(math.radians(4.0), min(math.tau, base_ang))
        topo_raio = raio + max(6.0, altura)
        if teto_ang is None or teto_ang <= 0.0:
            teto_ang = base_ang
        teto_ang = max(math.radians(2.0), min(math.tau, teto_ang))

        base_n = max(8, int(base_ang * raio / 4.0))
        topo_n = max(8, int(teto_ang * topo_raio / 5.5))
        pts = []
        for i in range(base_n + 1):
            t = i / max(1, base_n)
            a = angulo_rad - base_ang * 0.5 + base_ang * t
            pts.append((inicio[0] + math.cos(a) * raio, inicio[1] + math.sin(a) * raio))
        for i in range(topo_n, -1, -1):
            t = i / max(1, topo_n)
            a = angulo_rad - teto_ang * 0.5 + teto_ang * t
            pts.append((inicio[0] + math.cos(a) * topo_raio, inicio[1] + math.sin(a) * topo_raio))

        area = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(area, (255, 255, 255, alpha), pts)
        pygame.draw.polygon(area, (245, 250, 255, min(255, alpha + 65)), pts, 2)
        tela.blit(area, (0, 0))
