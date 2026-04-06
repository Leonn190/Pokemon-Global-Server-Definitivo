from __future__ import annotations

from typing import Dict, List, Tuple

import pygame


class FiltroCamera:
    def __init__(self) -> None:
        self._tempo = 0.0
        self._overlay = None
        self._camada_cor = None
        self._camada_noite = None
        self._camada_nevoa = None
        self._camada_chuva = None
        self._vinheta = None
        self._tamanho = (0, 0)
        self._gotas: List[Tuple[float, float, float, float, float, float]] = []
        self._chave_noite_cache = None
        self._alpha_nevoa_cache = -1
        self._ultimo_redesenho_chuva = -1.0
        self._chuva_n_cache = -1.0

    @staticmethod
    def _fator_noite(hora: int, minuto: int) -> float:
        m = int(hora) * 60 + int(minuto)
        if 8 * 60 <= m < 17 * 60:
            return 0.0
        if m >= 17 * 60 or m < 60:
            m_ext = m if m >= 17 * 60 else m + 1440
            return max(0.0, min(1.0, (m_ext - (17 * 60)) / float(8 * 60)))
        if 60 <= m < 8 * 60:
            return max(0.0, min(1.0, 1.0 - ((m - 60) / float(7 * 60))))
        return 0.0

    def _garantir_cache(self, largura: int, altura: int) -> None:
        if self._tamanho == (largura, altura) and self._overlay is not None:
            return
        self._tamanho = (largura, altura)
        self._overlay = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._camada_cor = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._camada_noite = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._camada_nevoa = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._camada_chuva = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._vinheta = pygame.Surface((largura, altura), pygame.SRCALPHA)
        self._chave_noite_cache = None
        self._alpha_nevoa_cache = -1
        self._ultimo_redesenho_chuva = -1.0
        self._chuva_n_cache = -1.0
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
        alpha_tonalidade = int(90 * min(1.0, noite + chuva_n * 0.45))
        chave_noite = (alpha_noite, alpha_tonalidade)
        if self._camada_noite is not None and self._chave_noite_cache != chave_noite:
            self._camada_noite.fill((0, 0, 0, 0))
            if alpha_noite > 0:
                self._camada_cor.fill((5, 10, 24, alpha_noite))
                self._camada_noite.blit(self._camada_cor, (0, 0))
            if alpha_tonalidade > 0:
                self._camada_cor.fill((18, 34, 56, alpha_tonalidade))
                self._camada_noite.blit(self._camada_cor, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                if self._vinheta is not None:
                    self._camada_noite.blit(self._vinheta, (0, 0))
            self._chave_noite_cache = chave_noite
        if self._camada_noite is not None and (alpha_noite > 0 or alpha_tonalidade > 0):
            self._overlay.blit(self._camada_noite, (0, 0))

        if chuva > 0:
            alpha_nevoa = int(60 * chuva_n)
            if self._camada_nevoa is not None and self._alpha_nevoa_cache != alpha_nevoa:
                self._camada_nevoa.fill((90, 98, 118, alpha_nevoa))
                self._alpha_nevoa_cache = alpha_nevoa
            self._overlay.blit(self._camada_nevoa, (0, 0))
            # Limita a taxa de atualização da chuva para evitar custo alto em FPS muito altos.
            precisa_redesenhar = (
                self._ultimo_redesenho_chuva < 0.0
                or (self._tempo - self._ultimo_redesenho_chuva) >= (1.0 / 45.0)
                or abs(self._chuva_n_cache - chuva_n) >= 0.05
            )
            if precisa_redesenhar and self._camada_chuva is not None:
                self._camada_chuva.fill((0, 0, 0, 0))
                self._desenhar_chuva(self._camada_chuva, chuva_n)
                self._ultimo_redesenho_chuva = self._tempo
                self._chuva_n_cache = chuva_n
            if self._camada_chuva is not None:
                self._overlay.blit(self._camada_chuva, (0, 0))
        else:
            self._alpha_nevoa_cache = -1
            self._chuva_n_cache = -1.0

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
