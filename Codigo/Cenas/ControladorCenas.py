from Codigo.Cenas.CenaMenu import CenaMenu
from Codigo.Cenas.CenaMundo import CenaMundo
from Codigo.Cenas.CenaCombate import CenaCombate
from Codigo.Cenas.CenaCarregamento import CenaCarregamento
from Codigo.Cenas.CenaLogin import CenaLogin
import pygame

from Codigo.Modulos.Sonoridades import AtualizarMusica
from Codigo.Modulos.EfeitosTela import aplicar_claridade, Escurecer
from Codigo.Prefabs.Texto import Texto
from Codigo.Modulos.Discord import DiscordPresence

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG):
        self.TELA = TELA
        self.RELOGIO = RELOGIO
        self.CONFIG = CONFIG
        self.INFO = {
        }
        self.FilaMensagensTecnicas = []

        self.Cenas = {
            "Carregamento": CenaCarregamento(),
            "Login": CenaLogin(),
            "Menu": CenaMenu(),
            "Mundo": CenaMundo(),
            "Combate": CenaCombate(),
        }

        self.Escuro = 100
        self.CenaAlvo = None
        self.Cena = None
        self.Rodando = True
        self.Saindo = False

        self.Discord = DiscordPresence()
        self.Discord.conectar()

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
        self.TextoCoords = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 76),
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
            preservando_mundo = self.Cena.ID == "Mundo" and self.CenaAlvo == "Menu" and self.INFO.get("MundoTelaSobreposta")
            retornando_para_mundo = self.Cena.ID == "Menu" and self.CenaAlvo == "Mundo"
            if not preservando_mundo and not retornando_para_mundo:
                self.Cena.Finalizar(self)
        
        alvo = self.CenaAlvo
        cena_anterior = self.Cena
        self.Cena = self.Cenas[alvo]
        self.CenaAlvo = None
        if not (alvo == "Menu" and cena_anterior is not None and cena_anterior.ID == "Login"):
            self.Escuro = 100
        self.Cena.Inicializar(self)
        self._atualizar_discord_presenca()

    def Rodar(self):

        while self.Rodando:
            dt = self.RELOGIO.tick(self.CONFIG["FPS"]) / 1000.0

            EVENTOS = pygame.event.get()
            for e in EVENTOS:
                if e.type == pygame.QUIT:
                    self.SolicitarSair()

            self.Cena.Tela(self, EVENTOS, dt)
            self._atualizar_discord_presenca()

            if self.Saindo:
                Escurecer(self, dt)
                if self.Escuro >= 100:
                    self.Rodando = False
            else:
                if self.CenaAlvo is None and self.Escuro != 0:
                    self.Cena.Abertura(self, dt)

                if self.CenaAlvo is not None and self.Escuro != 100:
                    self.Cena.Fechamento(self, dt)

                if self.CenaAlvo is not None and self.Escuro == 100:
                    self.DefinirCena()

            self.DesenhosAdicionais()
            AtualizarMusica()
            pygame.display.update()

        if self.Cena is not None:
            self.Cena.Finalizar(self)
        self.Discord.desconectar()

    def _atualizar_discord_presenca(self):
        cena_id = str(getattr(self.Cena, "ID", "Menu") or "Menu")
        if cena_id == "Mundo":
            local = "mundo"
            if getattr(self.Cena, "TelaAtual", None) == "Config":
                acao = "No mundo (configurações)"
            else:
                acao = "Explorando o mundo"
        else:
            local = "menu"
            tela = str(getattr(self.Cena, "TelaAtual", "MenuPrincipal"))
            acao = f"No menu ({tela})"

        self.Discord.atualizar(local=local, acao=acao)

    def SolicitarSair(self):
        self.CenaAlvo = None
        self.Saindo = True

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

        if self.CONFIG.get("Cords Visiveis", False):
            entidade_main = getattr(self.Cena, "EntidadeMain", None)
            if entidade_main is not None and hasattr(entidade_main, "Posicao"):
                x, y = entidade_main.Posicao
                self.TextoCoords.set_text(f"Cords: X {x:.2f} | Y {y:.2f}")
            else:
                self.TextoCoords.set_text("Cords: --")
            self.TextoCoords.set_pos((largura_tela - 16, 76))
            self.TextoCoords.draw(self.TELA)

        aplicar_claridade(self.TELA, self.CONFIG.get("Claridade", 75))
