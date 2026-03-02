import pygame
import math


def _clamp(v, a, b):
    return a if v < a else b if v > b else v


class Imagem:
    """
    Imagem com efeito vibrante suave usando máscara do ícone.
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
        largura_faixa=0.28,      # mantido por compatibilidade
        intensidade=0.9,         # 0..1 (força do efeito de cor)
        angulo_graus=-20,        # mantido por compatibilidade
        alpha_base=140,          # mantido por compatibilidade
    ):
        self.base = surface.convert_alpha()
        self.pos = pos
        self.align = align

        if scale is not None:
            self.base = pygame.transform.smoothscale(self.base, scale).convert_alpha()

        self.efeito = efeito
        self.duracao = max(0.4, float(duracao))
        self.intensidade = _clamp(float(intensidade), 0.0, 1.0)

        self._t = 0.0
        self._mask_cache = {}

        # parâmetros do efeito (usando máscara do ícone, não brilho reflexivo)
        self._saturacao_amp = 0.06
        self._luminosidade_amp = 0.08
        self._r_amp = 0.035
        self._g_amp = 0.025
        self._b_amp = 0.04

    def set_pos(self, pos):
        self.pos = pos

    def get_rect(self):
        r = self.base.get_rect()
        setattr(r, self.align, self.pos)
        return r

    def _get_alpha_mask(self, size):
        if size in self._mask_cache:
            return self._mask_cache[size]

        w, h = size
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        alpha = pygame.surfarray.array_alpha(self.base)
        rgb = pygame.surfarray.pixels3d(mask)
        rgb[:, :, :] = 255
        del rgb
        alpha_target = pygame.surfarray.pixels_alpha(mask)
        alpha_target[:, :] = alpha[:, :]
        del alpha_target

        self._mask_cache[size] = mask
        return mask

    def _modular_cor(self, base_surf, phase):
        overlay = pygame.Surface(base_surf.get_size(), pygame.SRCALPHA)

        sat_wave = 1.0 + self._saturacao_amp * math.sin(phase)
        lum_wave = 1.0 + self._luminosidade_amp * math.sin(phase * 1.43 + 0.6)
        r_wave = 1.0 + self._r_amp * math.sin(phase * 1.1)
        g_wave = 1.0 + self._g_amp * math.sin(phase * 1.9 + 1.2)
        b_wave = 1.0 + self._b_amp * math.sin(phase * 1.6 + 2.1)

        pulse_color = (
            int(255 * _clamp(lum_wave * sat_wave * r_wave, 0.85, 1.22)),
            int(255 * _clamp(lum_wave * sat_wave * g_wave, 0.85, 1.20)),
            int(255 * _clamp(lum_wave * sat_wave * b_wave, 0.85, 1.24)),
            int(80 * self.intensidade),
        )
        overlay.fill(pulse_color)

        mask = self._get_alpha_mask(base_surf.get_size())
        overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return overlay

    def draw(self, tela: pygame.Surface, dt: float):
        rect = self.get_rect()
        tela.blit(self.base, rect.topleft)

        if not self.efeito:
            return

        self._t = (self._t + dt) % self.duracao
        phase = (self._t / self.duracao) * (2.0 * math.pi)

        overlay = self._modular_cor(self.base, phase)
        tela.blit(overlay, rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)
