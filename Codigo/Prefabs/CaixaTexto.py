import pygame
from Codigo.Prefabs.Texto import CAMINHO_FONTE_PADRAO


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
        self._cursor_indice = len(self.texto)

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

        self._fonte_tamanho = int(self._estilo_texto["size"])
        self._fonte = pygame.font.Font(str(CAMINHO_FONTE_PADRAO), self._fonte_tamanho)
        self._cursor_altura = max(12, int(self._fonte.get_height() * 0.9))
        self._cache_render_chave = None
        self._cache_render_surf = None
        self._prefixos_largura = [0]

    def set_texto(self, texto):
        self.texto = str(texto)[: self.max_chars]
        self._cursor_indice = min(self._cursor_indice, len(self.texto))
        self._invalidar_cache_texto()

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
        trecho = conteudo[:espaco]
        self.texto = self.texto[:self._cursor_indice] + trecho + self.texto[self._cursor_indice:]
        self._cursor_indice += len(trecho)
        self._invalidar_cache_texto()

    def _apagar_anterior(self):
        if self._cursor_indice <= 0:
            return
        self.texto = self.texto[:self._cursor_indice - 1] + self.texto[self._cursor_indice:]
        self._cursor_indice -= 1
        self._invalidar_cache_texto()

    def _apagar_atual(self):
        if self._cursor_indice >= len(self.texto):
            return
        self.texto = self.texto[:self._cursor_indice] + self.texto[self._cursor_indice + 1:]
        self._invalidar_cache_texto()

    def _invalidar_cache_texto(self):
        self._cache_render_chave = None
        self._cache_render_surf = None
        self._prefixos_largura = [0]

    def _garantir_prefixos_largura(self):
        if len(self._prefixos_largura) == len(self.texto) + 1:
            return
        self._prefixos_largura = [0]
        acum = 0
        for ch in self.texto:
            acum += self._fonte.size(ch)[0]
            self._prefixos_largura.append(acum)

    def _indice_cursor_por_mouse(self, pos_mouse_x):
        x_interno = pos_mouse_x - (self.rect.x + 16)
        if x_interno <= 0:
            return 0
        self._garantir_prefixos_largura()
        for i, largura in enumerate(self._prefixos_largura):
            if largura >= x_interno:
                return i
        return len(self.texto)

    def _resetar_cursor(self):
        self._cursor_timer = 0.0
        self._cursor_visivel = True

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
                if self.selecionada:
                    self._cursor_indice = self._indice_cursor_por_mouse(evento.pos[0])
                    self._resetar_cursor()
                if not self.selecionada:
                    self._backspace_ativo = False

            if not self.selecionada:
                continue

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_BACKSPACE:
                    self._apagar_anterior()
                    self._backspace_ativo = True
                    self._backspace_timer = 0.0
                    self._resetar_cursor()
                elif evento.key == pygame.K_DELETE:
                    self._apagar_atual()
                    self._resetar_cursor()
                elif evento.key == pygame.K_LEFT:
                    self._cursor_indice = max(0, self._cursor_indice - 1)
                    self._resetar_cursor()
                elif evento.key == pygame.K_RIGHT:
                    self._cursor_indice = min(len(self.texto), self._cursor_indice + 1)
                    self._resetar_cursor()
                elif evento.key == pygame.K_HOME:
                    self._cursor_indice = 0
                    self._resetar_cursor()
                elif evento.key == pygame.K_END:
                    self._cursor_indice = len(self.texto)
                    self._resetar_cursor()
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.selecionada = False
                    self._backspace_ativo = False
                elif evento.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self._adicionar_texto(self._capturar_colar())
                    self._resetar_cursor()
                elif evento.unicode and evento.unicode.isprintable():
                    self._adicionar_texto(evento.unicode)
                    self._resetar_cursor()

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
            self._apagar_anterior()

    def render(self, tela, eventos, dt):
        self._processar_eventos(eventos)
        self._atualizar_backspace_continuo(dt)

        estilo_tamanho = max(1, int(self._estilo_texto.get("size", 30)))
        if self._fonte_tamanho != estilo_tamanho:
            self._fonte_tamanho = estilo_tamanho
            self._fonte = pygame.font.Font(str(CAMINHO_FONTE_PADRAO), estilo_tamanho)
            self._invalidar_cache_texto()
        self._cursor_altura = max(12, int(self._fonte.get_height() * 0.9))

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

        chave_render = (conteudo, cor, self._fonte_tamanho)
        if self._cache_render_chave != chave_render:
            self._cache_render_chave = chave_render
            self._cache_render_surf = self._fonte.render(conteudo, True, cor)
        surf_texto = self._cache_render_surf
        max_largura = max(8, self.rect.width - 28)
        if surf_texto.get_width() > max_largura:
            area = pygame.Rect(surf_texto.get_width() - max_largura, 0, max_largura, surf_texto.get_height())
            surf_cortada = pygame.Surface((max_largura, surf_texto.get_height()), pygame.SRCALPHA)
            surf_cortada.blit(surf_texto, (0, 0), area)
            surf_texto = surf_cortada
        pos_texto = (self.rect.x + 14, self.rect.centery - (surf_texto.get_height() // 2))
        tela.blit(surf_texto, pos_texto)

        if self.selecionada and self._cursor_visivel:
            self._garantir_prefixos_largura()
            largura_texto = self._prefixos_largura[min(self._cursor_indice, len(self._prefixos_largura) - 1)]
            x_cursor = min(self.rect.right - 14, self.rect.x + 16 + largura_texto + 2)
            centro_y = self.rect.centery
            y0 = max(self.rect.y + 8, centro_y - (self._cursor_altura // 2))
            y1 = min(self.rect.bottom - 8, y0 + self._cursor_altura)
            pygame.draw.line(
                tela,
                (255, 255, 255),
                (x_cursor, y0),
                (x_cursor, y1),
                2,
            )
