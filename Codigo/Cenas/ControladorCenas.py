from Codigo.Cenas.CenaMenu import CenaMenu
from Codigo.Cenas.CenaMundo import CenaMundo
from Codigo.Cenas.CenaCombate import CenaCombate
from Codigo.Cenas.CenaCarregamento import CenaCarregamento
import pygame

from Codigo.Modulos.Sonoridades import AtualizarMusica
from Codigo.Prefabs.Texto import Texto

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG):
        self.TELA = TELA
        self.RELOGIO = RELOGIO
        self.CONFIG = CONFIG
        self.INFO = {
        }

        self.Cenas = {
            "Carregamento": CenaCarregamento(),
            "Menu": CenaMenu(),
            "Mundo": CenaMundo(),
            "Combate": CenaCombate(),
        }

        self.Escuro = 100
        self.CenaAlvo = None
        self.Cena = None
        self.Rodando = True

        self.TextoFPS = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 12),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoPing = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 44),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )

    def DefinirCena(self):
        
        if self.Cena is not None:
            self.INFO.update({"UltimaCena": self.Cena.ID})
            self.Cena.Finalizar(self)
        
        self.Cena = self.Cenas[self.CenaAlvo]
        self.CenaAlvo = None
        self.Cena.Inicializar(self)

    def Rodar(self):

        while self.Rodando:
            dt = self.RELOGIO.tick(self.CONFIG["FPS"]) / 1000.0

            EVENTOS = pygame.event.get()
            for e in EVENTOS:
                if e.type == pygame.QUIT:
                    self.Rodando = False

            self.Cena.Tela(self, EVENTOS, dt)
            self.DesenhosAdicionais()

            if self.CenaAlvo is None and self.Escuro != 0:
                self.Cena.Abertura(self, dt)

            if self.CenaAlvo is not None and self.Escuro != 100:
                self.Cena.Fechamento(self, dt)

            if self.CenaAlvo is not None and self.Escuro == 100:
                self.DefinirCena()

            AtualizarMusica()
            pygame.display.update()

    def DesenhosAdicionais(self):
        largura_tela = self.TELA.get_width()

        if self.CONFIG.get("FPS Visivel", False):
            self.TextoFPS.set_pos((largura_tela - 16, 12))
            self.TextoFPS.set_text(f"FPS: {int(self.RELOGIO.get_fps())}")
            self.TextoFPS.draw(self.TELA)

        if self.CONFIG.get("Ping Visivel", False):
            self.TextoPing.set_pos((largura_tela - 16, 44))
            self.TextoPing.set_text("Ping: 5")
            self.TextoPing.draw(self.TELA)
