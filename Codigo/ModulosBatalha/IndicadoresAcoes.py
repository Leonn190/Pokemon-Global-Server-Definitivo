from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

import pygame


class IndicadoresAcoes:
    def __init__(self) -> None:
        self._cor_preview = (255, 255, 255)
        self._cor_preparado = (255, 255, 255, 110)

    @staticmethod
    def _to_tela(camera, ponto: tuple[float, float]) -> tuple[int, int]:
        px, py = camera.batalha_para_tela_px((float(ponto[0]), float(ponto[1])))
        return int(px), int(py)

    @staticmethod
    def _norm(vx: float, vy: float) -> tuple[float, float, float]:
        n = math.hypot(vx, vy)
        if n <= 1e-6:
            return 0.0, 0.0, 0.0
        return vx / n, vy / n, n

    def _seta(self, tela, camera, origem, destino, cor, espessura=3):
        o = self._to_tela(camera, origem)
        d = self._to_tela(camera, destino)
        pygame.draw.line(tela, cor, o, d, max(1, int(espessura)))
        vx = d[0] - o[0]
        vy = d[1] - o[1]
        ux, uy, n = self._norm(vx, vy)
        if n <= 1e-6:
            return
        ponta = (d[0], d[1])
        b1 = (int(d[0] - ux * 14 + uy * 8), int(d[1] - uy * 14 - ux * 8))
        b2 = (int(d[0] - ux * 14 - uy * 8), int(d[1] - uy * 14 + ux * 8))
        pygame.draw.polygon(tela, cor, [ponta, b1, b2])

    @staticmethod
    def estilo_de_ataque(ataque: Dict[str, object] | None, montador=None) -> str:
        if montador is not None:
            return str(montador.estilo_ataque(ataque) or "").casefold()
        if not isinstance(ataque, dict):
            return "movimento"
        return str(ataque.get("estilo") or "").casefold()

    def desenhar_preparando(self, tela, camera, preview: Dict[str, object], control: Dict[str, object] | None = None, *, preparado: bool = False) -> None:
        estilo = str(preview.get("estilo") or "movimento").casefold()
        invalido = bool(preview.get("invalido"))
        cor = (255, 130, 130) if invalido else self._cor_preview
        if preparado:
            alpha = 110
            cor = (*cor[:3], alpha) if len(cor) == 3 else (cor[0], cor[1], cor[2], alpha)
        origem = preview.get("origem_mundo")
        destino = preview.get("destino_mundo")
        if not (isinstance(origem, (tuple, list)) and len(origem) == 2):
            return
        o_px = self._to_tela(camera, origem)
        tile = max(16, int(getattr(camera, "TilePx", 40) or 40))

        if estilo == "alvo":
            alcance = float(preview.get("alcance", 3.0))
            pygame.draw.circle(tela, cor, o_px, int(alcance * tile), 2)
            for alvo in list((control or {}).get("alvos_validos") or []):
                if not (isinstance(alvo, (tuple, list)) and len(alvo) == 2):
                    continue
                pygame.draw.circle(tela, cor, self._to_tela(camera, alvo), max(6, tile // 4), 2)
        elif estilo == "zona":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                raio = float(preview.get("raio", 1.0))
                pygame.draw.circle(tela, cor, self._to_tela(camera, destino), int(raio * tile), 2)
                self._seta(tela, camera, origem, destino, cor, 2)
        elif estilo == "laser":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                self._seta(tela, camera, origem, destino, cor, 6)
        elif estilo == "area":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                self._seta(tela, camera, origem, destino, cor, 4)
        elif estilo in {"projetil", "dash", "impulso", "movimento", "troca"}:
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                esp = 3
                if estilo == "impulso":
                    esp = int(max(2, min(10, float(preview.get("intensidade", 0.5)) * 10)))
                self._seta(tela, camera, origem, destino, cor if estilo != "troca" else (255, 220, 80), esp)
        elif estilo == "status":
            pygame.draw.circle(tela, cor, o_px, max(12, tile // 2), 2)
        elif estilo == "irregular":
            ponto_a = preview.get("ponto_a") or origem
            ponto_b = preview.get("ponto_b") or destino
            if isinstance(ponto_a, (tuple, list)) and len(ponto_a) == 2:
                pygame.draw.circle(tela, cor, self._to_tela(camera, ponto_a), int(4 * tile), 1)
            if isinstance(ponto_a, (tuple, list)) and len(ponto_a) == 2 and isinstance(ponto_b, (tuple, list)) and len(ponto_b) == 2:
                self._seta(tela, camera, ponto_a, ponto_b, cor, max(1, int(tile * 0.25)))

    def desenhar_preparadas(self, tela, camera, visuais: Iterable[Dict[str, object]]) -> None:
        for item in visuais or []:
            estilo = str(item.get("estilo") or ("troca" if item.get("troca_reserva_id") else "movimento" if item.get("tipo_movimento") and not item.get("ataque") else "")).casefold()
            origem = item.get("origem_mundo")
            destino = item.get("destino_mundo")
            if not (isinstance(origem, (tuple, list)) and len(origem) == 2):
                continue
            surf = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            preview = {"estilo": estilo, "origem_mundo": origem, "destino_mundo": destino, "raio": item.get("raio", 1.0), "alcance": item.get("alcance", 3.0)}
            self.desenhar_preparando(surf, camera, preview, preparado=True)
            tela.blit(surf, (0, 0))
