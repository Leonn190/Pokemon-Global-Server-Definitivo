import pygame
from Codigo.Prefabs.Texto import Texto


def _clamp(valor, minimo, maximo):
    return minimo if valor < minimo else maximo if valor > maximo else valor


class Barra:
    def __init__(self, rect, texto, valor, minimo, maximo, casas_decimais=0):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.minimo = float(minimo)
        self.maximo = float(maximo)
        self.valor = float(valor)
        self.casas_decimais = casas_decimais
        self.arrastando = False

        self.cor_fundo = (25, 28, 40)
        self.cor_preenchimento = (60, 170, 255)
        self.cor_borda = (180, 200, 255)
        self.cor_manopla = (245, 245, 255)

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
        self.rotulo.set_pos((self.rect.x, self.rect.y - 34))

    def set_valor(self, valor):
        self.valor = _clamp(float(valor), self.minimo, self.maximo)
        self._atualizar_rotulo()

    def _valor_por_mouse(self, mouse_x):
        proporcao = (mouse_x - self.rect.x) / float(max(self.rect.width, 1))
        proporcao = _clamp(proporcao, 0.0, 1.0)
        self.set_valor(self.minimo + (self.maximo - self.minimo) * proporcao)

    def render(self, tela, eventos):
        mouse_pos = pygame.mouse.get_pos()
        alterou = False

        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.rect.collidepoint(mouse_pos):
                self.arrastando = True
                valor_antes = self.valor
                self._valor_por_mouse(mouse_pos[0])
                alterou = alterou or (self.valor != valor_antes)

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                self.arrastando = False

            if evento.type == pygame.MOUSEMOTION and self.arrastando:
                valor_antes = self.valor
                self._valor_por_mouse(mouse_pos[0])
                alterou = alterou or (self.valor != valor_antes)

        percentual = (self.valor - self.minimo) / float(max(self.maximo - self.minimo, 1))
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

        x_manopla = self.rect.x + preenchimento
        x_manopla = _clamp(x_manopla, self.rect.x, self.rect.right)
        pygame.draw.circle(tela, self.cor_manopla, (int(x_manopla), self.rect.centery), self.rect.height // 2 + 4)
        pygame.draw.circle(tela, (30, 30, 45), (int(x_manopla), self.rect.centery), self.rect.height // 2 + 4, 2)

        self.rotulo.draw(tela)
        return alterou
