"""Camera para mundo em tiles com conversão para pixels."""

from __future__ import annotations

from typing import Optional, Tuple

Vector2 = Tuple[float, float]


class Camera:
    TILE_PX_PADRAO = 48

    def __init__(
        self,
        tamanho_tela_px: Vector2,
        entidade_main=None,
        posicao_inicial_tiles: Vector2 = (0.0, 0.0),
        suavizacao: float = 6.0,
        tile_px: int = TILE_PX_PADRAO,
    ) -> None:
        self.TamanhoTelaPx = (float(tamanho_tela_px[0]), float(tamanho_tela_px[1]))
        self.PosicaoTiles = (float(posicao_inicial_tiles[0]), float(posicao_inicial_tiles[1]))
        self.EntidadeMain = entidade_main
        self.Suavizacao = max(0.1, float(suavizacao))
        self.TilePx = int(tile_px)

    def definir_main(self, entidade_main) -> None:
        self.EntidadeMain = entidade_main

    def atualizar(self, delta_time: float) -> Vector2:
        if self.EntidadeMain is None or not hasattr(self.EntidadeMain, "Posicao"):
            return self.PosicaoTiles

        half_w_tiles = (self.TamanhoTelaPx[0] * 0.5) / self.TilePx
        half_h_tiles = (self.TamanhoTelaPx[1] * 0.5) / self.TilePx
        alvo_x = float(self.EntidadeMain.Posicao[0]) - half_w_tiles
        alvo_y = float(self.EntidadeMain.Posicao[1]) - half_h_tiles

        fator = min(1.0, max(0.0, float(delta_time)) * self.Suavizacao)
        x = self.PosicaoTiles[0] + (alvo_x - self.PosicaoTiles[0]) * fator
        y = self.PosicaoTiles[1] + (alvo_y - self.PosicaoTiles[1]) * fator
        self.PosicaoTiles = (x, y)
        return self.PosicaoTiles

    def mundo_para_tela_px(self, posicao_mundo_tiles: Vector2) -> Vector2:
        return (
            (float(posicao_mundo_tiles[0]) - self.PosicaoTiles[0]) * self.TilePx,
            (float(posicao_mundo_tiles[1]) - self.PosicaoTiles[1]) * self.TilePx,
        )

    def tela_para_mundo_tiles(self, posicao_tela_px: Vector2) -> Vector2:
        return (
            self.PosicaoTiles[0] + (float(posicao_tela_px[0]) / self.TilePx),
            self.PosicaoTiles[1] + (float(posicao_tela_px[1]) / self.TilePx),
        )
