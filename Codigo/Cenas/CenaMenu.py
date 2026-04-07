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
        self._frame_surface = None

        JOGO.INFO.pop("PreservarMusicaAtual", False)

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = tela

    def _garantir_frame_surface(self, jogo):
        tamanho = jogo.TELA.get_size()
        if self._frame_surface is None or self._frame_surface.get_size() != tamanho:
            self._frame_surface = jogo.TELA.copy()

    def _desenhar_menu(self, JOGO, EVENTOS, dt):
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

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        self._garantir_frame_surface(JOGO)
        tela_real = JOGO.TELA
        JOGO.TELA = self._frame_surface
        try:
            self._desenhar_menu(JOGO, EVENTOS, dt)
        finally:
            JOGO.TELA = tela_real

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        _ = (EVENTOS, dt)
        self._garantir_frame_surface(JOGO)
        surface.blit(self._frame_surface, (0, 0))

    def Tela(self, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        pass
