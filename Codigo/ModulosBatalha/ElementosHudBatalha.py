from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

import pygame

from Codigo.Prefabs.Botao import Botao


class ElementosHudBatalha:
    def __init__(self, ao_fugir: Optional[Callable[[], None]] = None) -> None:
        self._ao_fugir = ao_fugir
        self._botao_fugir: Optional[Botao] = None
        self._icone_fugir: Optional[pygame.Surface] = None
        self._cache_tamanho: Optional[tuple[int, int]] = None
        self._fuga_pressao = 0.0
        self._fuga_alvo = 8.0
        self._fuga_taxa_clique = 1.65
        self._fuga_taxa_decay = 0.95
        self._fuga_disparada = False

    def _carregar_icone(self, lado: int) -> Optional[pygame.Surface]:
        caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "fugir.png"
        if not caminho.exists():
            return None
        try:
            img = pygame.image.load(str(caminho)).convert_alpha()
            return pygame.transform.smoothscale(img, (lado, lado))
        except pygame.error:
            return None

    def _garantir_layout(self, tela: pygame.Surface) -> None:
        tamanho = tuple(tela.get_size())
        if self._cache_tamanho == tamanho and self._botao_fugir is not None:
            return
        self._cache_tamanho = tamanho
        w, h = tamanho
        lado = max(56, min(80, int(min(w, h) * 0.085)))
        margem = max(16, int(lado * 0.25))
        rect = pygame.Rect(margem, h - lado - margem, lado, lado)
        self._botao_fugir = Botao(
            rect,
            "",
            execute=lambda _jogo, _botao: self._pressionar_fuga(),
            style={
                "radius": max(8, int(lado * 0.20)),
                "border_width": 2,
                "bg": (26, 33, 44),
                "bg_hover": (38, 50, 67),
                "bg_pressed": (16, 23, 34),
                "border": (147, 176, 214),
                "border_hover": (214, 230, 255),
                "text_style": {"size": 1, "outline_thickness": 0, "shadow": False},
            },
        )
        self._icone_fugir = self._carregar_icone(max(24, int(lado * 0.68)))

    def _pressionar_fuga(self) -> None:
        self._fuga_pressao = min(self._fuga_alvo, self._fuga_pressao + self._fuga_taxa_clique)
        if (not self._fuga_disparada) and self._fuga_pressao >= self._fuga_alvo:
            self._fuga_disparada = True
            if callable(self._ao_fugir):
                self._ao_fugir()

    def _atualizar_fuga(self, dt: float) -> None:
        if self._fuga_disparada:
            return
        fator = max(0.0, min(1.0, float(dt) * 60.0))
        queda = self._fuga_taxa_decay * fator
        self._fuga_pressao = max(0.0, self._fuga_pressao - queda)

    def _desenhar_overlay_fuga(self, tela: pygame.Surface) -> None:
        if self._fuga_pressao <= 0.01:
            return
        t = max(0.0, min(1.0, self._fuga_pressao / max(0.01, self._fuga_alvo)))
        overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * t)))
        tela.blit(overlay, (0, 0))

    def desenhar(self, tela: pygame.Surface, eventos: List[pygame.event.Event], dt: float = 0.0) -> None:
        self._garantir_layout(tela)
        self._atualizar_fuga(dt)
        if self._botao_fugir is not None:
            self._botao_fugir.render(tela, eventos or [], dt, None)
            if self._icone_fugir is not None:
                rect = self._icone_fugir.get_rect(center=self._botao_fugir.rect.center)
                tela.blit(self._icone_fugir, rect)
        self._desenhar_overlay_fuga(tela)
