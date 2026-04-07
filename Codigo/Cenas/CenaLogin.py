from Codigo.Modulos.EfeitosTela import Clarear, Escurecer
from Codigo.Telas.TelaLogin import ReiniciarTelaLogin, TelaLogin


class CenaLogin:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Login"
        self._frame_surface = None

    def _garantir_frame_surface(self, jogo):
        tamanho = jogo.TELA.get_size()
        if self._frame_surface is None or self._frame_surface.get_size() != tamanho:
            self._frame_surface = jogo.TELA.copy()

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        self._garantir_frame_surface(JOGO)
        tela_real = JOGO.TELA
        JOGO.TELA = self._frame_surface
        try:
            TelaLogin(self, JOGO, EVENTOS, dt)
        finally:
            JOGO.TELA = tela_real

    def tela_atual_eh_complexa(self) -> bool:
        return False

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        _ = (EVENTOS, dt)
        self._garantir_frame_surface(JOGO)
        surface.blit(self._frame_surface, (0, 0))

    def Tela(self, JOGO, EVENTOS, dt):
        TelaLogin(self, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        ReiniciarTelaLogin()
