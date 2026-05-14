from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

from Codigo.Prefabs.Texto import Texto


class ItemInventario:
    _mapa_por_nome: Dict[str, str] | None = None
    _cache_surface: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _txt_nome = None
    _txt_qtd = None

    @staticmethod
    def _norm(texto: str) -> str:
        base = "".join(
            c
            for c in unicodedata.normalize("NFKD", str(texto or "").lower())
            if not unicodedata.combining(c)
        )
        for ch in ("_", "-", "'", "."):
            base = base.replace(ch, " ")
        return " ".join(base.split())

    @classmethod
    def _mapa(cls) -> Dict[str, str]:
        if cls._mapa_por_nome is not None:
            return cls._mapa_por_nome

        mapa: Dict[str, str] = {}
        pasta = Path("Recursos") / "Visual" / "Itens"

        for arq in pasta.rglob("*.png"):
            chave = cls._norm(arq.stem)
            if chave and chave not in mapa:
                mapa[chave] = str(arq)

        aliases = {
            "max pocao": "pocao maxima",
            "revival": "revive",
            "max revival": "revive maximo",
        }
        for origem, destino in aliases.items():
            if destino in mapa:
                mapa[origem] = mapa[destino]

        cls._mapa_por_nome = mapa
        return mapa

    @classmethod
    def _path_item(cls, item: object) -> Optional[str]:
        if not isinstance(item, dict):
            return None
        nome = str(item.get("Nome") or item.get("nome") or "").strip()
        if not nome:
            return None
        return cls._mapa().get(cls._norm(nome))

    @classmethod
    def surface_item(cls, item: object, lado_px: int) -> Optional[pygame.Surface]:
        path = cls._path_item(item)
        if not path:
            return None

        lado_px = int(max(8, lado_px))
        chave = (path, lado_px)
        if chave in cls._cache_surface:
            return cls._cache_surface[chave]

        try:
            surf = pygame.image.load(path).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (lado_px, lado_px))
        except pygame.error:
            surf = None

        cls._cache_surface[chave] = surf
        return surf

    @staticmethod
    def nome_item(item: object) -> str:
        if isinstance(item, dict):
            return str(item.get("Nome") or item.get("nome") or "Item")
        return str(item)

    @staticmethod
    def raridade_item(item: object) -> str:
        if not isinstance(item, dict):
            return ''
        valor = item.get('Raridade')
        if valor not in (None, ''):
            return str(valor)
        return ''

    @staticmethod
    def estilo_item(item: object) -> str:
        if not isinstance(item, dict):
            return ''
        valor = item.get('Estilo')
        if valor not in (None, ''):
            return str(valor)
        return ''

    @classmethod
    def _garantir_fontes(cls):
        if cls._txt_nome is None:
            cls._txt_nome = Texto("", style={"size": 14, "align": "center", "outline": False, "shadow": False, "color": (244, 246, 255)})
        if cls._txt_qtd is None:
            cls._txt_qtd = Texto("", style={"size": 13, "align": "bottomright", "outline": True, "outline_thickness": 1, "shadow": False, "color": (255, 255, 255)})

    @classmethod
    def desenhar_item_no_rect(cls, tela, item, rect: pygame.Rect):
        if item is None:
            return

        cls._garantir_fontes()

        sprite = cls.surface_item(item, lado_px=max(20, rect.width - 14))
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=rect.center))
        else:
            nome = cls.nome_item(item)[:9]
            cls._txt_nome.set_text(nome)
            cls._txt_nome.set_pos(rect.center)
            cls._txt_nome.draw(tela)

        qtd = int(item.get("quantidade", 1)) if isinstance(item, dict) else 1
        if qtd > 1:
            cls._txt_qtd.set_text(str(qtd))
            cls._txt_qtd.set_pos((rect.right - 4, rect.bottom - 3))
            cls._txt_qtd.draw(tela)
