from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.EstruturaNaturais import EstruturaNaturalFake, tipo_estrutura_natural_por_codigo

Vector2 = Tuple[float, float]


class Arena:
    def __init__(self, contexto: Dict[str, object]):
        self.Contexto = dict(contexto or {})
        self.Centro = tuple(self.Contexto.get("centro", (50.0, 30.0)))
        self.Largura = int(self.Contexto.get("largura", 100) or 100)
        self.Altura = int(self.Contexto.get("altura", 60) or 60)
        self.ArenaLargura = int(self.Contexto.get("arena_largura", 50) or 50)
        self.ArenaAltura = int(self.Contexto.get("arena_altura", 30) or 30)
        self.BlocoInicio = tuple(self.Contexto.get("origem", (0.0, 0.0)))

        self._tiles: List[Tuple[int, int, int]] = []
        self._estruturas_fundo: List[EstruturaNaturalFake] = []
        self._cores = {
            0: (24, 72, 145), 1: (64, 156, 255), 2: (106, 190, 48), 3: (46, 125, 50),
            4: (230, 210, 140), 5: (217, 179, 92), 6: (245, 248, 252), 7: (140, 82, 255),
            8: (88, 70, 70), 9: (110, 92, 68),
        }
        self._cache_sprites: Dict[Tuple[str, int], pygame.Surface] = {}
        self._montar()

    def _retangulo_arena(self) -> pygame.Rect:
        cx, cy = float(self.Centro[0]), float(self.Centro[1])
        x0 = cx - (self.ArenaLargura * 0.5)
        y0 = cy - (self.ArenaAltura * 0.5)
        return pygame.Rect(int(x0), int(y0), int(self.ArenaLargura), int(self.ArenaAltura))

    def _montar(self) -> None:
        for item in self.Contexto.get("tiles", []):
            if not isinstance(item, dict):
                continue
            tx = int(item.get("x", 0) or 0)
            ty = int(item.get("y", 0) or 0)
            bloco = int(item.get("bloco", 0) or 0)
            self._tiles.append((tx, ty, bloco))

        arena_rect = self._retangulo_arena()
        margem = 3
        area_exclusao = pygame.Rect(arena_rect.x - margem, arena_rect.y - margem, arena_rect.w + margem * 2, arena_rect.h + margem * 2)
        for item in self.Contexto.get("estruturas", []):
            if not isinstance(item, dict):
                continue
            x = float(item.get("x", 0.0) or 0.0)
            y = float(item.get("y", 0.0) or 0.0)
            if area_exclusao.collidepoint(x, y):
                continue
            codigo = int(item.get("codigo_natural", 0) or 0)
            sprite = str(item.get("sprite", "") or "")
            if not sprite:
                cfg = tipo_estrutura_natural_por_codigo(codigo)
                if isinstance(cfg, dict):
                    sprite = str(cfg.get("sprite", "") or "")
            self._estruturas_fundo.append(EstruturaNaturalFake(posicao=(x, y), sprite=sprite, codigo_natural=codigo))

    def _carregar_sprite(self, caminho: str, tile_px: int):
        caminho = str(caminho or "").strip()
        if not caminho:
            return None
        chave = (caminho, int(tile_px))
        if chave in self._cache_sprites:
            return self._cache_sprites[chave]
        try:
            base = pygame.image.load(caminho).convert_alpha()
            escala = float(tile_px) / 40.0
            if abs(escala - 1.0) > 0.001:
                w = max(1, int(base.get_width() * escala))
                h = max(1, int(base.get_height() * escala))
                base = pygame.transform.smoothscale(base, (w, h))
            self._cache_sprites[chave] = base
        except Exception:
            self._cache_sprites[chave] = None
        return self._cache_sprites[chave]

    def _desenhar_grid_arena(self, tela: pygame.Surface, camera, tile_px: int) -> None:
        rect = self._retangulo_arena()
        x0_px, y0_px = camera.mundo_para_tela_px((rect.x, rect.y))
        w_px = int(rect.w * tile_px)
        h_px = int(rect.h * tile_px)
        grid_surf = pygame.Surface((max(1, w_px), max(1, h_px)), pygame.SRCALPHA)
        passo = max(6, tile_px)
        cor = (245, 245, 255, 28)
        for x in range(0, w_px, passo):
            pygame.draw.line(grid_surf, cor, (x, 0), (x, h_px), 1)
        for y in range(0, h_px, passo):
            pygame.draw.line(grid_surf, cor, (0, y), (w_px, y), 1)
        tela.blit(grid_surf, (int(x0_px), int(y0_px)))

    def renderizar(self, tela, camera) -> None:
        tile_px = max(1, int(getattr(camera, "TilePx", 40) or 40))
        for tx, ty, bloco in self._tiles:
            px, py = camera.mundo_para_tela_px((tx, ty))
            pygame.draw.rect(tela, self._cores.get(bloco, (255, 0, 255)), (int(px), int(py), tile_px + 1, tile_px + 1))

        for estrutura in self._estruturas_fundo:
            px, py = camera.mundo_para_tela_px(estrutura.Posicao)
            sprite = self._carregar_sprite(estrutura.Sprite, tile_px)
            if sprite is None:
                pygame.draw.circle(tela, (92, 72, 52), (int(px), int(py)), max(4, tile_px // 4))
                continue
            tela.blit(sprite, sprite.get_rect(center=(int(px), int(py))))

        rect = self._retangulo_arena()
        x0, y0 = camera.mundo_para_tela_px((rect.x, rect.y))
        border = pygame.Rect(int(x0), int(y0), int(rect.w * tile_px), int(rect.h * tile_px))
        pygame.draw.rect(tela, (245, 228, 130), border, width=max(2, tile_px // 10), border_radius=5)
        self._desenhar_grid_arena(tela, camera, tile_px)
