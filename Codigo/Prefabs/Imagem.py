import pygame
import math


def _clamp(v, a, b):
    return a if v < a else b if v > b else v


class Imagem:
    """
    Imagem com efeito "brilho em ondas" (sweep) para logos/banners.
    Use: img.draw(TELA, dt)
    """

    def __init__(
        self,
        surface: pygame.Surface,
        pos=(0, 0),
        align="center",          # topleft, center, midtop etc.
        scale=None,              # (w,h) ou None
        efeito=True,
        duracao=2.2,             # segundos por ciclo
        largura_faixa=0.28,      # 0..1 (largura do brilho relativo ao tamanho)
        intensidade=0.9,         # 0..1 (força do brilho)
        angulo_graus=-20,        # direção do brilho
        alpha_base=140,          # alpha máximo do brilho (0..255)
    ):
        self.base = surface.convert_alpha()
        self.pos = pos
        self.align = align

        if scale is not None:
            self.base = pygame.transform.smoothscale(self.base, scale).convert_alpha()

        self.efeito = efeito
        self.duracao = max(0.2, float(duracao))
        self.largura_faixa = _clamp(float(largura_faixa), 0.05, 0.8)
        self.intensidade = _clamp(float(intensidade), 0.0, 1.0)
        self.angulo_graus = float(angulo_graus)
        self.alpha_base = int(_clamp(alpha_base, 0, 255))

        self._t = 0.0
        self._mask_cache = {}  # key -> Surface (cache por w,h,angulo,largura)

    def set_pos(self, pos):
        self.pos = pos

    def get_rect(self):
        r = self.base.get_rect()
        setattr(r, self.align, self.pos)
        return r

    def _get_shine_mask(self, w, h):
        # cache key
        key = (w, h, int(self.angulo_graus), round(self.largura_faixa, 3))
        if key in self._mask_cache:
            return self._mask_cache[key]

        # máscara grande para permitir rotacionar sem cortar
        diag = int(math.hypot(w, h))
        mw, mh = diag, diag

        mask = pygame.Surface((mw, mh), pygame.SRCALPHA)

        # cria gradiente 1D horizontal (faixa) e "espalha" na máscara
        # a faixa tem centro branco e bordas transparentes
        faixa_w = max(10, int(mw * self.largura_faixa))
        grad = pygame.Surface((faixa_w, mh), pygame.SRCALPHA)

        # gradiente manual (rápido e simples)
        for x in range(faixa_w):
            # 0..1..0
            p = x / max(1, faixa_w - 1)
            tri = 1.0 - abs(2.0 * p - 1.0)
            a = int(self.alpha_base * tri)
            grad.fill((255, 255, 255, a), rect=pygame.Rect(x, 0, 1, mh))

        # cola gradiente no meio
        mask.blit(grad, ((mw - faixa_w) // 2, 0))

        # rotaciona
        if self.angulo_graus != 0:
            mask = pygame.transform.rotate(mask, self.angulo_graus).convert_alpha()

        self._mask_cache[key] = mask
        return mask

    def draw(self, tela: pygame.Surface, dt: float):
        # desenha imagem base
        rect = self.get_rect()
        tela.blit(self.base, rect.topleft)

        if not self.efeito:
            return

        # avança tempo (ciclo)
        self._t = (self._t + dt) % self.duracao
        phase = self._t / self.duracao  # 0..1

        w, h = self.base.get_size()

        # máscara
        mask = self._get_shine_mask(w, h)

        # posição do brilho: varre da esquerda pra direita (fora -> dentro -> fora)
        # usamos o tamanho da máscara pra garantir varredura completa
        mw, mh = mask.get_size()
        # deslocamento vai de -mw..+mw
        x = int((-mw) + (2 * mw) * phase)
        y = int((h // 2) - (mh // 2))

        # cria uma surface do tamanho da imagem para recortar a parte visível do brilho
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        # desenha máscara no overlay (com offset animado)
        overlay.blit(mask, (x, y))

        # aplica intensidade (multiplica alpha)
        if self.intensidade < 1.0:
            # reduz alpha geral do overlay
            overlay.set_alpha(int(255 * self.intensidade))

        # recorta brilho só onde a imagem tem pixels (usa alpha da imagem como máscara)
        # BLEND_RGBA_MULT: multiplica RGBA (mantém transparente fora da imagem)
        overlay.blit(self.base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # soma brilho por cima (fica bonito)
        tela.blit(overlay, rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)