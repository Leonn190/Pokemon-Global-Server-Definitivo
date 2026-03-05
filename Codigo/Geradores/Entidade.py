"""Classe base para entidades do jogo."""

from __future__ import annotations

from typing import Optional, Tuple

from .GameObjeto import GameObjeto

Vector2 = Tuple[float, float]


class Entidade(GameObjeto):
    """Classe mãe de entidades móveis."""

    def __init__(
        self,
        posicao: Vector2 = (0.0, 0.0),
        velocidade: Vector2 = (0.0, 0.0),
        raio_colisao: float = 12.0,
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
        self.Velocidade = (float(velocidade[0]), float(velocidade[1]))

    def mover(self, dx: float, dy: float) -> None:
        """Move a entidade e sincroniza posição do colisor."""
        px, py = self.Posicao
        self.definir_posicao(px + float(dx), py + float(dy))

    def Mover(self, dx: float, dy: float) -> None:
        """Alias para compatibilidade."""
        self.mover(dx, dy)

    def mover_com_forca(self, move_tiles_vec, tile_px, delta_time, estruturas=()):
        """Aplica campo de força de estruturas e resolve colisão física."""
        dx, dy = move_tiles_vec

        if self.HitBox:
            for estrutura in estruturas:
                dx, dy = estrutura.aplicar_campo_forca(
                    player_rect_tela=self.HitBox[1],
                    move_tiles_vec=(dx, dy),
                    tile_px=tile_px,
                    delta_time=delta_time,
                )

        self.mover(dx * tile_px, dy * tile_px)

        for estrutura in estruturas:
            estrutura.Colisor.resolver_empurrao(self.Colisor, fator=1.0, empurrar_ambos=False)
            self.Posicao = self.Colisor.centro

        return (dx, dy)
