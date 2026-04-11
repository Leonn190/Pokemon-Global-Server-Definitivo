from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

import pygame

from Codigo.Paineis.FichaPokemonBatalha import FichaPokemonBatalha
from Codigo.Paineis.PainelJogada import PainelJogada
from Codigo.ModulosBatalha.ControladorFluxos import ControladorFluxos
from Codigo.Prefabs.Botao import Botao


class ElementosHudBatalha:
    def __init__(self, controlador_batalha=None, camera=None, ao_fugir: Optional[Callable[[], None]] = None) -> None:
        self._ao_fugir = ao_fugir
        self._controlador = controlador_batalha
        self._camera = camera
        self._botao_fugir: Optional[Botao] = None
        self._icone_fugir: Optional[pygame.Surface] = None
        self._cache_tamanho: Optional[tuple[int, int]] = None
        self._fuga_pressao = 0.0
        self._fuga_alvo = 8.0
        self._fuga_taxa_clique = 1.65
        self._fuga_taxa_decay = 0.08
        self._fuga_disparada = False
        self._ficha = FichaPokemonBatalha()
        self._fluxos = ControladorFluxos(controlador_batalha, camera) if controlador_batalha is not None and camera is not None else None
        self._painel_jogada = PainelJogada()
        self._anim_ficha = 0.0
        self._pokemon_exibido = None
        self._botao_preparar: Optional[Botao] = None
        self._botao_pronto: Optional[Botao] = None

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
        bw = max(138, int(lado * 2.2))
        bh = max(44, int(lado * 0.82))
        bx = w - bw - margem
        by = h - (bh * 2 + 10 + margem)
        estilo_acao = {
            "radius": 10,
            "border_width": 2,
            "bg": (24, 36, 52),
            "bg_hover": (36, 52, 76),
            "bg_pressed": (18, 28, 40),
            "border": (153, 185, 224),
            "border_hover": (218, 236, 255),
            "text_style": {"size": 24, "outline_thickness": 2, "outline_color": (8, 12, 20)},
        }
        self._botao_preparar = Botao(pygame.Rect(bx, by, bw, bh), "Preparar", execute=lambda _jogo, _botao: self._preparar_jogada(), style=estilo_acao)
        self._botao_pronto = Botao(pygame.Rect(bx, by + bh + 10, bw, bh), "Pronto", execute=lambda _jogo, _botao: self._confirmar_jogadas(), style=estilo_acao)

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

    def _processar_selecao(self, eventos: List[pygame.event.Event], rects_bloqueados: List[pygame.Rect]):
        if self._controlador is None or self._camera is None or self._fluxos is not None:
            return
        for ev in eventos or []:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if any(rect.collidepoint(ev.pos) for rect in rects_bloqueados):
                    break
                self._controlador.selecionar_por_mouse(ev.pos, self._camera)
                break

    def _preparar_jogada(self) -> None:
        if self._fluxos is not None:
            self._fluxos.acao_principal(self._ficha)

    def _confirmar_jogadas(self) -> None:
        if self._fluxos is not None:
            self._fluxos.pronto()

    def _atualizar_animacao_ficha(self, dt: float):
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        if selecionado is not None:
            self._pokemon_exibido = selecionado
        alvo = 1.0 if selecionado is not None else 0.0
        vel = max(0.01, float(dt) * 8.0)
        self._anim_ficha += (alvo - self._anim_ficha) * min(1.0, vel)
        if self._anim_ficha <= 0.01 and selecionado is None:
            self._pokemon_exibido = None

    def desenhar(self, tela: pygame.Surface, eventos: List[pygame.event.Event], dt: float = 0.0) -> None:
        self._garantir_layout(tela)
        if self._controlador is not None and hasattr(self._controlador, "Jogador"):
            self._controlador.Jogador.Controle.processar_eventos(eventos or [], self._controlador, self._ficha, self._fluxos)
        self._atualizar_animacao_ficha(dt)
        self._atualizar_fuga(dt)

        if self._fluxos is not None:
            self._painel_jogada.sincronizar(self._fluxos.listar_jogadas(), self._fluxos.jogada_selecionada_id())
            self._painel_jogada.recalcular_layout(tela)
            self._painel_jogada.processar_eventos(eventos or [])
            self._fluxos.definir_hover_jogada(self._painel_jogada.jogada_hover())
            for comando in self._painel_jogada.coletar_comandos():
                if comando.get("acao") == "remover":
                    self._fluxos.remover_jogada(comando.get("id"))
                elif comando.get("acao") == "selecionar":
                    self._fluxos.selecionar_jogada(comando.get("id"))

        rects_hud = [
            self._ficha.rect,
            self._botao_preparar.rect if self._botao_preparar else pygame.Rect(0, 0, 0, 0),
            self._botao_pronto.rect if self._botao_pronto else pygame.Rect(0, 0, 0, 0),
            self._botao_fugir.rect if self._botao_fugir else pygame.Rect(0, 0, 0, 0),
        ]
        rects_hud.extend(self._painel_jogada.retangulos_interativos())
        if self._fluxos is not None:
            for ev in eventos or []:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not any(rect.collidepoint(ev.pos) for rect in rects_hud):
                    self._fluxos.selecionar_jogada(None)
                    break
        self._processar_selecao(eventos or [], rects_hud)

        if self._fluxos is not None:
            self._fluxos.atualizar_contexto(self._ficha.ataque_selecionado())
            self._fluxos.processar_eventos(eventos or [], self._ficha, rects_hud)
        selecionado_atual = getattr(self._controlador, "PokemonSelecionado", None)
        if selecionado_atual is None or str(getattr(selecionado_atual, "Lado", "")) != "jogador":
            self._ficha.limpar_ataque_selecionado()
        if self._botao_fugir is not None:
            self._botao_fugir.render(tela, eventos or [], dt, None)
            if self._icone_fugir is not None:
                rect = self._icone_fugir.get_rect(center=self._botao_fugir.rect.center)
                tela.blit(self._icone_fugir, rect)
        if self._botao_preparar is not None:
            if self._fluxos is not None:
                rotulo, habilitado = self._fluxos.estado_botao_preparar(self._ficha)
                self._botao_preparar.set_text(rotulo)
                self._botao_preparar.set_habilitado(habilitado)
            self._botao_preparar.render(tela, eventos or [], dt, None)
        if self._botao_pronto is not None:
            self._botao_pronto.render(tela, eventos or [], dt, None)
        if self._fluxos is not None and self._pokemon_exibido is not None:
            custo, pode = self._fluxos.previsao_consumo(self._pokemon_exibido, self._ficha.ataque_selecionado())
            self._ficha.atualizar_previsao(custo, pode)
        else:
            self._ficha.atualizar_previsao(0.0, True)
        if self._fluxos is not None:
            self._fluxos.desenhar(tela, dt)
        self._painel_jogada.desenhar(tela, dt)
        self._ficha.render(tela, self._pokemon_exibido, self._anim_ficha, eventos or [], dt)
        self._desenhar_overlay_fuga(tela)
