from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from Codigo.ModulosMundo.Geradores.Ator import Ator

if TYPE_CHECKING:
    from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha


class RenderizadorBatalha:
    def __init__(self, batalha: "ControladorBatalha"):
        self.batalha = batalha

    def desenhar(self, surface):
        b = self.batalha
        if b.arena is None:
            return
        if b.hud is not None:
            b.hud.preparar_layout(surface)
        b.arena.renderizar(surface, b.camera)
        areas_destacadas = []
        reservas_destacadas = []
        if b.montador_jogadas is not None:
            areas_destacadas = b.montador_jogadas.areas_destacadas()
            reservas_destacadas = b.montador_jogadas.reservas_destacadas()
        b.arena.desenhar_efeitos_areas(surface, b.camera)
        b.arena.desenhar_areas(
            surface,
            b.camera,
            area_hover=b._area_hover,
            area_selecionada=b.area_selecionada,
            areas_destacadas=areas_destacadas,
        )
        if b.montador_jogadas is not None:
            b.montador_jogadas.desenhar_pulso_previa(surface)
            b.montador_jogadas.desenhar_fantasmas_movimento(surface)
        for indicador in list(getattr(b.montador_jogadas, "indicadores_alvos_parciais", []) or []):
            indicador.atualizar(dt=b._ultimo_dt)
            indicador.desenhar(surface, b.camera)
        for indicador in list(getattr(b.montador_jogadas, "indicadores_preparados", []) or []):
            indicador.atualizar(dt=b._ultimo_dt)
            indicador.desenhar(surface, b.camera)
        if getattr(b.montador_jogadas, "indicador_previa", None) is not None:
            b.montador_jogadas.indicador_previa.atualizar(dt=b._ultimo_dt)
            b.montador_jogadas.indicador_previa.desenhar(surface, b.camera)

        b._desenhar_atores_visuais_batalha(surface)

        for pokemon in b.pokemons:
            if pokemon.esta_ativo() and not pokemon.esta_na_reserva():
                if not b.pokemon_visivel(pokemon):
                    pokemon.RectAtual = pygame.Rect(0, 0, 0, 0)
                    continue
                hover = pokemon.contem_ponto(pygame.mouse.get_pos())
                pokemon.desenhar(surface, b.camera, b.arena, selecionado=(b.area_selecionada == pokemon.AreaId), hover=hover)

        reservas_destacadas_set = set(reservas_destacadas)
        for lado in ("jogador", "inimigo"):
            for slot in b.arena.obter_slots_reserva(lado):
                poke = b.pokemons_por_id.get(slot.get("pokemon_id"))
                if poke is None:
                    continue
                if not b.pokemon_visivel(poke):
                    poke.RectAtual = pygame.Rect(0, 0, 0, 0)
                    continue
                rect = slot.get("rect_tela")
                hover = rect.collidepoint(pygame.mouse.get_pos()) if rect else False
                selecionado = b.area_selecionada in {slot.get("id_slot"), slot.get("pokemon_id")}
                if rect:
                    destacado = str(slot.get("id_slot")) in reservas_destacadas_set
                    if selecionado:
                        borda = (255, 235, 90, 245)
                    elif destacado:
                        pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
                        borda = (255, 225, 70, int(80 + 150 * pulso))
                    elif hover:
                        borda = (204, 212, 228, 170)
                    else:
                        borda = (0, 0, 0, 225)
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(overlay, (0, 0, 0, 235), overlay.get_rect(), 4)
                    pygame.draw.rect(overlay, borda, overlay.get_rect().inflate(-4, -4), 3)
                    surface.blit(overlay, rect.topleft)
                poke.desenhar_reserva(surface, rect, selecionado=selecionado, hover=hover, camera=b.camera)

        if b.controlador_animacoes is not None:
            b.controlador_animacoes.desenhar(surface)
        b.hud.desenhar(surface, b._ultimos_eventos, b._ultimo_dt)
        alpha = max(0, min(255, int(round(b._fuga_alpha))))
        if alpha > 0:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            surface.blit(overlay, (0, 0))

    def posicao_captura_lado_tela(self, lado_id=None):
        b = self.batalha
        pos = b.posicao_captura_lado_mundo(lado_id)
        if pos is None or b.camera is None:
            return None
        try:
            return b.camera.mundo_para_tela_px(pos)
        except Exception:
            return None

    def posicao_captura_lado_mundo(self, lado_id=None):
        b = self.batalha
        if b.arena is None:
            return None
        lado = int(lado_id if lado_id is not None else b.lado_jogador)
        aliado = int(lado) == int(b.lado_jogador)
        area_id = "A7" if aliado else "I3"
        area = b.arena.obter_area_por_id(area_id)
        if not area or not isinstance(area.get("rect"), pygame.Rect):
            return b.arena.centro_area(area_id)
        rect = area["rect"]
        margem = float(b.MARGEM_ATOR_CAPTURA_TILES)
        if aliado:
            return (float(rect.left) - margem, float(rect.centery))
        return (float(rect.right) + margem, float(rect.centery))

    def preparar_atores_visuais_batalha(self):
        b = self.batalha
        tile = max(1, int(getattr(b.camera, "TilePx", 40) or 40)) if b.camera is not None else 40
        b._ator_visual_player = Ator(nome_skin=b._skin_player_batalha(), posicao=(0.0, 0.0), escala_skin_tiles=b.ESCALA_ATOR_BATALHA, tile_px=tile)
        npc_skin = b._skin_npc_batalha()
        b._ator_visual_npc = Ator(nome_skin=npc_skin, posicao=(0.0, 0.0), escala_skin_tiles=b.ESCALA_ATOR_BATALHA, tile_px=tile) if npc_skin else None

    def skin_player_batalha(self):
        b = self.batalha
        if b.ator is not None and getattr(b.ator, "NomeSkin", None):
            return str(getattr(b.ator, "NomeSkin"))
        jogo = getattr(b, "jogo", None)
        dados = getattr(jogo, "INFO", {}).get("PlayerDadosServer") if jogo is not None and isinstance(getattr(jogo, "INFO", None), dict) else {}
        for chave in ("skin", "nome_skin", "NomeSkin"):
            if isinstance(dados, dict) and dados.get(chave):
                return str(dados.get(chave))
        perfil = b.perfil_local()
        skins = list(getattr(perfil, "SkinsLiberadas", []) or [])
        return str(skins[0] if skins else "S1.png")

    def skin_npc_batalha(self):
        b = self.batalha
        tipo = str(b.tipo_batalha or "").strip().lower()
        if tipo not in {"treinador", "trainer"}:
            return ""
        ctx = dict(getattr(b, "contexto_batalha", {}) or {})
        npc = ctx.get("npc_contexto") if isinstance(ctx.get("npc_contexto"), dict) else {}
        estado = npc.get("estado") if isinstance(npc.get("estado"), dict) else {}
        return str(npc.get("skin") or estado.get("skin") or "1.png")

    def desenhar_atores_visuais_batalha(self, surface):
        b = self.batalha
        tipo = str(b.tipo_batalha or "").strip().lower()
        if tipo not in {"confronto", "treinador", "trainer"} or bool(b.modo_teste):
            return
        if b._ator_visual_player is None:
            b._preparar_atores_visuais_batalha()
        b._desenhar_ator_captura(surface, b._ator_visual_player, b.lado_jogador)
        if tipo in {"treinador", "trainer"}:
            b._desenhar_ator_captura(surface, b._ator_visual_npc, b.obter_lado_ia())

    def desenhar_ator_captura(self, surface, ator, lado_id):
        b = self.batalha
        if ator is None or not hasattr(ator, "Desenhador"):
            return
        pos_mundo = b.posicao_captura_lado_mundo(lado_id)
        pos_tela = b.posicao_captura_lado_tela(lado_id)
        if pos_mundo is None or pos_tela is None:
            return
        if b.camera is not None and hasattr(ator, "set_tile_px"):
            ator.set_tile_px(max(1, int(getattr(b.camera, "TilePx", 40) or 40)))
        ator.definir_posicao(float(pos_mundo[0]), float(pos_mundo[1]))
        mouse = pygame.mouse.get_pos()
        dx = float(mouse[0]) - float(pos_tela[0])
        dy = float(mouse[1]) - float(pos_tela[1])
        if abs(dx) + abs(dy) > 0.001:
            ator.definir_angulo_olhar((math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0)
        ator.Desenhador.desenhar(surface, pos_tela, mouse_pos=mouse, angulo_graus=getattr(ator, "AnguloOlhar", 0.0), respiracao_tempo=b._respiracao_atores_batalha)
