from pathlib import Path
import pygame


def carregar_frames(pasta, loader=None):
    arquivos = sorted(Path(pasta).glob("*.png"))

    if loader is None:
        return [pygame.image.load(str(arquivo)).convert_alpha() for arquivo in arquivos]

    return [loader(str(arquivo)) for arquivo in arquivos]