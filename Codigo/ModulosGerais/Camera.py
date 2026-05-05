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
        self._normalizar_posicao_limites()

    def _normalizar_posicao_limites(self) -> None:
        if not self.LimitesMundoTiles:
            return
        largura, altura = self.LimitesMundoTiles
        x, y = float(self.PosicaoTiles[0]), float(self.PosicaoTiles[1])
        if self.LimitesToroidais:
            self.PosicaoTiles = (x % largura, y % altura)
            return
        tela_w_tiles = float(self.TamanhoTelaPx[0]) / max(1.0, float(self.TilePx))
        tela_h_tiles = float(self.TamanhoTelaPx[1]) / max(1.0, float(self.TilePx))
        max_x = max(0.0, float(largura) - tela_w_tiles)
        max_y = max(0.0, float(altura) - tela_h_tiles)
        self.PosicaoTiles = (max(0.0, min(max_x, x)), max(0.0, min(max_y, y)))

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
        self._normalizar_posicao_limites()
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


class CameraDungeon(Camera):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.LayoutDungeonAtual: dict = {}

    def definir_layout_dungeon(self, layout: dict | None) -> None:
        self.LayoutDungeonAtual = dict(layout) if isinstance(layout, dict) else {}

    @staticmethod
    def _tamanho_sala(layout: dict) -> Tuple[float, float]:
        base = float(layout.get("tamanho_bloco_sala_tiles", 30) or 30)
        return (
            float(layout.get("largura_bloco_sala_tiles", base) or base),
            float(layout.get("altura_bloco_sala_tiles", base) or base),
        )

    def _sala_1x1_atual(self):
        layout = self.LayoutDungeonAtual if isinstance(self.LayoutDungeonAtual, dict) else {}
        salas = layout.get("salas") if isinstance(layout.get("salas"), list) else []
        if not salas or self.EntidadeMain is None or not hasattr(self.EntidadeMain, "Posicao"):
            return None
        sala_w, sala_h = self._tamanho_sala(layout)
        px, py = float(self.EntidadeMain.Posicao[0]), float(self.EntidadeMain.Posicao[1])
        sala_atual = (int(px // max(1.0, sala_w)), int(py // max(1.0, sala_h)))
        for sala in salas:
            if not isinstance(sala, dict):
                continue
            pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
            if not pos or len(pos) != 2:
                continue
            if int(pos[0]) != sala_atual[0] or int(pos[1]) != sala_atual[1]:
                continue
            if int(sala.get("largura_blocos", 1) or 1) == 1 and int(sala.get("altura_blocos", 1) or 1) == 1:
                return (float(pos[0]) * sala_w, float(pos[1]) * sala_h, sala_w, sala_h)
        return None

    def atualizar(self, delta_time: float) -> Vector2:
        sala = self._sala_1x1_atual()
        if sala is None:
            return super().atualizar(delta_time)
        sx, sy, sw, sh = sala
        half_w_tiles = (self.TamanhoTelaPx[0] * 0.5) / max(1.0, float(self.TilePx))
        half_h_tiles = (self.TamanhoTelaPx[1] * 0.5) / max(1.0, float(self.TilePx))
        alvo = (sx + (sw * 0.5) - half_w_tiles, sy + (sh * 0.5) - half_h_tiles)
        fator = min(1.0, max(0.0, float(delta_time)) * max(10.0, float(self.Suavizacao) * 1.8))
        self.PosicaoTiles = (
            float(self.PosicaoTiles[0]) + (float(alvo[0]) - float(self.PosicaoTiles[0])) * fator,
            float(self.PosicaoTiles[1]) + (float(alvo[1]) - float(self.PosicaoTiles[1])) * fator,
        )
        self._normalizar_posicao_limites()
        return self.PosicaoTiles


class CameraBatalha(Camera):
    TILE_MIN = 30
    TILE_MAX = 50

    def __init__(self, tamanho_tela_px: Vector2, posicao_inicial_tiles: Vector2 = (0.0, 0.0), tile_px: int = 40) -> None:
        super().__init__(tamanho_tela_px=tamanho_tela_px, entidade_main=None, posicao_inicial_tiles=posicao_inicial_tiles, suavizacao=100.0, tile_px=tile_px)
        self._arrastando = False
        self._ultimo_mouse_px: Optional[Vector2] = None
        self._origem_arena_mundo_tiles: Vector2 = (0.0, 0.0)
        self._tamanho_arena_tiles: Optional[Vector2] = None

    def definir_referencia_arena(self, origem_mundo_tiles: Vector2, tamanho_arena_tiles: Optional[Vector2] = None) -> None:
        self._origem_arena_mundo_tiles = (float(origem_mundo_tiles[0]), float(origem_mundo_tiles[1]))
        if isinstance(tamanho_arena_tiles, (tuple, list)) and len(tamanho_arena_tiles) == 2:
            self._tamanho_arena_tiles = (float(tamanho_arena_tiles[0]), float(tamanho_arena_tiles[1]))
        else:
            self._tamanho_arena_tiles = None

    def batalha_para_mundo_tiles(self, posicao_batalha_tiles: Vector2) -> Vector2:
        return (
            float(self._origem_arena_mundo_tiles[0]) + float(posicao_batalha_tiles[0]),
            float(self._origem_arena_mundo_tiles[1]) + float(posicao_batalha_tiles[1]),
        )

    def batalha_para_tela_px(self, posicao_batalha_tiles: Vector2) -> Vector2:
        return self.mundo_para_tela_px(self.batalha_para_mundo_tiles(posicao_batalha_tiles))

    def tela_para_batalha_tiles(self, posicao_tela_px: Vector2) -> Vector2:
        mundo = self.tela_para_mundo_tiles(posicao_tela_px)
        local_x = float(mundo[0]) - float(self._origem_arena_mundo_tiles[0])
        local_y = float(mundo[1]) - float(self._origem_arena_mundo_tiles[1])
        if self._tamanho_arena_tiles is None:
            return local_x, local_y
        largura, altura = self._tamanho_arena_tiles
        return (
            max(0.0, min(float(largura), local_x)),
            max(0.0, min(float(altura), local_y)),
        )

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
