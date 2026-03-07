"""Representação simples de Pokémon no mundo do cliente."""

from __future__ import annotations

import math
from typing import Dict, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade

Vector2 = Tuple[float, float]


class PokemonMundo(Entidade):
    """Entidade de pokemon controlada por diffs do servidor."""

    def __init__(self, snapshot: Dict[str, object]) -> None:
        pos = self._pos(snapshot.get("posicao"))
        raio = max(0.2, self._f(snapshot.get("raio_colisao"), 0.45))
        try:
            oid = int(snapshot.get("id", 0))
        except (TypeError, ValueError):
            oid = 0
        super().__init__(posicao=pos, raio_colisao=raio, raio_interacao=max(1.1, raio), id_objeto=oid)
        self.Destino: Vector2 = pos
        self.Especie = str((snapshot.get("estado") or {}).get("especie") if isinstance(snapshot.get("estado"), dict) else "Pokemon")

    @staticmethod
    def _f(v, d=0.0) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(d)

    @staticmethod
    def _pos(v) -> Vector2:
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (float(v[0]), float(v[1]))
        return (0.0, 0.0)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        if estado.get("especie"):
            self.Especie = str(estado.get("especie"))

        self.Colisor.raio_colisao = max(0.2, self._f(snapshot.get("raio_colisao"), self.Colisor.raio_colisao))
        destino = self._pos(snapshot.get("posicao"))
        movimento = str(snapshot.get("movimento") or estado.get("movimento") or "mover").strip().lower()
        if movimento == "teleportar":
            self.Destino = destino
            self.definir_posicao(destino[0], destino[1])
        else:
            self.Destino = destino

    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        k = min(1.0, 8.0 * dt)
        px, py = self.Posicao
        dx, dy = self.Destino
        self.definir_posicao(px + (dx - px) * k, py + (dy - py) * k)

    def desenhar(self, tela, camera, dt: float) -> None:
        self.atualizar(dt)
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        centro = (int(cx), int(cy))
        base = max(6, int(getattr(camera, "TilePx", 50) * 0.40))
        t = pygame.time.get_ticks() * 0.008
        pulsar = 1.0 + math.sin(t + (abs(hash(self.Especie)) % 360) * 0.017) * 0.06
        r1 = max(5, int(base * pulsar))
        r2 = max(3, int(r1 * 0.62))

        pygame.draw.circle(tela, (70, 155, 245), centro, r1)
        pygame.draw.circle(tela, (24, 84, 190), centro, r1, 2)
        pygame.draw.circle(tela, (120, 210, 255), centro, r2)
