from __future__ import annotations

import math
import random
import unicodedata
from typing import Callable, Tuple

import pygame

from Codigo.Visual.AuxiliaresVisuais import obter_paleta_tipo

Vector2 = Tuple[float, float]


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, float(valor)))


def _interp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)


def _ease(t: float) -> float:
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _pulso(t: float, ciclos: float = 1.0) -> float:
    return math.sin(_clamp(t, 0.0, 1.0) * math.pi * ciclos)


def _cor_rgba(cor: object, alpha: float | int = 255) -> tuple[int, int, int, int]:
    if not (isinstance(cor, (list, tuple)) and len(cor) >= 3):
        cor = (255, 255, 255)
    return (
        max(0, min(255, int(cor[0]))),
        max(0, min(255, int(cor[1]))),
        max(0, min(255, int(cor[2]))),
        max(0, min(255, int(alpha))),
    )


def _distancia(a: Vector2, b: Vector2) -> float:
    return math.hypot(float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))


def _normal(a: Vector2, b: Vector2) -> Vector2:
    dx = float(b[0]) - float(a[0])
    dy = float(b[1]) - float(a[1])
    dist = max(0.001, math.hypot(dx, dy))
    return (dx / dist, dy / dist)


def _perpendicular(a: Vector2, b: Vector2) -> Vector2:
    nx, ny = _normal(a, b)
    return (-ny, nx)


def _ponto_linha(a: Vector2, b: Vector2, t: float) -> Vector2:
    return (_interp(a[0], b[0], t), _interp(a[1], b[1], t))


def _ponto_curva(a: Vector2, controle: Vector2, b: Vector2, t: float) -> Vector2:
    t = _clamp(t, 0.0, 1.0)
    u = 1.0 - t
    return (
        u * u * a[0] + 2.0 * u * t * controle[0] + t * t * b[0],
        u * u * a[1] + 2.0 * u * t * controle[1] + t * t * b[1],
    )


