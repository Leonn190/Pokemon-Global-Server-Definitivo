"""Classe base de projétil, filha de Entidade."""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Tuple

from .Entidade import Entidade

Vector2 = Tuple[float, float]


class Projetil(Entidade):
    """Classe mãe para projéteis.

    Regras padrão:
    - colidiu com estrutura -> morre (desaparece);
    - colidiu com entidade -> comportamento variável via callback/política.
    """

    def __init__(
        self,
        posicao: Vector2 = (0.0, 0.0),
        velocidade: Vector2 = (0.0, 0.0),
        raio_colisao: float = 4.0,
        raio_interacao: Optional[float] = None,
        on_colidir_entidade: Optional[Callable[["Projetil", Entidade], None]] = None,
        politica_colisao_entidade: str = "ignorar",
    ) -> None:
        super().__init__(
            posicao=posicao,
            velocidade=velocidade,
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
        )
        self.Vivo = True
        self.OnColidirEntidade = on_colidir_entidade
        self.PoliticaColisaoEntidade = politica_colisao_entidade

    def morrer(self) -> None:
        self.Vivo = False
        self.Colisor.ativo = False

    def atualizar(self, delta_time: float, estruturas: Iterable = (), entidades: Iterable[Entidade] = ()) -> None:
        """Atualiza movimento e aplica regras de colisão do projétil."""
        if not self.Vivo:
            return

        self.mover(self.Velocidade[0] * delta_time, self.Velocidade[1] * delta_time)

        for estrutura in estruturas:
            if self.Colisor.testa_com(estrutura.Colisor)["colidiu"]:
                self.morrer()
                return

        for entidade in entidades:
            if entidade is self:
                continue

            if self.Colisor.testa_com(entidade.Colisor)["colidiu"]:
                if self.OnColidirEntidade is not None:
                    self.OnColidirEntidade(self, entidade)
                    if not self.Vivo:
                        return
                    continue

                if self.PoliticaColisaoEntidade == "morrer":
                    self.morrer()
                    return
                if self.PoliticaColisaoEntidade == "parar":
                    self.Velocidade = (0.0, 0.0)
                # "ignorar" não faz nada
