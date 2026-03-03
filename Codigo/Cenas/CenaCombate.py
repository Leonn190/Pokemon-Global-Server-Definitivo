from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris


class CenaCombate:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Combate"

    def Tela(self, JOGO, EVENTOS, dt):
        JOGO.TELA.fill((20, 20, 28))

    def Finalizar(self, JOGO):
        pass
