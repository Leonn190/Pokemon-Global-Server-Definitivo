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

    @property
    def tempo(self) -> float:
        return float(self._tempo)

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
        fase_tempo: float | None = None,
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
        tempo_ref = float(self._tempo if fase_tempo is None else fase_tempo)
        deslocamento = ((tempo_ref * vel) % passo) if animado else 0.0
        p = -deslocamento
        idx = 0

        while p <= dist + passo:
            t = max(0.0, min(1.0, p / dist if dist > 0 else 0.0))

            # leve ondulação lateral
            onda = math.sin(tempo_ref * 5.0 + idx * 0.65) * 2.6
            tx = x1 + ux * p + px * onda
            ty = y1 + uy * p + py * onda

            # cabeça mais brilhante, cauda mais suave
            brilho = 0.55 + 0.45 * math.sin(tempo_ref * 7.0 + idx * 0.45)
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
    def desenhar(self, tela, inicio, angulo: float, tile_px: int, alcance_tiles: float, grossura_tiles: float, diametro_tiles: float, alpha: int = 82):
        alcance_px = max(1.0, float(alcance_tiles) * max(1, int(tile_px)))
        grossura_px = max(2, int(max(0.2, float(grossura_tiles)) * max(1, int(tile_px))))
        ponta = (inicio[0] + math.cos(angulo) * alcance_px, inicio[1] + math.sin(angulo) * alcance_px)
        camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        pygame.draw.line(camada, (190, 195, 205, alpha), inicio, ponta, grossura_px)
        if float(diametro_tiles) > 0.0:
            raio = max(2, int((float(diametro_tiles) * max(1, int(tile_px))) * 0.5))
            pygame.draw.circle(camada, (200, 205, 215, int(alpha * 0.86)), (int(ponta[0]), int(ponta[1])), raio)
        tela.blit(camada, (0, 0))


class FluxoArea:
    def desenhar(self, tela, centro, angulo: float, raio_pokemon_px: float, tile_px: int, base_pct: float, altura_pct: float, teto_pct: float, alpha: int = 96):
        raio = max(1.0, float(raio_pokemon_px))
        base_pct = max(0.01, float(base_pct))
        altura_pct = max(0.01, float(altura_pct))
        teto_pct = max(0.0, float(teto_pct))
        circ = 2.0 * math.pi * raio
        comprimento_base = circ * base_pct
        largura_arco = max(0.04, min(math.tau, comprimento_base / raio))
        passos = max(6, int(10 + 14 * base_pct))
        arco = []
        for i in range(passos + 1):
            k = i / max(1, passos)
            a = angulo - (largura_arco * 0.5) + largura_arco * k
            arco.append((centro[0] + math.cos(a) * raio, centro[1] + math.sin(a) * raio))

        altura = max(12.0, circ * altura_pct)
        comprimento_teto = circ * (base_pct if teto_pct <= 0.001 else teto_pct)
        topo_largura = max(2.0, comprimento_teto * 0.5)
        ux, uy = math.cos(angulo), math.sin(angulo)
        px, py = -uy, ux
        topo_centro = (centro[0] + ux * altura, centro[1] + uy * altura)
        topo_a = (topo_centro[0] - px * topo_largura, topo_centro[1] - py * topo_largura)
        topo_b = (topo_centro[0] + px * topo_largura, topo_centro[1] + py * topo_largura)

        poligono = [*arco, topo_b, topo_a]
        camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(camada, (255, 255, 255, int(alpha * 0.42)), poligono)
        pygame.draw.polygon(camada, (255, 255, 255, alpha), poligono, 2)
        pygame.draw.arc(
            camada,
            (255, 255, 255, int(alpha * 0.8)),
            pygame.Rect(centro[0] - raio, centro[1] - raio, raio * 2, raio * 2),
            angulo - (largura_arco * 0.5),
            angulo + (largura_arco * 0.5),
            2,
        )
        tela.blit(camada, (0, 0))
