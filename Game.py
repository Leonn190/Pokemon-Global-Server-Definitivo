import os
import ctypes

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from Codigo.Cenas.ControladorCenas import ControladorCenas
from Codigo.Modulos.Sonoridades import VerificaSonoridade

if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shell32"):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pokemon.global.server")

pygame.init()
pygame.mixer.init()

TELA = pygame.display.set_mode((1920, 1080), pygame.NOFRAME)
pygame.display.set_caption("Pokemon Global Server")

icone = pygame.image.load("Recursos/Visual/Icones/GlobalServer/Icone.png").convert_alpha()
pygame.display.set_icon(icone)

RELOGIO = pygame.time.Clock()

CONFIG = {
    "FPS": 200,
    "Volume": 0.5,
    "Claridade": 75,
    "Mudo": False,
    "GraficosBons": True,
    "FPS Visivel": True,
    "Cords Visiveis": False,
    "Ping Visivel": False,
    "Usuario": None
}

from Outros.ConfigFixa import ConfigFixa

if ConfigFixa is not None:
    CONFIG = ConfigFixa

CONFIG.setdefault("GraficosBons", True)
CONFIG.update({"VERSÃO": 1.0})
VerificaSonoridade(CONFIG)

Game = ControladorCenas(TELA, RELOGIO, CONFIG)
Game.CenaAlvo = "Menu" if CONFIG.get("Usuario") else "Login"
Game.DefinirCena()
try:
    Game.Rodar()
finally:
    Game.Encerrar()
    pygame.mixer.music.stop()
    pygame.mixer.stop()
    pygame.quit()
