from __future__ import annotations

import pygame


class GeradorEstadio:
    """Renderizador manual do visual externo do estádio com cache por tipo/escala."""

    _cache: dict[tuple[str, int], pygame.Surface] = {}
    _CASCO_ESCALA_X = 0.90
    _CASCO_ESCALA_Y = 0.60

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

        casco = pygame.Rect(0, 0, int(w * cls._CASCO_ESCALA_X), int(h * cls._CASCO_ESCALA_Y)); casco.center = (centro[0], int(centro[1] - h * 0.02))
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
    def renderizar(cls, tela, camera, estado_estadio: dict | None = None) -> None:
        estado = estado_estadio if isinstance(estado_estadio, dict) else {}
        tile = float(getattr(camera, "TilePx", 50) or 50)

        largura = float(estado.get("largura_interna", 60.0) or 60.0)
        altura = float(estado.get("altura_interna", 40.0) or 40.0)
        centro = estado.get("arena_centro") if isinstance(estado.get("arena_centro"), (list, tuple)) and len(estado.get("arena_centro")) == 2 else [largura * 0.5, altura * 0.5]
        porta = estado.get("saida_interna_pos") if isinstance(estado.get("saida_interna_pos"), (list, tuple)) and len(estado.get("saida_interna_pos")) == 2 else [largura * 0.5, altura - 3.0]
        cor_a = (220, 233, 247)

        parede = pygame.Rect(0, 0, int(largura * tile), int(altura * tile))
        parede.topleft = tuple(map(int, camera.mundo_para_tela_px((0.0, 0.0))))
        espessura = max(6, int(tile * 0.42))
        pygame.draw.rect(tela, (54, 61, 77), parede, espessura, border_radius=max(10, int(tile * 0.2)))

        cx, cy = camera.mundo_para_tela_px((float(centro[0]), float(centro[1])))
        pw, ph = max(120, int(12 * tile)), max(90, int(7 * tile))
        arena = pygame.Rect(0, 0, pw, ph)
        arena.center = (int(cx), int(cy))
        pygame.draw.rect(tela, (202, 220, 238), arena, border_radius=max(8, int(tile * 0.18)))
        pygame.draw.rect(tela, (126, 156, 186), arena, max(3, int(tile * 0.12)), border_radius=max(8, int(tile * 0.18)))
        pygame.draw.line(tela, (242, 246, 250), (arena.left + 12, arena.centery), (arena.right - 12, arena.centery), max(2, int(tile * 0.08)))
        pygame.draw.circle(tela, (242, 246, 250), (arena.centerx, arena.centery), max(8, int(tile * 0.35)), max(2, int(tile * 0.08)))

        px, py = camera.mundo_para_tela_px((float(porta[0]), float(porta[1])))
        porta_rect = pygame.Rect(0, 0, max(18, int(tile * 0.9)), max(24, int(tile * 1.25)))
        porta_rect.midbottom = (int(px), int(py))
        recorte = pygame.Rect(porta_rect.left - 6, porta_rect.top - 2, porta_rect.width + 12, porta_rect.height + 8)
        pygame.draw.rect(tela, cor_a, recorte)
        pygame.draw.rect(tela, (42, 48, 60), porta_rect, border_radius=max(4, int(tile * 0.08)))
        pygame.draw.rect(tela, (124, 188, 255), porta_rect.inflate(-max(4, int(tile * 0.2)), -max(4, int(tile * 0.2))), border_radius=max(3, int(tile * 0.06)))
