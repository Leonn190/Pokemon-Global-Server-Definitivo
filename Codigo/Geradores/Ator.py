"""Ator básico do mundo, derivado de Entidade."""

from __future__ import annotations

import math
import os
from typing import Optional, Tuple

import pygame

from Codigo.Modulos.DesenhaAtor import DesenhaAtor
from Codigo.Geradores.Entidade import Entidade
from Codigo.Modulos.Colisor import Colisor

Vector2 = Tuple[float, float]


class Ator(Entidade):
    """Entidade básica com skin de player e desenho via ``DesenhaAtor``."""

    @staticmethod
    def carregar_skin(nome_skin: str):
        nome_base = str(nome_skin or "S1")
        if not nome_base.endswith(".png"):
            nome_base = f"{nome_base}.png"
        caminho = os.path.join("Recursos", "Visual", "Skins", "Liberadas", nome_base)
        try:
            return pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
            fallback.fill((190, 220, 255))
            return fallback

    def __init__(
        self,
        skin_surface=None,
        nome_skin: str = "S1",
        posicao: Vector2 = (0.0, 0.0),
        velocidade: Vector2 = (0.0, 0.0),
        raio_colisao: float = 0.35,
        raio_interacao: Optional[float] = None,
        escala_skin: float = 1.35,
    ) -> None:
        super().__init__(
            posicao=posicao,
            velocidade=velocidade,
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
        )
        if skin_surface is None:
            skin_surface = self.carregar_skin(nome_skin)
        self.Skin = skin_surface
        self.Desenhador = DesenhaAtor(self.Skin, escala=escala_skin)

        self.AnguloOlhar = 0.0
        self.Nome = "Player"
        self._duracao_tapa = 0.16
        self._tempo_tapa = 0.0
        self._raio_mao_colisao = max(0.18, raio_colisao * 0.65)
        self.ColisorMao = Colisor(
            x=self.Posicao[0],
            y=self.Posicao[1],
            raio_colisao=self._raio_mao_colisao,
            raio_interacao=self._raio_mao_colisao,
            ativo=False,
        )

    def set_skin(self, skin_surface) -> None:
        self.Skin = skin_surface
        self.Desenhador.set_skin(skin_surface)

    def definir_angulo_olhar(self, angulo_graus: float) -> None:
        self.AnguloOlhar = float(angulo_graus)

    def iniciar_tapa(self) -> None:
        self._tempo_tapa = self._duracao_tapa

    def esta_tapando(self) -> bool:
        return self._tempo_tapa > 0.0

    def Tapar(self) -> None:
        """Alias em PT para compatibilidade."""
        self.iniciar_tapa()

    def atualizar(self, dt: float) -> None:
        if self._tempo_tapa > 0.0:
            self._tempo_tapa = max(0.0, self._tempo_tapa - max(0.0, float(dt)))

    def _progresso_tapa(self) -> float:
        if self._tempo_tapa <= 0.0:
            return 0.0
        return 1.0 - (self._tempo_tapa / self._duracao_tapa)

    def _alcance_tapa_px(self) -> float:
        if self._tempo_tapa <= 0.0:
            return 0.0

        progresso = self._progresso_tapa()
        fase = 1.0 - abs(1.0 - (progresso * 2.0))
        return max(0.0, fase) * 0.55

    def desenhar(self, tela, mouse_pos=None, posicao_tela=None, respiracao_tempo=0.0) -> None:
        centro = self.Posicao if posicao_tela is None else posicao_tela
        dados_mao = self.Desenhador.desenhar(
            tela,
            centro,
            mouse_pos=mouse_pos,
            angulo_graus=self.AnguloOlhar,
            alcance_tapa=self._alcance_tapa_px(),
            progresso_tapa=self._progresso_tapa(),
            respiracao_tempo=respiracao_tempo,
        )

        if self._tempo_tapa > 0.0:
            mx, my = dados_mao["mao_tapa"]
            self.ColisorMao.mover_para(mx, my)
            self.ColisorMao.ativo = True
        else:
            self.ColisorMao.mover_para(self.Posicao[0], self.Posicao[1])
            self.ColisorMao.ativo = False

    def atualizar_colisor_mao_mundo(self) -> None:
        rad = math.radians(self.AnguloOlhar)
        frente_x = math.cos(rad)
        frente_y = -math.sin(rad)
        alcance = self._alcance_tapa_px()
        self.ColisorMao.mover_para(
            self.Posicao[0] + frente_x * alcance,
            self.Posicao[1] + frente_y * alcance,
        )
        self.ColisorMao.ativo = self._tempo_tapa > 0.0
