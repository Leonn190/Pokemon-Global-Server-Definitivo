from Codigo.Modulos.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.TelaLogin import TelaLogin


class CenaLogin:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Login"

    def Tela(self, JOGO, EVENTOS, dt):
        TelaLogin(self, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        pass
