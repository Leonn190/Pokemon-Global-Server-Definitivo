from Codigo.Cenas.CenaMenu import CenaMenu
from Codigo.Cenas.CenaMundo import CenaMundo
from Codigo.Cenas.CenaCombate import CenaCombate
from Codigo.Cenas.CenaCarregamento import CenaCarregamento
from Codigo.Cenas.CenaLogin import CenaLogin
import pygame
import time
import threading
import shutil
from pathlib import Path

from Codigo.ModulosGerais.Sonoridades import SISTEMA_MUSICAS
from Codigo.ModulosGerais.EfeitosTela import aplicar_claridade, Escurecer
from Codigo.Prefabs.Texto import Texto
from Codigo.ModulosGerais.Discord import DiscordPresence
from Codigo.Telas.Subtelas.Subtela import GerenciadorSubtelas
from Codigo.ModulosGerais.PipelineGrafica import PipelineGrafica

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG, tela_display=None, janela_opengl=False):
        self.TELA = TELA
        self.TelaDisplay = tela_display if tela_display is not None else TELA
        self.JanelaOpenGL = bool(janela_opengl)
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
        self._preparacao_alvo = None
        self._preparacao_thread = None

        self.Discord = DiscordPresence()
        self.GerenciadorSubtelas = GerenciadorSubtelas()
        self.PipelineGrafica = PipelineGrafica(self.TELA, tela_display=self.TelaDisplay)
        if self.JanelaOpenGL and not self.PipelineGrafica.shader_disponivel():
            self.TelaDisplay = pygame.display.set_mode(self.TELA.get_size(), pygame.NOFRAME)
            self.JanelaOpenGL = False
            self.PipelineGrafica = PipelineGrafica(self.TELA, tela_display=self.TelaDisplay)
        self.INFO["ShaderSuportado"] = self.PipelineGrafica.shader_disponivel()
        self.INFO["ShaderFallback"] = self.PipelineGrafica.motivo_fallback()

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
        self._preparacao_alvo = None
        self._preparacao_thread = None
        if not (alvo == "Menu" and cena_anterior is not None and cena_anterior.ID == "Login"):
            self.Escuro = 100
        self.Cena.Inicializar(self)
        self._atualizar_discord_presenca()

    def _garantir_preparacao_transicao(self):
        alvo = self.CenaAlvo
        if alvo is None:
            self._preparacao_alvo = None
            self._preparacao_thread = None
            return
        if self._preparacao_alvo == alvo:
            return
        if alvo == "Mundo" and isinstance(self.INFO.get("MundoPreparadoTransicao"), dict):
            self._preparacao_alvo = alvo
            self._preparacao_thread = None
            return
        self._preparacao_alvo = alvo
        self._preparacao_thread = None
        cena_alvo = self.Cenas.get(str(alvo))
        preparar = getattr(cena_alvo, "PrepararTransicaoAssincrona", None) if cena_alvo is not None else None
        if not callable(preparar):
            return

        def _worker():
            try:
                preparar(self)
            except Exception as exc:
                self.INFO["UltimoErroPreparacaoCena"] = str(exc)

        self._preparacao_thread = threading.Thread(target=_worker, name=f"PreparacaoCena{alvo}", daemon=True)
        self._preparacao_thread.start()

    def _preparacao_transicao_concluida(self) -> bool:
        if self.CenaAlvo is None:
            return False
        if self._preparacao_alvo != self.CenaAlvo:
            return False
        return self._preparacao_thread is None or (not self._preparacao_thread.is_alive())

    def Rodar(self):

        while self.Rodando:
            dt = self.RELOGIO.tick(self.CONFIG["FPS"]) / 1000.0

            EVENTOS = pygame.event.get()
            for e in EVENTOS:
                if e.type == pygame.QUIT:
                    self.SolicitarSair()

            if self.CenaAlvo is not None and self.Escuro == 100:
                self._garantir_preparacao_transicao()
            if self.CenaAlvo is not None and self.Escuro == 100 and self._preparacao_transicao_concluida():
                self.DefinirCena()

            eventos_cena = self.GerenciadorSubtelas.filtrar_eventos_fundo(EVENTOS)
            eventos_render = eventos_cena
            if callable(getattr(self.Cena, "atualizar_cena", None)):
                retorno_atualizacao = self.Cena.atualizar_cena(self, eventos_cena, dt)
                if isinstance(retorno_atualizacao, list):
                    eventos_render = retorno_atualizacao
            self.GerenciadorSubtelas.atualizar(self, EVENTOS, dt)
            self._atualizar_discord_presenca()

            efeito_transicao = None
            if self.Saindo:
                efeito_transicao = Escurecer
            else:
                if self.CenaAlvo is None and self.Escuro != 0:
                    efeito_transicao = self.Cena.Abertura

                if self.CenaAlvo is not None:
                    efeito_transicao = self.Cena.Fechamento


            self.PipelineGrafica.renderizar_frame(
                jogo=self,
                cena=self.Cena,
                eventos=eventos_render,
                dt=dt,
                render_subtelas_scene=lambda surface: self.GerenciadorSubtelas.render(surface, EVENTOS, dt, JOGO=self, camada="scene"),
                render_subtelas_hud=lambda surface: self.GerenciadorSubtelas.render(surface, EVENTOS, dt, JOGO=self, camada="hud"),
                render_adicionais=self.DesenharInfosAdicionais,
                aplicar_claridade=self.AplicarClaridadeGlobal,
                render_transicao=(lambda _surface: efeito_transicao(self, dt)) if callable(efeito_transicao) else None,
            )
            if self.Saindo and self.Escuro >= 100:
                self.Rodando = False
            SISTEMA_MUSICAS.atualizar_musica(self)
            pygame.display.flip()
            time.sleep(0)

        self.Encerrar()

    def _atualizar_discord_presenca(self):
        if self.Saindo or self.Cena is None:
            self.Discord.desconectar()
            return

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

    def AplicarClaridadeGlobal(self, tela=None):
        bloquear = getattr(self.Cena, "bloquear_claridade_global", None)
        if callable(bloquear) and bool(bloquear()):
            return
        aplicar_claridade(self.TELA if tela is None else tela, self.CONFIG.get("Claridade", 75))

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
        self.PipelineGrafica.liberar()
        try:
            shutil.rmtree(Path("RAM") / "ImagensMapa", ignore_errors=True)
        except Exception:
            pass
        self._encerrado = True

    def DesenharInfosAdicionais(self, tela=None):
        if isinstance(getattr(self, "INFO", None), dict) and self.INFO.get("CreditosAtivos"):
            return
        destino = self.TELA if tela is None else tela
        largura_tela = destino.get_width()
        deslocamento_direita = 0
        cena_id = str(getattr(self.Cena, "ID", "") or "")
        somente_fps = cena_id == "Menu"
        if bool(self.CONFIG.get("MostrarMinimapa", False)) and cena_id == "Mundo":
            deslocamento_direita = 210
        itens_hud = []

        if self.CONFIG.get("FPS Visivel", False):
            self.TextoFPS.set_text(f"FPS: {int(self.RELOGIO.get_fps())}")
            itens_hud.append(self.TextoFPS)

        if not somente_fps and self.CONFIG.get("Ping Visivel", False):
            self.TextoPing.set_text("Ping: 5")
            itens_hud.append(self.TextoPing)

        if not somente_fps and self.CONFIG.get("Cords Visiveis", False):
            entidade_main = getattr(self.Cena, "EntidadeMain", None)
            if entidade_main is not None and hasattr(entidade_main, "Posicao"):
                x, y = entidade_main.Posicao
                self.TextoCoords.set_text(f"X {x:.2f} | Y {y:.2f}")
            else:
                self.TextoCoords.set_text("--")
            itens_hud.append(self.TextoCoords)

        if not somente_fps and self.CONFIG.get("MostrarHorario", False):
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
            texto.set_pos((largura_tela - 16 - deslocamento_direita, y_base + idx * espaco))
            texto.draw(destino)


    def DesenhosAdicionais(self):
        self.DesenharInfosAdicionais()
