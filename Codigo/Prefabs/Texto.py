import pygame
from pathlib import Path

CAMINHO_FONTE_PADRAO = Path("Recursos/Visual/Fontes/FontePadrão.ttf")

class Texto:
    """
    Texto estilo "CSS":
    - style dict (cor, size, align, outline, highlight, etc.)
    - sempre usa FontePadrão.ttf
    - suporta contorno (outline) e fundo grifado (highlight)
    """

    DEFAULT_STYLE = {
        "size": 24,
        "color": (255, 255, 255),
        "align": "topleft",  # topleft, center, midtop, etc.

        # outline
        "outline": True,
        "outline_color": (0, 0, 0),
        "outline_thickness": 2,

        # highlight (fundo grifado)
        "highlight": False,
        "highlight_color": (255, 235, 80, 200),  # RGBA
        "highlight_padding": (8, 4),  # (x, y)
        "highlight_radius": 10,

        # sombra simples (opcional, ajuda a ficar bonito)
        "shadow": False,
        "shadow_color": (0, 0, 0, 160),
        "shadow_offset": (2, 2),
    }

    def __init__(self, text: str, pos=(0, 0), style=None):
        self.text = text
        self.pos = pos
        self.style = dict(self.DEFAULT_STYLE)
        if style:
            self.style.update(style)

        self._font = None
        self._cache = None
        self._cache_key = None

        self._load_font()

    def _load_font(self):
        self._font = pygame.font.Font(str(CAMINHO_FONTE_PADRAO), int(self.style["size"]))
        self._invalidate()

    def _invalidate(self):
        self._cache = None
        self._cache_key = None

    # --- API estilo CSS ---
    def set_style(self, **kwargs):
        size_before = int(self.style["size"])
        self.style.update(kwargs)
        if int(self.style["size"]) != size_before:
            self._load_font()
        else:
            self._invalidate()

    def set_text(self, text: str):
        if text != self.text:
            self.text = text
            self._invalidate()

    def set_pos(self, pos):
        self.pos = pos

    def _render_text_surface(self, text, color):
        return self._font.render(text, True, color)

    def _render(self):
        key = (self.text, tuple(sorted(self.style.items())))
        if self._cache_key == key and self._cache is not None:
            return self._cache

        st = self.style

        # texto base
        base = self._render_text_surface(self.text, st["color"]).convert_alpha()
        w, h = base.get_size()

        # outline
        pad_outline = int(st["outline_thickness"]) if st["outline"] else 0

        # highlight padding
        hp_x, hp_y = st["highlight_padding"]
        pad_high_x = hp_x if st["highlight"] else 0
        pad_high_y = hp_y if st["highlight"] else 0

        # sombra
        shadow = st["shadow"]
        sh_x, sh_y = st["shadow_offset"] if shadow else (0, 0)

        pad_total_x = pad_outline + pad_high_x + abs(sh_x)
        pad_total_y = pad_outline + pad_high_y + abs(sh_y)

        surf = pygame.Surface((w + pad_total_x * 2, h + pad_total_y * 2), pygame.SRCALPHA)

        # highlight (fundo grifado) — desenha antes de tudo
        if st["highlight"]:
            rect = pygame.Rect(
                pad_total_x - pad_high_x,
                pad_total_y - pad_high_y,
                w + pad_high_x * 2,
                h + pad_high_y * 2,
            )
            pygame.draw.rect(
                surf,
                st["highlight_color"],
                rect,
                border_radius=int(st["highlight_radius"]),
            )

        # sombra (opcional)
        if shadow:
            shadow_surf = self._render_text_surface(self.text, st["shadow_color"]).convert_alpha()
            surf.blit(shadow_surf, (pad_total_x + sh_x, pad_total_y + sh_y))

        # outline (contorno)
        if st["outline"] and pad_outline > 0:
            border = self._render_text_surface(self.text, st["outline_color"]).convert_alpha()
            for dx in range(-pad_outline, pad_outline + 1):
                for dy in range(-pad_outline, pad_outline + 1):
                    if dx == 0 and dy == 0:
                        continue
                    surf.blit(border, (pad_total_x + dx, pad_total_y + dy))

        # texto principal
        surf.blit(base, (pad_total_x, pad_total_y))

        self._cache = surf
        self._cache_key = key
        return surf

    def get_rect(self):
        surf = self._render()
        rect = surf.get_rect()
        setattr(rect, self.style["align"], self.pos)
        return rect

    def draw(self, tela: pygame.Surface):
        surf = self._render()
        rect = surf.get_rect()
        setattr(rect, self.style["align"], self.pos)
        tela.blit(surf, rect)

