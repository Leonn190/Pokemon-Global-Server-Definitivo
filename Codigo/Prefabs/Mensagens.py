from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Prefabs.Texto import Texto


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
