import pygame
from Codigo.Prefabs.Texto import Texto


class CaixaTexto:
    def __init__(self, rect: pygame.Rect, texto_inicial="", placeholder="Digite aqui...", max_chars=28, ativo=True):
        self.rect = pygame.Rect(rect)
        self.texto = texto_inicial
        self.placeholder = placeholder
        self.max_chars = max_chars
        self.ativo = ativo
        self.selecionada = False

        self._cursor_visivel = True
        self._cursor_timer = 0.0

        self._backspace_ativo = False
        self._backspace_timer = 0.0
        self._backspace_delay = 0.32
        self._backspace_intervalo = 0.05

        self._estilo_texto = {
            "size": 30,
            "color": (235, 238, 255),
            "align": "midleft",
            "outline": False,
            "shadow": False,
        }

    def set_texto(self, texto):
        self.texto = str(texto)[: self.max_chars]

    def set_ativo(self, ativo: bool):
        self.ativo = bool(ativo)
        if not self.ativo:
            self.selecionada = False
            self._backspace_ativo = False

    def _adicionar_texto(self, conteudo):
        if not conteudo:
            return
        espaco = self.max_chars - len(self.texto)
        if espaco <= 0:
            return
        self.texto += conteudo[:espaco]

    def _capturar_colar(self):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not raw:
                return ""
            if isinstance(raw, bytes):
                conteudo = raw.decode("utf-8", errors="ignore")
            else:
                conteudo = str(raw)
            return "".join(ch for ch in conteudo.replace("\x00", "") if ch.isprintable())
        except Exception:
            return ""

    def _processar_eventos(self, eventos):
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.selecionada = self.ativo and self.rect.collidepoint(evento.pos)
                if not self.selecionada:
                    self._backspace_ativo = False

            if not self.selecionada:
                continue

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE:
                    self.texto = self.texto[:-1]
                    self._backspace_ativo = True
                    self._backspace_timer = 0.0
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.selecionada = False
                    self._backspace_ativo = False
                elif evento.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self._adicionar_texto(self._capturar_colar())
                elif evento.unicode and evento.unicode.isprintable():
                    self._adicionar_texto(evento.unicode)

            if evento.type == pygame.KEYUP and evento.key == pygame.K_BACKSPACE:
                self._backspace_ativo = False

    def _atualizar_backspace_continuo(self, dt):
        if not self.selecionada or not self._backspace_ativo:
            return

        self._backspace_timer += dt
        if self._backspace_timer < self._backspace_delay:
            return

        while self._backspace_timer >= self._backspace_delay + self._backspace_intervalo:
            self._backspace_timer -= self._backspace_intervalo
            if not self.texto:
                self._backspace_ativo = False
                break
            self.texto = self.texto[:-1]

    def render(self, tela, eventos, dt):
        self._processar_eventos(eventos)
        self._atualizar_backspace_continuo(dt)

        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_visivel = not self._cursor_visivel
            self._cursor_timer = 0.0

        bg = (30, 36, 62) if self.ativo else (25, 25, 32)
        borda = (255, 220, 120) if self.selecionada else (120, 130, 160)

        pygame.draw.rect(tela, bg, self.rect, border_radius=14)
        pygame.draw.rect(tela, borda, self.rect, width=2, border_radius=14)

        exibir_placeholder = (not self.texto) and (not self.selecionada)
        conteudo = self.placeholder if exibir_placeholder else self.texto
        cor = (160, 166, 190) if exibir_placeholder else (235, 238, 255)

        estilo = dict(self._estilo_texto)
        estilo["color"] = cor
        label = Texto(conteudo, (self.rect.x + 16, self.rect.centery), style=estilo)
        label.draw(tela)

        if self.selecionada and self._cursor_visivel:
            largura_texto = Texto(self.texto, (0, 0), style=estilo).get_rect().width
            x_cursor = min(self.rect.right - 14, self.rect.x + 16 + largura_texto + 2)
            pygame.draw.line(
                tela,
                (255, 255, 255),
                (x_cursor, self.rect.y + 12),
                (x_cursor, self.rect.bottom - 12),
                2,
            )
