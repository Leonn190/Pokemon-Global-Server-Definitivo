"""Ator básico do mundo, derivado de Entidade."""

from __future__ import annotations

from typing import Optional, Tuple

from Codigo.Modulos.DesenhaAtor import DesenhaAtor
from Codigo.Modulos.Entidade import Entidade

Vector2 = Tuple[float, float]


class Ator(Entidade):
    """Entidade básica com skin de player e desenho via ``DesenhaAtor``."""

    def __init__(
        self,
        skin_surface,
        posicao: Vector2 = (0.0, 0.0),
        velocidade: Vector2 = (0.0, 0.0),
        raio_colisao: float = 12.0,
        raio_interacao: Optional[float] = None,
        escala_skin: float = 1.45,
    ) -> None:
        super().__init__(
            posicao=posicao,
            velocidade=velocidade,
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
        )
        self.Skin = skin_surface
        self.Desenhador = DesenhaAtor(self.Skin, escala=escala_skin)

    def set_skin(self, skin_surface) -> None:
        self.Skin = skin_surface
        self.Desenhador.set_skin(skin_surface)

    def desenhar(self, tela, mouse_pos) -> None:
        self.Desenhador.desenhar(tela, self.Posicao, mouse_pos)
