from __future__ import annotations

from typing import Callable, List, Optional

import pygame

from Codigo.Paineis.PainelTimes import PainelTimes
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto
from Codigo.Telas.Subtelas.Subtela import Subtela


class SubtelaPreBatalha(Subtela):
    alpha_overlay = 180

    def __init__(self, times: List[dict], ao_confirmar: Callable[[dict], None], titulo: str = "Escolha seu time"):
        super().__init__()
        self.Ativa = True
        self._times = list(times or [])
        self._ao_confirmar = ao_confirmar
        self._titulo = Texto(str(titulo), style={"size": 30, "color": (240, 244, 255), "outline": True, "outline_color": (4, 8, 16), "outline_thickness": 2})

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._painel_rect = pygame.Rect(0, 0, 0, 0)
        self._botao_rect = pygame.Rect(0, 0, 0, 0)
        self._painel: Optional[PainelTimes] = None
        self._botao_pronto: Optional[Botao] = None
        self._indice_selecionado = 0 if self._times else -1
        self._cache_tamanho = None

    def _garantir_layout(self, tela: pygame.Surface) -> None:
        tamanho = tuple(tela.get_size())
        if self._cache_tamanho == tamanho and self._painel is not None and self._botao_pronto is not None:
            return
        self._cache_tamanho = tamanho
        w, h = tamanho
        mw = min(850, int(w * 0.72))
        mh = min(650, int(h * 0.84))
        self._rect = pygame.Rect((w - mw) // 2, (h - mh) // 2, mw, mh)

        cab_h = 72
        rod_h = 86
        self._painel_rect = pygame.Rect(self._rect.x + 22, self._rect.y + cab_h, self._rect.width - 44, self._rect.height - cab_h - rod_h)
        self._botao_rect = pygame.Rect(self._rect.centerx - 88, self._rect.bottom - 62, 176, 42)

        if self._painel is None:
            self._painel = PainelTimes(self._painel_rect, self._times, slots_por_time=6, modo_selecao=True, indice_selecionado=self._indice_selecionado)
        else:
            self._painel.configurar_rect(self._painel_rect)
            self._painel.definir_times(self._times)
            self._painel.definir_modo_selecao(True)
            self._painel.definir_indice_selecionado(self._indice_selecionado)

        if self._botao_pronto is None:
            self._botao_pronto = Botao(self._botao_rect, "Pronto!", execute=lambda _jogo, _botao: self._confirmar())
        else:
            self._botao_pronto.base_rect = pygame.Rect(self._botao_rect)
            self._botao_pronto.rect = pygame.Rect(self._botao_rect)

    def _confirmar(self) -> None:
        if self._indice_selecionado < 0 or self._indice_selecionado >= len(self._times):
            return
        if callable(self._ao_confirmar):
            self._ao_confirmar(dict(self._times[self._indice_selecionado]))
        self.Ativa = False
        self.encerrada = True

    def processar_eventos(self, _jogo, eventos):
        if not self.Ativa:
            return False
        for ev in eventos:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.Ativa = False
                self.encerrada = True
                return True
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self._painel is not None:
                idx = self._painel.indice_time_no_mouse(ev.pos)
                if idx is not None:
                    self._indice_selecionado = idx
                    self._painel.definir_indice_selecionado(idx)
        return True

    def render(self, tela, eventos, dt, JOGO=None):
        _ = (dt, JOGO)
        self._garantir_layout(tela)

        pygame.draw.rect(tela, (14, 21, 34), self._rect, border_radius=18)
        pygame.draw.rect(tela, (70, 96, 148), self._rect, 2, border_radius=18)

        self._titulo.set_pos((self._rect.centerx, self._rect.y + 36))
        self._titulo.draw(tela)

        if self._painel is not None:
            self._painel.desenhar(tela, eventos=eventos, dt=dt)
        if self._botao_pronto is not None:
            self._botao_pronto.set_habilitado(self._indice_selecionado >= 0)
            self._botao_pronto.render(tela, eventos or [], dt, JOGO)

    @property
    def ativa(self):
        return bool(self.Ativa) and not self.encerrada
