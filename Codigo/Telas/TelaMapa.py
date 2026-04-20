from __future__ import annotations

import pygame

from Codigo.Prefabs.Botao import BotaoAlavanca
from Codigo.Prefabs.Texto import Texto
from Codigo.ModulosGerais.DesenhoMapa import desenhar_seta_player


class TelaMapa:
    def __init__(self):
        self.ativo = False
        self.zoom = 1.0
        self.zoom_max = 10.0
        self.offset = [0.0, 0.0]
        self.dragging = False
        self.fade_ms = 250
        self.aberto_ms = 0
        self._cache_chave = None
        self._cache_frame = None
        self._txt_regiao = Texto("", style={"size": 34, "outline": True, "align": "center"})
        self._txt_poi = Texto("", style={"size": 20, "outline": True, "align": "center"})
        self._txt_loading = Texto("Carregando mapa...", style={"size": 30, "outline": True, "align": "center"})
        self._botoes = {}

    def abrir(self, jogo, servico_mapa, pos_player_mundo):
        self.ativo = True
        self.aberto_ms = pygame.time.get_ticks()
        self._cache_chave = None
        self._cache_frame = None
        mundo_w, mundo_h = servico_mapa.gerenciador.mundo_tamanho_px()
        tela_w, tela_h = jogo.TELA.get_size()
        self.zoom = max(float(tela_h) / max(1.0, float(mundo_h)), 2.0)
        self.zoom = min(self.zoom, self.zoom_max)
        self.offset = [tela_w * 0.5 - float(pos_player_mundo[0]) * self.zoom, tela_h * 0.5 - float(pos_player_mundo[1]) * self.zoom]
        self._garantir_botoes(jogo)
        self._clamp_offset(jogo, servico_mapa)

    def fechar(self):
        self.ativo = False
        self.dragging = False

    def _garantir_botoes(self, jogo):
        if self._botoes:
            return
        estilo = {"text_style": {"size": 18, "outline": True}}
        largura = 200
        altura = 44
        topo = 14
        gap = 8
        x = jogo.TELA.get_width() - largura - 14
        nomes = ["Vilas", "Estádios", "Regiões"]
        for i, nome in enumerate(nomes):
            self._botoes[nome] = BotaoAlavanca(pygame.Rect(x, topo + i * (altura + gap), largura, altura), nome, estado_inicial=(nome != "Regiões"), style=estilo)

    def _clamp_offset(self, jogo, servico_mapa):
        tela_w, tela_h = jogo.TELA.get_size()
        mundo_w, mundo_h = servico_mapa.gerenciador.mundo_tamanho_px()
        max_x = 40
        max_y = 40
        min_x = tela_w - (mundo_w * self.zoom) - 40
        min_y = tela_h - (mundo_h * self.zoom) - 40
        if min_x > max_x:
            min_x = max_x = (tela_w - (mundo_w * self.zoom)) * 0.5
        if min_y > max_y:
            min_y = max_y = (tela_h - (mundo_h * self.zoom)) * 0.5
        self.offset[0] = max(min_x, min(max_x, self.offset[0]))
        self.offset[1] = max(min_y, min(max_y, self.offset[1]))

    def processar_eventos(self, jogo, eventos, servico_mapa):
        self._garantir_botoes(jogo)
        for ev in eventos:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.fechar()
                return
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
                if (pygame.time.get_ticks() - int(self.aberto_ms or 0)) < 120:
                    continue
                self.fechar()
                return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
                self.dragging = True
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 3:
                self.dragging = False
            if ev.type == pygame.MOUSEMOTION and self.dragging:
                self.offset[0] += float(ev.rel[0])
                self.offset[1] += float(ev.rel[1])
                self._cache_chave = None
            if ev.type == pygame.MOUSEWHEEL:
                mouse = pygame.mouse.get_pos()
                old_zoom = self.zoom
                mundo_h = servico_mapa.gerenciador.mundo_tamanho_px()[1]
                min_zoom = max(float(jogo.TELA.get_height()) / max(1.0, float(mundo_h)), 0.05)
                self.zoom = max(min_zoom, min(self.zoom_max, self.zoom + (0.25 * ev.y)))
                if abs(self.zoom - old_zoom) > 1e-6:
                    self.offset[0] = mouse[0] - ((mouse[0] - self.offset[0]) * (self.zoom / old_zoom))
                    self.offset[1] = mouse[1] - ((mouse[1] - self.offset[1]) * (self.zoom / old_zoom))
                    self._cache_chave = None

        self._clamp_offset(jogo, servico_mapa)

    def _mundo_para_tela(self, pos):
        return (int(self.offset[0] + float(pos[0]) * self.zoom), int(self.offset[1] + float(pos[1]) * self.zoom))

    def desenhar(self, tela, jogo, eventos, dt, servico_mapa, estado_player: dict, pos_player_mundo, angulo_olhar: float = 0.0):
        _ = dt
        tela.fill((0, 0, 0))
        self.processar_eventos(jogo, eventos, servico_mapa)
        if not bool(getattr(servico_mapa, "pronto", False)):
            self._txt_loading.set_pos((tela.get_width() // 2, tela.get_height() // 2))
            self._txt_loading.draw(tela)
            for botao in self._botoes.values():
                botao.render(tela, eventos, 0.0, JOGO=jogo)
            return
        ger = servico_mapa.gerenciador
        mostrar_regioes = bool(self._botoes["Regiões"].estado)

        cam_rect = pygame.Rect(int(-self.offset[0] / self.zoom), int(-self.offset[1] / self.zoom), int(tela.get_width() / self.zoom) + 4, int(tela.get_height() / self.zoom) + 4)
        chave = (round(self.zoom, 3), int(self.offset[0]), int(self.offset[1]), mostrar_regioes, tuple((a.atlas_x, a.atlas_y, a.versao) for a in ger.all_atlas()))
        if self._cache_chave != chave:
            frame = pygame.Surface(tela.get_size())
            frame.fill((0, 0, 0))
            for atlas in ger.atlas_visiveis(cam_rect):
                src_surface = atlas.surface_regioes if mostrar_regioes else atlas.surface_base
                atlas_world = pygame.Rect(atlas.atlas_x * ger.atlas_px, atlas.atlas_y * ger.atlas_px, ger.atlas_px, ger.atlas_px)
                inter_world = atlas_world.clip(cam_rect)
                if inter_world.width <= 0 or inter_world.height <= 0:
                    continue
                src = pygame.Rect(inter_world.x - atlas_world.x, inter_world.y - atlas_world.y, inter_world.width, inter_world.height)
                dst = pygame.Rect(
                    int(self.offset[0] + inter_world.x * self.zoom),
                    int(self.offset[1] + inter_world.y * self.zoom),
                    max(1, int(inter_world.width * self.zoom)),
                    max(1, int(inter_world.height * self.zoom)),
                )
                sub = src_surface.subsurface(src).copy()
                escala = pygame.transform.smoothscale(sub, (dst.width, dst.height))
                frame.blit(escala, dst)
            self._cache_frame = frame
            self._cache_chave = chave

        if self._cache_frame is not None:
            tela.blit(self._cache_frame, (0, 0))
        largura_m, altura_m = ger.mundo_tamanho_px()
        borda = pygame.Rect(
            int(self.offset[0]),
            int(self.offset[1]),
            max(1, int(largura_m * self.zoom)),
            max(1, int(altura_m * self.zoom)),
        )
        pygame.draw.rect(tela, (190, 196, 212), borda, 2)

        if self._botoes["Vilas"].estado:
            for vila in servico_mapa.vilas:
                pos = vila.get("posicao")
                if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                    continue
                cx, cy = int(pos[0] // ger.chunk_blocos), int(pos[1] // ger.chunk_blocos)
                if not ger.chunk_explorado(cx, cy):
                    continue
                tx, ty = self._mundo_para_tela(pos)
                pygame.draw.circle(tela, (255, 255, 0), (tx, ty), 5)
                self._txt_poi.set_text(str(vila.get("nome") or "Vila"))
                self._txt_poi.set_pos((tx, ty - 18))
                self._txt_poi.draw(tela)

        if self._botoes["Estádios"].estado:
            for est in servico_mapa.estadios:
                pos = est.get("posicao")
                if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                    continue
                cx, cy = int(pos[0] // ger.chunk_blocos), int(pos[1] // ger.chunk_blocos)
                if not ger.chunk_explorado(cx, cy):
                    continue
                tx, ty = self._mundo_para_tela(pos)
                pygame.draw.circle(tela, (255, 70, 70), (tx, ty), 5)
                self._txt_poi.set_text(f"{est.get('tipo','Estádio')}")
                self._txt_poi.set_pos((tx, ty - 18))
                self._txt_poi.draw(tela)

        if mostrar_regioes:
            for reg in servico_mapa.regioes:
                centro = reg.get("centro") if isinstance(reg.get("centro"), (list, tuple)) and len(reg.get("centro")) == 2 else None
                if centro is None:
                    continue
                pos_label = tuple(centro)
                cx, cy = int(pos_label[0] // ger.chunk_blocos), int(pos_label[1] // ger.chunk_blocos)
                if not ger.chunk_explorado(cx, cy):
                    melhor = ger.ponto_explorado_regiao(int(reg.get("id", -1) or -1), preferencia=pos_player_mundo, area_visivel=cam_rect)
                    if melhor is None:
                        continue
                    pos_label = melhor
                tx, ty = self._mundo_para_tela(pos_label)
                self._txt_regiao.set_text(str(reg.get("nome") or "Região"))
                self._txt_regiao.set_pos((tx, ty))
                self._txt_regiao.draw(tela)

        tx, ty = self._mundo_para_tela(pos_player_mundo)
        angulo = float(angulo_olhar if angulo_olhar is not None else (estado_player.get("angulo", 0.0) if isinstance(estado_player, dict) else 0.0))
        desenhar_seta_player(tela, (tx, ty), angulo, tamanho=max(8, min(22, int(8 + (self.zoom * 2.0)))))

        for botao in self._botoes.values():
            botao.render(tela, eventos, 0.0, JOGO=jogo)

        tempo = pygame.time.get_ticks() - self.aberto_ms
        if tempo < self.fade_ms:
            alpha = int(255 * (1.0 - (tempo / self.fade_ms)))
            fade = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            fade.fill((0, 0, 0, alpha))
            tela.blit(fade, (0, 0))
