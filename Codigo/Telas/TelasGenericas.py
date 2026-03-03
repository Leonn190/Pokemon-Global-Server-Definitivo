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


class SubtelaConfirmacao:
    def __init__(self, tela_size, pergunta, confirmar_callback, cancelar_callback=None):
        largura, altura = tela_size
        caixa = pygame.Rect(0, 0, min(860, int(largura * 0.75)), min(340, int(altura * 0.46)))
        caixa.center = (largura // 2, altura // 2)

        self.caixa = caixa
        self.pergunta = pergunta
        self.confirmar_callback = confirmar_callback
        self.cancelar_callback = cancelar_callback
        self.encerrada = False

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

    def render(self, tela, eventos, dt, JOGO=None):
        overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        tela.blit(overlay, (0, 0))

        pygame.draw.rect(tela, (16, 21, 40), self.caixa, border_radius=20)
        pygame.draw.rect(tela, (255, 220, 120), self.caixa, width=2, border_radius=20)

        titulo = Texto("Confirmação", (self.caixa.centerx, self.caixa.top + 50), style={"size": 38, "align": "center"})
        pergunta = Texto(self.pergunta, (self.caixa.centerx, self.caixa.centery - 20), style={"size": 29, "align": "center"})
        titulo.draw(tela)
        pergunta.draw(tela)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_confirmar.render(tela, eventos, dt, JOGO=JOGO)


class SubtelaTexto:
    def __init__(self, tela_size, titulo, texto_inicial, enviar_callback, voltar_callback=None):
        largura, altura = tela_size
        caixa = pygame.Rect(0, 0, min(980, int(largura * 0.82)), min(460, int(altura * 0.60)))
        caixa.center = (largura // 2, altura // 2)

        self.caixa = caixa
        self.titulo = titulo
        self.enviar_callback = enviar_callback
        self.voltar_callback = voltar_callback
        self.encerrada = False

        self.barra_titulo = CaixaTexto(
            pygame.Rect(self.caixa.left + 42, self.caixa.top + 72, self.caixa.width - 84, 72),
            texto_inicial=titulo,
            placeholder="Título",
            ativo=False,
        )
        self.barra_texto = CaixaTexto(
            pygame.Rect(self.caixa.left + 42, self.caixa.top + 168, self.caixa.width - 84, 72),
            texto_inicial=texto_inicial,
            placeholder="Digite o texto...",
            max_chars=24,
            ativo=True,
        )

        y_botoes = self.caixa.bottom - 94
        self.botao_voltar = Botao(
            pygame.Rect(self.caixa.left + 42, y_botoes, 220, 66),
            "Voltar",
            execute=self._voltar,
            style=_ESTILO_BOTAO_MODAL,
        )
        self.botao_enviar = Botao(
            pygame.Rect(self.caixa.right - 262, y_botoes, 220, 66),
            "Enviar",
            execute=self._enviar,
            style=_ESTILO_BOTAO_MODAL,
        )

    def _enviar(self, jogo, botao):
        if callable(self.enviar_callback):
            self.enviar_callback(self.barra_texto.texto.strip())
        self.encerrada = True

    def _voltar(self, jogo, botao):
        if callable(self.voltar_callback):
            self.voltar_callback()
        self.encerrada = True

    def render(self, tela, eventos, dt, JOGO=None):
        overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))

        pygame.draw.rect(tela, (14, 20, 38), self.caixa, border_radius=20)
        pygame.draw.rect(tela, (255, 220, 120), self.caixa, width=2, border_radius=20)

        titulo = Texto("Subtela de Texto", (self.caixa.centerx, self.caixa.top + 38), style={"size": 36, "align": "center"})
        titulo.draw(tela)

        self.barra_titulo.render(tela, [], dt)
        self.barra_texto.render(tela, eventos, dt)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_enviar.render(tela, eventos, dt, JOGO=JOGO)
