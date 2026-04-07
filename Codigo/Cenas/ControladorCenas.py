from Codigo.Cenas.CenaMenu import CenaMenu
from Codigo.Cenas.CenaMundo import CenaMundo
from Codigo.Cenas.CenaCombate import CenaCombate
from Codigo.Cenas.CenaCarregamento import CenaCarregamento
from Codigo.Cenas.CenaLogin import CenaLogin
import pygame

from Codigo.Modulos.Sonoridades import SISTEMA_MUSICAS
from Codigo.Modulos.EfeitosTela import aplicar_claridade, Escurecer
from Codigo.Prefabs.Texto import Texto
from Codigo.Modulos.Discord import DiscordPresence
from Codigo.Telas.Subtela import GerenciadorSubtelas
from Codigo.Modulos.PipelineGrafica import PipelineGrafica

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG):
        self.TELA = TELA
        self.RELOGIO = RELOGIO
        self.CONFIG = CONFIG
        self.INFO = {
        }
        self.FilaMensagensTecnicas = []

        self.Cenas = {
            "Carregamento": CenaCarregamento(),
            "Login": CenaLogin(),
            "Menu": CenaMenu(),
            "Mundo": CenaMundo(),
            "Combate": CenaCombate(),
        }

        self.Escuro = 100
        self.CenaAlvo = None
        self.Cena = None
        self.Rodando = True
        self.Saindo = False
        self._encerrado = False

        self.Discord = DiscordPresence()
        self.GerenciadorSubtelas = GerenciadorSubtelas()
        self.PipelineGrafica = PipelineGrafica(self.TELA)

        self.TextoFPS = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 12),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoPing = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 44),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoCoords = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 76),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoHorario = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 108),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )

    def DefinirCena(self):
        
        if self.Cena is not None:
            self.INFO.update({"UltimaCena": self.Cena.ID})
            preservando_mundo = self.Cena.ID == "Mundo" and self.CenaAlvo == "Menu" and self.INFO.get("MundoTelaSobreposta")
            retornando_para_mundo = self.Cena.ID == "Menu" and self.CenaAlvo == "Mundo"
            if not preservando_mundo and not retornando_para_mundo:
                self.Cena.Finalizar(self)
        self.GerenciadorSubtelas.limpar()
        
        alvo = self.CenaAlvo
        cena_anterior = self.Cena
        self.Cena = self.Cenas[alvo]
        self.CenaAlvo = None
        if not (alvo == "Menu" and cena_anterior is not None and cena_anterior.ID == "Login"):
            self.Escuro = 100
        self.Cena.Inicializar(self)
        self._atualizar_discord_presenca()

    def Rodar(self):

        while self.Rodando:
            dt = self.RELOGIO.tick(self.CONFIG["FPS"]) / 1000.0

            EVENTOS = pygame.event.get()
            for e in EVENTOS:
                if e.type == pygame.QUIT:
                    self.SolicitarSair()

            if self.CenaAlvo is not None and self.Escuro == 100:
                self.DefinirCena()

            eventos_cena = self.GerenciadorSubtelas.filtrar_eventos_fundo(EVENTOS)
            eventos_render = eventos_cena
            if callable(getattr(self.Cena, "atualizar_cena", None)):
                retorno_atualizacao = self.Cena.atualizar_cena(self, eventos_cena, dt)
                if isinstance(retorno_atualizacao, list):
                    eventos_render = retorno_atualizacao
            else:
                self.Cena.Tela(self, eventos_cena, dt)
            self.GerenciadorSubtelas.atualizar(self, EVENTOS, dt)
            self._atualizar_discord_presenca()

            efeito_transicao = None
            if self.Saindo:
                efeito_transicao = Escurecer
            else:
                if self.CenaAlvo is None and self.Escuro != 0:
                    efeito_transicao = self.Cena.Abertura

                if self.CenaAlvo is not None and self.Escuro != 100:
                    efeito_transicao = self.Cena.Fechamento


            self.PipelineGrafica.renderizar_frame(
                jogo=self,
                cena=self.Cena,
                eventos=eventos_render,
                dt=dt,
                render_subtelas=lambda: self.GerenciadorSubtelas.render(self.TELA, EVENTOS, dt, JOGO=self),
                render_adicionais=self.DesenharInfosAdicionais,
                aplicar_claridade=self.AplicarClaridadeGlobal,
            )
            if callable(efeito_transicao):
                efeito_transicao(self, dt)
            if self.Saindo and self.Escuro >= 100:
                self.Rodando = False
            SISTEMA_MUSICAS.atualizar_musica(self)
            pygame.display.update()

        self.Encerrar()

    def _atualizar_discord_presenca(self):
        cena_id = str(getattr(self.Cena, "ID", "Menu") or "Menu")
        if cena_id == "Mundo":
            local = "mundo"
            if getattr(self.Cena, "TelaAtual", None) == "Config":
                acao = "No mundo (configurações)"
            else:
                acao = "Explorando o mundo"
        else:
            local = "menu"
            tela = str(getattr(self.Cena, "TelaAtual", "MenuPrincipal"))
            acao = f"No menu ({tela})"

        self.Discord.atualizar(local=local, acao=acao)
    def AplicarClaridadeGlobal(self):
        aplicar_claridade(self.TELA, self.CONFIG.get("Claridade", 75))

    def SolicitarSair(self):
        self.CenaAlvo = None
        self.Saindo = True
        self.Discord.desconectar()

    def Encerrar(self):
        if self._encerrado:
            return
        if self.Cena is not None:
            self.Cena.Finalizar(self)
        self.Discord.desconectar()
        self._encerrado = True

    def DesenharInfosAdicionais(self):
        largura_tela = self.TELA.get_width()
        itens_hud = []

        if self.CONFIG.get("FPS Visivel", False):
            self.TextoFPS.set_text(f"FPS: {int(self.RELOGIO.get_fps())}")
            itens_hud.append(self.TextoFPS)

        if self.CONFIG.get("Ping Visivel", False):
            self.TextoPing.set_text("Ping: 5")
            itens_hud.append(self.TextoPing)

        if self.CONFIG.get("Cords Visiveis", False):
            entidade_main = getattr(self.Cena, "EntidadeMain", None)
            if entidade_main is not None and hasattr(entidade_main, "Posicao"):
                x, y = entidade_main.Posicao
                self.TextoCoords.set_text(f"X {x:.2f} | Y {y:.2f}")
            else:
                self.TextoCoords.set_text("--")
            itens_hud.append(self.TextoCoords)

        if self.CONFIG.get("MostrarHorario", False):
            if hasattr(self.Cena, "ControladorMundo") and getattr(self.Cena, "ControladorMundo", None) is not None:
                tempo = self.Cena.ControladorMundo.tempo_mundo_atual()
                if "dia" in tempo and "hora" in tempo and "minuto" in tempo:
                    dia = int(tempo.get("dia", 0) or 0)
                    hora = int(tempo.get("hora", 0) or 0)
                    minuto = int(tempo.get("minuto", 0) or 0)
                    self.TextoHorario.set_text(f"Dia {dia} | {hora:02d}:{minuto:02d}")
                else:
                    self.TextoHorario.set_text("Dia -- | --:--")
            else:
                self.TextoHorario.set_text("Dia -- | --:--")
            itens_hud.append(self.TextoHorario)

        y_base = 12
        espaco = 32
        for idx, texto in enumerate(itens_hud):
            texto.set_pos((largura_tela - 16, y_base + idx * espaco))
            texto.draw(self.TELA)


    def DesenhosAdicionais(self):
        self.DesenharInfosAdicionais()
