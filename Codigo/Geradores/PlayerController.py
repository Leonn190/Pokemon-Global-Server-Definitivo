"""Controlador de player local para cena de mundo."""

from __future__ import annotations

import math

import pygame


class PlayerController:
    def __init__(self, ator, velocidade_px=220.0, callback_diff=None):
        self.Ator = ator
        self.VelocidadePx = float(velocidade_px)
        self.CallbackDiff = callback_diff

    def atualizar(self, eventos, dt, mouse_pos_mundo):
        dt = max(0.0, float(dt))
        self._processar_input_tapa(eventos)
        self._processar_rotacao(mouse_pos_mundo)
        moveu = self._processar_movimento(dt)
        self.Ator.atualizar(dt)
        self.Ator.atualizar_colisor_mao_mundo()
        if moveu:
            self._emitir_diff_update_posicao()

    def _emitir_diff(self, tipo, payload):
        if callable(self.CallbackDiff):
            self.CallbackDiff({"tipo": tipo, "objeto_id": getattr(self.Ator, "Id", None), "payload": payload})

    def _emitir_diff_update_posicao(self):
        self._emitir_diff("update", {"posicao": [self.Ator.Posicao[0], self.Ator.Posicao[1]]})

    def _processar_movimento(self, dt):
        teclas = pygame.key.get_pressed()
        eixo_x = 0.0
        eixo_y = 0.0

        if teclas[pygame.K_a]:
            eixo_x -= 1.0
        if teclas[pygame.K_d]:
            eixo_x += 1.0
        if teclas[pygame.K_w]:
            eixo_y -= 1.0
        if teclas[pygame.K_s]:
            eixo_y += 1.0

        mag = math.hypot(eixo_x, eixo_y)
        if mag > 0:
            eixo_x /= mag
            eixo_y /= mag

        antes = self.Ator.Posicao
        self.Ator.mover(eixo_x * self.VelocidadePx * dt, eixo_y * self.VelocidadePx * dt)
        return self.Ator.Posicao != antes

    def _processar_rotacao(self, mouse_pos_mundo):
        px, py = self.Ator.Posicao
        mx, my = mouse_pos_mundo
        dx = mx - px
        dy = my - py
        if dx == 0 and dy == 0:
            return
        angulo = math.degrees(math.atan2(-dy, dx))
        self.Ator.definir_angulo_olhar(angulo)
        self._emitir_diff("update", {"estado": {"angulo": angulo}})

    def _processar_input_tapa(self, eventos):
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.Ator.iniciar_tapa()
                self._emitir_diff("update", {"estado": {"tapa": True}})
