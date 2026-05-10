from __future__ import annotations

import pygame


class PainelCaptura:
    def __init__(self) -> None:
        self._captura: dict[str, object] = {}
        self._token = ""
        self._tempo_restante = 0.0
        self._x_anim = 1.0
        self._fonte_titulo = None
        self._fonte_linha = None

    def _fontes(self):
        if self._fonte_titulo is None:
            self._fonte_titulo = pygame.font.Font(None, 24)
        if self._fonte_linha is None:
            self._fonte_linha = pygame.font.Font(None, 19)
        return self._fonte_titulo, self._fonte_linha

    @staticmethod
    def _f(valor, padrao=0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    def definir_captura(self, captura: dict | None) -> None:
        if not isinstance(captura, dict) or not captura:
            return
        token = str(captura.get("token_arremesso") or captura.get("token") or "")
        chave = token or str(captura.get("recebido_ms") or "")
        if chave and chave == self._token:
            return
        self._captura = dict(captura)
        self._token = chave
        self._tempo_restante = 3.0
        self._x_anim = 0.0

    def desenhar(self, tela, captura: dict | None = None, mostrar_minimapa: bool = False, dt: float = 0.0) -> None:
        self.definir_captura(captura)
        if not self._captura:
            return

        largura_tela, _altura_tela = tela.get_size()
        w, h = 300, 118
        margem = 12
        y = 12 + 180 + 10 if mostrar_minimapa else 86
        destino_x = largura_tela - w - margem
        fora_x = largura_tela + 12

        rect_hover = pygame.Rect(int(destino_x + (fora_x - destino_x) * self._x_anim), y, w, h)
        if rect_hover.collidepoint(pygame.mouse.get_pos()):
            self._tempo_restante = 3.0
        else:
            self._tempo_restante -= max(0.0, float(dt))

        alvo = 0.0 if self._tempo_restante > 0.0 else 1.0
        k = min(1.0, max(0.08, float(dt) * 8.0))
        self._x_anim += (alvo - self._x_anim) * k
        if self._x_anim >= 0.985 and self._tempo_restante <= 0.0:
            self._captura = {}
            return

        x = int(destino_x + (fora_x - destino_x) * self._x_anim)
        rect = pygame.Rect(x, y, w, h)
        painel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(painel, (12, 16, 24, 214), painel.get_rect(), border_radius=6)
        pygame.draw.rect(painel, (215, 224, 238, 96), painel.get_rect(), 1, border_radius=6)

        titulo_font, linha_font = self._fontes()
        resultado = str(self._captura.get("resultado") or "").strip().lower()
        titulo = "CAPTUROU" if resultado == "sucesso" else "FALHOU" if resultado == "falha" else "CAPTURA"
        cor_titulo = (112, 226, 155) if titulo == "CAPTUROU" else (255, 132, 118) if titulo == "FALHOU" else (238, 226, 150)
        painel.blit(titulo_font.render(titulo, True, cor_titulo), (14, 10))

        poder = self._f(self._captura.get("poder_total"), 0.0)
        dificuldade = self._f(self._captura.get("dificuldade_captura"), 0.0)
        chance = self._f(self._captura.get("chance_geral", self._captura.get("chance_real_3_checks")), 0.0)
        linhas = (
            f"Poder de Captura = {poder:.1f}",
            f"Dificuldade do Pokémon = {dificuldade:.1f}",
            f"Chance Geral = {chance:.1f}%",
        )
        for i, linha in enumerate(linhas):
            painel.blit(linha_font.render(linha, True, (232, 236, 243)), (14, 42 + i * 22))

        tela.blit(painel, rect)
