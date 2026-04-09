from __future__ import annotations

import math
import random
from typing import Dict, Tuple

import pygame


class FiltroCamera:
    INICIO_ESCURECER_MIN = 17 * 60
    ESCURO_MAXIMO_MIN = 25 * 60
    INICIO_CLAREAR_MIN = 25 * 60
    FIM_CLAREAR_MIN = 32 * 60

    _BIOMA_POR_BLOCO = {
        5: "deserto",
        6: "neve",
        7: "magico",
        8: "vulcao",
        9: "pantano",
    }
    _BIOME_MODE_VALUE = {
        "normal": 0.0,
        "neve": 1.0,
        "vulcao": 2.0,
        "deserto": 3.0,
        "magico": 4.0,
        "pantano": 5.0,
    }
    _BIOMAS_ESPECIAIS = ("neve", "vulcao", "deserto", "magico", "pantano")
    _BIOMA_GAIN_PER_SEC = 0.01 / 5.0
    _BIOMA_DECAY_PER_SEC = 0.02

    @classmethod
    def reconfigurar_iluminacao(cls, dados: Dict[str, object]) -> None:
        ini_escurecer = int(dados.get("inicio_escurecer_hora", 17) or 17) * 60 + int(dados.get("inicio_escurecer_minuto", 0) or 0)
        escuro_max = int(dados.get("escuro_maximo_hora", 1) or 1) * 60 + int(dados.get("escuro_maximo_minuto", 0) or 0)
        ini_clarear = int(dados.get("inicio_clarear_hora", 1) or 1) * 60 + int(dados.get("inicio_clarear_minuto", 0) or 0)
        fim_clarear = int(dados.get("fim_clarear_hora", 8) or 8) * 60 + int(dados.get("fim_clarear_minuto", 0) or 0)

        cls.INICIO_ESCURECER_MIN = max(0, ini_escurecer)
        cls.ESCURO_MAXIMO_MIN = max(cls.INICIO_ESCURECER_MIN + 1, escuro_max + (1440 if escuro_max < cls.INICIO_ESCURECER_MIN else 0))
        cls.INICIO_CLAREAR_MIN = max(cls.ESCURO_MAXIMO_MIN, ini_clarear + (1440 if ini_clarear < cls.INICIO_ESCURECER_MIN else 0))
        cls.FIM_CLAREAR_MIN = max(cls.INICIO_CLAREAR_MIN + 1, fim_clarear + (1440 if fim_clarear < cls.INICIO_ESCURECER_MIN else 0))

    @classmethod
    def biome_por_bloco(cls, bloco: object) -> str:
        try:
            return cls._BIOMA_POR_BLOCO.get(int(bloco), "normal")
        except Exception:
            return "normal"

    @classmethod
    def biome_mode_value(cls, biome: str) -> float:
        return float(cls._BIOME_MODE_VALUE.get(str(biome or "normal"), 0.0))

    def __init__(self) -> None:
        self._tempo = 0.0
        self._rain_power = 0.0
        self._lightning_flash = 0.0
        self._rain_particles: list[Dict[str, float]] = []
        self._rain_size = (0, 0)
        self._rain_layer_cache: pygame.Surface | None = None
        self._rain_layer_cache_size = (0, 0)

        self._biome_type = "normal"
        self._biome_powers: Dict[str, float] = {nome: 0.0 for nome in self._BIOMAS_ESPECIAIS}
        self._fx_particles: list[Dict[str, float]] = []
        self._fx_particles_biome = "normal"
        self._biome_size = (0, 0)
        self._biome_layer_cache: pygame.Surface | None = None
        self._biome_layer_cache_size = (0, 0)

        self._uniformes_atuais: Dict[str, object] = {
            "tipo": "mundo",
            "player_uv": (0.5, 0.5),
            "tint": (1.0, 1.0, 1.0),
            "darkness": 0.0,
            "rain_power": 0.0,
            "lightning": 0.0,
            "star_strength": 0.0,
            "inside": False,
            "time": 0.0,
            "biome_mode": 0.0,
            "biome_power": 0.0,
        }

    @staticmethod
    def _clamp(v: float, a: float, b: float) -> float:
        return a if v < a else b if v > b else v

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @classmethod
    def _fator_noite(cls, hora: int, minuto: int) -> float:
        m = int(hora) * 60 + int(minuto)
        if m < cls.INICIO_ESCURECER_MIN:
            m += 1440
        if cls.FIM_CLAREAR_MIN <= m < (cls.INICIO_ESCURECER_MIN + 1440):
            return 0.0
        if cls.INICIO_ESCURECER_MIN <= m < cls.ESCURO_MAXIMO_MIN:
            dur = max(1, cls.ESCURO_MAXIMO_MIN - cls.INICIO_ESCURECER_MIN)
            return cls._clamp((m - cls.INICIO_ESCURECER_MIN) / float(dur), 0.0, 1.0)
        if cls.ESCURO_MAXIMO_MIN <= m < cls.INICIO_CLAREAR_MIN:
            return 1.0
        if cls.INICIO_CLAREAR_MIN <= m < cls.FIM_CLAREAR_MIN:
            dur = max(1, cls.FIM_CLAREAR_MIN - cls.INICIO_CLAREAR_MIN)
            return cls._clamp(1.0 - ((m - cls.INICIO_CLAREAR_MIN) / float(dur)), 0.0, 1.0)
        return 0.0

    def _player_uv(self, tamanho_tela: Tuple[int, int], camera, entidade_main) -> Tuple[float, float]:
        largura = max(1, int(tamanho_tela[0]))
        altura = max(1, int(tamanho_tela[1]))
        if camera is None or entidade_main is None or not hasattr(entidade_main, "Posicao"):
            return (0.5, 0.5)
        if not callable(getattr(camera, "mundo_para_tela_px", None)):
            return (0.5, 0.5)

        px, py = camera.mundo_para_tela_px(tuple(entidade_main.Posicao))
        return (
            self._clamp(float(px) / float(largura), 0.0, 1.0),
            self._clamp(float(py) / float(altura), 0.0, 1.0),
        )

    def _rain_profile(self) -> Dict[str, float]:
        p = float(self._rain_power)
        if p <= 0.0:
            return {"target": 0, "speed": 0.0, "length": 0, "thickness": 0}
        return {
            "target": int(self._lerp(45, 680, p)),
            "speed": self._lerp(380.0, 1800.0, p),
            "length": int(self._lerp(10, 46, p)),
            "thickness": 2 if p < 0.35 else 3 if p < 0.76 else 4,
        }

    @staticmethod
    def _make_rain_particle(largura: int, altura: int) -> Dict[str, float]:
        return {
            "x": random.uniform(-180, largura + 180),
            "y": random.uniform(-altura, altura),
            "dx": random.uniform(165.0, 320.0),
            "dy": random.uniform(0.92, 1.10),
        }

    def _ensure_rain_population(self, target: int, largura: int, altura: int) -> None:
        while len(self._rain_particles) < target:
            self._rain_particles.append(self._make_rain_particle(largura, altura))
        if len(self._rain_particles) > target:
            del self._rain_particles[target:]

    def _atualizar_estado_chuva(self, chuva_n: float, dt: float, tamanho_tela: Tuple[int, int], dentro_estadio: bool) -> None:
        largura = max(1, int(tamanho_tela[0]))
        altura = max(1, int(tamanho_tela[1]))
        if self._rain_size != (largura, altura):
            self._rain_size = (largura, altura)
            if self._rain_particles:
                self._rain_particles = [self._make_rain_particle(largura, altura) for _ in range(len(self._rain_particles))]

        self._rain_power = 0.0 if dentro_estadio else self._clamp(float(chuva_n), 0.0, 1.0)
        profile = self._rain_profile()
        self._ensure_rain_population(int(profile["target"]), largura, altura)

        if int(profile["target"]) <= 0:
            self._lightning_flash = max(0.0, self._lightning_flash - dt * 2.3)
            return

        for drop in self._rain_particles:
            drop["x"] += float(drop["dx"]) * dt
            drop["y"] += float(profile["speed"]) * float(drop["dy"]) * dt
            if float(drop["y"]) > altura + float(profile["length"]) or float(drop["x"]) > largura + 220:
                drop.update(self._make_rain_particle(largura, altura))
                drop["x"] = random.uniform(-220, largura)
                drop["y"] = random.uniform(-220, -20)

        if self._rain_power >= 0.64:
            self._lightning_flash = max(0.0, self._lightning_flash - dt * 2.0)
            chance = self._lerp(0.12, 1.55, (self._rain_power - 0.64) / 0.36)
            if self._lightning_flash <= 0.0 and random.random() < dt * chance:
                self._lightning_flash = random.uniform(0.55, 1.25)
        else:
            self._lightning_flash = max(0.0, self._lightning_flash - dt * 2.6)

    @staticmethod
    def _make_fx_particle(mode: str, largura: int, altura: int) -> Dict[str, float]:
        if mode == "neve":
            return {
                "x": random.uniform(-30, largura + 30),
                "y": random.uniform(-altura, altura),
                "sx": random.uniform(1.8, 4.8),
                "sy": random.uniform(36.0, 160.0),
                "phase": random.uniform(0.0, math.tau),
                "size": random.uniform(1.4, 4.6),
            }
        if mode == "vulcao":
            return {
                "x": random.uniform(-40, largura + 40),
                "y": random.uniform(altura * 0.52, altura + 40),
                "sx": random.uniform(-22.0, 22.0),
                "sy": random.uniform(-120.0, -44.0),
                "phase": random.uniform(0.0, math.tau),
                "size": random.uniform(1.4, 3.8),
            }
        if mode == "deserto":
            return {
                "x": random.uniform(-60, largura + 60),
                "y": random.uniform(40, altura - 20),
                "sx": random.uniform(30.0, 96.0),
                "sy": random.uniform(-6.0, 12.0),
                "phase": random.uniform(0.0, math.tau),
                "size": random.uniform(1.2, 3.0),
            }
        if mode == "magico":
            return {
                "x": random.uniform(-20, largura + 20),
                "y": random.uniform(30, altura + 20),
                "sx": random.uniform(-22.0, 22.0),
                "sy": random.uniform(-18.0, 18.0),
                "phase": random.uniform(0.0, math.tau),
                "size": random.uniform(1.4, 3.5),
            }
        if mode == "pantano":
            return {
                "x": random.uniform(-40, largura + 40),
                "y": random.uniform(altura * 0.30, altura + 20),
                "sx": random.uniform(-10.0, 10.0),
                "sy": random.uniform(-22.0, 10.0),
                "phase": random.uniform(0.0, math.tau),
                "size": random.uniform(6.0, 18.0),
            }
        return {
            "x": random.uniform(-20, largura + 20),
            "y": random.uniform(-20, altura + 20),
            "sx": 0.0,
            "sy": 0.0,
            "phase": 0.0,
            "size": 0.0,
        }

    def _biome_particle_target(self, mode: str, power: float) -> int:
        p = self._clamp(float(power), 0.0, 1.0)
        if mode == "normal" or p <= 0.0:
            return 0
        if mode == "neve":
            return int(self._lerp(35, 260, p))
        if mode == "vulcao":
            return int(self._lerp(16, 150, p))
        if mode == "deserto":
            return int(self._lerp(24, 180, p))
        if mode == "magico":
            return int(self._lerp(18, 120, p))
        return int(self._lerp(12, 84, p))

    def _ensure_fx_population(self, target: int, mode: str, largura: int, altura: int) -> None:
        if self._fx_particles_biome != mode:
            self._fx_particles_biome = mode
            self._fx_particles = []
        while len(self._fx_particles) < target:
            self._fx_particles.append(self._make_fx_particle(mode, largura, altura))
        if len(self._fx_particles) > target:
            del self._fx_particles[target:]

    def _atualizar_estado_bioma(self, biome_atual: str, dt: float, tamanho_tela: Tuple[int, int], dentro_estadio: bool) -> None:
        largura = max(1, int(tamanho_tela[0]))
        altura = max(1, int(tamanho_tela[1]))
        if self._biome_size != (largura, altura):
            self._biome_size = (largura, altura)
            self._fx_particles = []
            self._fx_particles_biome = "normal"

        biome_norm = str(biome_atual or "normal")
        if dentro_estadio or biome_norm not in self._BIOME_MODE_VALUE:
            biome_norm = "normal"

        ganho = max(0.0, float(dt)) * self._BIOMA_GAIN_PER_SEC
        perda = max(0.0, float(dt)) * self._BIOMA_DECAY_PER_SEC
        for nome in self._BIOMAS_ESPECIAIS:
            atual = float(self._biome_powers.get(nome, 0.0) or 0.0)
            if nome == biome_norm:
                atual += ganho
            else:
                atual -= perda
            self._biome_powers[nome] = self._clamp(atual, 0.0, 1.0)

        if dentro_estadio:
            self._biome_type = "normal"
        elif biome_norm in self._BIOMAS_ESPECIAIS:
            self._biome_type = biome_norm
        else:
            self._biome_type = max(self._biome_powers, key=self._biome_powers.get, default="normal")
            if float(self._biome_powers.get(self._biome_type, 0.0) or 0.0) <= 0.0:
                self._biome_type = "normal"

        if self._biome_type == "normal":
            self._fx_particles = []
            self._fx_particles_biome = "normal"
            return

        target = self._biome_particle_target(self._biome_type, float(self._biome_powers.get(self._biome_type, 0.0) or 0.0))
        self._ensure_fx_population(target, self._biome_type, largura, altura)
        ticks = pygame.time.get_ticks() * 0.001

        for part in self._fx_particles:
            if self._biome_type == "neve":
                part["phase"] += dt * 2.2
                part["x"] += (math.sin(ticks * 1.7 + part["phase"]) * 18.0 + part["sx"]) * dt
                part["y"] += part["sy"] * dt
                if part["y"] > altura + 18 or part["x"] < -60 or part["x"] > largura + 60:
                    part.update(self._make_fx_particle("neve", largura, altura))
                    part["x"] = random.uniform(-20, largura + 20)
                    part["y"] = random.uniform(-140, -12)
            elif self._biome_type == "vulcao":
                part["phase"] += dt * 4.0
                part["x"] += (part["sx"] + math.sin(ticks * 3.2 + part["phase"]) * 12.0) * dt
                part["y"] += part["sy"] * dt
                if part["y"] < -20 or part["x"] < -60 or part["x"] > largura + 60:
                    part.update(self._make_fx_particle("vulcao", largura, altura))
            elif self._biome_type == "deserto":
                part["phase"] += dt * 2.4
                part["x"] += (part["sx"] + math.sin(ticks * 2.0 + part["phase"]) * 20.0) * dt
                part["y"] += (part["sy"] + math.sin(ticks * 1.7 + part["phase"]) * 5.0) * dt
                if part["x"] > largura + 80 or part["y"] < -30 or part["y"] > altura + 30:
                    part.update(self._make_fx_particle("deserto", largura, altura))
                    part["x"] = random.uniform(-100, -10)
            elif self._biome_type == "magico":
                part["phase"] += dt * 2.8
                part["x"] += math.sin(ticks * 1.4 + part["phase"]) * 16.0 * dt + part["sx"] * dt
                part["y"] += math.cos(ticks * 1.9 + part["phase"]) * 10.0 * dt + part["sy"] * dt
                if part["x"] < -30 or part["x"] > largura + 30 or part["y"] < -30 or part["y"] > altura + 30:
                    part.update(self._make_fx_particle("magico", largura, altura))
            elif self._biome_type == "pantano":
                part["phase"] += dt * 1.2
                part["x"] += math.sin(ticks * 0.9 + part["phase"]) * 7.0 * dt + part["sx"] * dt
                part["y"] += math.cos(ticks * 1.1 + part["phase"]) * 4.0 * dt + part["sy"] * dt
                if part["x"] < -80 or part["x"] > largura + 80 or part["y"] < altura * 0.20 or part["y"] > altura + 50:
                    part.update(self._make_fx_particle("pantano", largura, altura))

    def coletar_uniformes(
        self,
        tamanho_tela: Tuple[int, int],
        camera,
        entidade_main,
        tempo_mundo: Dict[str, object],
        dt: float,
        dentro_estadio: bool = False,
        biome_atual: str = "normal",
    ) -> Dict[str, object]:
        self._tempo += max(0.0, float(dt))
        hora = int(tempo_mundo.get("hora", 8) or 8)
        minuto = int(tempo_mundo.get("minuto", 0) or 0)
        chuva = int(max(0, min(100, int(tempo_mundo.get("chuva_intensidade", 0) or 0))))

        noite = self._fator_noite(hora, minuto)
        chuva_n = 0.0 if dentro_estadio else (chuva / 100.0)
        self._atualizar_estado_chuva(chuva_n, max(0.0, float(dt)), tamanho_tela, dentro_estadio)
        self._atualizar_estado_bioma(str(biome_atual or "normal"), max(0.0, float(dt)), tamanho_tela, dentro_estadio)

        brilho_azulado = self._clamp(noite * 0.82 + self._rain_power * 0.12, 0.0, 1.0)
        tint_r = self._lerp(1.0, 106.0 / 255.0, brilho_azulado)
        tint_g = self._lerp(1.0, 124.0 / 255.0, brilho_azulado)
        tint_b = self._lerp(1.0, 168.0 / 255.0, brilho_azulado)

        dark = self._clamp((noite * 0.80) + (self._rain_power * 0.08), 0.0, 0.88)
        if dentro_estadio:
            dark *= 0.50
        star_strength = 0.0 if dentro_estadio else self._clamp((noite - 0.36) / 0.64, 0.0, 1.0)
        biome_power = float(self._biome_powers.get(self._biome_type, 0.0) or 0.0) if self._biome_type != "normal" else 0.0

        self._uniformes_atuais = {
            "tipo": "mundo",
            "player_uv": self._player_uv(tamanho_tela, camera, entidade_main),
            "tint": (tint_r, tint_g, tint_b),
            "darkness": dark,
            "rain_power": float(self._rain_power),
            "lightning": float(self._lightning_flash),
            "star_strength": star_strength,
            "inside": bool(dentro_estadio),
            "time": self._tempo,
            "biome_mode": self.biome_mode_value(self._biome_type),
            "biome_power": biome_power,
        }
        return dict(self._uniformes_atuais)

    def uniformes_atuais(self) -> Dict[str, object]:
        return dict(self._uniformes_atuais)

    def desenhar_bioma_base(self, surface: pygame.Surface) -> None:
        if not isinstance(surface, pygame.Surface):
            return
        if self._biome_type == "normal":
            return
        biome_power = float(self._biome_powers.get(self._biome_type, 0.0) or 0.0)
        if biome_power <= 0.0:
            return

        largura, altura = surface.get_size()
        if self._biome_layer_cache is None or self._biome_layer_cache_size != (largura, altura):
            self._biome_layer_cache = pygame.Surface((largura, altura), pygame.SRCALPHA)
            self._biome_layer_cache_size = (largura, altura)

        camada = self._biome_layer_cache
        camada.fill((0, 0, 0, 0))
        if self._biome_type == "neve":
            alpha = int(self._lerp(80, 210, biome_power))
            for part in self._fx_particles:
                raio = max(1, int(part["size"] + biome_power * 1.2))
                pygame.draw.circle(camada, (245, 248, 255, alpha), (int(part["x"]), int(part["y"])), raio)
        elif self._biome_type == "vulcao":
            alpha = int(self._lerp(90, 195, biome_power))
            for part in self._fx_particles:
                raio = max(1, int(part["size"]))
                pygame.draw.circle(camada, (255, 165, 70, alpha), (int(part["x"]), int(part["y"])), raio)
                if raio >= 2:
                    pygame.draw.circle(camada, (255, 232, 150, max(40, alpha - 50)), (int(part["x"]), int(part["y"])), max(1, raio - 1))
        elif self._biome_type == "deserto":
            alpha = int(self._lerp(28, 108, biome_power))
            for part in self._fx_particles:
                pygame.draw.circle(camada, (220, 200, 150, alpha), (int(part["x"]), int(part["y"])), max(1, int(part["size"])))
        elif self._biome_type == "magico":
            alpha = int(self._lerp(55, 165, biome_power))
            for part in self._fx_particles:
                raio = max(1, int(part["size"]))
                pygame.draw.circle(camada, (225, 170, 255, alpha), (int(part["x"]), int(part["y"])), raio)
                pygame.draw.circle(camada, (180, 220, 255, max(30, alpha - 45)), (int(part["x"]), int(part["y"])), max(1, raio - 1))
        elif self._biome_type == "pantano":
            alpha = int(self._lerp(20, 80, biome_power))
            for part in self._fx_particles:
                rect = pygame.Rect(0, 0, int(part["size"] * 2.2), int(part["size"]))
                rect.center = (int(part["x"]), int(part["y"]))
                pygame.draw.ellipse(camada, (160, 170, 156, alpha), rect)
        surface.blit(camada, (0, 0))

    def desenhar_chuva_base(self, surface: pygame.Surface) -> None:
        if not isinstance(surface, pygame.Surface):
            return
        if self._rain_power <= 0.0:
            return

        largura, altura = surface.get_size()
        if self._rain_layer_cache is None or self._rain_layer_cache_size != (largura, altura):
            self._rain_layer_cache = pygame.Surface((largura, altura), pygame.SRCALPHA)
            self._rain_layer_cache_size = (largura, altura)

        profile = self._rain_profile()
        alpha = int(self._lerp(66, 190, self._rain_power))
        camada = self._rain_layer_cache
        camada.fill((0, 0, 0, 0))
        cor = (205, 223, 255, alpha)
        for drop in self._rain_particles:
            x1 = int(drop["x"])
            y1 = int(drop["y"])
            x2 = int(drop["x"] - float(profile["length"]) * 0.40)
            y2 = int(drop["y"] - float(profile["length"]))
            pygame.draw.line(camada, cor, (x1, y1), (x2, y2), int(profile["thickness"]))
        surface.blit(camada, (0, 0))

    def aplicar(self, _tela, _tempo_mundo: Dict[str, object], _dt: float) -> None:
        return None
