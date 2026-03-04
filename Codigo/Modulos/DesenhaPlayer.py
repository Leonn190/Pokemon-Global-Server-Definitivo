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


class DesenhaPlayer:
    def __init__(self, skin_surface, escala=2.4):
        self.escala = float(escala)
        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)
        self._cor_maos = _cor_predominante(self._skin_original)

    def _redimensionar_skin(self, surf):
        largura = max(1, int(surf.get_width() * self.escala))
        altura = max(1, int(surf.get_height() * self.escala))
        return pygame.transform.smoothscale(surf, (largura, altura)).convert_alpha()

    def set_skin(self, skin_surface):
        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)
        self._cor_maos = _cor_predominante(self._skin_original)

    def set_escala(self, escala):
        self.escala = max(0.2, float(escala))
        self._skin = self._redimensionar_skin(self._skin_original)

    def desenhar(self, tela, centro, mouse_pos):
        cx, cy = centro
        mx, my = mouse_pos

        dx = mx - cx
        dy = my - cy
        if dx == 0 and dy == 0:
            dx = 1

        angulo = math.degrees(math.atan2(-dy, dx))

        corpo = pygame.transform.rotate(self._skin, angulo)
        corpo_rect = corpo.get_rect(center=(int(cx), int(cy)))

        mag = max(1e-6, math.hypot(dx, dy))
        vx = dx / mag
        vy = dy / mag

        px = -vy
        py = vx

        base = min(self._skin.get_width(), self._skin.get_height())
        raio_mao = max(6, int(base * 0.12))
        dist_lateral = int(base * 0.42)

        mao_esq = (int(cx - px * dist_lateral), int(cy - py * dist_lateral))
        mao_dir = (int(cx + px * dist_lateral), int(cy + py * dist_lateral))

        pygame.draw.circle(tela, (12, 20, 38), mao_esq, raio_mao + 2)
        pygame.draw.circle(tela, (12, 20, 38), mao_dir, raio_mao + 2)
        pygame.draw.circle(tela, self._cor_maos, mao_esq, raio_mao)
        pygame.draw.circle(tela, self._cor_maos, mao_dir, raio_mao)

        tela.blit(corpo, corpo_rect)
