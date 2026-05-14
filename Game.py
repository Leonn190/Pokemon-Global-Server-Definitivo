import os
import ctypes

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
try:
    import moderngl  # noqa: F401
except ImportError:
    moderngl = None

from Codigo.ModulosGerais.Cenas.ControladorCenas import ControladorCenas
from Codigo.ModulosGerais.Sonoridades import VerificaSonoridade

if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shell32"):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pokemon.global.server")

pygame.init()
pygame.mixer.init()

def _criar_janela():
    flags = pygame.NOFRAME
    if moderngl is not None:
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            try:
                return pygame.display.set_mode((1920, 1080), flags | pygame.OPENGL | pygame.DOUBLEBUF, vsync=0), True
            except TypeError:
                return pygame.display.set_mode((1920, 1080), flags | pygame.OPENGL | pygame.DOUBLEBUF), True
        except pygame.error:
            pass
    return pygame.display.set_mode((1920, 1080), flags), False


JANELA, JANELA_OPENGL = _criar_janela()
TELA = pygame.Surface(JANELA.get_size()).convert()
pygame.display.set_caption("Pokemon Global Server")

icone = pygame.image.load("Recursos/Visual/Icones/GlobalServer/Icone.png").convert_alpha()
pygame.display.set_icon(icone)

RELOGIO = pygame.time.Clock()

CONFIG = {
    "FPS": 200,
    "Volume": 0.5,
    "Claridade": 75,
    "Mudo": False,
    "FPS Visivel": True,
    "Cords Visiveis": False,
    "Ping Visivel": False,
    "MostrarHorario": False,
    "MostrarMinimapa": False,
    "Shader": True,
    "Usuario": None
}

from Ferramentas.ConfigFixa import ConfigFixa

if ConfigFixa is not None:
    CONFIG = ConfigFixa

CONFIG.update({"VERSÃO": 1.0})
CONFIG.setdefault("FPS Visivel", True)
CONFIG.setdefault("Ping Visivel", False)
CONFIG.setdefault("Cords Visiveis", False)
CONFIG.setdefault("MostrarHorario", False)
CONFIG.setdefault("MostrarMinimapa", False)
CONFIG.setdefault("Shader", True)
VerificaSonoridade(CONFIG)

Game = ControladorCenas(TELA, RELOGIO, CONFIG, tela_display=JANELA, janela_opengl=JANELA_OPENGL)
Game.CenaAlvo = "Menu" if CONFIG.get("Usuario") else "Login"
Game.DefinirCena()
try:
    Game.Rodar()
finally:
    Game.Encerrar()
    pygame.mixer.music.stop()
    pygame.mixer.stop()
    pygame.quit()
