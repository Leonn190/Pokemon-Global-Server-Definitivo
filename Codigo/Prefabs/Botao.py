import math
import pygame
from Codigo.ModulosGerais.Sonoridades import tocar
from Codigo.Prefabs.Texto import Texto
from Codigo.Prefabs.Tooltip import Tooltip


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
    _adiar_tooltips = False
    _fila_tooltips = []

    DEFAULT_STYLE = {
        "radius": 16,
        "border_width": 3,
        "bg": (45, 70, 140),
        "bg_hover": (70, 105, 200),
        "bg_pressed": (35, 55, 110),
        "border": (15, 18, 24),
        "border_hover": (230, 230, 255),
        "bg_disabled": (38, 43, 58),
        "border_disabled": (92, 103, 126),
        "text_disabled": (165, 173, 196),
        "hover_scale": 1.06,
        "hover_speed": 12.0,
        "press_scale": 0.98,
        "bg_image": None,
        "bg_frames_hover": None,
        "bg_frames_fps": 12,
        "bg_frames_mode": "ticks",
        "bg_frames_interval_ms": 50,
        "bg_frames_scale_mode": "fast",
        "text_color_steps": 12,
        "text_update_on_change": True,
        "som_clique": "Clique",
        "som_bloqueado": "Bloq",
        "pulse": False,
        "pulse_color": (255, 224, 134),
        "pulse_border_color": (255, 244, 196),
        "pulse_speed": 2.8,
        "pulse_strength": 0.34,
        "text_style": {
            "size": 26,
            "color": (255, 255, 255),
            "hover_color": (255, 238, 90),
            "hover_speed": 24.0,
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
        self.execute = execute

        self.style = dict(self.DEFAULT_STYLE)
        if style:
            text_style = dict(self.style["text_style"])
            if "text_style" in style:
                text_style.update(style["text_style"])
            self.style.update(style)
            self.style["text_style"] = text_style

        self.text = Texto(text, pos=self.base_rect.center, style=self.style["text_style"])

        self.hover = False
        self.pressed = False
        self.clicado = False
        self._hover_t = 0.0
        self._frame_idx = 0
        self._frame_acc = 0.0
        self._text_hover_t = 0.0
        self._clip_cache_size = None
        self._clip_surf = None
        self._mask_cache = {}
        self._scaled_cache = {}
        self._last_text_color = None
        self._last_text_step = None
        self._last_tick_ms = 0
        self.habilitado = True
        self.som_clique = self.style.get("som_clique", "Clique")
        self.som_bloqueado = self.style.get("som_bloqueado", "Bloq")
        self.tooltip = None

    @classmethod
    def iniciar_camada_tooltips(cls):
        cls._adiar_tooltips = True
        cls._fila_tooltips = []

    @classmethod
    def finalizar_camada_tooltips(cls, tela: pygame.Surface):
        fila = list(cls._fila_tooltips)
        cls._adiar_tooltips = False
        cls._fila_tooltips = []
        for tooltip, mouse_pos, forcar in fila:
            tooltip.render(tela, mouse_pos=mouse_pos, forcar=forcar)

    def set_text(self, text: str):
        self.text.set_text(text)
        self._last_text_color = None
        self._last_text_step = None

    def set_execute(self, execute):
        self.execute = execute

    def set_style(self, **kwargs):
        if "text_style" in kwargs:
            self.text.set_style(**kwargs["text_style"])
        self.style.update({k: v for k, v in kwargs.items() if k != "text_style"})

        if "som_clique" in kwargs:
            self.som_clique = kwargs["som_clique"]
        if "som_bloqueado" in kwargs:
            self.som_bloqueado = kwargs["som_bloqueado"]

        if "text_color_steps" in kwargs or "text_update_on_change" in kwargs:
            self._last_text_color = None
            self._last_text_step = None

    def set_habilitado(self, habilitado: bool):
        self.habilitado = bool(habilitado)

    def set_pulsando(self, ativo: bool, cor=None, cor_borda=None, velocidade=None, intensidade=None):
        self.style["pulse"] = bool(ativo)
        if cor is not None:
            self.style["pulse_color"] = cor
        if cor_borda is not None:
            self.style["pulse_border_color"] = cor_borda
        if velocidade is not None:
            self.style["pulse_speed"] = float(velocidade)
        if intensidade is not None:
            self.style["pulse_strength"] = float(intensidade)

    def set_tooltip(self, tooltip, **kwargs):
        if isinstance(tooltip, Tooltip):
            self.tooltip = tooltip
            return self.tooltip
        self.tooltip = Tooltip(str(tooltip or ""), **kwargs)
        return self.tooltip

    def limpar_tooltip(self):
        self.tooltip = None

    def _scaled_rect(self, scale: float):
        cx, cy = self.base_rect.center
        w = int(self.base_rect.width * scale)
        h = int(self.base_rect.height * scale)
        r = pygame.Rect(0, 0, w, h)
        r.center = (cx, cy)
        return r

    def _executar(self, jogo):
        if self.som_clique:
            tocar(self.som_clique)

        if self.execute is None:
            return
        if callable(self.execute):
            self.execute(jogo, self)
            return
        if isinstance(self.execute, (list, tuple)):
            for acao in self.execute:
                if callable(acao):
                    acao(jogo, self)

    def _get_mask(self, w: int, h: int, radius: int) -> pygame.Surface:
        key = (w, h, radius)
        mask = self._mask_cache.get(key)
        if mask is not None:
            return mask
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        self._mask_cache[key] = mask
        return mask

    def _get_scaled(self, surf: pygame.Surface, w: int, h: int, scale_mode: str = "smooth") -> pygame.Surface:
        key = (id(surf), w, h, scale_mode)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached

        if scale_mode == "fast":
            scaled = pygame.transform.scale(surf, (w, h)).convert_alpha()
        else:
            scaled = pygame.transform.smoothscale(surf, (w, h)).convert_alpha()

        self._scaled_cache[key] = scaled
        return scaled

    def _ensure_clip(self, w: int, h: int):
        if self._clip_surf is None or self._clip_cache_size != (w, h):
            self._clip_cache_size = (w, h)
            self._clip_surf = pygame.Surface((w, h), pygame.SRCALPHA)

    def _update_text_color_fast(self, text_style):
        if not self.habilitado:
            cor = self.style.get("text_disabled", (165, 173, 196))
            if cor != self._last_text_color:
                self.text.set_style(color=cor)
                self._last_text_color = cor
            return

        base = text_style.get("color", (255, 255, 255))
        hover = text_style.get("hover_color", (255, 238, 90))
        steps = int(self.style.get("text_color_steps", 12))
        update_on_change = bool(self.style.get("text_update_on_change", True))

        if steps <= 0:
            color_now = hover if self.hover else base
            if (not update_on_change) or (color_now != self._last_text_color):
                self.text.set_style(color=color_now)
                self._last_text_color = color_now
            return

        step = int(self._text_hover_t * steps)
        step = 0 if step < 0 else steps if step > steps else step
        if update_on_change and (step == self._last_text_step):
            return

        tq = step / steps
        color_now = _lerp_color(base, hover, tq)
        if (not update_on_change) or (color_now != self._last_text_color):
            self.text.set_style(color=color_now)
            self._last_text_color = color_now
            self._last_text_step = step

    def _aplicar_pulso(self, bg_now, border_now):
        if not self.habilitado or not self.style.get("pulse", False):
            return bg_now, border_now

        tempo = pygame.time.get_ticks() / 1000.0
        velocidade = max(0.01, float(self.style.get("pulse_speed", 2.8)))
        intensidade = _clamp(float(self.style.get("pulse_strength", 0.34)), 0.0, 1.0)
        t = ((math.sin(tempo * velocidade * math.tau) + 1.0) * 0.5) * intensidade

        bg_now = _lerp_color(bg_now, self.style.get("pulse_color", (255, 224, 134)), t)
        border_now = _lerp_color(border_now, self.style.get("pulse_border_color", (255, 244, 196)), min(1.0, t * 1.3))
        return bg_now, border_now

    def render(self, tela: pygame.Surface, eventos, dt: float, JOGO=None, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        self.hover = self.rect.collidepoint(mouse_pos)
        self.clicado = False

        clicou = False
        clicou_bloqueado = False
        for e in eventos:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.hover:
                if self.habilitado:
                    self.pressed = True
                else:
                    clicou_bloqueado = True
                    self.pressed = False
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if self.pressed and self.hover:
                    clicou = True
                self.pressed = False

        target = 1.0 if (self.hover and self.habilitado) else 0.0
        speed = float(self.style["hover_speed"])
        self._hover_t = _clamp(self._hover_t + (target - self._hover_t) * _clamp(speed * dt, 0.0, 1.0), 0.0, 1.0)

        text_style = self.style["text_style"]
        text_speed = float(text_style.get("hover_speed", 24.0))
        self._text_hover_t = _clamp(self._text_hover_t + (target - self._text_hover_t) * _clamp(text_speed * dt, 0.0, 1.0), 0.0, 1.0)

        scale = _lerp(1.0, float(self.style["hover_scale"]), self._hover_t)
        if self.pressed and self.habilitado:
            scale *= float(self.style["press_scale"])
        self.rect = self._scaled_rect(scale)

        frames = self.style["bg_frames_hover"] or []
        if frames and self.hover and self.habilitado:
            mode = self.style.get("bg_frames_mode", "ticks")
            if mode == "ticks":
                intervalo = int(self.style.get("bg_frames_interval_ms", 50))
                agora = pygame.time.get_ticks()
                if self._last_tick_ms == 0:
                    self._last_tick_ms = agora
                if agora - self._last_tick_ms >= intervalo:
                    self._frame_idx = (self._frame_idx + 1) % len(frames)
                    self._last_tick_ms = agora
            else:
                self._frame_acc += dt
                frame_dur = 1.0 / max(1, int(self.style["bg_frames_fps"]))
                while self._frame_acc >= frame_dur:
                    self._frame_acc -= frame_dur
                    self._frame_idx = (self._frame_idx + 1) % len(frames)
        else:
            self._frame_idx = 0
            self._frame_acc = 0.0
            self._last_tick_ms = 0

        bg = self.style["bg"]
        bg_hover = self.style["bg_hover"]
        bg_pressed = self.style["bg_pressed"]
        border_now = self.style["border_hover"] if (self.hover and self.habilitado) else self.style["border"]

        bg_now = _lerp_color(bg, bg_hover, self._hover_t)
        if self.pressed and self.habilitado:
            bg_now = bg_pressed

        if not self.habilitado:
            bg_now = self.style.get("bg_disabled", (38, 43, 58))
            border_now = self.style.get("border_disabled", (92, 103, 126))
        else:
            bg_now, border_now = self._aplicar_pulso(bg_now, border_now)

        radius = int(self.style["radius"])
        bw = int(self.style["border_width"])
        w, h = self.rect.width, self.rect.height

        self._ensure_clip(w, h)
        clip_surf = self._clip_surf
        clip_surf.fill((0, 0, 0, 0))

        if self.hover and frames and self.habilitado:
            frame = frames[self._frame_idx]
            scale_mode = self.style.get("bg_frames_scale_mode", "fast")
            frame_scaled = self._get_scaled(frame, w, h, scale_mode)
            clip_surf.blit(frame_scaled, (0, 0))
        elif self.style["bg_image"] is not None:
            img = self.style["bg_image"]
            img_scaled = self._get_scaled(img, w, h, "smooth")
            clip_surf.blit(img_scaled, (0, 0))
        else:
            clip_surf.fill((*bg_now, 255))

        mask = self._get_mask(w, h, radius)
        clip_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        tela.blit(clip_surf, self.rect.topleft)
        if bw > 0:
            pygame.draw.rect(tela, border_now, self.rect, width=bw, border_radius=radius)

        self._update_text_color_fast(text_style)
        ancora_texto = str(self.style.get("text_anchor", "center")).strip().lower()
        if ancora_texto == "left":
            self.text.set_pos((self.rect.x + 12, self.rect.centery))
        else:
            self.text.set_pos(self.rect.center)
        self.text.draw(tela)

        if self.tooltip is not None:
            self.tooltip.definir_area(self.rect)
            if Botao._adiar_tooltips:
                Botao._fila_tooltips.append((self.tooltip, mouse_pos, self.hover))
            else:
                self.tooltip.render(tela, mouse_pos=mouse_pos, forcar=self.hover)

        if clicou_bloqueado and self.som_bloqueado:
            tocar(self.som_bloqueado)

        if clicou:
            self.clicado = True
            self._executar(JOGO)


class BotaoAlavanca(Botao):
    def __init__(self, rect: pygame.Rect, nome: str, estado_inicial=False, execute=None, style=None):
        self.nome = nome
        self.estado = bool(estado_inicial)
        style = dict(style or {})
        self.estilo_ativo = dict(self._estilo_ativo_padrao())
        self.estilo_ativo.update(style.pop("estilo_ativo", {}))
        self.estilo_desativado = dict(self._estilo_desativado_padrao())
        self.estilo_desativado.update(style.pop("estilo_desativado", {}))

        estilo_final = dict(self._estilo_estado())
        if style:
            texto_style = dict(style.get("text_style", {}))
            estilo_final.update(style)
            if texto_style:
                estilo_final["text_style"] = texto_style

        estilo_final.update(self._estilo_estado())
        super().__init__(rect, self._texto_estado(), execute=execute, style=estilo_final)

    def _texto_estado(self):
        return f"{self.nome}: {'Ligado' if self.estado else 'Desligado'}"

    def _estilo_ativo_padrao(self):
        return {
            "bg": (24, 128, 42),
            "bg_hover": (35, 156, 54),
            "bg_pressed": (20, 102, 34),
            "border": (12, 60, 20),
            "border_hover": (180, 255, 180),
        }

    def _estilo_desativado_padrao(self):
        return {
            "bg": (150, 32, 32),
            "bg_hover": (186, 42, 42),
            "bg_pressed": (118, 26, 26),
            "border": (70, 16, 16),
            "border_hover": (255, 180, 180),
        }

    def _estilo_estado(self):
        return self.estilo_ativo if self.estado else self.estilo_desativado

    def set_estado(self, estado: bool):
        self.estado = bool(estado)
        self.set_text(self._texto_estado())
        self.set_style(**self._estilo_estado())

    def alternar(self, jogo=None):
        self.set_estado(not self.estado)
        return self.estado

    def _executar(self, jogo):
        self.alternar(jogo)

        if self.execute is None:
            return

        if callable(self.execute):
            self.execute(jogo, self.estado, self)
            return

        if isinstance(self.execute, (list, tuple)):
            for acao in self.execute:
                if callable(acao):
                    acao(jogo, self.estado, self)


class BotaoSelecao(Botao):
    def __init__(self, rect: pygame.Rect, text: str, execute=None, style=None, selecionado=False):
        self.selecionado = bool(selecionado)
        self._base_style = dict(style or {})
        super().__init__(rect, text, execute=execute, style=self._estilo_atual())

    def _estilo_selecionado(self):
        return {
            "bg": (28, 86, 48),
            "bg_hover": (40, 115, 64),
            "bg_pressed": (20, 60, 34),
            "border": (180, 230, 180),
            "border_hover": (255, 245, 180),
        }

    def _estilo_atual(self):
        estilo = dict(self._base_style)
        texto_style = dict(estilo.get("text_style", {}))
        if self.selecionado:
            estilo.update(self._estilo_selecionado())
        if texto_style:
            estilo["text_style"] = texto_style
        return estilo

    def set_selecionado(self, selecionado: bool):
        self.selecionado = bool(selecionado)
        estilo = self._estilo_atual()
        text_style = dict(self.DEFAULT_STYLE.get("text_style", {}))
        text_style.update(estilo.get("text_style", {}))
        self.style = dict(self.DEFAULT_STYLE)
        self.style.update({k: v for k, v in estilo.items() if k != "text_style"})
        self.style["text_style"] = text_style

    def render(self, tela: pygame.Surface, eventos, dt: float, JOGO=None, mouse_pos=None):
        super().render(tela, eventos, dt, JOGO=JOGO, mouse_pos=mouse_pos)
