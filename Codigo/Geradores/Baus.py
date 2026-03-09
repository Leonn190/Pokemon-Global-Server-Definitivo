from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade
from Codigo.Geradores.GameObjeto import GameObjeto


class Bau(Entidade):
    """Baú do mundo com animação por frames de sprites."""

    DURACAO_VISUAL_ABERTO_MS = 1000
    _frames_por_tipo: Dict[str, List[pygame.Surface]] = {}

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
        self.TipoBau = str(tipo_bau or "Comum").strip() or "Comum"
        self.Itens = [dict(i) for i in itens if isinstance(i, dict)]
        self.Aberto = bool(aberto)
        self.AberturaLocalMs = int(pygame.time.get_ticks()) if self.Aberto else 0
        self._ja_abriu_local = bool(aberto)

    @classmethod
    def _carregar_frames(cls, tipo_bau: str) -> List[pygame.Surface]:
        tipo = str(tipo_bau or "Comum").strip() or "Comum"
        if tipo in cls._frames_por_tipo:
            return cls._frames_por_tipo[tipo]

        base = Path("Recursos") / "Visual" / "Mundo" / "Baus" / f"Bau {tipo}"
        frames: List[pygame.Surface] = []
        for idx in range(4):
            sprite = GameObjeto._obter_sprite(str(base / f"{idx}.png"))
            if sprite is not None:
                frames.append(sprite)
        cls._frames_por_tipo[tipo] = frames
        return frames

    def abrir_localmente(self) -> bool:
        if self._ja_abriu_local or self.Aberto:
            return False
        self.Aberto = True
        self._ja_abriu_local = True
        self.AberturaLocalMs = int(pygame.time.get_ticks())
        return True

    def marcar_aberto_por_sync(self) -> None:
        if self.Aberto:
            return
        self.Aberto = True
        self._ja_abriu_local = True
        self.AberturaLocalMs = int(pygame.time.get_ticks())

    def esta_visivel(self) -> bool:
        return (not self.Aberto) or self.AberturaLocalMs <= 0 or (pygame.time.get_ticks() - self.AberturaLocalMs) < self.DURACAO_VISUAL_ABERTO_MS

    def _frame_atual(self, frames: List[pygame.Surface]) -> pygame.Surface | None:
        if not frames:
            return None
        if not self.Aberto or len(frames) == 1:
            return frames[0]
        if self.AberturaLocalMs <= 0:
            return frames[-1]

        decorrido = max(0, pygame.time.get_ticks() - self.AberturaLocalMs)
        progresso = min(1.0, decorrido / float(self.DURACAO_VISUAL_ABERTO_MS))
        idx = min(len(frames) - 1, int(progresso * (len(frames) - 1)))
        return frames[idx]

    def desenhar(self, tela, camera) -> None:
        if not self.esta_visivel():
            return

        frame = self._frame_atual(self._carregar_frames(self.TipoBau))
        if frame is None:
            return

        px, py = camera.mundo_para_tela_px(self.Posicao)
        escala = max(1, int(camera.TilePx * 0.95))
        sprite = pygame.transform.smoothscale(frame, (escala, escala))
        tela.blit(sprite, sprite.get_rect(center=(int(px), int(py))))
