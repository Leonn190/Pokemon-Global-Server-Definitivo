from __future__ import annotations

import math
from typing import Dict, Tuple

import pygame

Vector2 = Tuple[float, float]


class XpMundo:
    _XP_POR_TAMANHO = {"pequeno": 15, "medio": 40, "grande": 100}
    _ESCALA_POR_TAMANHO = {"pequeno": 0.18, "medio": 0.24, "grande": 0.30}

    def __init__(self, snapshot: Dict[str, object]):
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else (0.0, 0.0)
        self.Id = int(snapshot.get("id", 0) or 0)
        self.id_objeto = self.Id
        self.Posicao = (float(pos[0]), float(pos[1]))
        self.PosicaoInicial = self.Posicao
        self.PosicaoFinal = self.Posicao
        self.Velocidade = 3.6
        self.Voando = False
        self.Tamanho = "pequeno"
        self.XpValor = 15
        self.TempoAnimacao = 0.0
        self._alpha = 255
        self._sumindo_ttl = False
        self._fade_ttl_segundos = (10.0 / 30.0)
        self._fade_ttl_decorrido = 0.0
        self.aplicar_snapshot(snapshot)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else None
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            self.Posicao = (float(pos[0]), float(pos[1]))
        p0 = estado.get("pos_inicial") if isinstance(estado.get("pos_inicial"), (list, tuple)) else snapshot.get("pos_inicial")
        p1 = estado.get("pos_final") if isinstance(estado.get("pos_final"), (list, tuple)) else snapshot.get("pos_final")
        if isinstance(p0, (list, tuple)) and len(p0) == 2:
            self.PosicaoInicial = (float(p0[0]), float(p0[1]))
        if isinstance(p1, (list, tuple)) and len(p1) == 2:
            self.PosicaoFinal = (float(p1[0]), float(p1[1]))
        self.Velocidade = max(0.1, float(estado.get("velocidade", snapshot.get("velocidade", self.Velocidade)) or self.Velocidade))
        tamanho = str(snapshot.get("tamanho") or estado.get("tamanho") or self.Tamanho).strip().lower()
        self.Tamanho = tamanho if tamanho in self._XP_POR_TAMANHO else "pequeno"
        self.XpValor = int(snapshot.get("xp_valor") or estado.get("xp_valor") or self._XP_POR_TAMANHO.get(self.Tamanho, 15))
        voando_estado = estado.get("voando")
        if isinstance(voando_estado, bool):
            self.Voando = voando_estado
        else:
            self.Voando = math.hypot(self.PosicaoFinal[0] - self.Posicao[0], self.PosicaoFinal[1] - self.Posicao[1]) > 0.03
        if bool(estado.get("sumindo_ttl", False)):
            self._sumindo_ttl = True
            self._fade_ttl_segundos = max(0.033, float(estado.get("ttl_fade_ticks", 10) or 10) / 30.0)

    def _mover_para(self, destino: Vector2, velocidade: float, dt: float) -> bool:
        dx = float(destino[0]) - float(self.Posicao[0])
        dy = float(destino[1]) - float(self.Posicao[1])
        dist = math.hypot(dx, dy)
        if dist <= 0.03:
            self.Posicao = (float(destino[0]), float(destino[1]))
            return True
        passo = min(dist, max(0.1, float(velocidade)) * dt)
        self.Posicao = (self.Posicao[0] + (dx / dist) * passo, self.Posicao[1] + (dy / dist) * passo)
        return passo >= dist - 1e-6

    def atualizar_visual(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        if self.Voando and self._mover_para(self.PosicaoFinal, self.Velocidade, dt):
            self.Voando = False
        self.TempoAnimacao += dt
        if self._sumindo_ttl:
            self._fade_ttl_decorrido = min(self._fade_ttl_segundos, self._fade_ttl_decorrido + dt)
            t = self._fade_ttl_decorrido / max(0.001, self._fade_ttl_segundos)
            self._alpha = max(0, int(255 * (1.0 - t)))

    def desenhar(self, tela, camera) -> None:
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        lado_base = max(8, int(getattr(camera, "TilePx", 50) * self._ESCALA_POR_TAMANHO.get(self.Tamanho, 0.18)))
        pulso = 0.75 + 0.25 * (math.sin(self.TempoAnimacao * 4.4) * 0.5 + 0.5)
        cor = (40, int(130 + (90 * pulso)), 45, int(self._alpha))
        surf = pygame.Surface((lado_base, lado_base), pygame.SRCALPHA)
        pygame.draw.circle(surf, cor, (lado_base // 2, lado_base // 2), max(2, lado_base // 2 - 1))
        tela.blit(surf, surf.get_rect(center=(int(cx), int(cy))))
