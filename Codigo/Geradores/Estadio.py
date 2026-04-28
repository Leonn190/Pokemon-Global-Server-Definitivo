from __future__ import annotations

import pygame


class GeradorEstadio:
    """Renderizador manual do visual externo do estádio com cache por tipo/escala."""

    _cache: dict[tuple[str, int], pygame.Surface] = {}
    _CASCO_ESCALA_X = 0.90
    _CASCO_ESCALA_Y = 0.60
    _CASCO_DESLOCAMENTO_Y = -0.02

    @classmethod
    def _cor_tipo(cls, tipo: str) -> tuple[int, int, int]:
        paleta = {
            "normal": (187, 176, 151),
            "fogo": (219, 106, 72),
            "agua": (80, 130, 219),
            "planta": (86, 171, 90),
            "eletrico": (224, 199, 61),
            "gelo": (152, 208, 225),
            "lutador": (168, 89, 71),
            "venenoso": (147, 92, 180),
            "terra": (164, 132, 73),
            "voador": (133, 168, 205),
            "psiquico": (217, 104, 146),
            "inseto": (140, 164, 63),
            "pedra": (128, 121, 107),
            "fantasma": (96, 90, 143),
            "dragao": (87, 97, 191),
            "sombrio": (86, 77, 76),
            "metal": (132, 145, 157),
            "fada": (220, 154, 196),
            "cosmico": (102, 105, 176),
            "sonoro": (198, 123, 219),
        }
        return paleta.get(str(tipo or "").strip().lower(), (170, 170, 170))

    @classmethod
    def obter_superficie(cls, tipo: str, tile_px: float, raio_x: float = 24.0, raio_y: float = 24.0) -> pygame.Surface:
        rx = max(8.0, float(raio_x))
        ry = max(8.0, float(raio_y))
        escala_x = max(64, int(tile_px * (rx * 2.0)))
        escala_y = max(64, int(tile_px * (ry * 2.0)))
        chave = (str(tipo or "normal").lower(), escala_x, escala_y)
        pronta = cls._cache.get(chave)
        if pronta is not None:
            return pronta

        w, h = int(escala_x), int(escala_y)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        centro = (w // 2, h // 2)
        base = cls._cor_tipo(tipo)

        sombra = pygame.Rect(0, 0, int(w * 0.96), int(h * 0.65)); sombra.center = (centro[0], int(centro[1] + h * 0.12))
        pygame.draw.ellipse(surf, (0, 0, 0, 70), sombra)

        casco = pygame.Rect(0, 0, int(w * cls._CASCO_ESCALA_X), int(h * cls._CASCO_ESCALA_Y)); casco.center = (centro[0], int(centro[1] + h * cls._CASCO_DESLOCAMENTO_Y))
        pygame.draw.ellipse(surf, (60, 60, 70), casco, width=max(3, int(min(w, h) * 0.06)))

        anel = casco.inflate(-int(w * 0.18), -int(h * 0.16))
        pygame.draw.ellipse(surf, (230, 238, 248), anel)

        campo = anel.inflate(-int(w * 0.22), -int(h * 0.20))
        pygame.draw.ellipse(surf, base, campo)
        pygame.draw.line(surf, (240, 240, 240), (campo.left + 8, campo.centery), (campo.right - 8, campo.centery), max(1, int(min(w, h) * 0.03)))
        pygame.draw.line(surf, (240, 240, 240), (campo.centerx, campo.top + 6), (campo.centerx, campo.bottom - 6), max(1, int(min(w, h) * 0.025)))

        porta = pygame.Rect(0, 0, int(w * 0.10), int(h * 0.18)); porta.midbottom = (centro[0], casco.bottom - 2)
        pygame.draw.rect(surf, (92, 92, 104), porta, border_radius=max(3, int(min(w, h) * 0.02)))
        pygame.draw.rect(surf, (54, 54, 64), porta, width=max(1, int(min(w, h) * 0.015)), border_radius=max(3, int(min(w, h) * 0.02)))

        cls._cache[chave] = surf
        return surf

    @classmethod
    def raios_casco_colisao(cls, raio_x: float, raio_y: float) -> tuple[float, float]:
        """Raio elíptico do casco externo desenhado manualmente (em tiles)."""
        rx = max(2.0, float(raio_x) * cls._CASCO_ESCALA_X)
        ry = max(2.0, float(raio_y) * cls._CASCO_ESCALA_Y)
        return (rx, ry)

    @classmethod
    def deslocamento_casco_colisao(cls, raio_y: float) -> tuple[float, float]:
        """Deslocamento do centro do casco externo em tiles."""
        ry = max(2.0, float(raio_y))
        return (0.0, (2.0 * ry) * cls._CASCO_DESLOCAMENTO_Y)

    @classmethod
    def offset_porta_externa(cls, raio_y: float) -> tuple[float, float]:
        """Offset da porta externa real em relaÃ§Ã£o ao centro do estÃ¡dio."""
        ry = max(2.0, float(raio_y))
        _, off_casco_y = cls.deslocamento_casco_colisao(ry)
        return (0.0, off_casco_y + (ry * cls._CASCO_ESCALA_Y))

    @classmethod
    def renderizar(cls, tela, camera, payload: dict) -> None:
        pos = payload.get("posicao") if isinstance(payload, dict) else None
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        tipo = str(estado.get("tipo_estadio") or "normal")
        rx = float(estado.get("raio_elipse_x", 24.0) or 24.0)
        ry = float(estado.get("raio_elipse_y", 24.0) or 24.0)
        img = cls.obter_superficie(tipo=tipo, tile_px=float(getattr(camera, "TilePx", 50)), raio_x=rx, raio_y=ry)
        rect = img.get_rect(center=(int(px), int(py)))
        tela.blit(img, rect)


class EstadioInterno:
    """Desenhos internos padronizados para qualquer dimensão de estádio."""


    @classmethod
    def contexto_batalha(cls, estado_estadio: dict | None = None) -> dict:
        estado = estado_estadio if isinstance(estado_estadio, dict) else {}
        largura = 80
        altura = 40
        arena_largura = 40
        arena_altura = 20
        centro = [largura * 0.5, altura * 0.5]
        return {
            "origem": [0.0, 0.0],
            "centro": centro,
            "largura": largura,
            "altura": altura,
            "arena_largura": arena_largura,
            "arena_altura": arena_altura,
            "tiles": [],
            "estruturas": [],
            "contexto_estadio": True,
            "tipo_estadio": str(estado.get("tipo_estadio") or "normal"),
        }
    @classmethod
    def renderizar(cls, tela, camera, estado_estadio: dict | None = None) -> None:
        estado = estado_estadio if isinstance(estado_estadio, dict) else {}
        tile = float(getattr(camera, "TilePx", 50) or 50)

        largura = float(estado.get("largura_interna", 60.0) or 60.0)
        altura = float(estado.get("altura_interna", 40.0) or 40.0)
        centro = (
            estado.get("arena_centro")
            if isinstance(estado.get("arena_centro"), (list, tuple)) and len(estado.get("arena_centro")) == 2
            else [largura * 0.5, altura * 0.5]
        )
        porta = (
            estado.get("saida_interna_pos")
            if isinstance(estado.get("saida_interna_pos"), (list, tuple)) and len(estado.get("saida_interna_pos")) == 2
            else [largura * 0.5, altura - 2.0]
        )

        def px(v: float) -> int:
            return max(1, int(v * tile))

        def tela_px(pos):
            x, y = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
            return int(x), int(y)

        def clarear(cor: tuple[int, int, int], fator: float) -> tuple[int, int, int]:
            fator_l = max(0.0, min(1.0, float(fator)))
            return (
                int(cor[0] + (255 - cor[0]) * fator_l),
                int(cor[1] + (255 - cor[1]) * fator_l),
                int(cor[2] + (255 - cor[2]) * fator_l),
            )

        # Paleta
        tipo = str(estado.get("tipo_estadio") or "normal")
        cor_base_tipo = GeradorEstadio._cor_tipo(tipo)
        cor_chao_a = clarear(cor_base_tipo, 0.66)
        cor_chao_b = clarear(cor_base_tipo, 0.78)
        cor_parede = (54, 61, 77)
        cor_arena = (222, 232, 244)
        cor_arena_borda = (120, 150, 184)
        cor_arena_sombra = (160, 178, 198)
        cor_arena_centro = (245, 248, 252)
        cor_linha = (242, 246, 250)

        cor_porta_moldura = (44, 50, 64)
        cor_porta_arco = (68, 79, 100)
        cor_porta_luz = (115, 185, 255)
        cor_porta_luz_2 = (190, 230, 255)

        cor_corredor = (184, 198, 216)
        cor_corredor_borda = (132, 150, 174)

        # Moldura externa da sala
        sala = pygame.Rect(0, 0, int(largura * tile), int(altura * tile))
        sala.topleft = tela_px((0.0, 0.0))
        espessura = max(6, px(0.42))
        piso = sala.inflate(-espessura * 2, -espessura * 2)
        passo = max(8, px(1.0))
        for y in range(piso.top, piso.bottom, passo):
            linha = (y - piso.top) // passo
            for x in range(piso.left, piso.right, passo):
                coluna = (x - piso.left) // passo
                cor_tile = cor_chao_a if (linha + coluna) % 2 == 0 else cor_chao_b
                pygame.draw.rect(tela, cor_tile, (x, y, passo, passo))
        pygame.draw.rect(
            tela,
            cor_parede,
            sala,
            espessura,
            border_radius=max(12, px(0.22)),
        )

        # Arena principal
        cx, cy = tela_px((float(centro[0]), float(centro[1])))

        arena_w = max(px(18), int(12 * tile))
        arena_h = max(px(10), int(7.5 * tile))
        arena = pygame.Rect(0, 0, arena_w, arena_h)
        arena.center = (cx, cy)

        # Sombra da arena
        arena_sombra = arena.inflate(px(1.0), px(0.9))
        arena_sombra.y += px(0.16)
        pygame.draw.rect(
            tela,
            cor_arena_sombra,
            arena_sombra,
            border_radius=max(18, px(0.30)),
        )

        # Corpo da arena
        pygame.draw.rect(
            tela,
            cor_arena,
            arena,
            border_radius=max(18, px(0.30)),
        )
        pygame.draw.rect(
            tela,
            cor_arena_borda,
            arena,
            max(3, px(0.10)),
            border_radius=max(18, px(0.30)),
        )

        # Campo interno
        campo = arena.inflate(-px(2.0), -px(1.7))
        pygame.draw.rect(
            tela,
            cor_arena_centro,
            campo,
            border_radius=max(14, px(0.22)),
        )

        # Linha central
        pygame.draw.line(
            tela,
            cor_linha,
            (campo.left + px(0.35), campo.centery),
            (campo.right - px(0.35), campo.centery),
            max(2, px(0.08)),
        )

        # Símbolo central estilo batalha/pokebola
        raio_centro = max(12, px(0.60))
        pygame.draw.circle(
            tela,
            cor_linha,
            (campo.centerx, campo.centery),
            raio_centro,
            max(2, px(0.08)),
        )
        pygame.draw.circle(
            tela,
            cor_linha,
            (campo.centerx, campo.centery),
            max(3, px(0.12)),
        )

        # Marcas laterais de posição
        raio_lateral = max(10, px(0.42))
        dist_lateral = int(campo.width * 0.27)
        for sx in (-1, 1):
            bx = campo.centerx + sx * dist_lateral
            by = campo.centery
            pygame.draw.circle(tela, (232, 238, 246), (bx, by), raio_lateral)
            pygame.draw.circle(tela, cor_arena_borda, (bx, by), raio_lateral, max(2, px(0.08)))

        # Porta
        px_porta, py_porta = tela_px((float(porta[0]), float(porta[1])))

        # Corredor da porta ate a arena
        corredor_top = arena.bottom - px(0.2)
        corredor_bottom = py_porta - px(0.55)  # desenhado antes da porta
        if corredor_bottom > corredor_top:
            corredor_w = max(px(2.0), int(arena.width * 0.16))
            corredor = pygame.Rect(0, 0, corredor_w, corredor_bottom - corredor_top)
            corredor.midtop = (px_porta, corredor_top)

            pygame.draw.rect(
                tela,
                cor_corredor,
                corredor,
                border_radius=max(8, px(0.16)),
            )
            pygame.draw.rect(
                tela,
                cor_corredor_borda,
                corredor,
                max(2, px(0.07)),
                border_radius=max(8, px(0.16)),
            )

        porta_w = max(px(1.7), 34)
        porta_h = max(px(2.4), 52)

        porta_externa = pygame.Rect(0, 0, porta_w, porta_h)
        porta_externa.midbottom = (px_porta, py_porta)

        pygame.draw.rect(
            tela,
            cor_porta_moldura,
            porta_externa,
            border_radius=max(8, px(0.16)),
        )

        # Arco da porta
        arco = pygame.Rect(
            porta_externa.left - px(0.15),
            porta_externa.top - px(0.75),
            porta_externa.width + px(0.3),
            max(px(1.0), int(porta_externa.height * 0.62)),
        )
        pygame.draw.ellipse(tela, cor_porta_arco, arco)
        pygame.draw.ellipse(tela, cor_porta_moldura, arco, max(2, px(0.07)))

        # Centro luminoso
        porta_interna = porta_externa.inflate(-px(0.42), -px(0.42))
        pygame.draw.rect(
            tela,
            cor_porta_luz,
            porta_interna,
            border_radius=max(6, px(0.12)),
        )

        brilho = porta_interna.inflate(-px(0.45), -px(0.55))
        if brilho.width > 4 and brilho.height > 4:
            pygame.draw.rect(
                tela,
                cor_porta_luz_2,
                brilho,
                border_radius=max(4, px(0.08)),
            )

        # Faixa superior da porta
        faixa_topo = pygame.Rect(
            porta_externa.left - px(0.25),
            porta_externa.top - px(0.22),
            porta_externa.width + px(0.5),
            max(6, px(0.24)),
        )
        pygame.draw.rect(
            tela,
            (88, 100, 124),
            faixa_topo,
            border_radius=max(4, px(0.08)),
        )

        # Luzes pequenas laterais
        luz_r = max(3, px(0.10))
        pygame.draw.circle(tela, (255, 214, 95), (porta_externa.left + px(0.22), porta_externa.top + px(0.34)), luz_r)
        pygame.draw.circle(tela, (255, 214, 95), (porta_externa.right - px(0.22), porta_externa.top + px(0.34)), luz_r)

        # Corredor da porta até a arena
        corredor_top = arena.bottom - px(0.2)
        corredor_bottom = min(py_porta - px(0.55), arco.top - px(0.08))
        if corredor_bottom > corredor_top:
            corredor_w = max(px(2.0), int(arena.width * 0.16))
            corredor = pygame.Rect(0, 0, corredor_w, corredor_bottom - corredor_top)
            corredor.midtop = (px_porta, corredor_top)

            pygame.draw.rect(
                tela,
                cor_corredor,
                corredor,
                border_radius=max(8, px(0.16)),
            )
            pygame.draw.rect(
                tela,
                cor_corredor_borda,
                corredor,
                max(2, px(0.07)),
                border_radius=max(8, px(0.16)),
            )
