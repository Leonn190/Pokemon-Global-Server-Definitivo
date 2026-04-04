from __future__ import annotations

import pygame


class GeradorEstadio:
    """Renderizador manual do visual externo do estádio com cache por tipo/escala."""

    _cache: dict[tuple[str, int], pygame.Surface] = {}

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

        casco = pygame.Rect(0, 0, int(w * 0.9), int(h * 0.6)); casco.center = (centro[0], int(centro[1] - h * 0.02))
        pygame.draw.ellipse(surf, (60, 60, 70), casco, width=max(3, int(min(w, h) * 0.06)))

        anel = casco.inflate(-int(w * 0.18), -int(h * 0.16))
        pygame.draw.ellipse(surf, (205, 208, 216), anel)

        campo = anel.inflate(-int(w * 0.24), -int(h * 0.22))
        pygame.draw.ellipse(surf, base, campo)
        pygame.draw.line(surf, (240, 240, 240), (campo.left + 8, campo.centery), (campo.right - 8, campo.centery), max(1, int(min(w, h) * 0.03)))
        pygame.draw.line(surf, (240, 240, 240), (campo.centerx, campo.top + 6), (campo.centerx, campo.bottom - 6), max(1, int(min(w, h) * 0.025)))

        porta = pygame.Rect(0, 0, int(w * 0.10), int(h * 0.18)); porta.midbottom = (centro[0], casco.bottom - 2)
        pygame.draw.rect(surf, (34, 34, 40), porta, border_radius=max(3, int(min(w, h) * 0.02)))

        cls._cache[chave] = surf
        return surf

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
