import time

from Codigo.ModulosGerais.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.TelaConfig import TelaConfig, ResetTelaConfig
from Codigo.Telas.TelaMenu import TelaMenu, TelaMenuGL
from Codigo.Telas.TelaOperador import TelaOperador
from Codigo.Telas.TelaServers import TelaServers


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

    def render_gl(self, renderer, JOGO, EVENTOS, dt):
        if self.TelaAtual != "MenuPrincipal":
            return False
        inicio = time.perf_counter()
        try:
            TelaMenuGL(self, JOGO, EVENTOS, dt, renderer)
            return True
        finally:
            if isinstance(getattr(JOGO, "INFO", None), dict):
                JOGO.INFO["MenuRenderMs"] = round((time.perf_counter() - inicio) * 1000.0, 3)

    def Tela(self, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=JOGO.TELA)

    def Finalizar(self, JOGO):
        pass
