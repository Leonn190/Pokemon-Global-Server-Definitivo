import pygame

from Codigo.Modulos.Camera import Camera
from Codigo.Modulos.ControladorObjetos import ControladorObjetos
from Codigo.Modulos.LeitorMundo import LeitorMundo
from Codigo.Modulos.ElementosHud import ElementosHud
from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Modulos.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Modulos.Ferramentas import GerenciadorFPS
from Codigo.Telas.Config import TelaConfig, ResetTelaConfig
from Codigo.Server.ServerMundo import (
    consultar_chunks_mundo,
    consultar_estado_mundo,
    enviar_diffs_mundo_categoria,
    receber_diffs_mundo,
    desconectar_mundo,
    enviar_mensagem_terminal,
    buscar_mensagens_terminal,
)
from Codigo.Telas.Inventario.Unificador import UnificadorInventario
from Codigo.Prefabs.Terminal import Terminal


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
        self.Terminal = None

        self._montar_mundo(JOGO)

        tela_sobreposta = JOGO.INFO.pop("MundoTelaSobreposta", None)
        if tela_sobreposta == "Config":
            ResetTelaConfig()
            self.TelaAtual = "Config"


    def _aplicar_regras_servidor(self, regras: dict | None) -> None:
        if not isinstance(regras, dict):
            return
        mundo = regras.get("mundo") if isinstance(regras.get("mundo"), dict) else {}
        chunk_tiles = mundo.get("chunk_tiles")
        if chunk_tiles is not None:
            try:
                self.ControladorObjetos._chunk_tamanho_tiles = max(1, int(chunk_tiles))
            except (TypeError, ValueError):
                pass

    def _montar_mundo(self, JOGO):
        self._aplicar_regras_servidor(JOGO.INFO.get("RegrasServer"))
        dados = JOGO.INFO.get("PlayerDadosServer") or {}
        player_local = self.ControladorObjetos.montar_player_local(dados)
        self.EntidadeMain = player_local
        self.SubtelaInventario = UnificadorInventario(player_local)

        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=self.EntidadeMain, tile_px=50)
        self.LeitorMundo = LeitorMundo(
            jogo=JOGO,
            camera=self.Camera,
            callback_atualizacao=consultar_chunks_mundo,
            intervalo_poll=0.20,
            raio_chunks=4,
        )

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
            self.LeitorMundo.conectar_servidor(link)
            self.LeitorMundo.iniciar()
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))

            # Bootstrap inicial de objetos remotos já existentes próximos ao player.
            self._bootstrap_objetos_remotos_iniciais(link, client_id)

            self.ControladorObjetos.iniciar_threads_diffs(
                callback_loop_rapido=lambda diffs: self._loop_rede_diffs_rapidas(link, client_id, diffs),
                callback_loop_lento=lambda diffs: self._loop_rede_diffs_lentas(link, client_id, diffs),
                intervalo_rapido=0.05,
                intervalo_lento=5.0,
            )

    def _bootstrap_objetos_remotos_iniciais(self, link, client_id):
        """Consulta única em modo estado para receber spawns iniciais próximos."""
        resposta = consultar_estado_mundo(link, client_id, self.Camera.PosicaoTiles, raio_chunks=4)
        if not isinstance(resposta, dict):
            return

        diffs = resposta.get("diffs", [])
        if not isinstance(diffs, list):
            return

        for diff in diffs:
            if isinstance(diff, dict):
                self.ControladorObjetos.aplicar_diff(diff)

    def _loop_rede_diffs_rapidas(self, link, client_id, diffs_locais):
        """Canal rápido: envia e recebe apenas diffs visuais/dinâmicas."""
        if diffs_locais:
            enviar_diffs_mundo_categoria(link, client_id, "rapida", diffs_locais)
        resposta = receber_diffs_mundo(link, client_id, self.Camera.PosicaoTiles, categoria="rapida", raio_chunks=4)
        if not isinstance(resposta, dict):
            return []
        return resposta.get("diffs", []) if isinstance(resposta.get("diffs", []), list) else []

    def _loop_rede_diffs_lentas(self, link, client_id, diffs_locais):
        """Canal lento: envia e recebe apenas diffs persistentes."""
        if diffs_locais:
            enviar_diffs_mundo_categoria(link, client_id, "lenta", diffs_locais)
        resposta = receber_diffs_mundo(link, client_id, self.Camera.PosicaoTiles, categoria="lenta", raio_chunks=4)
        if not isinstance(resposta, dict):
            return []
        return resposta.get("diffs", []) if isinstance(resposta.get("diffs", []), list) else []

    def Tela(self, JOGO, EVENTOS, dt):
        gfps = self.GerenciadorFPS

        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()

        bloqueio_gameplay = False
        if self.Terminal is not None:
            EVENTOS = self.Terminal.processar_eventos(EVENTOS)
            bloqueio_gameplay = bool(self.Terminal.esta_digitando)

        gfps.iniciar_trecho("aplicacao_subtela")
        self.SubtelaOpcoes.processar_eventos(JOGO, EVENTOS)

        if self.ControladorObjetos.PlayerLocal is not None and self.SubtelaOpcoes.Ativa:
            self.ControladorObjetos.PlayerLocal.Controle.InventarioAberto = False

        player_bloqueado = bloqueio_gameplay or self.SubtelaOpcoes.Ativa or self.TelaAtual == "Config"
        if not player_bloqueado:
            mouse_tela = pygame.mouse.get_pos()
            mouse_mundo_tiles = self.Camera.tela_para_mundo_tiles(mouse_tela)
            self.ControladorObjetos.atualizar_player_local(EVENTOS, dt, mouse_mundo_tiles, gerenciador_fps=gfps)
        elif self.ControladorObjetos.PlayerLocal is not None and self.ControladorObjetos.PlayerLocal.Controle is not None:
            self.ControladorObjetos.PlayerLocal.Controle.atualizar_bloqueado(dt)

        if self.ControladorObjetos.PlayerLocal is not None and self.SubtelaInventario is not None:
            self.SubtelaInventario.Ativo = self.ControladorObjetos.PlayerLocal.Controle.InventarioAberto
            self.SubtelaInventario.atualizar(EVENTOS, dt, JOGO.TELA.get_size())
        gfps.finalizar_trecho("aplicacao_subtela")

        self.Camera.atualizar(dt)

        if self.ControladorObjetos.PlayerLocal is not None:
            self.LeitorMundo.atualizar_regras_mundo(self.ControladorObjetos.PlayerLocal.Controle)

        JOGO.TELA.fill((20, 20, 28))
        self.LeitorMundo.renderizar_mundo(JOGO.TELA, gerenciador_fps=gfps)

        gfps.iniciar_trecho("renderizar_objetos")
        self.ControladorObjetos.renderizar(JOGO.TELA, self.Camera)
        gfps.finalizar_trecho("renderizar_objetos")

        if self.ControladorObjetos.PlayerLocal is not None:
            self.ControladorObjetos.PlayerLocal.renderizar_stamina(JOGO.TELA, self.Camera, dt)

        if self.ControladorObjetos.PlayerLocal is not None:
            player_local = self.ControladorObjetos.PlayerLocal
            self.ElementosHud.desenhar(JOGO.TELA, player_local.Inventario, terminal=self.Terminal, eventos=EVENTOS, dt=dt)

        self.SubtelaOpcoes.desenhar(JOGO)
        if self.SubtelaInventario is not None and self.SubtelaInventario.Ativo:
            self.SubtelaInventario.desenhar(JOGO.TELA, EVENTOS, dt)
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt)

        gfps.imprimir_relatorio()


    def Finalizar(self, JOGO):
        self.ControladorObjetos.parar_threads_diffs()
        if self.Terminal is not None:
            self.Terminal.parar()
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
