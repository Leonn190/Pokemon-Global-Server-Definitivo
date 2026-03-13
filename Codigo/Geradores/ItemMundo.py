from __future__ import annotations

import math
from typing import Dict, Tuple

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario

Vector2 = Tuple[float, float]


class ItemMundo:
    def __init__(self, snapshot: Dict[str, object]):
        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else (0.0, 0.0)
        self.Id = int(snapshot.get("id", 0) or 0)
        self.id_objeto = self.Id
        self.Posicao = (float(pos[0]), float(pos[1]))

        self.ItemNome = ""
        self.ItemBaseId = ""
        self.Quantidade = 1
        self.DonoId = 0
        self.TokenDrop = ""

        self.PosicaoInicial = self.Posicao
        self.PosicaoFinal = self.Posicao
        self.Velocidade = 3.0
        self.Voando = False

        self.TempoRespirar = 0.0
        self.EscalaRespirar = 1.0
        self._despawn_local = False

        self.aplicar_snapshot(snapshot)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}

        pos = snapshot.get("posicao") if isinstance(snapshot.get("posicao"), (list, tuple)) else None
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            self.Posicao = (float(pos[0]), float(pos[1]))

        self.ItemNome = str(snapshot.get("item_nome") or estado.get("item_nome") or self.ItemNome)
        self.ItemBaseId = str(snapshot.get("item_base_id") or estado.get("item_base_id") or self.ItemBaseId)
        self.Quantidade = max(1, int(snapshot.get("quantidade") or estado.get("quantidade") or self.Quantidade))
        self.DonoId = int(snapshot.get("dono_id", estado.get("dono_id", self.DonoId)) or 0)
        self.TokenDrop = str(snapshot.get("token_drop") or estado.get("token_drop") or self.TokenDrop)

        p0 = estado.get("pos_inicial") if isinstance(estado.get("pos_inicial"), (list, tuple)) else snapshot.get("pos_inicial")
        p1 = estado.get("pos_final") if isinstance(estado.get("pos_final"), (list, tuple)) else snapshot.get("pos_final")
        if isinstance(p0, (list, tuple)) and len(p0) == 2:
            self.PosicaoInicial = (float(p0[0]), float(p0[1]))
        if isinstance(p1, (list, tuple)) and len(p1) == 2:
            self.PosicaoFinal = (float(p1[0]), float(p1[1]))

        self.Velocidade = max(0.1, float(estado.get("velocidade", snapshot.get("velocidade", self.Velocidade)) or self.Velocidade))

        voando_estado = estado.get("voando")
        if isinstance(voando_estado, bool):
            self.Voando = voando_estado
        else:
            dist = math.hypot(self.PosicaoFinal[0] - self.Posicao[0], self.PosicaoFinal[1] - self.Posicao[1])
            self.Voando = dist > 0.03

        evento = estado.get("evento") if isinstance(estado.get("evento"), dict) else {}
        tipo_evento = str(evento.get("tipo") or "").strip().lower()
        if tipo_evento in {"coleta", "fusao"}:
            self._despawn_local = True

    def reconciliar_autoritativo(self, snapshot: Dict[str, object]) -> None:
        self.aplicar_snapshot(snapshot)

    def deve_remover_local(self) -> bool:
        return bool(self._despawn_local)

    def _mover_para(self, destino: Vector2, velocidade: float, dt: float) -> bool:
        dx = float(destino[0]) - float(self.Posicao[0])
        dy = float(destino[1]) - float(self.Posicao[1])
        dist = math.hypot(dx, dy)
        if dist <= 0.03:
            self.Posicao = (float(destino[0]), float(destino[1]))
            return True
        passo = min(dist, max(0.1, float(velocidade)) * dt)
        self.Posicao = (self.Posicao[0] + (dx / dist) * passo, self.Posicao[1] + (dy / dist) * passo)
        return passo >= dist - 1e-6

    def atualizar_visual(self, dt: float) -> None:
        dt = max(0.0, float(dt))

        if self._despawn_local:
            return

        if self.Voando:
            if self._mover_para(self.PosicaoFinal, self.Velocidade, dt):
                self.Voando = False

        if not self.Voando:
            self.TempoRespirar += dt
            self.EscalaRespirar = 1.0 + (math.sin(self.TempoRespirar * 3.2) * 0.045)
        else:
            self.EscalaRespirar = 1.0

    def desenhar(self, tela, camera) -> None:
        if self._despawn_local:
            return
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        item = {"Nome": self.ItemNome or "Item", "Code": self.ItemBaseId}
        lado = max(12, int(getattr(camera, "TilePx", 50) * 0.52 * self.EscalaRespirar))
        sprite = ItemInventario.surface_item(item, lado_px=lado)
        if sprite is None:
            sprite = pygame.Surface((lado, lado), pygame.SRCALPHA)
            pygame.draw.circle(sprite, (235, 235, 235, 230), (lado // 2, lado // 2), max(3, lado // 2 - 2))
        tela.blit(sprite, sprite.get_rect(center=(int(cx), int(cy))))
