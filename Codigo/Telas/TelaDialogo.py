from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Prefabs.Texto import Texto, TextoAnimado


class TelaDialogo:
    def __init__(self, player_nome: str, player_skin: str, npc_payload: Dict[str, object], ao_encerrar: Optional[Callable[[], None]] = None):
        self.Ativa = True
        self._ao_encerrar = ao_encerrar
        self._npc = dict(npc_payload or {})
        estado = self._npc.get("estado") if isinstance(self._npc.get("estado"), dict) else {}
        self._npc_nome = str(self._npc.get("nome") or estado.get("nome") or "NPC")
        self._npc_skin = str(self._npc.get("skin") or estado.get("skin") or "S1.png")
        self._player_nome = str(player_nome or "Você")
        self._player_skin = str(player_skin or "S1.png")

        self._ator_player = Ator(nome_skin=self._player_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.0, tile_px=64)
        self._ator_npc = Ator(nome_skin=self._npc_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.0, tile_px=64)
        self._ator_player.Nome = self._player_nome
        self._ator_npc.Nome = self._npc_nome

        self._dialogo = self._carregar_dialogo()
        self._no_atual = str(self._dialogo.get("inicio", ""))
        self._texto_animado = TextoAnimado("", cps=48.0)
        self._opcoes: List[Dict[str, object]] = []
        self._hover_idx = -1
        self._reconstruir_no_atual()

    def _carregar_dialogo(self) -> Dict[str, object]:
        caminho = Path("Codigo") / "InteracaoNPC" / f"{self._npc_nome}.json"
        if not caminho.exists():
            return {
                "inicio": "fallback",
                "nos": {
                    "fallback": {
                        "fala": f"Olá, eu sou {self._npc_nome}. Ainda estou sem falas configuradas.",
                        "opcoes": [{"texto": "Tudo bem, até depois.", "fim": True}],
                    }
                },
            }
        try:
            with caminho.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {
            "inicio": "fallback",
            "nos": {"fallback": {"fala": "Tive um problema para abrir meu diálogo.", "opcoes": [{"texto": "Fechar", "fim": True}]}}
        }

    def _reconstruir_no_atual(self) -> None:
        nos = self._dialogo.get("nos") if isinstance(self._dialogo.get("nos"), dict) else {}
        no = nos.get(self._no_atual, {}) if isinstance(nos.get(self._no_atual, {}), dict) else {}
        fala = str(no.get("fala") or "...")
        opcoes = list(no.get("opcoes", [])) if isinstance(no.get("opcoes"), list) else []
        self._texto_animado.set_texto(fala)
        self._opcoes = [o for o in opcoes if isinstance(o, dict)]
        self._hover_idx = -1

    def _encerrar(self) -> None:
        self.Ativa = False
        if callable(self._ao_encerrar):
            self._ao_encerrar()

    def _selecionar_opcao(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._opcoes):
            return
        op = self._opcoes[idx]
        if bool(op.get("fim", False)):
            self._encerrar()
            return
        prox = str(op.get("proximo") or "")
        if not prox:
            self._encerrar()
            return
        self._no_atual = prox
        self._reconstruir_no_atual()

    def processar_eventos(self, eventos: List[pygame.event.Event]) -> bool:
        if not self.Ativa:
            return False
        for ev in eventos:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._encerrar()
                return True
            if ev.type == pygame.MOUSEMOTION:
                self._hover_idx = self._opcao_no_mouse(ev.pos)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if not self._texto_animado.concluido:
                    self._texto_animado.pular_animacao()
                else:
                    idx = self._opcao_no_mouse(ev.pos)
                    if idx >= 0:
                        self._selecionar_opcao(idx)
                return True
        return True

    def _opcao_rects(self, tela_size) -> List[pygame.Rect]:
        w, h = tela_size
        base_x = int(w * 0.12)
        base_y = int(h * 0.70)
        bw = int(w * 0.76)
        bh = 44
        gap = 10
        return [pygame.Rect(base_x, base_y + i * (bh + gap), bw, bh) for i in range(len(self._opcoes))]

    def _opcao_no_mouse(self, mouse_pos) -> int:
        for i, r in enumerate(self._opcao_rects(pygame.display.get_surface().get_size() if pygame.display.get_surface() else (1280, 720))):
            if r.collidepoint(mouse_pos):
                return i
        return -1

    def atualizar(self, dt: float) -> None:
        if self.Ativa:
            self._texto_animado.atualizar(dt)

    def desenhar(self, tela: pygame.Surface) -> None:
        if not self.Ativa:
            return
        w, h = tela.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 90))
        tela.blit(overlay, (0, 0))

        top_grad = pygame.Surface((w, int(h * 0.25)), pygame.SRCALPHA)
        for y in range(top_grad.get_height()):
            a = int(180 * (1.0 - (y / max(1, top_grad.get_height()))))
            pygame.draw.line(top_grad, (0, 0, 0, a), (0, y), (w, y))
        tela.blit(top_grad, (0, 0))

        bot_grad = pygame.Surface((w, int(h * 0.30)), pygame.SRCALPHA)
        for y in range(bot_grad.get_height()):
            a = int(210 * (y / max(1, bot_grad.get_height())))
            pygame.draw.line(bot_grad, (0, 0, 0, a), (0, y), (w, y))
        tela.blit(bot_grad, (0, h - bot_grad.get_height()))

        box = pygame.Rect(int(w * 0.08), int(h * 0.52), int(w * 0.84), int(h * 0.40))
        pygame.draw.rect(tela, (18, 24, 36, 220), box, border_radius=16)
        pygame.draw.rect(tela, (83, 123, 177), box, width=2, border_radius=16)

        self._ator_player.set_tile_px(64)
        self._ator_npc.set_tile_px(64)
        self._ator_player.desenhar(tela, posicao_tela=(int(w * 0.12), int(h * 0.83)), respiracao_tempo=0.0)
        self._ator_npc.desenhar(tela, posicao_tela=(int(w * 0.88), int(h * 0.83)), respiracao_tempo=0.0)
        Texto(self._player_nome, pos=(int(w * 0.12), int(h * 0.91)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)
        Texto(self._npc_nome, pos=(int(w * 0.88), int(h * 0.91)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)

        fala = self._texto_animado.texto_visivel
        Texto(fala, pos=(int(w * 0.12), int(h * 0.58)), style={"size": 24, "align": "topleft", "outline": True}).draw(tela)

        if self._texto_animado.concluido:
            for i, (op, rect) in enumerate(zip(self._opcoes, self._opcao_rects((w, h)))):
                hover = i == self._hover_idx
                cor = (46, 66, 96) if not hover else (72, 102, 148)
                pygame.draw.rect(tela, cor, rect, border_radius=9)
                pygame.draw.rect(tela, (130, 170, 226), rect, width=1, border_radius=9)
                Texto(str(op.get("texto") or "..."), pos=(rect.x + 10, rect.centery), style={"size": 21, "align": "midleft", "outline": True}).draw(tela)
        else:
            Texto("(clique para concluir o texto)", pos=(int(w * 0.5), int(h * 0.88)), style={"size": 18, "align": "midbottom", "outline": True, "color": (220, 220, 230)}).draw(tela)
