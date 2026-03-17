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

        self.AreaReal = (
            pygame.Rect(0, 0, self.rect.width, self.rect.height)
            if area_real is None
            else pygame.Rect(area_real)
        )

        self.ScrollX = 0
        self.ScrollY = 0
        self.VelocidadeScroll = max(8, int(velocidade_scroll))

        self._surface_conteudo = None
        self._surface_viewport = None
        self._mascara_viewport = None
        self._mascara_chave = None

        self._ultimo_scroll = (None, None)
        self._conteudo_sujo = True
        self._viewport_suja = True

        self._clamp_scroll()
        self._garantir_surfaces()

    def marcar_sujo(self):
        self._conteudo_sujo = True
        self._viewport_suja = True

    def definir_area_real(self, largura, altura):
        nova_largura = max(self.rect.width, int(largura))
        nova_altura = max(self.rect.height, int(altura))

        if self.AreaReal.width != nova_largura or self.AreaReal.height != nova_altura:
            self.AreaReal.width = nova_largura
            self.AreaReal.height = nova_altura
            self._recriar_surface_conteudo()
            self._conteudo_sujo = True
            self._viewport_suja = True

        self._clamp_scroll()

    def obter_area_visivel_no_conteudo(self):
        return pygame.Rect(self.ScrollX, self.ScrollY, self.rect.width, self.rect.height)

    def _clamp_scroll(self):
        max_x = max(0, self.AreaReal.width - self.rect.width)
        max_y = max(0, self.AreaReal.height - self.rect.height)

        novo_x = max(0, min(int(self.ScrollX), max_x))
        novo_y = max(0, min(int(self.ScrollY), max_y))

        if novo_x != self.ScrollX or novo_y != self.ScrollY:
            self.ScrollX = novo_x
            self.ScrollY = novo_y
            self._viewport_suja = True

    def _recriar_surface_conteudo(self):
        self._surface_conteudo = pygame.Surface(
            (self.AreaReal.width, self.AreaReal.height),
            pygame.SRCALPHA
        )

    def _recriar_surface_viewport(self):
        self._surface_viewport = pygame.Surface(
            (self.rect.width, self.rect.height),
            pygame.SRCALPHA
        )
        self._mascara_viewport = None
        self._mascara_chave = None

    def _garantir_surfaces(self):
        if (
            self._surface_conteudo is None
            or self._surface_conteudo.get_width() != self.AreaReal.width
            or self._surface_conteudo.get_height() != self.AreaReal.height
        ):
            self._recriar_surface_conteudo()
            self._conteudo_sujo = True
            self._viewport_suja = True

        if (
            self._surface_viewport is None
            or self._surface_viewport.get_width() != self.rect.width
            or self._surface_viewport.get_height() != self.rect.height
        ):
            self._recriar_surface_viewport()
            self._viewport_suja = True

    def _processar_scroll(self, eventos):
        if not self.rect.collidepoint(pygame.mouse.get_pos()):
            return False

        scrollou = False

        for evento in eventos:
            if evento.type != pygame.MOUSEWHEEL:
                continue

            scrollou = True

            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self.ScrollX -= evento.y * self.VelocidadeScroll
            else:
                self.ScrollY -= evento.y * self.VelocidadeScroll

        if scrollou:
            self._clamp_scroll()

        return scrollou

    def _aplicar_mascara_raio(self, surface):
        if self.Raio <= 0:
            return

        chave = (surface.get_width(), surface.get_height(), self.Raio)

        if self._mascara_chave != chave:
            self._mascara_viewport = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            self._mascara_viewport.fill((0, 0, 0, 0))
            pygame.draw.rect(
                self._mascara_viewport,
                (255, 255, 255, 255),
                self._mascara_viewport.get_rect(),
                border_radius=self.Raio
            )
            self._mascara_chave = chave

        surface.blit(self._mascara_viewport, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def render(self, tela, eventos, dt, jogo=None):
        if not self.Visivel:
            return

        self._garantir_surfaces()

        scroll_antes = (self.ScrollX, self.ScrollY)
        houve_scroll = self._processar_scroll(eventos)
        scroll_depois = (self.ScrollX, self.ScrollY)

        if scroll_antes != scroll_depois:
            self._viewport_suja = True

        mouse_global = pygame.mouse.get_pos()
        mouse_local = (
            mouse_global[0] - self.rect.x + self.ScrollX,
            mouse_global[1] - self.rect.y + self.ScrollY,
        )

        # Mantém compatibilidade com o sistema atual
        self.update(
            eventos,
            dt,
            jogo=jogo,
            tela_painel=self._surface_conteudo,
            mouse_local=mouse_local
        )

        # Só redesenha o conteúdo inteiro quando ele estiver marcado como sujo
        if self._conteudo_sujo:
            self._surface_conteudo.fill((0, 0, 0, 0))
            self.draw(self._surface_conteudo)
            self._conteudo_sujo = False
            self._viewport_suja = True

        # Só recompõe a viewport quando scroll/tamanho/conteúdo mudar
        if self._viewport_suja:
            self._surface_viewport.fill((0, 0, 0, 0))
            self._surface_viewport.blit(
                self._surface_conteudo,
                (-self.ScrollX, -self.ScrollY)
            )
            self._aplicar_mascara_raio(self._surface_viewport)
            self._viewport_suja = False

        tela.blit(self._surface_viewport, self.rect.topleft)

        if self.Borda > 0:
            pygame.draw.rect(
                tela,
                self.CorBorda,
                self.rect,
                self.Borda,
                border_radius=self.Raio
            )