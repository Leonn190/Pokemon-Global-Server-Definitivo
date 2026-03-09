import pygame


class Arrastavel:
    def __init__(self):
        self.Ativo = False
        self.Item = None
        self.Origem = None
        self.Rect = pygame.Rect(0, 0, 0, 0)
        self._offset_mouse = (0, 0)

    def iniciar(self, item, origem, rect_item, mouse_pos):
        self.Ativo = True
        self.Item = item
        self.Origem = int(origem)
        self.Rect = pygame.Rect(rect_item)
        self._offset_mouse = (
            mouse_pos[0] - self.Rect.x,
            mouse_pos[1] - self.Rect.y,
        )

    def atualizar(self, mouse_pos):
        if not self.Ativo:
            return
        self.Rect.x = int(mouse_pos[0] - self._offset_mouse[0])
        self.Rect.y = int(mouse_pos[1] - self._offset_mouse[1])

    def cancelar(self):
        self.Ativo = False
        self.Item = None
        self.Origem = None
        self.Rect = pygame.Rect(0, 0, 0, 0)
        self._offset_mouse = (0, 0)
