from __future__ import annotations

import csv
from pathlib import Path

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto, SetorTexto


class FichaItem:
    _dados_csv = None
    _raridades = {
        1: ('Comum', (160, 170, 190)),
        2: ('Incomum', (110, 205, 135)),
        3: ('Raro', (90, 160, 255)),
        4: ('Épico', (176, 117, 255)),
        5: ('Lendário', (255, 178, 74)),
        6: ('Mítico', (255, 110, 125)),
    }

    def __init__(self):
        base = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20),
        }
        self.TxtVazio = Texto('Passe o mouse em um item para ver os detalhes.', style={**base, 'size': 16, 'color': (166, 178, 208), 'align': 'center'})
        self.TxtNome = Texto('Item', style={**base, 'size': 19, 'color': (245, 247, 255), 'align': 'midleft'})
        self.TxtRaridade = Texto('-', style={**base, 'size': 15, 'color': (236, 241, 255), 'align': 'midleft'})
        self.TxtDescricao = SetorTexto(
            texto='',
            linhas=3,
            caracteres_por_linha=34,
            style={**base, 'size': 13, 'color': (181, 193, 220), 'setor_align': 'left'},
        )
        self.TxtVazio.set_text('')

    @classmethod
    def _carregar_csv(cls):
        if cls._dados_csv is not None:
            return cls._dados_csv
        cls._dados_csv = {}
        caminhos = [
            Path('Dados') / 'Pokemon Global Server - Itens.csv',
            Path('Pokemon Global Server - Itens.csv'),
            Path(__file__).resolve().parents[3] / 'Dados' / 'Pokemon Global Server - Itens.csv',
            Path(__file__).resolve().parents[3] / 'Pokemon Global Server - Itens.csv',
        ]
        caminho = next((p for p in caminhos if p.exists()), None)
        if caminho is None:
            return cls._dados_csv
        try:
            with caminho.open('r', encoding='utf-8-sig', newline='') as arquivo:
                leitor = csv.DictReader(arquivo)
                for linha in leitor:
                    nome = str(linha.get('Nome') or '').strip().lower()
                    code = str(linha.get('Code') or '').strip()
                    if nome:
                        cls._dados_csv[('nome', nome)] = dict(linha)
                    if code:
                        cls._dados_csv[('code', code)] = dict(linha)
        except OSError:
            pass
        return cls._dados_csv

    @classmethod
    def _info_item(cls, item):
        if not isinstance(item, dict):
            return {}
        base = cls._carregar_csv()
        code = str(item.get('Code') or item.get('code') or '').strip()
        nome = str(item.get('Nome') or item.get('nome') or '').strip().lower()
        if code and ('code', code) in base:
            return dict(base[('code', code)])
        if nome and ('nome', nome) in base:
            return dict(base[('nome', nome)])
        return {}

    @classmethod
    def _dados_raridade(cls, valor):
        try:
            raridade = int(valor)
        except (TypeError, ValueError):
            raridade = 0
        return cls._raridades.get(raridade, ('-', (120, 136, 170)))

    def renderizar(self, tela, rect, item):
        area = pygame.Rect(rect)

        if item is None:
            self.TxtVazio.set_pos((area.centerx, area.centery))
            self.TxtVazio.draw(tela)
            return

        info = self._info_item(item)
        nome = str(item.get('Nome') or item.get('nome') or info.get('Nome') or 'Item')
        descricao = str(item.get('Descrição') or item.get('descricao') or info.get('Descrição') or 'Sem descrição cadastrada.')
        raridade = str(item.get('Raridade') or item.get('raridade') or info.get('Raridade') or '-')
        raridade_texto, raridade_cor = self._dados_raridade(raridade)

        margem = 8
        gap = 10
        deslocamento_x = 15
        box_icone = pygame.Rect(area.right - 58 + deslocamento_x, area.y + (area.height - 50) // 2, 50, 50)
        nome_x = area.x + margem - 4 + deslocamento_x
        centro_y = area.centery
        self.TxtNome.set_text(nome)
        self.TxtNome.set_pos((nome_x, centro_y))
        self.TxtNome.draw(tela)
        nome_rect = self.TxtNome.get_rect()
        gap_nome_desc = 14
        desc_x = nome_rect.right + gap_nome_desc

        self.TxtRaridade.set_text(raridade_texto)
        rar_rect = self.TxtRaridade.get_rect()
        pill_rect = pygame.Rect(0, 0, rar_rect.width + 20, rar_rect.height + 6)
        pill_rect.midleft = (box_icone.x - gap - pill_rect.width, centro_y)
        pygame.draw.rect(tela, raridade_cor, pill_rect, border_radius=10)
        pygame.draw.rect(tela, (8, 12, 20), pill_rect, 2, border_radius=10)
        self.TxtRaridade.set_pos((pill_rect.x + 10, pill_rect.centery))
        self.TxtRaridade.draw(tela)
        fundo_slot = box_icone.inflate(8, 8)
        pygame.draw.rect(tela, (52, 72, 114), fundo_slot, border_radius=10)
        pygame.draw.rect(tela, (220, 232, 252), fundo_slot, 2, border_radius=10)
        ItemInventario.desenhar_item_no_rect(tela, item, box_icone)

        desc_rect = pygame.Rect(desc_x, area.y + 6, max(28, pill_rect.x - gap - desc_x - 8), area.height - 12)
        self.TxtDescricao.configurar_rect(desc_rect)
        self.TxtDescricao.set_limites(linhas=3, caracteres_por_linha=34)
        self.TxtDescricao.set_texto(descricao)
        self.TxtDescricao.draw(tela)
