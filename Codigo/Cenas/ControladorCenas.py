from Codigo.Cenas.CenaMenu import CenaMenu
from Codigo.Cenas.CenaMundo import CenaMundo
from Codigo.Cenas.CenaCombate import CenaCombate
from Codigo.Cenas.CenaCarregamento import CenaCarregamento  

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG):
        self.TELA = TELA
        self.RELOGIO = RELOGIO
        self.CONFIG = CONFIG
        self.INFO = {}

        self.Cenas = {
            "Carregamento": CenaCarregamento(),
            "Menu": CenaMenu(),
            "Mundo": CenaMundo(),
            "Combate": CenaCombate(),
        }

        self.Cena = None
        self.Rodando = True

    def DefinirCena(self, CenaID):
        
        if self.Cena is not None:
            self.Cena.Finalizar()
        
        self.Cena = self.Cenas[CenaID]
        self.Cena.Inicializar()

    def Rodar(self, CenaInicial="Menu"):
        self.DefinirCena(CenaInicial)

        while self.Rodando:
            self.Cena.Loop(self)