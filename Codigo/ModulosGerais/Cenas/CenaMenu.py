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
        self._menu_logo_shader_rect = None
        self._menu_logo_shader_time = 0.0

        JOGO.INFO.pop("PreservarMusicaAtual", False)

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = tela

    def _desenhar_menu(self, JOGO, EVENTOS, dt, tela_destino=None, camada="tudo"):
        if self.TelaAtual == "Servers":
            TelaServers(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)
            return

        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)
            return

        if self.TelaAtual == "Operador":
            TelaOperador(self, JOGO, EVENTOS, dt, tela_destino=tela_destino)
            return

        TelaMenu(self, JOGO, EVENTOS, dt, tela_destino=tela_destino, camada=camada)

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)

    def tela_atual_eh_complexa(self) -> bool:
        # MenuPrincipal vira cena complexa para separar:
        # scene = fundo/botoes, hud = logo com alpha.
        # Assim o shader consegue fazer bloom/fumaca usando a logo como mascara.
        return self.TelaAtual == "MenuPrincipal"

    def render_base_limpa_surface(self) -> bool:
        return False

    def render_base(self, surface, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=surface, camada="base")

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=surface, camada="hud")

    def coletar_efeito_shader(self, JOGO, dt, scene_size):
        _ = (JOGO, dt, scene_size)
        if self.TelaAtual != "MenuPrincipal" or self._menu_logo_shader_rect is None:
            return None

        return {
            "tipo": "menu_logo",
            "ativo": True,
            "time": float(self._menu_logo_shader_time),
            "menu_logo_rect": self._menu_logo_shader_rect,
            "menu_logo_power": 1.0,
        }

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=surface, camada="tudo")

    def Tela(self, JOGO, EVENTOS, dt):
        self._desenhar_menu(JOGO, EVENTOS, dt, tela_destino=JOGO.TELA, camada="tudo")

    def Finalizar(self, JOGO):
        pass
