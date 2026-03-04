import pygame


class Mensagem:
    """Toast visual temporário e configurável para feedback rápido."""

    DEFAULT_STYLE = {
        "padding": (26, 18),
        "radius": 18,
        "max_width": 900,
        "font_size": 32,
        "font_color": (245, 246, 255),
        "border_color": (255, 220, 120),
        "border_width": 2,
        "bg_color": (14, 20, 38, 225),
        "shadow_color": (0, 0, 0, 120),
        "shadow_offset": (0, 6),
        "duracao": 3.2,
        "fade_in": 0.22,
        "fade_out": 0.30,
        "margem_topo": 34,
        "slide_dist": 20,
    }

    def __init__(self, tela_size, style=None, fila_externa=None, limite_fila=4):
        self.style = dict(self.DEFAULT_STYLE)
        if style:
            self.style.update(style)

        self._largura_tela, self._altura_tela = tela_size
        self._fila = fila_externa if fila_externa is not None else []
        self._limite_fila = max(1, int(limite_fila))
        self._fonte = pygame.font.Font(None, int(self.style["font_size"]))

    def set_fila_externa(self, fila_externa):
        self._fila = fila_externa if fila_externa is not None else []

    def redimensionar(self, tela_size):
        self._largura_tela, self._altura_tela = tela_size

    def set_style(self, **kwargs):
        self.style.update(kwargs)
        if "font_size" in kwargs:
            self._fonte = pygame.font.Font(None, int(self.style["font_size"]))

    def emitir(self, texto, tipo="info", duracao=None):
        tipo_mensagem = self._normalizar_tipo(tipo)
        self._fila.append(
            {
                "texto": str(texto),
                "tipo": tipo_mensagem,
                "duracao": float(duracao or self.style["duracao"]),
                "tempo": 0.0,
            }
        )
        excesso = len(self._fila) - self._limite_fila
        if excesso > 0:
            del self._fila[0:excesso]

    def _normalizar_tipo(self, tipo):
        tipo = str(tipo).lower().strip()
        if tipo in ("sucesso", "positivo", "positiva"):
            return "sucesso"
        if tipo in ("erro", "negativo", "negativa"):
            return "erro"
        return "info"

    def _cores_tipo(self, tipo):
        if tipo == "sucesso":
            return (118, 255, 162), (19, 55, 35, 230)
        if tipo == "erro":
            return (255, 130, 130), (66, 20, 24, 230)
        return (255, 226, 120), (72, 58, 18, 230)

    def _alfa_animacao(self, item):
        tempo = item["tempo"]
        dur = item["duracao"]
        fade_in = float(self.style["fade_in"])
        fade_out = float(self.style["fade_out"])

        if tempo < fade_in:
            return max(0.0, min(1.0, tempo / max(0.001, fade_in)))
        if tempo > dur - fade_out:
            return max(0.0, min(1.0, (dur - tempo) / max(0.001, fade_out)))
        return 1.0

    def render(self, tela, dt):
        if not self._fila:
            return

        item = self._fila[0]
        fator_duracao = 0.55 if len(self._fila) > 1 else 1.0
        duracao_efetiva = max(0.45, item["duracao"] * fator_duracao)

        item["tempo"] += dt
        if item["tempo"] >= duracao_efetiva:
            self._fila.pop(0)
            return

        item_render = dict(item)
        item_render["duracao"] = duracao_efetiva

        alpha = self._alfa_animacao(item_render)
        borda, fundo = self._cores_tipo(item["tipo"])

        texto = self._fonte.render(item["texto"], True, self.style["font_color"])
        texto_rect = texto.get_rect()
        pad_x, pad_y = self.style["padding"]

        largura = min(self.style["max_width"], texto_rect.width + pad_x * 2)
        altura = texto_rect.height + pad_y * 2

        caixa = pygame.Rect(0, 0, largura, altura)
        caixa.centerx = self._largura_tela // 2

        slide = int((1.0 - alpha) * self.style["slide_dist"])
        caixa.top = self.style["margem_topo"] - slide

        placa = pygame.Surface(caixa.size, pygame.SRCALPHA)

        sombra = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(
            sombra,
            self.style["shadow_color"],
            sombra.get_rect(),
            border_radius=int(self.style["radius"]),
        )

        pygame.draw.rect(placa, fundo, placa.get_rect(), border_radius=int(self.style["radius"]))
        pygame.draw.rect(
            placa,
            borda,
            placa.get_rect(),
            width=int(self.style["border_width"]),
            border_radius=int(self.style["radius"]),
        )

        texto_dest = texto.get_rect(center=placa.get_rect().center)
        placa.blit(texto, texto_dest)

        alfa_byte = max(0, min(255, int(255 * alpha)))
        sombra.set_alpha(int(alfa_byte * 0.7))
        placa.set_alpha(alfa_byte)

        off_x, off_y = self.style["shadow_offset"]
        tela.blit(sombra, (caixa.x + off_x, caixa.y + off_y))
        tela.blit(placa, caixa.topleft)
