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
        self.PosAlvo = None
        self._ao_final_animacao = None
        self._velocidade_animacao = 16.0
        self._pos_anim = [0.0, 0.0]

    def iniciar(self, item, origem, rect_item, mouse_pos, botao=1):
        self.Ativo = True
        self.Item = item
        self.Origem = origem
        self.Rect = pygame.Rect(rect_item)
        self.Rect.center = (int(mouse_pos[0]), int(mouse_pos[1]))
        self.BotaoInicial = botao
        self.ModoDistribuidor = False
        self._slots_distribuidos = set()
        self.PosAlvo = None
        self._ao_final_animacao = None
        self._pos_anim = [float(self.Rect.x), float(self.Rect.y)]
        self._offset_mouse = (
            self.Rect.width // 2,
            self.Rect.height // 2,
        )

    def atualizar(self, mouse_pos):
        if not self.Ativo or self.PosAlvo is not None:
            return
        self.Rect.x = int(mouse_pos[0] - self._offset_mouse[0])
        self.Rect.y = int(mouse_pos[1] - self._offset_mouse[1])
        self._pos_anim[0] = float(self.Rect.x)
        self._pos_anim[1] = float(self.Rect.y)

    def definir_pos_alvo(self, pos_alvo, ao_final=None, velocidade=16.0):
        if not self.Ativo:
            return
        self.PosAlvo = (int(pos_alvo[0]), int(pos_alvo[1]))
        self._ao_final_animacao = ao_final
        self._velocidade_animacao = max(1.0, float(velocidade))
        self._pos_anim[0] = float(self.Rect.x)
        self._pos_anim[1] = float(self.Rect.y)

    def iniciar_retorno(self, pos_alvo, ao_retorno_logico=None, velocidade=16.0):
        if not self.Ativo:
            return

        def _finalizar():
            if callable(ao_retorno_logico):
                ao_retorno_logico()
            self.cancelar()

        self.definir_pos_alvo(pos_alvo, ao_final=_finalizar, velocidade=velocidade)

    def animar(self, dt):
        if not self.Ativo or self.PosAlvo is None:
            return
        fator = max(0.05, min(1.0, dt * self._velocidade_animacao))
        self._pos_anim[0] += (self.PosAlvo[0] - self._pos_anim[0]) * fator
        self._pos_anim[1] += (self.PosAlvo[1] - self._pos_anim[1]) * fator
        self.Rect.x = int(round(self._pos_anim[0]))
        self.Rect.y = int(round(self._pos_anim[1]))
        if abs(self._pos_anim[0] - self.PosAlvo[0]) <= 0.5 and abs(self._pos_anim[1] - self.PosAlvo[1]) <= 0.5:
            self.Rect.topleft = self.PosAlvo
            self._pos_anim[0] = float(self.PosAlvo[0])
            self._pos_anim[1] = float(self.PosAlvo[1])
            self.PosAlvo = None
            callback = self._ao_final_animacao
            self._ao_final_animacao = None
            if callable(callback):
                callback()

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
        self.PosAlvo = None
        self._ao_final_animacao = None
        self._pos_anim = [0.0, 0.0]
