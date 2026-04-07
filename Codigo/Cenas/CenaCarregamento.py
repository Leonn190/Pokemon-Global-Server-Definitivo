import pygame

from Codigo.Modulos.Auxiliares import carregar_frames
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
        self._tempo_espera_mundo = 0.0

        self._carregar_frames()
        self._montar_layout(JOGO)

    def _carregar_frames(self):
        self._frames = carregar_frames("Recursos/Visual/Outros/Carregando_Frames")

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

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        _ = EVENTOS
        if self._ultimo_tamanho != JOGO.TELA.get_size():
            self._montar_layout(JOGO)

        if self._frames:
            self._acumulado_frame += dt
            if self._acumulado_frame >= self._intervalo_frame:
                self._acumulado_frame -= self._intervalo_frame
                self._indice_frame = (self._indice_frame + 1) % len(self._frames)
                self._atualizar_frame_escalado()

        if JOGO.INFO.get("ServerSelecionado") and JOGO.INFO.get("PlayerDadosServer") is not None:
            self._tempo_espera_mundo += max(0.0, float(dt))
            if self._tempo_espera_mundo >= 3.0:
                JOGO.CenaAlvo = "Mundo"

    def tela_atual_eh_complexa(self) -> bool:
        return False

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        surface.fill((9, 12, 22))

        if self._frame_escalado:
            rect = self._frame_escalado.get_rect(
                center=(surface.get_width() // 2, int(surface.get_height() * 0.45))
            )
            surface.blit(self._frame_escalado, rect)

        if self._botao_cancelar:
            self._botao_cancelar.render(surface, EVENTOS, dt, JOGO=JOGO)

    def Tela(self, JOGO, EVENTOS, dt):
        self.atualizar_cena(JOGO, EVENTOS, dt)
        self.render_tela(JOGO.TELA, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        pass
