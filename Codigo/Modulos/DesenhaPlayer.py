import math
import pygame


class DesenhaPlayer:
    def __init__(self, skin_surface, escala=3.0):
        self.escala = float(escala)
        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

    def _redimensionar_skin(self, surf):
        largura = max(1, int(surf.get_width() * self.escala))
        altura = max(1, int(surf.get_height() * self.escala))
        return pygame.transform.smoothscale(surf, (largura, altura)).convert_alpha()

    def set_skin(self, skin_surface):
        self._skin_original = skin_surface.convert_alpha()
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

        mag = math.hypot(dx, dy)
        vx = dx / mag
        vy = dy / mag

        px = -vy
        py = vx

        raio_braco = max(8, int(min(self._skin.get_width(), self._skin.get_height()) * 0.14))
        dist_lateral = int(raio_braco * 2.1)

        braco_esq = (int(cx - px * dist_lateral), int(cy - py * dist_lateral))
        braco_dir = (int(cx + px * dist_lateral), int(cy + py * dist_lateral))

        pygame.draw.circle(tela, (9, 43, 58), braco_esq, raio_braco + 2)
        pygame.draw.circle(tela, (9, 43, 58), braco_dir, raio_braco + 2)
        pygame.draw.circle(tela, (198, 236, 247), braco_esq, raio_braco)
        pygame.draw.circle(tela, (198, 236, 247), braco_dir, raio_braco)

        tela.blit(corpo, corpo_rect)
