from __future__ import annotations

import colorsys
import hashlib
import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto


class Doce:
    _txt_qtd = None
    _paleta = {
        "abelha": ((245, 174, 122), (184, 115, 66)),
        "agua-viva": ((121, 103, 245), (68, 51, 184)),
        "anjo": ((110, 245, 83), (61, 184, 37)),
        "anta": ((245, 64, 146), (184, 33, 102)),
        "aranha": ((116, 203, 232), (66, 154, 184)),
        "arbusto": ((232, 227, 97), (184, 178, 51)),
        "arraia": ((181, 79, 232), (135, 37, 184)),
        "arvore": ((60, 232, 125), (33, 184, 90)),
        "avestruz": ((109, 214, 242), (58, 157, 183)),
        "axolote": ((181, 109, 242), (126, 58, 183)),
        "baleia": ((236, 242, 109), (178, 183, 58)),
        "bateria": ((242, 109, 151), (183, 58, 98)),
        "beleia": ((217, 109, 242), (160, 58, 183)),
        "bola": ((121, 109, 242), (70, 58, 183)),
        "borboleta": ((152, 242, 109), (99, 183, 58)),
        "cabra": ((109, 242, 230), (58, 183, 172)),
        "cachorro": ((109, 194, 242), (58, 138, 183)),
        "cacto": ((109, 192, 242), (58, 137, 183)),
        "camaleão": ((242, 110, 109), (183, 59, 58)),
        "camelo": ((242, 130, 109), (183, 78, 58)),
        "canguru": ((242, 109, 239), (183, 58, 181)),
        "caracol": ((242, 124, 109), (183, 72, 58)),
        "caranguejo": ((109, 206, 242), (58, 150, 183)),
        "castor": ((109, 242, 199), (58, 183, 143)),
        "casulo": ((176, 242, 109), (121, 183, 58)),
        "cavalo": ((204, 109, 242), (148, 58, 183)),
        "cavalo-marinho": ((242, 194, 109), (183, 139, 58)),
        "coala": ((217, 242, 109), (160, 183, 58)),
        "cobra": ((134, 109, 242), (82, 58, 183)),
        "coelho": ((109, 242, 175), (58, 183, 120)),
        "cogumelo": ((109, 138, 242), (58, 86, 183)),
        "comida": ((191, 109, 242), (135, 58, 183)),
        "concha": ((211, 242, 109), (154, 183, 58)),
        "coral": ((234, 109, 242), (176, 58, 183)),
        "coruja": ((242, 181, 109), (183, 126, 58)),
        "criatura": ((109, 242, 167), (58, 183, 113)),
        "desconhecido": ((109, 242, 112), (58, 183, 61)),
        "deus": ((110, 242, 109), (60, 183, 58)),
        "dinossauro": ((242, 109, 205), (183, 58, 148)),
        "dragão": ((109, 147, 242), (58, 94, 183)),
        "elefante": ((137, 167, 233), (90, 122, 196)),
        "escorpião": ((159, 109, 242), (105, 58, 183)),
        "espirito": ((146, 109, 242), (94, 58, 183)),
        "esquilo": ((233, 242, 109), (175, 183, 58)),
        "estatico": ((242, 109, 209), (183, 58, 152)),
        "estrela": ((226, 109, 242), (168, 58, 183)),
        "flor": ((236, 109, 242), (178, 58, 183)),
        "foca": ((242, 235, 109), (183, 177, 58)),
        "fossil": ((166, 109, 242), (112, 58, 183)),
        "fruta": ((242, 219, 109), (183, 161, 58)),
        "furão": ((166, 242, 109), (112, 183, 58)),
        "galinha": ((109, 127, 242), (58, 76, 183)),
        "gambá": ((242, 236, 109), (183, 178, 58)),
        "gato": ((255, 183, 108), (230, 133, 61)),
        "girafa": ((121, 242, 109), (70, 183, 58)),
        "golem": ((109, 242, 149), (58, 183, 96)),
        "gosma": ((109, 189, 242), (58, 133, 183)),
        "hipopotamo": ((242, 195, 109), (183, 140, 58)),
        "humanoide": ((178, 242, 109), (124, 183, 58)),
        "insetoide": ((242, 109, 131), (183, 58, 79)),
        "jacare": ((109, 120, 242), (58, 69, 183)),
        "joaninha": ((242, 109, 127), (183, 58, 76)),
        "lagarto": ((109, 163, 242), (58, 110, 183)),
        "leão": ((159, 242, 109), (106, 183, 58)),
        "lontra": ((117, 242, 109), (66, 183, 58)),
        "macaco": ((242, 109, 158), (183, 58, 104)),
        "maquina": ((165, 242, 109), (112, 183, 58)),
        "mineral": ((242, 136, 109), (183, 84, 58)),
        "minerio": ((167, 109, 242), (113, 58, 183)),
        "minhoca": ((109, 242, 143), (58, 183, 91)),
        "morcego": ((144, 109, 242), (91, 58, 183)),
        "objeto": ((109, 114, 242), (58, 63, 183)),
        "ouriço": ((109, 161, 242), (58, 107, 183)),
        "ovelha": ((109, 242, 217), (58, 183, 160)),
        "passaro": ((138, 242, 109), (86, 183, 58)),
        "pato": ((242, 226, 109), (183, 168, 58)),
        "peixe": ((210, 109, 242), (154, 58, 183)),
        "peixei": ((109, 192, 242), (58, 136, 183)),
        "pereba": ((242, 109, 200), (183, 58, 144)),
        "pinguim": ((224, 109, 242), (166, 58, 183)),
        "planta": ((190, 109, 242), (134, 58, 183)),
        "polvo": ((242, 195, 109), (183, 139, 58)),
        "pomba": ((242, 109, 180), (183, 58, 125)),
        "pombo": ((242, 232, 109), (183, 174, 58)),
        "porco": ((229, 242, 109), (171, 183, 58)),
        "porco-espinho": ((109, 242, 147), (58, 183, 94)),
        "povlo": ((109, 191, 242), (58, 136, 183)),
        "pré-histórico": ((109, 221, 242), (58, 164, 183)),
        "raposa": ((109, 242, 157), (58, 183, 104)),
        "rato": ((122, 242, 109), (71, 183, 58)),
        "rinoceronte": ((109, 206, 242), (58, 150, 183)),
        "rocha": ((109, 242, 130), (58, 183, 78)),
        "sapo": ((86, 202, 116), (48, 149, 74)),
        "tartaruga": ((242, 114, 109), (183, 63, 58)),
        "tatu": ((131, 242, 109), (79, 183, 58)),
        "topeira": ((242, 109, 216), (183, 58, 159)),
        "touro": ((109, 211, 242), (58, 155, 183)),
        "tubarão": ((145, 109, 242), (93, 58, 183)),
        "urso": ((242, 152, 109), (183, 99, 58)),
        "vaca": ((109, 189, 242), (58, 134, 183)),
        "veado": ((232, 242, 109), (174, 183, 58)),
        "zebra": ((109, 242, 172), (58, 183, 118)),
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
