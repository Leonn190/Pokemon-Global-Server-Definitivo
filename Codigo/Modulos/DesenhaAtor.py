import math
import pygame


def _cor_predominante(surface):
    amostra = pygame.transform.smoothscale(surface, (16, 16))
    soma_r = soma_g = soma_b = total = 0
    for y in range(amostra.get_height()):
        for x in range(amostra.get_width()):
            r, g, b, a = amostra.get_at((x, y))
            if a < 25:
                continue
            soma_r += r
            soma_g += g
            soma_b += b
            total += 1

    if total == 0:
        return (198, 236, 247)

    return (soma_r // total, soma_g // total, soma_b // total)


def _clarear_cor(cor, fator=0.35):
    """
    fator: 0.0 = original, 1.0 = branco
    """
    r, g, b = cor
    r = int(r + (255 - r) * fator)
    g = int(g + (255 - g) * fator)
    b = int(b + (255 - b) * fator)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


class DesenhaAtor:
    def __init__(self, skin_surface, escala=1.45):
        self.escala = float(escala)
        self.sprite_offset_graus = -90

        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

        # cor da mão: base + clareada (mais “fofinha”)
        base = _cor_predominante(self._skin_original)
        self._cor_maos = _clarear_cor(base, fator=0.40)

    def _redimensionar_skin(self, surf):
        w = max(1, int(surf.get_width() * self.escala))
        h = max(1, int(surf.get_height() * self.escala))
        return pygame.transform.smoothscale(surf, (w, h)).convert_alpha()

    def set_skin(self, skin_surface):
        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

        base = _cor_predominante(self._skin_original)
        self._cor_maos = _clarear_cor(base, fator=0.40)

    def set_escala(self, escala):
        self.escala = max(0.2, float(escala))
        self._skin = self._redimensionar_skin(self._skin_original)

    def desenhar(self, tela, centro, mouse_pos=None, angulo_graus=None, alcance_tapa=0.0):
        cx, cy = centro

        if angulo_graus is None:
            mx, my = mouse_pos if mouse_pos is not None else (cx + 1, cy)
            dx = mx - cx
            dy = my - cy
            if dx == 0 and dy == 0:
                dx = 1
            angulo_base = math.degrees(math.atan2(-dy, dx))
        else:
            angulo_base = float(angulo_graus)

        rad = math.radians(angulo_base)
        vx = math.cos(rad)
        vy = -math.sin(rad)

        # +180 pra não ficar de costas
        angulo = angulo_base + self.sprite_offset_graus + 180

        corpo = pygame.transform.rotate(self._skin, angulo)
        corpo_rect = corpo.get_rect(center=(int(cx), int(cy)))

        # perpendicular (lado a lado do olhar)
        px = -vy
        py = vx

        base = min(self._skin.get_width(), self._skin.get_height())

        raio_mao = max(5, int(base * 0.14))

        # MAIS ESPAÇADO:
        # - percentual maior
        # - +gap fixo em pixels pra nunca grudar
        dist_lateral = int(base * 0.76) + 7

        # micro ajuste vertical se quiser
        dist_vertical = int(base * 0.02)

        empurrao_tapa = max(0.0, float(alcance_tapa))
        mao_esq = (
            int(cx - px * dist_lateral + vx * empurrao_tapa),
            int(cy - py * dist_lateral + vy * empurrao_tapa - dist_vertical),
        )
        mao_dir = (int(cx + px * dist_lateral), int(cy + py * dist_lateral - dist_vertical))

        tela.blit(corpo, corpo_rect)

        contorno = (12, 20, 38)
        pygame.draw.circle(tela, contorno, mao_esq, raio_mao + 2)
        pygame.draw.circle(tela, contorno, mao_dir, raio_mao + 2)
        pygame.draw.circle(tela, self._cor_maos, mao_esq, raio_mao)
        pygame.draw.circle(tela, self._cor_maos, mao_dir, raio_mao)

        return {
            "mao_tapa": mao_esq,
            "mao_apoio": mao_dir,
            "raio_mao": raio_mao,
        }
