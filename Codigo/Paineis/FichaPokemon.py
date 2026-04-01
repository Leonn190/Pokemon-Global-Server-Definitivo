from __future__ import annotations

import math
import unicodedata
from pathlib import Path

import pygame


from Codigo.Prefabs.Arrastavel import Arrastavel
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto
from Codigo.Paineis.FichaAtaque import FichaAtaque

class FichaPokemon:
    _cache_superficies: dict[tuple[str, tuple[int, int], str], pygame.Surface] = {}
    _cache_listagem: dict[str, dict[str, Path]] = {}
    _cache_frames: dict[str, list[pygame.Surface]] = {}
    _cache_frames_escalados: dict[tuple[str, int], list[pygame.Surface]] = {}
    _INTERVALO_FRAME_ANIM_MS = 85

    _ordem_status = ('Vida', 'Atk', 'Def', 'SpA', 'SpD', 'Vel', 'Mag', 'Per', 'Ene', 'EnR')
    _cores_status = {
        'Vida': (108, 201, 123),
        'Atk': (235, 109, 94),
        'Def': (227, 192, 92),
        'SpA': (119, 169, 255),
        'SpD': (154, 133, 255),
        'Vel': (255, 174, 82),
        'Mag': (103, 207, 215),
        'Per': (194, 128, 221),
        'Ene': (242, 216, 96),
        'EnR': (120, 210, 175),
    }
    _nomes_status = {
        'Vida': 'Vida',
        'Atk': 'Atk',
        'Def': 'Def',
        'SpA': 'SpA',
        'SpD': 'SpD',
        'Vel': 'Vel',
        'Mag': 'Mag',
        'Per': 'Per',
        'Ene': 'Ene',
        'EnR': 'EnR',
    }
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

    def __init__(self):
        self._painel: Painel | None = None
        self._rect_cache: tuple[int, int, int, int] | None = None
        self._barra_xp: Barra | None = None
        self._botao_fechar: Botao | None = None
        self._ficha_ataque = FichaAtaque()
        self._arrastavel_ataque = Arrastavel()
        self._slot_hover: tuple[str, int] | None = None
        self._slot_origem_oculto: tuple[str, int] | None = None
        self._slots_ataque: dict[tuple[str, int], pygame.Rect] = {}
        self._slots_build: list[pygame.Rect] = []
        self._ultimo_pokemon_id = None
        self.FecharSolicitado = False

        base = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20),
            'shadow': False,
        }
        self.TxtTitulo = Texto('', style={**base, 'size': 25, 'color': (245, 249, 255)})
        self.TxtSubtitulo = Texto('', style={**base, 'size': 16, 'color': (176, 190, 224)})
        self.TxtNivel = Texto('', style={**base, 'size': 18, 'color': (245, 249, 255)})
        self.TxtXP = Texto('', style={**base, 'size': 15, 'color': (186, 202, 236)})
        self.TxtInfo = Texto('', style={**base, 'size': 15, 'color': (196, 208, 232)})
        self.TxtSetor = Texto('', style={**base, 'size': 18, 'color': (238, 244, 255)})
        self.TxtMini = Texto('', style={**base, 'size': 14, 'color': (176, 190, 221)})
        self.TxtSlot = Texto('+', style={**base, 'size': 28, 'color': (206, 216, 240), 'align': 'center'})
        self.TxtStatus = Texto('', style={**base, 'size': 14, 'color': (245, 249, 255)})
        self.TxtIV = Texto('', style={**base, 'size': 12, 'color': (169, 186, 222)})
        self.TxtResumo = Texto('', style={**base, 'size': 18, 'color': (244, 248, 255)})
        self.TxtVazio = Texto('Selecione um pokémon para abrir a ficha.', style={**base, 'size': 18, 'color': (180, 194, 225)})

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
    def _ler_valor_por_chaves(cls, dados: dict | None, *chaves, default=None):
        if not isinstance(dados, dict):
            return default
        candidatos = [cls._normalizar(ch) for ch in chaves if str(ch or '').strip()]
        if not candidatos:
            return default
        for chave, valor in dados.items():
            if cls._normalizar(chave) in candidatos and valor not in (None, ''):
                return valor
        return default

    @classmethod
    def _coletar_fontes(cls, pokemon: dict | None) -> list[dict]:
        fontes = []
        if isinstance(pokemon, dict):
            fontes.append(pokemon)
            for chave in ('Info', 'info', 'Estado', 'estado', 'Snapshot', 'snapshot'):
                valor = pokemon.get(chave)
                if isinstance(valor, dict):
                    fontes.append(valor)
                    for sub in ('stats', 'Stats', 'Status', 'Atributos'):
                        if isinstance(valor.get(sub), dict):
                            fontes.append(valor[sub])
            for chave in ('stats', 'Stats', 'Status', 'Atributos'):
                valor = pokemon.get(chave)
                if isinstance(valor, dict):
                    fontes.append(valor)
            for chave in ('IVs', 'ivs', 'SubIVs', 'subivs'):
                valor = pokemon.get(chave)
                if isinstance(valor, dict):
                    fontes.append(valor)
        return fontes

    @classmethod
    def _valor_pokemon(cls, pokemon: dict | None, *chaves, default=None):
        for fonte in cls._coletar_fontes(pokemon):
            valor = cls._ler_valor_por_chaves(fonte, *chaves, default=None)
            if valor not in (None, ''):
                return valor
        return default

    @classmethod
    def _stats_dict(cls, pokemon: dict | None) -> dict[str, float]:
        stats: dict[str, float] = {}
        for fonte in cls._coletar_fontes(pokemon):
            for status in cls._ordem_status + ('CrC', 'CrD'):
                valor = cls._ler_valor_por_chaves(fonte, status, status.lower(), default=None)
                if valor in (None, ''):
                    continue
                try:
                    stats[status] = float(valor)
                except (TypeError, ValueError):
                    pass
        return stats

    @classmethod
    def _ivs_dict(cls, pokemon: dict | None) -> dict[str, float]:
        ivs: dict[str, float] = {}
        if not isinstance(pokemon, dict):
            return ivs
        fontes = []
        for chave in ('SubIVs', 'subivs', 'IVs', 'ivs'):
            valor = pokemon.get(chave)
            if isinstance(valor, dict):
                fontes.append(valor)
        for fonte in fontes:
            for status in cls._ordem_status:
                valor = cls._ler_valor_por_chaves(fonte, status, status.lower(), default=None)
                if valor in (None, ''):
                    continue
                try:
                    ivs[status] = float(valor)
                except (TypeError, ValueError):
                    pass
        for status in cls._ordem_status:
            for chave in (f'IV{status}', f'{status}IV', f'SubIV{status}', f'{status}SubIV'):
                valor = cls._valor_pokemon(pokemon, chave, default=None)
                if valor in (None, ''):
                    continue
                try:
                    ivs.setdefault(status, float(valor))
                except (TypeError, ValueError):
                    pass
        return ivs

    @classmethod
    def _formatar_numero(cls, valor, casas=0, sufixo='') -> str:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return '-'
        if casas <= 0:
            return f'{int(round(numero))}{sufixo}'
        return f'{numero:.{casas}f}{sufixo}'

    @classmethod
    def _formatar_percentual(cls, valor) -> str:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return '-'
        if 0.0 <= numero <= 1.0:
            numero *= 100.0
        return f'{int(round(numero))}%'

    @classmethod
    def _tipos(cls, pokemon: dict | None) -> list[str]:
        bruto = cls._valor_pokemon(pokemon, 'Tipos', 'Tipo', 'tipos', 'tipo', 'Tipagem', default=None)
        if bruto is None:
            return []
        if isinstance(bruto, (list, tuple)):
            valores = [str(v).strip() for v in bruto if str(v or '').strip()]
        else:
            texto = str(bruto)
            separadores = ['/', ',', ';', '|']
            for sep in separadores:
                texto = texto.replace(sep, ',')
            valores = [parte.strip() for parte in texto.split(',') if parte.strip()]
        unicos = []
        for tipo in valores:
            if tipo not in unicos:
                unicos.append(tipo)
        return unicos[:3]

    @classmethod
    def _lista_ref(cls, pokemon: dict | None, chaves: tuple[str, ...], padrao: str) -> list:
        if not isinstance(pokemon, dict):
            return []
        normalizadas = [cls._normalizar(ch) for ch in chaves]
        for chave, valor in pokemon.items():
            if cls._normalizar(chave) in normalizadas and isinstance(valor, list):
                return valor
        pokemon.setdefault(padrao, [])
        if not isinstance(pokemon[padrao], list):
            pokemon[padrao] = []
        return pokemon[padrao]

    @classmethod
    def _habilidades_ref(cls, pokemon: dict | None) -> list:
        return cls._lista_ref(pokemon, ('Habilidades', 'Ataques', 'Ativos', 'Moves', 'Golpes'), 'Habilidades')

    @classmethod
    def _memoria_ref(cls, pokemon: dict | None) -> list:
        return cls._lista_ref(pokemon, ('Memoria', 'Memória', 'Memorias', 'Memórias', 'Reserva', 'BancoHabilidades'), 'Memoria')

    @classmethod
    def _equipaveis(cls, pokemon: dict | None) -> int:
        valor = cls._valor_pokemon(pokemon, 'Equipaveis', 'Equipáveis', 'Equipamentos', 'SlotsEquipaveis', 'SlotsEquipáveis', default=1)
        try:
            return max(1, min(4, int(valor)))
        except (TypeError, ValueError):
            return 1

    @classmethod
    def _nivel(cls, pokemon: dict | None) -> int:
        valor = cls._valor_pokemon(pokemon, 'Nivel', 'Nível', 'nivel', 'nível', default=0)
        try:
            return max(0, int(valor))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _xp(cls, pokemon: dict | None) -> tuple[int, int]:
        atual = cls._valor_pokemon(pokemon, 'XP', 'xp', default=0)
        alvo = cls._valor_pokemon(pokemon, 'XPAlvo', 'XpAlvo', 'xp_alvo', 'PróximoXP', 'ProximoXP', default=100)
        try:
            atual_i = max(0, int(float(atual)))
        except (TypeError, ValueError):
            atual_i = 0
        try:
            alvo_i = max(1, int(float(alvo)))
        except (TypeError, ValueError):
            alvo_i = 1
        return atual_i, alvo_i

    @classmethod
    def _altura(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Altura', 'altura', default=None)

    @classmethod
    def _peso(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Peso', 'peso', default=None)

    @classmethod
    def _amizade(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Amizade', 'amizade', 'Friendship', default=None)

    @classmethod
    def _grupo(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Grupo', 'grupo', 'GrupoOvo', 'EggGroup', default='-')

    @classmethod
    def _criticos(cls, pokemon: dict | None) -> tuple[str, str]:
        stats = cls._stats_dict(pokemon)
        crc = stats.get('CrC', cls._valor_pokemon(pokemon, 'CrC', 'CriticoChance', 'ChanceCritico', default=None))
        crd = stats.get('CrD', cls._valor_pokemon(pokemon, 'CrD', 'DanoCritico', 'CriticoDano', default=None))
        return cls._formatar_percentual(crc), cls._formatar_percentual(crd)

    @classmethod
    def _nome_especie(cls, pokemon: dict | None) -> tuple[str, str]:
        nome = str(cls._valor_pokemon(pokemon, 'Nome', 'nome', default='Pokémon')).strip() or 'Pokémon'
        especie = str(cls._valor_pokemon(pokemon, 'Especie', 'Espécie', 'especie', 'espécie', default=nome)).strip() or nome
        return nome, especie

    @classmethod
    def _poder_total(cls, pokemon: dict | None) -> int:
        bruto = cls._valor_pokemon(pokemon, 'Poder', 'power', 'Power', 'Total', 'total', default=None)
        try:
            if bruto is not None:
                return max(0, int(round(float(bruto))))
        except (TypeError, ValueError):
            pass
        return int(round(sum(cls._stats_dict(pokemon).get(status, 0.0) for status in cls._ordem_status)))

    @classmethod
    def _iv_medio(cls, pokemon: dict | None) -> int:
        ivs = cls._ivs_dict(pokemon)
        if not ivs:
            bruto = cls._valor_pokemon(pokemon, 'IV', 'Iv', 'iv', default=0)
            try:
                numero = float(bruto)
                if 0.0 <= numero <= 1.0:
                    numero *= 100.0
                return max(0, min(100, int(round(numero))))
            except (TypeError, ValueError):
                return 0
        valores = []
        for valor in ivs.values():
            numero = float(valor)
            if 0.0 <= numero <= 1.0:
                numero *= 100.0
            valores.append(numero)
        return max(0, min(100, int(round(sum(valores) / max(1, len(valores))))))

    @classmethod
    def _poder_relativo(cls, pokemon: dict | None) -> int:
        bruto = cls._valor_pokemon(pokemon, 'PoderRelativo', 'Poder Relativo', 'power_relative', 'power relativo', default=None)
        try:
            if bruto is not None:
                numero = float(bruto)
                if 0.0 <= numero <= 1.0:
                    numero *= 100.0
                return max(0, min(999, int(round(numero))))
        except (TypeError, ValueError):
            pass
        stats = cls._stats_dict(pokemon)
        if not stats:
            return 0
        media = sum(stats.get(status, 0.0) for status in cls._ordem_status) / float(len(cls._ordem_status))
        relativo = (media / 255.0) * 100.0
        return max(0, min(100, int(round(relativo))))

    @classmethod
    def _subiv_status(cls, pokemon: dict | None, status: str) -> float:
        ivs = cls._ivs_dict(pokemon)
        valor = ivs.get(status, 0.0)
        if 0.0 <= valor <= 1.0:
            valor *= 100.0
        return max(0.0, min(100.0, float(valor)))

    @classmethod
    def _valor_status(cls, pokemon: dict | None, status: str) -> float:
        return float(cls._stats_dict(pokemon).get(status, 0.0))

    @classmethod
    def _max_barra_status(cls, pokemon: dict | None, status: str) -> float:
        bruto = cls._valor_pokemon(pokemon, f'Max{status}', f'{status}Max', default=None)
        try:
            if bruto is not None:
                return max(1.0, float(bruto))
        except (TypeError, ValueError):
            pass
        valor = cls._valor_status(pokemon, status)
        referencia = max(100.0, valor * 1.18)
        passo = 25.0 if referencia <= 200 else 50.0
        return math.ceil(referencia / passo) * passo

    @classmethod
    def _carregar_frames_nome(cls, especie: str) -> list[pygame.Surface]:
        chave = cls._normalizar(especie)
        if not chave:
            return []
        if chave in cls._cache_frames:
            return cls._cache_frames[chave]

        frames: list[pygame.Surface] = []
        pastas = cls._pastas_existentes(Path('Recursos') / 'Visual' / 'Pokemons' / 'Animação')
        for pasta_base in pastas:
            subpastas = [p for p in pasta_base.iterdir() if p.is_dir()]
            alvo = None
            for pasta in subpastas:
                nome = cls._normalizar(pasta.name)
                if nome == chave or nome.startswith(chave) or chave in nome:
                    alvo = pasta
                    break
            if alvo is None:
                continue
            arquivos = sorted(
                [p for p in alvo.iterdir() if p.is_file() and p.suffix.lower() in ('.png', '.webp', '.jpg', '.jpeg')],
                key=lambda p: p.name
            )
            for arquivo in arquivos:
                try:
                    frames.append(pygame.image.load(str(arquivo)).convert_alpha())
                except Exception:
                    continue
            if frames:
                break

        cls._cache_frames[chave] = frames
        return frames

    @classmethod
    def _obter_frames_escalados(cls, especie: str, tamanho_px: int) -> list[pygame.Surface]:
        tamanho = max(8, int(tamanho_px))
        chave = (cls._normalizar(especie), tamanho)
        if chave in cls._cache_frames_escalados:
            return cls._cache_frames_escalados[chave]
        frames = cls._carregar_frames_nome(especie)
        escalados = []
        for frame in frames:
            w, h = frame.get_size()
            if w <= 0 or h <= 0:
                continue
            k = tamanho / max(w, h)
            escalados.append(pygame.transform.smoothscale(frame, (max(1, int(w * k)), max(1, int(h * k)))))
        cls._cache_frames_escalados[chave] = escalados
        return escalados

    def _desenhar_animacao_pokemon(self, tela: pygame.Surface, rect: pygame.Rect, especie: str):
        pygame.draw.rect(tela, (16, 24, 42), rect, border_radius=16)
        pygame.draw.rect(tela, (83, 114, 177), rect, 2, border_radius=16)
        centro = rect.center
        frames = self._obter_frames_escalados(especie, int(min(rect.width, rect.height) * 0.82))
        if frames:
            indice = int((pygame.time.get_ticks() / self._INTERVALO_FRAME_ANIM_MS) % len(frames))
            frame = frames[indice]
            tela.blit(frame, frame.get_rect(center=centro))
            return
        raio = max(12, int(min(rect.width, rect.height) * 0.22))
        pygame.draw.circle(tela, (84, 146, 244), centro, raio)
        pygame.draw.circle(tela, (25, 74, 164), centro, raio, 2)

    def _icone_tipo(self, tipo: str, lado: int) -> pygame.Surface | None:
        arquivo = self._achar_arquivo(Path('Recursos') / 'Visual' / 'Icones' / 'Tipos', tipo)
        return self._carregar_surface(arquivo, (lado, lado), chave_extra='contain')

    @classmethod
    def _pastas_tipo_ataque(cls, tipo: str) -> list[Path]:
        base_pastas = cls._pastas_existentes(Path('Recursos') / 'Visual' / 'Icones' / 'Ataques')
        alvo_norm = cls._normalizar(tipo)
        encontradas: list[Path] = []
        for base in base_pastas:
            try:
                for pasta in base.iterdir():
                    if not pasta.is_dir():
                        continue
                    nome = cls._normalizar(pasta.name)
                    if nome == alvo_norm or nome.startswith(alvo_norm) or alvo_norm in nome:
                        encontradas.append(pasta)
            except OSError:
                continue
        return encontradas

    @classmethod
    def _icone_ataque_path(cls, nome_ataque: str, tipo: str) -> Path | None:
        candidatos = [cls._normalizar(nome_ataque)]
        for pasta in cls._pastas_tipo_ataque(tipo):
            mapa = cls._listar_arquivos(pasta)
            for nome in candidatos:
                if nome in mapa:
                    return mapa[nome]
            for nome in candidatos:
                for chave, arquivo in mapa.items():
                    if chave == nome or chave.startswith(nome) or nome in chave:
                        return arquivo
        base_pastas = cls._pastas_existentes(Path('Recursos') / 'Visual' / 'Icones' / 'Ataques')
        for base in base_pastas:
            try:
                for pasta in base.iterdir():
                    if not pasta.is_dir():
                        continue
                    mapa = cls._listar_arquivos(pasta)
                    for nome in candidatos:
                        if nome in mapa:
                            return mapa[nome]
            except OSError:
                continue
        return None

    def _icone_ataque(self, ataque: dict | None, lado: int) -> pygame.Surface | None:
        if not isinstance(ataque, dict):
            return None
        nome = str(ataque.get('Ataque') or ataque.get('Nome') or ataque.get('nome') or '').strip()
        tipo = str(ataque.get('Tipo') or ataque.get('tipo') or 'Normal').strip() or 'Normal'
        arquivo = self._icone_ataque_path(nome, tipo)
        return self._carregar_surface(arquivo, (lado, lado), chave_extra='contain')

    def _garantir_layout(self, rect):
        rect = pygame.Rect(rect)
        chave = (rect.x, rect.y, rect.width, rect.height)
        if self._painel is not None and self._rect_cache == chave:
            return
        self._rect_cache = chave
        self._painel = Painel(rect, cor_fundo=(20, 26, 42, 238), cor_borda=(74, 98, 146), borda=2, raio=18)
        self._barra_xp = Barra(pygame.Rect(0, 0, 100, 18), texto='', valor=0, minimo=0, maximo=100, mostrar_rotulo=False, suavizacao=12.0)
        self._barra_xp.cor_fundo = (25, 30, 48)
        self._barra_xp.cor_preenchimento = (126, 86, 224)
        self._barra_xp.cor_borda = (214, 202, 255)

        def _fechar(_jogo, _botao):
            self.FecharSolicitado = True

        self._botao_fechar = Botao(
            pygame.Rect(rect.right - 44, rect.y + 12, 30, 30),
            'X',
            execute=_fechar,
            style={
                'radius': 12,
                'border_width': 2,
                'bg': (116, 54, 54),
                'bg_hover': (150, 68, 68),
                'bg_pressed': (90, 42, 42),
                'border': (242, 219, 219),
                'border_hover': (255, 245, 245),
                'hover_scale': 1.0,
                'press_scale': 0.98,
                'text_style': {'size': 18, 'outline_thickness': 1, 'shadow': False},
            },
        )

    @staticmethod
    def calcular_rect_ancorado(area_host) -> pygame.Rect:
        area = pygame.Rect(area_host)
        largura = min(max(440, int(area.width * 0.46)), 640)
        altura = area.height
        return pygame.Rect(area.x, area.y, largura, altura)

    def _setores(self, rect: pygame.Rect):
        margem = 14
        interno = rect.inflate(-margem * 2, -margem * 2)
        interno_topo = interno.y + 26
        interno = pygame.Rect(interno.x, interno_topo, interno.width, interno.bottom - interno_topo)

        left_w = max(180, int(interno.width * 0.28))
        gap = 12
        left = pygame.Rect(interno.x, interno.y, left_w, interno.height)
        right = pygame.Rect(left.right + gap, interno.y, interno.width - left_w - gap, interno.height)
        top_h = max(165, int(right.height * 0.43))
        right_top = pygame.Rect(right.x, right.y, right.width, top_h)
        right_bottom = pygame.Rect(right.x, right_top.bottom + gap, right.width, right.height - top_h - gap)
        return left, right_top, right_bottom

    def _draw_panel_bg(self, tela: pygame.Surface, rect: pygame.Rect):
        assert self._painel is not None
        self._painel.rect = rect
        self._painel.render(tela, [], 0)
        header = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, 44)
        pygame.draw.rect(tela, (18, 24, 39), header, border_radius=14)
        pygame.draw.rect(tela, (76, 104, 160), header, 1, border_radius=14)

    def _desenhar_tipos(self, tela: pygame.Surface, area: pygame.Rect, tipos: list[str]):
        lado = min(34, area.height - 4)
        gap = 8
        x = area.x
        for tipo in tipos:
            base_rect = pygame.Rect(x, area.y + (area.height - lado) // 2, lado, lado)
            pygame.draw.circle(tela, (245, 248, 255), base_rect.center, lado // 2)
            pygame.draw.circle(tela, self._cor_tipo(tipo), base_rect.center, lado // 2, 2)
            icone = self._icone_tipo(tipo, lado - 8)
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=base_rect.center))
            else:
                self.TxtMini.set_text(tipo[:2].upper())
                self.TxtMini.set_pos(base_rect.center)
                self.TxtMini.draw(tela)
            x = base_rect.right + gap

    def _bloco_infos_esquerda(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None):
        pygame.draw.rect(tela, (11, 17, 30), rect, border_radius=18)
        pygame.draw.rect(tela, (66, 90, 140), rect, 1, border_radius=18)

        nome, especie = self._nome_especie(pokemon)
        nivel = self._nivel(pokemon)
        xp_atual, xp_alvo = self._xp(pokemon)
        tipos = self._tipos(pokemon)
        altura = self._altura(pokemon)
        peso = self._peso(pokemon)
        amizade = self._amizade(pokemon)
        crit_chance, crit_dano = self._criticos(pokemon)
        grupo = self._grupo(pokemon)

        anim_rect = pygame.Rect(rect.x + 16, rect.y + 16, rect.width - 32, rect.width - 32)
        self._desenhar_animacao_pokemon(tela, anim_rect, especie)

        self.TxtNivel.set_text(f'Lv {nivel}')
        self.TxtNivel.set_pos((rect.x + 18, anim_rect.bottom + 14))
        self.TxtNivel.draw(tela)

        barra_rect = pygame.Rect(rect.x + 16, anim_rect.bottom + 44, rect.width - 32, 16)
        assert self._barra_xp is not None
        self._barra_xp.rect = barra_rect
        self._barra_xp.minimo = 0.0
        self._barra_xp.maximo = float(max(1, xp_alvo))
        self._barra_xp.set_valor(min(xp_atual, xp_alvo))
        self._barra_xp.render(tela, [], 0)

        self.TxtXP.set_text(f'{xp_atual}/{xp_alvo}')
        self.TxtXP.set_pos((barra_rect.centerx, barra_rect.bottom + 11))
        self.TxtXP.style['align'] = 'center'
        self.TxtXP.draw(tela)
        self.TxtXP.style['align'] = 'topleft'

        tipos_rect = pygame.Rect(rect.x + 16, barra_rect.bottom + 34, rect.width - 32, 38)
        self._desenhar_tipos(tela, tipos_rect, tipos)

        linhas = [
            ('Altura', self._formatar_numero(altura, 2, ' m') if altura not in (None, '') else '-'),
            ('Peso', self._formatar_numero(peso, 2, ' kg') if peso not in (None, '') else '-'),
            ('Amizade', self._formatar_percentual(amizade)),
            ('Crítico', crit_chance),
            ('Dano crítico', crit_dano),
            ('Grupo', str(grupo or '-')),
        ]
        y = tipos_rect.bottom + 10
        for rotulo, valor in linhas:
            self.TxtInfo.set_text(f'{rotulo}: {valor}')
            self.TxtInfo.set_pos((rect.x + 16, y))
            self.TxtInfo.draw(tela)
            y += 24

        self.TxtTitulo.set_text(nome)
        self.TxtTitulo.set_pos((rect.x + 16, rect.y - 12))
        self.TxtTitulo.draw(tela)

    def _desenhar_slot_build(self, tela: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(tela, (20, 28, 46), rect, border_radius=12)
        pygame.draw.rect(tela, (92, 122, 182), rect, 2, border_radius=12)
        self.TxtSlot.set_pos(rect.center)
        self.TxtSlot.draw(tela)

    def _desenhar_slot_ataque(self, tela: pygame.Surface, rect: pygame.Rect, ataque: dict | None, selecionado=False):
        bg = (24, 33, 54) if ataque is not None else (18, 24, 38)
        borda = (232, 239, 255) if selecionado else (88, 110, 156)
        pygame.draw.rect(tela, bg, rect, border_radius=11)
        pygame.draw.rect(tela, borda, rect, 2, border_radius=11)
        if ataque is None:
            self.TxtMini.set_text('+')
            self.TxtMini.set_pos(rect.center)
            self.TxtMini.draw(tela)
            return
        icone = self._icone_ataque(ataque, min(rect.width, rect.height) - 10)
        if icone is not None:
            tela.blit(icone, icone.get_rect(center=rect.center))
        else:
            nome = str(ataque.get('Ataque') or ataque.get('Nome') or 'Atk')
            tipo = str(ataque.get('Tipo') or 'Normal')
            pygame.draw.circle(tela, self._cor_tipo(tipo), rect.center, max(10, min(rect.width, rect.height) // 3))
            self.TxtMini.set_text(nome[:2].upper())
            self.TxtMini.set_pos(rect.center)
            self.TxtMini.draw(tela)

    def _desenhar_bloco_superior_direito(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None):
        pygame.draw.rect(tela, (11, 17, 30), rect, border_radius=18)
        pygame.draw.rect(tela, (66, 90, 140), rect, 1, border_radius=18)

        habilidades = self._habilidades_ref(pokemon)
        memoria = self._memoria_ref(pokemon)
        equipaveis = self._equipaveis(pokemon)
        colunas_habilidades = max(1, max(len(habilidades), len(memoria)))

        padding = 14
        area_interna = rect.inflate(-padding * 2, -padding * 2)
        build_w = max(104, int(area_interna.width * 0.28))
        build_rect = pygame.Rect(area_interna.x, area_interna.y + 20, build_w, area_interna.height - 22)
        habilidades_rect = pygame.Rect(build_rect.right + 12, area_interna.y + 20, area_interna.width - build_w - 12, area_interna.height - 22)

        self.TxtSetor.set_text(f'Build ({equipaveis})')
        self.TxtSetor.set_pos((build_rect.x, rect.y + 12))
        self.TxtSetor.draw(tela)
        self.TxtSetor.set_text(f'Habilidades ({len(habilidades)}) / Memória ({len(memoria)})')
        self.TxtSetor.set_pos((habilidades_rect.x, rect.y + 12))
        self.TxtSetor.draw(tela)

        pygame.draw.rect(tela, (15, 22, 38), build_rect, border_radius=14)
        pygame.draw.rect(tela, (74, 99, 148), build_rect, 1, border_radius=14)
        pygame.draw.rect(tela, (15, 22, 38), habilidades_rect, border_radius=14)
        pygame.draw.rect(tela, (74, 99, 148), habilidades_rect, 1, border_radius=14)

        self._slots_build = []
        lado_build = min(54, max(42, (build_rect.width - 28) // 2))
        gap_build = 10
        linhas_build = 1 if equipaveis == 1 else 2
        colunas_build = 1 if equipaveis <= 2 else 2
        total_w = colunas_build * lado_build + (colunas_build - 1) * gap_build
        total_h = linhas_build * lado_build + (linhas_build - 1) * gap_build
        start_x = build_rect.x + (build_rect.width - total_w) // 2
        start_y = build_rect.y + (build_rect.height - total_h) // 2
        posicoes_3 = [(0, 0), (1, 0), (0, 1)]
        for i in range(equipaveis):
            if equipaveis == 3:
                col, lin = posicoes_3[i]
            else:
                col = i % colunas_build
                lin = i // colunas_build
            slot = pygame.Rect(start_x + col * (lado_build + gap_build), start_y + lin * (lado_build + gap_build), lado_build, lado_build)
            self._slots_build.append(slot)
            self._desenhar_slot_build(tela, slot)

        self._slots_ataque = {}
        header_top_y = habilidades_rect.y + 8
        self.TxtMini.set_text('Ativos')
        self.TxtMini.set_pos((habilidades_rect.x + 10, header_top_y))
        self.TxtMini.draw(tela)
        self.TxtMini.set_text('Memória')
        self.TxtMini.set_pos((habilidades_rect.x + 10, header_top_y + (habilidades_rect.height // 2)))
        self.TxtMini.draw(tela)

        slots_area_y = habilidades_rect.y + 28
        linha_gap = 16
        bloco_h = (habilidades_rect.height - 28 - linha_gap) // 2
        lado_slot = min(56, max(36, (habilidades_rect.width - 18 - (colunas_habilidades - 1) * 8) // max(1, colunas_habilidades)))
        gap = 8
        largura_total = colunas_habilidades * lado_slot + (colunas_habilidades - 1) * gap
        start_x = habilidades_rect.x + (habilidades_rect.width - largura_total) // 2
        y_hab = slots_area_y + max(0, (bloco_h - lado_slot) // 2)
        y_mem = y_hab + bloco_h + linha_gap

        origem_oculta = self._slot_origem_oculto if self._arrastavel_ataque.Ativo else None
        for i in range(colunas_habilidades):
            rect_h = pygame.Rect(start_x + i * (lado_slot + gap), y_hab, lado_slot, lado_slot)
            rect_m = pygame.Rect(start_x + i * (lado_slot + gap), y_mem, lado_slot, lado_slot)
            self._slots_ataque[('habilidades', i)] = rect_h
            self._slots_ataque[('memoria', i)] = rect_m
            ataque_h = habilidades[i] if i < len(habilidades) else None
            ataque_m = memoria[i] if i < len(memoria) else None
            if origem_oculta == ('habilidades', i):
                ataque_h = None
            if origem_oculta == ('memoria', i):
                ataque_m = None
            self._desenhar_slot_ataque(tela, rect_h, ataque_h, selecionado=self._slot_hover == ('habilidades', i))
            self._desenhar_slot_ataque(tela, rect_m, ataque_m, selecionado=self._slot_hover == ('memoria', i))

    def _desenhar_resumo_status(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None):
        pygame.draw.rect(tela, (15, 22, 38), rect, border_radius=14)
        pygame.draw.rect(tela, (74, 99, 148), rect, 1, border_radius=14)
        poder = self._poder_total(pokemon)
        iv = self._iv_medio(pokemon)
        relativo = self._poder_relativo(pokemon)
        blocos = [('Poder', str(poder)), ('IV', f'{iv}%'), ('Relativo', f'{relativo}%')]
        y = rect.y + 18
        for rotulo, valor in blocos:
            self.TxtMini.set_text(rotulo)
            self.TxtMini.set_pos((rect.x + 12, y))
            self.TxtMini.draw(tela)
            self.TxtResumo.set_text(valor)
            self.TxtResumo.set_pos((rect.x + 12, y + 16))
            self.TxtResumo.draw(tela)
            y += 66

    def _desenhar_bloco_status(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None, dt: float):
        pygame.draw.rect(tela, (11, 17, 30), rect, border_radius=18)
        pygame.draw.rect(tela, (66, 90, 140), rect, 1, border_radius=18)
        self.TxtSetor.set_text('Atributos')
        self.TxtSetor.set_pos((rect.x + 16, rect.y + 12))
        self.TxtSetor.draw(tela)

        padding = 14
        resumo_w = 128
        area_barras = pygame.Rect(rect.x + padding, rect.y + 40, rect.width - resumo_w - padding * 3, rect.height - 52)
        area_resumo = pygame.Rect(area_barras.right + 12, rect.y + 40, resumo_w, rect.height - 52)
        self._desenhar_resumo_status(tela, area_resumo, pokemon)

        colunas = 2
        linhas = 5
        gap_x = 14
        gap_y = 10
        card_w = (area_barras.width - gap_x) // colunas
        card_h = (area_barras.height - gap_y * (linhas - 1)) // linhas

        for idx, status in enumerate(self._ordem_status):
            col = idx % colunas
            lin = idx // colunas
            card = pygame.Rect(area_barras.x + col * (card_w + gap_x), area_barras.y + lin * (card_h + gap_y), card_w, card_h)
            pygame.draw.rect(tela, (15, 22, 38), card, border_radius=12)
            pygame.draw.rect(tela, (74, 99, 148), card, 1, border_radius=12)

            valor = self._valor_status(pokemon, status)
            iv = self._subiv_status(pokemon, status)
            cor = self._cores_status.get(status, (110, 170, 255))
            self.TxtStatus.set_text(f'{self._nomes_status[status]}  {int(round(valor))}')
            self.TxtStatus.set_pos((card.x + 10, card.y + 6))
            self.TxtStatus.draw(tela)

            barra = Barra(pygame.Rect(card.x + 10, card.y + 25, card.width - 20, 15), texto='', valor=valor, minimo=0, maximo=self._max_barra_status(pokemon, status), mostrar_rotulo=False, suavizacao=12.0)
            barra.cor_fundo = (26, 34, 56)
            barra.cor_preenchimento = cor
            barra.cor_borda = tuple(max(0, min(255, c + 42)) for c in cor)
            barra.render(tela, [], dt)

            self.TxtIV.set_text(f'IV {int(round(iv))}%')
            self.TxtIV.set_pos((card.x + 10, card.bottom - 18))
            self.TxtIV.draw(tela)

    def _slot_no_mouse(self, pos) -> tuple[str, int] | None:
        for chave, rect in self._slots_ataque.items():
            if rect.collidepoint(pos):
                return chave
        return None

    def _ataque_no_slot(self, pokemon: dict | None, slot: tuple[str, int] | None):
        if slot is None or not isinstance(pokemon, dict):
            return None
        grupo, indice = slot
        lista = self._habilidades_ref(pokemon) if grupo == 'habilidades' else self._memoria_ref(pokemon)
        if 0 <= indice < len(lista):
            return lista[indice]
        return None

    def _iniciar_arrasto_ataque(self, pokemon: dict | None, slot: tuple[str, int], mouse_pos):
        ataque = self._ataque_no_slot(pokemon, slot)
        rect = self._slots_ataque.get(slot)
        if ataque is None or rect is None:
            return
        self._arrastavel_ataque.iniciar(ataque, slot, rect.inflate(-6, -6), mouse_pos, botao=1)
        self._slot_origem_oculto = slot

    def _retornar_arrasto(self):
        if not self._arrastavel_ataque.Ativo:
            return
        origem = self._arrastavel_ataque.Origem
        rect = self._slots_ataque.get(origem)
        if rect is None:
            self._arrastavel_ataque.cancelar()
            self._slot_origem_oculto = None
            return
        self._arrastavel_ataque.definir_pos_alvo(rect.inflate(-6, -6).topleft, ao_final=self._cancelar_arrasto)

    def _cancelar_arrasto(self):
        self._arrastavel_ataque.cancelar()
        self._slot_origem_oculto = None

    def _garantir_tamanho_lista(self, lista: list, indice: int):
        if indice >= len(lista):
            lista.extend([None] * (indice + 1 - len(lista)))

    def _trocar_ataques(self, pokemon: dict | None, origem: tuple[str, int], destino: tuple[str, int]):
        if not isinstance(pokemon, dict):
            self._cancelar_arrasto()
            return
        lista_origem = self._habilidades_ref(pokemon) if origem[0] == 'habilidades' else self._memoria_ref(pokemon)
        lista_destino = self._habilidades_ref(pokemon) if destino[0] == 'habilidades' else self._memoria_ref(pokemon)
        self._garantir_tamanho_lista(lista_origem, origem[1])
        self._garantir_tamanho_lista(lista_destino, destino[1])
        lista_origem[origem[1]], lista_destino[destino[1]] = lista_destino[destino[1]], lista_origem[origem[1]]
        self._cancelar_arrasto()

    def _processar_eventos(self, tela: pygame.Surface, pokemon: dict | None, eventos, dt: float):
        eventos = eventos or []
        self.FecharSolicitado = False
        if self._botao_fechar is not None:
            self._botao_fechar.render(tela, eventos, dt, None)

        self._arrastavel_ataque.animar(dt)
        mouse = pygame.mouse.get_pos()
        self._slot_hover = self._slot_no_mouse(mouse)

        for evento in eventos:
            if evento.type == pygame.MOUSEMOTION and self._arrastavel_ataque.Ativo and self._arrastavel_ataque.PosAlvo is None:
                self._arrastavel_ataque.atualizar(evento.pos)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self._arrastavel_ataque.Ativo:
                    continue
                slot = self._slot_no_mouse(evento.pos)
                if slot is not None and self._ataque_no_slot(pokemon, slot) is not None:
                    self._iniciar_arrasto_ataque(pokemon, slot, evento.pos)
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and self._arrastavel_ataque.Ativo:
                if self._arrastavel_ataque.PosAlvo is not None:
                    continue
                origem = self._arrastavel_ataque.Origem
                destino = self._slot_no_mouse(evento.pos)
                if origem is None or destino is None:
                    self._retornar_arrasto()
                elif origem == destino:
                    self._retornar_arrasto()
                else:
                    self._trocar_ataques(pokemon, origem, destino)

    def _desenhar_arrastavel(self, tela: pygame.Surface):
        if not self._arrastavel_ataque.Ativo or self._arrastavel_ataque.Item is None:
            return
        self._desenhar_slot_ataque(tela, self._arrastavel_ataque.Rect, self._arrastavel_ataque.Item, selecionado=True)

    def renderizar(self, tela: pygame.Surface, rect, pokemon: dict | None, eventos=None, dt: float = 0.0):
        rect = pygame.Rect(rect)
        self._garantir_layout(rect)
        self._draw_panel_bg(tela, rect)

        if pokemon is None:
            self.TxtVazio.set_pos((rect.x + 18, rect.y + 18))
            self.TxtVazio.draw(tela)
            if self._botao_fechar is not None:
                self._botao_fechar.base_rect.topleft = (rect.right - 44, rect.y + 12)
                self._botao_fechar.rect = pygame.Rect(self._botao_fechar.base_rect)
                self._botao_fechar.render(tela, eventos or [], dt, None)
            return

        if self._botao_fechar is not None:
            self._botao_fechar.base_rect.topleft = (rect.right - 44, rect.y + 12)
            self._botao_fechar.rect = pygame.Rect(self._botao_fechar.base_rect)

        left, right_top, right_bottom = self._setores(rect)
        self._bloco_infos_esquerda(tela, left, pokemon)
        self._desenhar_bloco_superior_direito(tela, right_top, pokemon)
        self._desenhar_bloco_status(tela, right_bottom, pokemon, dt)
        self._processar_eventos(tela, pokemon, eventos or [], dt)
        self._desenhar_arrastavel(tela)

        ataque_hover = self._ataque_no_slot(pokemon, self._slot_hover)
        if self._arrastavel_ataque.Ativo and self._arrastavel_ataque.Item is not None:
            ataque_hover = self._arrastavel_ataque.Item
        if ataque_hover is not None:
            self._ficha_ataque.renderizar_tooltip(tela, ataque_hover, area_ancora=right_bottom)
