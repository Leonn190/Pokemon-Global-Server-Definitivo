"""Camera para mundo em tiles com conversão para pixels."""

from __future__ import annotations

from typing import Optional, Tuple

import pygame

Vector2 = Tuple[float, float]


class Camera:
    TILE_PX_PADRAO = 40

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
        self.LimitesToroidais = True

    def definir_limites_mundo(self, largura_tiles: float, altura_tiles: float, toroidal: bool = True) -> None:
        try:
            largura = max(1.0, float(largura_tiles))
            altura = max(1.0, float(altura_tiles))
        except (TypeError, ValueError):
            self.LimitesMundoTiles = None
            return
        self.LimitesMundoTiles = (largura, altura)
        self.LimitesToroidais = bool(toroidal)

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
        if self.LimitesMundoTiles and self.LimitesToroidais:
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
            if self.LimitesMundoTiles and not self.LimitesToroidais:
                largura, altura = self.LimitesMundoTiles
                tela_w_tiles = float(self.TamanhoTelaPx[0]) / max(1.0, float(self.TilePx))
                tela_h_tiles = float(self.TamanhoTelaPx[1]) / max(1.0, float(self.TilePx))
                max_x = max(0.0, float(largura) - tela_w_tiles)
                max_y = max(0.0, float(altura) - tela_h_tiles)
                x = max(0.0, min(max_x, x))
                y = max(0.0, min(max_y, y))
        self.PosicaoTiles = (x, y)
        return self.PosicaoTiles

    def mundo_para_tela_px(self, posicao_mundo_tiles: Vector2) -> Vector2:
        dx = float(posicao_mundo_tiles[0]) - self.PosicaoTiles[0]
        dy = float(posicao_mundo_tiles[1]) - self.PosicaoTiles[1]
        if self.LimitesMundoTiles and self.LimitesToroidais:
            largura, altura = self.LimitesMundoTiles
            dx = self._delta_toroidal(0.0, dx, largura)
            dy = self._delta_toroidal(0.0, dy, altura)
        return (dx * self.TilePx, dy * self.TilePx)

    def tela_para_mundo_tiles(self, posicao_tela_px: Vector2) -> Vector2:
        wx = self.PosicaoTiles[0] + (float(posicao_tela_px[0]) / self.TilePx)
        wy = self.PosicaoTiles[1] + (float(posicao_tela_px[1]) / self.TilePx)
        if self.LimitesMundoTiles and self.LimitesToroidais:
            largura, altura = self.LimitesMundoTiles
            wx %= largura
            wy %= altura
        return (wx, wy)


class CameraBatalha(Camera):
    TILE_MIN = 25
    TILE_MAX = 55

    def __init__(self, tamanho_tela_px: Vector2, posicao_inicial_tiles: Vector2 = (0.0, 0.0), tile_px: int = 40) -> None:
        super().__init__(tamanho_tela_px=tamanho_tela_px, entidade_main=None, posicao_inicial_tiles=posicao_inicial_tiles, suavizacao=100.0, tile_px=tile_px)
        self._arrastando = False
        self._ultimo_mouse_px: Optional[Vector2] = None

    def processar_eventos(self, eventos) -> None:
        for evento in eventos:
            if getattr(evento, "type", None) == pygame.MOUSEBUTTONDOWN and getattr(evento, "button", 0) == 3:  # MOUSEBUTTONDOWN
                self._arrastando = True
                self._ultimo_mouse_px = tuple(getattr(evento, "pos", (0, 0)))
            elif getattr(evento, "type", None) == pygame.MOUSEBUTTONUP and getattr(evento, "button", 0) == 3:  # MOUSEBUTTONUP
                self._arrastando = False
                self._ultimo_mouse_px = None
            elif getattr(evento, "type", None) == pygame.MOUSEMOTION and self._arrastando:  # MOUSEMOTION
                pos = tuple(getattr(evento, "pos", (0, 0)))
                if self._ultimo_mouse_px is not None:
                    dx_px = float(pos[0]) - float(self._ultimo_mouse_px[0])
                    dy_px = float(pos[1]) - float(self._ultimo_mouse_px[1])
                    self.PosicaoTiles = (
                        float(self.PosicaoTiles[0]) - (dx_px / max(1, self.TilePx)),
                        float(self.PosicaoTiles[1]) - (dy_px / max(1, self.TilePx)),
                    )
                    self._aplicar_limites()
                self._ultimo_mouse_px = pos
            elif getattr(evento, "type", None) == pygame.MOUSEBUTTONDOWN and getattr(evento, "button", 0) in (4, 5):  # wheel legacy
                self._alterar_zoom(+1 if evento.button == 4 else -1)
            elif getattr(evento, "type", None) == pygame.MOUSEWHEEL:  # MOUSEWHEEL
                self._alterar_zoom(int(getattr(evento, "y", 0)))

    def _alterar_zoom(self, passos: int) -> None:
        if passos == 0:
            return
        antigo = int(self.TilePx)
        novo = max(self.TILE_MIN, min(self.TILE_MAX, int(self.TilePx + passos)))
        if novo == antigo:
            return
        centro_x = float(self.PosicaoTiles[0]) + (float(self.TamanhoTelaPx[0]) / max(1.0, float(antigo))) * 0.5
        centro_y = float(self.PosicaoTiles[1]) + (float(self.TamanhoTelaPx[1]) / max(1.0, float(antigo))) * 0.5
        self.TilePx = int(novo)
        self.PosicaoTiles = (
            centro_x - (float(self.TamanhoTelaPx[0]) / max(1.0, float(self.TilePx))) * 0.5,
            centro_y - (float(self.TamanhoTelaPx[1]) / max(1.0, float(self.TilePx))) * 0.5,
        )
        self._aplicar_limites()

    def _aplicar_limites(self) -> None:
        if not self.LimitesMundoTiles:
            return
        largura, altura = self.LimitesMundoTiles
        tela_w_tiles = float(self.TamanhoTelaPx[0]) / max(1.0, float(self.TilePx))
        tela_h_tiles = float(self.TamanhoTelaPx[1]) / max(1.0, float(self.TilePx))
        max_x = max(0.0, float(largura) - tela_w_tiles)
        max_y = max(0.0, float(altura) - tela_h_tiles)
        self.PosicaoTiles = (
            max(0.0, min(max_x, float(self.PosicaoTiles[0]))),
            max(0.0, min(max_y, float(self.PosicaoTiles[1]))),
        )

    def atualizar(self, delta_time: float) -> Vector2:
        self._aplicar_limites()
        return self.PosicaoTiles

    def mundo_para_tela_px(self, posicao_mundo_tiles: Vector2) -> Vector2:
        dx = float(posicao_mundo_tiles[0]) - self.PosicaoTiles[0]
        dy = float(posicao_mundo_tiles[1]) - self.PosicaoTiles[1]
        return (dx * self.TilePx, dy * self.TilePx)

    def tela_para_mundo_tiles(self, posicao_tela_px: Vector2) -> Vector2:
        wx = self.PosicaoTiles[0] + (float(posicao_tela_px[0]) / self.TilePx)
        wy = self.PosicaoTiles[1] + (float(posicao_tela_px[1]) / self.TilePx)
        return (wx, wy)
