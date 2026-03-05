from __future__ import annotations

import pygame


class Arrastavel:
    def __init__(self, rect, id_arrastavel=None, desenhar_callback=None):
        self.rect = pygame.Rect(rect)
        self.PosicaoOriginal = self.rect.topleft
        self.Id = id_arrastavel
        self.DesenharCallback = desenhar_callback

        self.Arrastando = False
        self._offset_mouse = (0, 0)
        self.AreasAcao = []

    def definir_posicao(self, pos):
        self.rect.topleft = (int(pos[0]), int(pos[1]))
        self.PosicaoOriginal = self.rect.topleft

    def voltar_para_origem(self):
        self.rect.topleft = self.PosicaoOriginal

    def adicionar_area_acao(self, area_rect, callback=None, area_id=None):
        self.AreasAcao.append((pygame.Rect(area_rect), callback, area_id))

    def limpar_areas_acao(self):
        self.AreasAcao.clear()

    def update(self, eventos):
        mouse = pygame.mouse.get_pos()
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.rect.collidepoint(evento.pos):
                self.Arrastando = True
                self._offset_mouse = (evento.pos[0] - self.rect.x, evento.pos[1] - self.rect.y)

            elif evento.type == pygame.MOUSEMOTION and self.Arrastando:
                self.rect.x = mouse[0] - self._offset_mouse[0]
                self.rect.y = mouse[1] - self._offset_mouse[1]

            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1 and self.Arrastando:
                self.Arrastando = False
                if not self._executar_area_acao():
                    self.voltar_para_origem()

    def _executar_area_acao(self):
        for area_rect, callback, area_id in self.AreasAcao:
            if not self.rect.colliderect(area_rect):
                continue
            if callable(callback):
                callback(self, area_id, area_rect)
            return True
        return False

    def draw(self, tela):
        if callable(self.DesenharCallback):
            self.DesenharCallback(tela, self)
            return
        pygame.draw.rect(tela, (95, 120, 175), self.rect, border_radius=6)
        pygame.draw.rect(tela, (15, 22, 33), self.rect, 2, border_radius=6)
