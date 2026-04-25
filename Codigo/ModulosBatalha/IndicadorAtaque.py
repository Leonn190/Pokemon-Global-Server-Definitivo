from __future__ import annotations

import math
from typing import Tuple

import pygame


class IndicadorAtaque:
    CORES = {
        "ataque": (255, 156, 62),
        "movimento": (82, 168, 255),
        "troca_posicao": (92, 216, 122),
        "troca_reserva": (92, 216, 122),
    }

    def __init__(self):
        self.origem: Tuple[float, float] | None = None
        self.destino: Tuple[float, float] | None = None
        self.tipo_acao = "ataque"
        self.estado = "preparando"
        self.valido = True
        self.cor = self.CORES["ataque"]
        self.alpha = 210
        self.tempo_animacao = 0.0
        self.pontos_setas: list[tuple[float, float]] = []
        self.id_acao = None

    def configurar(self, origem, destino, tipo_acao, estado="preparando", valido=True, id_acao=None):
        self.origem = tuple(origem) if origem else None
        self.destino = tuple(destino) if destino else None
        self.tipo_acao = str(tipo_acao or "ataque")
        self.estado = str(estado or "preparando")
        self.valido = bool(valido)
        self.id_acao = id_acao
        self.tempo_animacao = 0.0
        self._atualizar_cor_alpha()
        self.calcular_pontos_setas()
        return self

    def _atualizar_cor_alpha(self):
        self.cor = self.CORES.get(self.tipo_acao, self.CORES["ataque"])
        if not self.valido:
            self.cor = (238, 76, 76)
        self.alpha = 148 if self.estado == "preparado" else 220

    def atualizar(self, destino_atual=None, dt=0.0):
        self.tempo_animacao += max(0.0, float(dt or 0.0))
        if destino_atual is not None:
            self.destino = tuple(destino_atual)
            self.calcular_pontos_setas()
        if self.estado == "preparando":
            self.alpha = 180 + int(50 * (0.5 + 0.5 * math.sin(self.tempo_animacao * 8.0)))

    def desenhar(self, surface, camera=None):
        _ = camera
        if self.origem is None or self.destino is None:
            return
        origem = (int(self.origem[0]), int(self.origem[1]))
        destino = (int(self.destino[0]), int(self.destino[1]))
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.line(overlay, (*self.cor, self.alpha), origem, destino, 4)
        for ponto in self.pontos_setas:
            self._desenhar_seta(overlay, ponto)
        surface.blit(overlay, (0, 0))

    def _desenhar_seta(self, surface, ponto):
        if self.origem is None or self.destino is None:
            return
        angle = math.atan2(self.destino[1] - self.origem[1], self.destino[0] - self.origem[0])
        comprimento = 11
        abertura = 0.6
        p = (float(ponto[0]), float(ponto[1]))
        p1 = (p[0] - comprimento * math.cos(angle - abertura), p[1] - comprimento * math.sin(angle - abertura))
        p2 = (p[0] - comprimento * math.cos(angle + abertura), p[1] - comprimento * math.sin(angle + abertura))
        pygame.draw.polygon(
            surface,
            (*self.cor, max(80, self.alpha - 20)),
            [(int(p[0]), int(p[1])), (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1]))],
        )

    def definir_estado_preparando(self):
        self.estado = "preparando"
        self._atualizar_cor_alpha()

    def definir_estado_preparado(self):
        self.estado = "preparado"
        self._atualizar_cor_alpha()

    def definir_validade(self, valido):
        self.valido = bool(valido)
        self._atualizar_cor_alpha()

    def calcular_pontos_setas(self):
        self.pontos_setas = []
        if self.origem is None or self.destino is None:
            return
        dx = float(self.destino[0]) - float(self.origem[0])
        dy = float(self.destino[1]) - float(self.origem[1])
        dist = math.hypot(dx, dy)
        if dist < 20:
            return
        passos = max(1, int(dist // 40))
        for i in range(1, passos + 1):
            t = i / (passos + 1)
            self.pontos_setas.append((self.origem[0] + dx * t, self.origem[1] + dy * t))

    def copiar_para_preparado(self, id_acao):
        novo = IndicadorAtaque()
        novo.configurar(self.origem, self.destino, self.tipo_acao, estado="preparado", valido=self.valido, id_acao=id_acao)
        return novo
