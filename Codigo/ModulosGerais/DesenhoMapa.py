from __future__ import annotations

import math
from pathlib import Path
import pygame

_CURSOR_BASE: pygame.Surface | None = None
_CURSOR_ENCONTRADO = False


def _carregar_cursor() -> pygame.Surface | None:
    global _CURSOR_BASE, _CURSOR_ENCONTRADO
    if _CURSOR_ENCONTRADO:
        return _CURSOR_BASE
    _CURSOR_ENCONTRADO = True
    base = Path("Recursos/Visual/Icones/Diversos")
    nomes = ["PonteiroMapa.png", "Ponteiro.png", "CursorMapa.png", "SetaMapa.png", "PlayerMapa.png"]
    for nome in nomes:
        arq = base / nome
        if arq.exists():
            try:
                _CURSOR_BASE = pygame.image.load(str(arq)).convert_alpha()
                return _CURSOR_BASE
            except Exception:
                continue
    return None


def desenhar_seta_player(surface: pygame.Surface, centro: tuple[int, int], angulo: float, tamanho: int) -> None:
    t = max(6, min(24, int(tamanho)))
    cx, cy = int(centro[0]), int(centro[1])
    cursor = _carregar_cursor()
    if cursor is not None:
        escala = max(0.1, float(t) / max(1.0, float(max(cursor.get_width(), cursor.get_height()))))
        # imagem base aponta para cima; angulo jogo 0 aponta para direita.
        rot = 90.0 - float(angulo)
        sprite = pygame.transform.rotozoom(cursor, rot, escala)
        rect = sprite.get_rect(center=(cx, cy))
        surface.blit(sprite, rect)
        return
    ponta = (cx + int(math.cos(math.radians(angulo)) * t), cy - int(math.sin(math.radians(angulo)) * t))
    esq = (cx + int(math.cos(math.radians(angulo + 145)) * (t * 0.65)), cy - int(math.sin(math.radians(angulo + 145)) * (t * 0.65)))
    dire = (cx + int(math.cos(math.radians(angulo - 145)) * (t * 0.65)), cy - int(math.sin(math.radians(angulo - 145)) * (t * 0.65)))
    pygame.draw.polygon(surface, (240, 240, 255), [ponta, esq, dire])
