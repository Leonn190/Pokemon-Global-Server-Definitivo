from __future__ import annotations

import math
import random
import unicodedata
from typing import Dict, Tuple

import pygame


class ClimaBatalha:
    """Filtro visual de clima especifico da batalha."""

    TEMPO_TRANSICAO = 6.0

    _TODOS = (
        "chuva",
        "tempestade_raios",
        "nevasca",
        "tempestade_areia",
        "sol_forte",
        "noite_densa",
        "chuva_acida",
        "nevoa",
    )

    _ALIASES = {
        "35": "chuva",
        "chuva": "chuva",
        "36": "sol_forte",
        "sol_forte": "sol_forte",
        "37": "nevasca",
        "nevasca": "nevasca",
        "38": "tempestade_areia",
        "tempestade_areia": "tempestade_areia",
        "tempestade_de_areia": "tempestade_areia",
        "tempestade_area": "tempestade_areia",
        "tempestade_de_area": "tempestade_areia",
        "39": "nevoa",
        "nevoa": "nevoa",
        "40": "gravidade_anomala",
        "gravidade_anomala": "gravidade_anomala",
        "41": "chuva_acida",
        "chuva_acida": "chuva_acida",
        "42": "tempestade_raios",
        "tempestade_raios": "tempestade_raios",
        "tempestade_de_raios": "tempestade_raios",
        "43": "noite_densa",
        "noite_densa": "noite_densa",
    }

    def __init__(self) -> None:
        self._tempo = 0.0
        self._clima_alvo: str | None = None
        self._powers: Dict[str, float] = {nome: 0.0 for nome in self._TODOS}
        self._lightning_flash = 0.0
        self._rain_particles: list[Dict[str, float]] = []
        self._snow_particles: list[Dict[str, float]] = []
        self._sand_particles: list[Dict[str, float]] = []
        self._fog_particles: list[Dict[str, float]] = []
        self._size = (0, 0)
        self._layer_cache: pygame.Surface | None = None
        self._layer_cache_size = (0, 0)
        self._uniformes_atuais: Dict[str, object] = self._uniformes_vazios()

    @staticmethod
    def _clamp(v: float, a: float, b: float) -> float:
        return a if v < a else b if v > b else v

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @classmethod
    def _normalizar_nome(cls, valor: object) -> str | None:
        if isinstance(valor, dict):
            for chave in ("nome", "clima", "clima_nome", "Nome", "name", "code", "id", "ID"):
                if valor.get(chave) not in (None, ""):
                    return cls._normalizar_nome(valor.get(chave))
            if isinstance(valor.get("clima_atual"), (dict, str, int)):
                return cls._normalizar_nome(valor.get("clima_atual"))
            return None
        if valor in (None, "", False):
            return None

        texto = str(valor).strip()
        if not texto:
            return None
        sem_acento = "".join(
            c for c in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(c)
        )
        chave = "_".join(sem_acento.lower().replace("-", " ").split())
        chave = "".join(c for c in chave if c.isalnum() or c == "_")
        return cls._ALIASES.get(chave, chave if chave in cls._ALIASES.values() else None)

    @classmethod
    def clima_visual(cls, clima: object) -> str | None:
        nome = cls._normalizar_nome(clima)
        if nome == "gravidade_anomala":
            return None
        return nome if nome in cls._TODOS else None

    def definir_clima(self, clima: object) -> None:
        self._clima_alvo = self.clima_visual(clima)

    def _uniformes_vazios(self) -> Dict[str, object]:
        return {
            "tipo": "batalha",
            "ativo": False,
            "player_uv": (0.5, 0.5),
            "tint": (1.0, 1.0, 1.0),
            "darkness": 0.0,
            "rain_power": 0.0,
            "lightning": 0.0,
            "star_strength": 0.0,
            "inside": False,
            "time": self._tempo,
            "biome_mode": 0.0,
            "biome_power": 0.0,
            "battle_sun_power": 0.0,
            "battle_sand_power": 0.0,
            "battle_fog_power": 0.0,
            "battle_acid_power": 0.0,
        }

    def _atualizar_transicao(self, dt: float) -> None:
        passo = max(0.0, float(dt or 0.0)) / max(0.001, self.TEMPO_TRANSICAO)
        for nome in self._TODOS:
            alvo = 1.0 if nome == self._clima_alvo else 0.0
            atual = float(self._powers.get(nome, 0.0) or 0.0)
            if atual < alvo:
                atual = min(alvo, atual + passo)
            elif atual > alvo:
                atual = max(alvo, atual - passo)
            self._powers[nome] = self._clamp(atual, 0.0, 1.0)

    @staticmethod
    def _make_rain_particle(largura: int, altura: int) -> Dict[str, float]:
        return {
            "x": random.uniform(-220, largura + 220),
            "y": random.uniform(-altura, altura),
            "dx": random.uniform(170.0, 330.0),
            "dy": random.uniform(0.94, 1.12),
        }

    @staticmethod
    def _make_snow_particle(largura: int, altura: int) -> Dict[str, float]:
        return {
            "x": random.uniform(-40, largura + 40),
            "y": random.uniform(-altura, altura),
            "sx": random.uniform(-18.0, 18.0),
            "sy": random.uniform(95.0, 245.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(1.8, 5.8),
        }

    @staticmethod
    def _make_sand_particle(largura: int, altura: int) -> Dict[str, float]:
        return {
            "x": random.uniform(-80, largura + 160),
            "y": random.uniform(35, altura - 25),
            "speed": random.uniform(280.0, 760.0),
            "length": random.uniform(18.0, 58.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(1.0, 3.2),
        }

    @staticmethod
    def _make_fog_particle(largura: int, altura: int) -> Dict[str, float]:
        return {
            "x": random.uniform(-120, largura + 120),
            "y": random.uniform(0, altura),
            "speed": random.uniform(10.0, 42.0),
            "w": random.uniform(largura * 0.18, largura * 0.42),
            "h": random.uniform(24.0, 72.0),
            "alpha": random.uniform(16.0, 42.0),
        }

    def _ensure_population(self, lista: list[Dict[str, float]], target: int, maker, largura: int, altura: int) -> None:
        while len(lista) < target:
            lista.append(maker(largura, altura))
        if len(lista) > target:
            del lista[target:]

    def _atualizar_particulas(self, dt: float, tamanho_tela: Tuple[int, int]) -> None:
        largura = max(1, int(tamanho_tela[0]))
        altura = max(1, int(tamanho_tela[1]))
        if self._size != (largura, altura):
            self._size = (largura, altura)
            self._rain_particles = []
            self._snow_particles = []
            self._sand_particles = []
            self._fog_particles = []

        chuva = self._clamp(self._powers["chuva"] * 0.82 + self._powers["tempestade_raios"] + self._powers["chuva_acida"] * 0.88, 0.0, 1.0)
        neve = self._powers["nevasca"]
        areia = self._powers["tempestade_areia"]
        nevoa = self._powers["nevoa"]

        self._ensure_population(self._rain_particles, int(self._lerp(0, 760, chuva)), self._make_rain_particle, largura, altura)
        self._ensure_population(self._snow_particles, int(self._lerp(0, 320, neve)), self._make_snow_particle, largura, altura)
        self._ensure_population(self._sand_particles, int(self._lerp(0, 240, areia)), self._make_sand_particle, largura, altura)
        self._ensure_population(self._fog_particles, int(self._lerp(0, 34, nevoa)), self._make_fog_particle, largura, altura)

        rain_speed = self._lerp(980.0, 2050.0, chuva)
        rain_len = self._lerp(22.0, 54.0, chuva)
        for drop in self._rain_particles:
            drop["x"] += float(drop["dx"]) * dt
            drop["y"] += rain_speed * float(drop["dy"]) * dt
            if drop["y"] > altura + rain_len or drop["x"] > largura + 240:
                drop.update(self._make_rain_particle(largura, altura))
                drop["x"] = random.uniform(-240, largura)
                drop["y"] = random.uniform(-240, -20)

        ticks = pygame.time.get_ticks() * 0.001
        for part in self._snow_particles:
            part["phase"] += dt * 2.8
            part["x"] += (math.sin(ticks * 1.8 + part["phase"]) * 28.0 + part["sx"]) * dt
            part["y"] += part["sy"] * dt
            if part["y"] > altura + 22 or part["x"] < -70 or part["x"] > largura + 70:
                part.update(self._make_snow_particle(largura, altura))
                part["y"] = random.uniform(-160, -12)

        for part in self._sand_particles:
            part["phase"] += dt * 3.0
            part["x"] -= part["speed"] * dt
            part["y"] += math.sin(ticks * 4.0 + part["phase"]) * 18.0 * dt
            if part["x"] < -120 or part["y"] < -30 or part["y"] > altura + 30:
                part.update(self._make_sand_particle(largura, altura))
                part["x"] = random.uniform(largura + 20, largura + 180)

        for part in self._fog_particles:
            part["x"] -= part["speed"] * dt
            if part["x"] < -float(part["w"]) - 80:
                part.update(self._make_fog_particle(largura, altura))
                part["x"] = random.uniform(largura + 20, largura + 180)

        storm = self._powers["tempestade_raios"]
        if storm > 0.01:
            self._lightning_flash = max(0.0, self._lightning_flash - dt * 2.0)
            chance = self._lerp(0.22, 1.85, storm)
            if self._lightning_flash <= 0.0 and random.random() < dt * chance:
                self._lightning_flash = random.uniform(0.65, 1.25)
        else:
            self._lightning_flash = max(0.0, self._lightning_flash - dt * 3.0)

    def coletar_uniformes(self, tamanho_tela: Tuple[int, int], clima: object, dt: float) -> Dict[str, object]:
        self._tempo += max(0.0, float(dt or 0.0))
        self.definir_clima(clima)
        self._atualizar_transicao(dt)
        self._atualizar_particulas(max(0.0, float(dt or 0.0)), tamanho_tela)

        chuva = self._clamp(self._powers["chuva"] * 0.84 + self._powers["tempestade_raios"] + self._powers["chuva_acida"] * 0.90, 0.0, 1.0)
        tempestade = self._powers["tempestade_raios"]
        neve = self._powers["nevasca"]
        areia = self._powers["tempestade_areia"]
        sol = self._powers["sol_forte"]
        noite = self._powers["noite_densa"]
        acid = self._powers["chuva_acida"]
        nevoa = self._powers["nevoa"]
        ativo = max(self._powers.values(), default=0.0) > 0.001 or self._lightning_flash > 0.001

        tint = [1.0, 1.0, 1.0]
        for cor, p in (
            ((0.72, 0.82, 1.00), chuva * 0.36),
            ((0.77, 0.98, 0.70), acid * 0.48),
            ((0.88, 0.96, 1.00), neve * 0.34),
            ((0.96, 0.84, 0.62), areia * 0.32),
            ((1.00, 0.92, 0.74), sol * 0.42),
            ((0.36, 0.42, 0.64), noite * 0.78),
            ((0.78, 0.82, 0.80), nevoa * 0.42),
        ):
            tint[0] = self._lerp(tint[0], cor[0], self._clamp(p, 0.0, 1.0))
            tint[1] = self._lerp(tint[1], cor[1], self._clamp(p, 0.0, 1.0))
            tint[2] = self._lerp(tint[2], cor[2], self._clamp(p, 0.0, 1.0))

        biome_mode = 1.0 if neve >= areia else 3.0
        biome_power = max(neve * 0.92, areia * 0.60)
        darkness = self._clamp(noite * 0.82 + chuva * 0.12 + nevoa * 0.10 - sol * 0.12, 0.0, 0.88)

        self._uniformes_atuais = {
            "tipo": "batalha",
            "ativo": ativo,
            "player_uv": (0.5, 0.5),
            "tint": tuple(tint),
            "darkness": darkness,
            "rain_power": chuva,
            "lightning": self._lightning_flash * tempestade,
            "star_strength": noite,
            "inside": False,
            "time": self._tempo,
            "biome_mode": biome_mode,
            "biome_power": biome_power,
            "battle_sun_power": sol,
            "battle_sand_power": areia,
            "battle_fog_power": nevoa,
            "battle_acid_power": acid,
        }
        return dict(self._uniformes_atuais)

    def uniformes_atuais(self) -> Dict[str, object]:
        return dict(self._uniformes_atuais)

    def _camada(self, surface: pygame.Surface) -> pygame.Surface:
        largura, altura = surface.get_size()
        if self._layer_cache is None or self._layer_cache_size != (largura, altura):
            self._layer_cache = pygame.Surface((largura, altura), pygame.SRCALPHA)
            self._layer_cache_size = (largura, altura)
        self._layer_cache.fill((0, 0, 0, 0))
        return self._layer_cache

    def desenhar_base(self, surface: pygame.Surface) -> None:
        if not isinstance(surface, pygame.Surface):
            return
        if not bool(self._uniformes_atuais.get("ativo", False)):
            return

        largura, altura = surface.get_size()
        camada = self._camada(surface)

        noite = self._powers["noite_densa"]
        if noite > 0.001:
            camada.fill((12, 18, 38, int(self._lerp(0, 78, noite))))

        sol = self._powers["sol_forte"]
        if sol > 0.001:
            alpha = int(self._lerp(0, 54, sol))
            camada.fill((255, 238, 176, alpha), special_flags=pygame.BLEND_RGBA_ADD)
            for idx in range(5):
                x = int((idx * largura * 0.24 + (self._tempo * 18.0)) % (largura + 260)) - 260
                pts = [(x, 0), (x + 92, 0), (x + 360, altura), (x + 210, altura)]
                pygame.draw.polygon(camada, (255, 248, 202, int(20 * sol)), pts)

        chuva = self._clamp(self._powers["chuva"] * 0.84 + self._powers["tempestade_raios"] + self._powers["chuva_acida"] * 0.90, 0.0, 1.0)
        if chuva > 0.001:
            acid = self._powers["chuva_acida"]
            alpha = int(self._lerp(70, 205, chuva))
            cor = (135, 244, 110, alpha) if acid >= max(self._powers["chuva"], self._powers["tempestade_raios"]) else (205, 223, 255, alpha)
            comprimento = int(self._lerp(22, 54, chuva))
            espessura = 3 if chuva < 0.74 else 4
            for drop in self._rain_particles:
                x1 = int(drop["x"])
                y1 = int(drop["y"])
                pygame.draw.line(camada, cor, (x1, y1), (int(x1 - comprimento * 0.40), int(y1 - comprimento)), espessura)

        neve = self._powers["nevasca"]
        if neve > 0.001:
            alpha = int(self._lerp(80, 220, neve))
            for part in self._snow_particles:
                raio = max(1, int(part["size"] + neve * 1.6))
                pygame.draw.circle(camada, (245, 248, 255, alpha), (int(part["x"]), int(part["y"])), raio)

        areia = self._powers["tempestade_areia"]
        if areia > 0.001:
            alpha = int(self._lerp(26, 130, areia))
            for part in self._sand_particles:
                x1 = int(part["x"])
                y1 = int(part["y"])
                x2 = int(x1 + part["length"])
                y2 = int(y1 - 4)
                pygame.draw.line(camada, (226, 204, 150, alpha), (x1, y1), (x2, y2), max(1, int(part["size"])))

        nevoa = self._powers["nevoa"]
        if nevoa > 0.001:
            camada.fill((210, 218, 218, int(self._lerp(0, 42, nevoa))), special_flags=pygame.BLEND_RGBA_ADD)
            for part in self._fog_particles:
                rect = pygame.Rect(0, 0, int(part["w"]), int(part["h"]))
                rect.center = (int(part["x"]), int(part["y"]))
                pygame.draw.ellipse(camada, (218, 224, 224, int(part["alpha"] * nevoa)), rect)

        surface.blit(camada, (0, 0))
