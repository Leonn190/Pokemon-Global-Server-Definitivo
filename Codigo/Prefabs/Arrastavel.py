import pygame


class Arrastavel:
    def __init__(self):
        self.Ativo = False
        self.Item = None
        self.Origem = None
        self.Rect = pygame.Rect(0, 0, 0, 0)
        self._offset_mouse = (0, 0)
        self.BotaoInicial = 1
        self.ModoDistribuidor = False
        self._slots_distribuidos = set()

    def iniciar(self, item, origem, rect_item, mouse_pos, botao=1):
        self.Ativo = True
        self.Item = item
        self.Origem = origem
        self.Rect = pygame.Rect(rect_item)
        self.BotaoInicial = botao
        self.ModoDistribuidor = False
        self._slots_distribuidos = set()
        self._offset_mouse = (
            mouse_pos[0] - self.Rect.x,
            mouse_pos[1] - self.Rect.y,
        )

    def atualizar(self, mouse_pos):
        if not self.Ativo:
            return
        self.Rect.x = int(mouse_pos[0] - self._offset_mouse[0])
        self.Rect.y = int(mouse_pos[1] - self._offset_mouse[1])

    def ativar_distribuidor(self):
        self.ModoDistribuidor = True
        self._slots_distribuidos = set()

    def limpar_distribuidor(self):
        self.ModoDistribuidor = False
        self._slots_distribuidos = set()

    def pode_distribuir_em(self, alvo):
        return alvo not in self._slots_distribuidos

    def registrar_distribuicao(self, alvo):
        self._slots_distribuidos.add(alvo)

    def vazio(self):
        if not self.Ativo or self.Item is None:
            return True
        if isinstance(self.Item, dict) and 'quantidade' in self.Item:
            return int(self.Item.get('quantidade', 0)) <= 0
        return False

    def cancelar(self):
        self.Ativo = False
        self.Item = None
        self.Origem = None
        self.Rect = pygame.Rect(0, 0, 0, 0)
        self._offset_mouse = (0, 0)
        self.BotaoInicial = 1
        self.ModoDistribuidor = False
        self._slots_distribuidos = set()
