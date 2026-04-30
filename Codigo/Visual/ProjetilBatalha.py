from __future__ import annotations

import math
import unicodedata
from pathlib import Path
from typing import Callable, Dict, Tuple

import pygame

from Codigo.Visual.AuxiliaresVisuais import CORES_TIPOS_ATAQUE, normalizar_tipo_ataque

Vector2 = Tuple[float, float]


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _interp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)


PALETA_TIPOS_ATAQUE = CORES_TIPOS_ATAQUE



PROJETEIS_ESPECIAIS: Dict[str, dict[str, object]] = {
    "biscoito": {
        "nome": "Biscoito",
        "caminho": "Recursos/Visual/Projeteis/biscoito.png",
        "velocidade": 8.0,
        "gira": True,
        "rotacao_base": 0.0,
    }
}


class ProjetilBatalha:
    def __init__(self, origem: Vector2, destino: Vector2, config: dict[str, object], duracao: float) -> None:
        self.origem = origem
        self.destino = destino
        self.config = dict(config or {})
        self.sprite = self.config.get("sprite")
        self.tempo = 0.0
        self.duracao = max(0.001, float(duracao or 0.0))

    @property
    def finalizado(self) -> bool:
        return self.tempo >= self.duracao

    def atualizar(self, dt: float) -> None:
        self.tempo += max(0.0, float(dt or 0.0))

    def desenhar(self, surface: pygame.Surface, posicao_tela: Callable[[Vector2], Vector2 | None]) -> None:
        t = _clamp(self.tempo / self.duracao, 0.0, 1.0)
        pos = posicao_tela((_interp(self.origem[0], self.destino[0], t), _interp(self.origem[1], self.destino[1], t)))
        if pos is None:
            return
        x, y = pos
        if isinstance(self.sprite, pygame.Surface):
            lado = max(20, min(50, int(max(self.sprite.get_width(), self.sprite.get_height()))))
            img = pygame.transform.smoothscale(self.sprite, (lado, lado)).convert_alpha()
            ang = float(self.config.get("rotacao_base", 0.0) or 0.0)
            if bool(self.config.get("gira", False)):
                ang += self.tempo * 720.0
            if abs(ang) > 0.001:
                img = pygame.transform.rotozoom(img, -ang, 1.0)
            surface.blit(img, img.get_rect(center=(int(x), int(y))))
            return
        cor = tuple(self.config.get("cor") or PALETA_TIPOS_ATAQUE["normal"])
        raio = max(7, int(13 + 4 * math.sin(t * math.pi)))
        brilho = tuple(min(255, int(c * 1.25 + 32)) for c in cor)
        pygame.draw.circle(surface, (*cor, 230), (int(x), int(y)), raio)
        pygame.draw.circle(surface, (*brilho, 235), (int(x - raio * 0.25), int(y - raio * 0.25)), max(3, raio // 2))


class GerenciadorProjeteisBatalha:
    _cache_projeteis: dict[str, pygame.Surface | None] = {}

    def __init__(self, posicao_tela: Callable[[Vector2], Vector2 | None]) -> None:
        self._posicao_tela = posicao_tela
        self.projeteis: list[ProjetilBatalha] = []

    def animar_lancar(self, origem: Vector2, destino: Vector2, sprite=None, duracao=None, tipo_ataque=None, velocidade=None):
        config = self._config_projetil(sprite, tipo_ataque=tipo_ataque, velocidade=velocidade)
        dist = max(0.001, math.hypot(destino[0] - origem[0], destino[1] - origem[1]))
        duracao_real = float(duracao or 0.0)
        if duracao_real <= 0:
            vel = float(config.get("velocidade") or 0.0)
            duracao_real = _clamp(dist / vel if vel > 0 else 0.46, 0.18, 1.20)
        projetil = ProjetilBatalha(origem, destino, config, duracao_real)
        self.projeteis.append(projetil)
        return {"tipo": "projetil", "projetil": projetil, "tempo": 0.0, "duracao": duracao_real, "bloqueante": True}

    def atualizar(self, dt: float) -> None:
        for projetil in list(self.projeteis):
            projetil.atualizar(dt)
        self.projeteis = [p for p in self.projeteis if not p.finalizado]

    def desenhar(self, surface: pygame.Surface) -> None:
        for projetil in list(self.projeteis):
            projetil.desenhar(surface, self._posicao_tela)

    def esta_ocupado(self) -> bool:
        return bool(self.projeteis)

    def _config_projetil(self, sprite=None, tipo_ataque=None, velocidade=None):
        dados = dict(sprite or {}) if isinstance(sprite, dict) else {}
        nome = dados.get("nome") or dados.get("projetil") or dados.get("codigo") or dados.get("code") or (sprite if isinstance(sprite, str) else None)
        chave = _normalizar_nome(nome)
        base = dict(PROJETEIS_ESPECIAIS.get(chave) or {})
        caminho = dados.get("caminho") or dados.get("arquivo") or base.get("caminho") or base.get("arquivo")
        if caminho is None and chave in PROJETEIS_ESPECIAIS:
            caminho = self._buscar_arquivo_projetil(base.get("nome") or nome)
        elif caminho is not None and not Path(str(caminho)).is_absolute() and Path(str(caminho)).parent == Path("."):
            caminho = self._buscar_arquivo_projetil(caminho) or caminho
        config = {
            "nome": str(base.get("nome") or nome or "padrao"),
            "velocidade": float(velocidade or dados.get("velocidade") or base.get("velocidade") or 7.0),
            "gira": bool(dados.get("gira", base.get("gira", False))),
            "rotacao_base": float(dados.get("rotacao_base", base.get("rotacao_base", 0.0)) or 0.0),
            "tipo_ataque": normalizar_tipo_ataque(tipo_ataque or dados.get("tipo") or dados.get("tipo_ataque") or "normal"),
            "sprite": self._carregar_projetil(caminho),
        }
        config["cor"] = PALETA_TIPOS_ATAQUE.get(config["tipo_ataque"], PALETA_TIPOS_ATAQUE["normal"])
        return config

    def _buscar_arquivo_projetil(self, nome):
        chave = _normalizar_nome(nome)
        if not chave:
            return None
        cache_key = f"_busca:{chave}"
        if cache_key in self._cache_projeteis:
            return None
        base = Path.cwd() / "Recursos" / "Visual" / "Projeteis"
        try:
            for caminho in base.rglob("*"):
                if caminho.is_file() and caminho.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"} and _normalizar_nome(caminho.stem) == chave:
                    return caminho
        except Exception:
            pass
        self._cache_projeteis[cache_key] = None
        return None

    def _carregar_projetil(self, sprite):
        if not sprite:
            return None
        path = Path(str(sprite))
        if not path.is_absolute():
            path = Path.cwd() / path
        chave = str(path)
        if chave not in self._cache_projeteis:
            try:
                self._cache_projeteis[chave] = pygame.image.load(str(path)).convert_alpha()
            except Exception:
                self._cache_projeteis[chave] = None
        return self._cache_projeteis.get(chave)
