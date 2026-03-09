from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

from Codigo.Prefabs.Arrastavel import Arrastavel


class ItemInventario(Arrastavel):
    """Slot arrastável de inventário com suporte visual e stack."""

    _mapa_por_nome: Dict[str, str] | None = None
    _cache_surface: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}

    def __init__(self, rect, slot_id: int, inventario, callback_troca=None):
        super().__init__(rect, id_arrastavel=slot_id)
        self.Inventario = inventario
        self._callback_troca = callback_troca

    @staticmethod
    def _norm(texto: str) -> str:
        base = "".join(c for c in unicodedata.normalize("NFKD", str(texto or "").lower()) if not unicodedata.combining(c))
        for ch in ("_", "-", "'", "."):
            base = base.replace(ch, " ")
        return " ".join(base.split())

    @classmethod
    def _mapa(cls) -> Dict[str, str]:
        if cls._mapa_por_nome is not None:
            return cls._mapa_por_nome
        mapa: Dict[str, str] = {}
        for arq in (Path("Recursos") / "Visual" / "Itens").rglob("*.png"):
            chave = cls._norm(arq.stem)
            if chave and chave not in mapa:
                mapa[chave] = str(arq)
        aliases = {"max pocao": "pocao maxima", "revival": "revive", "max revival": "revive maximo"}
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
        key = (path, int(max(8, lado_px)))
        if key in cls._cache_surface:
            return cls._cache_surface[key]
        try:
            surf = pygame.transform.smoothscale(pygame.image.load(path).convert_alpha(), (key[1], key[1]))
        except pygame.error:
            surf = None
        cls._cache_surface[key] = surf
        return surf


    @staticmethod
    def nome_item(item: object) -> str:
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

        sprite = self.surface_item(item, lado_px=max(20, self.rect.width - 14))
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=self.rect.center))
        else:
            nome = str(item.get("Nome") or item.get("nome") or "Item") if isinstance(item, dict) else str(item)
            txt = pygame.font.SysFont("arial", 14).render(nome[:9], True, (244, 246, 255))
            tela.blit(txt, txt.get_rect(center=self.rect.center))

        qtd = int(item.get("quantidade", 1)) if isinstance(item, dict) else 1
        if qtd > 1:
            txt_qtd = pygame.font.SysFont("arial", 13, bold=True).render(str(qtd), True, (255, 255, 255))
            tela.blit(txt_qtd, txt_qtd.get_rect(bottomright=(self.rect.right - 4, self.rect.bottom - 2)))

    def _executar_area_acao(self):
        for area_rect, callback, area_id in self.AreasAcao:
            if not self.rect.colliderect(area_rect):
                continue
            if callable(callback):
                callback(self, area_id, area_rect)
            elif callable(self._callback_troca):
                self._callback_troca(self, area_id, area_rect)
            return True
        return False
