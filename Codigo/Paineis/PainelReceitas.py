from __future__ import annotations

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

    def __init__(self, rect):
        super().__init__(rect, area_real=(0, 0, rect[2], rect[3]), cor_fundo=(18, 26, 44, 242), cor_borda=(66, 88, 136), borda=2, raio=16)
        self.Colunas = 5
        self.LinhasVisiveis = 2
        self.SlotPx = 54
        self.Gap = 10
        self.Padding = 16
        self.TopOffset = 48
        self.Receitas = self._carregar_receitas()
        self._hover = None
        self._visiveis = []

        base = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtTitulo = Texto('Receitas', style={**base, 'size': 19, 'color': (236, 241, 255)})

        self.Filtros = {'verde': True, 'amarelo': True, 'vermelho': False}
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

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self.definir_area_real(self.rect.width, max(self.rect.height, self.altura_conteudo()))
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
                    'text_style': {'size': 1, 'color': (255, 255, 255), 'hover_color': (255, 255, 255), 'align': 'center', 'outline': False, 'shadow': False},
                },
            )
        return botoes

    @classmethod
    def _carregar_receitas(cls):
        if cls._receitas_cache is not None:
            return cls._receitas_cache

        caminhos = [
            Path('Dados') / 'Global server - Receitas.json',
            Path('Global server - Receitas.json'),
            Path(__file__).resolve().parents[3] / 'Global server - Receitas.json',
        ]
        caminho = next((p for p in caminhos if p.exists()), None)
        receitas = []
        if caminho is None:
            cls._receitas_cache = receitas
            return receitas

        with caminho.open('r', encoding='utf-8-sig') as arquivo:
            bruto = json.load(arquivo)

        if isinstance(bruto, dict):
            for nome_saida, grade in bruto.items():
                grade_final = []
                for linha in grade or []:
                    for valor in linha or []:
                        grade_final.append(None if valor is None or valor == '' else {'Nome': str(valor), 'quantidade': 1})
                while len(grade_final) < 9:
                    grade_final.append(None)
                receitas.append({
                    'nome': str(nome_saida),
                    'saida': {'Nome': str(nome_saida), 'quantidade': 1},
                    'grade': grade_final[:9],
                })

        cls._receitas_cache = receitas
        return receitas

    def altura_conteudo(self):
        linhas = max(self.LinhasVisiveis, (max(1, len(self.Receitas)) + self.Colunas - 1) // self.Colunas)
        return self.TopOffset + self.Padding + linhas * self.SlotPx + max(0, linhas - 1) * self.Gap + self.Padding

    def _rect_filtro(self, indice):
        tamanho = 20
        espacamento = 8
        total = 3 * tamanho + 2 * espacamento
        x = self.rect.right - 16 - total + indice * (tamanho + espacamento)
        y = self.rect.y + 12
        return pygame.Rect(x, y, tamanho, tamanho)

    def _slot_rect(self, indice):
        col = indice % self.Colunas
        lin = indice // self.Colunas
        x = self.rect.x + self.Padding + col * (self.SlotPx + self.Gap)
        y = self.rect.y + self.TopOffset + lin * (self.SlotPx + self.Gap) - self.ScrollY
        return pygame.Rect(x, y, self.SlotPx, self.SlotPx)

    def _chave_item(self, item):
        if isinstance(item, dict):
            return self._norm(item.get('Nome') or item.get('nome') or item.get('Code') or item.get('code') or '')
        return self._norm(item)

    def _estado_receita(self, receita, quantidades):
        precisa = {}
        for item in receita['grade']:
            if item is None:
                continue
            chave = self._chave_item(item)
            precisa[chave] = precisa.get(chave, 0) + 1
        if precisa and all(quantidades.get(chave, 0) >= qtd for chave, qtd in precisa.items()):
            return 'verde'
        if any(quantidades.get(chave, 0) > 0 for chave in precisa):
            return 'amarelo'
        return 'vermelho'

    def receitas_visiveis(self, inventario_container):
        quantidades = inventario_container.quantidade_por_nome() if inventario_container is not None else {}
        quantidades = {self._norm(chave): valor for chave, valor in quantidades.items()}
        self._visiveis = []
        for receita in self.Receitas:
            estado = self._estado_receita(receita, quantidades)
            if self.Filtros.get(estado, False):
                self._visiveis.append((receita, estado))
        self.definir_area_real(self.rect.width, max(self.rect.height, self.altura_conteudo()))
        return self._visiveis

    def _toggle_filtros(self, eventos):
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                for chave, botao in self.BotoesFiltro.items():
                    if botao.rect.collidepoint(evento.pos):
                        self.Filtros[chave] = not self.Filtros[chave]

    def processar_eventos(self, tela, eventos, dt, inventario_container):
        self._processar_scroll(eventos)
        self._toggle_filtros(eventos)

        for chave, botao in self.BotoesFiltro.items():
            botao.set_style(border=(230, 238, 250) if self.Filtros[chave] else (20, 26, 40), border_hover=(230, 238, 250))
            botao.render(tela, eventos, dt, None)

        mouse = pygame.mouse.get_pos()
        visiveis = self.receitas_visiveis(inventario_container)
        self._hover = None
        for i, (receita, _estado) in enumerate(visiveis):
            rect = self._slot_rect(i)
            if self.rect.colliderect(rect) and rect.collidepoint(mouse):
                self._hover = receita
                break

        clicada = None
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for i, (receita, _estado) in enumerate(visiveis):
                    rect = self._slot_rect(i)
                    if self.rect.colliderect(rect) and rect.collidepoint(evento.pos):
                        clicada = receita
                        break
        return clicada, self._hover

    def renderizar(self, tela, inventario_container, eventos=None, dt=0):
        self.render(tela, [], 0)
        self.TxtTitulo.set_pos((self.rect.x + 16, self.rect.y + 12))
        self.TxtTitulo.draw(tela)

        for chave, botao in self.BotoesFiltro.items():
            botao.set_style(border=(230, 238, 250) if self.Filtros[chave] else (20, 26, 40), border_hover=(230, 238, 250))
            botao.render(tela, eventos or [], dt, None)

        visiveis = self.receitas_visiveis(inventario_container)
        cores = {
            'verde': ((65, 170, 90), (228, 239, 255)),
            'amarelo': ((205, 175, 60), (228, 239, 255)),
            'vermelho': ((186, 72, 72), (228, 239, 255)),
        }
        for i, (receita, estado) in enumerate(visiveis):
            rect = self._slot_rect(i)
            if not self.rect.colliderect(rect):
                continue
            cor_bg, cor_hover = cores[estado]
            pygame.draw.rect(tela, cor_bg, rect, border_radius=10)
            pygame.draw.rect(tela, cor_hover if self._hover is receita else (20, 26, 40), rect, 2, border_radius=10)
            ItemInventario.desenhar_item_no_rect(tela, receita['saida'], rect.inflate(-6, -6))
        return self._hover
