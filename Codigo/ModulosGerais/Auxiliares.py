from pathlib import Path
import pygame

from pathlib import Path
import re
import pygame

def carregar_frames(pasta, loader=None):
    def chave(arq):
        m = re.search(r"\d+$", arq.stem)
        return int(m.group()) if m else 0

    arquivos = sorted(Path(pasta).glob("*.png"), key=chave)

    if loader is None:
        return [pygame.image.load(str(arquivo)).convert_alpha() for arquivo in arquivos]

    return [loader(str(arquivo)) for arquivo in arquivos]