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
        self.id_acao = None
        self.destino_snap_area_id: str | None = None
        self.destino_snap_slot_id: str | None = None
        self.destino_snap_pos: Tuple[float, float] | None = None

    def configurar(self, origem, destino, tipo_acao, estado="preparando", valido=True, id_acao=None):
        self.origem = tuple(origem) if origem else None
        self.destino = tuple(destino) if destino else None
        self.tipo_acao = str(tipo_acao or "ataque")
        self.estado = str(estado or "preparando")
        self.valido = bool(valido)
        self.id_acao = id_acao
        self.tempo_animacao = 0.0
        self.destino_snap_area_id = None
        self.destino_snap_slot_id = None
        self.destino_snap_pos = None
        self._atualizar_cor_alpha()
        return self

    def _atualizar_cor_alpha(self):
        self.cor = self.CORES.get(self.tipo_acao, self.CORES["ataque"])
        if not self.valido:
            self.cor = (238, 76, 76)
        self.alpha = 136 if self.estado == "preparado" else 218

    def atualizar(self, destino_atual=None, dt=0.0):
        self.tempo_animacao += max(0.0, float(dt or 0.0))
        if destino_atual is not None:
            self.destino = tuple(destino_atual)
        if self.estado == "preparando":
            self.alpha = 170 + int(50 * (0.5 + 0.5 * math.sin(self.tempo_animacao * 6.0)))
        else:
            self.alpha = 130 + int(20 * (0.5 + 0.5 * math.sin(self.tempo_animacao * 3.0)))

    def desenhar(self, surface, camera=None):
        _ = camera
        if self.origem is None or self.destino is None:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._desenhar_fluxo_setas(overlay)
        self._desenhar_pulso(overlay)
        surface.blit(overlay, (0, 0))

    def _desenhar_fluxo_setas(self, surface):
        if self.origem is None or self.destino is None:
            return
        ox, oy = float(self.origem[0]), float(self.origem[1])
        dx, dy = float(self.destino[0]) - ox, float(self.destino[1]) - oy
        dist = math.hypot(dx, dy)
        if dist < 8:
            return
        ux, uy = dx / dist, dy / dist
        passo = 30.0 if self.estado == "preparando" else 36.0
        quantidade = max(3, int(dist // passo) + 1)
        for i in range(quantidade):
            frac = (i / max(1, quantidade - 1))
            desloc = ((self.tempo_animacao * (0.85 if self.estado == "preparado" else 1.5)) + frac) % 1.0
            x = ox + ux * dist * desloc
            y = oy + uy * dist * desloc
            fase = math.sin((desloc * 6.0 + self.tempo_animacao * 3.8) * math.pi)
            alpha = int(max(50, min(235, self.alpha * (0.45 + 0.55 * (0.5 + 0.5 * fase)))))
            self._desenhar_seta_fluxo(surface, (x, y), (ux, uy), alpha)

    def _desenhar_seta_fluxo(self, surface, centro, direcao, alpha):
        ux, uy = direcao
        px, py = -uy, ux
        largura = 8.0
        comprimento = 16.0
        corte = 5.0
        cx, cy = centro
        ponta = (cx + ux * comprimento * 0.5, cy + uy * comprimento * 0.5)
        base = (cx - ux * comprimento * 0.5, cy - uy * comprimento * 0.5)
        recorte = (cx - ux * (comprimento * 0.5 - corte), cy - uy * (comprimento * 0.5 - corte))
        p1 = (base[0] + px * largura * 0.45, base[1] + py * largura * 0.45)
        p2 = (cx + px * largura, cy + py * largura)
        p3 = ponta
        p4 = (cx - px * largura, cy - py * largura)
        p5 = (base[0] - px * largura * 0.45, base[1] - py * largura * 0.45)
        p6 = recorte
        pygame.draw.polygon(surface, (*self.cor, int(alpha)), [p1, p2, p3, p4, p5, p6])

    def _desenhar_pulso(self, surface):
        if self.destino_snap_pos is None:
            return
        r_base = 10 if self.estado == "preparado" else 12
        pulso = 3.0 * (0.5 + 0.5 * math.sin(self.tempo_animacao * 5.0))
        raio = int(max(4, r_base + pulso))
        alpha = 45 if self.valido else 60
        cor = self.cor if self.valido else (238, 76, 76)
        pygame.draw.circle(surface, (*cor, alpha), (int(self.destino_snap_pos[0]), int(self.destino_snap_pos[1])), raio)
        pygame.draw.circle(surface, (*cor, int(alpha * 1.8)), (int(self.destino_snap_pos[0]), int(self.destino_snap_pos[1])), max(2, raio // 2), 1)

    def definir_estado_preparando(self):
        self.estado = "preparando"
        self._atualizar_cor_alpha()

    def definir_estado_preparado(self):
        self.estado = "preparado"
        self._atualizar_cor_alpha()

    def definir_validade(self, valido):
        self.valido = bool(valido)
        self._atualizar_cor_alpha()

    def definir_destino_snap(self, area_id=None, slot_id=None, pos=None, valido=True):
        self.destino_snap_area_id = str(area_id) if area_id else None
        self.destino_snap_slot_id = str(slot_id) if slot_id else None
        self.destino_snap_pos = tuple(pos) if pos is not None and (area_id or slot_id) else None
        self.destino = tuple(pos) if pos is not None else self.destino
        self.definir_validade(valido)

    def copiar_para_preparado(self, id_acao):
        novo = IndicadorAtaque()
        novo.configurar(self.origem, self.destino, self.tipo_acao, estado="preparado", valido=self.valido, id_acao=id_acao)
        return novo
