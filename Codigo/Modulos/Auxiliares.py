from pathlib import Path

import pygame


def carregar_frames(pasta, loader=None):
    """Carrega frames .png numerados (0.png até N.png) em ordem crescente."""
    base = Path(pasta)
    if not base.is_dir():
        return []

    carregar = loader or (lambda caminho: pygame.image.load(caminho).convert_alpha())

    arquivos = [p for p in base.glob("*.png") if p.stem.isdigit()]
    arquivos.sort(key=lambda p: int(p.stem))

    frames = []
    for arquivo in arquivos:
        try:
            frame = carregar(str(arquivo))
            if frame is not None:
                frames.append(frame)
        except Exception:
            pass
    return frames
