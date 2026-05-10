from __future__ import annotations

import math
from collections import OrderedDict
from pathlib import Path
from typing import Tuple

import pygame


class LogoMenu:

    def __init__(
        self,
        path: str | Path,
        center: Tuple[int, int] = (0, 0),
        size: Tuple[int, int] | None = None,
        cache_limit: int = 32,
        pulse_scale: float = 0.010,
        float_pixels: float = 4.0,
    ) -> None:
        self.path = Path(path)
        self.center = (int(center[0]), int(center[1]))
        self.base_image = pygame.image.load(str(self.path)).convert_alpha()
        self.base_size = tuple(size or self.base_image.get_size())
        self.cache_limit = max(2, int(cache_limit))
        self.pulse_scale = float(pulse_scale)
        self.float_pixels = float(float_pixels)

        self._cache: OrderedDict[Tuple[int, int], pygame.Surface] = OrderedDict()
        self._last_rect = pygame.Rect(0, 0, 0, 0)

    def set_layout(self, center: Tuple[int, int], size: Tuple[int, int]) -> None:
        self.center = (int(center[0]), int(center[1]))
        self.base_size = (max(1, int(size[0])), max(1, int(size[1])))

    def _surface_for_size(self, size: Tuple[int, int]) -> pygame.Surface:
        size = (max(1, int(size[0])), max(1, int(size[1])))
        cached = self._cache.get(size)
        if cached is not None:
            self._cache.move_to_end(size)
            return cached

        if size == self.base_image.get_size():
            surf = self.base_image
        else:
            surf = pygame.transform.smoothscale(self.base_image, size)

        self._cache[size] = surf
        self._cache.move_to_end(size)
        while len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)
        return surf

    def _animated_layout(self, t: float) -> tuple[Tuple[int, int], Tuple[int, int]]:
        pulse = 1.0 + self.pulse_scale * math.sin(t * 1.55)
        w = max(1, int(round(self.base_size[0] * pulse)))
        h = max(1, int(round(self.base_size[1] * pulse)))
        y_float = int(round(math.sin(t * 1.20) * self.float_pixels))
        center = (self.center[0], self.center[1] + y_float)
        return center, (w, h)

    def render(self, surface: pygame.Surface, t: float) -> pygame.Rect:
        center, size = self._animated_layout(float(t))
        logo = self._surface_for_size(size)
        rect = logo.get_rect(center=center)
        surface.blit(logo, rect)
        self._last_rect = rect.copy()
        return self._last_rect

    @property
    def layout_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, int(self.base_size[0]), int(self.base_size[1])).copy().move(
            int(self.center[0] - self.base_size[0] * 0.5),
            int(self.center[1] - self.base_size[1] * 0.5),
        )

    @property
    def last_rect(self) -> pygame.Rect:
        return self._last_rect.copy()
