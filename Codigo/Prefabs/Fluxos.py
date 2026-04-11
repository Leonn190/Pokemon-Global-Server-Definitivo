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

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

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

        passo = max(12.0, float(espacamento))
        raio_base = max(1.0, float(tamanho))

        # velocidades mais controladas por estilo
        if estilo_fluxo == "seta":
            vel = max(0.0, float(velocidade) * 0.38)
        elif estilo_fluxo in ("linha", "faixa"):
            vel = max(0.0, float(velocidade) * 0.55)
        else:
            vel = max(0.0, float(velocidade) * 0.75)

        margem = int(max(48, tamanho * 8))
        min_x = int(min(x1, x2) - margem)
        min_y = int(min(y1, y2) - margem)
        max_x = int(max(x1, x2) + margem)
        max_y = int(max(y1, y2) + margem)

        camada = pygame.Surface(
            (max(2, max_x - min_x), max(2, max_y - min_y)),
            pygame.SRCALPHA,
        )

        def local(x, y):
            return int(round(x - min_x)), int(round(y - min_y))

        trilha_alpha = self._limitar_alpha(alpha_trilha)
        alpha_base = self._limitar_alpha(alpha)

        # fundo/trilha base
        largura_fundo = max(1, int(largura_trilha + 4))
        largura_miolo = max(1, int(largura_trilha))

        pygame.draw.line(
            camada,
            (*cor_principal, max(12, trilha_alpha // 2)),
            local(x1, y1),
            local(x2, y2),
            largura_fundo,
        )
        pygame.draw.line(
            camada,
            (*cor_principal, trilha_alpha),
            local(x1, y1),
            local(x2, y2),
            largura_miolo,
        )

        if not animado:
            if estilo_fluxo in ("linha", "faixa"):
                pygame.draw.line(
                    camada,
                    (*cor_secundaria, alpha_base),
                    local(x1, y1),
                    local(x2, y2),
                    max(1, int(max(2.0, raio_base))),
                )
            else:
                pygame.draw.line(
                    camada,
                    (*cor_secundaria, alpha_base),
                    local(x1, y1),
                    local(x2, y2),
                    max(1, int(max(1.0, largura_trilha))),
                )
            tela.blit(camada, (min_x, min_y))
            return

        # agora o deslocamento anda PARA FRENTE
        deslocamento = (self._tempo * vel) % passo

        # -------------------------
        # ORB: bolinhas fixas
        # -------------------------
        if estilo_fluxo == "orb":
            p = deslocamento - passo
            while p <= dist + passo:
                t = max(0.0, min(1.0, p / dist))
                if 0.0 <= t <= 1.0:
                    fade = math.sin(t * math.pi)
                    fade = max(0.22, fade)

                    tx = x1 + ux * p
                    ty = y1 + uy * p

                    a1 = self._limitar_alpha(alpha_base * fade * 0.45)
                    a2 = self._limitar_alpha(alpha_base * fade)

                    # sem variar tamanho
                    r_outer = max(1, int(raio_base * 1.9))
                    r_inner = max(1, int(raio_base))

                    pygame.draw.circle(camada, (*cor_principal, a1), local(tx, ty), r_outer)
                    pygame.draw.circle(camada, (*cor_secundaria, a2), local(tx, ty), r_inner)

                p += passo

            tela.blit(camada, (min_x, min_y))
            return

        # -------------------------
        # SETA: fundo contínuo + chevrons
        # -------------------------
        if estilo_fluxo == "seta":
            # reforça uma faixa bonita por baixo
            pygame.draw.line(
                camada,
                (*cor_principal, max(trilha_alpha, 36)),
                local(x1, y1),
                local(x2, y2),
                max(1, int(largura_trilha + raio_base * 1.2)),
            )
            pygame.draw.line(
                camada,
                (*cor_secundaria, max(24, trilha_alpha // 2)),
                local(x1, y1),
                local(x2, y2),
                max(1, int(largura_trilha)),
            )

            p = deslocamento - passo * 1.5
            passo_seta = passo * 1.25
            comprimento = max(10.0, raio_base * 3.4)
            abertura = max(4.0, raio_base * 1.5)

            while p <= dist + passo_seta:
                t = max(0.0, min(1.0, p / dist))
                if 0.0 <= t <= 1.0:
                    fade = math.sin(t * math.pi)
                    fade = max(0.12, fade)

                    cx = x1 + ux * p
                    cy = y1 + uy * p

                    a = self._limitar_alpha(alpha_base * fade)

                    # chevron tipo “aceleração”, não triângulo sólido
                    ponta = (cx + ux * comprimento, cy + uy * comprimento)
                    meio = (cx, cy)
                    cima = (cx - ux * comprimento * 0.35 + px * abertura, cy - uy * comprimento * 0.35 + py * abertura)
                    baixo = (cx - ux * comprimento * 0.35 - px * abertura, cy - uy * comprimento * 0.35 - py * abertura)

                    espessura1 = max(1, int(raio_base * 0.95))
                    espessura2 = max(1, int(raio_base * 0.55))

                    pygame.draw.line(camada, (*cor_principal, int(a * 0.55)), local(*cima), local(*meio), espessura1)
                    pygame.draw.line(camada, (*cor_principal, int(a * 0.55)), local(*baixo), local(*meio), espessura1)

                    pygame.draw.line(camada, (*cor_secundaria, a), local(*cima), local(*ponta), espessura2)
                    pygame.draw.line(camada, (*cor_secundaria, a), local(*baixo), local(*ponta), espessura2)

                p += passo_seta

            tela.blit(camada, (min_x, min_y))
            return

        # -------------------------
        # LINHA / FAIXA: fluxo contínuo liso
        # -------------------------
        largura_fluxo_externo = max(1, int(max(largura_trilha + 3, raio_base * 2.2)))
        largura_fluxo_interno = max(1, int(max(largura_trilha, raio_base * 1.1)))

        # desenha o corpo inteiro do fluxo
        pygame.draw.line(
            camada,
            (*cor_principal, max(alpha_base // 3, 40)),
            local(x1, y1),
            local(x2, y2),
            largura_fluxo_externo,
        )
        pygame.draw.line(
            camada,
            (*cor_secundaria, max(alpha_base // 2, 70)),
            local(x1, y1),
            local(x2, y2),
            largura_fluxo_interno,
        )

        # brilho correndo por cima, contínuo
        comprimento_brilho = max(passo * 1.8, 24.0)
        p = deslocamento - comprimento_brilho

        while p <= dist + comprimento_brilho:
            t0 = max(0.0, min(1.0, p / dist))
            t1 = max(0.0, min(1.0, (p + comprimento_brilho) / dist))

            if t1 > 0.0 and t0 < 1.0:
                sx = self._lerp(x1, x2, t0)
                sy = self._lerp(y1, y2, t0)
                ex = self._lerp(x1, x2, t1)
                ey = self._lerp(y1, y2, t1)

                centro = (t0 + t1) * 0.5
                fade = math.sin(centro * math.pi)
                fade = max(0.18, fade)

                a_outer = self._limitar_alpha(alpha_base * 0.38 * fade)
                a_inner = self._limitar_alpha(alpha_base * 0.95 * fade)

                pygame.draw.line(
                    camada,
                    (*cor_principal, a_outer),
                    local(sx, sy),
                    local(ex, ey),
                    max(1, int(largura_fluxo_externo)),
                )
                pygame.draw.line(
                    camada,
                    (*cor_secundaria, a_inner),
                    local(sx, sy),
                    local(ex, ey),
                    max(1, int(largura_fluxo_interno)),
                )

            p += passo * 0.55

        tela.blit(camada, (min_x, min_y))
