"""Representação simples de Pokémon no mundo do cliente."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class PokemonMundo(Entidade):
    """Entidade de pokemon controlada por diffs do servidor."""

    _cache_frames: Dict[str, List[pygame.Surface]] = {}
    _cache_frames_escalados: Dict[Tuple[str, int], List[pygame.Surface]] = {}

    def __init__(self, snapshot: Dict[str, object]) -> None:
        pos = self._pos(snapshot.get("posicao"))
        raio = max(0.2, self._f(snapshot.get("raio_colisao"), 0.45))
        try:
            oid = int(snapshot.get("id", 0))
        except (TypeError, ValueError):
            oid = 0
        super().__init__(posicao=pos, raio_colisao=raio, raio_interacao=max(1.1, raio), id_objeto=oid)
        self.Destino: Vector2 = pos
        self.Nome = "Pokemon"
        self.Especie = "Pokemon"
        self.Info: Dict[str, object] = {"stats": {}}
        self._velocidade_interp_tiles_s = 2.5
        self.aplicar_snapshot(snapshot)

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

    @classmethod
    def _carregar_frames_nome(cls, nome: str) -> List[pygame.Surface]:
        chave = str(nome or "").strip().lower()
        if not chave:
            return []
        if chave in cls._cache_frames:
            return cls._cache_frames[chave]

        pasta = _PASTA_ANIMACOES / chave
        frames: List[pygame.Surface] = []
        if pasta.exists() and pasta.is_dir():
            arquivos = sorted(pasta.glob("*.png"), key=lambda p: p.name)
            for arquivo in arquivos:
                try:
                    frames.append(pygame.image.load(str(arquivo)).convert_alpha())
                except Exception:
                    continue

        cls._cache_frames[chave] = frames
        return frames

    @classmethod
    def _obter_frames_escalados(cls, nome: str, tamanho_px: int) -> List[pygame.Surface]:
        tamanho = max(8, int(tamanho_px))
        chave = (str(nome or "").strip().lower(), tamanho)
        if chave in cls._cache_frames_escalados:
            return cls._cache_frames_escalados[chave]

        frames = cls._carregar_frames_nome(chave[0])
        frames_escalados: List[pygame.Surface] = []
        for frame in frames:
            try:
                frames_escalados.append(pygame.transform.smoothscale(frame, (tamanho, tamanho)))
            except Exception:
                continue
        cls._cache_frames_escalados[chave] = frames_escalados
        return frames_escalados

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}

        self.Especie = str(estado.get("especie") or snapshot.get("nome") or self.Especie or "Pokemon")
        self.Nome = str(estado.get("nome") or snapshot.get("nome") or self.Especie or "Pokemon")

        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
        stats_norm = {str(k): self._f(v) for k, v in stats.items()}
        self.Info = {
            "id": int(snapshot.get("id", self.Id)),
            "nome": self.Nome,
            "especie": self.Especie,
            "stats": stats_norm,
            "nivel": estado.get("nivel", 1),
            "raridade": estado.get("raridade"),
            "tipos": list(estado.get("tipos") or []),
        }

        self.Colisor.raio_colisao = max(0.2, self._f(snapshot.get("raio_colisao"), self.Colisor.raio_colisao))
        destino = self._pos(snapshot.get("posicao"))
        vel_stats = self._f(stats_norm.get("Vel"), 0.0)
        self._velocidade_interp_tiles_s = max(1.2, min(3.2, 1.2 + (vel_stats / 220.0)))

        movimento = str(snapshot.get("movimento") or estado.get("movimento") or "mover").strip().lower()
        if movimento == "teleportar":
            self.Destino = destino
            self.definir_posicao(destino[0], destino[1])
        else:
            self.Destino = destino

    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        px, py = self.Posicao
        dx, dy = self.Destino
        dist = ((dx - px) ** 2 + (dy - py) ** 2) ** 0.5
        if dist <= 1e-4:
            self.definir_posicao(dx, dy)
            return
        passo = max(0.0, self._velocidade_interp_tiles_s * dt)
        if passo >= dist:
            self.definir_posicao(dx, dy)
            return
        k = passo / dist
        self.definir_posicao(px + (dx - px) * k, py + (dy - py) * k)

    def desenhar(self, tela, camera, dt: float) -> None:
        self.atualizar(dt)
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        centro = (int(cx), int(cy))
        tile_px = int(getattr(camera, "TilePx", 50))
        base = max(6, int(tile_px * self.Colisor.raio_colisao))
        t = pygame.time.get_ticks() * 0.008
        pulsar = 1.0 + math.sin(t + (abs(hash(self.Nome)) % 360) * 0.017) * 0.06
        r1 = max(5, int(base * pulsar))
        r2 = max(3, int(r1 * 0.62))

        pygame.draw.circle(tela, (70, 155, 245), centro, r1)
        pygame.draw.circle(tela, (24, 84, 190), centro, r1, 2)
        pygame.draw.circle(tela, (120, 210, 255), centro, r2)

        sprite_tamanho = max(14, int(r1 * 1.6))
        frames = self._obter_frames_escalados(self.Nome, sprite_tamanho)
        if frames:
            idx = int((pygame.time.get_ticks() / 120) % len(frames))
            frame = frames[idx]
            rect = frame.get_rect(center=centro)
            tela.blit(frame, rect)
