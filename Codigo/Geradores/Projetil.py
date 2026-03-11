"""Projétil serializável com suporte a predição local e reconciliação autoritativa."""

from __future__ import annotations

import math
from typing import Dict

import pygame

from Codigo.Geradores.Entidade import Entidade
from Codigo.Geradores.Itens.ItemInventario import ItemInventario


class Projetil(Entidade):
    _cache_rotacao = {}

    def __init__(self, snapshot: Dict[str, object]):
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else (0.0, 0.0)
        super().__init__(
            posicao=(float(pos[0]), float(pos[1])),
            raio_colisao=max(0.08, float(snapshot.get("raio_colisao", 0.16) or 0.16)),
            id_objeto=int(snapshot.get("id", 0) or 0),
        )
        self.TipoProjetil = "item"
        self.Subtipo = ""
        self.ItemBaseId = ""
        self.DonoId = 0
        self.PosicaoInicial = tuple(self.Posicao)
        self.Direcao = (1.0, 0.0)
        self.VelocidadeEscalar = 10.0
        self.AlcanceMaximo = 6.0
        self.DistanciaPercorrida = 0.0
        self.TempoVida = 0.0
        self.RotacaoVisual = 0.0
        self.Ativo = True
        self.Terminado = False
        self.Colidiu = False
        self.PreditoLocal = False
        self.TokenArremesso = ""
        self.Autoritativo = False
        self.Estado = {}
        self.AguardandoConfirmacaoColisao = False
        self.ColisaoCandidata = None
        self.ColisaoConfirmada = False
        self.DistanciaConferenciaInicial = 4.0
        self.ConferenciaFinalEnviada = False
        self.ConferenciaResultadoRecebido = False
        self.TempoAposTermino = 0.0
        self.ModoMovimento = "indo"
        self._offset_correcao = [0.0, 0.0]
        self._tempo_correcao = 0.0
        self.aplicar_snapshot(snapshot)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else None
        if pos is not None:
            nx, ny = float(pos[0]), float(pos[1])
            px, py = self.Posicao
            if self.PreditoLocal or self.Autoritativo:
                self._offset_correcao = [px - nx, py - ny]
                self._tempo_correcao = 0.12
            else:
                self._offset_correcao = [0.0, 0.0]
                self._tempo_correcao = 0.0
            self.definir_posicao(nx, ny)

        self.TipoProjetil = str(snapshot.get("tipo_projetil") or estado.get("tipo_projetil") or self.TipoProjetil)
        self.Subtipo = str(snapshot.get("subtipo") or snapshot.get("nome_item") or estado.get("subtipo") or self.Subtipo)
        self.ItemBaseId = str(snapshot.get("item_base_id") or estado.get("item_base_id") or self.ItemBaseId)
        self.DonoId = int(snapshot.get("dono_id", estado.get("dono_id", self.DonoId)) or 0)
        self.TokenArremesso = str(snapshot.get("token_arremesso") or estado.get("token_arremesso") or self.TokenArremesso)

        p0 = snapshot.get("posicao_inicial") or estado.get("posicao_inicial") or self.PosicaoInicial
        if isinstance(p0, (list, tuple)) and len(p0) == 2:
            self.PosicaoInicial = (float(p0[0]), float(p0[1]))

        direcao = snapshot.get("direcao") if isinstance(snapshot.get("direcao"), (list, tuple)) else estado.get("direcao")
        if isinstance(direcao, (list, tuple)) and len(direcao) == 2:
            dx, dy = float(direcao[0]), float(direcao[1])
            n = math.hypot(dx, dy)
            if n > 1e-6:
                self.Direcao = (dx / n, dy / n)

        self.VelocidadeEscalar = max(0.1, float(snapshot.get("velocidade", estado.get("velocidade", self.VelocidadeEscalar)) or self.VelocidadeEscalar))
        self.AlcanceMaximo = max(0.1, float(snapshot.get("alcance", estado.get("alcance", self.AlcanceMaximo)) or self.AlcanceMaximo))
        self.DistanciaPercorrida = max(0.0, float(snapshot.get("distancia", estado.get("distancia", self.DistanciaPercorrida)) or self.DistanciaPercorrida))
        self.TempoVida = max(0.0, float(snapshot.get("tempo_vida", estado.get("tempo_vida", self.TempoVida)) or self.TempoVida))
        self.RotacaoVisual = float(snapshot.get("rotacao", estado.get("rotacao", self.RotacaoVisual)) or self.RotacaoVisual)

        self.PreditoLocal = bool(snapshot.get("predito_local", estado.get("predito_local", self.PreditoLocal)))
        self.Autoritativo = bool(snapshot.get("autoritativo", estado.get("autoritativo", self.Autoritativo)))
        self.Colidiu = bool(snapshot.get("colidiu", estado.get("colidiu", self.Colidiu)))
        self.Terminado = bool(snapshot.get("terminado", estado.get("terminado", self.Terminado)))
        self.Ativo = not self.Terminado
        self.ColisaoConfirmada = self.ColisaoConfirmada or self.Colidiu or self.Terminado
        self.DistanciaConferenciaInicial = max(0.8, min(4.0, float(snapshot.get("distancia_conferencia_inicial", estado.get("distancia_conferencia_inicial", self.DistanciaConferenciaInicial)) or self.DistanciaConferenciaInicial)))
        self.ModoMovimento = str(snapshot.get("modo_movimento") or estado.get("modo_movimento") or self.ModoMovimento or "indo")
        self.Estado = dict(estado)

    def atualizar_visual(self, dt: float) -> None:
        if self.Terminado:
            self.TempoAposTermino += max(0.0, float(dt))
            return
        dt = max(0.0, float(dt))
        self.TempoVida += dt

        if self.PreditoLocal or self.Autoritativo:
            passo = self.VelocidadeEscalar * dt
            self.mover(self.Direcao[0] * passo, self.Direcao[1] * passo)
            self.DistanciaPercorrida += passo
            if self.DistanciaPercorrida >= self.AlcanceMaximo:
                self.Terminado = True
                self.Ativo = False

        if self._tempo_correcao > 0.0:
            fator = min(1.0, dt / self._tempo_correcao) if self._tempo_correcao > 1e-6 else 1.0
            self.mover(self._offset_correcao[0] * fator, self._offset_correcao[1] * fator)
            self._offset_correcao[0] *= (1.0 - fator)
            self._offset_correcao[1] *= (1.0 - fator)
            self._tempo_correcao = max(0.0, self._tempo_correcao - dt)

        if self.ModoMovimento == "indo":
            self.RotacaoVisual = (self.RotacaoVisual + 560.0 * dt) % 360.0

    def serializar_estado(self) -> Dict[str, object]:
        return {
            "tipo_projetil": self.TipoProjetil,
            "subtipo": self.Subtipo,
            "item_base_id": self.ItemBaseId,
            "dono_id": self.DonoId,
            "token_arremesso": self.TokenArremesso,
            "direcao": [self.Direcao[0], self.Direcao[1]],
            "velocidade": self.VelocidadeEscalar,
            "alcance": self.AlcanceMaximo,
            "distancia": self.DistanciaPercorrida,
            "tempo_vida": self.TempoVida,
            "rotacao": self.RotacaoVisual,
            "predito_local": self.PreditoLocal,
            "autoritativo": self.Autoritativo,
            "colidiu": self.Colidiu,
            "terminado": self.Terminado,
            "distancia_conferencia_inicial": self.DistanciaConferenciaInicial,
            "modo_movimento": self.ModoMovimento,
        }

    def desenhar(self, tela, camera) -> None:
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        item = {"Nome": self.Subtipo or self.TipoProjetil, "Code": self.ItemBaseId}
        base = ItemInventario.surface_item(item, lado_px=max(14, int(getattr(camera, "TilePx", 50) * 0.55)))
        if base is None:
            pygame.draw.circle(tela, (255, 180, 90), (int(cx), int(cy)), max(3, int(camera.TilePx * 0.16)))
            return
        chave = (id(base), int(self.RotacaoVisual) % 360)
        rot = self._cache_rotacao.get(chave)
        if rot is None:
            rot = pygame.transform.rotate(base, self.RotacaoVisual)
            self._cache_rotacao[chave] = rot
            if len(self._cache_rotacao) > 720:
                self._cache_rotacao.clear()
        tela.blit(rot, rot.get_rect(center=(int(cx), int(cy))))
