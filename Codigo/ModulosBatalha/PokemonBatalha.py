from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import unicodedata

import pygame

from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.ModulosGerais.Auxiliares import carregar_frames


def _f(valor, default=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _i(valor, default=0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


@dataclass
class PokemonBatalha:
    _PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"
    _MAPA_ANIMACOES: dict[str, Path] | None = None
    id_batalha: str
    id_original: Any = None
    Nome: str = "Pokemon"
    Especie: str = "Pokemon"
    Nivel: int = 1
    lado_id: int = 50
    Lado: str = "jogador"
    Ativo: bool = False
    EmReserva: bool = False
    Vivo: bool = True
    AreaId: str | None = None
    Dados: dict[str, Any] = field(default_factory=dict)
    AtributosBase: dict[str, float] = field(default_factory=dict)
    Atributos: dict[str, float] = field(default_factory=dict)
    Variacoes: dict[str, float] = field(default_factory=dict)
    VidaAtual: float = 1.0
    VidaMax: float = 1.0
    Energia: float = 1.0
    EnergiaMax: float = 1.0
    BarreiraAtual: float = 0.0
    Tipos: list[str] = field(default_factory=list)
    ListaAtaques: list[dict[str, Any]] = field(default_factory=list)
    RectAtual: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    Frames: list[pygame.Surface] = field(default_factory=list)
    FrameAtual: int = 0
    TempoFrame: float = 1.0 / 8.0
    TimerAnimacao: float = 0.0
    SpriteFallback: pygame.Surface | None = None
    _cache_frames_escalados: dict[int, list[pygame.Surface]] = field(default_factory=dict)
    _carregamento_frames_tentado: bool = False

    @classmethod
    def from_serializado(cls, dados):
        bruto = dict(dados or {})
        info = dict(bruto.get("dados") or {})
        estado = info.get("estado") if isinstance(info.get("estado"), dict) else {}
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else info.get("stats") if isinstance(info.get("stats"), dict) else {}
        stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else info.get("stats_base") if isinstance(info.get("stats_base"), dict) else {}

        p = cls(
            id_batalha=str(bruto.get("id_batalha") or "00000"),
            id_original=bruto.get("id_original") if bruto.get("id_original") is not None else info.get("id"),
            Nome=str(info.get("nome") or info.get("Nome") or bruto.get("nome") or bruto.get("especie") or "Pokemon"),
            Especie=str(info.get("especie") or info.get("Especie") or bruto.get("especie") or "Pokemon"),
            Nivel=_i(info.get("nivel", info.get("Nivel", 1)), 1),
            lado_id=_i(bruto.get("lado_id", 50), 50),
            Lado=str(bruto.get("lado_visual") or ("jogador" if _i(bruto.get("lado_id", 50), 50) == 50 else "inimigo")),
            Ativo=bool(bruto.get("ativo", False)),
            EmReserva=bool(bruto.get("em_reserva", False)),
            Vivo=bool(bruto.get("vivo", True)),
            AreaId=bruto.get("area_id"),
            Dados=info,
            AtributosBase={},
            Atributos={},
            Variacoes={},
            Tipos=list(info.get("tipos") or estado.get("tipos") or []),
            ListaAtaques=list(bruto.get("ataques") or []),
        )
        p._aplicar_stats(stats, stats_base)
        p._carregar_animacao()
        return p

    def _aplicar_stats(self, stats: dict, stats_base: dict):
        aliases = {"Amplificacao": "Amp", "Durabilidade": "Dur"}
        chaves = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int", "CrD", "CrC", "Amp", "Dur", "Vamp", "Acuracia", "Assertividade", "EneM"]
        variacoes_brutas = self.Dados.get("variacoes")
        if not isinstance(variacoes_brutas, dict):
            variacoes_brutas = self.Dados.get("Variacoes") if isinstance(self.Dados.get("Variacoes"), dict) else {}
        for chave in chaves:
            chave_stats = chave
            if chave in ("Amp", "Dur"):
                alt = "Amplificacao" if chave == "Amp" else "Durabilidade"
                chave_stats = chave if chave in stats or chave in stats_base else alt
            base = _f(stats_base.get(chave_stats, stats.get(chave_stats, 0.0)), 0.0)
            atual = _f(stats.get(chave_stats, base), base)
            self.AtributosBase[chave] = base
            self.Atributos[chave] = atual
            self.Variacoes[chave] = _f(variacoes_brutas.get(chave, 0.0), 0.0)

        for alias_antigo, oficial in aliases.items():
            if oficial in self.Atributos:
                self.Atributos[alias_antigo] = self.Atributos[oficial]
                self.AtributosBase[alias_antigo] = self.AtributosBase.get(oficial, 0.0)
                self.Variacoes[alias_antigo] = self.Variacoes.get(oficial, 0.0)

        self.VidaMax = max(1.0, _f(self.Atributos.get("Vida", 1.0), 1.0))
        vida_atual = self.Dados.get("VidaAtual", self.Dados.get("vida_atual", self.Dados.get("vidaAtual", None)))
        if vida_atual is None and isinstance(self.Dados.get("estado"), dict):
            est = self.Dados.get("estado")
            vida_atual = est.get("VidaAtual", est.get("vida_atual", est.get("vidaAtual", None)))
        self.VidaAtual = max(0.0, min(self.VidaMax, _f(vida_atual, self.VidaMax)))

        energia_raw = _f(self.Dados.get("EnergiaMaxima", self.Dados.get("EnergiaMax", self.Dados.get("EneM", 0.0))), 0.0)
        if energia_raw <= 0:
            energia_raw = _f(self.Atributos.get("EnergiaMaxima", self.Atributos.get("EneM", 0.0)), 0.0)
        if energia_raw <= 0:
            energia_raw = max(1.0, _f(self.Atributos.get("Ene", 1.0), 1.0) * 3.0)
        self.EnergiaMax = max(1.0, energia_raw)
        energia_atual = self.Dados.get("EnergiaAtual", self.Dados.get("energia_atual", self.Dados.get("energiaAtual", None)))
        if energia_atual is None and isinstance(self.Dados.get("estado"), dict):
            est = self.Dados.get("estado")
            energia_atual = est.get("EnergiaAtual", est.get("energia_atual", est.get("energiaAtual", None)))
        energia_padrao = round(self.EnergiaMax * 0.75, 2)
        self.Energia = max(0.0, min(self.EnergiaMax, _f(energia_atual, energia_padrao)))

        self.BarreiraAtual = _f(self.Dados.get("BarreiraAtual", self.Dados.get("Barreira", self.Dados.get("barreira", 0.0))), 0.0)

        peso = self.Dados.get("peso", self.Dados.get("Peso"))
        escala = self.Dados.get("escala", self.Dados.get("Escala"))
        if peso is not None:
            self.Atributos["Peso"] = _f(peso, 0.0)
            self.AtributosBase["Peso"] = _f(peso, 0.0)
            self.Variacoes["Peso"] = 0.0
        if escala is not None:
            self.Atributos["Escala"] = _f(escala, 0.0)
            self.AtributosBase["Escala"] = _f(escala, 0.0)
            self.Variacoes["Escala"] = 0.0

    def _carregar_animacao(self):
        if self._carregamento_frames_tentado:
            return
        self._carregamento_frames_tentado = True

        info = self.Dados if isinstance(self.Dados, dict) else {}
        frames = []

        especie = str(self.Especie or info.get("especie") or info.get("Especie") or self.Nome or "").strip()
        pasta_anim = self._pasta_animacao_por_especie(especie)
        if pasta_anim is not None:
            try:
                frames = carregar_frames(pasta_anim)
            except Exception:
                frames = []

        if not frames:
            pistas = [
                info.get("CaminhoFrames"),
                info.get("caminho_frames"),
                info.get("FramesPath"),
                info.get("frames_path"),
                info.get("SpriteFrames"),
                info.get("sprite_frames"),
            ]
            for pista in pistas:
                if not pista:
                    continue
                pasta = Path(str(pista))
                if pasta.exists() and pasta.is_dir():
                    try:
                        frames = carregar_frames(pasta)
                    except Exception:
                        frames = []
                if frames:
                    break
        self.Frames = [f for f in frames if isinstance(f, pygame.Surface)]

    @classmethod
    def _normalizar_nome_especie(cls, nome: str) -> str:
        base = "".join(
            c for c in unicodedata.normalize("NFKD", str(nome or "").lower())
            if not unicodedata.combining(c)
        )
        for ch in ("_", "-", "'", ".", ":", ";", ","):
            base = base.replace(ch, " ")
        return " ".join(base.split())

    @classmethod
    def _mapa_animacoes(cls) -> dict[str, Path]:
        if cls._MAPA_ANIMACOES is not None:
            return cls._MAPA_ANIMACOES
        mapa: dict[str, Path] = {}
        if cls._PASTA_ANIMACOES.exists():
            for pasta in cls._PASTA_ANIMACOES.iterdir():
                if not pasta.is_dir():
                    continue
                chave = cls._normalizar_nome_especie(pasta.name)
                if chave and chave not in mapa:
                    mapa[chave] = pasta
        cls._MAPA_ANIMACOES = mapa
        return cls._MAPA_ANIMACOES

    @classmethod
    def _pasta_animacao_por_especie(cls, especie: str) -> Path | None:
        chave = cls._normalizar_nome_especie(especie)
        if not chave:
            return None
        mapa = cls._mapa_animacoes()
        if chave in mapa:
            return mapa[chave]
        chave_sem_espaco = chave.replace(" ", "")
        for nome_norm, pasta in mapa.items():
            if nome_norm.replace(" ", "") == chave_sem_espaco:
                return pasta
        return None

    def atualizar_animacao(self, dt: float):
        if not self.Frames:
            return
        self.TimerAnimacao += max(0.0, float(dt))
        while self.TimerAnimacao >= self.TempoFrame:
            self.TimerAnimacao -= self.TempoFrame
            self.FrameAtual = (self.FrameAtual + 1) % len(self.Frames)

    def _frame_atual_escalado(self, lado: int):
        if not self.Frames:
            return None
        lado = int(max(8, lado))
        if lado not in self._cache_frames_escalados:
            self._cache_frames_escalados[lado] = [
                pygame.transform.smoothscale(frame, (lado, lado)).convert_alpha()
                for frame in self.Frames
            ]
        frames = self._cache_frames_escalados.get(lado) or []
        if not frames:
            return None
        idx = self.FrameAtual % len(frames)
        return frames[idx]

    def serializar(self):
        return {
            "id_batalha": self.id_batalha,
            "id_original": self.id_original,
            "lado_id": self.lado_id,
            "lado_visual": self.Lado,
            "ativo": self.Ativo,
            "em_reserva": self.EmReserva,
            "vivo": self.Vivo,
            "area_id": self.AreaId,
            "dados": self.Dados,
            "ataques": list(self.ListaAtaques),
        }

    def atualizar_por_diff(self, diff):
        _ = diff

    def obter_ataques_ficha(self, limite=5):
        return list(self.ListaAtaques or [])[: max(0, int(limite or 5))]

    def obter_valor_ficha(self, chave):
        k = str(chave)
        if k in ("Barreira", "BarreiraAtual"):
            return self.BarreiraAtual
        if k in self.Atributos:
            return self.Atributos[k]
        if k == "EnergiaMaxima":
            return self.EnergiaMax
        if k == "Vida":
            return self.VidaMax
        if k == "Precisao":
            return self.Atributos.get("Per", 0.0)
        return 0.0

    def obter_valor_base_ficha(self, chave):
        return self.AtributosBase.get(str(chave), self.obter_valor_ficha(chave))

    def obter_variacao_ficha(self, chave):
        return self.Variacoes.get(str(chave), self.obter_valor_ficha(chave) - self.obter_valor_base_ficha(chave))

    def atributos_texto_ataque(self):
        return {
            "Energia": self.Energia,
            "EnergiaMax": self.EnergiaMax,
            "Atk": self.Atributos.get("Atk", 0.0),
            "SpA": self.Atributos.get("SpA", 0.0),
            "Mag": self.Atributos.get("Mag", 0.0),
            "Per": self.Atributos.get("Per", 0.0),
            "Vel": self.Atributos.get("Vel", 0.0),
            "Acuracia": self.Atributos.get("Acuracia", 100.0),
            "Assertividade": self.Atributos.get("Assertividade", 100.0),
        }

    def obter_itens_ficha(self, limite=3):
        _ = limite
        return []

    def desenhar(self, surface, camera, arena, selecionado=False, hover=False):
        _ = (selecionado, hover)
        if not self.Ativo or self.EmReserva or not self.AreaId:
            return
        centro = arena.centro_area(self.AreaId)
        if centro is None:
            return
        cx, cy = camera.mundo_para_tela_px(centro)
        lado = max(46, int(getattr(camera, "TilePx", 40) * 1.7))
        img = self._frame_atual_escalado(lado)
        if img is None:
            try:
                if self.SpriteFallback is None:
                    self.SpriteFallback = PokemonInventario.surface_pokemon(self.Dados, lado)
                elif self.SpriteFallback.get_width() != lado:
                    self.SpriteFallback = pygame.transform.smoothscale(self.SpriteFallback, (lado, lado))
                img = self.SpriteFallback
            except Exception:
                img = None
        if img is None:
            cor = (110, 196, 126) if self.Lado == "jogador" else (204, 108, 108)
            pygame.draw.circle(surface, cor, (int(cx), int(cy)), lado // 2)
            fonte = pygame.font.SysFont("arial", max(16, lado // 4), bold=True)
            txt = fonte.render(str(self.Nome)[:3].upper(), True, (20, 20, 20))
            surface.blit(txt, txt.get_rect(center=(int(cx), int(cy))))
            self.RectAtual = pygame.Rect(int(cx - lado // 2), int(cy - lado // 2), lado, lado)
        else:
            rect = img.get_rect(center=(int(cx), int(cy)))
            surface.blit(img, rect)
            self.RectAtual = pygame.Rect(rect)
        self.desenhar_barras(surface)

    def desenhar_reserva(self, surface, rect_slot, selecionado=False, hover=False):
        _ = (selecionado, hover)
        base = pygame.Rect(rect_slot)
        img = None
        lado = min(base.w, base.h) - 8
        img = self._frame_atual_escalado(lado)
        if img is None:
            try:
                img = PokemonInventario.surface_pokemon(self.Dados, lado)
            except Exception:
                img = None
        if img is not None:
            surface.blit(img, img.get_rect(center=base.center))
        self.RectAtual = base

    def desenhar_barras(self, surface):
        if self.RectAtual.width <= 0 or self.RectAtual.height <= 0:
            return
        vida_max = max(1.0, float(self.VidaMax))
        ene_max = max(1.0, float(self.EnergiaMax))
        vida_t = max(0.0, min(1.0, float(self.VidaAtual) / vida_max))
        ene_t = max(0.0, min(1.0, float(self.Energia) / ene_max))

        barra_w = max(46, int(self.RectAtual.width * 0.92))
        vida_h = max(8, int(self.RectAtual.height * 0.14))
        ene_h = max(4, int(vida_h * 0.5))
        x = self.RectAtual.centerx - barra_w // 2
        y = self.RectAtual.y - vida_h - ene_h - 8
        rect_vida = pygame.Rect(x, y, barra_w, vida_h)
        rect_ene = pygame.Rect(x, y + vida_h + 3, barra_w, ene_h)

        pygame.draw.rect(surface, (14, 18, 24), rect_vida, border_radius=max(3, vida_h // 2))
        pygame.draw.rect(surface, (24, 28, 35), rect_ene, border_radius=max(2, ene_h // 2))
        pygame.draw.rect(surface, (44, 190, 88), pygame.Rect(rect_vida.x, rect_vida.y, int(rect_vida.w * vida_t), rect_vida.h), border_radius=max(3, vida_h // 2))
        pygame.draw.rect(surface, (74, 148, 255), pygame.Rect(rect_ene.x, rect_ene.y, int(rect_ene.w * ene_t), rect_ene.h), border_radius=max(2, ene_h // 2))
        pygame.draw.rect(surface, (230, 236, 244), rect_vida, 1, border_radius=max(3, vida_h // 2))
        pygame.draw.rect(surface, (230, 236, 244), rect_ene, 1, border_radius=max(2, ene_h // 2))

        if vida_max >= 30:
            setores = int(vida_max // 30)
            for i in range(1, setores + 1):
                tx = rect_vida.x + int(rect_vida.w * ((i * 30) / vida_max))
                if rect_vida.x < tx < rect_vida.right:
                    pygame.draw.line(surface, (0, 0, 0), (tx, rect_vida.y + 1), (tx, rect_vida.bottom - 1), 1)

    def contem_ponto(self, pos_mouse):
        return self.RectAtual.collidepoint(pos_mouse)

    def esta_ativo(self):
        return bool(self.Ativo)

    def esta_na_reserva(self):
        return bool(self.EmReserva)

    def esta_vivo(self):
        return bool(self.Vivo)
