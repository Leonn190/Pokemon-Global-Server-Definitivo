from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Paineis.FichaPokemonBatalha import FichaPokemonBatalha
from Codigo.Paineis.PainelAcoes import PainelAcoes
from Codigo.Paineis.VisualizadorLog import VisualizadorLog
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
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
            pygame.Rect(20, 84, 64, 64),
            "",
            execute=lambda _jogo, _botao: self.controlador.enviar_jogada_pronta(),
            style={"radius": 12, "text_style": {"size": 14}},
        )
        self.botao_fugir = Botao(
            pygame.Rect(170, 84, 64, 64),
            "",
            execute=lambda _jogo, _botao: self._fugir_local(),
            style={"radius": 12, "bg": (74, 82, 108), "bg_hover": (92, 104, 136), "bg_pressed": (58, 64, 88), "text_style": {"size": 14}},
        )
        self._icone_fuga = self._carregar_icone("Fugir")
        self._icone_pronto = self._carregar_icone("Pronto")
        self._ficha_t_visivel = 0.0
        self._ficha_alvo_visivel = 0.0
        self.velocidade_animacao_ficha = 8.0

        self._retangulos_fixos: list[pygame.Rect] = []

    def _carregar_icone(self, nome: str):
        base = Path("Recursos") / "Visual" / "Icones" / "Diversos"
        nomes = [nome, nome.lower(), nome.upper(), nome.capitalize(), "Fuga" if nome.lower() == "fugir" else nome]
        exts = (".png", ".webp", ".jpg", ".jpeg")
        for nome_base in nomes:
            for ext in exts:
                caminho = base / f"{nome_base}{ext}"
                if caminho.exists():
                    try:
                        return pygame.image.load(str(caminho)).convert_alpha()
                    except Exception:
                        return None
        return None

    def _fugir_local(self):
        self.controlador.logs_locais.append({"rodada": self.controlador.rodada_atual, "texto": "Fuga solicitada (visual)."})
        self.controlador.iniciar_fuga()

    def atualizar(self, dt: float, eventos):
        self._ficha_alvo_visivel = 1.0 if self.controlador.pokemon_selecionado is not None else 0.0
        passo = min(1.0, max(0.0, float(dt)) * self.velocidade_animacao_ficha)
        self._ficha_t_visivel += (self._ficha_alvo_visivel - self._ficha_t_visivel) * passo
        if abs(self._ficha_t_visivel - self._ficha_alvo_visivel) < 0.001:
            self._ficha_t_visivel = self._ficha_alvo_visivel
        self.ficha.definir_controle_inimigo(self.controlador.modo_teste)
        montador = getattr(self.controlador, "montador_jogadas", None)
        jogadas = list(getattr(montador, "acoes_preparadas", []) or [])
        selecionado_id = getattr(montador, "acao_selecionada_id", None)
        self.painel_acoes.sincronizar(jogadas, selecionado_id)
        self.painel_acoes.processar_eventos(eventos)
        for cmd in self.painel_acoes.coletar_comandos():
            acao = str(cmd.get("acao") or "")
            if acao == "remover" and montador is not None:
                montador.remover_acao(cmd.get("id"))
                self.controlador.atualizar_previsoes_hud()

    def consumiu_clique(self, pos_mouse):
        if self._ficha_t_visivel > 0.05 and self.ficha.contem_ponto(pos_mouse):
            return True
        for rect in self._retangulos_fixos:
            if rect.collidepoint(pos_mouse):
                return True
        for rect in self.visualizador.retangulos_interativos():
            if rect.collidepoint(pos_mouse):
                return True
        for rect in self.painel_acoes.retangulos_interativos():
            if rect.collidepoint(pos_mouse):
                return True
        return False

    def desenhar(self, tela: pygame.Surface, eventos, dt: float):
        w, h = tela.get_size()
        btn = max(52, min(76, int(h * 0.07)))
        margem = 18
        self.botao_fugir.base_rect = pygame.Rect(margem, h - btn - margem, btn, btn)
        self.botao_fugir.rect = pygame.Rect(self.botao_fugir.base_rect)
        self.botao_pronto.base_rect = pygame.Rect(w - btn - margem, h - btn - margem, btn, btn)
        self.botao_pronto.rect = pygame.Rect(self.botao_pronto.base_rect)

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
        if self._icone_fuga is not None:
            lado = self.botao_fugir.rect.height - 16
            icone = pygame.transform.smoothscale(self._icone_fuga, (lado, lado))
            tela.blit(icone, icone.get_rect(center=self.botao_fugir.rect.center))
        else:
            txt = Texto("Fugir", style={"size": 14, "align": "center", "outline": True, "outline_thickness": 2})
            txt.set_pos(self.botao_fugir.rect.center)
            txt.draw(tela)

        if self._icone_pronto is not None:
            lado = self.botao_pronto.rect.height - 16
            icone = pygame.transform.smoothscale(self._icone_pronto, (lado, lado))
            tela.blit(icone, icone.get_rect(center=self.botao_pronto.rect.center))
        else:
            txt = Texto("Pronto", style={"size": 14, "align": "center", "outline": True, "outline_thickness": 2})
            txt.set_pos(self.botao_pronto.rect.center)
            txt.draw(tela)

        self._retangulos_fixos = [pygame.Rect(self.botao_pronto.rect), pygame.Rect(self.botao_fugir.rect)]

        pokemon = self.controlador.pokemon_selecionado
        if pokemon is not None or self._ficha_t_visivel > 0.01:
            self.ficha.render(tela, pokemon, self._ficha_t_visivel, eventos, dt)
        if pokemon is not None:
            custo = float(getattr(pokemon, "CustoPrevistoPendente", 0.0) or 0.0)
            pode = bool(getattr(pokemon, "PodePagarPrevisao", True))
            self.ficha.atualizar_previsao(custo, pode)
            ataque = self.ficha.ataque_selecionado()
            if ataque is not None:
                estilo = str(ataque.get("Estilo") or ataque.get("estilo") or "").strip().lower()
                if estilo in {"passiva", "passivo"}:
                    self.ficha.limpar_ataque_selecionado()
                    ataque = None
            if ataque != self.controlador.ataque_selecionado:
                self.controlador.selecionar_ataque(ataque)
                if ataque is not None and self.controlador.montador_jogadas is not None and pokemon is not None:
                    self.controlador.montador_jogadas.iniciar_preparacao_ataque(pokemon, ataque)
                    if self.controlador.montador_jogadas.estado_montagem != "preparando_ataque":
                        self.controlador.limpar_ataque()
        else:
            self.ficha.limpar_ataque_selecionado()

        self.painel_acoes.desenhar(tela, dt)
        self.visualizador.desenhar(tela, eventos, dt)
