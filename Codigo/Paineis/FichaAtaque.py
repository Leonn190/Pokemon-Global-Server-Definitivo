from __future__ import annotations

import unicodedata
from pathlib import Path

import pygame

from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto, TextoAtaque

class FichaAtaque:
    _cache_superficies: dict[tuple[str, tuple[int, int], str], pygame.Surface] = {}
    _cache_listagem: dict[str, dict[str, Path]] = {}

    _cores_tipo = {
        'normal': (166, 168, 181),
        'fogo': (239, 120, 74),
        'agua': (89, 159, 255),
        'elétrico': (239, 202, 74),
        'eletrico': (239, 202, 74),
        'grama': (93, 188, 106),
        'planta': (93, 188, 106),
        'gelo': (109, 210, 214),
        'lutador': (205, 96, 78),
        'lutadora': (205, 96, 78),
        'veneno': (174, 97, 196),
        'terra': (212, 181, 96),
        'voador': (134, 162, 245),
        'psiquico': (247, 116, 164),
        'psíquico': (247, 116, 164),
        'inseto': (150, 189, 77),
        'pedra': (190, 163, 92),
        'fantasma': (118, 105, 188),
        'dragao': (96, 120, 236),
        'dragão': (96, 120, 236),
        'sombrio': (116, 104, 92),
        'noturno': (116, 104, 92),
        'aco': (118, 142, 158),
        'aço': (118, 142, 158),
        'fada': (225, 133, 199),
        'cosmico': (108, 110, 210),
        'cósmico': (108, 110, 210),
        'vento': (112, 206, 196),
        'luz': (255, 230, 130),
        'trevas': (108, 95, 118),
    }
    _alias_fundo_tipo = {
        'terra': 'Terrestre',
        'terrestre': 'Terrestre',
        'veneno': 'Venenoso',
        'venenoso': 'Venenoso',
        'aço': 'Metal',
        'aco': 'Metal',
        'metal': 'Metal',
        'eletrico': 'Eletrico',
        'elétrico': 'Eletrico',
        'psiquico': 'Psiquico',
        'psíquico': 'Psiquico',
        'sombrio': 'Sombrio',
    }

    def __init__(self):
        self._painel: Painel | None = None
        self._rect_cache: tuple[int, int, int, int] | None = None

        base = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20),
            'shadow': False,
        }
        self.TxtNome = Texto('', style={**base, 'size': 22, 'color': (248, 251, 255)})
        self.TxtEstilo = Texto('', style={**base, 'size': 14, 'color': (242, 246, 255), 'align': 'center'})
        self.TxtCusto = Texto('', style={**base, 'size': 14, 'color': (255, 244, 211), 'align': 'center'})
        self.TxtDescricao = TextoAtaque(
            rect=(0, 0, 10, 10),
            texto='',
            linhas=4,
            caracteres_por_linha=62,
            style={**base, 'size': 15, 'color': (203, 214, 238)},
        )
        self.TxtVazio = Texto('Passe o mouse em um ataque.', style={**base, 'size': 16, 'color': (180, 194, 225)})

    @staticmethod
    def _normalizar(texto) -> str:
        base = ''.join(
            c for c in unicodedata.normalize('NFKD', str(texto or '').strip().lower())
            if not unicodedata.combining(c)
        )
        for ch in ('_', '-', '.', "'", '(', ')', '[', ']', '{', '}', ':', ';', ',', '/', '\\'):
            base = base.replace(ch, ' ')
        return ' '.join(base.split())

    @classmethod
    def _roots(cls) -> list[Path]:
        atual = Path(__file__).resolve()
        candidatos = [Path('.').resolve(), atual.parent]
        candidatos.extend(atual.parents[:6])
        vistos = []
        for caminho in candidatos:
            if caminho not in vistos:
                vistos.append(caminho)
        return vistos

    @classmethod
    def _pastas_existentes(cls, subcaminho: Path) -> list[Path]:
        pastas = []
        for raiz in cls._roots():
            pasta = raiz / subcaminho
            if pasta.exists() and pasta.is_dir():
                pastas.append(pasta)
        return pastas

    @classmethod
    def _listar_arquivos(cls, pasta: Path) -> dict[str, Path]:
        chave = str(pasta.resolve())
        if chave in cls._cache_listagem:
            return cls._cache_listagem[chave]

        mapa: dict[str, Path] = {}
        try:
            for arquivo in pasta.iterdir():
                if not arquivo.is_file():
                    continue
                mapa.setdefault(cls._normalizar(arquivo.stem), arquivo)
        except OSError:
            pass

        cls._cache_listagem[chave] = mapa
        return mapa

    @classmethod
    def _achar_arquivo(cls, subcaminho: Path, *nomes) -> Path | None:
        candidatos = [cls._normalizar(nome) for nome in nomes if str(nome or '').strip()]
        if not candidatos:
            return None

        for pasta in cls._pastas_existentes(subcaminho):
            mapa = cls._listar_arquivos(pasta)
            for nome in candidatos:
                if nome in mapa:
                    return mapa[nome]
            for nome in candidatos:
                for chave, arquivo in mapa.items():
                    if chave == nome or chave.startswith(nome) or nome in chave:
                        return arquivo
        return None

    @classmethod
    def _carregar_surface(cls, arquivo: Path | None, tamanho: tuple[int, int], chave_extra='contain') -> pygame.Surface | None:
        if arquivo is None:
            return None
        chave = (str(arquivo), tuple(map(int, tamanho)), str(chave_extra))
        if chave in cls._cache_superficies:
            return cls._cache_superficies[chave]
        try:
            imagem = pygame.image.load(str(arquivo)).convert_alpha()
        except Exception:
            return None

        if chave_extra == 'fill':
            surface = pygame.transform.smoothscale(imagem, (max(1, int(tamanho[0])), max(1, int(tamanho[1]))))
        else:
            iw, ih = imagem.get_size()
            tw, th = max(1, int(tamanho[0])), max(1, int(tamanho[1]))
            escala = min(tw / max(1, iw), th / max(1, ih))
            nw, nh = max(1, int(iw * escala)), max(1, int(ih * escala))
            surface = pygame.transform.smoothscale(imagem, (nw, nh))
        cls._cache_superficies[chave] = surface
        return surface

    @classmethod
    def _cor_tipo(cls, tipo: str) -> tuple[int, int, int]:
        return cls._cores_tipo.get(cls._normalizar(tipo), (88, 126, 196))

    @classmethod
    def _descricao_ataque(cls, ataque: dict | None) -> str:
        if not isinstance(ataque, dict):
            return ''

        nivel = None
        for chave in ('Nivel', 'Nível', 'nivel', 'nível', 'NivelAtual', 'NívelAtual', 'nivel_atual'):
            try:
                valor = int(ataque.get(chave))
                nivel = max(1, valor)
                break
            except (TypeError, ValueError):
                continue

        if nivel is not None:
            for chave in (f'Descrição Nivel {nivel}', f'Descricao Nivel {nivel}', f'Descrição Nível {nivel}', f'Descricao Nível {nivel}'):
                texto = str(ataque.get(chave) or '').strip()
                if texto:
                    return texto

        for chave in (
            'Descrição', 'Descricao', 'descrição', 'descricao',
            'Descrição Nivel 1', 'Descricao Nivel 1', 'Descrição Nível 1', 'Descricao Nível 1',
            'Efeito', 'Texto', 'Resumo',
        ):
            texto = str(ataque.get(chave) or '').strip()
            if texto:
                return texto
        return 'Sem descrição cadastrada.'

    @staticmethod
    def _quebrar_linhas(medidor: Texto, texto: str, largura: int, max_linhas: int = 6) -> list[str]:
        palavras = str(texto or '').split()
        if not palavras:
            return []
        linhas: list[str] = []
        atual = ''
        for palavra in palavras:
            teste = palavra if not atual else f'{atual} {palavra}'
            medidor.set_text(teste)
            medidor.set_pos((0, 0))
            if medidor.get_rect().width <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
                if len(linhas) >= max_linhas - 1:
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
                medidor.set_text(atual.rstrip() + '...')
                medidor.set_pos((0, 0))
            if restante:
                atual = atual.rstrip() + '...'
            linhas.append(atual)
        return linhas[:max_linhas]

    def _garantir_painel(self, rect):
        rect = pygame.Rect(rect)
        chave = (rect.x, rect.y, rect.width, rect.height)
        if self._painel is not None and self._rect_cache == chave:
            return
        self._rect_cache = chave
        self._painel = Painel(rect, cor_fundo=(13, 18, 31, 244), cor_borda=(78, 104, 160), borda=2, raio=16)

    def _fundo_tipo(self, tipo: str, tamanho: tuple[int, int]) -> pygame.Surface | None:
        tipo_limpo = str(tipo or '').strip()
        tipo_norm = self._normalizar(tipo_limpo)
        base_nome = ''.join(ch for ch in tipo_limpo.title() if ch.isalnum())
        tipo_norm_title = ''.join(ch for ch in tipo_norm.title() if ch.isalnum())
        alias = self._alias_fundo_tipo.get(tipo_norm, tipo_norm_title or base_nome or 'Normal')
        arquivo = self._achar_arquivo(
            Path('Recursos') / 'Visual' / 'Fundos' / 'Ataques',
            tipo_limpo,
            f'Fundo{tipo_limpo}',
            tipo_norm,
            f'Fundo{tipo_norm}',
            tipo_norm_title,
            f'Fundo{tipo_norm_title}',
            base_nome,
            f'Fundo{base_nome}',
            alias,
            f'Fundo{alias}',
        )
        return self._carregar_surface(arquivo, tamanho, chave_extra='fill')

    def _retangulo_tooltip(self, tela: pygame.Surface, area_ancora=None, mouse_pos=None, largura=368, altura=196) -> pygame.Rect:
        tela_rect = tela.get_rect()
        if area_ancora is not None:
            area_ancora = pygame.Rect(area_ancora)
            x = area_ancora.centerx - largura // 2
            y = area_ancora.y - altura - 14
            if y < tela_rect.top + 8:
                y = area_ancora.bottom + 14
        else:
            if mouse_pos is None:
                mouse_pos = pygame.mouse.get_pos()
            x = mouse_pos[0] + 18
            y = mouse_pos[1] - altura // 2

        x = max(tela_rect.left + 8, min(int(x), tela_rect.right - largura - 8))
        y = max(tela_rect.top + 8, min(int(y), tela_rect.bottom - altura - 8))
        return pygame.Rect(x, y, largura, altura)

    @staticmethod
    def _retangulo_sobre_status(area_ancora) -> pygame.Rect:
        area = pygame.Rect(area_ancora)
        largura = min(area.width - 16, max(332, int(area.width * 0.9)))
        altura = min(178, max(154, int(area.height * 0.48)))
        x = area.centerx - largura // 2
        y = max(area.y + 94, area.bottom - altura - 8)
        return pygame.Rect(x, y, largura, altura)

    def renderizar_tooltip(self, tela: pygame.Surface, ataque: dict | None, area_ancora=None, mouse_pos=None, atributos: dict | None = None):
        if ataque is None:
            return
        rect = self._retangulo_tooltip(tela, area_ancora=area_ancora, mouse_pos=mouse_pos)
        self.renderizar(tela, rect, ataque, atributos=atributos)

    def renderizar(self, tela: pygame.Surface, rect, ataque: dict | None, atributos: dict | None = None):
        rect = pygame.Rect(rect)
        self._garantir_painel(rect)
        assert self._painel is not None
        self._painel.rect = rect
        self._painel.render(tela, [], 0)

        if ataque is None:
            self.TxtVazio.set_pos((rect.x + 16, rect.y + 14))
            self.TxtVazio.draw(tela)
            return

        nome = str(ataque.get('Ataque') or ataque.get('Nome') or ataque.get('nome') or 'Ataque').strip()
        tipo = str(ataque.get('Tipo') or ataque.get('tipo') or 'Normal').strip() or 'Normal'
        estilo = str(ataque.get('Estilo') or ataque.get('estilo') or '-').strip() or '-'
        custo = str(ataque.get('Custo') or ataque.get('custo') or '0').strip() or '0'
        descricao = self._descricao_ataque(ataque)

        header = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, 58)
        fundo = self._fundo_tipo(tipo, header.size)
        if fundo is not None:
            sombra = pygame.Surface(header.size, pygame.SRCALPHA)
            sombra.fill((255, 255, 255, 0))
            sombra.blit(fundo, fundo.get_rect(center=sombra.get_rect().center))
            pygame.draw.rect(sombra, (255, 255, 255, 26), sombra.get_rect(), border_radius=12)
            tela.blit(sombra, header.topleft)
        else:
            pygame.draw.rect(tela, self._cor_tipo(tipo), header, border_radius=12)
        pygame.draw.rect(tela, (235, 241, 255), header, 2, border_radius=12)

        self.TxtNome.set_text(nome)
        self.TxtNome.set_pos((header.x + 14, header.y + 10))
        self.TxtNome.draw(tela)

        pill_h = 22
        pill_custo = pygame.Rect(header.right - 78, header.y + 10, 64, pill_h)
        pill_estilo = pygame.Rect(header.right - 164, header.y + 10, 78, pill_h)

        pygame.draw.rect(tela, (30, 39, 63), pill_estilo, border_radius=10)
        pygame.draw.rect(tela, (244, 248, 255), pill_estilo, 1, border_radius=10)
        pygame.draw.rect(tela, (76, 56, 18), pill_custo, border_radius=10)
        pygame.draw.rect(tela, (255, 235, 185), pill_custo, 1, border_radius=10)

        self.TxtEstilo.set_text(estilo)
        self.TxtEstilo.set_pos(pill_estilo.center)
        self.TxtEstilo.draw(tela)
        self.TxtCusto.set_text(f'Custo {custo}')
        self.TxtCusto.set_pos(pill_custo.center)
        self.TxtCusto.draw(tela)

        area_desc = pygame.Rect(rect.x + 16, header.bottom + 10, rect.width - 32, rect.bottom - header.bottom - 16)
        self.TxtDescricao.configurar_rect(area_desc)
        self.TxtDescricao.set_limites(linhas=4, caracteres_por_linha=66)
        self.TxtDescricao.set_atributos(atributos or {})
        self.TxtDescricao.set_texto(descricao)
        self.TxtDescricao.draw(tela)
