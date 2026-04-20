from __future__ import annotations

from pathlib import Path
import pygame

_CURSOR_BASE: pygame.Surface | None = None
_CURSOR_ENCONTRADO = False


def _carregar_cursor() -> pygame.Surface | None:
    global _CURSOR_BASE, _CURSOR_ENCONTRADO
    if _CURSOR_ENCONTRADO:
        return _CURSOR_BASE
    _CURSOR_ENCONTRADO = True
    arq = Path("Recursos/Visual/Icones/Diversos/Ponteiro.png")
    if arq.exists():
        try:
            _CURSOR_BASE = pygame.image.load(str(arq)).convert_alpha()
            return _CURSOR_BASE
        except Exception:
            return None
    return None


def desenhar_seta_player(surface: pygame.Surface, centro: tuple[int, int], angulo: float, tamanho: int) -> None:
    t = max(3, min(16, int(round(float(tamanho) * 0.4))))
    cx, cy = int(centro[0]), int(centro[1])
    cursor = _carregar_cursor()
    if cursor is None:
        return
    escala = max(0.1, float(t) / max(1.0, float(max(cursor.get_width(), cursor.get_height()))))
    # Ajuste de orientação para acompanhar corretamente o angulo de olhar.
    rot = 90.0 + float(angulo)
    sprite = pygame.transform.rotozoom(cursor, rot, escala)
    rect = sprite.get_rect(center=(cx, cy))
    surface.blit(sprite, rect)
