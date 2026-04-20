from __future__ import annotations

import csv
import math
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.ModulosGerais.Auxiliares import carregar_frames
from Codigo.Paineis.FichaPokemon import FichaPokemon

try:
    from Codigo.ModulosGerais.PokemonAnimator import PokemonAnimator
except Exception:
    PokemonAnimator = None

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class PokemonBatalha:
    _cache_frames: Dict[str, List[pygame.Surface]] = {}
    _cache_base_ataques: Dict[str, Dict[str, object]] | None = None

    _ORDEM_BASE = ("Atk", "Def", "Mag", "Vel", "SpA", "SpD", "Ene", "Per", "Int", "Vamp")
    _EXTRAS_PREFERIDOS = (
        "Vida",
        "EnergiaMaxima",
        "Amplificacao",
        "Durabilidade",
        "Peso",
        "Escala",
        "CrC",
        "CrD",
        "Barreira",
    )
    _MAPA_LABELS = {
        "vida": "Vida",
        "atk": "Atk",
        "def": "Def",
        "spa": "SpA",
        "spd": "SpD",
        "vel": "Vel",
        "mag": "Mag",
        "per": "Per",
        "ene": "Ene",
        "int": "Int",
        "vamp": "Vamp",
        "vampirismo": "Vamp",
        "peso": "Peso",
        "escala": "Escala",
        "energiamaxima": "EnergiaMaxima",
        "energiamax": "EnergiaMaxima",
        "amplificacao": "Amplificacao",
        "durabilidade": "Durabilidade",
        "crc": "CrC",
        "crd": "CrD",
        "barreira": "Barreira",
        "precisao": "Precisao",
    }

    def __init__(self, dados: Dict[str, object], posicao: Vector2, lado: str, regras: Dict[str, object] | None = None) -> None:
        self.Dados = dict(dados or {})
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Lado = str(lado or "jogador")
        self.Regras = dict(regras or {})
        self.Uid = str(self.Dados.get("uid") or self.Dados.get("id") or self.Dados.get("ID") or f"pokemon:temp:{id(self)}")
        self.Ativo = True
        self.SlotTime = 0
        self.SlotAtivo = 0
        self.ForaDeCombate = False
        self.EmReserva = False
        self.Barreira = 0.0
        self.PosicaoAnterior = self.Posicao
        self.VelocidadeAtualTilesTick = 0.0
        self.TamanhoTiles = 0.0
        self.RaioColisao = 0.0
        self.AtributosBase: dict[str, float] = {}
        self.AtributosAtuais: dict[str, float] = {}
        self.VariacoesFixas: dict[str, float] = {}
        self.VariacoesTemporarias: dict[str, float] = {}
        self.MultiplicadoresTemporarios: dict[str, float] = {}
        self.Flags: dict[str, object] = {}
        self.Efeitos: List[Dict[str, object]] = []
        self.Memorias: List[object] = []

        self._fontes = FichaPokemon._coletar_fontes(self.Dados)
        self._stats_brutos = self._coletar_stats_brutos()

        self.Nome, self.Especie = FichaPokemon._nome_especie(self.Dados)
        self.Peso = self._numero(self._valor('Peso', 'peso', default=0.0), 0.0)
        self.Escala = max(0, int(round(self._numero(self._valor('Escala', 'escala', default=FichaPokemon._escala(self.Dados)), 3.0))))
        self.CrC = self._numero(self._valor('CrC', 'CriticoChance', 'ChanceCritico', default=0.0), 0.0)
        self.CrD = self._numero(self._valor('CrD', 'CriticoDano', 'DanoCritico', default=0.0), 0.0)
        self.Tipos = list(FichaPokemon._tipos(self.Dados))
        self.Nivel = max(1, int(FichaPokemon._nivel(self.Dados) or 1))

        base_tamanho = self._numero(
            self.Regras.get('combate_pokemon_tamanho_diametro_base_tiles', self.Regras.get('pokemon_tamanho_diametro_base_tiles', 1.0)),
            1.0,
        )
        incremento = self._numero(
            self.Regras.get('combate_pokemon_tamanho_incremento_por_escala', self.Regras.get('pokemon_tamanho_incremento_por_escala', 0.1)),
            0.1,
        )
        self.DiametroTiles = max(0.4, base_tamanho + max(0.0, float(self.Escala)) * max(0.01, incremento))

        stats_principais = dict(FichaPokemon._stats_dict(self.Dados))
        self.VidaMax = max(
            1.0,
            self._numero(
                self._valor('VidaMax', 'Vida Máxima', 'MaxVida', 'MaxHP', default=stats_principais.get('Vida', 1.0)),
                stats_principais.get('Vida', 1.0),
            ),
        )
        self.VidaAtual = max(0.0, min(self.VidaMax, self._numero(FichaPokemon._vida_atual(self.Dados), self.VidaMax)))

        energia_base = max(1.0, self._numero(stats_principais.get('Ene', self._valor('Ene', 'EnergiaBase', default=1.0)), 1.0))
        energia_max_extraida = self._valor('EnergiaMaxima', 'EnergiaMax', 'Energia Máxima', 'MaxEnergia', default=None)
        self.EnergiaMax = max(1.0, self._numero(energia_max_extraida, energia_base * 3.0))
        self.Energia = max(0.0, min(self.EnergiaMax, self.EnergiaMax * 0.5))

        self.Stats = self._montar_stats_publicos(stats_principais)
        self.ListaAtaques = self._extrair_lista_ataques(self.Dados)
        self.ItensBuild = self._extrair_itens_build(self.Dados)
        self.VariacoesAtributos: dict[str, float] = {}
        for chave in self.Stats.keys():
            self.VariacoesAtributos[self._normalizar_chave_ficha(chave)] = 0.0
        self.Animador = PokemonAnimator(self) if PokemonAnimator is not None else None
        self.atualizar(self.Dados)

    @staticmethod
    def _normalizar_chave_ficha(chave: str) -> str:
        base = ''.join(
            c for c in unicodedata.normalize('NFKD', str(chave or '').strip().lower())
            if not unicodedata.combining(c)
        )
        for ch in (' ', '_', '-', '.', '/', '\\'):
            base = base.replace(ch, '')
        return base

    @classmethod
    def _label_publico(cls, chave: str) -> str:
        normalizada = cls._normalizar_chave_ficha(chave)
        if normalizada in cls._MAPA_LABELS:
            return cls._MAPA_LABELS[normalizada]
        bruto = str(chave or '').strip().replace('_', ' ')
        return bruto[:1].upper() + bruto[1:] if bruto else '-'

    @staticmethod
    def _numero(valor, default=0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @classmethod
    def _arquivo_base_ataques(cls) -> Path | None:
        atual = Path(__file__).resolve()
        candidatos = [
            atual.parents[2] / "Dados" / "Pokemon Global Server - Ataques.csv",
            atual.parents[2] / "Outros" / "Pokemon Global Server - Ataques.csv",
            Path("Dados") / "Pokemon Global Server - Ataques.csv",
            Path("Outros") / "Pokemon Global Server - Ataques.csv",
        ]
        for caminho in candidatos:
            if caminho.exists():
                return caminho
        return None

    @classmethod
    def _base_ataques(cls) -> Dict[str, Dict[str, object]]:
        if cls._cache_base_ataques is not None:
            return cls._cache_base_ataques
        cls._cache_base_ataques = {}
        caminho = cls._arquivo_base_ataques()
        if caminho is None:
            return cls._cache_base_ataques
        try:
            with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
                leitor = csv.DictReader(arquivo)
                for row in leitor:
                    nome = str(row.get("Ataque") or row.get("Nome") or "").strip()
                    if not nome:
                        continue
                    cls._cache_base_ataques[cls._normalizar_chave_ficha(nome)] = dict(row)
        except Exception:
            cls._cache_base_ataques = {}
        return cls._cache_base_ataques

    @classmethod
    def _enriquecer_ataque(cls, ataque: dict[str, object]) -> dict[str, object]:
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
        if not nome:
            return ataque
        base = dict(cls._base_ataques().get(cls._normalizar_chave_ficha(nome), {}))
        if base:
            base.update(ataque)
            ataque = base
        ataque.setdefault("Ataque", nome)
        ataque.setdefault("Nome", nome)
        ataque.setdefault("Tipo", str(ataque.get("Tipo") or ataque.get("tipo") or "Normal").strip() or "Normal")
        return ataque

    def _valor(self, *chaves, default=None):
        return FichaPokemon._valor_pokemon(self.Dados, *chaves, default=default)

    def _coletar_stats_brutos(self) -> dict[str, tuple[str, float]]:
        ignorar = {
            'nome', 'especie', 'nivel', 'xp', 'xpalvo', 'tipo', 'tipos', 'uid', 'id', 'estado', 'snapshot',
            'build', 'buildequipaveis', 'itensbuild', 'habilidades', 'ataques', 'moves', 'golpes', 'memoria',
            'altura', 'amizade', 'frutafavorita', 'grupo', 'estagio', 'tamanho', 'power', 'poder', 'poderrelativo',
        }
        saida: dict[str, tuple[str, float]] = {}
        for fonte in self._fontes:
            if not isinstance(fonte, dict):
                continue
            for chave, valor in fonte.items():
                normalizada = self._normalizar_chave_ficha(chave)
                if not normalizada or normalizada in ignorar:
                    continue
                if isinstance(valor, bool):
                    continue
                try:
                    numero = float(valor)
                except (TypeError, ValueError):
                    continue
                saida.setdefault(normalizada, (str(chave), numero))
        return saida

    def _montar_stats_publicos(self, stats_principais: dict[str, float]) -> dict[str, float]:
        stats: dict[str, float] = {}
        for chave, valor in stats_principais.items():
            stats[self._label_publico(chave)] = float(valor)

        complementos = {
            'Vida': self.VidaMax,
            'EnergiaMaxima': self.EnergiaMax,
            'Peso': self.Peso,
            'Escala': float(self.Escala),
            'CrC': self.CrC,
            'CrD': self.CrD,
            'Amplificacao': self._numero(self._valor('Amplificacao', 'Amplificação', default=self._stats_brutos.get('amplificacao', ('', 0.0))[1] if 'amplificacao' in self._stats_brutos else 0.0), 0.0),
            'Durabilidade': self._numero(self._valor('Durabilidade', default=self._stats_brutos.get('durabilidade', ('', 0.0))[1] if 'durabilidade' in self._stats_brutos else 0.0), 0.0),
            'Barreira': self._numero(self._valor('Barreira', default=self._stats_brutos.get('barreira', ('', 0.0))[1] if 'barreira' in self._stats_brutos else 0.0), 0.0),
            'Precisao': self._numero(self._valor('Precisao', 'Precisão', default=self._stats_brutos.get('precisao', ('', 0.0))[1] if 'precisao' in self._stats_brutos else 0.0), 0.0),
        }
        vamp = self._valor('Vamp', 'Vampirismo', default=self._stats_brutos.get('vamp', self._stats_brutos.get('vampirismo', ('', 0.0)))[1] if ('vamp' in self._stats_brutos or 'vampirismo' in self._stats_brutos) else 0.0)
        complementos['Vamp'] = self._numero(vamp, 0.0)

        for chave, valor in complementos.items():
            stats[chave] = float(valor)

        for normalizada, (original, valor) in self._stats_brutos.items():
            label = self._label_publico(original)
            stats.setdefault(label, float(valor))

        return stats

    @classmethod
    def _normalizar_ataque(cls, item) -> dict[str, object] | None:
        if item is None:
            return None
        if isinstance(item, dict):
            ataque = dict(item)
            nome = str(
                ataque.get('Ataque')
                or ataque.get('Nome')
                or ataque.get('nome')
                or ataque.get('Habilidade')
                or ataque.get('habilidade')
                or ataque.get('Move')
                or ataque.get('move')
                or ataque.get('Golpe')
                or ataque.get('golpe')
                or ''
            ).strip()
            if not nome:
                return None
            tipo = str(ataque.get('Tipo') or ataque.get('tipo') or 'Normal').strip() or 'Normal'
            ataque.setdefault('Ataque', nome)
            ataque.setdefault('Nome', nome)
            ataque.setdefault('Tipo', tipo)
            return cls._enriquecer_ataque(ataque)
        nome = str(item).strip()
        if not nome:
            return None
        return cls._enriquecer_ataque({'Ataque': nome, 'Nome': nome, 'Tipo': 'Normal'})

    @classmethod
    def _extrair_lista_ataques(cls, dados: Dict[str, object]) -> List[Dict[str, object]]:
        candidatos = FichaPokemon._habilidades_ref(dados)
        saida: List[Dict[str, object]] = []
        for item in candidatos:
            normalizado = cls._normalizar_ataque(item)
            if normalizado is not None:
                saida.append(normalizado)
        return saida

    @staticmethod
    def _extrair_itens_build(dados: Dict[str, object]) -> List[object]:
        build = FichaPokemon._build_ref(dados)
        if isinstance(build, list) and build:
            return list(build)
        estado = dados.get('estado') if isinstance(dados.get('estado'), dict) else dados
        candidatos = estado.get('build') or estado.get('itens_build') or dados.get('build') or []
        return list(candidatos) if isinstance(candidatos, list) else []

    def obter_valor_base_ficha(self, chave: str):
        normalizada = self._normalizar_chave_ficha(chave)
        mapa_direto = {
            'peso': self.Peso,
            'escala': self.Escala,
            'energiamaxima': self.EnergiaMax,
            'energiamax': self.EnergiaMax,
            'energiaatual': self.Energia,
            'energia': self.Energia,
            'vida': self.VidaMax,
            'vidaatual': self.VidaAtual,
            'crc': self.CrC,
            'crd': self.CrD,
        }
        if normalizada in mapa_direto:
            return mapa_direto[normalizada]

        for chave_publica, valor in self.Stats.items():
            if self._normalizar_chave_ficha(chave_publica) == normalizada:
                return valor
        return 0.0

    def obter_variacao_ficha(self, chave: str) -> float:
        normalizada = self._normalizar_chave_ficha(chave)
        return float(self.VariacoesAtributos.get(normalizada, 0.0))

    def definir_variacao_ficha(self, chave: str, valor: float) -> None:
        normalizada = self._normalizar_chave_ficha(chave)
        self.VariacoesAtributos[normalizada] = float(valor)

    def alterar_variacao_ficha(self, chave: str, delta: float) -> None:
        normalizada = self._normalizar_chave_ficha(chave)
        self.VariacoesAtributos[normalizada] = float(self.VariacoesAtributos.get(normalizada, 0.0) + float(delta))

    def obter_valor_ficha(self, chave: str):
        base = self.obter_valor_base_ficha(chave)
        try:
            return float(base) + self.obter_variacao_ficha(chave)
        except (TypeError, ValueError):
            return base

    def listar_atributos_extras_ficha(self, limite: int = 10) -> list[str]:
        escolhidos: list[str] = []
        usados = {self._normalizar_chave_ficha(ch) for ch in self._ORDEM_BASE}
        usados.update({'vidaatual', 'energiaatual'})

        for chave in self._EXTRAS_PREFERIDOS:
            if len(escolhidos) >= limite:
                break
            if self._normalizar_chave_ficha(chave) in usados:
                continue
            valor = self.obter_valor_ficha(chave)
            if valor not in (None, ''):
                escolhidos.append(chave)
                usados.add(self._normalizar_chave_ficha(chave))

        for chave_publica in self.Stats.keys():
            if len(escolhidos) >= limite:
                break
            normalizada = self._normalizar_chave_ficha(chave_publica)
            if normalizada in usados:
                continue
            escolhidos.append(chave_publica)
            usados.add(normalizada)

        return escolhidos[:limite]

    def montar_dados_ficha(self) -> Dict[str, object]:
        return {
            'nome': self.Nome,
            'especie': self.Especie,
            'nivel': self.Nivel,
            'tipos': list(self.Tipos),
            'ataques': list(self.ListaAtaques),
            'itens': list(self.ItensBuild),
            'vida_atual': self.VidaAtual,
            'vida_max': self.VidaMax,
            'energia_atual': self.Energia,
            'energia_max': self.EnergiaMax,
            'stats': dict(self.Stats),
        }

    def obter_ataques_ficha(self, limite: int | None = None) -> list[dict[str, object]]:
        ataques = list(self.ListaAtaques)
        return ataques if limite is None else ataques[: max(0, int(limite))]

    def obter_itens_ficha(self, limite: int | None = None) -> list[object]:
        itens = list(self.ItensBuild)
        return itens if limite is None else itens[: max(0, int(limite))]

    def atributos_texto_ataque(self) -> Dict[str, float]:
        return {str(chave): float(self.obter_valor_ficha(chave)) for chave in self.Stats.keys()}

    def atualizar(self, dados_servidor: Dict[str, object] | None = None) -> None:
        if not isinstance(dados_servidor, dict):
            return

        dados = dict(dados_servidor)
        self.Dados.update(dados)
        self.Uid = str(dados.get("uid") or dados.get("id") or dados.get("ID") or self.Uid or "")
        self.Nome = str(dados.get("nome") or dados.get("Nome") or self.Nome)
        self.Especie = str(dados.get("especie") or dados.get("Especie") or self.Especie)
        self.Lado = str(dados.get("lado") or self.Lado)
        self.Ativo = bool(dados.get("ativo", self.Ativo))
        slot_time = dados.get("slot_time", self.SlotTime)
        slot_ativo = dados.get("slot_ativo", self.SlotAtivo)
        self.SlotTime = int(self.SlotTime if slot_time is None else slot_time)
        self.SlotAtivo = int(self.SlotAtivo if slot_ativo is None else slot_ativo)
        self.ForaDeCombate = bool(dados.get("fora_de_combate", self.ForaDeCombate))
        self.Peso = self._numero(dados.get("peso", self.Peso), self.Peso)
        self.Escala = max(0, int(round(self._numero(dados.get("escala", self.Escala), self.Escala))))
        self.Barreira = self._numero(dados.get("barreira", self.Barreira), self.Barreira)
        self.Tipos = [str(item).strip() for item in list(dados.get("tipos") or self.Tipos) if str(item).strip()]
        self.ListaAtaques = [self._normalizar_ataque(item) or dict(item) for item in list(dados.get("habilidades") or dados.get("ataques") or self.ListaAtaques) if item]
        self.ListaAtaques = [item for item in self.ListaAtaques if isinstance(item, dict)]
        self.Habilidades = list(self.ListaAtaques)
        self.ItensBuild = list(dados.get("itens_build") or dados.get("build") or self.ItensBuild or [])
        self.Memorias = list(dados.get("memorias") or self.Memorias or [])
        self.Efeitos = [dict(item) for item in list(dados.get("efeitos") or []) if isinstance(item, dict)]
        self.Flags = dict(dados.get("flags") or self.Flags or {})
        self.MultiplicadoresTemporarios = {
            str(chave): float(valor)
            for chave, valor in dict(dados.get("multiplicadores_temporarios") or self.MultiplicadoresTemporarios or {}).items()
        }

        posicao = dados.get("posicao")
        if isinstance(posicao, (list, tuple)) and len(posicao) == 2:
            self.Posicao = (float(posicao[0]), float(posicao[1]))
        posicao_anterior = dados.get("posicao_anterior")
        if isinstance(posicao_anterior, (list, tuple)) and len(posicao_anterior) == 2:
            self.PosicaoAnterior = (float(posicao_anterior[0]), float(posicao_anterior[1]))

        self.VelocidadeAtualTilesTick = self._numero(
            dados.get("velocidade_atual_tiles_tick", self.VelocidadeAtualTilesTick),
            self.VelocidadeAtualTilesTick,
        )
        base_tamanho = self._numero(
            self.Regras.get('combate_pokemon_tamanho_diametro_base_tiles', self.Regras.get('pokemon_tamanho_diametro_base_tiles', 1.0)),
            1.0,
        )
        incremento = self._numero(
            self.Regras.get('combate_pokemon_tamanho_incremento_por_escala', self.Regras.get('pokemon_tamanho_incremento_por_escala', 0.1)),
            0.1,
        )
        self.DiametroTiles = max(0.4, base_tamanho + max(0.0, float(self.Escala)) * max(0.01, incremento))
        self.TamanhoTiles = max(0.0, self._numero(dados.get("tamanho_tiles", self.TamanhoTiles or self.DiametroTiles), self.DiametroTiles))
        self.DiametroTiles = self.TamanhoTiles
        self.RaioColisao = max(0.0, self._numero(dados.get("raio_colisao", self.RaioColisao or (self.TamanhoTiles * 0.5)), self.TamanhoTiles * 0.5))

        atributos_base_brutos = dict(dados.get("atributos_base") or {})
        atributos_atuais_brutos = dict(dados.get("atributos") or {})
        self.AtributosBase = {self._label_publico(chave): float(valor) for chave, valor in atributos_base_brutos.items()}
        self.AtributosAtuais = {self._label_publico(chave): float(valor) for chave, valor in atributos_atuais_brutos.items()}
        if self.AtributosBase:
            self.Stats = dict(self.AtributosBase)
        elif self.AtributosAtuais:
            self.Stats = dict(self.AtributosAtuais)

        self.VariacoesFixas = {self._label_publico(chave): float(valor) for chave, valor in dict(dados.get("variacoes_fixas") or {}).items()}
        self.VariacoesTemporarias = {self._label_publico(chave): float(valor) for chave, valor in dict(dados.get("variacoes_temporarias") or {}).items()}
        self.VariacoesAtributos = {}
        for chave in set(self.Stats.keys()) | set(self.VariacoesFixas.keys()) | set(self.VariacoesTemporarias.keys()) | set(self.AtributosAtuais.keys()):
            normalizada = self._normalizar_chave_ficha(chave)
            if self.AtributosBase:
                delta = float(self.VariacoesFixas.get(chave, 0.0)) + float(self.VariacoesTemporarias.get(chave, 0.0))
            else:
                delta = 0.0
                self.Stats.setdefault(chave, float(self.AtributosAtuais.get(chave, self.Stats.get(chave, 0.0))))
            self.VariacoesAtributos[normalizada] = delta

        vida_max = dados.get("vida_max")
        if vida_max is None and self.AtributosAtuais:
            vida_max = self.AtributosAtuais.get("Vida")
        self.VidaMax = max(1.0, self._numero(vida_max, self.VidaMax))
        self.VidaAtual = max(0.0, min(self.VidaMax, self._numero(dados.get("vida_atual", self.VidaAtual), self.VidaAtual)))

        energia_max = dados.get("energia_max")
        if energia_max is None and self.AtributosAtuais:
            energia_max = self.AtributosAtuais.get("Ene", self.EnergiaMax)
        self.EnergiaMax = max(1.0, self._numero(energia_max, self.EnergiaMax))
        self.Energia = max(0.0, min(self.EnergiaMax, self._numero(dados.get("energia", self.Energia), self.Energia)))
        if self.Animador is not None and not self.ForaDeCombate and self.VidaAtual > 0.0:
            self.Animador.restaurar_visual_corpo()

    @classmethod
    def _frames_especie(cls, especie: str) -> List[pygame.Surface]:
        chave = str(especie or '').strip().lower()
        if not chave:
            return []
        if chave in cls._cache_frames:
            return cls._cache_frames[chave]
        cls._cache_frames[chave] = carregar_frames(_PASTA_ANIMACOES / chave)
        return cls._cache_frames[chave]

    def _frame_atual(self, tamanho_px: int) -> pygame.Surface | None:
        frames = self._frames_especie(self.Especie)
        if not frames:
            return None
        idx = int((pygame.time.get_ticks() // 95) % max(1, len(frames)))
        base = frames[idx]
        w, h = base.get_size()
        if w <= 0 or h <= 0:
            return None
        k = float(tamanho_px) / float(max(w, h))
        return pygame.transform.smoothscale(base, (max(1, int(w * k)), max(1, int(h * k))))

    def raio_px(self, camera) -> int:
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        raio_tiles = self.RaioColisao or (self.DiametroTiles * 0.5)
        return max(12, int(tile_px * raio_tiles))

    def centro_tela(self, camera) -> Tuple[int, int]:
        if hasattr(camera, "batalha_para_tela_px"):
            px, py = camera.batalha_para_tela_px(self.Posicao)
        else:
            px, py = camera.mundo_para_tela_px(self.Posicao)
        return int(px), int(py)

    def _desenhar_corpo(self, tela: pygame.Surface, camera, centro: Tuple[int, int], raio: int, tile_px: int, *, selecionado: bool = False, hover: bool = False, alpha_extra: int = 255) -> bool:
        cor_circulo = (56, 90, 145) if self.Lado == 'jogador' else (144, 74, 74)
        camada = pygame.Surface((raio * 4, raio * 4), pygame.SRCALPHA)
        centro_local = (camada.get_width() // 2, camada.get_height() // 2)
        pygame.draw.circle(camada, (*cor_circulo, max(0, min(255, alpha_extra))), centro_local, raio)
        cor_borda = (22, 26, 34)
        largura_borda = max(2, int(tile_px * 0.06))
        if selecionado or hover:
            pulso = (pygame.time.get_ticks() % 900) / 900.0
            alpha = int((120 if selecionado else 84) + (115 if selecionado else 78) * abs(0.5 - pulso) * 2.0)
            brilho = pygame.Surface((raio * 3, raio * 3), pygame.SRCALPHA)
            pygame.draw.circle(
                brilho,
                (255, 248, 190, alpha),
                (brilho.get_width() // 2, brilho.get_height() // 2),
                raio,
                max(largura_borda + (3 if selecionado else 2), 4),
            )
            tela.blit(brilho, brilho.get_rect(center=centro))
            cor_borda = (244, 238, 178)
        pygame.draw.circle(camada, (*cor_borda, max(0, min(255, alpha_extra))), centro_local, raio, largura_borda)

        frame = self._frame_atual(int(raio * 1.40))
        if frame is not None:
            frame = frame.copy()
            if alpha_extra < 255:
                frame.fill((255, 255, 255, max(0, min(255, alpha_extra))), special_flags=pygame.BLEND_RGBA_MULT)
            camada.blit(frame, frame.get_rect(center=(centro_local[0], centro_local[1] - int(raio * 0.08))))

        offset_px = (0, 0)
        oculto = False
        if self.Animador is not None:
            camada, offset_px, oculto = self.Animador.preparar_corpo_visual(camada, camera)
        if oculto:
            return False
        centro_final = (int(centro[0] + offset_px[0]), int(centro[1] + offset_px[1]))
        tela.blit(camada, camada.get_rect(center=centro_final))
        return True

    def renderizar(self, tela: pygame.Surface, camera, selecionado: bool = False, hover: bool = False, energia_reservada: float = 0.0) -> None:
        if self.Animador is not None:
            self.Animador.atualizar()
        centro = self.centro_tela(camera)
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        raio = self.raio_px(camera)
        corpo_desenhado = self._desenhar_corpo(tela, camera, centro, raio, tile_px, selecionado=selecionado, hover=hover, alpha_extra=255)
        if self.Animador is not None:
            self.Animador.renderizar(tela, camera)
        if corpo_desenhado:
            self._desenhar_barras(tela, centro, raio, tile_px, energia_reservada=energia_reservada)

    def renderizar_construto(self, tela: pygame.Surface, camera, posicao_mundo, *, alpha: int = 96) -> None:
        if not isinstance(posicao_mundo, (tuple, list)) or len(posicao_mundo) != 2:
            return
        if hasattr(camera, "batalha_para_tela_px"):
            px, py = camera.batalha_para_tela_px((float(posicao_mundo[0]), float(posicao_mundo[1])))
        else:
            px, py = camera.mundo_para_tela_px((float(posicao_mundo[0]), float(posicao_mundo[1])))
        centro = (int(px), int(py))
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        raio = self.raio_px(camera)
        sombra = pygame.Surface((raio * 5, raio * 5), pygame.SRCALPHA)
        centro_local = (sombra.get_width() // 2, sombra.get_height() // 2)
        pygame.draw.circle(sombra, (255, 255, 255, max(20, int(alpha * 0.18))), centro_local, int(raio * 1.08), 2)
        pygame.draw.circle(sombra, (255, 255, 255, max(10, int(alpha * 0.10))), centro_local, int(raio * 0.90))
        tela.blit(sombra, sombra.get_rect(center=centro))
        self._desenhar_corpo(tela, camera, centro, raio, tile_px, selecionado=False, alpha_extra=max(24, min(180, int(alpha))))

    @staticmethod
    def _desenhar_reserva_arredondada(tela: pygame.Surface, rect_barra: pygame.Rect, inicio_t: float, fim_t: float, cor_rgba: tuple[int, int, int, int]) -> None:
        if rect_barra.width <= 2 or rect_barra.height <= 0:
            return
        x_inicio = rect_barra.x + int(rect_barra.width * max(0.0, min(1.0, inicio_t)))
        x_fim = rect_barra.x + int(rect_barra.width * max(0.0, min(1.0, fim_t)))
        largura = max(1, x_fim - x_inicio)
        overlay = pygame.Surface((largura, rect_barra.height), pygame.SRCALPHA)
        pygame.draw.rect(overlay, cor_rgba, overlay.get_rect(), border_radius=max(1, rect_barra.height // 2))
        tela.blit(overlay, (x_inicio, rect_barra.y))

    def _desenhar_barras(self, tela: pygame.Surface, centro: Tuple[int, int], raio: int, tile_px: int, energia_reservada: float = 0.0) -> None:
        largura = max(24, int(tile_px * self.DiametroTiles * 1.25))
        vida_h = max(8, int(tile_px * 0.20))
        ene_h = max(2, int(vida_h * 0.44))
        espaco = max(1, int(tile_px * 0.05))
        topo = int(centro[1] - raio - (tile_px * 0.38))
        x = int(centro[0] - largura * 0.5)

        rect_vida = pygame.Rect(x, topo, largura, vida_h)
        rect_ene = pygame.Rect(x, topo + vida_h + espaco, largura, ene_h)

        pygame.draw.rect(tela, (0, 0, 0), rect_vida, border_radius=max(2, vida_h // 3))
        inner_vida = rect_vida.inflate(-2, -2)
        pygame.draw.rect(tela, (34, 44, 34), inner_vida, border_radius=max(2, inner_vida.height // 3))
        vida_t = 0.0 if self.VidaMax <= 0 else max(0.0, min(1.0, self.VidaAtual / self.VidaMax))
        if vida_t > 0.001 and inner_vida.width > 2:
            fill_vida = pygame.Rect(inner_vida.x, inner_vida.y, max(1, int(inner_vida.width * vida_t)), inner_vida.height)
            pygame.draw.rect(tela, (52, 205, 72), fill_vida, border_radius=max(2, inner_vida.height // 3))

        total_marcas = max(0, int(self.VidaMax // 30.0))
        for indice in range(1, total_marcas + 1):
            vida_marca = float(indice * 30.0)
            if vida_marca >= self.VidaMax:
                break
            marca_x = inner_vida.x + int(inner_vida.width * (vida_marca / self.VidaMax))
            pygame.draw.line(tela, (0, 0, 0), (marca_x, inner_vida.y), (marca_x, inner_vida.y + inner_vida.height), 1)

        pygame.draw.rect(tela, (0, 0, 0), rect_ene, border_radius=max(1, ene_h // 2))
        inner_ene = rect_ene.inflate(-2, -2)
        pygame.draw.rect(tela, (20, 46, 80), inner_ene, border_radius=max(1, inner_ene.height // 2))
        ene_t = 0.0 if self.EnergiaMax <= 0 else max(0.0, min(1.0, self.Energia / self.EnergiaMax))
        if ene_t > 0.001 and inner_ene.width > 2:
            fill_ene = pygame.Rect(inner_ene.x, inner_ene.y, max(1, int(inner_ene.width * ene_t)), inner_ene.height)
            pygame.draw.rect(tela, (60, 150, 255), fill_ene, border_radius=max(1, inner_ene.height // 2))
        reservado = max(0.0, min(float(energia_reservada or 0.0), max(0.0, self.Energia)))
        if reservado > 0.001 and inner_ene.width > 2 and self.EnergiaMax > 0:
            inicio_t = max(0.0, min(1.0, (self.Energia - reservado) / self.EnergiaMax))
            fim_t = max(0.0, min(1.0, self.Energia / self.EnergiaMax))
            alpha_pulso = int(90 + 90 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 120.0)))
            self._desenhar_reserva_arredondada(tela, inner_ene, inicio_t, fim_t, (255, 255, 255, alpha_pulso))
