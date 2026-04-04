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
        self._tempo_respiracao = 0.0
        self._cache_tamanho: tuple[int, int] | None = None
        self._overlay: pygame.Surface | None = None
        self._fade_top: pygame.Surface | None = None
        self._fade_bottom: pygame.Surface | None = None
        self._ator_player.definir_angulo_olhar(45.0)
        self._ator_npc.definir_angulo_olhar(135.0)
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
        base_x = int(w * 0.10)
        base_y = int(h * 0.75)
        bw = int(w * 0.80)
        bh = 44
        gap = 8
        return [pygame.Rect(base_x, base_y + i * (bh + gap), bw, bh) for i in range(len(self._opcoes))]

    def _garantir_cache_fundos(self, tela_size: tuple[int, int]) -> None:
        if self._cache_tamanho == tela_size:
            return
        w, h = tela_size
        self._cache_tamanho = tela_size
        self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 130))

        self._fade_top = pygame.Surface((w, int(h * 0.42)), pygame.SRCALPHA)
        for y in range(self._fade_top.get_height()):
            t = y / max(1, self._fade_top.get_height() - 1)
            alpha = int(255 * (1.0 - t) ** 1.95)
            pygame.draw.line(self._fade_top, (0, 0, 0, alpha), (0, y), (w, y))

        self._fade_bottom = pygame.Surface((w, int(h * 0.58)), pygame.SRCALPHA)
        for y in range(self._fade_bottom.get_height()):
            t = y / max(1, self._fade_bottom.get_height() - 1)
            alpha = int(248 * (t ** 1.75))
            pygame.draw.line(self._fade_bottom, (0, 0, 0, alpha), (0, y), (w, y))

    def _opcao_no_mouse(self, mouse_pos) -> int:
        for i, r in enumerate(self._opcao_rects(pygame.display.get_surface().get_size() if pygame.display.get_surface() else (1280, 720))):
            if r.collidepoint(mouse_pos):
                return i
        return -1

    def atualizar(self, dt: float) -> None:
        if self.Ativa:
            self._texto_animado.atualizar(dt)
            self._tempo_respiracao += max(0.0, float(dt))

    def desenhar(self, tela: pygame.Surface) -> None:
        if not self.Ativa:
            return
        w, h = tela.get_size()
        self._garantir_cache_fundos((w, h))
        tela.blit(self._overlay, (0, 0))
        tela.blit(self._fade_top, (0, 0))
        tela.blit(self._fade_bottom, (0, h - self._fade_bottom.get_height()))

        self._ator_player.set_tile_px(64)
        self._ator_npc.set_tile_px(64)
        self._ator_player.desenhar(tela, posicao_tela=(int(w * 0.12), int(h * 0.87)), respiracao_tempo=self._tempo_respiracao)
        self._ator_npc.desenhar(tela, posicao_tela=(int(w * 0.88), int(h * 0.87)), respiracao_tempo=self._tempo_respiracao)
        Texto(self._player_nome, pos=(int(w * 0.12), int(h * 0.91)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)
        Texto(self._npc_nome, pos=(int(w * 0.88), int(h * 0.91)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)

        fala = self._texto_animado.texto_visivel
        Texto(fala, pos=(int(w * 0.10), int(h * 0.61)), style={"size": 24, "align": "topleft", "outline": True}).draw(tela)

        if self._texto_animado.concluido:
            self._hover_idx = self._opcao_no_mouse(pygame.mouse.get_pos())
            for i, (op, rect) in enumerate(zip(self._opcoes, self._opcao_rects((w, h)))):
                hover = (i == self._hover_idx)
                tamanho = 24 if hover else 22
                cor = (255, 241, 156) if hover else (228, 235, 248)
                desloc_x = 4 if hover else 0
                Texto(
                    str(op.get("texto") or "..."),
                    pos=(rect.x + 6 + desloc_x, rect.centery),
                    style={"size": tamanho, "align": "midleft", "outline": True, "color": cor},
                ).draw(tela)
        else:
            Texto("(clique para concluir o texto)", pos=(int(w * 0.5), int(h * 0.88)), style={"size": 18, "align": "midbottom", "outline": True, "color": (220, 220, 230)}).draw(tela)
