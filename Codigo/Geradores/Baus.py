from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.Modulos.Auxiliares import carregar_frames
from Codigo.Modulos.Colisor import Colisor


class Bau:
    _frames_por_tipo: Dict[str, List[pygame.Surface]] = {}
    _cache_sprites: Dict[str, pygame.Surface | None] = {}

    def __init__(self, id_objeto: int, posicao: Tuple[float, float], tipo_bau: str, itens: List[Dict[str, object]], aberto: bool = False, raio_colisao: float = 0.42) -> None:
        self.Id = int(id_objeto)
        self.id_objeto = self.Id
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.nome = "bau"
        self.TipoBau = str(tipo_bau or "Comum").strip() or "Comum"
        self.Itens = [dict(i) for i in itens if isinstance(i, dict)]
        self.Aberto = bool(aberto)
        self.Colisor = Colisor(x=self.Posicao[0], y=self.Posicao[1], raio_colisao=float(raio_colisao), raio_interacao=0.85)
        self.AberturaLocalMs = int(pygame.time.get_ticks()) if self.Aberto else 0
        self.AguardandoConfirmacaoAbertura = False
        self._aguardando_desde_ms = 0

    @classmethod
    def _obter_sprite(cls, caminho):
        caminho = str(caminho or "").strip()
        if not caminho:
            return None
        if caminho in cls._cache_sprites:
            return cls._cache_sprites[caminho]
        if not Path(caminho).exists():
            cls._cache_sprites[caminho] = None
            return None
        try:
            sprite = pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            sprite = None
        cls._cache_sprites[caminho] = sprite
        return sprite

    @classmethod
    def _carregar_frames(cls, tipo_bau: str) -> List[pygame.Surface]:
        tipo = str(tipo_bau or "Comum").strip() or "Comum"
        if tipo in cls._frames_por_tipo:
            return cls._frames_por_tipo[tipo]
        base = Path("Recursos") / "Visual" / "Mundo" / "Baus" / f"Bau {tipo}"
        frames = carregar_frames(base, loader=cls._obter_sprite)
        cls._frames_por_tipo[tipo] = frames
        return frames

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def abrir(self) -> bool:
        if self.Aberto:
            return False
        self.Aberto = True
        self.AguardandoConfirmacaoAbertura = False
        self._aguardando_desde_ms = 0
        self.AberturaLocalMs = int(pygame.time.get_ticks())
        return True

    def _frame_atual(self, frames: List[pygame.Surface]) -> pygame.Surface | None:
        if not frames:
            return None
        if not self.Aberto or len(frames) == 1:
            return frames[0]
        if self.AberturaLocalMs <= 0:
            return frames[-1]
        decorrido = max(0, pygame.time.get_ticks() - self.AberturaLocalMs)
        progresso = min(1.0, decorrido / 1000.0)
        idx = min(len(frames) - 1, int(progresso * (len(frames) - 1)))
        return frames[idx]

    def render(self, tela, camera) -> None:
        frame = self._frame_atual(self._carregar_frames(self.TipoBau))
        if frame is None:
            return
        px, py = camera.mundo_para_tela_px(self.Posicao)
        escala = max(1, int(camera.TilePx * 0.95))
        sprite = pygame.transform.smoothscale(frame, (escala, escala))
        tela.blit(sprite, sprite.get_rect(center=(int(px), int(py))))

    desenhar = render

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, object]) -> "Bau":
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        posicao = snapshot.get("posicao", [0.0, 0.0])
        if not isinstance(posicao, (list, tuple)) or len(posicao) != 2:
            posicao = [0.0, 0.0]
        return cls(id_objeto=int(snapshot.get("id", 0)), posicao=(float(posicao[0]), float(posicao[1])), tipo_bau=str(estado.get("tipo_bau", "Comum")), itens=list(estado.get("itens", [])), aberto=bool(estado.get("aberto", False)), raio_colisao=float(snapshot.get("raio_colisao", 0.42)))

    def update(self, snapshot: Dict[str, object]) -> None:
        self.aplicar_snapshot(snapshot)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        posicao = snapshot.get("posicao", [self.Posicao[0], self.Posicao[1]])
        if isinstance(posicao, (list, tuple)) and len(posicao) == 2:
            self.definir_posicao(float(posicao[0]), float(posicao[1]))
        self.TipoBau = str(estado.get("tipo_bau", self.TipoBau)).strip() or "Comum"
        self.Itens = [dict(i) for i in list(estado.get("itens", self.Itens)) if isinstance(i, dict)]
        self.Colisor.raio_colisao = max(0.1, float(snapshot.get("raio_colisao", self.Colisor.raio_colisao)))
        if bool(estado.get("aberto", False)):
            self.abrir()
        elif self.AguardandoConfirmacaoAbertura and self._aguardando_desde_ms > 0:
            if (pygame.time.get_ticks() - self._aguardando_desde_ms) > 1800:
                self.AguardandoConfirmacaoAbertura = False
                self._aguardando_desde_ms = 0

    def processar_interacao_player(self, player) -> Dict[str, object] | None:
        return None
