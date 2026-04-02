from __future__ import annotations

import csv
from pathlib import Path

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto


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
        self.TxtRaridade = Texto('-', style={**base, 'size': 15, 'color': (236, 241, 255), 'align': 'center'})
        self.TxtDescricao = Texto('', style={**base, 'size': 13, 'color': (181, 193, 220), 'align': 'midleft'})

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

    def _quebrar_em_linhas(self, texto: str, largura: int, max_linhas: int = 3):
        palavras = str(texto or '').split()
        if not palavras:
            return []

        linhas = []
        atual = ''
        medidor = self.TxtDescricao

        for palavra in palavras:
            teste = palavra if not atual else f'{atual} {palavra}'
            medidor.set_text(teste)
            medidor.set_pos((0, 0))
            if medidor.get_rect().width <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
                if len(linhas) == max_linhas - 1:
                    break

        if atual and len(linhas) < max_linhas:
            usadas = len(' '.join(linhas + [atual]).split())
            restante = palavras[usadas:]
            if restante:
                atual = atual + ' ' + ' '.join(restante)
            medidor.set_text(atual)
            medidor.set_pos((0, 0))
            while medidor.get_rect().width > largura and len(atual) > 1:
                atual = atual[:-1]
                medidor.set_text(atual + '...')
                medidor.set_pos((0, 0))
            if len(restante) > 0:
                atual = atual.rstrip() + '...'
            linhas.append(atual)

        return linhas[:max_linhas]

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
        box_icone = pygame.Rect(area.right - 58, area.y + (area.height - 52) // 2, 52, 52)
        nome_x = area.x + margem - 2
        desc_x = area.x + 158
        raridade_x = area.x + 330
        centro_y = area.centery
        self.TxtNome.set_text(nome)
        self.TxtNome.set_pos((nome_x, centro_y))
        self.TxtNome.draw(tela)

        self.TxtRaridade.set_text(raridade_texto)
        self.TxtRaridade.set_pos((raridade_x, centro_y))
        rar_rect = self.TxtRaridade.get_rect()
        pill_rect = pygame.Rect(0, 0, rar_rect.width + 20, rar_rect.height + 6)
        pill_rect.center = (raridade_x + pill_rect.width // 2, centro_y)
        pygame.draw.rect(tela, raridade_cor, pill_rect, border_radius=10)
        pygame.draw.rect(tela, (8, 12, 20), pill_rect, 2, border_radius=10)
        self.TxtRaridade.set_pos((pill_rect.centerx, pill_rect.centery))
        self.TxtRaridade.draw(tela)
        ItemInventario.desenhar_item_no_rect(tela, item, box_icone)

        linhas = self._quebrar_em_linhas(descricao, max(40, raridade_x - desc_x - 10), max_linhas=3)
        if not linhas:
            linhas = [descricao]
        bloco_h = len(linhas) * 14
        y_ini = centro_y - bloco_h // 2 + 1
        for i, linha in enumerate(linhas):
            self.TxtDescricao.set_text(linha)
            self.TxtDescricao.set_pos((desc_x, y_ini + i * 14))
            self.TxtDescricao.draw(tela)
