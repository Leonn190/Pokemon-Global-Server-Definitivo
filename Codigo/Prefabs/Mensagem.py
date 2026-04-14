import pygame

from __future__ import annotations

from pathlib import Path

from Codigo.Prefabs.Texto import Texto

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
        if not isinstance(item, dict):
            item = {
                "texto": str(item),
                "tipo": "info",
                "duracao": float(self.style["duracao"]),
                "tempo": 0.0,
            }
            self._fila[0] = item

        item.setdefault("texto", "")
        item.setdefault("tipo", "info")
        item.setdefault("duracao", float(self.style["duracao"]))
        item.setdefault("tempo", 0.0)

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

class MensagensGanhosMundo:
    def __init__(self) -> None:
        self._fila: list[dict] = []
        self._icone_moeda = self._carregar_icone_moeda((22, 22))
        self._mapa_icones = self._mapear_icones_itens()

    @staticmethod
    def _carregar_icone_moeda(size: tuple[int, int]) -> pygame.Surface | None:
        caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "Moeda.png"
        if not caminho.exists():
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(str(caminho)).convert_alpha(), size)
        except pygame.error:
            return None

    @staticmethod
    def _mapear_icones_itens() -> dict[str, Path]:
        base = Path("Recursos") / "Visual" / "Itens"
        mapa: dict[str, Path] = {}
        if not base.exists():
            return mapa
        for arquivo in base.rglob("*.png"):
            mapa[arquivo.stem.strip().lower()] = arquivo
        return mapa

    def _icone_item(self, nome_item: str) -> pygame.Surface | None:
        caminho = self._mapa_icones.get(str(nome_item or "").strip().lower())
        if caminho is None or not caminho.exists():
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(str(caminho)).convert_alpha(), (22, 22))
        except pygame.error:
            return None

    def adicionar_item(self, nome_item: str, quantidade: int) -> None:
        qtd = max(1, int(quantidade or 1))
        self._fila.append(
            {
                "tipo": "item",
                "titulo": f"Ganhou {str(nome_item or 'item')} x{qtd}",
                "icone": self._icone_item(nome_item),
                "vida": 2.8,
                "idade": 0.0,
                "x_lerp": 1.0,
                "alpha": 0.0,
            }
        )

    def adicionar_moedas(self, quantidade: int) -> None:
        qtd = max(1, int(quantidade or 1))
        self._fila.append(
            {
                "tipo": "moedas",
                "titulo": f"Ganhou {qtd} moedas",
                "icone": self._icone_moeda,
                "vida": 2.8,
                "idade": 0.0,
                "x_lerp": 1.0,
                "alpha": 0.0,
            }
        )

    def adicionar_xp(self, quantidade: int) -> None:
        qtd = max(1, int(quantidade or 1))
        self._fila.append(
            {
                "tipo": "xp",
                "titulo": f"Ganhou {qtd} XP",
                "icone": None,
                "vida": 2.8,
                "idade": 0.0,
                "x_lerp": 1.0,
                "alpha": 0.0,
            }
        )

    def atualizar(self, dt: float) -> None:
        dt_seg = max(0.0, float(dt or 0.0))
        nova = []
        for item in self._fila:
            item["idade"] = float(item.get("idade", 0.0)) + dt_seg
            vida = float(item.get("vida", 2.8))
            t = item["idade"]
            entrada = min(1.0, t / 0.25)
            saida = 1.0 if t < (vida - 0.45) else max(0.0, (vida - t) / 0.45)
            item["alpha"] = min(1.0, entrada) * saida
            item["x_lerp"] = max(0.0, 1.0 - min(1.0, t / 0.30))
            if t <= vida:
                nova.append(item)
        self._fila = nova

    def desenhar(self, tela: pygame.Surface) -> None:
        if not self._fila:
            return
        w, h = tela.get_size()
        base_y = h - 26
        card_w = min(320, max(250, int(w * 0.28)))
        card_h = 42
        espaco = 8

        for idx, item in enumerate(reversed(self._fila)):
            alpha_mul = float(item.get("alpha", 0.0))
            if alpha_mul <= 0.01:
                continue
            destino_x = w - card_w - 18
            offscreen_x = w + 16
            x = int(destino_x + (offscreen_x - destino_x) * float(item.get("x_lerp", 1.0)))
            y = int(base_y - (idx + 1) * (card_h + espaco))

            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            a = int(205 * alpha_mul)
            pygame.draw.rect(card, (13, 22, 38, a), card.get_rect(), border_radius=12)
            pygame.draw.rect(card, (118, 152, 211, int(220 * alpha_mul)), card.get_rect(), 2, border_radius=12)

            icone = item.get("icone")
            if isinstance(icone, pygame.Surface):
                ic = icone.copy()
                ic.set_alpha(int(255 * alpha_mul))
                card.blit(ic, ic.get_rect(midleft=(14, card_h // 2)))
                tx = 32
            elif str(item.get("tipo")) == "xp":
                Texto("XP", pos=(14, card_h // 2), style={"size": 16, "align": "midleft", "outline": True, "color": (146, 219, 255)}).draw(card)
                tx = 34
            else:
                tx = 14

            Texto(str(item.get("titulo") or "Ganho"), pos=(tx, card_h // 2), style={"size": 16, "align": "midleft", "outline": True, "color": (236, 242, 255)}).draw(card)
            card.set_alpha(int(255 * alpha_mul))
            tela.blit(card, (x, y))

