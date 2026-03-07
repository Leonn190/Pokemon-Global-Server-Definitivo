import pygame
from Codigo.Prefabs.Texto import Texto


def _clamp(valor, minimo, maximo):
    return minimo if valor < minimo else maximo if valor > maximo else valor


class Barra:
    def __init__(
        self,
        rect,
        texto="",
        valor=0,
        minimo=0,
        maximo=100,
        casas_decimais=0,
        mostrar_rotulo=True,
        suavizacao=14.0,
    ):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.minimo = float(minimo)
        self.maximo = float(maximo)
        self.valor = _clamp(float(valor), self.minimo, self.maximo)
        self.valor_visual = self.valor
        self.casas_decimais = casas_decimais
        self.mostrar_rotulo = bool(mostrar_rotulo)
        self.suavizacao = max(0.01, float(suavizacao))

        self.cor_fundo = (25, 28, 40)
        self.cor_preenchimento = (60, 170, 255)
        self.cor_borda = (180, 200, 255)

        self.rotulo = Texto(
            "",
            pos=(self.rect.x, self.rect.y - 30),
            style={
                "size": 30,
                "align": "topleft",
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self._atualizar_rotulo()

    def _atualizar_rotulo(self):
        valor = round(self.valor, self.casas_decimais)
        if self.casas_decimais == 0:
            valor = int(valor)
        self.rotulo.set_text(f"{self.texto}: {valor}")
        self.rotulo.set_pos((self.rect.x, self.rect.y - 36))

    def set_valor(self, valor):
        self.valor = _clamp(float(valor), self.minimo, self.maximo)
        self._atualizar_rotulo()

    def atualizar(self, dt):
        dt = max(0.0, float(dt))
        fator = min(1.0, dt * self.suavizacao)
        self.valor_visual += (self.valor - self.valor_visual) * fator
        if abs(self.valor_visual - self.valor) < 0.001:
            self.valor_visual = self.valor

    def percentual(self):
        return (self.valor_visual - self.minimo) / float(max(self.maximo - self.minimo, 1))

    def _desenhar_barra(self, tela):
        percentual = _clamp(self.percentual(), 0.0, 1.0)
        preenchimento = int(self.rect.width * percentual)

        pygame.draw.rect(tela, self.cor_fundo, self.rect, border_radius=12)
        if preenchimento > 0:
            pygame.draw.rect(
                tela,
                self.cor_preenchimento,
                pygame.Rect(self.rect.x, self.rect.y, preenchimento, self.rect.height),
                border_radius=12,
            )

        pygame.draw.rect(tela, self.cor_borda, self.rect, width=2, border_radius=12)

    def render(self, tela, eventos=None, dt=0.0):
        self.atualizar(dt)
        self._desenhar_barra(tela)
        if self.mostrar_rotulo and self.texto:
            self.rotulo.draw(tela)
        return False


class BarraEditavel(Barra):
    def __init__(self, rect, texto, valor, minimo, maximo, casas_decimais=0):
        super().__init__(rect, texto, valor, minimo, maximo, casas_decimais=casas_decimais, mostrar_rotulo=True)
        self.arrastando = False
        self._estava_arrastando = False
        self.cor_manopla = (245, 245, 255)

    def _valor_por_mouse(self, mouse_x):
        proporcao = (mouse_x - self.rect.x) / float(max(self.rect.width, 1))
        proporcao = _clamp(proporcao, 0.0, 1.0)
        self.set_valor(self.minimo + (self.maximo - self.minimo) * proporcao)

    def _encaixar_no_ponto_mais_proximo(self):
        if self.maximo <= self.minimo:
            return
        passo = 1.0 / (10 ** max(self.casas_decimais, 0))
        if passo <= 0:
            return

        idx = round((self.valor - self.minimo) / passo)
        alvo = self.minimo + (idx * passo)
        self.set_valor(alvo)

    def render(self, tela, eventos, dt=0.0):
        mouse_pos = pygame.mouse.get_pos()
        alterou = False

        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.rect.collidepoint(mouse_pos):
                self.arrastando = True
                self._estava_arrastando = True
                valor_antes = self.valor
                self._valor_por_mouse(evento.pos[0])
                alterou = alterou or (self.valor != valor_antes)

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self._estava_arrastando:
                    valor_antes = self.valor
                    self._encaixar_no_ponto_mais_proximo()
                    alterou = alterou or (self.valor != valor_antes)
                self.arrastando = False
                self._estava_arrastando = False

            if evento.type == pygame.MOUSEMOTION and self.arrastando:
                valor_antes = self.valor
                self._valor_por_mouse(evento.pos[0])
                alterou = alterou or (self.valor != valor_antes)

        self.atualizar(dt)
        self._desenhar_barra(tela)

        percentual = _clamp((self.valor - self.minimo) / float(max(self.maximo - self.minimo, 1)), 0.0, 1.0)
        x_manopla = self.rect.x + int(self.rect.width * percentual)
        x_manopla = _clamp(x_manopla, self.rect.x, self.rect.right)
        pygame.draw.circle(tela, self.cor_manopla, (int(x_manopla), self.rect.centery), self.rect.height // 2 + 4)
        pygame.draw.circle(tela, (30, 30, 45), (int(x_manopla), self.rect.centery), self.rect.height // 2 + 4, 2)

        self.rotulo.draw(tela)
        return alterou
