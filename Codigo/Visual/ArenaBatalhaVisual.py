from __future__ import annotations

import math
import unicodedata

import pygame


class ArenaBatalhaVisual:
    PRIORIDADE = {
        "destruido": 100,
        "congelado": 90,
        "queimado": 80,
        "envenenado": 70,
        "eletrificado": 60,
        "encharcado": 50,
        "amaldicoado": 40,
        "abencoado": 30,
    }
    CODIGOS_SHADER = {
        "destruido": 1,
        "queimado": 2,
        "envenenado": 3,
        "congelado": 4,
        "eletrificado": 5,
        "encharcado": 6,
        "amaldicoado": 7,
        "abencoado": 8,
    }
    ALIASES = {
        "destruida": "destruido",
        "destruicao": "destruido",
        "queimada": "queimado",
        "chamuscado": "queimado",
        "veneno": "envenenado",
        "poison": "envenenado",
        "gelo": "congelado",
        "gelado": "congelado",
        "eletrico": "eletrificado",
        "eletrica": "eletrificado",
        "energizado": "eletrificado",
        "molhado": "encharcado",
        "agua": "encharcado",
        "amaldiacoado": "amaldicoado",
        "amaldicoada": "amaldicoado",
        "maldicao": "amaldicoado",
        "abencoada": "abencoado",
        "bencao": "abencoado",
    }

    @classmethod
    def normalizar_efeito(cls, nome) -> str | None:
        bruto = unicodedata.normalize("NFKD", str(nome or "").strip().casefold())
        sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
        chave = "".join(ch for ch in sem_acento if ch.isalnum())
        chave = cls.ALIASES.get(chave, chave)
        return chave if chave in cls.PRIORIDADE else None

    @classmethod
    def ordenar_efeitos(cls, efeitos) -> list[str]:
        vistos = set()
        saida = []
        for efeito in efeitos or []:
            norm = cls.normalizar_efeito(efeito)
            if norm and norm not in vistos:
                vistos.add(norm)
                saida.append(norm)
        saida.sort(key=lambda e: cls.PRIORIDADE.get(e, 0), reverse=True)
        return saida

    def desenhar_efeitos_area(self, surface, rect_tela, efeitos, tempo_ms=None, area_id=None) -> None:
        if surface is None or rect_tela is None:
            return
        try:
            rect = pygame.Rect(rect_tela)
        except Exception:
            return
        if rect.width <= 2 or rect.height <= 2:
            return

        efeitos_ordenados = self.ordenar_efeitos(efeitos)[:3]
        if not efeitos_ordenados:
            return

        tempo = float(pygame.time.get_ticks() if tempo_ms is None else tempo_ms) / 1000.0
        area_id = str(area_id or "")
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        for idx, efeito in enumerate(efeitos_ordenados):
            self._desenhar_efeito(overlay, efeito, area_id, tempo, idx)
        surface.blit(overlay, rect.topleft)

    def desenhar_efeitos_areas(self, surface, camera, arena) -> None:
        if surface is None or camera is None or arena is None:
            return
        tempo_ms = pygame.time.get_ticks()
        for area_id, efeitos in self._iterar_areas_com_efeitos(arena):
            try:
                rect_tela = arena.rect_area_tela(area_id, camera)
            except Exception:
                rect_tela = None
            self.desenhar_efeitos_area(surface, rect_tela, efeitos, tempo_ms=tempo_ms, area_id=area_id)

    def coletar_efeitos_shader(self, arena, camera, tamanho_tela):
        if arena is None or camera is None:
            return []
        try:
            largura = max(1.0, float(tamanho_tela[0]))
            altura = max(1.0, float(tamanho_tela[1]))
        except Exception:
            largura, altura = 1.0, 1.0

        saida = []
        for area_id, efeitos in self._iterar_areas_com_efeitos(arena):
            if len(saida) >= 18:
                break
            try:
                rect = arena.rect_area_tela(area_id, camera)
            except Exception:
                rect = None
            if rect is None or rect.width <= 0 or rect.height <= 0:
                continue
            cx = float(rect.centerx) / largura
            cy = float(rect.centery) / altura
            if cx < -0.12 or cx > 1.12 or cy < -0.12 or cy > 1.12:
                continue
            raio = max(float(rect.width), float(rect.height)) / altura * 0.58
            raio = max(0.020, min(0.115, raio))
            for efeito in self.ordenar_efeitos(efeitos)[:3]:
                if len(saida) >= 18:
                    break
                codigo = int(self.CODIGOS_SHADER.get(efeito, 0))
                if codigo <= 0:
                    continue
                saida.append({
                    "area_id": str(area_id),
                    "tipo": efeito,
                    "codigo": codigo,
                    "pos_uv": [cx, cy],
                    "raio": raio,
                    "power": 1.0,
                })
        return saida

    @staticmethod
    def _iterar_areas_com_efeitos(arena):
        if not hasattr(arena, "areas_com_efeitos"):
            return []
        try:
            itens = arena.areas_com_efeitos()
        except Exception:
            return []
        if isinstance(itens, dict):
            return list(itens.items())
        return list(itens or [])

    def _desenhar_efeito(self, overlay, efeito: str, area_id: str, tempo: float, camada: int) -> None:
        if efeito == "destruido":
            self._desenhar_destruido(overlay, area_id)
        elif efeito == "queimado":
            self._desenhar_queimado(overlay, area_id, tempo, camada)
        elif efeito == "envenenado":
            self._desenhar_envenenado(overlay, area_id, tempo, camada)
        elif efeito == "congelado":
            self._desenhar_congelado(overlay, area_id, tempo, camada)
        elif efeito == "eletrificado":
            self._desenhar_eletrificado(overlay, area_id, tempo, camada)
        elif efeito == "encharcado":
            self._desenhar_encharcado(overlay, area_id, tempo, camada)
        elif efeito == "amaldicoado":
            self._desenhar_amaldicoado(overlay, area_id, tempo, camada)
        elif efeito == "abencoado":
            self._desenhar_abencoado(overlay, area_id, tempo, camada)

    def _desenhar_destruido(self, surf, area_id: str) -> None:
        w, h = surf.get_size()
        pygame.draw.rect(surf, (8, 7, 6, 78), surf.get_rect(), border_radius=max(3, min(w, h) // 18))
        for i in range(7):
            pts = self._linha_irregular(area_id, "destruido", i, w, h)
            if len(pts) >= 2:
                pygame.draw.lines(surf, (20, 18, 16, 176), False, pts, max(1, min(w, h) // 42))
                pygame.draw.lines(surf, (210, 200, 180, 42), False, [(x + 1, y + 1) for x, y in pts], 1)
        for i in range(15):
            x = int(self._hash(area_id, "detrito-x", i) * w)
            y = int(self._hash(area_id, "detrito-y", i) * h)
            r = max(1, int(1 + self._hash(area_id, "detrito-r", i) * min(w, h) * 0.025))
            cor = int(52 + self._hash(area_id, "detrito-c", i) * 58)
            pygame.draw.circle(surf, (cor, cor - 8, cor - 18, 118), (x, y), r)

    def _desenhar_queimado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        w, h = surf.get_size()
        self._ellipse_central(surf, (16, 10, 6, 82), 0.82, 0.58, camada)
        pulso = 0.5 + 0.5 * math.sin(tempo * 3.4 + self._hash(area_id, "fire", 0) * math.tau)
        self._ellipse_central(surf, (255, 92, 24, int(28 + 25 * pulso)), 0.70, 0.44, camada)
        for i in range(12):
            fase = self._hash(area_id, "brasa", i)
            x = int((0.12 + self._hash(area_id, "brasa-x", i) * 0.76) * w)
            y = int((0.18 + ((fase + tempo * 0.28) % 1.0) * 0.64) * h)
            alpha = int(70 + 95 * (0.5 + 0.5 * math.sin(tempo * 5.0 + fase * math.tau)))
            pygame.draw.circle(surf, (255, 122, 35, alpha), (x, y), max(1, min(w, h) // 36))

    def _desenhar_envenenado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        w, h = surf.get_size()
        self._ellipse_central(surf, (95, 34, 126, 82), 0.76, 0.54, camada)
        self._ellipse_central(surf, (82, 154, 84, 36), 0.58, 0.38, camada)
        for i in range(9):
            fase = self._hash(area_id, "bolha", i)
            x = int((0.16 + self._hash(area_id, "bolha-x", i) * 0.70) * w)
            y = int((0.18 + ((fase - tempo * 0.10) % 1.0) * 0.62) * h)
            r = max(2, int(min(w, h) * (0.025 + 0.018 * fase)))
            alpha = int(45 + 55 * (1.0 - abs(((tempo * 0.8 + fase) % 1.0) - 0.5) * 2.0))
            pygame.draw.circle(surf, (185, 98, 214, alpha), (x, y), r, 1)
        self._fumaca(surf, area_id, tempo, (74, 38, 92, 34), "veneno")

    def _desenhar_congelado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        w, h = surf.get_size()
        self._ellipse_central(surf, (124, 214, 255, 78), 0.90, 0.68, camada)
        brilho = int(26 + 20 * (0.5 + 0.5 * math.sin(tempo * 2.1)))
        pygame.draw.rect(surf, (202, 244, 255, brilho), surf.get_rect().inflate(-w // 12, -h // 12), 1, border_radius=max(3, min(w, h) // 14))
        for i in range(8):
            pts = self._linha_irregular(area_id, "gelo", i, w, h, passos=3)
            if len(pts) >= 2:
                pygame.draw.lines(surf, (218, 248, 255, 116), False, pts, 1)
        for i in range(6):
            cx = int((0.18 + self._hash(area_id, "cristal-x", i) * 0.64) * w)
            cy = int((0.18 + self._hash(area_id, "cristal-y", i) * 0.64) * h)
            r = max(3, int(min(w, h) * (0.030 + self._hash(area_id, "cristal-r", i) * 0.026)))
            pygame.draw.polygon(surf, (190, 236, 255, 72), [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])

    def _desenhar_eletrificado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        w, h = surf.get_size()
        pulso = 0.5 + 0.5 * math.sin(tempo * 8.0 + camada)
        self._ellipse_central(surf, (70, 140, 255, int(22 + 26 * pulso)), 0.72, 0.46, camada)
        for i in range(9):
            fase = self._hash(area_id, "raio", i)
            if math.sin(tempo * (5.5 + fase * 3.0) + fase * 20.0) < -0.22:
                continue
            x = int((0.10 + self._hash(area_id, "raio-x", i) * 0.80) * w)
            y = int((0.12 + self._hash(area_id, "raio-y", i) * 0.76) * h)
            tam = max(5, int(min(w, h) * (0.10 + fase * 0.07)))
            pts = [(x, y), (x + tam // 3, y + tam // 5), (x - tam // 8, y + tam // 2), (x + tam // 2, y + tam)]
            pygame.draw.lines(surf, (255, 232, 70, 168), False, pts, max(1, min(w, h) // 50))
            pygame.draw.lines(surf, (96, 202, 255, 126), False, [(px + 1, py) for px, py in pts], 1)

    def _desenhar_encharcado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        w, h = surf.get_size()
        self._ellipse_central(surf, (42, 122, 224, 74), 0.82, 0.52, camada)
        for i in range(4):
            fase = (tempo * 0.45 + i * 0.25 + self._hash(area_id, "onda", i)) % 1.0
            rx = int(w * (0.18 + fase * 0.28))
            ry = int(h * (0.10 + fase * 0.16))
            alpha = int(68 * (1.0 - fase))
            rect = pygame.Rect(0, 0, max(3, rx), max(3, ry))
            rect.center = (w // 2, h // 2)
            pygame.draw.ellipse(surf, (170, 224, 255, alpha), rect, 1)
        for i in range(8):
            fase = self._hash(area_id, "gota", i)
            x = int((0.12 + self._hash(area_id, "gota-x", i) * 0.76) * w)
            y = int((0.10 + ((fase + tempo * 0.22) % 1.0) * 0.72) * h)
            pygame.draw.circle(surf, (172, 222, 255, 72), (x, y), max(1, min(w, h) // 44))

    def _desenhar_amaldicoado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        self._ellipse_central(surf, (26, 12, 42, 90), 0.84, 0.62, camada)
        self._ellipse_central(surf, (96, 42, 150, 34), 0.68, 0.44, camada)
        self._fumaca(surf, area_id, tempo, (20, 10, 32, 48), "sombra")

    def _desenhar_abencoado(self, surf, area_id: str, tempo: float, camada: int) -> None:
        w, h = surf.get_size()
        pulso = 0.5 + 0.5 * math.sin(tempo * 2.6 + self._hash(area_id, "luz", 0) * math.tau)
        self._ellipse_central(surf, (255, 236, 132, int(42 + 30 * pulso)), 0.78, 0.54, camada)
        self._ellipse_central(surf, (255, 255, 240, 24), 0.50, 0.32, camada)
        for i in range(12):
            fase = self._hash(area_id, "part-luz", i)
            x = int((0.10 + self._hash(area_id, "part-luz-x", i) * 0.80) * w)
            y = int((0.10 + ((fase - tempo * 0.10) % 1.0) * 0.76) * h)
            alpha = int(56 + 80 * (0.5 + 0.5 * math.sin(tempo * 3.4 + fase * math.tau)))
            pygame.draw.circle(surf, (255, 252, 214, alpha), (x, y), max(1, min(w, h) // 46))

    def _ellipse_central(self, surf, cor, escala_x: float, escala_y: float, camada: int) -> None:
        w, h = surf.get_size()
        rect = pygame.Rect(0, 0, max(2, int(w * escala_x)), max(2, int(h * escala_y)))
        rect.center = (w // 2, h // 2 + int((camada - 1) * h * 0.025))
        pygame.draw.ellipse(surf, cor, rect)

    def _fumaca(self, surf, area_id: str, tempo: float, cor, chave: str) -> None:
        w, h = surf.get_size()
        for i in range(7):
            fase = self._hash(area_id, chave, i)
            x = int((0.14 + self._hash(area_id, chave + "-x", i) * 0.72 + math.sin(tempo * 0.9 + i) * 0.025) * w)
            y = int((0.15 + ((fase - tempo * 0.065) % 1.0) * 0.68) * h)
            r = max(4, int(min(w, h) * (0.05 + fase * 0.045)))
            alpha = int(cor[3] * (0.45 + 0.55 * (1.0 - abs(((tempo * 0.25 + fase) % 1.0) - 0.5) * 2.0)))
            pygame.draw.circle(surf, (cor[0], cor[1], cor[2], alpha), (x, y), r)

    def _linha_irregular(self, area_id: str, chave: str, idx: int, w: int, h: int, passos: int = 4):
        x0 = self._hash(area_id, chave, idx, "x0") * w
        y0 = self._hash(area_id, chave, idx, "y0") * h
        ang = self._hash(area_id, chave, idx, "ang") * math.tau
        comp = min(w, h) * (0.18 + self._hash(area_id, chave, idx, "len") * 0.28)
        pts = []
        for p in range(passos):
            t = p / max(1, passos - 1)
            jitter = (self._hash(area_id, chave, idx, p, "jit") - 0.5) * min(w, h) * 0.13
            x = x0 + math.cos(ang) * comp * (t - 0.5) + math.cos(ang + math.pi * 0.5) * jitter
            y = y0 + math.sin(ang) * comp * (t - 0.5) + math.sin(ang + math.pi * 0.5) * jitter
            pts.append((int(max(1, min(w - 2, x))), int(max(1, min(h - 2, y)))))
        return pts

    @staticmethod
    def _hash(*partes) -> float:
        texto = "|".join(str(p) for p in partes)
        acc = 2166136261
        for ch in texto:
            acc ^= ord(ch)
            acc = (acc * 16777619) & 0xFFFFFFFF
        return (acc % 10000) / 10000.0
