from __future__ import annotations

import pygame
from Codigo.ModulosGerais.DesenhoMapa import desenhar_seta_player
from Codigo.Geradores.ConstrutorDungeon import construir_surface_mapa_dungeon_local


class MinimapaMundo:
    def __init__(self, tamanho: int = 180, margem: int = 12):
        self.tamanho = int(tamanho)
        self.margem = int(margem)
        self._cache_key = None
        self._cache_surface = None

    def desenhar(self, tela: pygame.Surface, servico_mapa, pos_player_mundo: tuple[float, float], angulo: float, layout_dungeon=None, estado_dungeon=None) -> None:
        area = pygame.Rect(tela.get_width() - self.tamanho - self.margem, self.margem, self.tamanho, self.tamanho)
        if isinstance(layout_dungeon, dict) and str(layout_dungeon.get("dimensao") or "").startswith("Dungeon_"):
            base = construir_surface_mapa_dungeon_local(layout_dungeon, estado_dungeon, cell=16, raio=1)
            if base is not None:
                mini = pygame.transform.smoothscale(base, area.size)
                tela.blit(mini, area)
                pygame.draw.rect(tela, (8, 8, 8), area, 2)
                desenhar_seta_player(tela, area.center, angulo, tamanho=10, escala_extra=0.5)
            return
        if servico_mapa is None:
            return
        ger = servico_mapa.gerenciador
        chunk_blocos = int(ger.meta.get("chunk_blocos", 10) or 10)
        lado_chunks = 6
        lado_px_logico = lado_chunks * chunk_blocos
        x0 = int(pos_player_mundo[0]) - (lado_px_logico // 2)
        y0 = int(pos_player_mundo[1]) - (lado_px_logico // 2)
        chunk_player = (int(pos_player_mundo[0] // max(1, chunk_blocos)), int(pos_player_mundo[1] // max(1, chunk_blocos)))
        cache_key = (chunk_player, area.size, lado_px_logico, int(ger.versao_mapa()))
        if self._cache_key != cache_key or self._cache_surface is None:
            base = pygame.Surface((lado_px_logico, lado_px_logico))
            base.fill((0, 0, 0))
            for atlas_key in ger.atlas_keys_no_rect(x0, y0, lado_px_logico, lado_px_logico):
                atlas = ger.obter_atlas(*atlas_key)
                if atlas is None:
                    continue
                rect_atlas = pygame.Rect(atlas.atlas_x * ger.atlas_px, atlas.atlas_y * ger.atlas_px, ger.atlas_px, ger.atlas_px)
                area_mundo = pygame.Rect(x0, y0, lado_px_logico, lado_px_logico)
                inter = rect_atlas.clip(area_mundo)
                if inter.width <= 0 or inter.height <= 0:
                    continue
                src = pygame.Rect(inter.x - rect_atlas.x, inter.y - rect_atlas.y, inter.width, inter.height)
                dst = pygame.Rect(inter.x - x0, inter.y - y0, inter.width, inter.height)
                base.blit(atlas.surface_base, dst, src)
            self._cache_surface = pygame.transform.smoothscale(base, (area.width, area.height))
            self._cache_key = cache_key
        mini = self._cache_surface if self._cache_surface is not None else pygame.Surface((area.width, area.height))
        tela.blit(mini, area)
        pygame.draw.rect(tela, (8, 8, 8), area, 2)

        desenhar_seta_player(tela, area.center, angulo, tamanho=10, escala_extra=0.5)
