from __future__ import annotations

import csv
from pathlib import Path

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Painel import Painel
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
        self._painel = None
        self._rect_cache = None
        base = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20),
        }
        self.TxtTitulo = Texto('Ficha do item', style={**base, 'size': 20, 'color': (236, 241, 255)})
        self.TxtVazio = Texto('Passe o mouse em um item para ver os detalhes.', style={**base, 'size': 17, 'color': (166, 178, 208)})
        self.TxtNome = Texto('Item', style={**base, 'size': 22, 'color': (245, 247, 255)})
        self.TxtRaridade = Texto('-', style={**base, 'size': 16, 'color': (245, 247, 255)})
        self.TxtEstilo = Texto('-', style={**base, 'size': 16, 'color': (214, 222, 242)})
        self.TxtDescricao = Texto('', style={**base, 'size': 16, 'color': (181, 193, 220)})

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

    def _garantir_painel(self, rect):
        if self._painel is not None and self._rect_cache == tuple(rect):
            return
        self._rect_cache = tuple(rect)
        self._painel = Painel(rect, cor_fundo=(20, 26, 42, 238), cor_borda=(74, 98, 146), borda=2, raio=16)

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
        self._garantir_painel(rect)
        self._painel.rect = pygame.Rect(rect)
        self._painel.render(tela, [], 0)
        area = pygame.Rect(rect)

        if item is None:
            self.TxtTitulo.set_text('Ficha do item')
            self.TxtTitulo.set_pos((area.x + 18, area.y + 12))
            self.TxtTitulo.draw(tela)
            self.TxtVazio.set_pos((area.x + 18, area.y + 50))
            self.TxtVazio.draw(tela)
            return

        info = self._info_item(item)
        nome = str(item.get('Nome') or item.get('nome') or info.get('Nome') or 'Item')
        descricao = str(item.get('Descrição') or item.get('descricao') or info.get('Descrição') or 'Sem descrição cadastrada.')
        estilo = str(item.get('Estilo') or item.get('estilo') or info.get('Estilo') or '-')
        raridade = str(item.get('Raridade') or item.get('raridade') or info.get('Raridade') or '-')
        raridade_texto, raridade_cor = self._dados_raridade(raridade)

        topo_y = area.y + 12
        margem = 18
        box_icone = pygame.Rect(area.x + margem, area.y + 50, 68, 68)
        area_texto_x = box_icone.right + 14
        area_texto_w = area.right - margem - area_texto_x

        self.TxtNome.set_text(nome)
        self.TxtNome.set_pos((area.x + margem, topo_y))
        self.TxtNome.draw(tela)
        nome_rect = self.TxtNome.get_rect()

        self.TxtEstilo.set_text(estilo)
        self.TxtEstilo.set_pos((0, 0))
        estilo_w = self.TxtEstilo.get_rect().width
        estilo_x = area.right - margem - estilo_w
        self.TxtEstilo.set_pos((estilo_x, topo_y + 3))
        self.TxtEstilo.draw(tela)

        self.TxtRaridade.set_text(raridade_texto)
        self.TxtRaridade.set_pos((0, 0))
        rar_rect = self.TxtRaridade.get_rect()
        pill_rect = pygame.Rect(0, 0, rar_rect.width + 24, rar_rect.height + 8)
        pill_x = min(area.right - margem - estilo_w - 12 - pill_rect.width, max(nome_rect.right + 12, area.x + margem + 120))
        pill_rect.topleft = (pill_x, topo_y)
        pygame.draw.rect(tela, raridade_cor, pill_rect, border_radius=10)
        pygame.draw.rect(tela, (8, 12, 20), pill_rect, 2, border_radius=10)
        self.TxtRaridade.set_pos((pill_rect.x + (pill_rect.width - rar_rect.width) // 2, pill_rect.y + (pill_rect.height - rar_rect.height) // 2 - 1))
        self.TxtRaridade.draw(tela)

        pygame.draw.rect(tela, (46, 60, 96), box_icone, border_radius=12)
        pygame.draw.rect(tela, (86, 110, 162), box_icone, 2, border_radius=12)
        ItemInventario.desenhar_item_no_rect(tela, item, box_icone.inflate(-10, -10))

        linhas = self._quebrar_em_linhas(descricao, area_texto_w, max_linhas=3)
        for i, linha in enumerate(linhas):
            self.TxtDescricao.set_text(linha)
            self.TxtDescricao.set_pos((area_texto_x, box_icone.y + 6 + i * 20))
            self.TxtDescricao.draw(tela)
