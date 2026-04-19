from __future__ import annotations

import math
import pygame


def desenhar_seta_player(surface: pygame.Surface, centro: tuple[int, int], angulo: float, tamanho: int) -> None:
    t = max(6, min(24, int(tamanho)))
    cx, cy = int(centro[0]), int(centro[1])
    ponta = (cx + int(math.cos(math.radians(angulo)) * t), cy - int(math.sin(math.radians(angulo)) * t))
    esq = (cx + int(math.cos(math.radians(angulo + 145)) * (t * 0.65)), cy - int(math.sin(math.radians(angulo + 145)) * (t * 0.65)))
    dire = (cx + int(math.cos(math.radians(angulo - 145)) * (t * 0.65)), cy - int(math.sin(math.radians(angulo - 145)) * (t * 0.65)))
    pontos = [ponta, esq, dire]
    pygame.draw.polygon(surface, (20, 20, 24), pontos, 3)
    pygame.draw.polygon(surface, (242, 246, 255), pontos)
    pygame.draw.circle(surface, (20, 20, 24), (cx, cy), max(2, t // 5) + 2)
    pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(2, t // 5))
