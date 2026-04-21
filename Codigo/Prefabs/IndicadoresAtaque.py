from __future__ import annotations

import math
from typing import Iterable, Sequence

import pygame


def _ponto2(valor) -> tuple[float, float]:
    if isinstance(valor, (tuple, list)) and len(valor) >= 2:
        return float(valor[0]), float(valor[1])
    return 0.0, 0.0


def _vetor(origem, destino) -> tuple[float, float]:
    ox, oy = _ponto2(origem)
    dx, dy = _ponto2(destino)
    return dx - ox, dy - oy


def _normalizar(vx: float, vy: float) -> tuple[float, float]:
    tamanho = math.hypot(vx, vy)
    if tamanho <= 0.0001:
        return 1.0, 0.0
    return vx / tamanho, vy / tamanho


def _perp(vx: float, vy: float) -> tuple[float, float]:
    return -vy, vx


def _poly_corredor(origem, destino, largura_px: float) -> list[tuple[int, int]]:
    ox, oy = _ponto2(origem)
    dx, dy = _ponto2(destino)
    nx, ny = _normalizar(dx - ox, dy - oy)
    px, py = _perp(nx, ny)
    meia = max(1.0, float(largura_px) * 0.5)
    return [
        (int(ox + px * meia), int(oy + py * meia)),
        (int(ox - px * meia), int(oy - py * meia)),
        (int(dx - px * meia), int(dy - py * meia)),
        (int(dx + px * meia), int(dy + py * meia)),
    ]


def _desenhar_poligono_alpha(tela: pygame.Surface, pontos: Sequence[tuple[int, int]], cor, alpha: int) -> None:
    if len(pontos) < 3:
        return
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    largura = max(1, max_x - min_x + 2)
    altura = max(1, max_y - min_y + 2)
    overlay = pygame.Surface((largura, altura), pygame.SRCALPHA)
    locais = [(p[0] - min_x, p[1] - min_y) for p in pontos]
    pygame.draw.polygon(overlay, (*cor[:3], int(alpha)), locais)
    tela.blit(overlay, (min_x, min_y))


def desenhar_linha(tela, origem, destino, largura_px, cor, alpha=120):
    pontos = _poly_corredor(origem, destino, largura_px)
    _desenhar_poligono_alpha(tela, pontos, cor, alpha)


def desenhar_impulso(tela, origem, destino, largura_px, cor, alpha=130):
    desenhar_linha(tela, origem, destino, largura_px, cor, alpha)
    ox, oy = _ponto2(origem)
    dx, dy = _ponto2(destino)
    nx, ny = _normalizar(dx - ox, dy - oy)
    px, py = _perp(nx, ny)
    ponta = max(8.0, float(largura_px) * 1.6)
    base = max(5.0, float(largura_px) * 0.75)
    tri = [
        (int(dx + nx * ponta), int(dy + ny * ponta)),
        (int(dx + px * base), int(dy + py * base)),
        (int(dx - px * base), int(dy - py * base)),
    ]
    _desenhar_poligono_alpha(tela, tri, cor, min(255, alpha + 35))


def desenhar_dash(tela, origem, destino, largura_px, cor, alpha=140):
    desenhar_linha(tela, origem, destino, max(2, int(largura_px)), cor, alpha)


def desenhar_projetil(tela, origem, destino, raio_px, cor, alpha=120):
    largura = max(2.0, float(raio_px) * 2.0)
    desenhar_linha(tela, origem, destino, largura, cor, alpha)
    dx, dy = _ponto2(destino)
    pygame.draw.circle(tela, cor[:3], (int(dx), int(dy)), max(2, int(raio_px)), width=1)


def desenhar_projetil_explosivo(tela, origem, destino, raio_px, raio_explosao_px, cor, alpha=120):
    desenhar_projetil(tela, origem, destino, raio_px, cor, alpha)
    desenhar_area_circular(tela, destino, raio_explosao_px, cor, alpha=max(70, alpha - 20))


def desenhar_laser(tela, origem, destino, largura_px, cor, alpha=150):
    desenhar_linha(tela, origem, destino, largura_px, cor, alpha)


def desenhar_cone(tela, origem, destino, alcance_px, angulo_graus, cor, alpha=100):
    ox, oy = _ponto2(origem)
    vx, vy = _vetor(origem, destino)
    nx, ny = _normalizar(vx, vy)
    abertura = math.radians(max(1.0, float(angulo_graus)))
    semi = abertura * 0.5
    alc = max(4.0, float(alcance_px))
    pontos = [(int(ox), int(oy))]
    segmentos = 18
    base = math.atan2(ny, nx)
    for i in range(segmentos + 1):
        t = i / max(1, segmentos)
        ang = base - semi + (abertura * t)
        pontos.append((int(ox + math.cos(ang) * alc), int(oy + math.sin(ang) * alc)))
    _desenhar_poligono_alpha(tela, pontos, cor, alpha)


def desenhar_cone_invertido(tela, origem, destino, alcance_px, largura_base_px, largura_topo_px, cor, alpha=100):
    ox, oy = _ponto2(origem)
    vx, vy = _vetor(origem, destino)
    nx, ny = _normalizar(vx, vy)
    px, py = _perp(nx, ny)
    alc = max(4.0, float(alcance_px))
    ponta_x, ponta_y = ox + nx * alc, oy + ny * alc
    b = max(2.0, float(largura_base_px) * 0.5)
    t = max(1.0, float(largura_topo_px) * 0.5)
    pontos = [
        (int(ox + px * b), int(oy + py * b)),
        (int(ox - px * b), int(oy - py * b)),
        (int(ponta_x - px * t), int(ponta_y - py * t)),
        (int(ponta_x + px * t), int(ponta_y + py * t)),
    ]
    _desenhar_poligono_alpha(tela, pontos, cor, alpha)


def desenhar_area_circular(tela, centro, raio_px, cor, alpha=100):
    cx, cy = _ponto2(centro)
    raio = max(2, int(raio_px))
    overlay = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (*cor[:3], int(alpha)), (raio + 1, raio + 1), raio)
    tela.blit(overlay, (int(cx - raio - 1), int(cy - raio - 1)))


def desenhar_alvo(tela, origem, alvo, cor, alpha=150):
    desenhar_linha(tela, origem, alvo, 3, cor, alpha)
    ax, ay = _ponto2(alvo)
    pygame.draw.circle(tela, cor[:3], (int(ax), int(ay)), 12, width=2)


def desenhar_aro(tela, centro, raio_px, cor, alpha=120):
    cx, cy = _ponto2(centro)
    raio = max(6, int(raio_px))
    overlay = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (*cor[:3], int(alpha)), (raio + 2, raio + 2), raio, width=3)
    tela.blit(overlay, (int(cx - raio - 2), int(cy - raio - 2)))
