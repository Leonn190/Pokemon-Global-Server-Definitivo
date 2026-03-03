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

    def _processar_eventos(self, eventos):
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.selecionada = self.ativo and self.rect.collidepoint(evento.pos)

            if not self.selecionada:
                continue

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE:
                    self.texto = self.texto[:-1]
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.selecionada = False
                elif evento.unicode and evento.unicode.isprintable() and len(self.texto) < self.max_chars:
                    self.texto += evento.unicode

    def render(self, tela, eventos, dt):
        self._processar_eventos(eventos)

        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_visivel = not self._cursor_visivel
            self._cursor_timer = 0.0

        bg = (30, 36, 62) if self.ativo else (25, 25, 32)
        borda = (255, 220, 120) if self.selecionada else (120, 130, 160)

        pygame.draw.rect(tela, bg, self.rect, border_radius=14)
        pygame.draw.rect(tela, borda, self.rect, width=2, border_radius=14)

        conteudo = self.texto if self.texto else self.placeholder
        cor = (235, 238, 255) if self.texto else (160, 166, 190)

        estilo = dict(self._estilo_texto)
        estilo["color"] = cor
        label = Texto(conteudo, (self.rect.x + 16, self.rect.centery), style=estilo)
        label.draw(tela)

        if self.selecionada and self._cursor_visivel:
            largura_texto = label.get_rect().width
            x_cursor = min(self.rect.right - 14, self.rect.x + 16 + largura_texto + 2)
            pygame.draw.line(
                tela,
                (255, 255, 255),
                (x_cursor, self.rect.y + 12),
                (x_cursor, self.rect.bottom - 12),
                2,
            )
