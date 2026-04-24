from __future__ import annotations

import math
from typing import Dict, Iterable

import pygame


class IndicadoresAcoes:
    def __init__(self) -> None:
        self._cor_preview = (238, 246, 255, 170)
        self._cor_preparado = (238, 246, 255, 96)

    @staticmethod
    def _to_tela(camera, ponto: tuple[float, float]) -> tuple[int, int]:
        px, py = camera.batalha_para_tela_px((float(ponto[0]), float(ponto[1])))
        return int(px), int(py)

    @staticmethod
    def _norm(vx: float, vy: float) -> tuple[float, float, float]:
        n = math.hypot(vx, vy)
        if n <= 1e-6:
            return 1.0, 0.0, 0.0
        return vx / n, vy / n, n

    @staticmethod
    def _cor(cor, alpha_padrao: int | None = None):
        if len(cor) == 4:
            if alpha_padrao is None:
                return cor
            return cor[0], cor[1], cor[2], alpha_padrao
        if alpha_padrao is None:
            return cor
        return cor[0], cor[1], cor[2], alpha_padrao

    def _faixa(self, tela, camera, origem, destino, largura_tiles: float, cor, *, contorno: bool = False) -> None:
        ox, oy = self._to_tela(camera, origem)
        dx, dy = self._to_tela(camera, destino)
        ux, uy, dist = self._norm(dx - ox, dy - oy)
        if dist <= 1e-6:
            return
        tile = max(16, int(getattr(camera, "TilePx", 40) or 40))
        meia = max(2.0, float(largura_tiles) * tile * 0.5)
        px, py = -uy * meia, ux * meia
        pontos = [(ox + px, oy + py), (dx + px, dy + py), (dx - px, dy - py), (ox - px, oy - py)]
        pygame.draw.polygon(tela, self._cor(cor, 70), pontos)
        if contorno:
            pygame.draw.polygon(tela, cor, pontos, max(1, int(tile * 0.035)))
        pygame.draw.circle(tela, cor, (ox, oy), max(2, int(meia)), 1)
        pygame.draw.circle(tela, cor, (dx, dy), max(2, int(meia)), 1)

    def _circulo(self, tela, camera, centro, raio_tiles: float, cor, *, preenchido: bool = False) -> None:
        tile = max(16, int(getattr(camera, "TilePx", 40) or 40))
        raio = max(2, int(float(raio_tiles) * tile))
        if preenchido:
            pygame.draw.circle(tela, self._cor(cor, 58), self._to_tela(camera, centro), raio)
        pygame.draw.circle(tela, cor, self._to_tela(camera, centro), raio, max(1, int(tile * 0.035)))

    def _cone(self, tela, camera, origem, destino, alcance: float, abertura_graus: float, cor) -> None:
        ox, oy = origem
        dx, dy = float(destino[0]) - ox, float(destino[1]) - oy
        angulo = math.atan2(dy, dx) if math.hypot(dx, dy) > 1e-6 else 0.0
        abertura = math.radians(max(1.0, float(abertura_graus)))
        passos = 18
        pontos = [self._to_tela(camera, origem)]
        for i in range(passos + 1):
            t = -0.5 + i / passos
            a = angulo + abertura * t
            p = (ox + math.cos(a) * alcance, oy + math.sin(a) * alcance)
            pontos.append(self._to_tela(camera, p))
        pygame.draw.polygon(tela, self._cor(cor, 56), pontos)
        pygame.draw.lines(tela, cor, True, pontos, 2)

    def _trapezio(self, tela, camera, origem, destino, altura: float, base: float, teto: float, cor) -> None:
        ox, oy = origem
        ux, uy, _ = self._norm(float(destino[0]) - ox, float(destino[1]) - oy)
        px, py = -uy, ux
        meia_base = float(base) * 0.5
        meia_teto = float(teto) * 0.5
        topo = (ox + ux * altura, oy + uy * altura)
        pontos_mundo = [
            (ox + px * meia_base, oy + py * meia_base),
            (topo[0] + px * meia_teto, topo[1] + py * meia_teto),
            (topo[0] - px * meia_teto, topo[1] - py * meia_teto),
            (ox - px * meia_base, oy - py * meia_base),
        ]
        pontos = [self._to_tela(camera, p) for p in pontos_mundo]
        pygame.draw.polygon(tela, self._cor(cor, 56), pontos)
        pygame.draw.polygon(tela, cor, pontos, 2)

    def _desenhar_seta_impulso(self, tela, camera, origem, destino, cor, intensidade: float = 0.5) -> None:
        ox, oy = self._to_tela(camera, origem)
        dx, dy = self._to_tela(camera, destino)
        ux, uy, dist = self._norm(dx - ox, dy - oy)
        if dist <= 1e-6:
            return
        tile = max(16, int(getattr(camera, "TilePx", 40) or 40))
        intensidade = max(0.0, min(1.0, float(intensidade)))
        alpha = cor[3] if len(cor) == 4 else 170
        cor = (255, int(255 * (1.0 - intensidade)), int(255 * (1.0 - intensidade)), alpha)
        largura = max(8.0, tile * 0.30)
        ponta_len = max(18.0, tile * 0.56)
        cabo_fim = max(0.0, dist - ponta_len * 0.82)
        px, py = -uy * largura * 0.5, ux * largura * 0.5
        cabo = [
            (ox + px, oy + py),
            (ox + ux * cabo_fim + px, oy + uy * cabo_fim + py),
            (ox + ux * cabo_fim - px, oy + uy * cabo_fim - py),
            (ox - px, oy - py),
        ]
        base_x = dx - ux * ponta_len
        base_y = dy - uy * ponta_len
        ponta = [
            (dx, dy),
            (base_x - py * 1.55, base_y + px * 1.55),
            (base_x + py * 1.55, base_y - px * 1.55),
        ]
        pygame.draw.polygon(tela, self._cor(cor, 92), cabo)
        pygame.draw.polygon(tela, cor, cabo, 1)
        pygame.draw.polygon(tela, self._cor(cor, 118), ponta)
        pygame.draw.polygon(tela, cor, ponta, 1)

    @staticmethod
    def estilo_de_ataque(ataque: Dict[str, object] | None, montador=None) -> str:
        if montador is not None:
            return str(montador.estilo_ataque(ataque) or "").casefold()
        if not isinstance(ataque, dict):
            return "movimento"
        return str(ataque.get("estilo") or "").casefold()

    def desenhar_preparando(self, tela, camera, preview: Dict[str, object], control: Dict[str, object] | None = None, *, preparado: bool = False) -> None:
        if not bool(preview.get("_em_camada")):
            camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            preview_camada = dict(preview)
            preview_camada["_em_camada"] = True
            self.desenhar_preparando(camada, camera, preview_camada, control, preparado=preparado)
            tela.blit(camada, (0, 0))
            return
        estilo = str(preview.get("estilo") or "movimento").casefold()
        invalido = bool(preview.get("invalido"))
        cor = (255, 120, 120, 170) if invalido else self._cor_preview
        if preparado:
            cor = (cor[0], cor[1], cor[2], self._cor_preparado[3])
        origem = preview.get("origem_mundo")
        destino = preview.get("destino_mundo")
        if not (isinstance(origem, (tuple, list)) and len(origem) == 2):
            return

        if estilo == "alvo":
            self._circulo(tela, camera, origem, float(preview.get("alcance", 3.0)), cor)
        elif estilo == "status":
            return
        elif estilo == "zona":
            self._circulo(tela, camera, origem, float(preview.get("alcance", 6.0)), self._cor(cor, 80))
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                self._circulo(tela, camera, destino, float(preview.get("raio", 1.0)), cor, preenchido=True)
        elif estilo == "laser":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                self._faixa(tela, camera, origem, destino, float(preview.get("grossura", 0.8)), cor, contorno=True)
        elif estilo == "area":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                forma = str(preview.get("forma") or "cone").casefold()
                alcance = float(preview.get("alcance", 2.0))
                if forma == "trapezio":
                    self._trapezio(tela, camera, origem, destino, alcance, float(preview.get("base", 0.8)), float(preview.get("teto", 2.2)), cor)
                else:
                    self._cone(tela, camera, origem, destino, alcance, float(preview.get("abertura_graus", 70.0)), cor)
        elif estilo in {"projetil", "explosivo"}:
            segmentos = list(preview.get("segmentos") or [])
            raio = float(preview.get("raio", 0.35))
            for segmento in segmentos:
                if not isinstance(segmento, dict):
                    continue
                ini = segmento.get("inicio")
                fim = segmento.get("fim")
                if isinstance(ini, (tuple, list)) and len(ini) == 2 and isinstance(fim, (tuple, list)) and len(fim) == 2:
                    self._faixa(tela, camera, ini, fim, raio * 2.0, cor, contorno=True)
            zonas = list(preview.get("zonas_explosao") or [])
            zona = preview.get("zona_explosao") if not zonas and isinstance(preview.get("zona_explosao"), dict) else None
            if zona:
                zonas.append(zona)
            for zona in zonas:
                if isinstance(zona, dict) and isinstance(zona.get("centro"), (tuple, list)):
                    self._circulo(tela, camera, zona["centro"], float(zona.get("raio", 1.5)), cor, preenchido=True)
        elif estilo == "dash":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                self._faixa(tela, camera, origem, destino, float(preview.get("largura", 1.0)), cor, contorno=True)
        elif estilo == "impulso":
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                self._desenhar_seta_impulso(tela, camera, origem, destino, cor, float(preview.get("intensidade", 0.5)))
        elif estilo in {"movimento", "troca"}:
            if isinstance(destino, (tuple, list)) and len(destino) == 2:
                cor_mov = cor if estilo != "troca" else (255, 220, 80, 112)
                self._faixa(tela, camera, origem, destino, 0.22, cor_mov, contorno=True)
                self._circulo(tela, camera, destino, max(0.25, float(preview.get("largura", 1.0)) * 0.5), cor_mov, preenchido=True)
        elif estilo == "parede":
            ponto_a = preview.get("ponto_a")
            ponto_b = preview.get("ponto_b") or destino
            if isinstance(ponto_a, (tuple, list)) and len(ponto_a) == 2:
                if not preparado:
                    self._circulo(tela, camera, origem, float(preview.get("alcance", 6.0)), self._cor(cor, 54))
                    self._circulo(tela, camera, ponto_a, float(preview.get("distancia_max_entre_pontos", 4.0)), self._cor(cor, 70))
                if isinstance(ponto_b, (tuple, list)) and len(ponto_b) == 2:
                    self._faixa(tela, camera, ponto_a, ponto_b, float(preview.get("largura", 0.25)), cor, contorno=True)

    def desenhar_preparadas(self, tela, camera, visuais: Iterable[Dict[str, object]]) -> None:
        for item in visuais or []:
            estilo = str(item.get("estilo") or ("troca" if item.get("troca_reserva_id") else "movimento" if item.get("tipo_movimento") and not item.get("ataque") else "")).casefold()
            origem = item.get("origem_mundo")
            if not (isinstance(origem, (tuple, list)) and len(origem) == 2):
                continue
            surf = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            preview = dict(item)
            preview["estilo"] = estilo
            self.desenhar_preparando(surf, camera, preview, preparado=True)
            tela.blit(surf, (0, 0))
