from __future__ import annotations

from pathlib import Path
from typing import Callable, Tuple

import pygame

from Codigo.ModulosGerais.Auxiliares import carregar_frames
from Codigo.Visual.AuxiliaresVisuais import EFEITOS_ATAQUE_FPS

Vector2 = Tuple[float, float]


class ArenaAnimator:
    _cache_frames_efeitos: dict[str, list[pygame.Surface]] = {}

    def __init__(
        self,
        posicao_mundo: Callable[[object], Vector2 | None],
        posicao_tela: Callable[[Vector2], Vector2 | None],
    ) -> None:
        self._posicao_mundo = posicao_mundo
        self._posicao_tela = posicao_tela
        self.animacoes: list[dict[str, object]] = []

    def animar_efeito(self, alvo, nome_efeito_gif, posicao="alvo"):
        frames = self._carregar_frames_efeito(nome_efeito_gif)
        pos_mundo = self._posicao_mundo(alvo)
        if pos_mundo is None or not frames:
            return None
        fps = float(EFEITOS_ATAQUE_FPS.get(str(nome_efeito_gif), 20.0) or 20.0)
        duracao = max(0.15, len(frames) / max(1.0, fps))
        anim = {
            "tipo": "gif",
            "alvo": alvo,
            "pos_mundo": pos_mundo,
            "frames": frames,
            "fps": fps,
            "tempo": 0.0,
            "duracao": duracao,
            "bloqueante": False,
        }
        self.animacoes.append(anim)
        return anim

    def atualizar(self, dt):
        dt = max(0.0, float(dt or 0.0))
        restantes = []
        for anim in list(self.animacoes):
            anim["tempo"] = float(anim.get("tempo", 0.0)) + dt
            if float(anim.get("tempo", 0.0)) < float(anim.get("duracao", 0.0)):
                restantes.append(anim)
        self.animacoes = restantes

    def desenhar(self, surface):
        for anim in list(self.animacoes):
            self._desenhar_gif(surface, anim)

    def esta_ocupado(self):
        return any(bool(anim.get("bloqueante", False)) for anim in self.animacoes)

    def _carregar_frames_efeito(self, nome):
        nome = str(nome or "").strip()
        if not nome:
            return []
        if nome in self._cache_frames_efeitos:
            return self._cache_frames_efeitos[nome]
        base = Path.cwd() / "Recursos" / "Visual" / "AtaquesGifs"
        candidatos = [base / nome, base / f"{nome}_frames"]
        frames = []
        for pasta in candidatos:
            if not pasta.exists() or not pasta.is_dir():
                continue
            try:
                frames = carregar_frames(pasta)
            except Exception:
                frames = []
            if frames:
                break
        self._cache_frames_efeitos[nome] = [f for f in frames if isinstance(f, pygame.Surface)]
        return self._cache_frames_efeitos[nome]

    def _desenhar_gif(self, surface, anim):
        frames = anim.get("frames") if isinstance(anim.get("frames"), list) else []
        alvo = anim.get("alvo")
        pos_mundo = self._posicao_mundo(alvo) or anim.get("pos_mundo")
        pos = self._posicao_tela(pos_mundo)
        if not frames or pos is None:
            return
        fps = max(1.0, float(anim.get("fps", 20.0) or 20.0))
        idx = min(len(frames) - 1, int(float(anim.get("tempo", 0.0)) * fps) % len(frames))
        frame = frames[idx]
        if not isinstance(frame, pygame.Surface):
            return
        rect = getattr(alvo, "RectAtual", pygame.Rect(0, 0, 72, 72))
        tamanho_base = max(rect.size or (72, 72)) if isinstance(rect, pygame.Rect) else 72
        tamanho = max(72, int(tamanho_base * 1.35))
        img = pygame.transform.smoothscale(frame, (tamanho, tamanho)).convert_alpha()
        surface.blit(img, img.get_rect(center=(int(pos[0]), int(pos[1]))))
