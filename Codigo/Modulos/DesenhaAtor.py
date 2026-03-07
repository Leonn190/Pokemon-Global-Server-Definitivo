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
    r, g, b = cor
    r = int(r + (255 - r) * fator)
    g = int(g + (255 - g) * fator)
    b = int(b + (255 - b) * fator)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


class DesenhaAtor:
    def __init__(self, skin_surface, escala=1.0, tile_px=50):
        self._escala_tiles = float(escala)
        self._tile_px = max(1, int(tile_px))
        self._largura_tiles = 1.75
        self._altura_tiles = 1.2
        self.sprite_offset_graus = -90

        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

        base = _cor_predominante(self._skin_original)
        self._cor_maos = _clarear_cor(base, fator=0.40)
        self._cache_corpo_rotacionado = {}
        self._cache_ordem_angulos = []
        self._cache_limite_angulos = 120

    def _redimensionar_skin(self, surf):
        largura = max(1, int(self._tile_px * self._largura_tiles * self._escala_tiles))
        altura = max(1, int(self._tile_px * self._altura_tiles * self._escala_tiles))
        return pygame.transform.smoothscale(surf, (largura, altura)).convert_alpha()

    def set_skin(self, skin_surface):
        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

        base = _cor_predominante(self._skin_original)
        self._cor_maos = _clarear_cor(base, fator=0.40)
        self._cache_corpo_rotacionado.clear()
        self._cache_ordem_angulos.clear()

    def set_escala(self, escala):
        self._escala_tiles = max(0.2, float(escala))
        self._skin = self._redimensionar_skin(self._skin_original)
        self._cache_corpo_rotacionado.clear()
        self._cache_ordem_angulos.clear()

    def set_tile_px(self, tile_px):
        tile_px = max(1, int(tile_px))
        if tile_px == self._tile_px:
            return
        self._tile_px = tile_px
        self._skin = self._redimensionar_skin(self._skin_original)
        self._cache_corpo_rotacionado.clear()
        self._cache_ordem_angulos.clear()

    def _obter_corpo_rotacionado(self, angulo: float):
        chave = int(round(float(angulo) * 0.5) * 2) % 360
        corpo = self._cache_corpo_rotacionado.get(chave)
        if corpo is not None:
            return corpo

        corpo = pygame.transform.rotate(self._skin, chave)
        self._cache_corpo_rotacionado[chave] = corpo
        self._cache_ordem_angulos.append(chave)
        if len(self._cache_ordem_angulos) > self._cache_limite_angulos:
            antigo = self._cache_ordem_angulos.pop(0)
            self._cache_corpo_rotacionado.pop(antigo, None)
        return corpo

    def desenhar(self, tela, centro, mouse_pos=None, angulo_graus=None, alcance_tapa=0.0, progresso_tapa=0.0, respiracao_tempo=0.0):
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

        angulo = angulo_base + self.sprite_offset_graus + 180

        corpo = self._obter_corpo_rotacionado(angulo)
        corpo_rect = corpo.get_rect(center=(int(cx), int(cy)))

        px = -vy
        py = vx

        base = float(self._tile_px)
        raio_mao = max(5, int(base * 0.20 * max(1.0, self._escala_tiles)))
        dist_lateral = int(base * 0.78 * max(1.0, self._escala_tiles))
        dist_vertical = int(base * 0.03 * max(1.0, self._escala_tiles))

        progresso = max(0.0, min(1.0, float(progresso_tapa)))
        empurrao_tapa = max(0.0, float(alcance_tapa))
        respiracao = math.sin(max(0.0, float(respiracao_tempo)) * 3.4) * 3.0

        mao_dir_base_x = cx + px * dist_lateral
        mao_dir_base_y = cy + py * dist_lateral - dist_vertical
        mao_esq_base_x = cx - px * dist_lateral
        mao_esq_base_y = cy - py * dist_lateral - dist_vertical

        if empurrao_tapa > 0.0:
            arco = math.sin(progresso * math.pi)
            curva_frente = 60.0 * arco
            curva_esquerda = 15.0 * arco
            mao_dir_x = mao_dir_base_x + vx * curva_frente - px * curva_esquerda
            mao_dir_y = mao_dir_base_y + vy * curva_frente - py * curva_esquerda
        else:
            mao_dir_x = mao_dir_base_x + vx * respiracao
            mao_dir_y = mao_dir_base_y + vy * respiracao

        mao_esq_x = mao_esq_base_x + vx * respiracao
        mao_esq_y = mao_esq_base_y + vy * respiracao

        mao_dir = (int(mao_dir_x), int(mao_dir_y))
        mao_esq = (int(mao_esq_x), int(mao_esq_y))

        tela.blit(corpo, corpo_rect)

        contorno = (12, 20, 38)
        pygame.draw.circle(tela, contorno, mao_esq, raio_mao + 2)
        pygame.draw.circle(tela, contorno, mao_dir, raio_mao + 2)
        pygame.draw.circle(tela, self._cor_maos, mao_esq, raio_mao)
        pygame.draw.circle(tela, self._cor_maos, mao_dir, raio_mao)

        return {
            "mao_tapa": mao_dir,
            "mao_apoio": mao_esq,
            "raio_mao": raio_mao,
        }
