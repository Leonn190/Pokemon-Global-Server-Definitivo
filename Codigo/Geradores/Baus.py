from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade
from Codigo.Geradores.GameObjeto import GameObjeto
from Codigo.Modulos.Auxiliares import carregar_frames


class Bau(Entidade):
    """Baú do mundo com animação por frames de sprites."""

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
        frames = carregar_frames(base, loader=GameObjeto._obter_sprite)
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
        return True

    def _frame_atual(self, frames: List[pygame.Surface]) -> pygame.Surface | None:
        if not frames:
            return None
        if not self.Aberto or len(frames) == 1:
            return frames[0]
        if self.AberturaLocalMs <= 0:
            return frames[-1]

        duracao_ms = 1000.0
        decorrido = max(0, pygame.time.get_ticks() - self.AberturaLocalMs)
        progresso = min(1.0, decorrido / duracao_ms)
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

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, object]) -> "Bau":
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        posicao = snapshot.get("posicao", [0.0, 0.0])
        if not isinstance(posicao, (list, tuple)) or len(posicao) != 2:
            posicao = [0.0, 0.0]
        return cls(
            id_objeto=int(snapshot.get("id", 0)),
            posicao=(float(posicao[0]), float(posicao[1])),
            tipo_bau=str(estado.get("tipo_bau", "Comum")),
            itens=list(estado.get("itens", [])),
            aberto=bool(estado.get("aberto", False)),
            raio_colisao=float(snapshot.get("raio_colisao", 0.42)),
        )

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        posicao = snapshot.get("posicao", [self.Posicao[0], self.Posicao[1]])
        if isinstance(posicao, (list, tuple)) and len(posicao) == 2:
            self.definir_posicao(float(posicao[0]), float(posicao[1]))
        self.TipoBau = str(estado.get("tipo_bau", self.TipoBau)).strip() or "Comum"
        self.Itens = [dict(i) for i in list(estado.get("itens", self.Itens)) if isinstance(i, dict)]
        self.Colisor.raio_colisao = max(0.1, float(snapshot.get("raio_colisao", self.Colisor.raio_colisao)))
        if bool(estado.get("aberto", False)):
            self.marcar_aberto_por_sync()

    def processar_interacao_player(self, player) -> Dict[str, object] | None:
        ator = getattr(player, "Ator", player)
        inventario = getattr(player, "Inventario", None)
        if ator is None or inventario is None or self.Aberto:
            return None

        dx = float(self.Posicao[0]) - float(ator.Posicao[0])
        dy = float(self.Posicao[1]) - float(ator.Posicao[1])
        raio_player = max(0.1, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))
        limite = raio_player + float(getattr(self.Colisor, "raio_interacao", self.Colisor.raio_colisao)) + 0.02
        if (dx * dx + dy * dy) > (limite * limite):
            return None

        for item in self.Itens:
            inventario.adicionar_item(dict(item))
        if not self.abrir_localmente():
            return None
        return {"tipo": "abrir_bau", "objeto_id": int(self.Id), "payload": {}}
