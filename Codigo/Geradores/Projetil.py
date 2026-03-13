"""Projétil visual client-heavy: sem stream contínuo do servidor."""

from __future__ import annotations

import math
from typing import Dict

import pygame

from Codigo.Modulos.Colisor import Colisor
from Codigo.Geradores.ItemInventario import ItemInventario


class Projetil:
    _cache_rotacao = {}

    def __init__(self, snapshot: Dict[str, object]):
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else (0.0, 0.0)
        self.Id = int(snapshot.get("id", 0) or 0)
        self.id_objeto = self.Id
        self.Posicao = (float(pos[0]), float(pos[1]))
        self.Colisor = Colisor(
            x=self.Posicao[0],
            y=self.Posicao[1],
            raio_colisao=max(0.08, float(snapshot.get("raio_colisao", 0.16) or 0.16)),
            raio_interacao=max(0.08, float(snapshot.get("raio_colisao", 0.16) or 0.16)),
        )
        self.TipoProjetil = "item"
        self.Subtipo = ""
        self.ItemBaseId = ""
        self.ItemNome = ""
        self.DonoId = 0
        self.TokenArremesso = ""
        self.Direcao = (1.0, 0.0)
        self.VelocidadeEscalar = 7.0
        self.AlcanceMaximo = 7.0
        self.DistanciaPercorrida = 0.0
        self.RotacaoVisual = 0.0
        self.Terminado = False
        self.Colidiu = False
        self.PreditoLocal = False
        self.TempoVida = 0.0
        self._fade_total = 0.0
        self._fade_restante = 0.0
        self._parado = False
        self._alpha = 255
        self.aplicar_snapshot(snapshot)

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else None
        if pos is not None:
            self.definir_posicao(float(pos[0]), float(pos[1]))
        self.TipoProjetil = str(snapshot.get("tipo_projetil") or estado.get("tipo_projetil") or self.TipoProjetil)
        self.Subtipo = str(snapshot.get("subtipo") or snapshot.get("nome_item") or estado.get("subtipo") or self.Subtipo)
        self.ItemBaseId = str(snapshot.get("item_base_id") or estado.get("item_base_id") or self.ItemBaseId)
        self.ItemNome = str(snapshot.get("item_nome") or snapshot.get("nome_item") or estado.get("item_nome") or estado.get("nome_item") or self.ItemNome or self.Subtipo or self.TipoProjetil)
        self.DonoId = int(snapshot.get("dono_id", estado.get("dono_id", self.DonoId)) or 0)
        self.TokenArremesso = str(snapshot.get("token_arremesso") or estado.get("token_arremesso") or self.TokenArremesso)
        direcao = estado.get("direcao") if isinstance(estado.get("direcao"), (list, tuple)) else snapshot.get("direcao")
        if isinstance(direcao, (list, tuple)) and len(direcao) == 2:
            dx, dy = float(direcao[0]), float(direcao[1])
            n = math.hypot(dx, dy) or 1.0
            self.Direcao = (dx / n, dy / n)
        self.VelocidadeEscalar = max(0.1, float(estado.get("velocidade", snapshot.get("velocidade", self.VelocidadeEscalar)) or self.VelocidadeEscalar))
        self.AlcanceMaximo = max(0.1, float(estado.get("alcance", snapshot.get("alcance", self.AlcanceMaximo)) or self.AlcanceMaximo))
        self.PreditoLocal = bool(estado.get("predito_local", snapshot.get("predito_local", self.PreditoLocal)))

    def encerrar_imediato(self) -> None:
        self.Terminado = True
        self.Colidiu = True
        self._fade_total = 0.0
        self._fade_restante = 0.0

    def encerrar_com_fade(self, tempo_s: float = 0.5) -> None:
        self.Colidiu = True
        self._parado = True
        self._fade_total = max(0.05, float(tempo_s))
        self._fade_restante = self._fade_total

    def deve_remover(self) -> bool:
        return self.Terminado and self._fade_restante <= 0.0

    def atualizar_visual(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        self.TempoVida += dt
        if self.Terminado and self._fade_restante <= 0.0:
            return

        if not self._parado and not self.Terminado:
            passo = self.VelocidadeEscalar * dt
            self.definir_posicao(self.Posicao[0] + self.Direcao[0] * passo, self.Posicao[1] + self.Direcao[1] * passo)
            self.DistanciaPercorrida += passo
            if self.DistanciaPercorrida >= self.AlcanceMaximo:
                self.encerrar_com_fade(0.5)

        if self._fade_restante > 0.0:
            self._fade_restante = max(0.0, self._fade_restante - dt)
            k = (self._fade_restante / self._fade_total) if self._fade_total > 1e-6 else 0.0
            self._alpha = max(0, min(255, int(255 * k)))
            if self._fade_restante <= 0.0:
                self.Terminado = True
                self._alpha = 0

        self.RotacaoVisual = (self.RotacaoVisual + 560.0 * dt) % 360.0

    def desenhar(self, tela, camera) -> None:
        if self.Terminado and self._alpha <= 0:
            return
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        item = {"Nome": self.ItemNome or self.Subtipo or self.TipoProjetil, "Code": self.ItemBaseId}
        base = ItemInventario.surface_item(item, lado_px=max(14, int(getattr(camera, "TilePx", 50) * 0.55)))
        if base is None:
            surf = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 180, 90, self._alpha), (6, 6), 5)
            tela.blit(surf, surf.get_rect(center=(int(cx), int(cy))))
            return
        chave = (id(base), int(self.RotacaoVisual) % 360)
        rot = self._cache_rotacao.get(chave)
        if rot is None:
            rot = pygame.transform.rotate(base, self.RotacaoVisual)
            self._cache_rotacao[chave] = rot
            if len(self._cache_rotacao) > 720:
                self._cache_rotacao.clear()
        sprite = rot.copy()
        if self._alpha < 255:
            sprite.set_alpha(self._alpha)
        tela.blit(sprite, sprite.get_rect(center=(int(cx), int(cy))))
