import pygame

from Codigo.Modulos.Camera import Camera
from Codigo.Modulos.ControladorObjetos import ControladorObjetos
from Codigo.Modulos.LeitorMundo import LeitorMundo
from Codigo.Modulos.ElementosHud import ElementosHud
from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Modulos.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Modulos.Ferramentas import GerenciadorFPS
from Codigo.Telas.Config import TelaConfig, ResetTelaConfig
from Codigo.Server.ServerMundo import consultar_estado_mundo, enviar_diffs_mundo, desconectar_mundo
from Codigo.Telas.Inventario.Unificador import UnificadorInventario


class CenaMundo:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Mundo"

        self.Camera = None
        self.LeitorMundo = None
        self.ControladorObjetos = ControladorObjetos()
        self.EntidadeMain = None
        self.ElementosHud = ElementosHud()
        self.SubtelaOpcoes = SubtelaOpcoes()
        self._desconectado = False
        self.TelaAtual = None
        self.SubtelaInventario = None
        self.GerenciadorFPS = GerenciadorFPS((JOGO.CONFIG or {}).get("FPS", 60))

        self._montar_mundo(JOGO)

        tela_sobreposta = JOGO.INFO.pop("MundoTelaSobreposta", None)
        if tela_sobreposta == "Config":
            ResetTelaConfig()
            self.TelaAtual = "Config"

    def _montar_mundo(self, JOGO):
        dados = JOGO.INFO.get("PlayerDadosServer") or {}
        player_local = self.ControladorObjetos.montar_player_local(dados)
        self.EntidadeMain = player_local.Ator
        self.SubtelaInventario = UnificadorInventario(player_local.Inventario)

        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=self.EntidadeMain, tile_px=50)
        self.LeitorMundo = LeitorMundo(
            jogo=JOGO,
            camera=self.Camera,
            callback_atualizacao=consultar_estado_mundo,
            intervalo_poll=0.20,
            raio_chunks=10,
        )

        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        if link:
            self.LeitorMundo.conectar_servidor(link)
            self.LeitorMundo.iniciar()
            self.ControladorObjetos.iniciar_thread_envio_diffs(
                lambda diffs: enviar_diffs_mundo(link, str(JOGO.INFO.get("UsuarioLogado", "anon")), diffs),
                intervalo=0.05,
            )

    def Tela(self, JOGO, EVENTOS, dt):
        gfps = self.GerenciadorFPS

        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()

        gfps.iniciar_trecho("aplicacao_subtela")
        self.SubtelaOpcoes.processar_eventos(JOGO, EVENTOS)

        if not self.SubtelaOpcoes.Ativa and self.TelaAtual != "Config":
            mouse_tela = pygame.mouse.get_pos()
            mouse_mundo_tiles = self.Camera.tela_para_mundo_tiles(mouse_tela)
            self.ControladorObjetos.atualizar_player_local(EVENTOS, dt, mouse_mundo_tiles, gerenciador_fps=gfps)
            if self.ControladorObjetos.PlayerLocal is not None and self.SubtelaInventario is not None:
                self.SubtelaInventario.Ativo = self.ControladorObjetos.PlayerLocal.Controle.InventarioAberto
                self.SubtelaInventario.atualizar(EVENTOS, dt, JOGO.TELA.get_size())
        gfps.finalizar_trecho("aplicacao_subtela")

        self.Camera.atualizar(dt)

        for diff in self.LeitorMundo.consumir_diffs_recebidas():
            self.ControladorObjetos.aplicar_diff(diff)

        if self.ControladorObjetos.PlayerLocal is not None:
            self.LeitorMundo.atualizar_regras_mundo(self.ControladorObjetos.PlayerLocal.Controle)

        JOGO.TELA.fill((20, 20, 28))
        self.LeitorMundo.renderizar_mundo(JOGO.TELA, gerenciador_fps=gfps)

        gfps.iniciar_trecho("renderizar_player")
        self.ControladorObjetos.renderizar_player(JOGO.TELA, self.Camera)
        gfps.finalizar_trecho("renderizar_player")

        if self.ControladorObjetos.PlayerLocal is not None:
            self.ControladorObjetos.PlayerLocal.Controle.renderizar_stamina(JOGO.TELA, self.Camera, dt)

        gfps.iniciar_trecho("renderizar_estruturas")
        self.ControladorObjetos.renderizar_estruturas(JOGO.TELA, self.Camera)
        gfps.finalizar_trecho("renderizar_estruturas")

        if self.ControladorObjetos.PlayerLocal is not None:
            player_local = self.ControladorObjetos.PlayerLocal
            self.ElementosHud.desenhar(JOGO.TELA, player_local.Inventario)

        self.SubtelaOpcoes.desenhar(JOGO)
        if self.SubtelaInventario is not None and self.SubtelaInventario.Ativo:
            self.SubtelaInventario.desenhar(JOGO.TELA, EVENTOS, dt)
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt)

        gfps.imprimir_relatorio()


    def Finalizar(self, JOGO):
        self.ControladorObjetos.parar_thread_envio_diffs()
        if self.LeitorMundo:
            self.LeitorMundo.parar()
        self._desconectar_do_mundo(JOGO)

    def _desconectar_do_mundo(self, JOGO):
        if self._desconectado:
            return
        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        if link:
            desconectar_mundo(link, client_id)
        self._desconectado = True
