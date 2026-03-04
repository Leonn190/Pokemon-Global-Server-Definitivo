import os

import pygame

from Codigo.Modulos.EfeitosTela import Clarear, Escurecer
from Codigo.Prefabs.Botao import Botao


class CenaCarregamento:
    def Inicializar(self, JOGO):
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Carregamento"

        self._frames = []
        self._indice_frame = 0
        self._acumulado_frame = 0.0
        self._intervalo_frame = 1.0 / 20.0

        self._ultimo_tamanho = None
        self._frame_escalado = None
        self._botao_cancelar = None

        self._carregar_frames()
        self._montar_layout(JOGO)

    def _carregar_frames(self):
        pasta_frames = "Recursos/Visual/Outros/Carregando_Frames"
        if not os.path.isdir(pasta_frames):
            return

        nomes = sorted(
            [arquivo for arquivo in os.listdir(pasta_frames) if arquivo.lower().endswith(".png")]
        )

        for nome in nomes:
            caminho = os.path.join(pasta_frames, nome)
            try:
                imagem = pygame.image.load(caminho).convert_alpha()
            except pygame.error:
                continue
            self._frames.append(imagem)

    def _voltar_menu(self, JOGO, _botao):
        JOGO.CenaAlvo = "Menu"

    def _montar_layout(self, JOGO):
        largura_tela, altura_tela = JOGO.TELA.get_size()
        self._ultimo_tamanho = (largura_tela, altura_tela)

        largura_botao = min(300, int(largura_tela * 0.3))
        altura_botao = 84
        x_botao = (largura_tela - largura_botao) // 2
        y_botao = int(altura_tela * 0.72)

        estilo_botao = {
            "radius": 20,
            "border_width": 2,
            "bg": (30, 36, 64),
            "bg_hover": (46, 56, 94),
            "bg_pressed": (22, 28, 50),
            "border": (14, 16, 28),
            "border_hover": (255, 224, 110),
            "hover_scale": 1.05,
            "text_style": {
                "size": 34,
                "color": (245, 246, 255),
                "hover_color": (255, 230, 120),
                "outline": True,
                "outline_thickness": 1,
                "outline_color": (0, 0, 0),
                "shadow": True,
                "shadow_color": (0, 0, 0, 180),
                "shadow_offset": (2, 2),
            },
        }

        self._botao_cancelar = Botao(
            pygame.Rect(x_botao, y_botao, largura_botao, altura_botao),
            "Cancelar",
            execute=self._voltar_menu,
            style=estilo_botao,
        )

        self._atualizar_frame_escalado()

    def _atualizar_frame_escalado(self):
        self._frame_escalado = None
        if not self._frames:
            return

        largura_tela, altura_tela = self._ultimo_tamanho
        frame_base = self._frames[self._indice_frame]

        max_largura = int(largura_tela * 0.25)
        max_altura = int(altura_tela * 0.25)

        escala = min(max_largura / frame_base.get_width(), max_altura / frame_base.get_height())
        escala = max(0.1, escala)

        tamanho = (
            max(1, int(frame_base.get_width() * escala)),
            max(1, int(frame_base.get_height() * escala)),
        )
        self._frame_escalado = pygame.transform.smoothscale(frame_base, tamanho)

    def Tela(self, JOGO, EVENTOS, dt):
        if self._ultimo_tamanho != JOGO.TELA.get_size():
            self._montar_layout(JOGO)

        JOGO.TELA.fill((9, 12, 22))

        if self._frames:
            self._acumulado_frame += dt
            if self._acumulado_frame >= self._intervalo_frame:
                self._acumulado_frame -= self._intervalo_frame
                self._indice_frame = (self._indice_frame + 1) % len(self._frames)
                self._atualizar_frame_escalado()

            if self._frame_escalado:
                rect = self._frame_escalado.get_rect(
                    center=(JOGO.TELA.get_width() // 2, int(JOGO.TELA.get_height() * 0.45))
                )
                JOGO.TELA.blit(self._frame_escalado, rect)

        if self._botao_cancelar:
            self._botao_cancelar.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)

    def Finalizar(self, JOGO):
        pass
