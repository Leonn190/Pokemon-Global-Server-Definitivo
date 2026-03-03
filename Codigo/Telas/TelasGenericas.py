import pygame
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.CaixaTexto import CaixaTexto
from Codigo.Prefabs.Texto import Texto


_ESTILO_BOTAO_MODAL = {
    "radius": 18,
    "border_width": 2,
    "bg": (22, 30, 55),
    "bg_hover": (35, 45, 78),
    "bg_pressed": (15, 21, 39),
    "border": (80, 90, 130),
    "border_hover": (255, 220, 120),
    "hover_scale": 1.03,
    "press_scale": 0.98,
    "text_style": {
        "size": 28,
        "color": (245, 246, 255),
        "hover_color": (255, 226, 120),
        "outline": True,
        "outline_color": (0, 0, 0),
        "outline_thickness": 1,
        "shadow": True,
        "shadow_color": (0, 0, 0, 160),
        "shadow_offset": (2, 2),
    },
}


def _normalizar_lista(valor, n, padrao):
    if valor is None:
        return [padrao] * n
    if isinstance(valor, str):
        return [valor] * n
    if isinstance(valor, int):
        return [valor] * n
    lst = list(valor)
    while len(lst) < n:
        lst.append(padrao)
    return lst


class _BaseModal:
    def __init__(self, tela_size, alpha_overlay=180):
        self._overlay_size = (0, 0)
        self._overlay = None
        self._alpha_overlay = int(alpha_overlay)

        self._painel_size = (0, 0)
        self._painel_surf = None

        self._rebuild_cache(tela_size)

    def _rebuild_cache(self, tela_size):
        w, h = tela_size
        if (w, h) != self._overlay_size:
            self._overlay_size = (w, h)
            self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            self._overlay.fill((0, 0, 0, self._alpha_overlay))

        # painel é dependente do tamanho/rect (cada classe define caixa), então aqui não desenha o painel

    def _get_painel(self, caixa_rect, bg_color, border_color, border_w=2, radius=20):
        size = (caixa_rect.width, caixa_rect.height)
        if size != self._painel_size or self._painel_surf is None:
            self._painel_size = size
            self._painel_surf = pygame.Surface(size, pygame.SRCALPHA)

            r = self._painel_surf.get_rect()
            pygame.draw.rect(self._painel_surf, bg_color, r, border_radius=radius)
            pygame.draw.rect(self._painel_surf, border_color, r, width=border_w, border_radius=radius)

        return self._painel_surf

    def _blit_overlay(self, tela):
        size = tela.get_size()
        if size != self._overlay_size:
            self._rebuild_cache(size)
        tela.blit(self._overlay, (0, 0))


