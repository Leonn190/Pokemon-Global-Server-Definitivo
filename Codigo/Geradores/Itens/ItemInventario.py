from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

from Codigo.Prefabs.Arrastavel import Arrastavel


class ItemInventario(Arrastavel):
    _mapa_por_nome: Dict[str, str] | None = None
    _cache_surface: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _fonte_nome = None
    _fonte_qtd = None

    def __init__(self, rect, slot_id: int, inventario):
        super().__init__(rect, id_arrastavel=slot_id)
        self.Inventario = inventario

    @staticmethod
    def _norm(texto: str) -> str:
        texto = str(texto or "").lower()
        texto = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
        for ch in ("_", "-", "'", "."):
            texto = texto.replace(ch, " ")
        return " ".join(texto.split())

    @classmethod
    def _mapa(cls) -> Dict[str, str]:
        if cls._mapa_por_nome is not None:
            return cls._mapa_por_nome

        mapa = {}
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
    def _path_item(cls, item) -> Optional[str]:
        if not isinstance(item, dict):
            return None
        nome = item.get("Nome") or item.get("nome") or ""
        nome = str(nome).strip()
        if not nome:
            return None
        return cls._mapa().get(cls._norm(nome))

    @classmethod
    def surface_item(cls, item, lado_px: int) -> Optional[pygame.Surface]:
        path = cls._path_item(item)
        if not path:
            return None

        lado_px = max(8, int(lado_px))
        chave = (path, lado_px)

        if chave in cls._cache_surface:
            return cls._cache_surface[chave]

        try:
            imagem = pygame.image.load(path).convert_alpha()
            imagem = pygame.transform.smoothscale(imagem, (lado_px, lado_px))
        except pygame.error:
            imagem = None

        cls._cache_surface[chave] = imagem
        return imagem

    @staticmethod
    def nome_item(item) -> str:
        if isinstance(item, dict):
            return str(item.get("Nome") or item.get("nome") or "Item")
        return str(item)

    def item(self):
        idx = int(self.Id)
        itens = getattr(self.Inventario, "Itens", [])
        return itens[idx] if 0 <= idx < len(itens) else None

    def draw(self, tela):
        pygame.draw.rect(tela, (76, 96, 140), self.rect, border_radius=8)
        pygame.draw.rect(tela, (20, 26, 40), self.rect, 2, border_radius=8)

        item = self.item()
        if item is None:
            return

        if ItemInventario._fonte_nome is None:
            ItemInventario._fonte_nome = pygame.font.SysFont("arial", 14)
        if ItemInventario._fonte_qtd is None:
            ItemInventario._fonte_qtd = pygame.font.SysFont("arial", 13, bold=True)

        sprite = self.surface_item(item, self.rect.width - 14)
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=self.rect.center))
        else:
            nome = self.nome_item(item)[:9]
            txt = ItemInventario._fonte_nome.render(nome, True, (244, 246, 255))
            tela.blit(txt, txt.get_rect(center=self.rect.center))

        qtd = 1
        if isinstance(item, dict):
            qtd = int(max(1, item.get("quantidade", 1)))

        if qtd > 1:
            txt_qtd = ItemInventario._fonte_qtd.render(str(qtd), True, (255, 255, 255))
            tela.blit(txt_qtd, txt_qtd.get_rect(bottomright=(self.rect.right - 4, self.rect.bottom - 3)))
