import pygame
from pathlib import Path

_CAMINHO_FONTE_CINEMATICA = Path("Recursos/Visual/Fontes/FonteCinematica.ttf")


class TextoCinematico:
    def __init__(self, texto: str, tamanho: int = 92, cor=(240, 240, 240)):
        self._texto = str(texto or "")
        self._tamanho = max(12, int(tamanho))
        self._cor = tuple(cor)
        self._alpha = 0
        self._fonte = pygame.font.Font(str(_CAMINHO_FONTE_CINEMATICA), self._tamanho)

    def set_texto(self, texto: str) -> None:
        self._texto = str(texto or "")

    def set_alpha(self, alpha: float) -> None:
        self._alpha = max(0, min(255, int(alpha)))

    def desenhar(self, surface: pygame.Surface, centro: tuple[int, int]) -> None:
        base = self._fonte.render(self._texto, True, self._cor).convert_alpha()
        sombra = self._fonte.render(self._texto, True, (0, 0, 0)).convert_alpha()
        borda = self._fonte.render(self._texto, True, (0, 0, 0)).convert_alpha()
        placa = pygame.Surface((base.get_width() + 12, base.get_height() + 12), pygame.SRCALPHA)
        cx, cy = 6, 6
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            placa.blit(borda, (cx + dx, cy + dy))
        placa.blit(sombra, (cx + 3, cy + 3))
        placa.blit(base, (cx, cy))
        placa.set_alpha(self._alpha)
        rect = placa.get_rect(center=centro)
        surface.blit(placa, rect.topleft)
