import pygame
from pathlib import Path

from Codigo.Modulos.EfeitosTela import Clarear, Escurecer
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Imagem import Imagem


class CenaMenu:
    def Inicializar(self, JOGO):
        self.TelaAtiva = self.Tela
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Menu"

        largura_tela, altura_tela = JOGO.TELA.get_size()

        caminho_fundo = Path("Recursos/Visual/Fundos/FundoMenu.jpg")
        self.Fundo = pygame.image.load(str(caminho_fundo)).convert()
        self.FundoLargura, self.FundoAltura = self.Fundo.get_size()
        self.FundoOffsetX = 0.0
        self.FundoDirecao = 1
        self.FundoVelocidade = 26.0

        caminho_logo = Path("Recursos/Visual/Icones/GlobalServer/Logo.png")
        logo_surface = pygame.image.load(str(caminho_logo)).convert_alpha()

        largura_logo = min(int(largura_tela * 0.48), logo_surface.get_width())
        altura_logo = int(logo_surface.get_height() * (largura_logo / logo_surface.get_width()))

        self.Logo = Imagem(
            logo_surface,
            pos=(largura_tela // 2, int(altura_tela * 0.23)),
            align="center",
            scale=(largura_logo, altura_logo),
            efeito=True,
            duracao=2.4,
            largura_faixa=0.24,
            intensidade=0.92,
            angulo_graus=-18,
            alpha_base=160,
        )

        pasta_textura = Path("Recursos/Visual/Texturas/TexturaCosmica")
        frames_textura = sorted(pasta_textura.glob("gif_frame*.png"), key=lambda p: int(p.stem.replace("gif_frame", "")))
        frames_hover = [
            pygame.image.load(str(frame)).convert_alpha()
            for i, frame in enumerate(frames_textura)
            if i % 6 == 0
        ]
        textura_base = frames_hover[0] if frames_hover else None

        estilo_botao = {
            "radius": 22,
            "border_width": 2,
            "border": (22, 26, 40),
            "border_hover": (252, 234, 125),
            "bg": (18, 20, 30),
            "bg_hover": (38, 44, 66),
            "bg_pressed": (16, 19, 28),
            "bg_image": textura_base,
            "bg_frames_hover": frames_hover,
            "bg_frames_fps": 20,
            "hover_scale": 1.08,
            "hover_speed": 14.0,
            "press_scale": 0.97,
            "text_style": {
                "size": 40,
                "color": (245, 246, 255),
                "hover_color": (255, 232, 80),
                "hover_speed": 28.0,
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 2,
                "shadow": True,
                "shadow_color": (0, 0, 0, 170),
                "shadow_offset": (2, 2),
            },
        }

        largura_botao = 480
        altura_botao = 108
        espacamento = 28
        inicio_y = int(altura_tela * 0.50)
        x = (largura_tela - largura_botao) // 2

        self.Botoes = [
            Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 0, largura_botao, altura_botao), "Jogar", style=estilo_botao),
            Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 1, largura_botao, altura_botao), "Configurações", style=estilo_botao),
            Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 2, largura_botao, altura_botao), "Sair", style=estilo_botao),
        ]

    def Loop(self, JOGO):

        dt = JOGO.RELOGIO.tick(JOGO.CONFIG["FPS"]) / 1000.0

        EVENTOS = pygame.event.get()
        for e in EVENTOS:
            if e.type == pygame.QUIT:
                JOGO.Rodando = False

        self.TelaAtiva(JOGO, EVENTOS, dt)

        if JOGO.CenaAlvo is None and JOGO.Escuro != 0:
            self.Abertura(JOGO, dt)

        if JOGO.CenaAlvo is not None and JOGO.Escuro != 100:
            self.Fechamento(JOGO, dt)

        if JOGO.CenaAlvo is not None and JOGO.Escuro == 100:
            JOGO.DefinirCena()

        pygame.display.update()
        JOGO.RELOGIO.tick(JOGO.CONFIG["FPS"])

    def _desenhar_fundo(self, JOGO, dt):
        largura_tela, altura_tela = JOGO.TELA.get_size()

        max_offset = max(self.FundoLargura, largura_tela)
        self.FundoOffsetX += self.FundoVelocidade * dt * self.FundoDirecao
        if self.FundoOffsetX >= max_offset:
            self.FundoOffsetX = max_offset
            self.FundoDirecao = -1
        elif self.FundoOffsetX <= 0:
            self.FundoOffsetX = 0
            self.FundoDirecao = 1

        x_base = int(self.FundoOffsetX)

        for x in (-x_base, self.FundoLargura - x_base):
            for y in range(0, altura_tela, self.FundoAltura):
                JOGO.TELA.blit(self.Fundo, (x, y))

        if self.FundoAltura != altura_tela:
            overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 70))
            JOGO.TELA.blit(overlay, (0, 0))

    def Tela(self, JOGO, EVENTOS, dt):
        self._desenhar_fundo(JOGO, dt)

        self.Logo.draw(JOGO.TELA, dt)

        for botao in self.Botoes:
            botao.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)

    def Finalizar(self, JOGO):
        pass
