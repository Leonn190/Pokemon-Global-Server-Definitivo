from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pygame

try:
    import moderngl
except ImportError:  # pragma: no cover
    moderngl = None


@dataclass
class _EntradaTextura:
    textura: object
    size: Tuple[int, int]
    filtro: str


class CacheTexturasGL:
    def __init__(self, ctx):
        self._ctx = ctx
        self._entradas: Dict[str, _EntradaTextura] = {}
        self.uploads_frame = 0

    def iniciar_frame(self) -> None:
        self.uploads_frame = 0

    def _aplicar_filtro(self, textura, filtro: str) -> None:
        modo = str(filtro or "smooth").strip().lower()
        if modo == "fast":
            textura.filter = (moderngl.NEAREST, moderngl.NEAREST)
            return
        textura.filter = (moderngl.LINEAR, moderngl.LINEAR)

    def _criar_textura(self, size: Tuple[int, int], filtro: str = "smooth"):
        tex = self._ctx.texture(size, 4)
        self._aplicar_filtro(tex, filtro)
        tex.repeat_x = False
        tex.repeat_y = False
        return tex

    @staticmethod
    def _surface_bytes(surface: pygame.Surface) -> bytes:
        return pygame.image.tobytes(surface, "RGBA", False)

    def obter_textura(self, chave: str, surface: pygame.Surface, dirty: bool = False, filtro: str = "smooth"):
        tamanho = tuple(surface.get_size())
        filtro = str(filtro or "smooth").strip().lower()
        entrada = self._entradas.get(chave)

        if entrada is None:
            textura = self._criar_textura(tamanho, filtro=filtro)
            textura.write(self._surface_bytes(surface))
            self._entradas[chave] = _EntradaTextura(textura=textura, size=tamanho, filtro=filtro)
            self.uploads_frame += 1
            return textura

        if entrada.size != tamanho:
            try:
                entrada.textura.release()
            except Exception:
                pass
            textura = self._criar_textura(tamanho, filtro=filtro)
            textura.write(self._surface_bytes(surface))
            self._entradas[chave] = _EntradaTextura(textura=textura, size=tamanho, filtro=filtro)
            self.uploads_frame += 1
            return textura

        if entrada.filtro != filtro:
            self._aplicar_filtro(entrada.textura, filtro)
            entrada.filtro = filtro

        if dirty:
            entrada.textura.write(self._surface_bytes(surface))
            self.uploads_frame += 1

        return entrada.textura

    def liberar(self) -> None:
        for entrada in self._entradas.values():
            try:
                entrada.textura.release()
            except Exception:
                pass
        self._entradas.clear()