class SubtelaConfirmacao(_BaseModal):
    def __init__(self, tela_size, pergunta, confirmar_callback, cancelar_callback=None, titulo=None):
        largura, altura = tela_size
        caixa = pygame.Rect(0, 0, min(860, int(largura * 0.75)), min(340, int(altura * 0.46)))
        caixa.center = (largura // 2, altura // 2)

        self.caixa = caixa
        self.pergunta = pergunta
        self.titulo = titulo or pergunta
        self.confirmar_callback = confirmar_callback
        self.cancelar_callback = cancelar_callback
        self.encerrada = False

        super().__init__(tela_size, alpha_overlay=175)

        self._texto_titulo = Texto(
            self.titulo,
            (self.caixa.centerx, self.caixa.top + 56),
            style={"size": 38, "align": "center"},
        )
        self._texto_pergunta = Texto(
            self.pergunta,
            (self.caixa.centerx, self.caixa.centery - 18),
            style={"size": 29, "align": "center"},
        )

        y_botoes = self.caixa.bottom - 98
        self.botao_voltar = Botao(
            pygame.Rect(self.caixa.left + 60, y_botoes, 250, 70),
            "Voltar",
            execute=self._cancelar,
            style=_ESTILO_BOTAO_MODAL,
        )
        self.botao_confirmar = Botao(
            pygame.Rect(self.caixa.right - 310, y_botoes, 250, 70),
            "Confirmar",
            execute=self._confirmar,
            style=_ESTILO_BOTAO_MODAL,
        )

    def _confirmar(self, jogo, botao):
        if callable(self.confirmar_callback):
            self.confirmar_callback()
        self.encerrada = True

    def _cancelar(self, jogo, botao):
        if callable(self.cancelar_callback):
            self.cancelar_callback()
        self.encerrada = True

    def _on_resize(self, tela_size):
        largura, altura = tela_size
        caixa = pygame.Rect(0, 0, min(860, int(largura * 0.75)), min(340, int(altura * 0.46)))
        caixa.center = (largura // 2, altura // 2)
        self.caixa = caixa

        self._texto_titulo.set_pos((self.caixa.centerx, self.caixa.top + 56))
        self._texto_pergunta.set_pos((self.caixa.centerx, self.caixa.centery - 18))

        y_botoes = self.caixa.bottom - 98
        self.botao_voltar.rect = pygame.Rect(self.caixa.left + 60, y_botoes, 250, 70)
        self.botao_confirmar.rect = pygame.Rect(self.caixa.right - 310, y_botoes, 250, 70)

        # invalida painel cache (tamanho mudou)
        self._painel_surf = None
        self._painel_size = (0, 0)

    def render(self, tela, eventos, dt, JOGO=None):
        size = tela.get_size()
        if size != self._overlay_size:
            self._rebuild_cache(size)
            self._on_resize(size)

        self._blit_overlay(tela)

        painel = self._get_painel(
            self.caixa,
            bg_color=(16, 21, 40),
            border_color=(255, 220, 120),
            border_w=2,
            radius=20,
        )
        tela.blit(painel, self.caixa.topleft)

        self._texto_titulo.draw(tela)
        self._texto_pergunta.draw(tela)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_confirmar.render(tela, eventos, dt, JOGO=JOGO)


class SubtelaTexto(_BaseModal):
    def __init__(
        self,
        tela_size,
        titulo,
        texto_inicial,
        enviar_callback,
        voltar_callback=None,
        placeholders=None,
        max_chars=None,
    ):
        largura, altura = tela_size

        if isinstance(texto_inicial, (list, tuple)):
            textos_iniciais = [str(t) for t in texto_inicial]
        else:
            textos_iniciais = [str(texto_inicial)]

        self._qtd_campos = max(1, len(textos_iniciais))

        placeholders = _normalizar_lista(placeholders, self._qtd_campos, "Digite o texto...")
        max_chars = _normalizar_lista(max_chars, self._qtd_campos, 24)

        altura_modal = min(620, int(altura * 0.72)) if self._qtd_campos > 1 else min(460, int(altura * 0.60))
        caixa = pygame.Rect(0, 0, min(980, int(largura * 0.82)), altura_modal)
        caixa.center = (largura // 2, altura // 2)

        self.caixa = caixa
        self.titulo = titulo
        self.enviar_callback = enviar_callback
        self.voltar_callback = voltar_callback
        self.encerrada = False

        super().__init__(tela_size, alpha_overlay=185)

        self._texto_titulo = Texto(
            self.titulo,
            (self.caixa.centerx, self.caixa.top + 52),
            style={"size": 36, "align": "center"},
        )

        self.barras_texto = []
        y_base = self.caixa.top + 112
        espacamento = 96
        for i in range(self._qtd_campos):
            self.barras_texto.append(
                CaixaTexto(
                    pygame.Rect(self.caixa.left + 42, y_base + i * espacamento, self.caixa.width - 84, 72),
                    texto_inicial=textos_iniciais[i],
                    placeholder=placeholders[i],
                    max_chars=max_chars[i],
                    ativo=True,
                )
            )

        self.barra_texto = self.barras_texto[0]

        y_botoes = self.caixa.bottom - 94
        self.botao_voltar = Botao(
            pygame.Rect(self.caixa.left + 42, y_botoes, 220, 66),
            "Voltar",
            execute=self._voltar,
            style=_ESTILO_BOTAO_MODAL,
        )
        self.botao_enviar = Botao(
            pygame.Rect(self.caixa.right - 262, y_botoes, 220, 66),
            "Criar" if self._qtd_campos > 1 else "Enviar",
            execute=self._enviar,
            style=_ESTILO_BOTAO_MODAL,
        )

    def _enviar(self, jogo, botao):
        if callable(self.enviar_callback):
            valores = [barra.texto.strip() for barra in self.barras_texto]
            if len(valores) == 1:
                self.enviar_callback(valores[0])
            else:
                self.enviar_callback(*valores)
        self.encerrada = True

    def _voltar(self, jogo, botao):
        if callable(self.voltar_callback):
            self.voltar_callback()
        self.encerrada = True

    def _on_resize(self, tela_size):
        largura, altura = tela_size

        altura_modal = min(620, int(altura * 0.72)) if self._qtd_campos > 1 else min(460, int(altura * 0.60))
        caixa = pygame.Rect(0, 0, min(980, int(largura * 0.82)), altura_modal)
        caixa.center = (largura // 2, altura // 2)
        self.caixa = caixa

        self._texto_titulo.set_pos((self.caixa.centerx, self.caixa.top + 52))

        y_base = self.caixa.top + 112
        espacamento = 96
        for i, barra in enumerate(self.barras_texto):
            barra.rect = pygame.Rect(self.caixa.left + 42, y_base + i * espacamento, self.caixa.width - 84, 72)

        y_botoes = self.caixa.bottom - 94
        self.botao_voltar.rect = pygame.Rect(self.caixa.left + 42, y_botoes, 220, 66)
        self.botao_enviar.rect = pygame.Rect(self.caixa.right - 262, y_botoes, 220, 66)

        self._painel_surf = None
        self._painel_size = (0, 0)

    def render(self, tela, eventos, dt, JOGO=None):
        size = tela.get_size()
        if size != self._overlay_size:
            self._rebuild_cache(size)
            self._on_resize(size)

        self._blit_overlay(tela)

        painel = self._get_painel(
            self.caixa,
            bg_color=(14, 20, 38),
            border_color=(255, 220, 120),
            border_w=2,
            radius=20,
        )
        tela.blit(painel, self.caixa.topleft)

        self._texto_titulo.draw(tela)

        for barra in self.barras_texto:
            barra.render(tela, eventos, dt)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_enviar.render(tela, eventos, dt, JOGO=JOGO)

