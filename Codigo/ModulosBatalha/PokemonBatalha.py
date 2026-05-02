from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any
import unicodedata

import pygame
from Codigo.Visual.PokemonBatalhaEstado import PokemonBatalhaEstado



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


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())




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
    EnergiaPrevista: float = 0.0
    CustoPrevistoPendente: float = 0.0
    PodePagarPrevisao: bool = True
    Tipos: list[str] = field(default_factory=list)
    ListaAtaques: list[dict[str, Any]] = field(default_factory=list)
    RectAtual: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    Frames: list[pygame.Surface] = field(default_factory=list)
    FrameAtual: int = 0
    TempoFrame: float = 1.0 / 8.0
    TimerAnimacao: float = 0.0
    _cache_frames_escalados: dict[int, list[pygame.Surface]] = field(default_factory=dict)
    _carregamento_frames_tentado: bool = False
    EfeitosFormais: list[dict[str, Any]] = field(default_factory=list)
    AnimacoesEfeitos: dict[str, float] = field(default_factory=dict)
    EfeitosSaindo: dict[str, float] = field(default_factory=dict)
    AnimacoesStatus: list[dict[str, Any]] = field(default_factory=list)
    TempoVisualEfeitos: float = 0.0
    CentroMundoOverride: tuple[float, float] | None = None
    CentroTelaOverride: tuple[float, float] | None = None
    OffsetVisual: tuple[float, float] = (0.0, 0.0)
    AlphaVisual: int = 255
    RotacaoVisual: float = 0.0
    FlashVisualCor: tuple[int, int, int] = (255, 255, 255)
    FlashVisualAlpha: int = 0
    Estado: PokemonBatalhaEstado = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.Estado = PokemonBatalhaEstado(self)

    def __getattr__(self, nome):
        estado = self.__dict__.get("Estado")
        if estado is not None and getattr(type(estado), nome, None) is not None:
            return getattr(estado, nome)
        raise AttributeError(nome)

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
            Nivel=max(1, _i(info.get("nivel", info.get("Nivel", 1)), 1)),
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
        if isinstance(bruto.get("Variacoes"), dict) and not isinstance(info.get("variacoes"), dict):
            p.Dados["variacoes"] = dict(bruto.get("Variacoes") or {})
        p._aplicar_stats(stats, stats_base)
        p.EfeitosFormais = list(bruto.get("efeitos") or info.get("efeitos") or [])
        p.Estado.carregar_animacao()
        return p

    def definir_intervalo_frame_ms(self, intervalo_ms: float | int | None):
        self.Estado.definir_intervalo_frame_ms(intervalo_ms)

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
            variacao_real = atual - base
            self.AtributosBase[chave] = base
            self.Atributos[chave] = atual
            variacao = _f(variacoes_brutas.get(chave, 0.0), 0.0)
            self.Variacoes[chave] = variacao_real if abs(variacao) < 0.001 and abs(variacao_real) > 0.001 else variacao

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
        vida_atual = _f(vida_atual, self.VidaMax)
        if 0.0 <= vida_atual <= 1.0:
            vida_atual *= self.VidaMax
        self.VidaAtual = max(0.0, min(self.VidaMax, vida_atual))

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
        self.EnergiaPrevista = float(self.Energia)
        self.CustoPrevistoPendente = 0.0
        self.PodePagarPrevisao = True

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

    def _sincronizar_alias_atributos(self):
        aliases = {"Amplificacao": "Amp", "Durabilidade": "Dur"}
        for alias, oficial in aliases.items():
            if oficial in self.Atributos:
                self.Atributos[alias] = self.Atributos[oficial]
            elif alias in self.Atributos:
                self.Atributos[oficial] = self.Atributos[alias]
            if oficial in self.AtributosBase:
                self.AtributosBase[alias] = self.AtributosBase[oficial]
            elif alias in self.AtributosBase:
                self.AtributosBase[oficial] = self.AtributosBase[alias]
            if oficial in self.Variacoes:
                self.Variacoes[alias] = self.Variacoes[oficial]
            elif alias in self.Variacoes:
                self.Variacoes[oficial] = self.Variacoes[alias]

    def _carregar_animacao(self):
        self.Estado.carregar_animacao()

    def atualizar_animacao(self, dt: float):
        self.Estado.atualizar_animacao(dt)

    def _frame_atual_escalado(self, camera):
        return self.Estado.frame_atual_escalado(camera)

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
        if not isinstance(diff, dict):
            return
        self.Vivo = bool(diff.get("Vivo", diff.get("vivo", self.Vivo)))
        self.Ativo = bool(diff.get("Ativo", diff.get("ativo", self.Ativo)))
        self.EmReserva = bool(diff.get("EmReserva", diff.get("em_reserva", self.EmReserva)))
        self.AreaId = diff.get("AreaId", diff.get("area_id", self.AreaId))
        self.VidaAtual = _f(diff.get("VidaAtual", self.VidaAtual), self.VidaAtual)
        self.VidaMax = max(1.0, _f(diff.get("VidaMax", self.VidaMax), self.VidaMax))
        self.Energia = _f(diff.get("Energia", diff.get("EnergiaAtual", self.Energia)), self.Energia)
        self.EnergiaMax = max(1.0, _f(diff.get("EnergiaMax", diff.get("EnergiaMaxima", self.EnergiaMax)), self.EnergiaMax))
        self.BarreiraAtual = max(0.0, _f(diff.get("BarreiraAtual", self.BarreiraAtual), self.BarreiraAtual))
        if isinstance(diff.get("Atributos"), dict):
            self.Atributos = {str(k): _f(v, 0.0) for k, v in diff.get("Atributos").items()}
        if isinstance(diff.get("AtributosBase"), dict):
            self.AtributosBase = {str(k): _f(v, 0.0) for k, v in diff.get("AtributosBase").items()}
        if isinstance(diff.get("Variacoes"), dict):
            self.Variacoes = {str(k): _f(v, 0.0) for k, v in diff.get("Variacoes").items()}
        if isinstance(diff.get("Tipos"), list):
            self.Tipos = list(diff.get("Tipos") or [])
        if isinstance(diff.get("ListaAtaques"), list):
            self.ListaAtaques = list(diff.get("ListaAtaques") or [])
        elif isinstance(diff.get("ataques"), list):
            self.ListaAtaques = list(diff.get("ataques") or [])
        if isinstance(diff.get("Dados"), dict):
            self.Dados.update(diff.get("Dados") or {})
        elif isinstance(diff.get("dados"), dict):
            self.Dados.update(diff.get("dados") or {})
        self._sincronizar_alias_atributos()
        if "efeitos" in diff:
            self.Dados["efeitos"] = list(diff.get("efeitos") or [])
        else:
            self.Dados["efeitos"] = list(self.Dados.get("efeitos") or [])
        self._sincronizar_efeitos(self.Dados["efeitos"])
        self.Dados["estados_transitorios"] = dict(diff.get("estados_transitorios") or self.Dados.get("estados_transitorios") or {})
        self.Dados["estatisticas_batalha"] = dict(diff.get("estatisticas_batalha") or self.Dados.get("estatisticas_batalha") or {})
        self.EnergiaPrevista = float(self.Energia)
        self.CustoPrevistoPendente = 0.0
        self.PodePagarPrevisao = True

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
        diff = self.obter_valor_ficha(chave) - self.obter_valor_base_ficha(chave)
        if abs(diff) > 0.001:
            return diff
        return self.Variacoes.get(str(chave), 0.0)

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
        if not self.Vivo or not self.Ativo or self.EmReserva or not self.AreaId:
            self.RectAtual = pygame.Rect(0, 0, 0, 0)
            return
        if self._furtivo_inimigo_oculto():
            self.RectAtual = pygame.Rect(0, 0, 0, 0)
            return
        if self.CentroMundoOverride is not None:
            cx, cy = camera.mundo_para_tela_px(self.CentroMundoOverride)
        elif self.CentroTelaOverride is not None:
            cx, cy = self.CentroTelaOverride
        else:
            centro = arena.centro_area(self.AreaId)
            if centro is None:
                return
            cx, cy = camera.mundo_para_tela_px(centro)
        ox, oy = self.OffsetVisual
        ex, ey = self._offset_efeitos_dinamicos(camera)
        cx += ox + ex
        cy += oy + ey
        img = self._frame_atual_escalado(camera)
        if img is None:
            cor = (110, 196, 126) if self.Lado == "jogador" else (204, 108, 108)
            lado = max(46, int(getattr(camera, "TilePx", 40) * 1.7))
            sprite = pygame.Surface((lado, lado), pygame.SRCALPHA)
            pygame.draw.circle(sprite, cor, (lado // 2, lado // 2), lado // 2)
            fonte = pygame.font.SysFont("arial", max(16, lado // 4), bold=True)
            txt = fonte.render(str(self.Nome)[:3].upper(), True, (20, 20, 20))
            sprite.blit(txt, txt.get_rect(center=(lado // 2, lado // 2)))
            sprite = self._aplicar_transformacao_visual(sprite)
            rect = sprite.get_rect(center=(int(cx), int(cy)))
            surface.blit(sprite, rect)
            self.RectAtual = pygame.Rect(rect)
        else:
            img = self._aplicar_transformacao_visual(img)
            rect = img.get_rect(center=(int(cx), int(cy)))
            surface.blit(img, rect)
            self.RectAtual = pygame.Rect(rect)
        self._desenhar_flash(surface)
        self._desenhar_sono(surface, camera)
        self.Estado.desenhar_animacoes_status(surface, camera, arena)
        self.desenhar_barras(surface, camera)
        self.Estado.desenhar_efeitos(surface, camera)

    def desenhar_fantasma(self, surface, camera, arena, area_id, alpha=68):
        if not self.Vivo:
            return
        centro = arena.centro_area(area_id)
        if centro is None:
            return
        cx, cy = camera.mundo_para_tela_px(centro)
        img = self._frame_atual_escalado(camera)
        if img is None:
            lado = max(46, int(getattr(camera, "TilePx", 40) * 1.7))
            ghost = pygame.Surface((lado, lado), pygame.SRCALPHA)
            cor = (110, 196, 126, int(alpha)) if self.Lado == "jogador" else (204, 108, 108, int(alpha))
            pygame.draw.circle(ghost, cor, (lado // 2, lado // 2), lado // 2)
            surface.blit(ghost, ghost.get_rect(center=(int(cx), int(cy))))
            return
        ghost = img.copy()
        ghost.set_alpha(int(alpha))
        surface.blit(ghost, ghost.get_rect(center=(int(cx), int(cy))))

    def desenhar_reserva(self, surface, rect_slot, selecionado=False, hover=False, camera=None):
        _ = (selecionado, hover)
        base = pygame.Rect(rect_slot)
        img = self._frame_atual_escalado(camera)
        alpha = max(0, min(255, int(self.AlphaVisual)))
        if img is None:
            cor = (110, 196, 126) if self.Lado == "jogador" else (204, 108, 108)
            camada = pygame.Surface(base.size, pygame.SRCALPHA)
            pygame.draw.circle(camada, (*cor, alpha), (base.w // 2, base.h // 2), max(6, min(base.w, base.h) // 3))
            surface.blit(camada, base.topleft)
        else:
            img = self._aplicar_transformacao_visual(img)
            surface.blit(img, img.get_rect(center=base.center))
        self.RectAtual = base

    def _aplicar_transformacao_visual(self, img):
        out = img
        rotacao = float(self.RotacaoVisual or 0.0) + self.Estado._rotacao_efeitos_dinamicos()
        escala = self.Estado._escala_efeitos_dinamicos()
        if abs(rotacao) > 0.001 or abs(escala - 1.0) > 0.001:
            out = pygame.transform.rotozoom(out, rotacao, escala)
        out = self.Estado._aplicar_filtros_efeitos(out)
        alpha = max(0, min(255, int(self.AlphaVisual * self.Estado._multiplicador_alpha_efeitos())))
        if alpha < 255:
            out = out.copy()
            out.set_alpha(alpha)
        return out

    @staticmethod
    def _escala_mundo_ui(camera=None):
        try:
            tile = float(getattr(camera, "TilePx", 40) or 40)
        except (TypeError, ValueError):
            tile = 40.0
        return max(0.48, min(2.35, tile / 40.0))

    def desenhar_barras(self, surface, camera=None):
        if self.RectAtual.width <= 0 or self.RectAtual.height <= 0:
            return
        escala = self._escala_mundo_ui(camera)
        vida_max = max(1.0, float(self.VidaMax))
        ene_max = max(1.0, float(self.EnergiaMax))
        vida_t = max(0.0, min(1.0, float(self.VidaAtual) / vida_max))
        ene_t = max(0.0, min(1.0, float(self.Energia) / ene_max))

        barra_w = max(34, int(round(86 * escala)))
        vida_h = max(4, int(round(10 * escala)))
        ene_h = max(3, int(round(5 * escala)))
        gap = max(1, int(round(3 * escala)))
        margem = max(4, int(round(8 * escala)))
        x = self.RectAtual.centerx - barra_w // 2
        y = self.RectAtual.y - vida_h - ene_h - gap - margem
        rect_vida = pygame.Rect(x, y, barra_w, vida_h)
        rect_ene = pygame.Rect(x, y + vida_h + gap, barra_w, ene_h)

        raio_vida = max(4, vida_h // 2)
        raio_ene = max(3, ene_h // 2)
        borda = max(1, int(round(escala)))
        pygame.draw.rect(surface, (14, 18, 24), rect_vida, border_radius=raio_vida)
        pygame.draw.rect(surface, (24, 28, 35), rect_ene, border_radius=raio_ene)
        fill_vida = pygame.Rect(rect_vida.x, rect_vida.y, int(rect_vida.w * vida_t), rect_vida.h)
        fill_ene = pygame.Rect(rect_ene.x, rect_ene.y, int(rect_ene.w * ene_t), rect_ene.h)
        if fill_vida.w > 0:
            pygame.draw.rect(surface, (44, 190, 88), fill_vida, border_radius=raio_vida)
        if fill_ene.w > 0:
            pygame.draw.rect(surface, (74, 148, 255), fill_ene, border_radius=raio_ene)
        if float(self.CustoPrevistoPendente) > 0.0 and ene_max > 0:
            reservado = max(0.0, min(float(self.CustoPrevistoPendente), float(self.Energia)))
            inicio_t = max(0.0, min(1.0, (float(self.Energia) - reservado) / ene_max))
            fim_t = max(0.0, min(1.0, float(self.Energia) / ene_max))
            ini_x = rect_ene.x + int(rect_ene.w * inicio_t)
            fim_x = rect_ene.x + int(rect_ene.w * fim_t)
            if fim_x > ini_x:
                alpha = int(90 + 80 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 140.0)))
                cor = (255, 255, 255, alpha) if self.PodePagarPrevisao else (255, 116, 116, alpha)
                overlay = pygame.Surface((fim_x - ini_x, rect_ene.h), pygame.SRCALPHA)
                pygame.draw.rect(overlay, cor, overlay.get_rect(), border_radius=raio_ene)
                surface.blit(overlay, (ini_x, rect_ene.y))

        pygame.draw.rect(surface, (230, 236, 244), rect_vida, borda, border_radius=raio_vida)
        pygame.draw.rect(surface, (230, 236, 244), rect_ene, borda, border_radius=raio_ene)

        if vida_max >= 30:
            setores = int(vida_max // 30)
            area_interna = rect_vida.inflate(-2, -2)
            for i in range(1, setores + 1):
                tx = area_interna.x + int(area_interna.w * ((i * 30) / vida_max))
                if area_interna.x < tx < area_interna.right:
                    pygame.draw.line(surface, (0, 0, 0), (tx, area_interna.y), (tx, area_interna.bottom - 1), borda)

    def contem_ponto(self, pos_mouse):
        if self._furtivo_inimigo_oculto():
            return False
        return self.RectAtual.collidepoint(pos_mouse)

    def possui_efeito(self, nome_ou_code):
        alvo = _normalizar_nome(nome_ou_code)
        return any(_normalizar_nome((e or {}).get("nome") or (e or {}).get("code")) == alvo for e in self.EfeitosFormais)

    def esta_furtivo(self):
        return self.possui_efeito("Furtivo")

    def esta_ativo(self):
        return bool(self.Ativo)

    def esta_na_reserva(self):
        return bool(self.EmReserva)

    def esta_vivo(self):
        return bool(self.Vivo)
