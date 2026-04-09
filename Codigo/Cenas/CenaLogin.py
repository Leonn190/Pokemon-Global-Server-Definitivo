from Codigo.ModulosGerais.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.TelaLogin import ReiniciarTelaLogin, TelaLogin


class CenaLogin:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Login"

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)

    def tela_atual_eh_complexa(self) -> bool:
        return False

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        TelaLogin(self, JOGO, EVENTOS, dt, tela_destino=surface)

    def Tela(self, JOGO, EVENTOS, dt):
        TelaLogin(self, JOGO, EVENTOS, dt, tela_destino=JOGO.TELA)

    def Finalizar(self, JOGO):
        ReiniciarTelaLogin()
