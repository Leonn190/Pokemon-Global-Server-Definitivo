import pygame
from Codigo.Prefabs.Texto import Texto


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _clamp(v, a, b):
    return a if v < a else b if v > b else v


class Botao:
    """
    Botão "HTML/CSS" com 1 método só: render(...)
    - hover, click
    - escala suave no hover
    - fundo cor / imagem / frames hover (gif -> lista)
    - borda e radius
    - texto via classe Texto (com highlight/outline/shadow)
    - executa ações no clique (não retorna True/False)

    execute pode ser:
      - uma função (callable)
      - uma lista/tupla de funções
      - None
    Cada função será chamada como: func(JOGO, self)
    """

    DEFAULT_STYLE = {
        "radius": 16,
        "border_width": 3,

        "bg": (45, 70, 140),
        "bg_hover": (70, 105, 200),
        "bg_pressed": (35, 55, 110),

        "border": (15, 18, 24),
        "border_hover": (230, 230, 255),

        "hover_scale": 1.06,
        "hover_speed": 12.0,
        "press_scale": 0.98,

        "bg_image": None,         # pygame.Surface
        "bg_frames_hover": None,  # list[pygame.Surface]
        "bg_frames_fps": 12,

        "text_style": {
            "size": 26,
            "color": (255, 255, 255),
            "align": "center",

            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 2,

            "shadow": True,
            "shadow_color": (0, 0, 0, 160),
            "shadow_offset": (2, 2),

            "highlight": False,
            "highlight_color": (255, 235, 80, 200),
            "highlight_padding": (8, 4),
            "highlight_radius": 10,
        },
    }

    def __init__(self, rect: pygame.Rect, text: str, execute=None, style=None):
        self.base_rect = pygame.Rect(rect)
        self.rect = pygame.Rect(rect)

        self.execute = execute  # callable | list[callable] | None

        # merge de estilo
        self.style = dict(self.DEFAULT_STYLE)
        if style:
            text_style = dict(self.style["text_style"])
            if "text_style" in style:
                text_style.update(style["text_style"])
            self.style.update(style)
            self.style["text_style"] = text_style

        self.text = Texto(text, pos=self.base_rect.center, style=self.style["text_style"])

        # estado interno
        self.hover = False
        self.pressed = False
        self._hover_t = 0.0

        self._frame_idx = 0
        self._frame_acc = 0.0

    def set_text(self, text: str):
        self.text.set_text(text)

    def set_execute(self, execute):
        self.execute = execute

    def set_style(self, **kwargs):
        if "text_style" in kwargs:
            self.text.set_style(**kwargs["text_style"])
        self.style.update({k: v for k, v in kwargs.items() if k != "text_style"})

    def _scaled_rect(self, scale: float):
        cx, cy = self.base_rect.center
        w = int(self.base_rect.width * scale)
        h = int(self.base_rect.height * scale)
        r = pygame.Rect(0, 0, w, h)
        r.center = (cx, cy)
        return r

    def _executar(self, JOGO):
        if self.execute is None:
            return

        if callable(self.execute):
            self.execute(JOGO, self)
            return

        if isinstance(self.execute, (list, tuple)):
            for acao in self.execute:
                if callable(acao):
                    acao(JOGO, self)

    def render(self, tela: pygame.Surface, eventos, dt: float, JOGO=None, mouse_pos=None):
        """
        Faz UPDATE + DRAW num método só.
        Se clicar, executa self.execute (ações).
        """
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        # hover baseado no rect do frame anterior
        self.hover = self.rect.collidepoint(mouse_pos)

        clicou = False
        for e in eventos:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.hover:
                self.pressed = True
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if self.pressed and self.hover:
                    clicou = True
                self.pressed = False

        # transição hover estilo CSS
        target = 1.0 if self.hover else 0.0
        speed = float(self.style["hover_speed"])
        self._hover_t = _clamp(
            self._hover_t + (target - self._hover_t) * _clamp(speed * dt, 0.0, 1.0),
            0.0,
            1.0,
        )

        # escala final
        scale = _lerp(1.0, float(self.style["hover_scale"]), self._hover_t)
        if self.pressed:
            scale *= float(self.style["press_scale"])
        self.rect = self._scaled_rect(scale)

        # animação frames no hover
        frames = self.style["bg_frames_hover"] or []
        if self.hover and frames:
            self._frame_acc += dt
            frame_dur = 1.0 / max(1, int(self.style["bg_frames_fps"]))
            while self._frame_acc >= frame_dur:
                self._frame_acc -= frame_dur
                self._frame_idx = (self._frame_idx + 1) % len(frames)
        else:
            self._frame_idx = 0
            self._frame_acc = 0.0

        # cores por estado
        bg = self.style["bg"]
        bg_hover = self.style["bg_hover"]
        bg_pressed = self.style["bg_pressed"]

        bg_now = _lerp_color(bg, bg_hover, self._hover_t)
        if self.pressed:
            bg_now = bg_pressed

        border_now = self.style["border_hover"] if self.hover else self.style["border"]

        # desenhar fundo
        radius = int(self.style["radius"])
        bw = int(self.style["border_width"])

        if self.hover and frames:
            frame = frames[self._frame_idx]
            frame = pygame.transform.smoothscale(frame, (self.rect.width, self.rect.height))
            tela.blit(frame, self.rect.topleft)
        elif self.style["bg_image"] is not None:
            img = self.style["bg_image"]
            img = pygame.transform.smoothscale(img, (self.rect.width, self.rect.height))
            tela.blit(img, self.rect.topleft)
        else:
            pygame.draw.rect(tela, bg_now, self.rect, border_radius=radius)

        # borda
        if bw > 0:
            pygame.draw.rect(tela, border_now, self.rect, width=bw, border_radius=radius)

        # texto
        self.text.set_pos(self.rect.center)
        self.text.draw(tela)

        # clique -> executa ações
        if clicou:
            self._executar(JOGO)