from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade


class Bau(Entidade):
    """Baú simples do mundo: estado local e renderização."""

    DURACAO_VISUAL_ABERTO_MS = 1000

    def __init__(
        self,
        id_objeto: int,
        posicao: Tuple[float, float],
        tipo_bau: str,
        itens: List[Dict[str, object]],
        aberto: bool = False,
        raio_colisao: float = 0.42,
    ) -> None:
        super().__init__(
            posicao=(float(posicao[0]), float(posicao[1])),
            raio_colisao=float(raio_colisao),
            raio_interacao=0.85,
            id_objeto=int(id_objeto),
        )
        self.TipoBau = str(tipo_bau)
        self.Itens = [dict(i) for i in itens if isinstance(i, dict)]
        self.Aberto = bool(aberto)
        self.AberturaLocalMs = int(pygame.time.get_ticks()) if self.Aberto else 0
        self._ja_abriu_local = bool(aberto)

    def abrir_localmente(self) -> bool:
        """Abre apenas uma vez no client."""
        if self._ja_abriu_local or self.Aberto:
            return False
        self.Aberto = True
        self._ja_abriu_local = True
        self.AberturaLocalMs = int(pygame.time.get_ticks())
        return True

    def marcar_aberto_por_sync(self) -> None:
        """Aplica abertura vinda do servidor preservando animação local."""
        if self.Aberto:
            return
        self.Aberto = True
        self._ja_abriu_local = True
        self.AberturaLocalMs = int(pygame.time.get_ticks())

    def esta_visivel(self) -> bool:
        if not self.Aberto:
            return True
        if self.AberturaLocalMs <= 0:
            return True
        return (pygame.time.get_ticks() - self.AberturaLocalMs) < self.DURACAO_VISUAL_ABERTO_MS

    def desenhar(self, tela, camera) -> None:
        if not self.esta_visivel():
            return

        px, py = camera.mundo_para_tela_px(self.Posicao)
        base_w = max(12, int(camera.TilePx * 0.65))
        base_h = max(10, int(camera.TilePx * 0.45))

        corpo = pygame.Rect(0, 0, base_w, base_h)
        corpo.center = (int(px), int(py))
        pygame.draw.rect(tela, (210, 160, 70), corpo, border_radius=3)

        if not self.Aberto:
            # frame 0 (fechado)
            tampa = pygame.Rect(corpo.left, corpo.top - int(corpo.height * 0.20), corpo.width, int(corpo.height * 0.25))
            pygame.draw.rect(tela, (180, 130, 45), tampa, border_radius=2)
            return

        # animação simples de abertura em 1s
        decorrido = max(0, pygame.time.get_ticks() - self.AberturaLocalMs)
        t = min(1.0, decorrido / float(self.DURACAO_VISUAL_ABERTO_MS))
        altura_tampa = int(corpo.height * 0.25)
        subida = int((corpo.height * 0.55) * t)
        tampa = pygame.Rect(corpo.left, corpo.top - altura_tampa - subida, corpo.width, altura_tampa)
        pygame.draw.rect(tela, (240, 220, 170), tampa, border_radius=2)
