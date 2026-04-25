from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pygame

from Codigo.Geradores.PokemonInventario import PokemonInventario


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
        p.Energia = max(0.0, round(p.EnergiaMax * 0.75, 2))
        return p

    def _aplicar_stats(self, stats: dict, stats_base: dict):
        chaves = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int", "CrD", "CrC"]
        for chave in chaves:
            base = _f(stats_base.get(chave, stats.get(chave, 0.0)), 0.0)
            atual = _f(stats.get(chave, base), base)
            self.AtributosBase[chave] = base
            self.Atributos[chave] = atual
            self.Variacoes[chave] = atual - base

        self.Atributos.setdefault("Amplificacao", 0.0)
        self.Atributos.setdefault("Durabilidade", 0.0)
        self.Atributos.setdefault("Vamp", 0.0)
        self.Atributos.setdefault("Acuracia", 100.0)
        self.Atributos.setdefault("Assertividade", 100.0)

        self.AtributosBase.setdefault("Amplificacao", 0.0)
        self.AtributosBase.setdefault("Durabilidade", 0.0)
        self.AtributosBase.setdefault("Vamp", 0.0)
        self.AtributosBase.setdefault("Acuracia", 100.0)
        self.AtributosBase.setdefault("Assertividade", 100.0)

        self.VidaMax = max(1.0, _f(self.Atributos.get("Vida", 1.0), 1.0))
        self.VidaAtual = self.VidaMax
        energia_raw = _f(self.Dados.get("EnergiaMaxima", self.Dados.get("EnergiaMax", 0.0)), 0.0)
        if energia_raw <= 0:
            energia_raw = _f(self.Atributos.get("EnergiaMaxima", self.Atributos.get("EneM", 0.0)), 0.0)
        if energia_raw <= 0:
            energia_raw = max(1.0, _f(self.Atributos.get("Ene", 1.0), 1.0) * 3.0)
        self.EnergiaMax = max(1.0, energia_raw)
        self.BarreiraAtual = _f(self.Dados.get("Barreira", self.Dados.get("barreira", 0.0)), 0.0)

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
        if not self.Ativo or self.EmReserva or not self.AreaId:
            return
        centro = arena.centro_area(self.AreaId)
        if centro is None:
            return
        cx, cy = camera.mundo_para_tela_px(centro)
        lado = max(46, int(getattr(camera, "TilePx", 40) * 1.7))
        img = None
        try:
            img = PokemonInventario.surface_pokemon(self.Dados, lado)
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

        if selecionado:
            pygame.draw.rect(surface, (255, 235, 90), self.RectAtual.inflate(8, 8), 3, border_radius=12)
        elif hover:
            pygame.draw.rect(surface, (240, 240, 240), self.RectAtual.inflate(4, 4), 2, border_radius=10)

    def desenhar_reserva(self, surface, rect_slot, selecionado=False, hover=False):
        base = pygame.Rect(rect_slot)
        cor = (26, 46, 74) if self.Lado == "jogador" else (74, 30, 30)
        pygame.draw.rect(surface, cor, base, border_radius=10)
        pygame.draw.rect(surface, (132, 172, 228), base, 2, border_radius=10)
        img = None
        lado = min(base.w, base.h) - 10
        try:
            img = PokemonInventario.surface_pokemon(self.Dados, lado)
        except Exception:
            img = None
        if img is not None:
            surface.blit(img, img.get_rect(midleft=(base.x + 6 + lado // 2, base.centery)))
        fonte = pygame.font.SysFont("arial", 14, bold=True)
        txt = fonte.render(self.Nome[:12], True, (245, 248, 255))
        surface.blit(txt, (base.x + lado + 10, base.y + 7))
        if selecionado:
            pygame.draw.rect(surface, (255, 235, 90), base.inflate(4, 4), 2, border_radius=10)
        elif hover:
            pygame.draw.rect(surface, (230, 230, 230), base.inflate(2, 2), 1, border_radius=10)
        self.RectAtual = base

    def desenhar_barras(self, surface):
        _ = surface

    def contem_ponto(self, pos_mouse):
        return self.RectAtual.collidepoint(pos_mouse)

    def esta_ativo(self):
        return bool(self.Ativo)

    def esta_na_reserva(self):
        return bool(self.EmReserva)

    def esta_vivo(self):
        return bool(self.Vivo)
