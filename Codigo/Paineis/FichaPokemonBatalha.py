from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Paineis.FichaPokemon import FichaPokemon
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
from Codigo.Paineis.FichaAtaque import FichaAtaque
from Codigo.Prefabs.Texto import Texto
from Codigo.Prefabs.Tooltip import Tooltip


class FichaPokemonBatalha:
    _COR_FUNDO = (10, 16, 28)
    _COR_SETOR = (12, 20, 34)
    _COR_SETOR_2 = (18, 27, 44)
    _COR_BORDA = (108, 136, 188)
    _COR_BORDA_SUAVE = (58, 76, 112)
    _COR_TITULO = (245, 249, 255)
    _COR_SUB = (188, 202, 232)
    _COR_TEXTO = (236, 241, 252)

    _ESTILO_TEXTO_BASE = {
        'outline': True,
        'outline_color': (6, 10, 18),
        'outline_thickness': 2,
        'shadow': False,
    }

    def __init__(self) -> None:
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._cache_tela: Optional[Tuple[int, int]] = None
        self._t_extra = 0.0
        self._extra_aberto = False

        self._barra_vida: Optional[Barra] = None
        self._barra_energia: Optional[Barra] = None

        self._botao_extra = self._criar_botao('+', self._alternar_extra)
        self._botao_mover = self._criar_botao('', None)
        self._botao_trocar = self._criar_botao('', None)
        self._botoes_habilidade: list[Botao] = []

        self._txt_titulo = Texto('', style={**self._ESTILO_TEXTO_BASE, 'size': 23, 'align': 'center', 'color': self._COR_TITULO})
        self._txt_sub = Texto('', style={**self._ESTILO_TEXTO_BASE, 'size': 15, 'align': 'center', 'color': self._COR_SUB})
        self._txt_numero = Texto('', style={**self._ESTILO_TEXTO_BASE, 'size': 15, 'align': 'midleft', 'color': self._COR_TEXTO})
        self._txt_centro = Texto('', style={**self._ESTILO_TEXTO_BASE, 'size': 14, 'align': 'center', 'color': self._COR_TEXTO})
        self._txt_barra = Texto('', style={**self._ESTILO_TEXTO_BASE, 'size': 14, 'align': 'midright', 'color': self._COR_TEXTO})
        self._txt_micro = Texto('', style={**self._ESTILO_TEXTO_BASE, 'size': 13, 'align': 'center', 'color': self._COR_SUB})

        self._ficha_ataque = FichaAtaque()
        self._tooltip_simples = Tooltip('', largura_max=280, padding=10, raio=12)
        self._mouse_pos = (0, 0)
        self._ataque_selecionado: dict | None = None
        self._previsao_consumo: float = 0.0
        self._previsao_pode: bool = True
        self._hover_atributo: tuple[str, str] | None = None
        self._hover_ataque: tuple[dict, pygame.Rect] | None = None
        self._hover_acao: tuple[str, str] | None = None

        self._cache_icones_stats: dict[tuple[str, int], pygame.Surface | None] = {}
        self._cache_icones_diversos: dict[tuple[str, int], pygame.Surface | None] = {}
        self._cache_ataque_icones: dict[tuple[str, str, int], pygame.Surface | None] = {}

    def _criar_botao(self, texto: str, execute) -> Botao:
        return Botao(
            pygame.Rect(0, 0, 10, 10),
            texto,
            execute=execute,
            style={
                'radius': 10,
                'border_width': 2,
                'bg': (20, 30, 48),
                'bg_hover': (34, 48, 74),
                'bg_pressed': (16, 24, 40),
                'border': (122, 152, 206),
                'border_hover': (224, 235, 255),
                'hover_scale': 1.0,
                'press_scale': 0.98,
                'text_style': {
                    'size': 18,
                    'align': 'center',
                    'outline': True,
                    'outline_thickness': 2,
                    'outline_color': (0, 0, 0),
                    'shadow': False,
                    'color': (255, 255, 255),
                    'hover_color': (255, 255, 255),
                },
            },
        )

    def _alternar_extra(self, _jogo=None, _botao=None):
        self._extra_aberto = not self._extra_aberto
        self._atualizar_estilo_botao_extra()

    def _atualizar_estilo_botao_extra(self):
        if self._extra_aberto:
            self._botao_extra.set_style(
                bg=(72, 100, 170),
                bg_hover=(92, 122, 202),
                bg_pressed=(58, 82, 144),
                border=(214, 230, 255),
                border_hover=(255, 255, 255),
            )
        else:
            self._botao_extra.set_style(
                bg=(20, 30, 48),
                bg_hover=(34, 48, 74),
                bg_pressed=(16, 24, 40),
                border=(122, 152, 206),
                border_hover=(224, 235, 255),
            )

    def _garantir_layout(self, tela: pygame.Surface):
        tamanho = tuple(tela.get_size())
        if self._cache_tela == tamanho and self.rect.width > 0:
            return
        self._cache_tela = tamanho
        w, h = tamanho
        largura = min(1100, max(820, int(w * 0.82)))
        altura = min(205, max(152, int(h * 0.22)))
        self.rect = pygame.Rect((w - largura) // 2, h - altura - 18, largura, altura)

    def _atualizar_animacoes(self, dt: float):
        velocidade = min(1.0, max(0.0, float(dt)) * 9.0)
        alvo = 1.0 if self._extra_aberto else 0.0
        self._t_extra += (alvo - self._t_extra) * velocidade
        if abs(self._t_extra - alvo) < 0.001:
            self._t_extra = alvo

    @staticmethod
    def _interpolar(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _icone_stat(self, chave: str, lado: int) -> Optional[pygame.Surface]:
        aliases = {
            'EnergiaMaxima': ('EnergiaMaxima', 'EnergiaMax', 'Ene'),
            'Vamp': ('Vamp', 'Vampirismo'),
            'Precisao': ('Precisao', 'Precisão', 'Per'),
            'Int': ('Int', 'Inteligencia', 'Inteligência'),
            'SpA': ('SpA', 'AtaqueEspecial'),
            'SpD': ('SpD', 'DefesaEspecial'),
            'CrC': ('CrC', 'CriticoChance', 'ChanceCritico'),
            'CrD': ('CrD', 'CriticoDano', 'DanoCritico'),
        }
        chave_cache = (str(chave), int(lado))
        if chave_cache in self._cache_icones_stats:
            return self._cache_icones_stats[chave_cache]
        nomes = aliases.get(str(chave), (str(chave),))
        arquivo = FichaPokemon._achar_arquivo(Path('Recursos') / 'Visual' / 'Icones' / 'Atributos', *nomes)
        surf = FichaPokemon._carregar_surface(arquivo, (lado, lado), chave_extra='contain') if arquivo is not None else None
        self._cache_icones_stats[chave_cache] = surf
        return surf

    def _icone_diverso(self, nome: str, lado: int) -> Optional[pygame.Surface]:
        chave_cache = (str(nome), int(lado))
        if chave_cache in self._cache_icones_diversos:
            return self._cache_icones_diversos[chave_cache]
        arquivo = FichaPokemon._achar_arquivo(Path('Recursos') / 'Visual' / 'Icones' / 'Diversos', nome)
        surf = FichaPokemon._carregar_surface(arquivo, (lado, lado), chave_extra='contain') if arquivo is not None else None
        self._cache_icones_diversos[chave_cache] = surf
        return surf

    def _icone_ataque(self, ataque: dict, lado: int) -> Optional[pygame.Surface]:
        nome = str(ataque.get('Ataque') or ataque.get('Nome') or ataque.get('nome') or '').strip()
        tipo = str(ataque.get('Tipo') or ataque.get('tipo') or 'Normal').strip() or 'Normal'
        chave = (nome.lower(), tipo.lower(), int(lado))
        if chave in self._cache_ataque_icones:
            return self._cache_ataque_icones[chave]
        caminho = FichaPokemon._icone_ataque_path(nome, tipo)
        surf = FichaPokemon._carregar_surface(caminho, (lado, lado), chave_extra='contain') if caminho is not None else None
        self._cache_ataque_icones[chave] = surf
        return surf

    def _sincronizar_botoes_habilidade(self, quantidade: int):
        quantidade = max(0, int(quantidade))
        while len(self._botoes_habilidade) < quantidade:
            self._botoes_habilidade.append(self._criar_botao('', None))
        if len(self._botoes_habilidade) > quantidade:
            self._botoes_habilidade = self._botoes_habilidade[:quantidade]

    def _desenhar_fundo(self, tela: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(tela, self._COR_FUNDO, rect, border_radius=18)
        pygame.draw.rect(tela, self._COR_BORDA, rect, width=2, border_radius=18)

    def _desenhar_setor(self, tela: pygame.Surface, rect: pygame.Rect, secundario: bool = False):
        pygame.draw.rect(tela, self._COR_SETOR_2 if secundario else self._COR_SETOR, rect, border_radius=14)
        pygame.draw.rect(tela, self._COR_BORDA_SUAVE, rect, width=1, border_radius=14)

    def _desenhar_texto(self, texto_obj: Texto, tela: pygame.Surface, texto: str, pos, *, align: str | None = None):
        texto_obj.set_text(str(texto or ''))
        if align is not None:
            texto_obj.set_style(align=align)
        texto_obj.set_pos(pos)
        texto_obj.draw(tela)

    @staticmethod
    def _nome_atributo(chave: str) -> str:
        mapa = {
            'Atk': 'Ataque',
            'Def': 'Defesa',
            'SpA': 'Ataque Especial',
            'SpD': 'Defesa Especial',
            'Vel': 'Velocidade',
            'Mag': 'Magia',
            'Per': 'Precisão',
            'Ene': 'Energia Base',
            'Int': 'Inteligência',
            'Vamp': 'Vampirismo',
            'Vida': 'Vida Máxima',
            'EnergiaMaxima': 'Energia Máxima',
            'Peso': 'Peso',
            'Escala': 'Escala',
            'Amplificacao': 'Amplificação',
            'Durabilidade': 'Durabilidade',
            'CrC': 'Chance Crítica',
            'CrD': 'Dano Crítico',
            'Barreira': 'Barreira',
            'Precisao': 'Precisão',
        }
        return mapa.get(str(chave), str(chave))

    @staticmethod
    def _fmt_numero(valor: float) -> str:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return '0'
        if abs(numero - round(numero)) < 0.001:
            return str(int(round(numero)))
        return f'{numero:.1f}'

    def _registrar_hover_atributo(self, chave: str, pokemon):
        nome = self._nome_atributo(chave)
        base = getattr(pokemon, 'obter_valor_base_ficha', pokemon.obter_valor_ficha)(chave)
        variacao = getattr(pokemon, 'obter_variacao_ficha', lambda _c: 0.0)(chave)
        total = getattr(pokemon, 'obter_valor_ficha', lambda _c: base)(chave)
        sinal = '+' if float(variacao) >= 0 else '-'
        descricao = (
            f"{self._fmt_numero(base)} base {sinal} {self._fmt_numero(abs(float(variacao)))} variação = {self._fmt_numero(total)}"
        )
        self._hover_atributo = (nome, descricao)

    def _registrar_hover_acao(self, titulo: str, descricao: str):
        self._hover_acao = (titulo, descricao)

    def _renderizar_tooltips(self, tela: pygame.Surface):
        if self._hover_ataque is not None:
            ataque, area = self._hover_ataque
            self._ficha_ataque.renderizar_tooltip(tela, ataque, area_ancora=area, mouse_pos=self._mouse_pos)
            return
        if self._hover_atributo is not None:
            titulo, descricao = self._hover_atributo
            self._tooltip_simples.definir_conteudo(titulo=titulo, descricao=descricao)
            self._tooltip_simples.render(tela, mouse_pos=self._mouse_pos, forcar=True)
            return
        if self._hover_acao is not None:
            titulo, descricao = self._hover_acao
            self._tooltip_simples.definir_conteudo(titulo=titulo, descricao=descricao)
            self._tooltip_simples.render(tela, mouse_pos=self._mouse_pos, forcar=True)

    def _desenhar_atributo(self, tela: pygame.Surface, area: pygame.Rect, pokemon, chave: str):
        valor = pokemon.obter_valor_ficha(chave)
        icon_lado = max(16, min(22, area.height - 4))
        icone = self._icone_stat(chave, icon_lado)
        x = area.x + 8
        if icone is not None:
            tela.blit(icone, icone.get_rect(midleft=(x, area.centery)))
            x += icon_lado + 7
        else:
            self._desenhar_texto(self._txt_micro, tela, chave[:3], (x + 11, area.centery), align='center')
            x += 26
        texto = f"{int(round(float(valor)))}" if isinstance(valor, (int, float)) else str(valor)
        self._desenhar_texto(self._txt_numero, tela, texto, (x, area.centery), align='midleft')
        if area.collidepoint(self._mouse_pos):
            self._registrar_hover_atributo(chave, pokemon)

    def _desenhar_grade_atributos(self, tela: pygame.Surface, area: pygame.Rect, pokemon, esquerda: list[str | None], direita: list[str]):
        area_interna = area.inflate(-8, -8)
        linha_h = max(28, area_interna.height // 5)
        col_w = area_interna.width // 2
        for idx in range(5):
            y = area_interna.y + idx * linha_h
            rect_esq = pygame.Rect(area_interna.x, y, col_w, linha_h)
            rect_dir = pygame.Rect(area_interna.x + col_w, y, col_w, linha_h)
            if esquerda[idx]:
                self._desenhar_atributo(tela, rect_esq, pokemon, esquerda[idx])
            if direita[idx]:
                self._desenhar_atributo(tela, rect_dir, pokemon, direita[idx])

    def _desenhar_extra_esquerda(self, tela: pygame.Surface, area: pygame.Rect, pokemon):
        if area.width <= 8:
            return
        self._desenhar_setor(tela, area, secundario=True)
        chaves = list(getattr(pokemon, 'listar_atributos_extras_ficha', lambda _=10: [])(10) or [])
        while len(chaves) < 10:
            chaves.append(None)
        esquerda = chaves[:5]
        direita = chaves[5:10]
        self._desenhar_grade_atributos(tela, area, pokemon, esquerda, direita)

    def _desenhar_stats_esquerda(self, tela: pygame.Surface, area: pygame.Rect, pokemon):
        self._desenhar_setor(tela, area)
        esquerda = ['Atk', 'Def', 'Mag', 'Vel', 'Vamp' if self._t_extra > 0.55 else None]
        direita = ['SpA', 'SpD', 'Ene', 'Per', 'Int']
        self._desenhar_grade_atributos(tela, area, pokemon, esquerda, direita)

    def _desenhar_botao_extra(self, tela: pygame.Surface, area_principal: pygame.Rect, area_extra: pygame.Rect, eventos, dt: float):
        area_interna = area_principal.inflate(-8, -8)
        linha_h = max(28, area_interna.height // 5)
        col_w = area_interna.width // 2
        destino_fechado = pygame.Rect(area_interna.x + 8, area_interna.y + linha_h * 4 + (linha_h - 26) // 2, 26, 26)
        destino_aberto = pygame.Rect(area_extra.x + 8, area_extra.bottom - 34, 26, 26)
        if area_extra.width <= 8:
            destino_aberto = destino_fechado

        x = int(round(self._interpolar(destino_fechado.x, destino_aberto.x, self._t_extra)))
        y = int(round(self._interpolar(destino_fechado.y, destino_aberto.y, self._t_extra)))
        self._botao_extra.base_rect = pygame.Rect(x, y, 26, 26)
        self._botao_extra.rect = pygame.Rect(self._botao_extra.base_rect)
        self._botao_extra.set_text('+')
        self._botao_extra.render(tela, eventos or [], dt, None)

    def _desenhar_ataques(self, tela: pygame.Surface, area: pygame.Rect, pokemon, eventos, dt: float):
        padding = 8
        habilidades = list(getattr(pokemon, 'obter_ataques_ficha', lambda limite=None: getattr(pokemon, 'ListaAtaques', []))(5) or [])[:5]
        if self._ataque_selecionado is not None and self._ataque_selecionado not in habilidades:
            self._ataque_selecionado = None
        total = len(habilidades)
        self._sincronizar_botoes_habilidade(total)

        area_interna = area.inflate(-padding * 2, -padding * 2)
        acao_lado = max(30, min(38, int(area_interna.height * 0.52)))
        area_acoes = pygame.Rect(area_interna.right - acao_lado, area_interna.y, acao_lado, area_interna.height)
        area_skills = pygame.Rect(area_interna.x, area_interna.y, max(10, area_interna.width - area_acoes.width - 10), area_interna.height)

        skill_lado = max(38, min(60, area_skills.height - 6))
        if total > 0:
            largura_usada = total * skill_lado
            sobra = max(0, area_skills.width - largura_usada)
            gap = 0 if total <= 1 else min(16, sobra // (total - 1))
            largura_total = total * skill_lado + max(0, total - 1) * gap
            x = area_skills.x + max(0, (area_skills.width - largura_total) // 2)
            y = area_skills.y + (area_skills.height - skill_lado) // 2
            for botao, ataque in zip(self._botoes_habilidade, habilidades):
                botao.base_rect = pygame.Rect(x, y, skill_lado, skill_lado)
                botao.rect = pygame.Rect(botao.base_rect)
                botao.set_text('')
                selecionado = ataque == self._ataque_selecionado
                botao.set_style(
                    bg=(40, 115, 64) if selecionado else (20, 30, 48),
                    bg_hover=(52, 132, 78) if selecionado else (34, 48, 74),
                    bg_pressed=(30, 88, 52) if selecionado else (16, 24, 40),
                    border=(214, 230, 255) if selecionado else (122, 152, 206),
                    border_hover=(255, 255, 255) if selecionado else (224, 235, 255),
                )
                botao.render(tela, eventos or [], dt, None)
                if botao.clicado:
                    self._ataque_selecionado = ataque
                icone = self._icone_ataque(ataque, skill_lado - 10)
                if icone is not None:
                    tela.blit(icone, icone.get_rect(center=botao.rect.center))
                else:
                    nome = str(ataque.get('Ataque') or ataque.get('Nome') or 'Atk')[:2].upper()
                    self._desenhar_texto(self._txt_centro, tela, nome, botao.rect.center, align='center')
                if botao.rect.collidepoint(self._mouse_pos):
                    self._hover_ataque = (ataque, pygame.Rect(botao.rect))
                x += skill_lado + gap

        self._botao_mover.base_rect = pygame.Rect(area_acoes.x, area_acoes.y + 2, acao_lado, acao_lado)
        self._botao_mover.rect = pygame.Rect(self._botao_mover.base_rect)
        mover_selecionado = self._ataque_selecionado is None
        self._botao_mover.set_style(
            bg=(40, 115, 64) if mover_selecionado else (20, 30, 48),
            bg_hover=(52, 132, 78) if mover_selecionado else (34, 48, 74),
            bg_pressed=(30, 88, 52) if mover_selecionado else (16, 24, 40),
            border=(214, 230, 255) if mover_selecionado else (122, 152, 206),
            border_hover=(255, 255, 255) if mover_selecionado else (224, 235, 255),
        )
        self._botao_mover.render(tela, eventos or [], dt, None)
        if self._botao_mover.clicado:
            self._ataque_selecionado = None
        icone_mover = self._icone_diverso('Mover', acao_lado - 8)
        if icone_mover is not None:
            tela.blit(icone_mover, icone_mover.get_rect(center=self._botao_mover.rect.center))
        if self._botao_mover.rect.collidepoint(self._mouse_pos):
            self._registrar_hover_acao('Mover', 'Reposiciona o pokémon no campo de batalha.')

        self._botao_trocar.base_rect = pygame.Rect(area_acoes.x, area_acoes.bottom - acao_lado - 2, acao_lado, acao_lado)
        self._botao_trocar.rect = pygame.Rect(self._botao_trocar.base_rect)
        self._botao_trocar.render(tela, eventos or [], dt, None)
        icone_trocar = self._icone_diverso('Trocar', acao_lado - 8)
        if icone_trocar is not None:
            tela.blit(icone_trocar, icone_trocar.get_rect(center=self._botao_trocar.rect.center))
        if self._botao_trocar.rect.collidepoint(self._mouse_pos):
            self._registrar_hover_acao('Trocar', 'Substitui o pokémon atual por outro do time.')

    def _garantir_barras(self):
        if self._barra_vida is None:
            self._barra_vida = Barra((0, 0, 1, 1), texto='', valor=0, minimo=0, maximo=1, mostrar_rotulo=False, suavizacao=22.0)
        if self._barra_energia is None:
            self._barra_energia = Barra((0, 0, 1, 1), texto='', valor=0, minimo=0, maximo=1, mostrar_rotulo=False, suavizacao=22.0)

    def _desenhar_item_slot(self, tela: pygame.Surface, rect: pygame.Rect, item):
        pygame.draw.rect(tela, (18, 26, 40), rect, border_radius=8)
        pygame.draw.rect(tela, (108, 136, 188), rect, width=2, border_radius=8)
        if hasattr(ItemInventario, 'desenhar_item_no_rect'):
            try:
                ItemInventario.desenhar_item_no_rect(tela, item, rect.inflate(-6, -6))
                return
            except Exception:
                pass
        try:
            icone = ItemInventario.surface_item(item, lado_px=min(rect.width, rect.height) - 6)
        except Exception:
            icone = None
        if icone is not None:
            tela.blit(icone, icone.get_rect(center=rect.center))

    def _desenhar_barras_e_itens(self, tela: pygame.Surface, area: pygame.Rect, pokemon, dt: float):
        self._garantir_barras()

        itens = list(getattr(pokemon, 'obter_itens_ficha', lambda limite=None: getattr(pokemon, 'ItensBuild', []))(3) or [])[:3]
        padding = 12
        gap_setor = 10
        area_interna = area.inflate(-padding * 2, -padding * 2)

        coluna_itens_w = 0
        if itens:
            coluna_itens_w = max(38, min(52, int(area_interna.height * 0.42)))
        area_barras = pygame.Rect(area_interna.x, area_interna.y, area_interna.width - coluna_itens_w - (gap_setor if itens else 0), area_interna.height)
        area_itens = pygame.Rect(area_barras.right + (gap_setor if itens else 0), area_interna.y, coluna_itens_w, area_interna.height)

        barra_h = max(13, min(18, int(area_barras.height * 0.24)))
        gap_barras = max(8, int(area_barras.height * 0.12))
        y0 = area_barras.y + max(2, (area_barras.height - (barra_h * 2 + gap_barras)) // 2)

        self._barra_vida.configurar(
            rect=pygame.Rect(area_barras.x, y0, area_barras.width, barra_h),
            minimo=0.0,
            maximo=max(1.0, float(getattr(pokemon, 'VidaMax', 1.0))),
            cor_fundo=(18, 25, 34),
            cor_borda=(234, 242, 255),
            cor_preenchimento=(62, 205, 82),
            vertical=False,
            border_radius=max(6, barra_h // 2),
        )
        self._barra_vida.set_valor(float(getattr(pokemon, 'VidaAtual', 0.0)), animar=True)
        self._barra_vida.render(tela, [], dt)
        self._desenhar_texto(
            self._txt_barra,
            tela,
            f"{int(round(float(getattr(pokemon, 'VidaAtual', 0.0))))}/{int(round(float(getattr(pokemon, 'VidaMax', 0.0))))}",
            (self._barra_vida.rect.right - 6, self._barra_vida.rect.centery),
            align='midright',
        )

        self._barra_energia.configurar(
            rect=pygame.Rect(area_barras.x, y0 + barra_h + gap_barras, area_barras.width, barra_h),
            minimo=0.0,
            maximo=max(1.0, float(getattr(pokemon, 'EnergiaMax', 1.0))),
            cor_fundo=(18, 25, 34),
            cor_borda=(234, 242, 255),
            cor_preenchimento=(74, 148, 255),
            vertical=False,
            border_radius=max(6, barra_h // 2),
        )
        self._barra_energia.set_valor(float(getattr(pokemon, 'Energia', 0.0)), animar=True)
        self._barra_energia.render(tela, [], dt)
        self._desenhar_texto(
            self._txt_barra,
            tela,
            f"{int(round(float(getattr(pokemon, 'Energia', 0.0))))}/{int(round(float(getattr(pokemon, 'EnergiaMax', 0.0))))}",
            (self._barra_energia.rect.right - 6, self._barra_energia.rect.centery),
            align='midright',
        )

        if not itens:
            return

        lado = max(30, min(area_itens.width, int((area_itens.height - 8) / max(1, len(itens)) - 4)))
        gap = 6 if len(itens) >= 3 else 10 if len(itens) == 2 else 0
        total_h = len(itens) * lado + max(0, len(itens) - 1) * gap
        y = area_itens.y + max(0, (area_itens.height - total_h) // 2)
        x = area_itens.x + max(0, (area_itens.width - lado) // 2)
        for item in itens:
            self._desenhar_item_slot(tela, pygame.Rect(x, y, lado, lado), item)
            y += lado + gap

    def _desenhar_tipos(self, tela: pygame.Surface, area: pygame.Rect, tipos: list[str]):
        if not tipos:
            return
        lado = max(20, min(28, area.height))
        gap = 8
        total_w = len(tipos) * lado + max(0, len(tipos) - 1) * gap
        x = area.centerx - total_w // 2
        for tipo in tipos:
            base = pygame.Rect(x, area.y + (area.height - lado) // 2, lado, lado)
            pygame.draw.circle(tela, (245, 248, 255), base.center, lado // 2)
            icone = None
            try:
                icone = PokemonInventario.icone_tipo(tipo, lado - 2)
            except Exception:
                icone = None
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=base.center))
            else:
                self._desenhar_texto(self._txt_micro, tela, str(tipo)[:2].upper(), base.center, align='center')
            x = base.right + gap

    def _desenhar_direita(self, tela: pygame.Surface, area: pygame.Rect, pokemon):
        self._desenhar_setor(tela, area)
        self._desenhar_texto(self._txt_titulo, tela, str(getattr(pokemon, 'Nome', 'Pokémon')), (area.centerx, area.y + 22), align='center')
        tipos = list(getattr(pokemon, 'Tipos', []) or [])
        self._desenhar_tipos(tela, pygame.Rect(area.x + 8, area.y + 34, area.width - 16, 30), tipos)

        lado_img = max(66, min(100, int(area.height * 0.50)))
        img = None
        try:
            img = PokemonInventario.surface_pokemon(getattr(pokemon, 'Dados', {}), lado_img)
        except Exception:
            img = None
        if img is not None:
            tela.blit(img, img.get_rect(center=(area.centerx, area.centery + 2)))

        self._desenhar_texto(self._txt_sub, tela, f"Lv {int(getattr(pokemon, 'Nivel', 1))}", (area.centerx, area.bottom - 26), align='center')

    def render(self, tela: pygame.Surface, pokemon, t_visivel: float, eventos, dt: float):
        if pokemon is None:
            return

        self._garantir_layout(tela)
        self._atualizar_animacoes(dt)
        self._atualizar_estilo_botao_extra()
        self._mouse_pos = pygame.mouse.get_pos()
        self._hover_atributo = None
        self._hover_ataque = None
        self._hover_acao = None

        t = max(0.0, min(1.0, t_visivel))
        offset = int((1.0 - t) * (self.rect.height + 32))
        rect = self.rect.move(0, offset)

        gap_setores = 10
        extra_max = max(150, int(rect.width * 0.16))
        extra_w = int(round(extra_max * self._t_extra))

        side_w = max(156, int(rect.width * 0.17))
        direita_w = side_w
        esquerda_w = side_w
        meio_w = rect.width - esquerda_w - direita_w - gap_setores * 2

        area_extra = pygame.Rect(rect.x - extra_w - gap_setores, rect.y, extra_w, rect.height)
        area_esq = pygame.Rect(rect.x, rect.y, esquerda_w, rect.height)
        area_meio = pygame.Rect(area_esq.right + gap_setores, rect.y, meio_w, rect.height)
        area_dir = pygame.Rect(area_meio.right + gap_setores, rect.y, direita_w, rect.height)

        if extra_w > 0:
            self._desenhar_extra_esquerda(tela, area_extra, pokemon)

        self._desenhar_fundo(tela, rect)
        self._desenhar_setor(tela, area_meio)

        topo_h = rect.height // 2
        area_meio_topo = pygame.Rect(area_meio.x, area_meio.y, area_meio.width, topo_h)
        area_meio_baixo = pygame.Rect(area_meio.x, area_meio.y + topo_h, area_meio.width, rect.height - topo_h)

        self._desenhar_stats_esquerda(tela, area_esq, pokemon)
        self._desenhar_ataques(tela, area_meio_topo, pokemon, eventos, dt)
        self._desenhar_barras_e_itens(tela, area_meio_baixo, pokemon, dt)
        self._desenhar_direita(tela, area_dir, pokemon)
        self._desenhar_botao_extra(tela, area_esq, area_extra, eventos, dt)
        self._renderizar_tooltips(tela)

    def ataque_selecionado(self):
        return self._ataque_selecionado

    def contem_ponto(self, pos) -> bool:
        if not isinstance(pos, (tuple, list)) or len(pos) < 2:
            return False
        if self.rect.width <= 0 or self.rect.height <= 0:
            return False
        ponto = (int(pos[0]), int(pos[1]))
        if self.rect.collidepoint(ponto):
            return True
        extra_max = max(150, int(self.rect.width * 0.16))
        extra_w = int(round(extra_max * self._t_extra))
        if extra_w <= 0:
            return False
        gap_setores = 10
        area_extra = pygame.Rect(self.rect.x - extra_w - gap_setores, self.rect.y, extra_w, self.rect.height)
        return area_extra.collidepoint(ponto)

    def atualizar_previsao(self, custo: float, pode: bool) -> None:
        self._previsao_consumo = float(custo)
        self._previsao_pode = bool(pode)
