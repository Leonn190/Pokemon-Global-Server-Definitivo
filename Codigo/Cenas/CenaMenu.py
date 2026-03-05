import random

from Codigo.Modulos.Sonoridades import Musica
from Codigo.Modulos.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.TelaMenu import TelaMenu
from Codigo.Telas.TelaServers import TelaServers
from Codigo.Telas.Config import TelaConfig, ResetTelaConfig
from Codigo.Telas.TelaOperador import TelaOperador


class CenaMenu:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Menu"
        self.TelaAtual = str(JOGO.INFO.pop("MenuTelaInicial", "MenuPrincipal"))

        Musica(random.choice(["Menu1","Menu2","Menu3"]))

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = tela

    def Tela(self, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Servers":
            TelaServers(self, JOGO, EVENTOS, dt)
            return

        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt)
            return

        if self.TelaAtual == "Operador":
            TelaOperador(self, JOGO, EVENTOS, dt)
            return

        TelaMenu(self, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        pass
