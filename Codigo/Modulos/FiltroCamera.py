from __future__ import annotations

from typing import Dict, List, Tuple

import pygame


class FiltroCamera:
    INICIO_ESCURECER_MIN = 17 * 60
    ESCURO_MAXIMO_MIN = 25 * 60
    INICIO_CLAREAR_MIN = 25 * 60
    FIM_CLAREAR_MIN = 32 * 60

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

    def __init__(self) -> None:
        self._tempo = 0.0
        self._overlay = None
        self._camada_cor = None
        self._camada_nevoa = None
        self._vinheta = None
        self._tamanho = (0, 0)
        self._gotas: List[Tuple[float, float, float, float, float, float]] = []

    @staticmethod
    def _fator_noite(hora: int, minuto: int) -> float:
        m = int(hora) * 60 + int(minuto)
        if m < FiltroCamera.INICIO_ESCURECER_MIN:
            m += 1440
        if FiltroCamera.FIM_CLAREAR_MIN <= m < (FiltroCamera.INICIO_ESCURECER_MIN + 1440):
            return 0.0
        if FiltroCamera.INICIO_ESCURECER_MIN <= m < FiltroCamera.ESCURO_MAXIMO_MIN:
            dur = max(1, FiltroCamera.ESCURO_MAXIMO_MIN - FiltroCamera.INICIO_ESCURECER_MIN)
            return max(0.0, min(1.0, (m - FiltroCamera.INICIO_ESCURECER_MIN) / float(dur)))
        if FiltroCamera.ESCURO_MAXIMO_MIN <= m < FiltroCamera.INICIO_CLAREAR_MIN:
            return 1.0
        if FiltroCamera.INICIO_CLAREAR_MIN <= m < FiltroCamera.FIM_CLAREAR_MIN:
            dur = max(1, FiltroCamera.FIM_CLAREAR_MIN - FiltroCamera.INICIO_CLAREAR_MIN)
            return max(0.0, min(1.0, 1.0 - ((m - FiltroCamera.INICIO_CLAREAR_MIN) / float(dur))))
        return 0.0

    def _garantir_cache(self, largura: int, altura: int) -> None:
        if self._tamanho == (largura, altura) and self._overlay is not None:
            return
        self._tamanho = (largura, altura)
        self._overlay = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._camada_cor = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._camada_nevoa = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._vinheta = pygame.Surface((largura, altura), pygame.SRCALPHA)
        cx, cy = largura * 0.5, altura * 0.5
        raio_max = max(1.0, ((cx * cx) + (cy * cy)) ** 0.5)
        for y in range(altura):
            for x in range(largura):
                dx = x - cx
                dy = y - cy
                t = min(1.0, (((dx * dx) + (dy * dy)) ** 0.5) / raio_max)
                alpha = int(max(0.0, (t - 0.58) / 0.42) * 130)
                if alpha > 0:
                    self._vinheta.set_at((x, y), (0, 0, 0, min(180, alpha)))
        self._gotas = []
        quantidade = max(24, int(largura / 18))
        for i in range(quantidade):
            seed = (i * 1103515245 + 12345) & 0xFFFFFFFF
            xf = float((seed % max(1, largura + 40)) - 20)
            yf = float(((seed >> 7) % max(1, altura + 240)) - 120)
            sf = 0.70 + (((seed >> 13) % 100) / 200.0)
            lf = 0.65 + (((seed >> 19) % 100) / 240.0)
            df = 0.75 + (((seed >> 23) % 100) / 260.0)
            af = 0.65 + (((seed >> 29) % 100) / 220.0)
            self._gotas.append((xf, yf, sf, lf, df, af))

    def aplicar(self, tela, tempo_mundo: Dict[str, object], dt: float) -> None:
        self._tempo += max(0.0, float(dt))
        largura, altura = tela.get_size()
        self._garantir_cache(largura, altura)

        hora = int(tempo_mundo.get("hora", 8) or 8)
        minuto = int(tempo_mundo.get("minuto", 0) or 0)
        chuva = int(max(0, min(100, int(tempo_mundo.get("chuva_intensidade", 0) or 0))))
        noite = self._fator_noite(hora, minuto)
        chuva_n = chuva / 100.0

        self._overlay.fill((0, 0, 0, 0))

        alpha_noite = int(170 * noite)
        if alpha_noite > 0:
            self._camada_cor.fill((5, 10, 24, alpha_noite))
            self._overlay.blit(self._camada_cor, (0, 0))

        alpha_tonalidade = int(90 * min(1.0, noite + chuva_n * 0.45))
        if alpha_tonalidade > 0:
            self._camada_cor.fill((18, 34, 56, alpha_tonalidade))
            self._overlay.blit(self._camada_cor, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            if self._vinheta is not None:
                self._overlay.blit(self._vinheta, (0, 0))

        if chuva > 0:
            self._camada_nevoa.fill((90, 98, 118, int(60 * chuva_n)))
            self._overlay.blit(self._camada_nevoa, (0, 0))
            self._desenhar_chuva(self._overlay, chuva_n)

        tela.blit(self._overlay, (0, 0))

    def _desenhar_chuva(self, overlay, chuva_n: float) -> None:
        largura, altura = self._tamanho
        if largura <= 0 or altura <= 0:
            return
        quantidade = max(10, int(len(self._gotas) * chuva_n))
        if quantidade <= 0:
            return
        comprimento_base = 8 + 16 * chuva_n
        velocidade = 220.0 + 320.0 * chuva_n

        for i in range(quantidade):
            x0, y0, sf, lf, df, af = self._gotas[i]
            comp = int(comprimento_base * lf)
            desloc = (self._tempo * velocidade * sf) % (altura + comp + 140)
            y = int((y0 + desloc) - 120)
            x = int(x0)
            x2 = int(x - (2.5 + 5.0 * chuva_n) * df)
            y2 = int(y + comp)
            alpha = int((88 + 110 * chuva_n) * af)
            pygame.draw.line(overlay, (180, 198, 220, max(40, min(255, alpha))), (x, y), (x2, y2), 1)
