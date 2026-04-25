from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Paineis.FichaPokemonBatalha import FichaPokemonBatalha
from Codigo.Paineis.PainelAcoes import PainelAcoes
from Codigo.Paineis.VisualizadorLog import VisualizadorLog
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao, BotaoAlavanca
from Codigo.Prefabs.Texto import Texto


class ElementosHudBatalha:
    def __init__(self, controlador) -> None:
        self.controlador = controlador
        self.ficha = FichaPokemonBatalha()
        self.painel_acoes = PainelAcoes()
        self.visualizador = VisualizadorLog(controlador=controlador)

        self._txt_rodada = Texto(
            "Rodada 1",
            style={"size": 26, "align": "topleft", "color": (244, 248, 255), "outline": True, "outline_thickness": 2, "outline_color": (6, 10, 18)},
        )

        self.barra_timer = Barra((20, 58, 300, 18), texto="", valor=0, minimo=0, maximo=1, mostrar_rotulo=False)
        self.barra_timer.configurar(cor_fundo=(22, 28, 42), cor_borda=(114, 145, 198), cor_preenchimento=(72, 184, 255), border_radius=8)

        self.botao_pronto = Botao(
            pygame.Rect(20, 84, 140, 42),
            "Pronto",
            execute=lambda _jogo, _botao: self.controlador.passar_rodada_local(),
            style={"text_style": {"size": 20}},
        )
        self.botao_fugir = Botao(
            pygame.Rect(170, 84, 140, 42),
            "Fugir",
            execute=lambda _jogo, _botao: self._fugir_local(),
            style={"bg": (74, 82, 108), "bg_hover": (92, 104, 136), "bg_pressed": (58, 64, 88), "text_style": {"size": 20}},
        )
        self._icone_fuga = self._carregar_icone_fuga()

        self.botao_modo_teste = BotaoAlavanca(
            pygame.Rect(320, 84, 220, 42),
            "Modo teste",
            estado_inicial=False,
            execute=lambda _jogo, estado, _botao: self._alternar_modo_teste(estado),
            style={"text_style": {"size": 18}},
        )

        self._retangulos_fixos: list[pygame.Rect] = []

    def _carregar_icone_fuga(self):
        base = Path("Recursos") / "Visual" / "Icones" / "Diversos"
        for nome in ("Fuga.png", "fuga.png", "Fuga.webp", "fuga.webp"):
            caminho = base / nome
            if caminho.exists():
                try:
                    return pygame.image.load(str(caminho)).convert_alpha()
                except Exception:
                    return None
        return None

    def _fugir_local(self):
        self.controlador.logs_locais.append({"rodada": self.controlador.rodada_atual, "texto": "Tentativa de fuga (visual)."})

    def _alternar_modo_teste(self, estado: bool):
        self.controlador.modo_teste = bool(estado)
        self.ficha.definir_controle_inimigo(self.controlador.modo_teste)

    def atualizar(self, dt: float, eventos):
        _ = dt
        self.ficha.definir_controle_inimigo(self.controlador.modo_teste)
        self.painel_acoes.sincronizar([], None)
        self.painel_acoes.processar_eventos(eventos)

    def consumiu_clique(self, pos_mouse):
        if self.ficha.contem_ponto(pos_mouse):
            return True
        for rect in self._retangulos_fixos:
            if rect.collidepoint(pos_mouse):
                return True
        for rect in self.visualizador.retangulos_interativos():
            if rect.collidepoint(pos_mouse):
                return True
        return False

    def desenhar(self, tela: pygame.Surface, eventos, dt: float):
        self._txt_rodada.set_text(f"Rodada {self.controlador.rodada_atual}")
        self._txt_rodada.set_pos((20, 22))
        self._txt_rodada.draw(tela)

        if self.controlador.timer_rodada_max > 0:
            t = max(0.0, min(1.0, self.controlador.timer_rodada / self.controlador.timer_rodada_max))
        else:
            t = 0.0
        self.barra_timer.set_valor(t, animar=False)
        self.barra_timer.render(tela, eventos, dt)

        self.botao_pronto.render(tela, eventos, dt, None)
        self.botao_fugir.render(tela, eventos, dt, None)
        self.botao_modo_teste.render(tela, eventos, dt, None)

        if self._icone_fuga is not None:
            lado = self.botao_fugir.rect.height - 12
            icone = pygame.transform.smoothscale(self._icone_fuga, (lado, lado))
            tela.blit(icone, icone.get_rect(midleft=(self.botao_fugir.rect.x + 10, self.botao_fugir.rect.centery)))

        self._retangulos_fixos = [pygame.Rect(self.botao_pronto.rect), pygame.Rect(self.botao_fugir.rect), pygame.Rect(self.botao_modo_teste.rect)]

        pokemon = self.controlador.pokemon_selecionado
        if pokemon is not None:
            self.ficha.render(tela, pokemon, 1.0, eventos, dt)
            ataque = self.ficha.ataque_selecionado()
            if ataque is not None:
                estilo = str(ataque.get("Estilo") or ataque.get("estilo") or "").strip().lower()
                if estilo in {"passiva", "passivo"}:
                    self.ficha.limpar_ataque_selecionado()
                    ataque = None
            if ataque != self.controlador.ataque_selecionado:
                self.controlador.selecionar_ataque(ataque)
        else:
            self.ficha.limpar_ataque_selecionado()

        self.painel_acoes.desenhar(tela, dt)
        self.visualizador.desenhar(tela, eventos, dt)
