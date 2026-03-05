import os

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Modulos.Camera import Camera
from Codigo.Modulos.ControladorObjetos import ControladorObjetos
from Codigo.Modulos.LeitorMundo import LeitorMundo
from Codigo.Modulos.Player.Player import Player
from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Modulos.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Telas.Config import TelaConfig, ResetTelaConfig
from Codigo.Server.ServerMundo import consultar_estado_mundo, enviar_diffs_mundo, desconectar_mundo


class CenaMundo:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Mundo"

        self.Camera = None
        self.LeitorMundo = None
        self.ControladorObjetos = ControladorObjetos()
        self.EntidadeMain = None
        self.Player = None
        self.SubtelaOpcoes = SubtelaOpcoes()
        self._desconectado = False
        self.TelaAtual = None

        self._montar_mundo(JOGO)

        tela_sobreposta = JOGO.INFO.pop("MundoTelaSobreposta", None)
        if tela_sobreposta == "Config":
            ResetTelaConfig()
            self.TelaAtual = "Config"

    def _carregar_skin(self, nome_skin):
        if not nome_skin:
            nome_skin = "S1"
        if not nome_skin.endswith(".png"):
            nome_skin = nome_skin + ".png"
        caminho = os.path.join("Recursos", "Visual", "Skins", "Liberadas", nome_skin)
        try:
            return pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
            fallback.fill((190, 220, 255))
            return fallback

    def _montar_mundo(self, JOGO):
        dados = JOGO.INFO.get("PlayerDadosServer") or {}
        skin = self._carregar_skin(str(dados.get("skin", "S1.png")))

        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)

        self.EntidadeMain = Ator(skin_surface=skin, posicao=(float(pos[0]), float(pos[1])), escala_skin=1.45)
        if dados.get("id") is not None:
            self.EntidadeMain.Id = int(dados.get("id"))

        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=self.EntidadeMain)
        self.LeitorMundo = LeitorMundo(
            jogo=JOGO,
            camera=self.Camera,
            callback_atualizacao=consultar_estado_mundo,
            callback_envio_diffs=enviar_diffs_mundo,
            intervalo_poll=0.20,
            raio_chunks=10,
        )

        self.Player = Player(
            ator=self.EntidadeMain,
            callback_diff=self.ControladorObjetos.registrar_diff_local,
            velocidade_tiles=4.8,
        )
        self.Player.Perfil.aplicar_serializado(dados)
        self.ControladorObjetos.definir_player_local(self.Player)
        self._sincronizar_player_no_controlador()

        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        if link:
            self.LeitorMundo.conectar_servidor(link)
            self.LeitorMundo.iniciar()

    def Tela(self, JOGO, EVENTOS, dt):
        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()

        self.SubtelaOpcoes.processar_eventos(JOGO, EVENTOS)

        if not self.SubtelaOpcoes.Ativa and self.TelaAtual != "Config":
            mouse_tela = pygame.mouse.get_pos()
            mouse_mundo_tiles = self.Camera.tela_para_mundo_tiles(mouse_tela)
            self.ControladorObjetos.atualizar_player_local(EVENTOS, dt, mouse_mundo_tiles)

        self.Camera.atualizar(dt)
        self.ControladorObjetos.enviar_diffs_pendentes(self.LeitorMundo.enfileirar_diff)

        for diff in self.LeitorMundo.consumir_diffs_recebidas():
            self.ControladorObjetos.aplicar_diff(diff)

        self._atualizar_limites_loop_mundo()
        self._atualizar_grid_chunks_player()
        self._sincronizar_player_no_controlador()

        JOGO.TELA.fill((20, 20, 28))
        self.LeitorMundo.renderizar_mundo(JOGO.TELA)
        self.ControladorObjetos.renderizar(JOGO.TELA, self.Camera)

        self.Player.Controle.renderizar_stamina(JOGO.TELA, self.Camera, dt)
        self.Player.Hud.desenhar(JOGO.TELA, self.Player.Inventario)

        self.SubtelaOpcoes.desenhar(JOGO)
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt)


    def _atualizar_limites_loop_mundo(self):
        if not self.Player or not self.LeitorMundo:
            return
        estado = self.LeitorMundo.snapshot()
        meta = estado.get("meta", {}) if isinstance(estado, dict) else {}
        if not isinstance(meta, dict):
            return
        largura = meta.get("largura_blocos")
        altura = meta.get("altura_blocos")
        if largura is None or altura is None:
            return
        self.Player.Controle.definir_limites_mundo(largura, altura)
        if self.Camera:
            self.Camera.definir_limites_mundo(largura, altura)

    def _atualizar_grid_chunks_player(self):
        if not self.Player or not self.LeitorMundo:
            return
        estado = self.LeitorMundo.snapshot()
        chunks = estado.get("chunks", {}) if isinstance(estado, dict) else {}
        if not isinstance(chunks, dict):
            chunks = {}
        self.Player.Controle.definir_grid_chunks(chunks, self.LeitorMundo.TamanhoChunkBlocos)

    def _sincronizar_player_no_controlador(self):
        if not self.ControladorObjetos or not self.EntidadeMain:
            return
        player_id = getattr(self.EntidadeMain, "Id", None)
        if player_id is None:
            return
        self.ControladorObjetos.aplicar_diff(
            {
                "tipo": "update",
                "objeto_id": int(player_id),
                "payload": {
                    "id": int(player_id),
                    "tipo": "entidade_player",
                    "posicao": [self.EntidadeMain.Posicao[0], self.EntidadeMain.Posicao[1]],
                    "raio_colisao": 0.5,
                },
            }
        )

    def Finalizar(self, JOGO):
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
