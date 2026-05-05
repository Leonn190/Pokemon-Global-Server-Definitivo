from __future__ import annotations

import math

import pygame


class AtorEstado:
    def __init__(self, ator) -> None:
        self.ator = ator
        self._tempo_agua = 0.0
        self._queda_inicio_ms = 0

    def atualizar(self, dt: float) -> None:
        self._tempo_agua += max(0.0, float(dt))
        if bool(getattr(self.ator, "SobreBuraco", False)) and self._queda_inicio_ms <= 0:
            self._queda_inicio_ms = int(pygame.time.get_ticks())
        if not bool(getattr(self.ator, "SobreBuraco", False)):
            self._queda_inicio_ms = 0

    def _alpha_invulneravel(self) -> int:
        agora_ms = int(pygame.time.get_ticks())
        imune_ate = int(getattr(self.ator, "ImuneCombateAteMs", 0) or 0)
        if agora_ms >= imune_ate:
            return 255
        pulso = (math.sin(agora_ms * 0.018) + 1.0) * 0.5
        return int(95 + (130 * pulso))

    def _escala_queda(self) -> float:
        if self._queda_inicio_ms <= 0:
            return 1.0
        t = max(0.0, min(1.0, (pygame.time.get_ticks() - self._queda_inicio_ms) / 420.0))
        return 1.0 - 0.38 * t

    def desenhar(self, tela, posicao_tela, respiracao_tempo: float = 0.0) -> None:
        ator = self.ator
        estado_agua = str(getattr(ator, "EstadoAgua", "") or "")
        if estado_agua:
            self._desenhar_ondinhas(tela, posicao_tela, estado_agua)

        alpha = self._alpha_invulneravel()
        escala = self._escala_queda()
        if alpha >= 255 and escala >= 0.999:
            ator.desenhar(tela, posicao_tela=posicao_tela, respiracao_tempo=respiracao_tempo)
            return

        camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        if escala < 0.999:
            original = getattr(ator.Desenhador, "_escala_tiles", 1.0)
            ator.Desenhador._escala_tiles = float(original) * escala
            try:
                ator.desenhar(camada, posicao_tela=posicao_tela, respiracao_tempo=respiracao_tempo)
            finally:
                ator.Desenhador._escala_tiles = original
        else:
            ator.desenhar(camada, posicao_tela=posicao_tela, respiracao_tempo=respiracao_tempo)
        camada.set_alpha(alpha)
        tela.blit(camada, (0, 0))

    def _desenhar_ondinhas(self, tela, posicao_tela, estado_agua: str) -> None:
        cx, cy = int(posicao_tela[0]), int(posicao_tela[1] + 16)
        cor = (125, 205, 255, 135) if estado_agua == "rasa" else (80, 160, 235, 165)
        largura = 18 if estado_agua == "rasa" else 24
        fase = self._tempo_agua * 6.0
        for i in range(2):
            off = int(math.sin(fase + i * 1.7) * 3)
            rect = pygame.Rect(0, 0, largura + i * 8, 7 + i * 3)
            rect.center = (cx + off, cy + i * 4)
            pygame.draw.arc(tela, cor, rect, math.radians(12), math.radians(168), 2)
