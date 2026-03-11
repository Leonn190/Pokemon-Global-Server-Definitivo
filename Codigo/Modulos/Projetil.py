"""Projétil concreto simples com Colisor."""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Tuple

from Codigo.Modulos.Colisor import Colisor

Vector2 = Tuple[float, float]


class Projetil:
    def __init__(self, posicao: Vector2 = (0.0, 0.0), velocidade: Vector2 = (0.0, 0.0), raio_colisao: float = 4.0, raio_interacao: Optional[float] = None, on_colidir_entidade: Optional[Callable] = None, politica_colisao_entidade: str = "ignorar") -> None:
        self.Id = 0
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Velocidade = (float(velocidade[0]), float(velocidade[1]))
        self.Colisor = Colisor(x=self.Posicao[0], y=self.Posicao[1], raio_colisao=raio_colisao, raio_interacao=raio_interacao)
        self.Vivo = True
        self.OnColidirEntidade = on_colidir_entidade
        self.PoliticaColisaoEntidade = politica_colisao_entidade

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def mover(self, dx: float, dy: float) -> None:
        self.definir_posicao(self.Posicao[0] + float(dx), self.Posicao[1] + float(dy))

    def morrer(self) -> None:
        self.Vivo = False
        self.Colisor.ativo = False

    def atualizar(self, delta_time: float, estruturas: Iterable = (), entidades: Iterable = ()) -> None:
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
