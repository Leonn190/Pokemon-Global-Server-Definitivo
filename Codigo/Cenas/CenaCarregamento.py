import pygame

from Codigo.Modulos.EfeitosTela import Clarear, Escurecer

class CenaCarregamento:
    def Inicializar(self, JOGO):
        self.TelaAtiva = self.Tela
        self.Abertura = Clarear
        self.Fechamento = Escurecer
        self.ID = "Carregamento"

    def Loop(self, JOGO):

        dt = JOGO.RELOGIO.tick(JOGO.CONFIG["FPS"]) / 1000.0

        EVENTOS = pygame.event.get()
        for e in EVENTOS:
            if e.type == pygame.QUIT:
                JOGO.Rodando = False

        self.TelaAtiva(JOGO, EVENTOS)

        if JOGO.CenaAlvo is None and JOGO.Escuro != 0:
            self.Abertura(JOGO, dt)

        if JOGO.CenaAlvo is not None and JOGO.Escuro != 100:
            self.Fechamento(JOGO, dt)

        if JOGO.CenaAlvo is not None and JOGO.Escuro == 100:
            JOGO.DefinirCena()

        pygame.display.update()
        JOGO.RELOGIO.tick(JOGO.CONFIG["FPS"])

    def Tela(self, JOGO, EVENTOS):
        JOGO.TELA.fill((20, 20, 28))
    
    def Finalizar(self, JOGO):
        pass