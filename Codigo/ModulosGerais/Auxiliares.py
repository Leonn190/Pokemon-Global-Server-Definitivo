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
_CACHE_ICO_BOTAO_EXPANDIR: dict[tuple[int, bool], pygame.Surface | None] = {}


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


def criar_botao_expandir(execute=None, rect=(0, 0, 10, 10), style=None):
    from Codigo.Prefabs.Botao import Botao

    base_style = {
        "radius": 10,
        "border_width": 2,
        "bg": (20, 30, 48),
        "bg_hover": (34, 48, 74),
        "bg_pressed": (16, 24, 40),
        "border": (122, 152, 206),
        "border_hover": (224, 235, 255),
        "hover_scale": 1.0,
        "press_scale": 0.98,
        "text_style": {
            "size": 1,
            "align": "center",
            "outline": False,
            "shadow": False,
            "color": (255, 255, 255),
            "hover_color": (255, 255, 255),
        },
    }
    if isinstance(style, dict):
        text_style = dict(base_style["text_style"])
        if isinstance(style.get("text_style"), dict):
            text_style.update(style.get("text_style") or {})
        base_style.update(style)
        base_style["text_style"] = text_style
    botao = Botao(pygame.Rect(rect), "", execute=execute, style=base_style)
    botao.set_text("")
    return botao


def configurar_estilo_botao_expandir(botao, aberto: bool) -> None:
    if botao is None or not hasattr(botao, "set_style"):
        return
    if aberto:
        botao.set_style(
            bg=(72, 100, 170),
            bg_hover=(92, 122, 202),
            bg_pressed=(58, 82, 144),
            border=(214, 230, 255),
            border_hover=(255, 255, 255),
        )
    else:
        botao.set_style(
            bg=(20, 30, 48),
            bg_hover=(34, 48, 74),
            bg_pressed=(16, 24, 40),
            border=(122, 152, 206),
            border_hover=(224, 235, 255),
        )


def icone_botao_expandir(lado_px: int, aberto: bool = False) -> pygame.Surface | None:
    lado_px = int(max(10, lado_px))
    chave = (lado_px, bool(aberto))
    if chave in _CACHE_ICO_BOTAO_EXPANDIR:
        return _CACHE_ICO_BOTAO_EXPANDIR[chave]

    caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "Seta.png"
    if not caminho.exists():
        _CACHE_ICO_BOTAO_EXPANDIR[chave] = None
        return None

    try:
        icone = pygame.image.load(str(caminho)).convert_alpha()
        icone = pygame.transform.smoothscale(icone, (lado_px, lado_px))
        if bool(aberto):
            icone = pygame.transform.flip(icone, True, False)
    except Exception:
        _CACHE_ICO_BOTAO_EXPANDIR[chave] = None
        return None

    _CACHE_ICO_BOTAO_EXPANDIR[chave] = icone
    return icone


def renderizar_botao_expandir(botao, tela, eventos, dt: float, rect, aberto: bool, jogo=None) -> pygame.Rect:
    if botao is None:
        return pygame.Rect(rect)
    configurar_estilo_botao_expandir(botao, aberto)
    novo_rect = pygame.Rect(rect)
    botao.base_rect = pygame.Rect(novo_rect)
    botao.rect = pygame.Rect(novo_rect)
    botao.set_text("")
    botao.render(tela, eventos or [], dt, jogo)
    icone = icone_botao_expandir(max(12, min(botao.rect.width, botao.rect.height) - 8), aberto=aberto)
    if icone is not None:
        tela.blit(icone, icone.get_rect(center=botao.rect.center))
    return pygame.Rect(botao.rect)
