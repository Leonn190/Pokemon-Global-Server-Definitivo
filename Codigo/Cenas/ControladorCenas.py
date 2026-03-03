from Codigo.Cenas.CenaMenu import CenaMenu
from Codigo.Cenas.CenaMundo import CenaMundo
from Codigo.Cenas.CenaCombate import CenaCombate
from Codigo.Cenas.CenaCarregamento import CenaCarregamento

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG):
        self.TELA = TELA
        self.RELOGIO = RELOGIO
        self.CONFIG = CONFIG
        self.INFO = {
        }

        self.Cenas = {
            "Carregamento": CenaCarregamento(),
            "Menu": CenaMenu(),
            "Mundo": CenaMundo(),
            "Combate": CenaCombate(),
        }

        self.Escuro = 100
        self.CenaAlvo = None
        self.Cena = None
        self.Rodando = True

    def DefinirCena(self):
        
        if self.Cena is not None:
            self.INFO.update({"UltimaCena": self.Cena.ID})
            self.Cena.Finalizar(self)
        
        self.Cena = self.Cenas[self.CenaAlvo]
        self.CenaAlvo = None
        self.Cena.Inicializar(self)

    def Rodar(self):

        while self.Rodando:
            self.Cena.Loop(self)