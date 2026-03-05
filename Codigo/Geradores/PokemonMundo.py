"""Pokemon no mundo aberto com animação circular."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade

Vector2 = Tuple[float, float]


class PokemonMundo(Entidade):
    """Pokémon exibido como círculo animado no mapa."""

    def __init__(
        self,
        frames_animacao: Iterable[pygame.Surface],
        posicao: Vector2 = (0.0, 0.0),
        dados: Optional[Dict] = None,
        velocidade: Vector2 = (0.0, 0.0),
        raio_colisao: float = 14.0,
        raio_visual: int = 18,
        duracao_frame: float = 0.10,
    ) -> None:
        super().__init__(
            posicao=posicao,
            velocidade=velocidade,
            raio_colisao=raio_colisao,
        )
        self.Frames = [frame.convert_alpha() for frame in frames_animacao]
        if not self.Frames:
            raise ValueError("PokemonMundo precisa de ao menos 1 frame de animação.")

        self.DuracaoFrame = max(0.01, float(duracao_frame))
        self._tempo_frame = 0.0
        self._frame_index = 0

        self.RaioVisual = max(6, int(raio_visual))
        self.Dados = dict(dados or {})
        self.Capturado = bool(self.Dados.get("capturado", False))
        self.Frutificado = bool(self.Dados.get("frutificado", False))

    @property
    def frame_atual(self) -> pygame.Surface:
        return self.Frames[self._frame_index]

    def atualizar_animacao(self, delta_time: float) -> None:
        self._tempo_frame += max(0.0, float(delta_time))
        while self._tempo_frame >= self.DuracaoFrame:
            self._tempo_frame -= self.DuracaoFrame
            self._frame_index = (self._frame_index + 1) % len(self.Frames)

    def desenhar(self, tela: pygame.Surface) -> None:
        diametro = self.RaioVisual * 2
        area = pygame.Surface((diametro, diametro), pygame.SRCALPHA)

        frame = pygame.transform.smoothscale(self.frame_atual, (diametro, diametro))
        area.blit(frame, (0, 0))

        mascara = pygame.Surface((diametro, diametro), pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), (self.RaioVisual, self.RaioVisual), self.RaioVisual)
        area.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        borda_cor = (230, 230, 230)
        pygame.draw.circle(area, borda_cor, (self.RaioVisual, self.RaioVisual), self.RaioVisual, 2)

        pos = (int(self.Posicao[0] - self.RaioVisual), int(self.Posicao[1] - self.RaioVisual))
        tela.blit(area, pos)

    def atualizar(self, delta_time: float) -> None:
        self.mover(self.Velocidade[0] * delta_time, self.Velocidade[1] * delta_time)
        self.atualizar_animacao(delta_time)

    def capturar(self, capturador_id=None) -> bool:
        if self.Capturado:
            return False

        self.Capturado = True
        self.Dados["capturado"] = True
        if capturador_id is not None:
            self.Dados["capturado_por"] = capturador_id
        return True

    def frutificar(self, frutificador_id=None) -> bool:
        if self.Frutificado:
            return False

        self.Frutificado = True
        self.Dados["frutificado"] = True
        if frutificador_id is not None:
            self.Dados["frutificado_por"] = frutificador_id
        return True
