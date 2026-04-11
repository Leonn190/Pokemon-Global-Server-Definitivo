from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pygame

Vec2 = pygame.math.Vector2


class LeitorFluxos:
    def __init__(self) -> None:
        self._tempo = 0.0
        self._fluxos = self._carregar_fluxos()

    def atualizar(self, dt: float) -> None:
        self._tempo += max(0.0, float(dt))

    @staticmethod
    def _safe_float(valor, padrao=0.0) -> float:
        try:
            if valor in (None, ""):
                return float(padrao)
            return float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            return float(padrao)

    @staticmethod
    def _clamp(valor: float, minimo: float, maximo: float) -> float:
        return max(minimo, min(maximo, valor))

    @staticmethod
    def _normalizar_nome(valor: object) -> str:
        return str(valor or "").strip().casefold()

    @classmethod
    def _arquivo_fluxos(cls) -> Optional[Path]:
        atual = Path(__file__).resolve()
        candidatos = [
            atual.parents[2] / "Dados" / "Pokemon Global Server - Fluxos.json",
            Path("Dados") / "Pokemon Global Server - Fluxos.json",
        ]
        for caminho in candidatos:
            if caminho.exists():
                return caminho
        return None

    def _carregar_fluxos(self) -> Dict[str, Dict[str, object]]:
        caminho = self._arquivo_fluxos()
        if caminho is None:
            return {}
        try:
            bruto = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        fluxos = bruto.get("fluxos") if isinstance(bruto, dict) else {}
        if not isinstance(fluxos, dict):
            return {}
        saida: Dict[str, Dict[str, object]] = {}
        for nome, dados in fluxos.items():
            if not isinstance(dados, dict):
                continue
            saida[self._normalizar_nome(nome)] = dict(dados)
        return saida

    def obter_fluxo(self, ataque: object) -> Dict[str, object]:
        if isinstance(ataque, dict):
            nome = ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome")
        else:
            nome = ataque
        return dict(self._fluxos.get(self._normalizar_nome(nome), {}))

    @staticmethod
    def _safe_normalize(vetor: Vec2) -> Vec2:
        if vetor.length_squared() <= 1e-9:
            return Vec2(1, 0)
        return vetor.normalize()

    @staticmethod
    def _desenhar_poligono(area: pygame.Surface, pontos: Iterable[Vec2], cor_fill, cor_borda, largura_borda: int = 2) -> None:
        pts = [(float(pt.x), float(pt.y)) for pt in pontos]
        if len(pts) < 3:
            return
        pygame.draw.polygon(area, cor_fill, pts)
        pygame.draw.polygon(area, cor_borda, pts, max(1, int(largura_borda)))

    def _construir_curva_ramo(
        self,
        inicio: Vec2,
        direcao: Vec2,
        perpendicular: Vec2,
        alcance_px: float,
        deslocamento_lateral_px: float,
        fluxo: Dict[str, object],
    ) -> List[Vec2]:
        segmentos = max(10, int(self._safe_float(fluxo.get("segmentos_corpo"), 26)))
        curvatura_lateral_px = self._safe_float(fluxo.get("curvatura_lateral_tiles"), 0.0) * (alcance_px / max(1.0, self._safe_float(fluxo.get("alcance_fixo_tiles"), 6.0)))
        curvatura_frontal_px = self._safe_float(fluxo.get("curvatura_frontal_tiles"), 0.0) * (alcance_px / max(1.0, self._safe_float(fluxo.get("alcance_fixo_tiles"), 6.0)))
        offset_lateral_final = self._safe_float(fluxo.get("offset_lateral_final_tiles"), 0.0)
        offset_frontal_final = self._safe_float(fluxo.get("offset_frontal_final_tiles"), 0.0)

        pontos: List[Vec2] = []
        for indice in range(segmentos + 1):
            t = indice / float(segmentos)
            curva = math.sin(t * math.pi) * curvatura_lateral_px
            frente = math.sin(t * math.pi) * curvatura_frontal_px
            lateral = deslocamento_lateral_px * (1.0 - t) + offset_lateral_final * t
            ponto = inicio + direcao * (alcance_px * t + frente + offset_frontal_final * t) + perpendicular * (lateral + curva)
            pontos.append(ponto)
        return pontos

    @staticmethod
    def _poligono_da_linha(pontos: List[Vec2], largura_inicio: float, largura_fim: float) -> List[Vec2]:
        if len(pontos) < 2:
            return []
        esquerda: List[Vec2] = []
        direita: List[Vec2] = []
        total = max(1, len(pontos) - 1)
        for indice, ponto in enumerate(pontos):
            if indice == 0:
                tangente = pontos[indice + 1] - ponto
            elif indice == len(pontos) - 1:
                tangente = ponto - pontos[indice - 1]
            else:
                tangente = pontos[indice + 1] - pontos[indice - 1]
            if tangente.length_squared() <= 1e-9:
                tangente = Vec2(1, 0)
            tangente = tangente.normalize()
            normal = Vec2(-tangente.y, tangente.x)
            t = indice / float(total)
            largura = largura_inicio + (largura_fim - largura_inicio) * t
            metade = max(1.0, largura * 0.5)
            esquerda.append(ponto + normal * metade)
            direita.append(ponto - normal * metade)
        return esquerda + list(reversed(direita))

    def _desenhar_ramos(self, area: pygame.Surface, inicio: Vec2, direcao: Vec2, alcance_px: float, fluxo: Dict[str, object], alpha: int, escala_px: float) -> None:
        quantidade = max(1, int(self._safe_float(fluxo.get("quantidade_ramos"), 1)))
        abertura = math.radians(self._safe_float(fluxo.get("abertura_ramos_graus"), 0.0))
        rotacao = math.radians(self._safe_float(fluxo.get("rotacao_ramos_graus"), 0.0))
        passo_lateral = self._safe_float(fluxo.get("passo_lateral_ramos_tiles"), 0.0)
        largura_inicio = self._safe_float(fluxo.get("largura_inicial_tiles"), 0.75)
        largura_fim = self._safe_float(fluxo.get("largura_final_tiles"), 0.9)
        perpendicular = Vec2(-direcao.y, direcao.x)

        for indice in range(quantidade):
            t = 0.0 if quantidade <= 1 else (indice / float(quantidade - 1)) - 0.5
            angulo = rotacao + abertura * t
            dir_ramo = Vec2(
                direcao.x * math.cos(angulo) - direcao.y * math.sin(angulo),
                direcao.x * math.sin(angulo) + direcao.y * math.cos(angulo),
            )
            lateral = passo_lateral * t
            curva = self._construir_curva_ramo(inicio, dir_ramo, perpendicular, alcance_px, lateral * escala_px, fluxo)
            poligono = self._poligono_da_linha(curva, largura_inicio * escala_px, largura_fim * escala_px)
            self._desenhar_poligono(
                area,
                poligono,
                (255, 255, 255, max(18, int(alpha * 0.52))),
                (255, 255, 255, max(46, int(alpha * 0.90))),
                2,
            )
            if not curva:
                continue
            for ponto in curva[:: max(2, len(curva) // 7)]:
                brilho = 0.5 + 0.5 * math.sin(self._tempo * 4.5 + ponto.x * 0.013 + ponto.y * 0.013)
                pygame.draw.circle(
                    area,
                    (255, 255, 255, max(0, int(alpha * 0.20 * brilho))),
                    (int(ponto.x), int(ponto.y)),
                    max(1, int(5 + brilho * 4)),
                )

    def _desenhar_setores(self, area: pygame.Surface, inicio: Vec2, direcao: Vec2, alcance_px: float, fluxo: Dict[str, object], alpha: int, escala_px: float) -> None:
        if not fluxo.get("usar_setor", False):
            return
        quantidade = max(1, int(self._safe_float(fluxo.get("quantidade_setores"), 1)))
        abertura = math.radians(self._safe_float(fluxo.get("abertura_setores_graus"), 55.0))
        rotacao = math.radians(self._safe_float(fluxo.get("rotacao_setores_graus"), 0.0))
        inicio_setor = self._safe_float(fluxo.get("inicio_setor_tiles"), 0.0)
        alcance_setor = self._safe_float(fluxo.get("alcance_setor_tiles"), 0.0)
        usar_alcance_geral = bool(fluxo.get("setor_usar_alcance_geral", False))
        angulo_setor = math.radians(self._safe_float(fluxo.get("angulo_setor_graus"), math.degrees(abertura)))
        segmentos = max(8, int(self._safe_float(fluxo.get("segmentos_setor"), 28)))

        comprimento = alcance_px if usar_alcance_geral or alcance_setor <= 0.0 else alcance_setor * escala_px
        raio_interno = max(0.0, inicio_setor * escala_px)
        ang_centro = math.atan2(direcao.y, direcao.x) + rotacao
        abertura_real = max(abertura, angulo_setor)

        for indice in range(quantidade):
            t = 0.0 if quantidade <= 1 else (indice / float(quantidade - 1)) - 0.5
            centro_atual = ang_centro + abertura * t
            pontos: List[Vec2] = []
            for passo in range(segmentos + 1):
                f = passo / float(segmentos)
                ang = centro_atual - abertura_real * 0.5 + abertura_real * f
                pontos.append(inicio + Vec2(math.cos(ang), math.sin(ang)) * (raio_interno + comprimento))
            for passo in range(segmentos, -1, -1):
                f = passo / float(segmentos)
                ang = centro_atual - abertura_real * 0.5 + abertura_real * f
                pontos.append(inicio + Vec2(math.cos(ang), math.sin(ang)) * raio_interno)
            self._desenhar_poligono(
                area,
                pontos,
                (255, 255, 255, max(16, int(alpha * 0.38))),
                (255, 255, 255, max(40, int(alpha * 0.78))),
                2,
            )

    def _desenhar_circulos(self, area: pygame.Surface, inicio: Vec2, direcao: Vec2, alcance_px: float, fluxo: Dict[str, object], alpha: int, escala_px: float) -> None:
        if fluxo.get("usar_area_final", False):
            raio = max(4.0, self._safe_float(fluxo.get("raio_area_final_tiles"), 1.0) * escala_px)
            offset = self._safe_float(fluxo.get("offset_area_final_tiles"), 0.0) * escala_px
            centro = inicio + direcao * (alcance_px + offset)
            pygame.draw.circle(area, (255, 255, 255, max(16, int(alpha * 0.35))), (int(centro.x), int(centro.y)), int(raio))
            pygame.draw.circle(area, (255, 255, 255, max(44, int(alpha * 0.85))), (int(centro.x), int(centro.y)), int(raio), 2)
        if fluxo.get("usar_area_extra", False):
            raio = max(4.0, self._safe_float(fluxo.get("raio_area_extra_tiles"), 1.0) * escala_px)
            offset = self._safe_float(fluxo.get("offset_area_extra_tiles"), 0.0) * escala_px
            centro = inicio + direcao * offset
            pygame.draw.circle(area, (255, 255, 255, max(12, int(alpha * 0.22))), (int(centro.x), int(centro.y)), int(raio))
            pygame.draw.circle(area, (255, 255, 255, max(30, int(alpha * 0.68))), (int(centro.x), int(centro.y)), int(raio), 2)

    def _desenhar_animacao(self, area: pygame.Surface, inicio: Vec2, fim: Vec2, alpha: int) -> None:
        direcao = self._safe_normalize(fim - inicio)
        distancia = max(1.0, (fim - inicio).length())
        perpendicular = Vec2(-direcao.y, direcao.x)
        passo = 36.0
        deslocamento = (self._tempo * 180.0) % passo
        cursor = -deslocamento
        while cursor < distancia + passo:
            centro = inicio + direcao * cursor + perpendicular * (math.sin(self._tempo * 5.5 + cursor * 0.06) * 3.0)
            largura = 24 + 8 * math.sin(self._tempo * 3.7 + cursor * 0.08)
            ponta = centro + direcao * largura
            pygame.draw.line(
                area,
                (255, 255, 255, max(0, int(alpha * 0.14))),
                (int(centro.x), int(centro.y)),
                (int(ponta.x), int(ponta.y)),
                3,
            )
            cursor += passo

    def desenhar(
        self,
        tela: pygame.Surface,
        ataque: object,
        inicio,
        fim,
        *,
        alpha: int = 120,
        animado: bool = True,
        tile_px: float = 42.0,
    ) -> None:
        inicio_v = Vec2(float(inicio[0]), float(inicio[1]))
        fim_v = Vec2(float(fim[0]), float(fim[1]))
        direcao = self._safe_normalize(fim_v - inicio_v)
        fluxo = self.obter_fluxo(ataque)
        area = pygame.Surface(tela.get_size(), pygame.SRCALPHA)

        if not fluxo:
            alcance = max(24.0, (fim_v - inicio_v).length())
            self._desenhar_setores(
                area,
                inicio_v,
                direcao,
                alcance,
                {
                    "usar_setor": True,
                    "quantidade_setores": 1,
                    "abertura_setores_graus": 0.0,
                    "angulo_setor_graus": 65.0,
                    "segmentos_setor": 26,
                    "setor_usar_alcance_geral": True,
                },
                alpha,
                42.0,
            )
            if animado:
                self._desenhar_animacao(area, inicio_v, inicio_v + direcao * alcance, alpha)
            tela.blit(area, (0, 0))
            return

        escala_px = max(18.0, float(tile_px))
        alcance_miravel = bool(fluxo.get("alcance_miravel", False))
        alcance_mouse = max(0.0, (fim_v - inicio_v).length() / escala_px)
        alcance = self._safe_float(fluxo.get("alcance_fixo_tiles"), max(alcance_mouse, 1.0))
        if alcance_miravel:
            alcance = self._clamp(
                alcance_mouse,
                self._safe_float(fluxo.get("alcance_min_tiles"), 0.0),
                max(self._safe_float(fluxo.get("alcance_max_tiles"), alcance_mouse), self._safe_float(fluxo.get("alcance_min_tiles"), 0.0)),
            )
        origem_gap = self._safe_float(fluxo.get("origem_gap_tiles"), 0.0) * escala_px
        alcance_px = max(18.0, alcance * escala_px)
        inicio_fluxo = inicio_v + direcao * origem_gap
        fim_fluxo = inicio_fluxo + direcao * alcance_px

        if fluxo.get("usar_corpo", True) or int(self._safe_float(fluxo.get("quantidade_ramos"), 1)) > 0:
            self._desenhar_ramos(area, inicio_fluxo, direcao, alcance_px, fluxo, alpha, escala_px)
        self._desenhar_setores(area, inicio_fluxo, direcao, alcance_px, fluxo, alpha, escala_px)
        self._desenhar_circulos(area, inicio_fluxo, direcao, alcance_px, fluxo, alpha, escala_px)

        if animado:
            self._desenhar_animacao(area, inicio_fluxo, fim_fluxo, alpha)

        tela.blit(area, (0, 0))
