"""Projétil Fruta para frutificar Pokémon no mundo."""

from __future__ import annotations

from typing import Optional, Tuple

from Codigo.Modulos.Projetil import Projetil
from Codigo.Geradores.PokemonMundo import PokemonMundo

Vector2 = Tuple[float, float]


class Fruta(Projetil):
    """Projétil que frutifica um ``PokemonMundo`` ao colidir."""

    def __init__(
        self,
        posicao: Vector2 = (0.0, 0.0),
        velocidade: Vector2 = (0.0, 0.0),
        treinador_id: Optional[int] = None,
        raio_colisao: float = 5.0,
    ) -> None:
        super().__init__(
            posicao=posicao,
            velocidade=velocidade,
            raio_colisao=raio_colisao,
            politica_colisao_entidade="ignorar",
            on_colidir_entidade=self._ao_colidir_entidade,
        )
        self.TreinadorId = treinador_id

    def _ao_colidir_entidade(self, projetil: "Fruta", entidade) -> None:
        if isinstance(entidade, PokemonMundo):
            entidade.frutificar(frutificador_id=self.TreinadorId)
            self.morrer()
