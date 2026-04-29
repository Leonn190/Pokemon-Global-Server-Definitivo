from __future__ import annotations

import colorsys
import hashlib
import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto


class Doce:
    _txt_qtd = None
    _paleta = {
        "sapo": ((86, 202, 116), (48, 149, 74)),
        "elefante": ((137, 167, 233), (90, 122, 196)),
        "gato": ((255, 183, 108), (230, 133, 61)),
    }

    @classmethod
    def _garantir_fontes(cls):
        if cls._txt_qtd is None:
            cls._txt_qtd = Texto("", style={"size": 13, "align": "bottomright", "outline": True, "outline_thickness": 1, "shadow": False, "color": (255, 255, 255)})

    @classmethod
    def _cores_grupo(cls, grupo: str):
        chave = str(grupo or "").strip().lower()
        if chave in cls._paleta:
            return cls._paleta[chave]
        digest = hashlib.md5(chave.encode("utf-8")).hexdigest() if chave else "0" * 32
        hue = int(digest[:8], 16) / 0xFFFFFFFF
        r1, g1, b1 = colorsys.hsv_to_rgb(hue, 0.55, 0.95)
        r2, g2, b2 = colorsys.hsv_to_rgb(hue, 0.68, 0.72)
        return (
            (int(r1 * 255), int(g1 * 255), int(b1 * 255)),
            (int(r2 * 255), int(g2 * 255), int(b2 * 255)),
        )

    @classmethod
    def desenhar_item_no_rect(cls, tela, item, rect: pygame.Rect):
        if not isinstance(item, dict):
            return
        if str(item.get("Estilo") or item.get("estilo") or "").strip().lower() != "doce":
            ItemInventario.desenhar_item_no_rect(tela, item, rect)
            return
        grupo = str(item.get("Grupo") or item.get("grupo") or "")
        cor_a, cor_b = cls._cores_grupo(grupo)
        raio = max(8, min(rect.width, rect.height) // 2 - 4)
        centro = rect.center
        pygame.draw.circle(tela, cor_a, centro, raio)
        faixa_h = max(3, raio // 3)
        for desloc in (-faixa_h, faixa_h):
            faixa = pygame.Rect(centro[0] - raio, centro[1] + desloc - faixa_h // 2, raio * 2, faixa_h)
            pygame.draw.rect(tela, cor_b, faixa, border_radius=max(2, faixa_h // 2))
        pygame.draw.circle(tela, (255, 255, 255), centro, raio, width=2)
        cls._garantir_fontes()
        qtd = int(item.get("quantidade", 1) or 1)
        if qtd > 0:
            cls._txt_qtd.set_text(str(qtd))
            cls._txt_qtd.set_pos((rect.right - 4, rect.bottom - 3))
            cls._txt_qtd.draw(tela)
