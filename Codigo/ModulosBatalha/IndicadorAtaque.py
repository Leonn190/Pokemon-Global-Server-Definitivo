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
        self.coordenadas_mundo = False

    def configurar(self, origem, destino, tipo_acao, estado="preparando", valido=True, id_acao=None, coordenadas_mundo=False):
        self.origem = tuple(origem) if origem else None
        self.destino = tuple(destino) if destino else None
        self.tipo_acao = str(tipo_acao or "ataque")
        self.estado = str(estado or "preparando")
        self.valido = bool(valido)
        self.id_acao = id_acao
        self.coordenadas_mundo = bool(coordenadas_mundo)
        self.tempo_animacao = 0.0
        self._atualizar_cor_alpha()
        self.calcular_pontos_setas()
        return self

    def _atualizar_cor_alpha(self):
        self.cor = self.CORES.get(self.tipo_acao, self.CORES["ataque"])
        if not self.valido:
            self.cor = (238, 76, 76)
        self.alpha = 182 if self.estado == "preparado" else 232

    def atualizar(self, destino_atual=None, dt=0.0):
        self.tempo_animacao += max(0.0, float(dt or 0.0))
        if destino_atual is not None:
            self.destino = tuple(destino_atual)
            self.calcular_pontos_setas()
        if self.estado == "preparando":
            self.alpha = 198 + int(42 * (0.5 + 0.5 * math.sin(self.tempo_animacao * 8.0)))

    def desenhar(self, surface, camera=None):
        if self.origem is None or self.destino is None:
            return
        origem, destino = self.origem, self.destino
        if self.coordenadas_mundo and camera is not None:
            origem = camera.mundo_para_tela_px(origem)
            destino = camera.mundo_para_tela_px(destino)
        self._desenhar_fluxo_setas(surface, origem, destino)

    def _desenhar_fluxo_setas(self, surface, origem, destino):
        x1, y1 = float(origem[0]), float(origem[1])
        x2, y2 = float(destino[0]), float(destino[1])
        dx, dy = x2 - x1, y2 - y1
        dist_total = math.hypot(dx, dy)
        if dist_total <= 1:
            return
        dir_x, dir_y = dx / dist_total, dy / dist_total
        nx, ny = -dir_y, dir_x
        espacamento = 42.0 * 0.85
        num_setas = max(2, int(dist_total / espacamento))
        tempo = pygame.time.get_ticks() / 1000.0 if self.estado == "preparando" else 0.0
        deslocamento = ((tempo * 34.0) % espacamento) if self.estado == "preparando" else 0.0
        for i in range(num_setas):
            distancia = ((i + 0.5) * espacamento + deslocamento) % dist_total
            fator = distancia / dist_total
            px = x1 + dir_x * fator * dist_total
            py = y1 + dir_y * fator * dist_total
            onda = 0.5 + 0.5 * math.sin((2 * math.pi * 4.0 * fator) - (3.0 * tempo))
            alpha = int(max(45, min(255, onda * self.alpha)))
            self._desenhar_seta_entalhada(surface, px, py, dir_x, dir_y, nx, ny, alpha)

    def _desenhar_seta_entalhada(self, surface, px, py, dir_x, dir_y, nx, ny, alpha):
        raio = 5
        comprimento = max(10, int(raio * 3.5))
        largura = max(6, int(raio * 3.2))
        entalhe = 0.20

        tipx = px + dir_x * (comprimento / 2)
        tipy = py + dir_y * (comprimento / 2)
        backx = px - dir_x * (comprimento / 2)
        backy = py - dir_y * (comprimento / 2)
        topx = backx + nx * (largura / 2)
        topy = backy + ny * (largura / 2)
        botx = backx - nx * (largura / 2)
        boty = backy - ny * (largura / 2)
        notchx = px - dir_x * (comprimento * entalhe)
        notchy = py - dir_y * (comprimento * entalhe)
        pts = [(topx, topy), (notchx, notchy), (botx, boty), (tipx, tipy)]

        minx = int(min(p[0] for p in pts)) - 2
        miny = int(min(p[1] for p in pts)) - 2
        maxx = int(max(p[0] for p in pts)) + 2
        maxy = int(max(p[1] for p in pts)) + 2
        w, h = max(1, maxx - minx), max(1, maxy - miny)
        local = pygame.Surface((w, h), pygame.SRCALPHA)
        pts_local = [(x - minx, y - miny) for (x, y) in pts]
        pygame.draw.polygon(local, (*self.cor, alpha), pts_local)
        surface.blit(local, (minx, miny))

    @staticmethod
    def desenhar_pulso(surface, pos, cor=(255, 225, 70), raio_base=40, variacao=0.3, velocidade=2.0, alpha_base=88):
        if pos is None:
            return
        t = pygame.time.get_ticks() / 1000.0
        osc = math.sin(2 * math.pi * velocidade * t)
        raio = int(raio_base * (1 + variacao * osc * 0.5))
        alpha = int(alpha_base * (0.5 + 0.5 * (osc + 1) / 2))
        raio = max(4, raio)
        s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*cor, alpha), (raio, raio), raio)
        surface.blit(s, (int(pos[0]) - raio, int(pos[1]) - raio))

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
        novo.configurar(self.origem, self.destino, self.tipo_acao, estado="preparado", valido=self.valido, id_acao=id_acao, coordenadas_mundo=self.coordenadas_mundo)
        return novo