class ContatoIrregularAnimator:
    """
    Animações de contato especial/irregular.

    O arquivo não força integração com o fluxo atual da batalha. Para usar, crie uma instância
    com as mesmas funções de conversão usadas pelos outros animators:

        animator = ContatoIrregularAnimator(posicao_mundo, posicao_tela)
        animator.animar_laser(pokemon_origem, pokemon_alvo, tipo_ataque="fogo")
        animator.atualizar(dt)
        animator.desenhar(surface)

    Métodos disponíveis:
    - animar_laser
    - animar_laser_linha
    - animar_raio
    - animar_jato_liquido
    - animar: despacho por string ("Laser", "LaserLinha", "Raio", "JatoLiquido")
    """

    def __init__(
        self,
        posicao_mundo: Callable[[object], Vector2 | None],
        posicao_tela: Callable[[Vector2], Vector2 | None],
    ) -> None:
        self._posicao_mundo = posicao_mundo
        self._posicao_tela = posicao_tela
        self.animacoes: list[dict[str, object]] = []
        self._sequencia = 0

    def animar(
        self,
        estilo: object,
        origem,
        destino=None,
        *,
        tipo_ataque=None,
        duracao=None,
        bloqueante=True,
        **kwargs,
    ):
        chave = _normalizar_nome(estilo)
        if chave == "laser":
            return self.animar_laser(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, bloqueante=bloqueante, **kwargs)
        if chave in {"laserlinha", "laserlinear", "linhalaser"}:
            return self.animar_laser_linha(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, bloqueante=bloqueante, **kwargs)
        if chave == "raio":
            return self.animar_raio(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, bloqueante=bloqueante, **kwargs)
        if chave in {"jatoliquido", "jato", "liquido", "agua"}:
            return self.animar_jato_liquido(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, bloqueante=bloqueante, **kwargs)
        return None

    def animar_laser(self, origem, destino, *, tipo_ataque=None, duracao=None, largura=None, bloqueante=True):
        p0 = self._resolver_posicao(origem)
        p1 = self._resolver_posicao(destino)
        if p0 is None or p1 is None:
            return None
        return self._adicionar(
            {
                "tipo": "laser",
                "origem_ref": origem,
                "destino_ref": destino,
                "origem": p0,
                "destino": p1,
                "tipo_ataque": tipo_ataque or "normal",
                "tempo": 0.0,
                "duracao": float(duracao or 0.48),
                "largura": largura,
                "bloqueante": bool(bloqueante),
            }
        )

    def animar_laser_linha(
        self,
        pokemon,
        linha_inicio,
        linha_fim=None,
        *,
        frente_linha=None,
        tipo_ataque=None,
        duracao=None,
        largura=None,
        bloqueante=True,
    ):
        origem = self._resolver_posicao(pokemon)
        inicio = self._resolver_posicao(linha_inicio)
        fim = self._resolver_posicao(linha_fim)

        if origem is None or inicio is None:
            return None
        if fim is None:
            fim = inicio

        frente = self._resolver_posicao(frente_linha)
        if frente is None:
            frente = self._ponto_frente_linha(origem, inicio, fim)

        return self._adicionar(
            {
                "tipo": "laser_linha",
                "pokemon": pokemon,
                "origem_movimento": origem,
                "frente_linha": frente,
                "linha_inicio_ref": linha_inicio,
                "linha_fim_ref": linha_fim,
                "linha_inicio": inicio,
                "linha_fim": fim,
                "tipo_ataque": tipo_ataque or "normal",
                "tempo": 0.0,
                "duracao": float(duracao or 0.82),
                "largura": largura,
                "bloqueante": bool(bloqueante),
            }
        )

    def animar_raio(self, origem, destino, *, tipo_ataque=None, duracao=None, intensidade=None, bloqueante=True):
        p0 = self._resolver_posicao(origem)
        p1 = self._resolver_posicao(destino)
        if p0 is None or p1 is None:
            return None
        return self._adicionar(
            {
                "tipo": "raio",
                "origem_ref": origem,
                "destino_ref": destino,
                "origem": p0,
                "destino": p1,
                "tipo_ataque": tipo_ataque or "eletrico",
                "tempo": 0.0,
                "duracao": float(duracao or 0.40),
                "intensidade": float(intensidade or 1.0),
                "bloqueante": bool(bloqueante),
            }
        )

    def animar_jato_liquido(self, origem, destino, *, tipo_ataque=None, duracao=None, largura=None, bloqueante=True):
        p0 = self._resolver_posicao(origem)
        p1 = self._resolver_posicao(destino)
        if p0 is None or p1 is None:
            return None
        return self._adicionar(
            {
                "tipo": "jato_liquido",
                "origem_ref": origem,
                "destino_ref": destino,
                "origem": p0,
                "destino": p1,
                "tipo_ataque": tipo_ataque or "agua",
                "tempo": 0.0,
                "duracao": float(duracao or 0.58),
                "largura": largura,
                "bloqueante": bool(bloqueante),
            }
        )

    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt or 0.0))
        restantes: list[dict[str, object]] = []
        for anim in list(self.animacoes):
            anim["tempo"] = float(anim.get("tempo", 0.0)) + dt
            self._atualizar_refs(anim)
            self._aplicar_movimento(anim)
            if float(anim.get("tempo", 0.0)) < float(anim.get("duracao", 0.0)):
                restantes.append(anim)
            else:
                self._finalizar(anim)
        self.animacoes = restantes

    def desenhar(self, surface: pygame.Surface) -> None:
        for anim in list(self.animacoes):
            tipo = str(anim.get("tipo") or "")
            if tipo == "laser":
                self._desenhar_laser(surface, anim)
            elif tipo == "laser_linha":
                self._desenhar_laser_linha(surface, anim)
            elif tipo == "raio":
                self._desenhar_raio(surface, anim)
            elif tipo == "jato_liquido":
                self._desenhar_jato_liquido(surface, anim)

    def esta_ocupado(self) -> bool:
        return any(bool(anim.get("bloqueante", True)) for anim in self.animacoes)

    def _adicionar(self, anim: dict[str, object]):
        self._sequencia += 1
        anim["id"] = self._sequencia
        self.animacoes.append(anim)
        return anim

    def _progresso(self, anim: dict[str, object]) -> float:
        duracao = max(0.001, float(anim.get("duracao", 0.0)))
        return _clamp(float(anim.get("tempo", 0.0)) / duracao, 0.0, 1.0)

    def _resolver_posicao(self, alvo) -> Vector2 | None:
        if alvo is None:
            return None
        if isinstance(alvo, (list, tuple)) and len(alvo) >= 2:
            try:
                return (float(alvo[0]), float(alvo[1]))
            except (TypeError, ValueError):
                return None
        override = getattr(alvo, "CentroMundoOverride", None)
        if isinstance(override, (list, tuple)) and len(override) >= 2:
            return (float(override[0]), float(override[1]))
        try:
            return self._posicao_mundo(alvo)
        except Exception:
            return None

    def _resolver_tela(self, pos_mundo) -> Vector2 | None:
        if not (isinstance(pos_mundo, (list, tuple)) and len(pos_mundo) >= 2):
            return None
        try:
            return self._posicao_tela((float(pos_mundo[0]), float(pos_mundo[1])))
        except Exception:
            return None

    def _atualizar_refs(self, anim: dict[str, object]) -> None:
        origem_ref = anim.get("origem_ref")
        destino_ref = anim.get("destino_ref")
        if origem_ref is not None:
            origem = self._resolver_posicao(origem_ref)
            if origem is not None:
                anim["origem"] = origem
        if destino_ref is not None:
            destino = self._resolver_posicao(destino_ref)
            if destino is not None:
                anim["destino"] = destino

        if str(anim.get("tipo") or "") == "laser_linha":
            inicio = self._resolver_posicao(anim.get("linha_inicio_ref"))
            fim = self._resolver_posicao(anim.get("linha_fim_ref"))
            if inicio is not None:
                anim["linha_inicio"] = inicio
            if fim is not None:
                anim["linha_fim"] = fim

    def _aplicar_movimento(self, anim: dict[str, object]) -> None:
        if str(anim.get("tipo") or "") != "laser_linha":
            return
        pokemon = anim.get("pokemon")
        origem = anim.get("origem_movimento")
        frente = anim.get("frente_linha")
        if pokemon is None or origem is None or frente is None:
            return

        t = self._progresso(anim)
        if t <= 0.38:
            local = _ease(t / 0.38)
            pokemon.CentroMundoOverride = (_interp(origem[0], frente[0], local), _interp(origem[1], frente[1], local))
            pokemon.OffsetVisual = (0.0, -math.sin(local * math.pi) * 0.18)
        else:
            pokemon.CentroMundoOverride = frente
            pokemon.OffsetVisual = (0.0, -math.sin(min(1.0, (t - 0.38) / 0.18) * math.pi) * 0.08)

    def _finalizar(self, anim: dict[str, object]) -> None:
        pokemon = anim.get("pokemon")
        if pokemon is not None:
            pokemon.CentroMundoOverride = None
            pokemon.CentroTelaOverride = None
            pokemon.OffsetVisual = (0.0, 0.0)
            pokemon.FlashVisualAlpha = 0

    def _paleta(self, anim: dict[str, object]):
        return obter_paleta_tipo(anim.get("tipo_ataque") or "normal")

    def _ponto_frente_linha(self, origem: Vector2, inicio: Vector2, fim: Vector2) -> Vector2:
        dx = fim[0] - inicio[0]
        dy = fim[1] - inicio[1]
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return inicio
        nx, ny = _normal(inicio, fim)
        px, py = -ny, nx
        lado = 1.0 if ((origem[0] - inicio[0]) * px + (origem[1] - inicio[1]) * py) >= 0 else -1.0
        dist_inicio = _distancia(origem, inicio)
        dist_fim = _distancia(origem, fim)
        ancora = fim if dist_fim < dist_inicio else inicio
        return (ancora[0] + px * lado * 0.72, ancora[1] + py * lado * 0.72)

    def _overlay(self, surface: pygame.Surface) -> pygame.Surface:
        return pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    def _desenhar_linha_glow(
        self,
        overlay: pygame.Surface,
        p0: Vector2,
        p1: Vector2,
        paleta,
        *,
        largura: float,
        alpha: float,
        abertura: float = 1.0,
    ) -> None:
        if abertura <= 0.0:
            return
        fim = _ponto_linha(p0, p1, _clamp(abertura, 0.0, 1.0))
        x0, y0 = int(p0[0]), int(p0[1])
        x1, y1 = int(fim[0]), int(fim[1])
        base = paleta["base"]
        clara = paleta["clara"]
        brilho = paleta["brilho"]
        sombra = paleta["sombra"]

        for fator, a, cor in (
            (4.8, 0.10, sombra),
            (3.2, 0.16, base),
            (2.0, 0.26, clara),
            (1.0, 0.78, brilho),
        ):
            w = max(1, int(largura * fator))
            pygame.draw.line(overlay, _cor_rgba(cor, alpha * a), (x0, y0), (x1, y1), w)

    def _desenhar_circulo_glow(self, overlay: pygame.Surface, centro: Vector2, paleta, raio: float, alpha: float) -> None:
        x, y = int(centro[0]), int(centro[1])
        for fator, a, cor in (
            (1.9, 0.10, paleta["base"]),
            (1.25, 0.18, paleta["clara"]),
            (0.58, 0.60, paleta["brilho"]),
        ):
            r = max(1, int(raio * fator))
            pygame.draw.circle(overlay, _cor_rgba(cor, alpha * a), (x, y), r)

    def _desenhar_particulas_linha(
        self,
        overlay: pygame.Surface,
        p0: Vector2,
        p1: Vector2,
        paleta,
        *,
        t: float,
        quantidade: int,
        espalhamento: float,
        alpha: float,
        seed_extra: int = 0,
    ) -> None:
        perp = _perpendicular(p0, p1)
        rng = random.Random((int(p0[0] * 7) ^ int(p1[1] * 13) ^ seed_extra) & 0xFFFFFFFF)
        for i in range(max(0, quantidade)):
            fase = (i / max(1, quantidade) + t * (0.52 + rng.random() * 0.28)) % 1.0
            centro = _ponto_linha(p0, p1, fase)
            lado = (rng.random() - 0.5) * espalhamento
            raio = max(1, int(2 + rng.random() * 4))
            a = alpha * (0.20 + 0.65 * (1.0 - abs(fase - 0.5) * 1.3))
            pos = (int(centro[0] + perp[0] * lado), int(centro[1] + perp[1] * lado))
            pygame.draw.circle(overlay, _cor_rgba(paleta["brilho"], a), pos, raio)

    def _desenhar_laser(self, surface: pygame.Surface, anim: dict[str, object]) -> None:
        p0 = self._resolver_tela(anim.get("origem"))
        p1 = self._resolver_tela(anim.get("destino"))
        if p0 is None or p1 is None:
            return
        t = self._progresso(anim)
        paleta = self._paleta(anim)
        overlay = self._overlay(surface)

        entrada = _clamp(t / 0.16, 0.0, 1.0)
        saida = _clamp((1.0 - t) / 0.22, 0.0, 1.0)
        pulso = 0.72 + 0.28 * math.sin(t * math.pi * 18.0)
        alpha = 255 * _ease(entrada) * _ease(saida)
        largura = float(anim.get("largura") or 8.0) * pulso

        self._desenhar_linha_glow(overlay, p0, p1, paleta, largura=largura, alpha=alpha, abertura=_ease(entrada))
        self._desenhar_particulas_linha(overlay, p0, p1, paleta, t=t, quantidade=14, espalhamento=22, alpha=alpha * 0.65, seed_extra=int(anim.get("id", 0)))
        self._desenhar_circulo_glow(overlay, p0, paleta, 10 + 7 * _pulso(t, 2.0), alpha * 0.72)
        self._desenhar_circulo_glow(overlay, p1, paleta, 15 + 11 * _pulso(t, 1.5), alpha)

        surface.blit(overlay, (0, 0))

    def _desenhar_laser_linha(self, surface: pygame.Surface, anim: dict[str, object]) -> None:
        inicio = self._resolver_tela(anim.get("linha_inicio"))
        fim = self._resolver_tela(anim.get("linha_fim"))
        frente = self._resolver_tela(anim.get("frente_linha"))
        origem_movimento = self._resolver_tela(anim.get("origem_movimento"))
        if inicio is None or fim is None:
            return

        t = self._progresso(anim)
        paleta = self._paleta(anim)
        overlay = self._overlay(surface)

        if origem_movimento is not None and frente is not None and t < 0.42:
            local = _ease(_clamp(t / 0.38, 0.0, 1.0))
            atual = _ponto_linha(origem_movimento, frente, local)
            self._desenhar_linha_glow(overlay, origem_movimento, atual, paleta, largura=4, alpha=130 * (1.0 - t / 0.42), abertura=1.0)

        carga = _clamp((t - 0.34) / 0.18, 0.0, 1.0)
        if frente is not None and carga > 0.0:
            self._desenhar_circulo_glow(overlay, frente, paleta, 14 + 20 * carga, 230 * carga)

        fogo = _clamp((t - 0.48) / 0.22, 0.0, 1.0)
        saida = _clamp((1.0 - t) / 0.20, 0.0, 1.0)
        if fogo > 0.0 and saida > 0.0:
            largura = float(anim.get("largura") or 10.0) * (0.82 + 0.22 * math.sin(t * math.pi * 14.0))
            alpha = 255 * _ease(fogo) * _ease(saida)
            self._desenhar_linha_glow(overlay, inicio, fim, paleta, largura=largura, alpha=alpha, abertura=_ease(fogo))
            self._desenhar_particulas_linha(overlay, inicio, fim, paleta, t=t, quantidade=20, espalhamento=30, alpha=alpha * 0.58, seed_extra=71 + int(anim.get("id", 0)))
            if frente is not None:
                self._desenhar_linha_glow(overlay, frente, inicio, paleta, largura=max(3, largura * 0.55), alpha=alpha * 0.66, abertura=1.0)

        surface.blit(overlay, (0, 0))

    def _pontos_raio(self, p0: Vector2, p1: Vector2, t: float, intensidade: float, seed: int) -> list[Vector2]:
        dist = _distancia(p0, p1)
        segmentos = max(5, min(15, int(dist / 42)))
        perp = _perpendicular(p0, p1)
        rng = random.Random(seed)
        pontos = [p0]
        tremor = (0.30 + 0.70 * (1.0 - t)) * max(0.2, intensidade)
        for i in range(1, segmentos):
            k = i / segmentos
            base = _ponto_linha(p0, p1, k)
            amp = math.sin(k * math.pi) * min(46.0, max(12.0, dist * 0.055)) * tremor
            sinal = -1 if rng.random() < 0.5 else 1
            pontos.append((base[0] + perp[0] * amp * sinal * rng.uniform(0.45, 1.0), base[1] + perp[1] * amp * sinal * rng.uniform(0.45, 1.0)))
        pontos.append(p1)
        return pontos

    def _desenhar_raio(self, surface: pygame.Surface, anim: dict[str, object]) -> None:
        p0 = self._resolver_tela(anim.get("origem"))
        p1 = self._resolver_tela(anim.get("destino"))
        if p0 is None or p1 is None:
            return

        t = self._progresso(anim)
        paleta = self._paleta(anim)
        overlay = self._overlay(surface)
        seed = int(anim.get("id", 0)) * 1009 + int(t * 36)
        intensidade = float(anim.get("intensidade", 1.0) or 1.0)
        pontos = self._pontos_raio(p0, p1, t, intensidade, seed)
        entrada = _ease(_clamp(t / 0.10, 0.0, 1.0))
        saida = _ease(_clamp((1.0 - t) / 0.26, 0.0, 1.0))
        alpha = 255 * entrada * saida * (0.74 + 0.26 * math.sin(t * math.pi * 26.0))

        for largura, a, cor in (
            (14, 0.11, paleta["base"]),
            (8, 0.28, paleta["clara"]),
            (3, 0.95, paleta["brilho"]),
        ):
            for a0, a1 in zip(pontos, pontos[1:]):
                pygame.draw.line(overlay, _cor_rgba(cor, alpha * a), (int(a0[0]), int(a0[1])), (int(a1[0]), int(a1[1])), largura)

        # Ramificações curtas, para o raio parecer vivo sem depender de assets externos.
        rng = random.Random(seed + 9041)
        for idx in range(1, len(pontos) - 1):
            if rng.random() > 0.55:
                continue
            base = pontos[idx]
            ang = math.atan2(pontos[-1][1] - pontos[0][1], pontos[-1][0] - pontos[0][0]) + rng.choice((-1, 1)) * rng.uniform(0.65, 1.25)
            comp = rng.uniform(18, 44) * intensidade
            ponta = (base[0] + math.cos(ang) * comp, base[1] + math.sin(ang) * comp)
            pygame.draw.line(overlay, _cor_rgba(paleta["clara"], alpha * 0.30), (int(base[0]), int(base[1])), (int(ponta[0]), int(ponta[1])), 3)
            pygame.draw.line(overlay, _cor_rgba(paleta["brilho"], alpha * 0.70), (int(base[0]), int(base[1])), (int(ponta[0]), int(ponta[1])), 1)

        impacto = 18 + 16 * _pulso(t, 1.0)
        self._desenhar_circulo_glow(overlay, p1, paleta, impacto, alpha * 0.92)
        surface.blit(overlay, (0, 0))

    def _desenhar_jato_liquido(self, surface: pygame.Surface, anim: dict[str, object]) -> None:
        p0 = self._resolver_tela(anim.get("origem"))
        p1 = self._resolver_tela(anim.get("destino"))
        if p0 is None or p1 is None:
            return

        t = self._progresso(anim)
        paleta = self._paleta(anim)
        overlay = self._overlay(surface)
        abertura = _ease(_clamp(t / 0.20, 0.0, 1.0))
        saida = _ease(_clamp((1.0 - t) / 0.24, 0.0, 1.0))
        alpha = 240 * abertura * saida
        largura = float(anim.get("largura") or 11.0) * (0.86 + 0.18 * math.sin(t * math.pi * 10.0))

        perp = _perpendicular(p0, p1)
        dist = _distancia(p0, p1)
        curva = math.sin(t * math.pi * 2.0) * min(38.0, dist * 0.08)
        controle = ((p0[0] + p1[0]) * 0.5 + perp[0] * curva, (p0[1] + p1[1]) * 0.5 + perp[1] * curva)
        passos = max(8, min(28, int(dist / 28)))
        pontos = [_ponto_curva(p0, controle, p1, i / passos * abertura) for i in range(passos + 1)]
        pontos = [p for p in pontos if not (math.isnan(p[0]) or math.isnan(p[1]))]
        if len(pontos) < 2:
            return

        for fator, a, cor in (
            (3.5, 0.09, paleta["sombra"]),
            (2.15, 0.22, paleta["base"]),
            (1.20, 0.58, paleta["clara"]),
            (0.52, 0.80, paleta["brilho"]),
        ):
            w = max(1, int(largura * fator))
            for a0, a1 in zip(pontos, pontos[1:]):
                pygame.draw.line(overlay, _cor_rgba(cor, alpha * a), (int(a0[0]), int(a0[1])), (int(a1[0]), int(a1[1])), w)

        rng = random.Random(int(anim.get("id", 0)) * 97)
        for i in range(18):
            fase = (i / 18.0 + t * (0.9 + rng.random() * 0.4)) % max(0.001, abertura)
            base = _ponto_curva(p0, controle, p1, fase)
            lado = (rng.random() - 0.5) * largura * 3.8
            velocidade_y = math.sin(t * math.pi * 2 + i) * 4.0
            pos = (int(base[0] + perp[0] * lado), int(base[1] + perp[1] * lado + velocidade_y))
            raio = max(1, int(2 + rng.random() * 5))
            pygame.draw.circle(overlay, _cor_rgba(paleta["brilho"], alpha * 0.45), pos, raio)
            pygame.draw.circle(overlay, _cor_rgba(paleta["clara"], alpha * 0.28), pos, raio + 2, 1)

        self._desenhar_circulo_glow(overlay, p1, paleta, 13 + 10 * _pulso(t, 1.2), alpha * 0.70)
        surface.blit(overlay, (0, 0))
