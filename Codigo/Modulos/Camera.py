"""Camera para mundo em tiles com conversão para pixels."""

from __future__ import annotations

from typing import Optional, Tuple

Vector2 = Tuple[float, float]


class Camera:
    TILE_PX_PADRAO = 50

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
        self.LimitesMundoTiles: Optional[Vector2] = None

    def definir_limites_mundo(self, largura_tiles: float, altura_tiles: float) -> None:
        try:
            largura = max(1.0, float(largura_tiles))
            altura = max(1.0, float(altura_tiles))
        except (TypeError, ValueError):
            self.LimitesMundoTiles = None
            return
        self.LimitesMundoTiles = (largura, altura)

    @staticmethod
    def _delta_toroidal(origem: float, destino: float, tamanho: float) -> float:
        delta = float(destino) - float(origem)
        if tamanho <= 0:
            return delta
        return delta - round(delta / tamanho) * tamanho

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
        if self.LimitesMundoTiles:
            largura, altura = self.LimitesMundoTiles
            alvo_x %= largura
            alvo_y %= altura
            delta_x = self._delta_toroidal(self.PosicaoTiles[0], alvo_x, largura)
            delta_y = self._delta_toroidal(self.PosicaoTiles[1], alvo_y, altura)
            x = (self.PosicaoTiles[0] + delta_x * fator) % largura
            y = (self.PosicaoTiles[1] + delta_y * fator) % altura
        else:
            x = self.PosicaoTiles[0] + (alvo_x - self.PosicaoTiles[0]) * fator
            y = self.PosicaoTiles[1] + (alvo_y - self.PosicaoTiles[1]) * fator
        self.PosicaoTiles = (x, y)
        return self.PosicaoTiles

    def mundo_para_tela_px(self, posicao_mundo_tiles: Vector2) -> Vector2:
        dx = float(posicao_mundo_tiles[0]) - self.PosicaoTiles[0]
        dy = float(posicao_mundo_tiles[1]) - self.PosicaoTiles[1]
        if self.LimitesMundoTiles:
            largura, altura = self.LimitesMundoTiles
            dx = self._delta_toroidal(0.0, dx, largura)
            dy = self._delta_toroidal(0.0, dy, altura)
        return (dx * self.TilePx, dy * self.TilePx)

    def tela_para_mundo_tiles(self, posicao_tela_px: Vector2) -> Vector2:
        wx = self.PosicaoTiles[0] + (float(posicao_tela_px[0]) / self.TilePx)
        wy = self.PosicaoTiles[1] + (float(posicao_tela_px[1]) / self.TilePx)
        if self.LimitesMundoTiles:
            largura, altura = self.LimitesMundoTiles
            wx %= largura
            wy %= altura
        return (wx, wy)
