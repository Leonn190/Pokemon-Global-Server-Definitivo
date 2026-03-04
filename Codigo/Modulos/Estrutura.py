"""Classe base para estruturas do jogo."""

from __future__ import annotations

from typing import Optional, Tuple

from .GameObjeto import GameObjeto

Vector2 = Tuple[float, float]


class Estrutura(GameObjeto):
    """Classe mãe de estruturas com colisão e campo de força."""

    def __init__(
        self,
        posicao: Vector2 = (0.0, 0.0),
        raio_colisao: float = 16.0,
        raio_interacao: Optional[float] = None,
        campo: float = 0.0,
        intensidade: float = 0.0,
        hitbox=None,
        id_objeto: Optional[int] = None,
    ) -> None:
        super().__init__(
            posicao=posicao,
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
            campo=campo,
            intensidade=intensidade,
            hitbox=hitbox,
            id_objeto=id_objeto,
        )
