from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any
import unicodedata

import pygame
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
    CentroMundoOverride: tuple[float, float] | None = None
    CentroTelaOverride: tuple[float, float] | None = None
    OffsetVisual: tuple[float, float] = (0.0, 0.0)
    AlphaVisual: int = 255
    RotacaoVisual: float = 0.0
    FlashVisualCor: tuple[int, int, int] = (255, 255, 255)
    FlashVisualAlpha: int = 0

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
        p._carregar_animacao()
        return p

    def definir_intervalo_frame_ms(self, intervalo_ms: float | int | None):
        try:
            ms = float(intervalo_ms)
        except (TypeError, ValueError):
            return
        if ms <= 0:
            return
        self.TempoFrame = max(0.01, ms / 1000.0)

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
        if self._carregamento_frames_tentado:
            return
        self._carregamento_frames_tentado = True

        info = self.Dados if isinstance(self.Dados, dict) else {}
        frames = []

        especie = str(self.Especie or info.get("especie") or info.get("Especie") or self.Nome or "").strip()
        base_anim = Path("Recursos") / "Visual" / "Pokemons" / "Animação"
        especie_candidatos = [
            especie,
            especie.lower(),
            especie.replace("_", " "),
            especie.replace("_", " ").lower(),
            especie.replace(" ", "-").lower(),
            especie.replace("-", " ").lower(),
        ]
        for nome_especie in especie_candidatos:
            if not nome_especie:
                continue
            pasta_anim = base_anim / nome_especie
            if not pasta_anim.exists() or not pasta_anim.is_dir():
                continue
            try:
                frames = carregar_frames(pasta_anim)
            except Exception:
                frames = []
            if frames:
                break

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
        self._cache_frames_escalados = {}

    def atualizar_animacao(self, dt: float):
        if not self.Frames:
            return
        self.TimerAnimacao += max(0.0, float(dt))
        while self.TimerAnimacao >= self.TempoFrame:
            self.TimerAnimacao -= self.TempoFrame
            self.FrameAtual = (self.FrameAtual + 1) % len(self.Frames)

    def _frame_atual_escalado(self, camera):
        if not self.Frames:
            return None
        tile_px = max(1, int(getattr(camera, "TilePx", 40) or 40)) if camera is not None else 40
        if tile_px not in self._cache_frames_escalados:
            fator_zoom = float(tile_px) / 40.0
            fator = max(0.1, 1.10 * fator_zoom)
            escalados = []
            for frame in self.Frames:
                fw = max(1, int(round(frame.get_width() * fator)))
                fh = max(1, int(round(frame.get_height() * fator)))
                escalado = pygame.transform.smoothscale(frame, (fw, fh)).convert_alpha()
                escalados.append(escalado)
            self._cache_frames_escalados[tile_px] = escalados
        frames = self._cache_frames_escalados.get(tile_px) or []
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
        cx += ox
        cy += oy
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
            surface.blit(sprite, sprite.get_rect(center=(int(cx), int(cy))))
            self.RectAtual = pygame.Rect(int(cx - lado // 2), int(cy - lado // 2), lado, lado)
        else:
            img = self._aplicar_transformacao_visual(img)
            rect = img.get_rect(center=(int(cx), int(cy)))
            surface.blit(img, rect)
            self.RectAtual = pygame.Rect(rect)
        self._desenhar_flash(surface)
        self.desenhar_animacoes_status(surface, camera, arena)
        self.desenhar_barras(surface, camera)
        self.desenhar_efeitos(surface, camera)

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
        if abs(float(self.RotacaoVisual or 0.0)) > 0.001:
            out = pygame.transform.rotozoom(out, float(self.RotacaoVisual or 0.0), 1.0)
        alpha = max(0, min(255, int(self.AlphaVisual)))
        if alpha < 255:
            out = out.copy()
            out.set_alpha(alpha)
        return out

    def _desenhar_flash(self, surface):
        alpha = max(0, min(255, int(self.FlashVisualAlpha or 0)))
        if alpha <= 0 or self.RectAtual.width <= 0:
            return
        overlay = pygame.Surface(self.RectAtual.size, pygame.SRCALPHA)
        pygame.draw.ellipse(overlay, (*tuple(self.FlashVisualCor or (255, 255, 255)), alpha), overlay.get_rect())
        surface.blit(overlay, self.RectAtual.topleft)

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

    def _sincronizar_efeitos(self, efeitos):
        novos_por_chave = {}
        for efeito in [dict(e) for e in list(efeitos or []) if isinstance(e, dict)]:
            chave = self._chave_efeito(efeito)
            if not chave:
                continue
            if chave in novos_por_chave:
                atual = novos_por_chave[chave]
                atuais = max(0, _i(atual.get("passos_restantes"), 0))
                novos = max(0, _i(efeito.get("passos_restantes"), 0))
                atual["stacks"] = 1
                atual["passos_restantes"] = atuais + novos
                atual["passos_totais"] = max(_i(atual.get("passos_totais"), atuais), atuais) + novos
            else:
                efeito["stacks"] = 1
                novos_por_chave[chave] = efeito
        novos = list(novos_por_chave.values())
        chaves_atuais = {self._chave_efeito(e) for e in self.EfeitosFormais}
        chaves_novas = {self._chave_efeito(e) for e in novos}
        for chave in chaves_novas - chaves_atuais:
            self.AnimacoesEfeitos[chave] = 0.0
        for chave in chaves_atuais - chaves_novas:
            self.EfeitosSaindo[chave] = 0.0
        self.EfeitosFormais = novos[:4]

    def aplicar_efeito_visual(self, efeito):
        if not isinstance(efeito, dict):
            return
        chave = self._chave_efeito(efeito)
        novo = dict(efeito)
        existente = next((e for e in self.EfeitosFormais if self._chave_efeito(e) == chave), None)
        if existente is not None:
            passos_anteriores = max(0, _i(existente.get("passos_restantes"), 0))
            passos_novos = max(0, _i(novo.get("passos_restantes"), 0))
            existente.update(novo)
            existente["stacks"] = 1
            if passos_novos > 0:
                existente["passos_restantes"] = passos_anteriores + passos_novos
                existente["passos_totais"] = max(_i(existente.get("passos_totais"), passos_anteriores), passos_anteriores) + passos_novos
        else:
            novo["stacks"] = 1
            self.EfeitosFormais.append(novo)
        self.EfeitosFormais = self.EfeitosFormais[:4]
        self.AnimacoesEfeitos[chave] = 0.0
        self.EfeitosSaindo.pop(chave, None)

    def atualizar_timer_efeito(self, efeito_code=None, efeito_nome=None, passos_restantes=None):
        alvo = _normalizar_nome(efeito_code or efeito_nome)
        for efeito in self.EfeitosFormais:
            if _normalizar_nome(efeito.get("code") or efeito.get("nome")) == alvo:
                efeito["passos_restantes"] = passos_restantes
                efeito["passos_totais"] = max(_i(efeito.get("passos_totais"), 0), _i(passos_restantes, 0))
                break

    def expirar_efeito_visual(self, efeito_code=None, efeito_nome=None):
        alvo = _normalizar_nome(efeito_code or efeito_nome)
        for efeito in list(self.EfeitosFormais):
            if _normalizar_nome(efeito.get("code") or efeito.get("nome")) == alvo:
                self.EfeitosSaindo[self._chave_efeito(efeito)] = 0.0

    def atualizar_efeitos_visuais(self, dt):
        dt = max(0.0, float(dt or 0.0))
        for chave in list(self.AnimacoesEfeitos):
            self.AnimacoesEfeitos[chave] = min(1.0, float(self.AnimacoesEfeitos.get(chave, 0.0)) + dt * 5.5)
            if self.AnimacoesEfeitos[chave] >= 1.0:
                self.AnimacoesEfeitos.pop(chave, None)
        for chave in list(self.EfeitosSaindo):
            self.EfeitosSaindo[chave] = min(1.0, float(self.EfeitosSaindo.get(chave, 0.0)) + dt * 5.5)
            if self.EfeitosSaindo[chave] >= 1.0:
                self.EfeitosSaindo.pop(chave, None)
                self.EfeitosFormais = [e for e in self.EfeitosFormais if self._chave_efeito(e) != chave]
        restantes = []
        for anim in self.AnimacoesStatus:
            anim["tempo"] = float(anim.get("tempo", 0.0)) + dt
            if float(anim.get("tempo", 0.0)) < float(anim.get("duracao", 0.8)):
                restantes.append(anim)
        self.AnimacoesStatus = restantes

    def animar_variacao_status(self, positivo=True):
        self.AnimacoesStatus.append({"positivo": bool(positivo), "tempo": 0.0, "duracao": 0.8})

    def desenhar_efeitos(self, surface, camera=None):
        if self.RectAtual.width <= 0:
            return
        efeitos = list(self.EfeitosFormais or [])[:4]
        if not efeitos:
            return
        escala_ui = self._escala_mundo_ui(camera)
        raio = max(7, int(round(16 * escala_ui)))
        gap = max(3, int(round(8 * escala_ui)))
        total_w = len(efeitos) * raio * 2 + (len(efeitos) - 1) * gap
        x0 = self.RectAtual.centerx - total_w // 2 + raio
        y = self.RectAtual.bottom + max(8, int(round(18 * escala_ui)))
        fonte_fallback = pygame.font.SysFont("arial", max(7, int(round(11 * escala_ui))), bold=True)
        fonte_stack = pygame.font.SysFont("arial", max(7, int(round(11 * escala_ui))), bold=True)
        fonte_tooltip = pygame.font.SysFont("arial", max(9, int(round(13 * escala_ui))), bold=True)
        mouse = pygame.mouse.get_pos()
        tooltip = None
        for idx, efeito in enumerate(efeitos):
            chave = self._chave_efeito(efeito)
            t_entrada = float(self.AnimacoesEfeitos.get(chave, 1.0))
            t_saida = float(self.EfeitosSaindo.get(chave, 0.0))
            escala = max(0.0, min(1.0, t_entrada)) * (1.0 - max(0.0, min(1.0, t_saida)))
            if escala <= 0.02:
                continue
            cx = x0 + idx * (raio * 2 + gap)
            r = max(2, int(raio * escala))
            negativo = bool(efeito.get("negativo")) or str(efeito.get("tipo") or "").lower() == "negativo"
            cor = (224, 70, 70, 220) if negativo else (72, 190, 104, 220)
            pygame.draw.circle(surface, cor, (cx, y), r)
            self._desenhar_borda_efeito(surface, cx, y, r, efeito, escala_ui)
            icone = self._icone_efeito(efeito.get("nome") or efeito.get("code"))
            if icone is not None and r > 6:
                margem_icone = max(3, int(round(4 * escala_ui)))
                img = pygame.transform.smoothscale(icone, (max(4, r * 2 - margem_icone * 2), max(4, r * 2 - margem_icone * 2)))
                surface.blit(img, img.get_rect(center=(cx, y)))
            else:
                nome = str(efeito.get("nome") or efeito.get("code") or "?")
                txt = fonte_fallback.render(nome[:2].upper(), True, (18, 24, 30))
                surface.blit(txt, txt.get_rect(center=(cx, y)))
            area = pygame.Rect(cx - r, y - r, r * 2, r * 2)
            if area.collidepoint(mouse):
                tooltip = (str(efeito.get("nome") or efeito.get("code") or "Efeito"), negativo, cx, y + r + max(4, int(round(6 * escala_ui))))
        if tooltip is not None:
            nome, negativo, cx, ty = tooltip
            cor_txt = (132, 218, 255) if not negativo else (190, 126, 255)
            txt = fonte_tooltip.render(nome, True, cor_txt)
            fundo = pygame.Rect(0, 0, txt.get_width() + max(6, int(round(10 * escala_ui))), txt.get_height() + max(4, int(round(6 * escala_ui))))
            fundo.midtop = (int(cx), int(ty))
            raio_tooltip = max(4, int(round(6 * escala_ui)))
            pygame.draw.rect(surface, (13, 16, 24, 232), fundo, border_radius=raio_tooltip)
            pygame.draw.rect(surface, cor_txt, fundo, max(1, int(round(escala_ui))), border_radius=raio_tooltip)
            surface.blit(txt, txt.get_rect(center=fundo.center))

    def _desenhar_borda_efeito(self, surface, cx, y, r, efeito, escala_ui=1.0):
        total = max(1, _i(efeito.get("passos_totais"), _i(efeito.get("passos_restantes"), 1)))
        restantes = max(0, min(total, _i(efeito.get("passos_restantes"), total)))
        rect = pygame.Rect(cx - r, y - r, r * 2, r * 2)
        largura = max(1, int(round(3 * escala_ui)))
        lacuna = math.radians(7)
        inicio_base = -math.pi / 2
        for i in range(total):
            a0 = inicio_base + (math.tau * i / total) + lacuna / 2
            a1 = inicio_base + (math.tau * (i + 1) / total) - lacuna / 2
            pygame.draw.arc(surface, (245, 250, 255), rect, a0, a1, largura)
            if i < restantes:
                pygame.draw.arc(surface, (80, 178, 255), rect, a0, a1, largura)

    def desenhar_animacoes_status(self, surface, camera=None, arena=None):
        if self.RectAtual.width <= 0 or not self.AnimacoesStatus:
            return
        base_x, base_y = self.RectAtual.center
        if camera is not None and arena is not None and self.CentroTelaOverride is None and self.CentroMundoOverride is None:
            centro = arena.centro_area(self.AreaId)
            if centro is not None:
                base_x, base_y = camera.mundo_para_tela_px(centro)
        escala = max(0.75, min(1.8, float(getattr(camera, "TilePx", 40) or 40) / 40.0)) if camera is not None else 1.0
        for anim in list(self.AnimacoesStatus):
            t = max(0.0, min(1.0, float(anim.get("tempo", 0.0)) / max(0.001, float(anim.get("duracao", 0.8)))))
            positivo = bool(anim.get("positivo", True))
            cor = (72, 190, 104, int(220 * (1.0 - t))) if positivo else (224, 70, 70, int(220 * (1.0 - t)))
            direcao = -1 if positivo else 1
            y_base = float(base_y) - 22 * escala + direcao * 26 * escala * t
            for i in range(3):
                x = float(base_x) + (i - 1) * 18 * escala
                y = y_base + (i % 2) * 7 * escala
                if positivo:
                    pts = [(x, y - 11 * escala), (x - 8 * escala, y + 5 * escala), (x - 3 * escala, y + 5 * escala), (x - 3 * escala, y + 14 * escala), (x + 3 * escala, y + 14 * escala), (x + 3 * escala, y + 5 * escala), (x + 8 * escala, y + 5 * escala)]
                else:
                    pts = [(x, y + 11 * escala), (x - 8 * escala, y - 5 * escala), (x - 3 * escala, y - 5 * escala), (x - 3 * escala, y - 14 * escala), (x + 3 * escala, y - 14 * escala), (x + 3 * escala, y - 5 * escala), (x + 8 * escala, y - 5 * escala)]
                pygame.draw.polygon(surface, cor, pts)

    @staticmethod
    def _chave_efeito(efeito):
        return _normalizar_nome((efeito or {}).get("code") or (efeito or {}).get("nome"))

    @classmethod
    def _icone_efeito(cls, nome):
        chave = _normalizar_nome(nome)
        if not chave:
            return None
        cache = getattr(cls, "_icones_cache_real", None)
        if cache is None:
            cache = {}
            setattr(cls, "_icones_cache_real", cache)
        if chave in cache:
            return cache[chave]
        base = Path("Recursos") / "Visual" / "Icones" / "Efeitos"
        escolhido = None
        try:
            for caminho in base.iterdir():
                if caminho.is_file() and _normalizar_nome(caminho.stem) == chave:
                    escolhido = caminho
                    break
        except Exception:
            escolhido = None
        if escolhido is not None:
            try:
                cache[chave] = pygame.image.load(str(escolhido)).convert_alpha()
            except Exception:
                cache[chave] = None
        else:
            cache[chave] = None
        return cache[chave]

    def contem_ponto(self, pos_mouse):
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
