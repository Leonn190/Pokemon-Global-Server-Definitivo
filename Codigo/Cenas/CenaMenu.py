from Codigo.Modulos.Sonoridades import Musica
from Codigo.Modulos.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.TelaMenu import TelaMenu

class CenaMenu:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Menu"

        Musica("Menu")

    def Tela(self, JOGO, EVENTOS, dt):
        TelaMenu(JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        pass
