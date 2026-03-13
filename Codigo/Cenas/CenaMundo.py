import pygame

from Codigo.Modulos.Camera import Camera
from Codigo.Modulos.ControladorMundo.ControladorMundo import ControladorMundo
from Codigo.Modulos.ElementosHud import ElementosHud
from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Telas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Modulos.Ferramentas import GerenciadorFPS
from Codigo.Telas.Config import TelaConfig, ResetTelaConfig
from Codigo.Server.ServerMundo import enviar_mensagem_terminal, buscar_mensagens_terminal
from Codigo.Telas.Inventario.Unificador import UnificadorInventario
from Codigo.Prefabs.Terminal import Terminal


class CenaMundo:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Mundo"

        self.Camera = None
        self.ControladorMundo = None
        self.EntidadeMain = None
        self.ElementosHud = ElementosHud()
        self.SubtelaOpcoes = SubtelaOpcoes()
        self._desconectado = False
        self.TelaAtual = None
        self.SubtelaInventario = None
        self.GerenciadorFPS = GerenciadorFPS((JOGO.CONFIG or {}).get("FPS", 60))
        self.Terminal = None

        self._montar_mundo(JOGO)

        tela_sobreposta = JOGO.INFO.pop("MundoTelaSobreposta", None)
        if tela_sobreposta == "Config":
            ResetTelaConfig()
            self.TelaAtual = "Config"

    def _montar_mundo(self, JOGO):
        dados = JOGO.INFO.get("PlayerDadosServer") or {}
        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=None, tile_px=50)
        self.ControladorMundo = ControladorMundo(jogo=JOGO, camera=self.Camera)
        player_local = self.ControladorMundo.montar_player_local(dados)
        self.EntidadeMain = player_local
        self.Camera.definir_main(self.EntidadeMain)
        self.SubtelaInventario = UnificadorInventario(player_local)

        regras = JOGO.INFO.get("RegrasServer") if isinstance(JOGO.INFO.get("RegrasServer"), dict) else {}
        mundo = regras.get("mundo") if isinstance(regras.get("mundo"), dict) else {}
        chunk_tiles = mundo.get("chunk_tiles")
        if chunk_tiles is not None:
            try:
                self.ControladorMundo.Objetos._chunk_tamanho_tiles = max(1, int(chunk_tiles))
            except (TypeError, ValueError):
                pass

        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        usuario = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        self.Terminal = Terminal(
            pygame.Rect(14, 14, 520, 220),
            callback_enviar=lambda texto: enviar_mensagem_terminal(link, usuario, texto) if link else None,
            callback_buscar=lambda ultimo_id: buscar_mensagens_terminal(link, ultimo_id=ultimo_id) if link else {"status": "ok", "mensagens": []},
            autor_local=usuario,
        )
        self.Terminal.iniciar()

        if link:
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
            self.ControladorMundo.conectar(link, client_id)

    def Tela(self, JOGO, EVENTOS, dt):
        gfps = self.GerenciadorFPS

        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()

        bloqueio_gameplay = False
        if self.Terminal is not None:
            EVENTOS = self.Terminal.processar_eventos(EVENTOS)
            bloqueio_gameplay = bool(self.Terminal.esta_digitando)

        gfps.iniciar_trecho("aplicacao_subtela")
        self.SubtelaOpcoes.processar_eventos(JOGO, EVENTOS)

        player = self.ControladorMundo.player_local
        if player is not None and self.SubtelaOpcoes.Ativa:
            player.Controle.InventarioAberto = False

        player_bloqueado = bloqueio_gameplay or self.SubtelaOpcoes.Ativa or self.TelaAtual == "Config"
        self.ControladorMundo.atualizar_frame(EVENTOS, dt, bloqueio_gameplay=player_bloqueado)

        if player is not None and self.SubtelaInventario is not None:
            self.SubtelaInventario.Ativo = player.Controle.InventarioAberto
            self.SubtelaInventario.atualizar(EVENTOS, dt, JOGO.TELA.get_size())
        gfps.finalizar_trecho("aplicacao_subtela")

        self.Camera.atualizar(dt)

        JOGO.TELA.fill((20, 20, 28))
        gfps.iniciar_trecho("renderizar_objetos")
        self.ControladorMundo.renderizar(JOGO.TELA)
        gfps.finalizar_trecho("renderizar_objetos")

        if player is not None:
            player.renderizar_stamina(JOGO.TELA, self.Camera, dt)
            self.ElementosHud.desenhar(JOGO.TELA, player.Inventario, terminal=self.Terminal, eventos=EVENTOS, dt=dt)

        self.SubtelaOpcoes.desenhar(JOGO)
        if self.SubtelaInventario is not None and self.SubtelaInventario.Ativo:
            self.SubtelaInventario.desenhar(JOGO.TELA, EVENTOS, dt)
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt)

        gfps.imprimir_relatorio()

    def Finalizar(self, JOGO):
        if self.Terminal is not None:
            self.Terminal.parar()
        if self.ControladorMundo is not None:
            server = JOGO.INFO.get("ServerSelecionado") or {}
            link = server.get("ip")
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
            self.ControladorMundo.parar(link, client_id)
        self._desconectado = True
