from __future__ import annotations

import math

import pygame


class AtorEstado:
    def __init__(self, ator) -> None:
        self.ator = ator
        self._tempo_agua = 0.0
        self._queda_inicio_ms = 0
        self._queda_forcada_ate_ms = 0
        self._queda_duracao_ms = 620

    def atualizar(self, dt: float) -> None:
        self._tempo_agua += max(0.0, float(dt))
        queda_ativa = bool(getattr(self.ator, "SobreBuraco", False)) or int(pygame.time.get_ticks()) < int(self._queda_forcada_ate_ms)
        if queda_ativa and self._queda_inicio_ms <= 0:
            self._queda_inicio_ms = int(pygame.time.get_ticks())
        if not queda_ativa:
            self._queda_inicio_ms = 0

    def iniciar_queda(self, duracao_ms: int = 620) -> None:
        agora = int(pygame.time.get_ticks())
        self._queda_duracao_ms = max(120, int(duracao_ms or 620))
        self._queda_inicio_ms = agora
        self._queda_forcada_ate_ms = max(self._queda_forcada_ate_ms, agora + self._queda_duracao_ms)

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
        dur = max(120.0, float(self._queda_duracao_ms or 620))
        t = max(0.0, min(1.0, (pygame.time.get_ticks() - self._queda_inicio_ms) / dur))
        return max(0.05, 1.0 - (t * t))

    def _progresso_queda(self) -> float:
        if self._queda_inicio_ms <= 0:
            return 0.0
        dur = max(120.0, float(self._queda_duracao_ms or 620))
        return max(0.0, min(1.0, (pygame.time.get_ticks() - self._queda_inicio_ms) / dur))

    def desenhar(self, tela, posicao_tela, respiracao_tempo: float = 0.0) -> None:
        ator = self.ator
        estado_agua = str(getattr(ator, "EstadoAgua", "") or "")
        if estado_agua:
            self._desenhar_ondinhas(tela, posicao_tela, estado_agua, camada="baixo")

        alpha = self._alpha_invulneravel()
        escala = self._escala_queda()
        if escala <= 0.02:
            return
        if alpha >= 255 and escala >= 0.999:
            ator.desenhar(tela, posicao_tela=posicao_tela, respiracao_tempo=respiracao_tempo)
            if estado_agua:
                self._desenhar_ondinhas(tela, posicao_tela, estado_agua, camada="cima")
            return

        if escala < 0.999:
            tile_px = max(1, int(getattr(getattr(ator, "Desenhador", None), "_tile_px", 50) or 50))
            t = self._progresso_queda()
            buraco_rect = pygame.Rect(0, 0, int(tile_px * 0.92), int(tile_px * 0.42))
            buraco_rect.center = (int(posicao_tela[0]), int(posicao_tela[1] + tile_px * 0.28))
            chao = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            pygame.draw.ellipse(chao, (4, 4, 6, 210), buraco_rect)
            pygame.draw.ellipse(chao, (24, 21, 28, 170), buraco_rect.inflate(int(tile_px * 0.16), int(tile_px * 0.10)), 2)
            tela.blit(chao, (0, 0))
            camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            ator.desenhar(camada, posicao_tela=posicao_tela, respiracao_tempo=respiracao_tempo)
            rect = camada.get_bounding_rect()
            if rect.width > 0 and rect.height > 0:
                sprite = camada.subsurface(rect).copy()
                w = max(1, int(rect.width * escala))
                h = max(1, int(rect.height * escala))
                sprite = pygame.transform.smoothscale(sprite, (w, h))
                alpha_queda = int(alpha * max(0.0, 1.0 - max(0.0, t - 0.72) / 0.28))
                sprite.set_alpha(alpha_queda)
                destino = sprite.get_rect()
                destino.center = (int(posicao_tela[0]), int(posicao_tela[1] + tile_px * 0.22 * t))
                tela.blit(sprite, destino)
        else:
            camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            ator.desenhar(camada, posicao_tela=posicao_tela, respiracao_tempo=respiracao_tempo)
            camada.set_alpha(alpha)
            tela.blit(camada, (0, 0))
        if estado_agua:
            self._desenhar_ondinhas(tela, posicao_tela, estado_agua, camada="cima")

    def _desenhar_ondinhas(self, tela, posicao_tela, estado_agua: str, camada: str = "baixo") -> None:
        cx, cy = int(posicao_tela[0]), int(posicao_tela[1] + 18)
        alpha = 125 if camada == "baixo" else 190
        cor = (150, 220, 255, alpha) if estado_agua == "rasa" else (82, 178, 255, alpha)
        largura = 24 if estado_agua == "rasa" else 31
        fase = self._tempo_agua * 6.0
        for i in range(3 if camada == "cima" else 2):
            off = int(math.sin(fase + i * 1.7) * 4)
            rect = pygame.Rect(0, 0, largura + i * 9, 8 + i * 3)
            rect.center = (cx + off, cy + i * 4)
            ini = math.radians(16 if camada == "baixo" else 196)
            fim = math.radians(164 if camada == "baixo" else 344)
            pygame.draw.arc(tela, cor, rect, ini, fim, 2)
