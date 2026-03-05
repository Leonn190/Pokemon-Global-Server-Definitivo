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
        self._cache_chunks_surface = {}
        self.ControladorObjetos = ControladorObjetos()
        self.EntidadeMain = None
        self.Player = None
        self.SubtelaOpcoes = SubtelaOpcoes()
        self._desconectado = False
        self.TelaAtual = None

        self.TamanhoChunkBlocos = 32
        self.CoresBlocos = {
            0: (14, 40, 92),
            1: (72, 162, 231),
            2: (230, 210, 146),
            3: (124, 204, 108),
            4: (56, 128, 64),
        }

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
            raio_chunks=2,
        )

        self.Player = Player(
            ator=self.EntidadeMain,
            callback_diff=self.LeitorMundo.enfileirar_diff,
            velocidade_tiles=4.8,
        )

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
            self.Player.Controle.atualizar(EVENTOS, dt, mouse_mundo_tiles)

        self.Camera.atualizar(dt)

        for diff in self.LeitorMundo.consumir_diffs_recebidas():
            self.ControladorObjetos.aplicar_diff(diff)

        self._atualizar_limites_loop_mundo()
        self._atualizar_cache_mundo()

        JOGO.TELA.fill((20, 20, 28))
        self._desenhar_mundo(JOGO)

        pos_tela_main = self.Camera.mundo_para_tela_px(self.EntidadeMain.Posicao)
        self.EntidadeMain.desenhar(JOGO.TELA, mouse_pos=pygame.mouse.get_pos(), posicao_tela=pos_tela_main)
        ignorar_id_main = getattr(self.EntidadeMain, "Id", None)
        self.ControladorObjetos.renderizar(JOGO.TELA, self.Camera, ignorar_entidade_id=ignorar_id_main)
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

    def _atualizar_cache_mundo(self):
        estado = self.LeitorMundo.snapshot() if self.LeitorMundo else {"chunks": {}}
        chunks = estado.get("chunks", {})
        if not chunks:
            self._cache_chunks_surface.clear()
            return

        chunks_ativos = set(chunks.keys())
        for chave in list(self._cache_chunks_surface.keys()):
            if chave[:2] not in chunks_ativos or chave[2] != self.Camera.TilePx:
                del self._cache_chunks_surface[chave]

        for (chunk_x, chunk_y), grid in chunks.items():
            assinatura_grid = tuple(tuple(int(bloco) for bloco in linha) for linha in grid)
            chave_cache = (chunk_x, chunk_y, self.Camera.TilePx, assinatura_grid)
            if chave_cache in self._cache_chunks_surface:
                continue

            tamanho_chunk_px = self.TamanhoChunkBlocos * self.Camera.TilePx
            surface = pygame.Surface((max(1, tamanho_chunk_px), max(1, tamanho_chunk_px))).convert()

            for by, linha in enumerate(assinatura_grid):
                for bx, bloco in enumerate(linha):
                    cor = self.CoresBlocos.get(bloco, (255, 0, 255))
                    pygame.draw.rect(
                        surface,
                        cor,
                        (
                            int(bx * self.Camera.TilePx),
                            int(by * self.Camera.TilePx),
                            self.Camera.TilePx + 1,
                            self.Camera.TilePx + 1,
                        ),
                    )

            self._cache_chunks_surface[chave_cache] = surface

    def _desenhar_mundo(self, JOGO):
        limites = self.Camera.LimitesMundoTiles if self.Camera else None
        repeticoes_x = (0,)
        repeticoes_y = (0,)
        if limites:
            largura, altura = limites
            repeticoes_x = (-largura, 0, largura)
            repeticoes_y = (-altura, 0, altura)

        for (chunk_x, chunk_y, _, _), chunk_surface in self._cache_chunks_surface.items():
            origem_x_tile = chunk_x * self.TamanhoChunkBlocos
            origem_y_tile = chunk_y * self.TamanhoChunkBlocos
            for off_x in repeticoes_x:
                for off_y in repeticoes_y:
                    px, py = self.Camera.mundo_para_tela_px((origem_x_tile + off_x, origem_y_tile + off_y))
                    JOGO.TELA.blit(chunk_surface, (int(px), int(py)))

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
