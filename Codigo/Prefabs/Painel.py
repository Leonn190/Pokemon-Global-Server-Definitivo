from __future__ import annotations

import pygame

from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class Painel:
    def __init__(self, rect, cor_fundo=(26, 30, 42, 230), cor_borda=(70, 84, 112), borda=2, raio=10):
        self.rect = pygame.Rect(rect)
        self.CorFundo = cor_fundo
        self.CorBorda = cor_borda
        self.Borda = int(max(0, borda))
        self.Raio = int(max(0, raio))
        self.AtualizacaoAtiva = True
        self.Visivel = True
        self.Componentes = []

    def ativar_update(self, ativo: bool):
        self.AtualizacaoAtiva = bool(ativo)

    def adicionar(self, componente):
        self.Componentes.append(componente)
        return componente

    def adicionar_texto(self, texto, pos=(0, 0), style=None):
        return self.adicionar(Texto(texto, pos=pos, style=style))

    def adicionar_botao(self, rect, texto, execute=None, style=None):
        return self.adicionar(Botao(rect, texto, execute=execute, style=style))

    def adicionar_barra(self, rect, **kwargs):
        return self.adicionar(Barra(rect, **kwargs))

    def update(self, eventos, dt, jogo=None, tela_painel=None, mouse_local=None):
        if not self.AtualizacaoAtiva:
            return
        for comp in self.Componentes:
            if hasattr(comp, "render") and callable(comp.render):
                comp.render(tela_painel, eventos, dt, jogo, mouse_pos=mouse_local)
            elif hasattr(comp, "atualizar") and callable(comp.atualizar):
                comp.atualizar(dt)
            elif hasattr(comp, "update") and callable(comp.update):
                comp.update(eventos, dt)

    def draw(self, tela_painel):
        pygame.draw.rect(tela_painel, self.CorFundo, tela_painel.get_rect(), border_radius=self.Raio)
        if self.Borda > 0:
            pygame.draw.rect(tela_painel, self.CorBorda, tela_painel.get_rect(), self.Borda, border_radius=self.Raio)

        for comp in self.Componentes:
            if hasattr(comp, "desenhar") and callable(comp.desenhar):
                comp.desenhar(tela_painel)
            elif hasattr(comp, "draw") and callable(comp.draw):
                comp.draw(tela_painel)

    def render(self, tela, eventos, dt, jogo=None):
        if not self.Visivel:
            return
        tela_painel = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.draw(tela_painel)
        mouse_global = pygame.mouse.get_pos()
        mouse_local = (mouse_global[0] - self.rect.x, mouse_global[1] - self.rect.y)
        self.update(eventos, dt, jogo=jogo, tela_painel=tela_painel, mouse_local=mouse_local)
        tela.blit(tela_painel, self.rect.topleft)


class PainelRolavel(Painel):
    def __init__(self, rect, area_real=None, velocidade_scroll=36, **kwargs):
        super().__init__(rect, **kwargs)
        self.AreaReal = pygame.Rect(0, 0, rect[2], rect[3]) if area_real is None else pygame.Rect(area_real)
        self.ScrollX = 0
        self.ScrollY = 0
        self.VelocidadeScroll = int(max(8, velocidade_scroll))

    def definir_area_real(self, largura, altura):
        self.AreaReal.width = max(self.rect.width, int(largura))
        self.AreaReal.height = max(self.rect.height, int(altura))
        self._clamp_scroll()

    def _clamp_scroll(self):
        max_x = max(0, self.AreaReal.width - self.rect.width)
        max_y = max(0, self.AreaReal.height - self.rect.height)
        self.ScrollX = max(0, min(max_x, int(self.ScrollX)))
        self.ScrollY = max(0, min(max_y, int(self.ScrollY)))

    def _processar_scroll(self, eventos):
        if not self.rect.collidepoint(pygame.mouse.get_pos()):
            return
        for evento in eventos:
            if evento.type != pygame.MOUSEWHEEL:
                continue
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self.ScrollX -= int(evento.y) * self.VelocidadeScroll
            else:
                self.ScrollY -= int(evento.y) * self.VelocidadeScroll
        self._clamp_scroll()

    def render(self, tela, eventos, dt, jogo=None):
        if not self.Visivel:
            return
        self._processar_scroll(eventos)
        tela_conteudo = pygame.Surface(self.AreaReal.size, pygame.SRCALPHA)
        self.draw(tela_conteudo)

        mouse_global = pygame.mouse.get_pos()
        mouse_local = (
            mouse_global[0] - self.rect.x + self.ScrollX,
            mouse_global[1] - self.rect.y + self.ScrollY,
        )
        self.update(eventos, dt, jogo=jogo, tela_painel=tela_conteudo, mouse_local=mouse_local)

        clip = pygame.Rect(self.ScrollX, self.ScrollY, self.rect.width, self.rect.height)
        tela.blit(tela_conteudo, self.rect.topleft, area=clip)
        if self.Borda > 0:
            pygame.draw.rect(tela, self.CorBorda, self.rect, self.Borda, border_radius=self.Raio)
