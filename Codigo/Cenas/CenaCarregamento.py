from Codigo.Modulos.EfeitosTela import Clarear, Escurecer


class CenaCarregamento:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Carregamento"

    def Tela(self, JOGO, EVENTOS, dt):
        JOGO.TELA.fill((20, 20, 28))

    def Finalizar(self, JOGO):
        pass
