"""Camera com suavização para acompanhar a entidade principal."""

from __future__ import annotations

from typing import Optional, Tuple

Vector2 = Tuple[float, float]


class Camera:
    """Segue a entidade Main com movimento amortecido."""

    def __init__(
        self,
        tamanho_tela: Vector2,
        entidade_main=None,
        posicao_inicial: Vector2 = (0.0, 0.0),
        suavizacao: float = 6.0,
    ) -> None:
        self.TamanhoTela = (float(tamanho_tela[0]), float(tamanho_tela[1]))
        self.Posicao = (float(posicao_inicial[0]), float(posicao_inicial[1]))
        self.EntidadeMain = entidade_main
        self.Suavizacao = max(0.1, float(suavizacao))

    def definir_main(self, entidade_main) -> None:
        self.EntidadeMain = entidade_main

    def atualizar(self, delta_time: float) -> Vector2:
        """Atualiza a câmera correndo atrás da entidade observada."""
        if self.EntidadeMain is None or not hasattr(self.EntidadeMain, "Posicao"):
            return self.Posicao

        alvo_x = float(self.EntidadeMain.Posicao[0]) - self.TamanhoTela[0] * 0.5
        alvo_y = float(self.EntidadeMain.Posicao[1]) - self.TamanhoTela[1] * 0.5

        fator = min(1.0, max(0.0, float(delta_time)) * self.Suavizacao)
        x = self.Posicao[0] + (alvo_x - self.Posicao[0]) * fator
        y = self.Posicao[1] + (alvo_y - self.Posicao[1]) * fator
        self.Posicao = (x, y)
        return self.Posicao

    def mundo_para_tela(self, posicao_mundo: Vector2) -> Vector2:
        return (
            float(posicao_mundo[0]) - self.Posicao[0],
            float(posicao_mundo[1]) - self.Posicao[1],
        )

    def MundoParaTela(self, posicao_mundo: Vector2) -> Vector2:
        """Alias para compatibilidade."""
        return self.mundo_para_tela(posicao_mundo)
