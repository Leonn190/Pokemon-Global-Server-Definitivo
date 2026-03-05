import pygame
import math


def clamp(x, a, b):
    return a if x < a else b if x > b else x


class Imagem:
    """
    Imagem com APENAS:
      - Efeito interno (ondas/shimmer) recortado pelo alpha da própria imagem
    """

    def __init__(
        self,
        path: str,
        center=(0, 0),
        size=None,
        scale: float = 1.0,
        effect_alpha: int = 160,
    ):
        self.path = path
        self.center = center

        self.effect_alpha = int(clamp(effect_alpha, 0, 255))

        # paleta do efeito (igual seu código inicial)
        self.cA = (70, 170, 255)
        self.cB = (255, 70, 140)
        self.cC = (140, 100, 255)

        self.image = pygame.image.load(path).convert_alpha()

        if size is not None:
            self.image = pygame.transform.smoothscale(self.image, size)
        elif scale != 1.0:
            w, h = self.image.get_size()
            self.image = pygame.transform.smoothscale(self.image, (int(w * scale), int(h * scale)))

        self.rect = self.image.get_rect(center=self.center)

        # máscara alpha da imagem (pra recortar o efeito interno)
        self.mask = self.image.copy()

        # cache do efeito pra não recalcular 100% todo frame
        self._fx_cache = None
        self._fx_cache_tkey = None

    def set_center(self, center):
        self.center = center
        self.rect.center = center

    def render(self, surface: pygame.Surface, t: float):
        # imagem base
        surface.blit(self.image, self.rect)

        # efeito interno
        if self.effect_alpha > 0:
            fx = self._get_fx_layer(t)
            fx.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            fx.set_alpha(self.effect_alpha)
            surface.blit(fx, self.rect.topleft)

    def _get_fx_layer(self, t: float):
        tkey = int(t * 60)  # ~60fps
        if self._fx_cache is not None and self._fx_cache_tkey == tkey:
            return self._fx_cache.copy()

        fx = self._make_logo_effect(self.image.get_size(), t)
        self._fx_cache = fx
        self._fx_cache_tkey = tkey
        return fx.copy()

    def _make_logo_effect(self, size, t: float):
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        speed = 0.9
        ay = 2 * math.pi / 220.0
        cA, cB, cC = self.cA, self.cB, self.cC

        # gradiente animado por linhas
        for y in range(h):
            u = 0.5 + 0.25 * math.sin(y * ay + t * speed) + 0.25 * math.sin(y * 0.02 - t * (speed * 1.2))
            u = clamp(u, 0.0, 1.0)

            r = int(cA[0] * (1 - u) + cB[0] * u)
            g = int(cA[1] * (1 - u) + cB[1] * u)
            b = int(cA[2] * (1 - u) + cB[2] * u)

            # shimmer sutil
            sh = 0.5 + 0.5 * math.sin(t * 2.4 + y * 0.06)
            r = min(255, int(r * (0.92 + 0.16 * sh)))
            g = min(255, int(g * (0.92 + 0.16 * sh)))
            b = min(255, int(b * (0.92 + 0.16 * sh)))

            # toque roxo
            mix = 0.18 * (0.5 + 0.5 * math.sin(t * 0.7 + y * 0.01))
            r = int(r * (1 - mix) + cC[0] * mix)
            g = int(g * (1 - mix) + cC[1] * mix)
            b = int(b * (1 - mix) + cC[2] * mix)

            pygame.draw.line(surf, (r, g, b, 255), (0, y), (w, y))

        # warp horizontal tipo onda
        warped = pygame.Surface((w, h), pygame.SRCALPHA)
        amp = 9
        for y in range(h):
            dx = int(math.sin(y * 0.04 + t * 2.0) * amp + math.sin(y * 0.013 - t * 1.6) * (amp * 0.55))
            warped.blit(surf, (dx, y), pygame.Rect(0, y, w, 1))

        return warped