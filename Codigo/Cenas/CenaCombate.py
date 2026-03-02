import pygame

class CenaCombate:
    def Inicializar(self, JOGO):
        self.TelaAtiva = self.Tela
        self.ID = "Combate"

    def Loop(self, JOGO):
        EVENTOS = pygame.event.get()
        for e in EVENTOS:
            if e.type == pygame.QUIT:
                JOGO.Rodando = False

        self.TelaAtiva(JOGO, EVENTOS)

        pygame.display.update()
        JOGO.RELOGIO.tick(JOGO.CONFIG["FPS"])

    def Tela(self, JOGO, EVENTOS):
        JOGO.TELA.fill((20, 20, 28))
    
    def Finalizar(self, JOGO):
        JOGO.INFO.update({"UltimaCena": self.ID})
        pass