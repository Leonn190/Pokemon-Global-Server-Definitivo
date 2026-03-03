import pygame

from Codigo.Modulos.EfeitosTela import Clarear, Escurecer


class CenaCarregamento:
    def Inicializar(self, JOGO):
        self.TelaAtiva = self.Tela
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Carregamento"
        self.FonteFPS = pygame.font.SysFont("consolas", 24)

    def DesenhosAdicionais(self, JOGO):
        if not JOGO.CONFIG.get("FPS Visivel", False):
            return

        texto_status = f"FPS: {int(JOGO.RELOGIO.get_fps())} | Ping: 5"
        superficie_status = self.FonteFPS.render(texto_status, True, (255, 255, 255))
        rect_status = superficie_status.get_rect(topright=(JOGO.TELA.get_width() - 16, 12))
        JOGO.TELA.blit(superficie_status, rect_status)

    def Loop(self, JOGO):
        dt = JOGO.RELOGIO.tick(JOGO.CONFIG["FPS"]) / 1000.0

        EVENTOS = pygame.event.get()
        for e in EVENTOS:
            if e.type == pygame.QUIT:
                JOGO.Rodando = False

        self.TelaAtiva(JOGO, EVENTOS)
        self.DesenhosAdicionais(JOGO)

        if JOGO.CenaAlvo is None and JOGO.Escuro != 0:
            self.Abertura(JOGO, dt)

        if JOGO.CenaAlvo is not None and JOGO.Escuro != 100:
            self.Fechamento(JOGO, dt)

        if JOGO.CenaAlvo is not None and JOGO.Escuro == 100:
            JOGO.DefinirCena()

        pygame.display.update()

    def Tela(self, JOGO, EVENTOS):
        JOGO.TELA.fill((20, 20, 28))

    def Finalizar(self, JOGO):
        pass
