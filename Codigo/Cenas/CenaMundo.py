import os

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.Camera import Camera
from Codigo.Geradores.LeitorMundo import LeitorMundo
from Codigo.Geradores.PlayerController import PlayerController
from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Server.ServerMenu import consultar_estado_mundo, enviar_diffs_mundo


class CenaMundo:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Mundo"

        self.Camera = None
        self.LeitorMundo = None
        self.EntidadeMain = None
        self.PlayerController = None

        self._montar_mundo(JOGO)

    def _carregar_skin(self, nome_skin):
        if not nome_skin:
            nome_skin = "S1.png"
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

        self.LeitorMundo = LeitorMundo(
            jogo=JOGO,
            entidade_main=self.EntidadeMain,
            callback_atualizacao=consultar_estado_mundo,
            callback_envio_diffs=enviar_diffs_mundo,
            intervalo_poll=0.20,
        )
        self.PlayerController = PlayerController(
            self.EntidadeMain,
            velocidade_px=230.0,
            callback_diff=self.LeitorMundo.enfileirar_diff,
        )
        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=self.EntidadeMain)

        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        if link:
            self.LeitorMundo.conectar_servidor(link)
            self.LeitorMundo.iniciar()

    def Tela(self, JOGO, EVENTOS, dt):
        self.Camera.TamanhoTela = JOGO.TELA.get_size()
        mouse_tela = pygame.mouse.get_pos()
        mouse_mundo = (
            mouse_tela[0] + self.Camera.Posicao[0],
            mouse_tela[1] + self.Camera.Posicao[1],
        )

        self.PlayerController.atualizar(EVENTOS, dt, mouse_mundo)
        self.Camera.atualizar(dt)

        JOGO.TELA.fill((20, 20, 28))
        self._desenhar_grade(JOGO)

        pos_tela_main = self.Camera.mundo_para_tela(self.EntidadeMain.Posicao)
        self.EntidadeMain.desenhar(JOGO.TELA, mouse_pos=mouse_tela, posicao_tela=pos_tela_main)

    def _desenhar_grade(self, JOGO):
        espacamento = 64
        largura, altura = JOGO.TELA.get_size()
        off_x = int(self.Camera.Posicao[0]) % espacamento
        off_y = int(self.Camera.Posicao[1]) % espacamento

        cor_linha = (28, 30, 40)
        for x in range(-off_x, largura + espacamento, espacamento):
            pygame.draw.line(JOGO.TELA, cor_linha, (x, 0), (x, altura), 1)
        for y in range(-off_y, altura + espacamento, espacamento):
            pygame.draw.line(JOGO.TELA, cor_linha, (0, y), (largura, y), 1)

    def Finalizar(self, JOGO):
        if self.LeitorMundo:
            self.LeitorMundo.parar()
