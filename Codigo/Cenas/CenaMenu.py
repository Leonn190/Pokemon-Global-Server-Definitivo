from Codigo.ModulosGerais.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.Telas.TelaMenu import TelaMenu
from Codigo.Telas.Telas.TelaServers import TelaServers
from Codigo.Telas.Telas.TelaConfig import TelaConfig, ResetTelaConfig
from Codigo.Telas.Telas.TelaOperador import TelaOperador


class CenaMenu:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Menu"
        self.TelaAtual = str(JOGO.INFO.pop("MenuTelaInicial", "MenuPrincipal"))

        JOGO.INFO.pop("PreservarMusicaAtual", False)

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = tela

    def _desenhar_menu(self, JOGO, EVENTOS, dt, tela_destino=None):
        if self.TelaAtual == "Servers":
            TelaServers(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)
            return

        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)
            return

        if self.TelaAtual == "Operador":
            TelaOperador(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)
            return

        TelaMenu(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)

    def tela_atual_eh_complexa(self) -> bool:
        return False

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=surface)

    def Tela(self, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=JOGO.TELA)

    def Finalizar(self, JOGO):
        pass
