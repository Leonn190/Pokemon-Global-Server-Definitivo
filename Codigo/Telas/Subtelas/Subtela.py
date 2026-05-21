from __future__ import annotations

from typing import List, Optional

import pygame


class Subtela:
    """Contrato comum para subtelas/modais."""

    bloquear_input_fundo = True
    usar_overlay_gerenciador = True
    alpha_overlay = 170
    camada_render = "hud"
    animar_entrada = True
    fade_entrada_ms = 160

    def __init__(self):
        self.encerrada = False

    @property
    def ativa(self) -> bool:
        if hasattr(self, "Ativa"):
            return bool(getattr(self, "Ativa"))
        return not bool(getattr(self, "encerrada", False))

    def processar_eventos(self, _jogo, _eventos) -> bool:
        return self.ativa and self.bloquear_input_fundo

    def atualizar(self, _dt):
        return None

    def render(self, tela, eventos, dt, JOGO=None):
        raise NotImplementedError


class GerenciadorSubtelas:
    def __init__(self):
        self._pilha: List[Subtela] = []
        self._overlay_cache = None
        self._overlay_cache_size = None
        self._overlay_alpha = 170
        self._fade_surface_cache = None
        self._fade_surface_cache_size = None

    @property
    def ativa(self) -> bool:
        self._limpar_encerradas()
        return bool(self._pilha)

    @property
    def topo(self) -> Optional[Subtela]:
        self._limpar_encerradas()
        return self._pilha[-1] if self._pilha else None

    def limpar(self):
        self._pilha.clear()

    def abrir(self, subtela: Subtela):
        if subtela is None:
            return None
        subtela._fade_inicio_ms = pygame.time.get_ticks()
        self._pilha.append(subtela)
        return subtela

    def fechar_topo(self):
        topo = self.topo
        if topo is not None:
            topo.encerrada = True

    def fechar(self, subtela=None):
        if subtela is None:
            self.fechar_topo()
            return
        alvo = subtela
        if isinstance(subtela, type):
            alvo = self.obter_por_tipo(subtela)
        if alvo is not None:
            alvo.encerrada = True

    def obter_por_tipo(self, tipo):
        self._limpar_encerradas()
        for subtela in reversed(self._pilha):
            if isinstance(subtela, tipo):
                return subtela
        return None

    def contem(self, subtela_ou_tipo):
        if isinstance(subtela_ou_tipo, type):
            return self.obter_por_tipo(subtela_ou_tipo) is not None
        self._limpar_encerradas()
        return subtela_ou_tipo in self._pilha

    @property
    def bloquear_fundo(self):
        topo = self.topo
        return bool(getattr(topo, "bloquear_input_fundo", True)) if topo is not None else False

    def _limpar_encerradas(self):
        self._pilha = [s for s in self._pilha if s is not None and not getattr(s, "encerrada", False) and bool(getattr(s, "Ativa", True))]

    def filtrar_eventos_fundo(self, eventos):
        topo = self.topo
        if topo is None:
            return eventos
        return [] if bool(getattr(topo, "bloquear_input_fundo", True)) else eventos

    def _progresso_fade_entrada(self, subtela):
        if subtela is None or not bool(getattr(subtela, "animar_entrada", True)):
            return 1.0
        duracao = int(getattr(subtela, "fade_entrada_ms", 160) or 0)
        if duracao <= 0:
            return 1.0
        inicio = getattr(subtela, "_fade_inicio_ms", None)
        if inicio is None:
            return 1.0
        tempo = max(0, pygame.time.get_ticks() - int(inicio))
        progresso_linear = max(0.0, min(1.0, tempo / duracao))
        return 1.0 - ((1.0 - progresso_linear) ** 2)

    def _surface_fade(self, tela):
        tamanho = tela.get_size()
        if self._fade_surface_cache is None or self._fade_surface_cache_size != tamanho:
            self._fade_surface_cache = pygame.Surface(tamanho, pygame.SRCALPHA)
            self._fade_surface_cache_size = tamanho
        self._fade_surface_cache.set_alpha(255)
        self._fade_surface_cache.fill((0, 0, 0, 0))
        return self._fade_surface_cache

    def atualizar(self, jogo, eventos, dt):
        topo = self.topo
        if topo is None:
            return
        progresso = self._progresso_fade_entrada(topo)
        eventos_topo = eventos if progresso >= 1.0 else []
        if hasattr(topo, "processar_eventos"):
            topo.processar_eventos(jogo, eventos_topo)
        if hasattr(topo, "atualizar"):
            topo.atualizar(dt)
        self._limpar_encerradas()

    def _desenhar_overlay(self, tela, alpha):
        tamanho = tela.get_size()
        alpha = int(alpha)
        if self._overlay_cache is None or self._overlay_cache_size != tamanho:
            self._overlay_cache = pygame.Surface(tamanho, pygame.SRCALPHA)
            self._overlay_cache_size = tamanho
            self._overlay_alpha = None
        if self._overlay_alpha != alpha:
            self._overlay_cache.fill((0, 0, 0, alpha))
            self._overlay_alpha = alpha
        tela.blit(self._overlay_cache, (0, 0))

    def render(self, tela, eventos, dt, JOGO=None, camada="hud"):
        topo = self.topo
        if topo is None:
            return
        camada_topo = str(getattr(topo, "camada_render", "hud") or "hud").strip().lower()
        camada_atual = str(camada or "hud").strip().lower()
        if camada_topo != camada_atual:
            return
        progresso = self._progresso_fade_entrada(topo)
        if bool(getattr(topo, "usar_overlay_gerenciador", True)):
            self._desenhar_overlay(tela, int(getattr(topo, "alpha_overlay", 170) * progresso))
        if progresso >= 1.0:
            topo.render(tela, eventos, dt, JOGO=JOGO)
        else:
            surface = self._surface_fade(tela)
            topo.render(surface, [], dt, JOGO=JOGO)
            surface.set_alpha(int(255 * progresso))
            tela.blit(surface, (0, 0))
            surface.set_alpha(255)
        self._limpar_encerradas()
