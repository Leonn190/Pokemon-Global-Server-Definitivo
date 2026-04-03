from __future__ import annotations

import math
import unicodedata
from pathlib import Path

import pygame

try:
    from Codigo.Modulos.Auxiliares import carregar_frames
    from Codigo.Geradores.ItemInventario import ItemInventario
    from Codigo.Geradores.PokemonInventario import PokemonInventario
    from Codigo.Prefabs.Arrastavel import Arrastavel
    from Codigo.Prefabs.Barra import Barra
    from Codigo.Prefabs.Botao import Botao
    from Codigo.Prefabs.Painel import Painel
    from Codigo.Prefabs.Texto import Texto
    from Codigo.Paineis.FichaAtaque import FichaAtaque
except Exception:  # pragma: no cover
    from PokemonInventario import PokemonInventario
    from Arrastavel import Arrastavel
    from Barra import Barra
    from Botao import Botao
    from Painel import Painel
    from Texto import Texto
    from FichaAtaque import FichaAtaque


_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class FichaPokemon:
    _cache_superficies: dict[tuple[str, tuple[int, int], str], pygame.Surface] = {}
    _cache_listagem: dict[str, dict[str, Path]] = {}
    _cache_frames: dict[str, list[pygame.Surface]] = {}
    _cache_frames_escalados: dict[tuple[str, int], list[pygame.Surface]] = {}
    _cache_pastas_tipo_ataque: dict[str, list[Path]] = {}
    _cache_icone_ataque_path: dict[tuple[str, str], Path | None] = {}
    _INTERVALO_FRAME_ANIM_MS = 60

    _ordem_status = ('Vida', 'Atk', 'Def', 'SpA', 'SpD', 'Vel', 'Mag', 'Per', 'Ene', 'Int')
    _cores_status = {
        'Vida': (108, 201, 123),
        'Atk': (235, 109, 94),
        'Def': (227, 192, 92),
        'SpA': (166, 104, 255),
        'SpD': (121, 214, 255),
        'Vel': (255, 174, 82),
        'Mag': (255, 138, 206),
        'Per': (155, 155, 155),
        'Ene': (56, 104, 212),
        'Int': (86, 229, 240),
    }
    _cores_tipo = {
        'normal': (166, 168, 181),
        'fogo': (239, 120, 74),
        'agua': (89, 159, 255),
        'eletrico': (239, 202, 74),
        'planta': (93, 188, 106),
        'gelo': (109, 210, 214),
        'lutador': (205, 96, 78),
        'venenoso': (174, 97, 196),
        'terrestre': (212, 181, 96),
        'voador': (134, 162, 245),
        'psiquico': (247, 116, 164),
        'inseto': (150, 189, 77),
        'pedra': (190, 163, 92),
        'fantasma': (118, 105, 188),
        'dragao': (96, 120, 236),
        'sombrio': (116, 104, 92),
        'metal': (118, 142, 158),
        'fada': (225, 133, 199),
        'cosmico': (108, 110, 210),
        'sonoro': (112, 206, 196),
    }

    def __init__(self):
        self._painel: Painel | None = None
        self._rect_cache: tuple[int, int, int, int] | None = None
        self._ficha_ataque = FichaAtaque()
        self._arrastavel_ataque = Arrastavel()
        self._botao_fechar: Botao | None = None
        self._botao_doar: Botao | None = None
        self._botao_upar: Botao | None = None
        self._slots_ataque: dict[tuple[str, int], pygame.Rect] = {}
        self._slots_build: dict[int, pygame.Rect] = {}
        self._area_animacao = pygame.Rect(0, 0, 0, 0)
        self._slot_hover: tuple[str, int] | None = None
        self._slot_origem_oculto: tuple[str, int] | None = None
        self._anim_barras_chave = None
        self._barra_hp: Barra | None = None
        self._barra_xp: Barra | None = None
        self._barras_status: dict[str, Barra] = {}
        self.FecharSolicitado = False
        self.DoarSolicitado = False
        self.UparNivelSolicitado = False

        base = {
            'outline': True,
            'outline_thickness': 2,
            'outline_color': (8, 12, 20),
            'shadow': False,
        }
        self.TxtTitulo = Texto('', style={**base, 'size': 25, 'color': (245, 249, 255)})
        self.TxtTituloCentro = Texto('', style={**base, 'size': 29, 'color': (245, 249, 255), 'align': 'center'})
        self.TxtSub = Texto('', style={**base, 'size': 15, 'color': (176, 190, 224)})
        self.TxtSubCentro = Texto('', style={**base, 'size': 15, 'color': (176, 190, 224), 'align': 'center'})
        self.TxtNivel = Texto('', style={**base, 'size': 18, 'color': (245, 249, 255), 'align': 'center'})
        self.TxtXP = Texto('', style={**base, 'size': 14, 'color': (186, 202, 236)})
        self.TxtInfo = Texto('', style={**base, 'size': 14, 'color': (196, 208, 232)})
        self.TxtSetor = Texto('', style={**base, 'size': 17, 'color': (238, 244, 255)})
        self.TxtMini = Texto('', style={**base, 'size': 13, 'color': (176, 190, 221)})
        self.TxtSlot = Texto('', style={**base, 'size': 28, 'color': (206, 216, 240), 'align': 'center'})
        self.TxtStatus = Texto('', style={**base, 'size': 13, 'color': (245, 249, 255), 'align': 'center'})
        self.TxtIV = Texto('', style={**base, 'size': 12, 'color': (169, 186, 222), 'align': 'center'})
        self.TxtResumo = Texto('', style={**base, 'size': 16, 'color': (244, 248, 255)})
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
        vistos: list[Path] = []
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
                if arquivo.is_file():
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
        return cls._cores_tipo.get(PokemonInventario.normalizar_tipo(tipo), (88, 126, 196))

    @classmethod
    def _ler_valor_por_chaves(cls, dados: dict | None, *chaves, default=None):
        if not isinstance(dados, dict):
            return default
        candidatos = [cls._normalizar(ch) for ch in chaves if str(ch or '').strip()]
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
        for chave in ('SubIVs', 'subivs', 'IVs', 'ivs'):
            valor = pokemon.get(chave)
            if isinstance(valor, dict):
                for status in cls._ordem_status:
                    bruto = cls._ler_valor_por_chaves(valor, status, status.lower(), default=None)
                    if bruto in (None, ''):
                        continue
                    try:
                        ivs[status] = float(bruto)
                    except (TypeError, ValueError):
                        pass
        for status in cls._ordem_status:
            for chave in (f'IV{status}', f'{status}IV', f'SubIV{status}', f'{status}SubIV'):
                bruto = cls._valor_pokemon(pokemon, chave, default=None)
                if bruto in (None, ''):
                    continue
                try:
                    ivs.setdefault(status, float(bruto))
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
            for sep in ('/', ',', ';', '|'):
                texto = texto.replace(sep, ',')
            valores = [parte.strip() for parte in texto.split(',') if parte.strip()]
        unicos: list[str] = []
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
        bruto = cls._valor_pokemon(pokemon, 'Equipaveis', 'Equipáveis', 'Equipamentos', 'SlotsEquipaveis', 'SlotsEquipáveis', default=1)
        try:
            return max(1, min(3, int(bruto)))
        except (TypeError, ValueError):
            return 1

    @classmethod
    def _nivel(cls, pokemon: dict | None) -> int:
        bruto = cls._valor_pokemon(pokemon, 'Nivel', 'Nível', 'nivel', 'nível', default=0)
        try:
            return max(0, int(bruto))
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
    def _vida_atual(cls, pokemon: dict | None) -> float:
        bruto = cls._valor_pokemon(
            pokemon,
            'VidaAtual', 'Vida Atual', 'vida_atual', 'HPAtual', 'HP Atual', 'CurrentHP', 'current_hp',
            default=None,
        )
        try:
            if bruto is not None:
                return max(0.0, float(bruto))
        except (TypeError, ValueError):
            pass
        return max(0.0, cls._valor_status(pokemon, 'Vida'))

    @classmethod
    def _amizade(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Amizade', 'amizade', 'Friendship', default=None)

    @classmethod
    def _fruta_favorita(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'FrutaFavorita', 'Fruta Favorita', 'Favorita', 'BerryFavorita', 'FavoriteBerry', default='-')

    @classmethod
    def _grupo(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Grupo', 'grupo', 'GrupoOvo', 'EggGroup', default='-')

    @classmethod
    def _estagio(cls, pokemon: dict | None):
        return cls._valor_pokemon(pokemon, 'Estagio', 'Estágio', 'Stage', 'stage', default='-')

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
        bruto = cls._valor_pokemon(pokemon, 'Poder', 'power', 'Power', default=0)
        try:
            return max(0, int(round(float(bruto))))
        except (TypeError, ValueError):
            return 0

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
        bruto = cls._valor_pokemon(pokemon, 'PoderRelativo', 'Poder Relativo', 'power_relative', 'power relativo', default=0)
        try:
            numero = float(bruto)
            if 0.0 <= numero <= 1.0:
                numero *= 100.0
            return max(0, min(999, int(round(numero))))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _subiv_status(cls, pokemon: dict | None, status: str) -> float:
        valor = cls._ivs_dict(pokemon).get(status, 0.0)
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
        chave = str(especie or '').strip().lower()
        if not chave:
            return []
        if chave in cls._cache_frames:
            return cls._cache_frames[chave]
        frames = carregar_frames(_PASTA_ANIMACOES / chave)
        cls._cache_frames[chave] = frames
        return frames

    @classmethod
    def _obter_frames_escalados(cls, especie: str, limite_px: int, escala: float = 1.1) -> list[pygame.Surface]:
        limite = max(8, int(limite_px))
        escala_i = max(1, int(round(float(escala) * 100)))
        chave = (str(especie).lower(), limite * 1000 + escala_i)
        if chave in cls._cache_frames_escalados:
            return cls._cache_frames_escalados[chave]
        frames = cls._carregar_frames_nome(especie)
        escalados = []
        for frame in frames:
            w, h = frame.get_size()
            if w <= 0 or h <= 0:
                continue
            nw = max(1, int(round(w * escala)))
            nh = max(1, int(round(h * escala)))
            maior = max(nw, nh)
            if maior > limite:
                k = limite / float(maior)
                nw = max(1, int(round(nw * k)))
                nh = max(1, int(round(nh * k)))
            escalados.append(pygame.transform.smoothscale(frame, (nw, nh)))
        cls._cache_frames_escalados[chave] = escalados
        return escalados

    def _icone_tipo(self, tipo: str, lado: int) -> pygame.Surface | None:
        arquivo = self._achar_arquivo(Path('Recursos') / 'Visual' / 'Icones' / 'Tipos', tipo)
        return self._carregar_surface(arquivo, (lado, lado), chave_extra='contain')

    @classmethod
    def _pastas_tipo_ataque(cls, tipo: str) -> list[Path]:
        chave = cls._normalizar(tipo)
        if chave in cls._cache_pastas_tipo_ataque:
            return cls._cache_pastas_tipo_ataque[chave]
        base_pastas = cls._pastas_existentes(Path('Recursos') / 'Visual' / 'Icones' / 'Ataques')
        alvo_norm = chave
        encontradas: list[Path] = []
        for base in base_pastas:
            try:
                for pasta in base.iterdir():
                    if pasta.is_dir():
                        nome = cls._normalizar(pasta.name)
                        if nome == alvo_norm or nome.startswith(alvo_norm) or alvo_norm in nome:
                            encontradas.append(pasta)
            except OSError:
                continue
        cls._cache_pastas_tipo_ataque[chave] = encontradas
        return encontradas

    @classmethod
    def _icone_ataque_path(cls, nome_ataque: str, tipo: str) -> Path | None:
        chave = (cls._normalizar(nome_ataque), cls._normalizar(tipo))
        if chave in cls._cache_icone_ataque_path:
            return cls._cache_icone_ataque_path[chave]
        candidatos = [chave[0]]
        for pasta in cls._pastas_tipo_ataque(tipo):
            mapa = cls._listar_arquivos(pasta)
            for nome in candidatos:
                if nome in mapa:
                    cls._cache_icone_ataque_path[chave] = mapa[nome]
                    return mapa[nome]
            for nome in candidatos:
                for chave_mapa, arquivo in mapa.items():
                    if chave_mapa == nome or chave_mapa.startswith(nome) or nome in chave_mapa:
                        cls._cache_icone_ataque_path[chave] = arquivo
                        return arquivo
        cls._cache_icone_ataque_path[chave] = None
        return None

    def _icone_ataque(self, ataque: dict | None, lado: int) -> pygame.Surface | None:
        if not isinstance(ataque, dict):
            return None
        nome = str(ataque.get('Ataque') or ataque.get('Nome') or ataque.get('nome') or '').strip()
        tipo = str(ataque.get('Tipo') or ataque.get('tipo') or 'Normal').strip() or 'Normal'
        return self._carregar_surface(self._icone_ataque_path(nome, tipo), (lado, lado), chave_extra='contain')

    def _garantir_layout(self, rect):
        rect = pygame.Rect(rect)
        chave = (rect.x, rect.y, rect.width, rect.height)
        if self._painel is not None and self._rect_cache == chave:
            return
        self._rect_cache = chave
        self._painel = Painel(rect, cor_fundo=(20, 26, 42, 238), cor_borda=(74, 98, 146), borda=2, raio=18)

        def _fechar(_jogo, _botao):
            self.FecharSolicitado = True

        self._botao_fechar = Botao(
            pygame.Rect(rect.right - 52, rect.y + 12, 36, 36),
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
                'text_style': {'size': 21, 'outline_thickness': 1, 'shadow': False},
            },
        )
        self._botao_doar = Botao(
            pygame.Rect(rect.x + 16, rect.bottom - 40, 112, 26),
            'Doar',
            execute=lambda _jogo, _botao: setattr(self, 'DoarSolicitado', True),
            style={
                'radius': 10, 'border_width': 2,
                'bg': (102, 54, 54), 'bg_hover': (132, 66, 66), 'bg_pressed': (88, 43, 43),
                'border': (242, 219, 219), 'border_hover': (255, 245, 245),
                'hover_scale': 1.0, 'press_scale': 0.98,
                'text_style': {'size': 15, 'outline_thickness': 1, 'shadow': False},
            },
        )
        self._botao_upar = Botao(
            pygame.Rect(rect.x + 136, rect.bottom - 40, 148, 26),
            'Subir nível',
            execute=lambda _jogo, _botao: setattr(self, 'UparNivelSolicitado', True),
            style={
                'radius': 10, 'border_width': 2,
                'bg': (46, 78, 130), 'bg_hover': (60, 97, 162), 'bg_pressed': (37, 61, 101),
                'border': (206, 224, 255), 'border_hover': (233, 241, 255),
                'hover_scale': 1.0, 'press_scale': 0.98,
                'text_style': {'size': 15, 'outline_thickness': 1, 'shadow': False},
            },
        )
        self._botao_upar.limpar_tooltip()

    @staticmethod
    def calcular_rect_ancorado(area_host) -> pygame.Rect:
        area = pygame.Rect(area_host)
        largura = min(max(420, int(area.width * 0.44)), 620)
        return pygame.Rect(area.x, area.y, largura, area.height)

    def _setores(self, rect: pygame.Rect):
        margem = 14
        header_h = 42
        interno = rect.inflate(-margem * 2, -margem * 2)
        conteudo = pygame.Rect(interno.x, interno.y + header_h, interno.width, interno.height - header_h)
        left_w = max(170, int(conteudo.width * 0.28))
        gap = 12
        left = pygame.Rect(conteudo.x, conteudo.y, left_w, conteudo.height)
        right = pygame.Rect(left.right + gap, conteudo.y, conteudo.width - left_w - gap, conteudo.height)
        top_h = max(190, int(right.height * 0.45))
        right_top = pygame.Rect(right.x, right.y, right.width, top_h)
        right_bottom = pygame.Rect(right.x, right_top.bottom + gap, right.width, right.height - top_h - gap)
        return left, right_top, right_bottom

    def _desenhar_base(self, tela: pygame.Surface, rect: pygame.Rect):
        assert self._painel is not None
        self._painel.rect = rect
        self._painel.render(tela, [], 0)
        header = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, 44)
        pygame.draw.rect(tela, (18, 24, 39), header, border_radius=12)

    def _desenhar_setor(self, tela: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(tela, (11, 17, 30), rect, border_radius=16)
        pygame.draw.rect(tela, (66, 90, 140), rect, 1, border_radius=16)

    def _desenhar_animacao_pokemon(self, tela: pygame.Surface, rect: pygame.Rect, especie: str):
        centro = rect.center
        frames = self._obter_frames_escalados(especie, int(min(rect.width, rect.height) * 0.68), escala=1.2)
        if frames:
            frame = frames[int((pygame.time.get_ticks() / self._INTERVALO_FRAME_ANIM_MS) % len(frames))]
            tela.blit(frame, frame.get_rect(center=centro))
            return
        raio = max(10, int(min(rect.width, rect.height) * 0.12))
        pygame.draw.circle(tela, (84, 146, 244), centro, raio)
        pygame.draw.circle(tela, (25, 74, 164), centro, raio, 2)

    def _desenhar_tipos(self, tela: pygame.Surface, area: pygame.Rect, tipos: list[str], lado_max: int = 34):
        lado = max(16, min(lado_max, area.height - 2))
        gap = 8
        x = area.x
        for tipo in tipos:
            base_rect = pygame.Rect(x, area.y + (area.height - lado) // 2, lado, lado)
            pygame.draw.circle(tela, (245, 248, 255), base_rect.center, lado // 2)
            pygame.draw.circle(tela, self._cor_tipo(tipo), base_rect.center, lado // 2, 2)
            icone = self._icone_tipo(tipo, lado)
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=base_rect.center))
            else:
                self.TxtMini.set_text(tipo[:2].upper())
                self.TxtMini.set_pos(base_rect.center)
                self.TxtMini.draw(tela)
            x = base_rect.right + gap

    def _desenhar_cabecalho(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None):
        if pokemon is None:
            return
        nome, _ = self._nome_especie(pokemon)
        tipos = self._tipos(pokemon)
        header = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, 44)
        botao_rect = self._botao_fechar.rect if self._botao_fechar is not None else pygame.Rect(header.right - 30, header.y + 1, 30, 30)
        tipo_lado = min(96, int((header.height + 12) * 1.95))
        gap_tipo = 8
        tipos_w = (len(tipos) * tipo_lado) + (max(0, len(tipos) - 1) * gap_tipo)
        tipos_area = pygame.Rect(header.x + 12, header.y + 2, tipos_w, header.height - 4)
        if tipos_w > 0:
            self._desenhar_tipos(tela, tipos_area, tipos, lado_max=tipo_lado)
        esquerda_titulo = tipos_area.right + 10 if tipos_w > 0 else header.x + 12
        direita_titulo = botao_rect.x - 10
        centro_x = (esquerda_titulo + direita_titulo) // 2
        self.TxtTituloCentro.set_text(nome)
        self.TxtTituloCentro.set_pos((centro_x, header.y + 27))
        self.TxtTituloCentro.draw(tela)

    def _preparar_animacao_barras(self, pokemon: dict | None):
        chave = self._normalizar(str(self._valor_pokemon(pokemon, 'UID', 'uid', 'Id', 'id', default='')))
        if not chave:
            chave = self._normalizar(str(self._nome_especie(pokemon)[0] if pokemon is not None else ''))
        if chave != self._anim_barras_chave:
            self._anim_barras_chave = chave
            if self._barra_hp is not None:
                self._barra_hp.reiniciar_animacao(0.0)
            if self._barra_xp is not None:
                self._barra_xp.reiniciar_animacao(0.0)
            for barra in self._barras_status.values():
                barra.reiniciar_animacao(0.0)

    def _bloco_infos_esquerda(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None, dt: float, stats: dict[str, float] | None = None):
        self._desenhar_setor(tela, rect)
        _nome, especie = self._nome_especie(pokemon)
        nivel = self._nivel(pokemon)
        xp_atual, xp_alvo = self._xp(pokemon)
        stats = stats or self._stats_dict(pokemon)
        vida_max = max(1, int(round(stats.get('Vida', 0.0))))
        vida_atual = min(vida_max, int(round(self._vida_atual(pokemon))))
        crit_chance, crit_dano = self._criticos(pokemon)

        self.TxtSubCentro.set_text(especie)
        self.TxtSubCentro.set_pos((rect.centerx, rect.y + 12))
        self.TxtSubCentro.draw(tela)

        anim_rect = pygame.Rect(rect.x + 16, rect.y + 28, rect.width - 32, 102)
        self._area_animacao = pygame.Rect(anim_rect)
        self._desenhar_animacao_pokemon(tela, anim_rect, especie)

        self.TxtNivel.set_text(f'Lv {nivel}')
        self.TxtNivel.set_pos((rect.centerx, anim_rect.bottom + 4))
        self.TxtNivel.draw(tela)

        barra_largura = rect.width - 32
        hp_label_y = anim_rect.bottom + 28
        self.TxtMini.set_text(f'HP {vida_atual}/{vida_max}')
        self.TxtMini.set_pos((rect.x + 16, hp_label_y))
        self.TxtMini.draw(tela)
        if self._barra_hp is None:
            self._barra_hp = Barra((0, 0, 1, 1), texto='', valor=0, minimo=0, maximo=1, mostrar_rotulo=False, suavizacao=30.0)
        self._barra_hp.configurar(
            rect=pygame.Rect(rect.x + 16, hp_label_y + 16, barra_largura, 12),
            minimo=0.0,
            maximo=float(max(1, vida_max)),
            cor_fundo=(21, 29, 48),
            cor_borda=(0, 0, 0),
            cor_preenchimento=(96, 212, 124),
            vertical=False,
        )
        self._barra_hp.set_valor(float(vida_atual), animar=False)
        self._barra_hp.render(tela, [], dt)

        xp_label_y = hp_label_y + 34
        self.TxtMini.set_text(f'XP {xp_atual}/{xp_alvo}')
        self.TxtMini.set_pos((rect.x + 16, xp_label_y))
        self.TxtMini.draw(tela)
        if self._barra_xp is None:
            self._barra_xp = Barra((0, 0, 1, 1), texto='', valor=0, minimo=0, maximo=1, mostrar_rotulo=False, suavizacao=30.0)
        self._barra_xp.configurar(
            rect=pygame.Rect(rect.x + 16, xp_label_y + 16, barra_largura, 12),
            minimo=0.0,
            maximo=float(max(1, xp_alvo)),
            cor_fundo=(21, 29, 48),
            cor_borda=(0, 0, 0),
            cor_preenchimento=(126, 86, 224),
            vertical=False,
        )
        self._barra_xp.set_valor(float(xp_atual), animar=False)
        self._barra_xp.render(tela, [], dt)

        linhas = [
            ('Altura', self._formatar_numero(self._altura(pokemon), 2, ' m')),
            ('Peso', self._formatar_numero(self._peso(pokemon), 2, ' kg')),
            ('Amizade', self._formatar_percentual(self._amizade(pokemon))),
            ('Fruta', str(self._fruta_favorita(pokemon) or '-')),
            ('Estágio', str(self._estagio(pokemon) or '-')),
            ('Crítico', crit_chance),
            ('D. crítico', crit_dano),
        ]
        y = xp_label_y + 48
        for rotulo, valor in linhas:
            self.TxtInfo.set_text(f'{rotulo}: {valor}')
            self.TxtInfo.set_pos((rect.x + 16, y))
            self.TxtInfo.draw(tela)
            y += 21

    def _desenhar_slot_build(self, tela: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(tela, (20, 28, 46), rect)
        pygame.draw.rect(tela, (92, 122, 182), rect, 2)
        self.TxtSlot.set_text('+')
        self.TxtSlot.set_pos(rect.center)
        self.TxtSlot.draw(tela)

    @classmethod
    def _build_ref(cls, pokemon: dict | None) -> list:
        if not isinstance(pokemon, dict):
            return []
        alvo = pokemon.get('estado') if isinstance(pokemon.get('estado'), dict) else pokemon
        valor = alvo.get('BuildEquipaveis')
        if isinstance(valor, list):
            return valor
        alvo['BuildEquipaveis'] = []
        return alvo['BuildEquipaveis']

    def _desenhar_slot_ataque(self, tela: pygame.Surface, rect: pygame.Rect, ataque: dict | None, selecionado=False):
        pygame.draw.rect(tela, (24, 33, 54) if ataque else (18, 24, 38), rect)
        pygame.draw.rect(tela, (232, 239, 255) if selecionado else (88, 110, 156), rect, 2)
        if ataque is None:
            return
        icone = self._icone_ataque(ataque, min(rect.width, rect.height) - 12)
        if icone is not None:
            tela.blit(icone, icone.get_rect(center=rect.center))
            return
        nome = str(ataque.get('Ataque') or ataque.get('Nome') or 'Atk')
        tipo = str(ataque.get('Tipo') or 'Normal')
        pygame.draw.circle(tela, self._cor_tipo(tipo), rect.center, max(10, min(rect.width, rect.height) // 3))
        self.TxtMini.set_text(nome[:2].upper())
        self.TxtMini.set_pos(rect.center)
        self.TxtMini.draw(tela)

    def _desenhar_bloco_superior_direito(self, tela: pygame.Surface, rect: pygame.Rect, pokemon: dict | None):
        self._desenhar_setor(tela, rect)
        habilidades = self._habilidades_ref(pokemon)
        memoria = self._memoria_ref(pokemon)
        equipaveis = self._equipaveis(pokemon)
        colunas_habilidades = max(1, max(len(habilidades), len(memoria), 5))

        padding = 14
        build_w = max(96, int(rect.width * 0.23))
        build_x = rect.x + padding + 4
        conteudo_y = rect.y + 34
        conteudo_h = rect.height - 46

        self.TxtSetor.set_text('Build')
        self.TxtSetor.set_pos((build_x, rect.y + 12))
        self.TxtSetor.draw(tela)
        lado_build = 58
        gap_build = 12
        start_x = build_x + (build_w - lado_build) // 2
        start_y = conteudo_y + max(2, int(conteudo_h * 0.12)) - 10
        self._slots_build = {}
        for i in range(equipaveis):
            slot = pygame.Rect(start_x, start_y + i * (lado_build + gap_build), lado_build, lado_build)
            self._slots_build[i] = slot
            self._desenhar_slot_build(tela, slot)
            equip_item = self.equipavel_no_slot(pokemon, i)
            if isinstance(equip_item, dict):
                ItemInventario.desenhar_item_no_rect(tela, equip_item, slot.inflate(-8, -8))

        self._slots_ataque = {}
        area_slots = pygame.Rect(build_x + build_w + 18, conteudo_y, rect.right - (build_x + build_w + 18) - padding, conteudo_h)
        lado_slot = min(68, max(52, (area_slots.width - (colunas_habilidades - 1) * 8) // max(1, colunas_habilidades)))
        gap = 8
        total_w_slots = colunas_habilidades * lado_slot + (colunas_habilidades - 1) * gap
        start_slots_x = area_slots.x + (area_slots.width - total_w_slots) // 2
        y_hab = area_slots.y + 24
        y_mem = area_slots.bottom - lado_slot - 14

        self.TxtMini.set_text('Habilidades')
        self.TxtMini.set_pos((area_slots.x, y_hab - 20))
        self.TxtMini.draw(tela)
        self.TxtMini.set_text('Memória')
        self.TxtMini.set_pos((area_slots.x, y_mem - 20))
        self.TxtMini.draw(tela)

        origem_oculta = self._slot_origem_oculto if self._arrastavel_ataque.Ativo else None
        for i in range(colunas_habilidades):
            rect_h = pygame.Rect(start_slots_x + i * (lado_slot + gap), y_hab, lado_slot, lado_slot)
            rect_m = pygame.Rect(start_slots_x + i * (lado_slot + gap), y_mem, lado_slot, lado_slot)
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

    def _desenhar_bloco_status(
        self,
        tela: pygame.Surface,
        rect: pygame.Rect,
        pokemon: dict | None,
        dt: float,
        stats: dict[str, float] | None = None,
        ivs: dict[str, float] | None = None,
    ):
        self._desenhar_setor(tela, rect)
        stats = stats or self._stats_dict(pokemon)
        ivs = ivs or self._ivs_dict(pokemon)

        self.TxtSetor.set_text('Atributos')
        self.TxtSetor.set_pos((rect.x + 14, rect.y + 14))
        self.TxtSetor.draw(tela)

        resumo_x = rect.right - 14
        resumo_y = rect.y + 8
        poder_total = self._poder_total(pokemon)
        iv_medio = self._iv_medio(pokemon)
        poder_rel = self._poder_relativo(pokemon)

        for rotulo, valor in reversed((
            ('Poder', str(poder_total)),
            ('Rel.', str(poder_rel)),
            ('IV', f'{iv_medio}%'),
        )):
            self.TxtMini.set_text(rotulo)
            self.TxtMini.set_pos((resumo_x - 56, resumo_y + 2))
            self.TxtMini.draw(tela)
            self.TxtResumo.set_text(valor)
            self.TxtResumo.set_pos((resumo_x - 56, resumo_y + 18))
            self.TxtResumo.draw(tela)
            resumo_x -= 82

        area_barras = pygame.Rect(rect.x + 12, rect.y + 72, rect.width - 24, rect.height - 84)
        col_w = max(28, area_barras.width // len(self._ordem_status))
        barra_h = max(88, area_barras.height - 48)
        barra_w = max(16, min(22, col_w - 12))

        for idx, status in enumerate(self._ordem_status):
            slot_x = area_barras.x + idx * col_w
            centro_x = slot_x + col_w // 2
            valor = float(stats.get(status, 0.0))
            iv = float(ivs.get(status, 0.0))
            if 0.0 <= iv <= 1.0:
                iv *= 100.0
            cor = self._cores_status.get(status, (110, 170, 255))
            maximo = self._max_barra_status(pokemon, status)
            if status == 'Vida':
                maximo *= 2.0

            self.TxtStatus.set_text(status)
            self.TxtStatus.set_pos((centro_x, area_barras.y))
            self.TxtStatus.draw(tela)
            self.TxtStatus.set_text(str(int(round(valor))))
            self.TxtStatus.set_pos((centro_x, area_barras.y + 14))
            self.TxtStatus.draw(tela)

            barra_rect = pygame.Rect(centro_x - barra_w // 2, area_barras.y + 32, barra_w, barra_h)
            barra_status = self._barras_status.get(status)
            if barra_status is None:
                barra_status = Barra((0, 0, 1, 1), texto='', valor=0, minimo=0, maximo=1, mostrar_rotulo=False, suavizacao=24.0, vertical=True)
            barra_status.configurar(
                rect=barra_rect,
                minimo=0.0,
                maximo=float(max(1.0, maximo)),
                cor_fundo=(21, 29, 48),
                cor_borda=(0, 0, 0),
                cor_preenchimento=cor,
                vertical=True,
                border_radius=0,
            )
            barra_status.set_valor(float(valor), animar=True)
            barra_status.render(tela, [], dt)
            self._barras_status[status] = barra_status

            self.TxtIV.set_text(f'IV {int(round(max(0.0, min(100.0, iv))))}%')
            self.TxtIV.set_pos((centro_x, barra_rect.bottom + 4))
            self.TxtIV.draw(tela)

    def _slot_no_mouse(self, pos) -> tuple[str, int] | None:
        for idx, rect in self._slots_build.items():
            if rect.collidepoint(pos):
                return ('build', idx)
        for chave, rect in self._slots_ataque.items():
            if rect.collidepoint(pos):
                return chave
        return None

    def area_animacao_rect(self):
        return pygame.Rect(self._area_animacao)

    def slot_build_no_mouse(self, pos):
        alvo = self._slot_no_mouse(pos)
        if alvo is None or alvo[0] != 'build':
            return None
        return alvo[1]

    def equipavel_no_slot(self, pokemon: dict | None, indice: int):
        build = self._build_ref(pokemon)
        if 0 <= int(indice) < len(build):
            return build[int(indice)]
        return None

    def definir_equipavel_slot(self, pokemon: dict | None, indice: int, equipavel: dict | None):
        if not isinstance(pokemon, dict):
            return None
        build = self._build_ref(pokemon)
        self._garantir_tamanho_lista(build, int(indice))
        anterior = build[int(indice)]
        build[int(indice)] = equipavel
        return anterior

    def retirar_equipavel_slot(self, pokemon: dict | None, indice: int):
        return self.definir_equipavel_slot(pokemon, indice, None)

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
            self._cancelar_arrasto()
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
        self.DoarSolicitado = False
        self.UparNivelSolicitado = False
        if self._botao_fechar is not None:
            self._botao_fechar.render(tela, eventos, dt, None)
        if self._botao_doar is not None:
            self._botao_doar.render(tela, eventos, dt, None)
        if self._botao_upar is not None:
            self._botao_upar.render(tela, eventos, dt, None)

        self._arrastavel_ataque.animar(dt)
        self._slot_hover = self._slot_no_mouse(pygame.mouse.get_pos())

        for evento in eventos:
            if evento.type == pygame.MOUSEMOTION and self._arrastavel_ataque.Ativo and self._arrastavel_ataque.PosAlvo is None:
                self._arrastavel_ataque.atualizar(evento.pos)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                destino = self._slot_no_mouse(evento.pos)
                if self._arrastavel_ataque.Ativo:
                    if self._arrastavel_ataque.PosAlvo is not None:
                        continue
                    origem = self._arrastavel_ataque.Origem
                    if origem is None or destino is None or origem == destino:
                        self._retornar_arrasto()
                    else:
                        self._trocar_ataques(pokemon, origem, destino)
                else:
                    if destino is not None and self._ataque_no_slot(pokemon, destino) is not None:
                        self._iniciar_arrasto_ataque(pokemon, destino, evento.pos)

    def _desenhar_arrastavel(self, tela: pygame.Surface):
        if self._arrastavel_ataque.Ativo and self._arrastavel_ataque.Item is not None:
            self._desenhar_slot_ataque(tela, self._arrastavel_ataque.Rect, self._arrastavel_ataque.Item, selecionado=True)

    def renderizar(self, tela: pygame.Surface, rect, pokemon: dict | None, eventos=None, dt: float = 0.0, desenhar_arrastavel: bool = True):
        rect = pygame.Rect(rect)
        self._garantir_layout(rect)
        self._desenhar_base(tela, rect)

        if pokemon is None:
            self.TxtVazio.set_pos((rect.x + 18, rect.y + 18))
            self.TxtVazio.draw(tela)
            if self._botao_fechar is not None:
                self._botao_fechar.base_rect.topleft = (rect.right - 52, rect.y + 12)
                self._botao_fechar.rect = pygame.Rect(self._botao_fechar.base_rect)
                self._botao_fechar.render(tela, eventos or [], dt, None)
            return

        if self._botao_fechar is not None:
            self._botao_fechar.base_rect.topleft = (rect.right - 52, rect.y + 12)
            self._botao_fechar.rect = pygame.Rect(self._botao_fechar.base_rect)
        left, right_top, right_bottom = self._setores(rect)

        if self._botao_doar is not None:
            btn_h = 30
            btn_w = left.width - 32
            base_y = left.bottom - ((btn_h * 2) + 8) - 10
            self._botao_doar.base_rect = pygame.Rect(left.x + 16, base_y + btn_h + 8, btn_w, btn_h)
            self._botao_doar.rect = pygame.Rect(self._botao_doar.base_rect)
        if self._botao_upar is not None:
            btn_h = 30
            btn_w = left.width - 32
            base_y = left.bottom - ((btn_h * 2) + 8) - 10
            self._botao_upar.base_rect = pygame.Rect(left.x + 16, base_y, btn_w, btn_h)
            self._botao_upar.rect = pygame.Rect(self._botao_upar.base_rect)
            xp_atual, xp_alvo = self._xp(pokemon)
            pode_upar = xp_atual >= xp_alvo
            self._botao_upar.set_habilitado(pode_upar)
            self._botao_upar.set_pulsando(pode_upar, cor=(188, 227, 140), cor_borda=(227, 255, 191), velocidade=2.0, intensidade=0.44)

        self._preparar_animacao_barras(pokemon)
        self._desenhar_cabecalho(tela, rect, pokemon)
        stats = self._stats_dict(pokemon)
        ivs = self._ivs_dict(pokemon)
        self._bloco_infos_esquerda(tela, left, pokemon, dt, stats=stats)
        self._desenhar_bloco_superior_direito(tela, right_top, pokemon)
        self._desenhar_bloco_status(tela, right_bottom, pokemon, dt, stats=stats, ivs=ivs)
        self._processar_eventos(tela, pokemon, eventos or [], dt)
        if desenhar_arrastavel:
            self._desenhar_arrastavel(tela)

        ataque_hover = self._ataque_no_slot(pokemon, self._slot_hover)
        if self._arrastavel_ataque.Ativo and self._arrastavel_ataque.Item is not None:
            ataque_hover = self._arrastavel_ataque.Item
        if ataque_hover is not None:
            self._ficha_ataque.renderizar_tooltip(tela, ataque_hover, area_ancora=right_bottom)
