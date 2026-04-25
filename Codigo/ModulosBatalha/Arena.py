from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.EstruturaNaturais import EstruturaNaturalFake, tipo_estrutura_natural_por_codigo
from Codigo.ModulosGerais.GerenciadorTiles import GerenciadorTiles
from Codigo.Prefabs.Texto import Texto

Vector2 = Tuple[float, float]


class Arena:
    def __init__(self, contexto: Dict[str, object]):
        self.Contexto = dict(contexto or {})
        self.Centro = tuple(self.Contexto.get("centro", (50.0, 30.0)))
        self.Largura = int(self.Contexto.get("largura", 80) or 80)
        self.Altura = int(self.Contexto.get("altura", 40) or 40)
        self.ArenaLargura = int(self.Contexto.get("arena_largura", 40) or 40)
        self.ArenaAltura = int(self.Contexto.get("arena_altura", 20) or 20)
        self.BlocoInicio = tuple(self.Contexto.get("origem", (0.0, 0.0)))

        self._tiles: List[Tuple[int, int, int]] = []
        self._tem_tiles_contexto = False
        self._estruturas_fundo: List[EstruturaNaturalFake] = []
        self._cores = {
            0: (24, 72, 145), 1: (64, 156, 255), 2: (106, 190, 48), 3: (46, 125, 50),
            4: (230, 210, 140), 5: (217, 179, 92), 6: (245, 248, 252), 7: (140, 82, 255),
            8: (88, 70, 70), 9: (110, 92, 68), 10: (226, 238, 252), 11: (206, 224, 243),
        }
        self._cache_sprites: Dict[Tuple[str, int], pygame.Surface] = {}
        self._grid_tiles: List[List[int]] = [[0 for _ in range(max(1, self.Largura))] for _ in range(max(1, self.Altura))]
        self._renderizador_tiles = GerenciadorTiles(cores_blocos=self._cores)
        self._cache_mapa: pygame.Surface | None = None
        self._cache_tile_px = 0

        self._areas: list[dict[str, object]] = []
        self._areas_por_id: dict[str, dict[str, object]] = {}
        self._ocupacao_areas: dict[str, object] = {}
        self._slots_reserva: dict[str, list[dict[str, object]]] = {"jogador": [], "inimigo": []}
        self._textos_indices_area: dict[str, Texto] = {}

        self._montar()
        self.criar_areas_batalha()

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
            self._tem_tiles_contexto = True
            if 0 <= ty < self.Altura and 0 <= tx < self.Largura:
                self._grid_tiles[ty][tx] = bloco

        arena_rect = self._retangulo_arena()
        for item in self.Contexto.get("estruturas", []):
            if not isinstance(item, dict):
                continue
            x = float(item.get("x", 0.0) or 0.0)
            y = float(item.get("y", 0.0) or 0.0)
            if arena_rect.collidepoint(x, y):
                continue
            codigo = int(item.get("codigo_natural", 0) or 0)
            sprite = str(item.get("sprite", "") or "")
            if not sprite:
                cfg = tipo_estrutura_natural_por_codigo(codigo)
                if isinstance(cfg, dict):
                    sprite = str(cfg.get("sprite", "") or "")
            self._estruturas_fundo.append(EstruturaNaturalFake(posicao=(x, y), sprite=sprite, codigo_natural=codigo))

    def criar_areas_batalha(self) -> None:
        self._areas = []
        self._areas_por_id = {}
        margem_x = 1
        margem_y = 1
        espaco_x = 2
        area_lado = 6

        arena_rect = self._retangulo_arena()
        base_ax = arena_rect.x + margem_x
        base_ay = arena_rect.y + margem_y
        base_ix = base_ax + (3 * area_lado) + espaco_x
        base_iy = arena_rect.y + margem_y

        for row in range(3):
            for col in range(3):
                aid = f"A{row * 3 + col + 1}"
                x = base_ax + (col * area_lado)
                y = base_ay + (row * area_lado)
                area = {
                    "id": aid,
                    "lado_visual": "jogador",
                    "lado_id": 50,
                    "rect": pygame.Rect(x, y, area_lado, area_lado),
                    "centro": (x + area_lado * 0.5, y + area_lado * 0.5),
                    "ocupante_id": None,
                }
                self._areas.append(area)
                self._areas_por_id[aid] = area
                self._textos_indices_area[aid] = Texto(
                    str(row * 3 + col + 1),
                    style={
                        "size": 36,
                        "align": "center",
                        "color": (220, 228, 245),
                        "outline": True,
                        "outline_thickness": 2,
                        "outline_color": (10, 14, 24),
                    },
                )

        for row in range(3):
            for col in range(3):
                aid = f"I{row * 3 + col + 1}"
                x = base_ix + (col * area_lado)
                y = base_iy + (row * area_lado)
                area = {
                    "id": aid,
                    "lado_visual": "inimigo",
                    "lado_id": 51,
                    "rect": pygame.Rect(x, y, area_lado, area_lado),
                    "centro": (x + area_lado * 0.5, y + area_lado * 0.5),
                    "ocupante_id": None,
                }
                self._areas.append(area)
                self._areas_por_id[aid] = area
                self._textos_indices_area[aid] = Texto(
                    str(row * 3 + col + 1),
                    style={
                        "size": 36,
                        "align": "center",
                        "color": (220, 228, 245),
                        "outline": True,
                        "outline_thickness": 2,
                        "outline_color": (10, 14, 24),
                    },
                )

    def atualizar_layout_batalha(self, camera=None) -> None:
        # Mantém API para fases futuras; layout atual é estático em tiles de mundo.
        _ = camera

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
        if not self._tem_tiles_contexto:
            tela.fill((0, 0, 0))
            return
        if self._cache_mapa is None or self._cache_tile_px != tile_px:
            self._cache_mapa = self._renderizador_tiles.renderizar_chunk(
                chave_chunk=(0, 0),
                grid=self._grid_tiles,
                tile_px=tile_px,
                tamanho_chunk=max(self.Largura, self.Altura, 1),
            )
            self._cache_tile_px = tile_px
        if self._cache_mapa is None:
            return
        x0, y0 = camera.mundo_para_tela_px((0, 0))
        tela.blit(self._cache_mapa, (int(x0), int(y0)))

        for estrutura in self._estruturas_fundo:
            px, py = camera.mundo_para_tela_px(estrutura.Posicao)
            sprite = self._carregar_sprite(estrutura.Sprite, tile_px)
            if sprite is None:
                pygame.draw.circle(tela, (92, 72, 52), (int(px), int(py)), max(4, tile_px // 4))
                continue
            tela.blit(sprite, sprite.get_rect(center=(int(px), int(py))))

    def desenhar_areas(self, surface, camera, area_hover=None, area_selecionada=None):
        for area in self._areas:
            rect_tela = self.rect_area_tela(area["id"], camera)
            if rect_tela is None:
                continue
            overlay = pygame.Surface((rect_tela.w, rect_tela.h), pygame.SRCALPHA)
            if not self._tem_tiles_contexto:
                cor_base = (44, 96, 210, 120) if area.get("lado_visual") == "jogador" else (196, 68, 76, 120)
                pygame.draw.rect(overlay, cor_base, overlay.get_rect(), border_radius=4)
            borda = (164, 170, 182, 130)
            if area_hover == area["id"]:
                borda = (198, 206, 220, 180)
            if area_selecionada == area["id"]:
                borda = (255, 235, 90, 235)
            pygame.draw.rect(overlay, borda, overlay.get_rect(), 2)
            surface.blit(overlay, rect_tela.topleft)
            texto_idx = self._textos_indices_area.get(str(area.get("id", "")))
            if texto_idx is not None:
                escala = max(20, int(rect_tela.height * 0.42))
                texto_idx.style["size"] = escala
                texto_layer = pygame.Surface((rect_tela.w, rect_tela.h), pygame.SRCALPHA)
                texto_idx.set_pos((rect_tela.w // 2, rect_tela.h // 2))
                texto_idx.draw(texto_layer)
                texto_layer.set_alpha(110)
                surface.blit(texto_layer, rect_tela.topleft)

    def obter_area_por_id(self, area_id):
        return self._areas_por_id.get(str(area_id or "").strip())

    def area_em_posicao_mouse(self, pos_mouse, camera):
        wx, wy = camera.tela_para_mundo_tiles(pos_mouse)
        for area in self._areas:
            rect = area.get("rect")
            if isinstance(rect, pygame.Rect) and rect.collidepoint(wx, wy):
                return area["id"]
        return None

    def area_esta_ocupada(self, area_id):
        return self._ocupacao_areas.get(str(area_id or "")) is not None

    def pokemon_na_area(self, area_id):
        return self._ocupacao_areas.get(str(area_id or ""))

    def atualizar_ocupacao(self, pokemons):
        self._ocupacao_areas = {}
        for area in self._areas:
            area["ocupante_id"] = None
        for pokemon in pokemons or []:
            aid = getattr(pokemon, "AreaId", None)
            if not aid or bool(getattr(pokemon, "EmReserva", False)):
                continue
            self._ocupacao_areas[str(aid)] = pokemon
            area = self.obter_area_por_id(aid)
            if area is not None:
                area["ocupante_id"] = getattr(pokemon, "id_batalha", None)

    def centro_area(self, area_id):
        area = self.obter_area_por_id(area_id)
        return tuple(area.get("centro", (0.0, 0.0))) if area else None

    def centro_area_tela(self, area_id, camera):
        centro = self.centro_area(area_id)
        return camera.mundo_para_tela_px(centro) if centro else None

    def rect_area_tela(self, area_id, camera):
        area = self.obter_area_por_id(area_id)
        if area is None:
            return None
        rect = area["rect"]
        x, y = camera.mundo_para_tela_px((rect.x, rect.y))
        tile = max(1, int(getattr(camera, "TilePx", 40)))
        return pygame.Rect(int(x), int(y), int(rect.width * tile), int(rect.height * tile))

    def obter_slots_reserva(self, lado_visual):
        return list(self._slots_reserva.get(str(lado_visual or ""), []))

    def reserva_em_posicao_mouse(self, pos_mouse, camera):
        wx, wy = camera.tela_para_mundo_tiles(pos_mouse)
        for lado, slots in self._slots_reserva.items():
            for slot in slots:
                rect_tela = slot.get("rect_tela")
                if isinstance(rect_tela, pygame.Rect) and rect_tela.collidepoint(pos_mouse):
                    retorno = dict(slot)
                    retorno["lado_visual"] = lado
                    return retorno
                rect = slot.get("rect")
                if isinstance(rect, pygame.Rect) and rect.collidepoint(wx, wy):
                    retorno = dict(slot)
                    retorno["lado_visual"] = lado
                    return retorno
        return None

    def atualizar_slots_reserva(self, pokemons, camera):
        tile = max(1, int(getattr(camera, "TilePx", 40)))
        arena_rect = self._retangulo_arena()
        self._slots_reserva = {"jogador": [], "inimigo": []}
        por_lado = {
            "jogador": [p for p in pokemons if bool(getattr(p, "EmReserva", False)) and getattr(p, "Lado", "") == "jogador"],
            "inimigo": [p for p in pokemons if bool(getattr(p, "EmReserva", False)) and getattr(p, "Lado", "") == "inimigo"],
        }
        lado_slot = 4
        gap = 1
        for lado, lista in por_lado.items():
            for i, poke in enumerate(lista[:3]):
                if lado == "jogador":
                    x = arena_rect.x + i * (lado_slot + gap)
                    y = arena_rect.bottom + 1
                else:
                    x = arena_rect.right - ((3 - i) * lado_slot + (2 - i) * gap)
                    y = arena_rect.y - (lado_slot + 1)
                rect_mundo = pygame.Rect(x, y, lado_slot, lado_slot)
                tx, ty = camera.mundo_para_tela_px((x, y))
                rect_tela = pygame.Rect(int(tx), int(ty), int(lado_slot * tile), int(lado_slot * tile))
                self._slots_reserva[lado].append({
                    "id_slot": f"R-{lado}-{i + 1}",
                    "pokemon_id": getattr(poke, "id_batalha", None),
                    "rect": rect_mundo,
                    "rect_tela": rect_tela,
                })
