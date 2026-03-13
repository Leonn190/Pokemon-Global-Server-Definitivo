from __future__ import annotations

import csv
from pathlib import Path

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto


class FichaItem:
    _dados_csv = None

    def __init__(self):
        self._painel = None
        self._rect_cache = None

        self.TxtTitulo = Texto(
            "Ficha do item",
            pos=(0, 0),
            style={
                "size": 20,
                "color": (236, 241, 255),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )

        self.TxtVazio = Texto(
            "Passe o mouse em um item para ver os detalhes.",
            pos=(0, 0),
            style={
                "size": 17,
                "color": (166, 178, 208),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )

        self.TxtNome = Texto(
            "Item",
            pos=(0, 0),
            style={
                "size": 24,
                "color": (245, 247, 255),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )

        self.TxtTagRaridade = Texto(
            "Raridade -",
            pos=(0, 0),
            style={
                "size": 15,
                "color": (250, 252, 255),
                "align": "center",
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )

        self.TxtMetaQuantidade = Texto(
            "",
            pos=(0, 0),
            style={
                "size": 17,
                "color": (206, 216, 240),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )
        self.TxtMetaEstilo = Texto(
            "",
            pos=(0, 0),
            style={
                "size": 17,
                "color": (206, 216, 240),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )
        self.TxtMetaCode = Texto(
            "",
            pos=(0, 0),
            style={
                "size": 17,
                "color": (206, 216, 240),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )

        self.TxtSubtituloDescricao = Texto(
            "Descrição",
            pos=(0, 0),
            style={
                "size": 15,
                "color": (236, 241, 255),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
            },
        )

        self.TxtLinhasDescricao = [
            Texto(
                "",
                pos=(0, 0),
                style={
                    "size": 17,
                    "color": (181, 193, 220),
                    "outline": True,
                    "outline_thickness": 2,
                    "outline_color": (8, 12, 20),
                },
            )
            for _ in range(6)
        ]

    @classmethod
    def _carregar_csv(cls):
        if cls._dados_csv is not None:
            return cls._dados_csv

        cls._dados_csv = {}
        caminho = Path("Global server - Itens.csv")
        if not caminho.exists():
            caminho = Path(__file__).resolve().parents[3] / "Global server - Itens.csv"

        if not caminho.exists():
            return cls._dados_csv

        try:
            with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
                leitor = csv.DictReader(arquivo)
                for linha in leitor:
                    nome = str(linha.get("Nome") or "").strip().lower()
                    code = str(linha.get("Code") or "").strip()
                    if nome:
                        cls._dados_csv[("nome", nome)] = dict(linha)
                    if code:
                        cls._dados_csv[("code", code)] = dict(linha)
        except OSError:
            pass

        return cls._dados_csv

    @classmethod
    def _info_item(cls, item):
        if not isinstance(item, dict):
            return {}

        base = cls._carregar_csv()
        code = str(item.get("Code") or item.get("code") or "").strip()
        nome = str(item.get("Nome") or item.get("nome") or "").strip().lower()

        if code and ("code", code) in base:
            return dict(base[("code", code)])
        if nome and ("nome", nome) in base:
            return dict(base[("nome", nome)])
        return {}

    @staticmethod
    def _cor_raridade(valor):
        try:
            raridade = int(valor)
        except (TypeError, ValueError):
            raridade = 0

        mapa = {
            1: (160, 170, 190),
            2: (110, 205, 135),
            3: (90, 160, 255),
            4: (176, 117, 255),
            5: (255, 178, 74),
            6: (255, 110, 125),
        }
        return mapa.get(raridade, (120, 136, 170))

    @staticmethod
    def _quebrar_texto(texto_obj: Texto, texto: str, largura: int):
        palavras = str(texto or "").split()
        if not palavras:
            return []

        linhas = []
        atual = palavras[0]

        for palavra in palavras[1:]:
            teste = atual + " " + palavra
            texto_obj.set_text(teste)
            if texto_obj.get_rect().width <= largura:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra

        linhas.append(atual)
        return linhas

    def _garantir_painel(self, rect):
        if self._painel is not None and self._rect_cache == tuple(rect):
            return

        self._rect_cache = tuple(rect)
        self._painel = Painel(
            rect,
            cor_fundo=(20, 26, 42, 238),
            cor_borda=(74, 98, 146),
            borda=2,
            raio=16,
        )

    def renderizar(self, tela, rect, item):
        self._garantir_painel(rect)
        self._painel.rect = pygame.Rect(rect)
        self._painel.render(tela, [], 0)

        area = pygame.Rect(rect)

        self.TxtTitulo.set_pos((area.x + 18, area.y + 14))
        self.TxtTitulo.draw(tela)

        if item is None:
            self.TxtVazio.set_pos((area.x + 18, area.y + 54))
            self.TxtVazio.draw(tela)
            return

        info = self._info_item(item)
        nome = str(item.get("Nome") or item.get("nome") or info.get("Nome") or "Item")
        descricao = str(item.get("Descrição") or item.get("descricao") or info.get("Descrição") or "Sem descrição cadastrada.")
        estilo = str(item.get("Estilo") or item.get("estilo") or info.get("Estilo") or "-")
        code = str(item.get("Code") or item.get("code") or info.get("Code") or "-")
        raridade = str(item.get("Raridade") or item.get("raridade") or info.get("Raridade") or "-")
        quantidade = int(item.get("quantidade", 1)) if isinstance(item, dict) else 1

        box_icone = pygame.Rect(area.x + 18, area.y + 52, 78, 78)
        pygame.draw.rect(tela, (46, 60, 96), box_icone, border_radius=12)
        pygame.draw.rect(tela, (86, 110, 162), box_icone, 2, border_radius=12)
        ItemInventario.desenhar_item_no_rect(tela, item, box_icone.inflate(-12, -12))

        self.TxtNome.set_text(nome)
        self.TxtNome.set_pos((box_icone.right + 14, area.y + 54))
        self.TxtNome.draw(tela)

        cor_tag = self._cor_raridade(raridade)
        tag_rect = pygame.Rect(box_icone.right + 14, area.y + 88, 118, 26)
        pygame.draw.rect(tela, (*cor_tag, 40), tag_rect, border_radius=10)
        pygame.draw.rect(tela, cor_tag, tag_rect, 2, border_radius=10)

        self.TxtTagRaridade.set_text(f"Raridade {raridade}")
        self.TxtTagRaridade.set_pos(tag_rect.center)
        self.TxtTagRaridade.draw(tela)

        meta_y = box_icone.bottom + 16

        self.TxtMetaQuantidade.set_text(f"Quantidade: {quantidade}")
        self.TxtMetaQuantidade.set_pos((area.x + 18, meta_y))
        self.TxtMetaQuantidade.draw(tela)

        self.TxtMetaEstilo.set_text(f"Estilo: {estilo}")
        self.TxtMetaEstilo.set_pos((area.x + 18, meta_y + 24))
        self.TxtMetaEstilo.draw(tela)

        self.TxtMetaCode.set_text(f"Code: {code}")
        self.TxtMetaCode.set_pos((area.x + 18, meta_y + 48))
        self.TxtMetaCode.draw(tela)

        desc_y = meta_y + 82
        self.TxtSubtituloDescricao.set_pos((area.x + 18, desc_y))
        self.TxtSubtituloDescricao.draw(tela)

        largura_texto = area.width - 36
        linhas = self._quebrar_texto(self.TxtLinhasDescricao[0], descricao, largura_texto)

        for i, texto_linha in enumerate(self.TxtLinhasDescricao):
            if i < len(linhas[:6]):
                texto_linha.set_text(linhas[i])
                texto_linha.set_pos((area.x + 18, desc_y + 24 + i * 22))
                texto_linha.draw(tela)
            else:
                texto_linha.set_text("")
