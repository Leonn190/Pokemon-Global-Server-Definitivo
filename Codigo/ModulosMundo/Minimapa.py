from __future__ import annotations

import pygame
from Codigo.ModulosGerais.DesenhoMapa import desenhar_seta_player


class MinimapaMundo:
    def __init__(self, tamanho: int = 180, margem: int = 12):
        self.tamanho = int(tamanho)
        self.margem = int(margem)

    def desenhar(self, tela: pygame.Surface, servico_mapa, pos_player_mundo: tuple[float, float], angulo: float) -> None:
        if servico_mapa is None:
            return
        ger = servico_mapa.gerenciador
        chunk_blocos = int(ger.meta.get("chunk_blocos", 10) or 10)
        lado_chunks = 6
        lado_px_logico = lado_chunks * chunk_blocos
        area = pygame.Rect(tela.get_width() - self.tamanho - self.margem, self.margem, self.tamanho, self.tamanho)

        base = pygame.Surface((lado_px_logico, lado_px_logico))
        base.fill((0, 0, 0))
        x0 = int(pos_player_mundo[0]) - (lado_px_logico // 2)
        y0 = int(pos_player_mundo[1]) - (lado_px_logico // 2)

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

        mini = pygame.transform.smoothscale(base, (area.width, area.height))
        tela.blit(mini, area)
        pygame.draw.rect(tela, (8, 8, 8), area, 2)

        desenhar_seta_player(tela, area.center, angulo, tamanho=10, escala_extra=0.5)
