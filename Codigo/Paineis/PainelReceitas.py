from __future__ import annotations

import copy
import csv
import json
import unicodedata
from pathlib import Path

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto


class PainelReceitas(PainelRolavel):
    _receitas_cache = None
    _itens_cache = None

    def __init__(self, rect):
        super().__init__(
            rect,
            area_real=(0, 0, rect[2], rect[3]),
            cor_fundo=(18, 26, 44, 242),
            cor_borda=(66, 88, 136),
            borda=2,
            raio=16
        )

        self.Colunas = 6
        self.SlotPx = 50
        self.Gap = 8
        self.Padding = 16

        self.Receitas = self._carregar_receitas()
        self._hover = None
        self._visiveis = []

        base = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20)
        }
        self.TxtTitulo = Texto(
            'Receitas',
            style={**base, 'size': 19, 'color': (236, 241, 255)}
        )

        self.Filtros = {
            'verde': True,
            'amarelo': True,
            'vermelho': False
        }
        self.BotoesFiltro = self._criar_botoes_filtro()

    @staticmethod
    def _norm(texto):
        base = ''.join(
            c for c in unicodedata.normalize('NFKD', str(texto or '').lower())
            if not unicodedata.combining(c)
        )
        for ch in ('_', '-', "'", '.'):
            base = base.replace(ch, ' ')
        return ' '.join(base.split())

    @classmethod
    def _caminho_json(cls):
        caminhos = [
            Path('Dados') / 'Pokemon Global Server - Receitas.json',
            Path('Pokemon Global Server - Receitas.json'),
            Path(__file__).resolve().parents[3] / 'Dados' / 'Pokemon Global Server - Receitas.json',
            Path(__file__).resolve().parents[3] / 'Pokemon Global Server - Receitas.json',
        ]
        return next((p for p in caminhos if p.exists()), None)

    @classmethod
    def _caminho_itens_csv(cls):
        caminhos = [
            Path('Dados') / 'Pokemon Global Server - Itens.csv',
            Path('Pokemon Global Server - Itens.csv'),
            Path(__file__).resolve().parents[3] / 'Dados' / 'Pokemon Global Server - Itens.csv',
            Path(__file__).resolve().parents[3] / 'Pokemon Global Server - Itens.csv',
        ]
        return next((p for p in caminhos if p.exists()), None)

    @classmethod
    def _carregar_itens_csv(cls):
        if cls._itens_cache is not None:
            return cls._itens_cache

        mapa = {}
        caminho = cls._caminho_itens_csv()

        if caminho is None:
            cls._itens_cache = mapa
            return mapa

        try:
            with caminho.open('r', encoding='utf-8-sig', newline='') as arquivo:
                for linha in csv.DictReader(arquivo):
                    dado = dict(linha)
                    nome = str(dado.get('Nome') or '').strip()
                    code = str(dado.get('Code') or '').strip()

                    if nome:
                        mapa[('nome', cls._norm(nome))] = dado
                    if code:
                        mapa[('code', cls._norm(code))] = dado
        except OSError:
            pass

        cls._itens_cache = mapa
        return mapa

    @classmethod
    def _item_real_por_nome(cls, nome):
        nome = str(nome or '').strip()
        if not nome:
            return None

        base = cls._carregar_itens_csv()
        chave_norm = cls._norm(nome)
        dado = base.get(('nome', chave_norm)) or base.get(('code', chave_norm))

        if dado is None:
            return {'Nome': nome, 'quantidade': 1}

        item = copy.deepcopy(dado)
        item['Nome'] = item.get('Nome') or nome
        item['quantidade'] = 1
        return item

    @classmethod
    def _item_grade_para_slot(cls, entrada):
        if entrada is None:
            return None

        quantidade = 1
        nome_item = entrada
        if isinstance(entrada, list):
            if len(entrada) <= 0:
                return None
            nome_item = entrada[0]
            if len(entrada) >= 2:
                try:
                    quantidade = max(1, int(entrada[1]))
                except (TypeError, ValueError):
                    quantidade = 1

        item = cls._item_real_por_nome(nome_item)
        if item is None:
            return None
        item['quantidade'] = quantidade
        return item

    @staticmethod
    def _quantidade_saida_receita(grade):
        if not isinstance(grade, list):
            return 1
        bruto = None
        if len(grade) >= 10 and not isinstance(grade[9], list):
            bruto = grade[9]
        elif len(grade) >= 4 and not isinstance(grade[3], list):
            bruto = grade[3]
        try:
            return max(1, int(bruto))
        except (TypeError, ValueError):
            return 1

    @classmethod
    def _carregar_receitas(cls):
        if cls._receitas_cache is not None:
            return cls._receitas_cache

        caminho = cls._caminho_json()
        receitas = []

        if caminho is None:
            cls._receitas_cache = receitas
            return receitas

        try:
            with caminho.open('r', encoding='utf-8-sig') as arquivo:
                bruto = json.load(arquivo)
        except (OSError, json.JSONDecodeError):
            bruto = {}

        if isinstance(bruto, dict):
            for nome_saida, grade in bruto.items():
                if not isinstance(grade, list):
                    continue

                receita = {
                    'nome': str(nome_saida),
                    'saida': cls._item_real_por_nome(nome_saida),
                    'grade': [None] * 9
                }
                if isinstance(receita['saida'], dict):
                    receita['saida']['quantidade'] = cls._quantidade_saida_receita(grade)

                idx = 0
                for lin in range(3):
                    linha = grade[lin] if lin < len(grade) and isinstance(grade[lin], list) else []
                    for col in range(3):
                        entrada = linha[col] if col < len(linha) else None
                        receita['grade'][idx] = cls._item_grade_para_slot(entrada)
                        idx += 1

                receitas.append(receita)

        cls._receitas_cache = receitas
        return receitas

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)

        altura_atual_area_real = self.AreaReal.height if hasattr(self, 'AreaReal') else self.rect.height
        self.definir_area_real(self.rect.width, max(self.rect.height, altura_atual_area_real))

        for i, chave in enumerate(('verde', 'amarelo', 'vermelho')):
            novo = self._rect_filtro(i)
            self.BotoesFiltro[chave].base_rect = pygame.Rect(novo)
            self.BotoesFiltro[chave].rect = pygame.Rect(novo)

    def _criar_botoes_filtro(self):
        cores = {
            'verde': ((65, 170, 90), (90, 210, 120), (40, 120, 60)),
            'amarelo': ((205, 175, 60), (235, 205, 90), (150, 120, 35)),
            'vermelho': ((186, 72, 72), (220, 105, 105), (126, 45, 45)),
        }

        botoes = {}
        for i, chave in enumerate(('verde', 'amarelo', 'vermelho')):
            bg, hover, pressed = cores[chave]
            botoes[chave] = Botao(
                self._rect_filtro(i),
                '',
                style={
                    'radius': 6,
                    'border_width': 2,
                    'bg': bg,
                    'bg_hover': hover,
                    'bg_pressed': pressed,
                    'border': (230, 238, 250) if self.Filtros[chave] else (20, 26, 40),
                    'border_hover': (230, 238, 250),
                    'hover_scale': 1.0,
                    'press_scale': 1.0,
                    'text_style': {
                        'size': 1,
                        'color': (255, 255, 255),
                        'align': 'center',
                        'outline': False,
                        'shadow': False
                    },
                },
            )
        return botoes

    def _rect_filtro(self, indice):
        tamanho = 20
        espacamento = 8
        total = 3 * tamanho + 2 * espacamento
        x = self.rect.right - self.Padding - total - 6 + indice * (tamanho + espacamento)
        y = self.rect.y + 14
        return pygame.Rect(x, y, tamanho, tamanho)

    def _area_lista(self):
        return pygame.Rect(
            self.rect.x + self.Padding,
            self.rect.y + 52,
            self.rect.width - self.Padding * 2,
            self.rect.height - 66
        )

    def _slot_rect(self, indice):
        col = indice % self.Colunas
        lin = indice // self.Colunas
        area_lista = self._area_lista()

        x = area_lista.x + col * (self.SlotPx + self.Gap)
        y = area_lista.y + lin * (self.SlotPx + self.Gap) - self.ScrollY

        return pygame.Rect(x, y, self.SlotPx, self.SlotPx)

    def _atualizar_area_rolagem(self, quantidade_receitas):
        linhas = max(1, (quantidade_receitas + self.Colunas - 1) // self.Colunas)
        area_lista = self._area_lista()

        altura_lista = linhas * (self.SlotPx + self.Gap) - self.Gap
        altura_total = (area_lista.y - self.rect.y) + altura_lista + self.Padding + 4

        self.definir_area_real(self.rect.width, max(self.rect.height, altura_total))

    def _nome_item(self, item):
        if not isinstance(item, dict):
            return self._norm(item)

        nome = str(item.get('Nome') or item.get('nome') or '').strip()
        if nome:
            return self._norm(nome)

        code = str(item.get('Code') or item.get('code') or '').strip()
        if not code:
            return ''

        base = self._carregar_itens_csv()
        dado = base.get(('code', self._norm(code)))
        if dado:
            return self._norm(dado.get('Nome'))
        return self._norm(code)

    def _quantidade_item(self, item):
        if not isinstance(item, dict):
            return 1 if item is not None else 0
        try:
            return max(0, int(item.get('quantidade', 1)))
        except (TypeError, ValueError):
            return 1

    def _quantidades_inventario(self, inventario_container):
        mapa = {}

        if inventario_container is None:
            return mapa

        for item in getattr(inventario_container, 'Itens', []):
            if item is None:
                continue
            nome = self._nome_item(item)
            if nome:
                mapa[nome] = mapa.get(nome, 0) + self._quantidade_item(item)

        return mapa

    def _estado_receita(self, receita, quantidades):
        precisa = {}

        for item in receita['grade']:
            if item is None:
                continue
            chave = self._nome_item(item)
            if not chave:
                continue
            precisa[chave] = precisa.get(chave, 0) + max(1, self._quantidade_item(item))

        if precisa and all(quantidades.get(ch, 0) >= qtd for ch, qtd in precisa.items()):
            return 'verde'
        if any(quantidades.get(ch, 0) > 0 for ch in precisa):
            return 'amarelo'
        return 'vermelho'

    def receitas_visiveis(self, inventario_container):
        quantidades = self._quantidades_inventario(inventario_container)
        self._visiveis = []

        for receita in self.Receitas:
            estado = self._estado_receita(receita, quantidades)
            if self.Filtros.get(estado, False):
                self._visiveis.append((receita, estado))

        return self._visiveis

    def estado_atual_receita(self, receita, inventario_container):
        for receita_visivel, estado in self._visiveis:
            if receita_visivel is receita:
                return estado
        quantidades = self._quantidades_inventario(inventario_container)
        return self._estado_receita(receita, quantidades)

    def processar_eventos(self, tela, eventos, dt, inventario_container):
        self._hover = None
        receita_clicada = None
        mouse = pygame.mouse.get_pos()

        for chave, botao in self.BotoesFiltro.items():
            botao.set_style(
                border=(230, 238, 250) if self.Filtros[chave] else (20, 26, 40),
                border_hover=(230, 238, 250)
            )
            for evento in eventos:
                if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and botao.rect.collidepoint(evento.pos):
                    self.Filtros[chave] = not self.Filtros[chave]
                    break

        visiveis = self.receitas_visiveis(inventario_container)
        self._atualizar_area_rolagem(len(visiveis))

        self._processar_scroll(eventos)

        area_lista = self._area_lista()
        if area_lista.collidepoint(mouse):
            for i, (receita, estado) in enumerate(visiveis):
                rect = self._slot_rect(i)
                if area_lista.colliderect(rect) and rect.collidepoint(mouse):
                    self._hover = receita
                    break

        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self._hover is not None:
                receita_clicada = self._hover
                break

        return receita_clicada, self._hover

    def renderizar(self, tela, inventario_container):
        visiveis = self.receitas_visiveis(inventario_container)
        self._atualizar_area_rolagem(len(visiveis))

        self.render(tela, [], 0)

        self.TxtTitulo.set_pos((self.rect.x + 16, self.rect.y + 14))
        self.TxtTitulo.draw(tela)

        for chave, botao in self.BotoesFiltro.items():
            botao.set_style(
                border=(230, 238, 250) if self.Filtros[chave] else (20, 26, 40),
                border_hover=(230, 238, 250)
            )
            botao.render(tela, [], 0, None)

        cores = {
            'verde': (70, 170, 90),
            'amarelo': (205, 175, 60),
            'vermelho': (186, 72, 72)
        }

        area_lista = self._area_lista()
        clip_anterior = tela.get_clip()
        tela.set_clip(area_lista)

        for i, (receita, estado) in enumerate(visiveis):
            rect = self._slot_rect(i)

            if not area_lista.colliderect(rect):
                continue

            pygame.draw.rect(tela, cores[estado], rect, border_radius=10)
            pygame.draw.rect(
                tela,
                (228, 239, 255) if self._hover is receita else (20, 26, 40),
                rect,
                2,
                border_radius=10
            )
            ItemInventario.desenhar_item_no_rect(
                tela,
                receita['saida'],
                rect.inflate(-6, -6)
            )

        tela.set_clip(clip_anterior)
