from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import pygame


_TILE_PARA_BIOMA = {
    0: "AguaFunda",
    1: "AguaRasa",
    2: "Vale",
    3: "Floresta",
    4: "Praia",
    5: "Deserto",
    6: "Neve",
    7: "Magico",
    8: "Vulcão",
    9: "Pantano",
}

_BIOMA_VISUAL_PT = {
    "Deserto": "deserto",
    "Neve": "neve",
    "Magico": "magico",
    "Vulcão": "vulcao",
    "Pantano": "pantano",
    "Praia": "praia",
    "Vale": "vale",
    "Floresta": "floresta",
    "AguaFunda": "agua_funda",
    "AguaRasa": "agua_rasa",
}

_CACHE_ICO_TIPO_COM_FUNDO: dict[tuple[str, int], pygame.Surface | None] = {}


def carregar_frames(pasta, loader=None):
    def chave(arq):
        m = re.search(r"\d+$", arq.stem)
        return int(m.group()) if m else 0

    arquivos = sorted(Path(pasta).glob("*.png"), key=chave)

    if loader is None:
        return [pygame.image.load(str(arquivo)).convert_alpha() for arquivo in arquivos]

    return [loader(str(arquivo)) for arquivo in arquivos]


def bioma_por_tile(tile: object) -> str:
    try:
        codigo = int(tile)
    except (TypeError, ValueError):
        return "Vale"
    return _TILE_PARA_BIOMA.get(codigo, "Vale")


def bioma_visual_por_tile(tile: object) -> str:
    return _BIOMA_VISUAL_PT.get(bioma_por_tile(tile), "vale")


def _normalizar_nome_tipo(tipo: str) -> str:
    base = "".join(
        c
        for c in unicodedata.normalize("NFKD", str(tipo or "").lower())
        if not unicodedata.combining(c)
    )
    for ch in ("_", "-", "'", "."):
        base = base.replace(ch, " ")
    return " ".join(base.split())


def construir_icone_tipo_com_fundo_branco(tipo: str, lado_px: int) -> pygame.Surface | None:
    lado_px = int(max(10, lado_px))
    nome = _normalizar_nome_tipo(tipo)
    chave = (nome, lado_px)
    if chave in _CACHE_ICO_TIPO_COM_FUNDO:
        return _CACHE_ICO_TIPO_COM_FUNDO[chave]

    caminho = Path("Recursos") / "Visual" / "Icones" / "Tipos" / f"{nome}.png"
    if not caminho.exists():
        _CACHE_ICO_TIPO_COM_FUNDO[chave] = None
        return None

    try:
        icone = pygame.image.load(str(caminho)).convert_alpha()
        icone = pygame.transform.smoothscale(icone, (lado_px, lado_px))
    except Exception:
        _CACHE_ICO_TIPO_COM_FUNDO[chave] = None
        return None

    canvas = pygame.Surface((lado_px, lado_px), pygame.SRCALPHA)
    raio = max(3, int(lado_px * 0.42))
    pygame.draw.circle(canvas, (255, 255, 255, 245), (lado_px // 2, lado_px // 2), raio)
    canvas.blit(icone, icone.get_rect(center=(lado_px // 2, lado_px // 2)))
    _CACHE_ICO_TIPO_COM_FUNDO[chave] = canvas
    return canvas
