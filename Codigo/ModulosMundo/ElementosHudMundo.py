from __future__ import annotations

import pygame
from pathlib import Path

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Mensagem import MensagensGanhosMundo
from Codigo.Prefabs.Texto import Texto
from Codigo.ModulosMundo.Minimapa import MinimapaMundo
from Codigo.Paineis.PainelCaptura import PainelCaptura


class ElementosHudMundo:
    def __init__(self):
        self.SlotsVisiveis = 8
        self.TextoQtd = Texto("", style={"size": 14, "align": "bottomright", "outline_thickness": 1})
        self._mensagens_ganhos = MensagensGanhosMundo()
        self._minimapa = MinimapaMundo()
        self._painel_captura = PainelCaptura()
        self._coracao = None
        self._coracao_preto = None

    def _carregar_coracao(self, lado=28):
        if self._coracao is not None:
            return
        try:
            img = pygame.image.load(str(Path("Recursos") / "Visual" / "Icones" / "Diversos" / "CoraçãoVida.png")).convert_alpha()
            self._coracao = pygame.transform.smoothscale(img, (lado, lado))
        except Exception:
            self._coracao = pygame.Surface((lado, lado), pygame.SRCALPHA)
            pygame.draw.polygon(self._coracao, (230, 42, 64), [(lado//2, lado-4), (4, lado//3), (lado//4, 4), (lado//2, lado//4), (3*lado//4, 4), (lado-4, lado//3)])
        preto = self._coracao.copy()
        preto.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._coracao_preto = preto

    def registrar_ganho(self, ganho: dict | None) -> None:
        if not isinstance(ganho, dict):
            return
        tipo = str(ganho.get("tipo") or "").strip().lower()
        quantidade = int(ganho.get("quantidade", 1) or 1)
        if quantidade <= 0:
            return
        if tipo == "item":
            self._mensagens_ganhos.adicionar_item(str(ganho.get("nome") or "Item"), quantidade)
            return
        if tipo == "moedas":
            self._mensagens_ganhos.adicionar_moedas(quantidade)
            return
        if tipo == "xp":
            self._mensagens_ganhos.adicionar_xp(quantidade)

    def atualizar(self, dt: float) -> None:
        self._mensagens_ganhos.atualizar(dt)

    def desenhar(self, tela, inventario, terminal=None, eventos=None, dt=0.0, servico_mapa=None, pos_player_mundo=(0.0, 0.0), angulo_olhar=0.0, mostrar_minimapa=False, estado_dungeon=None, layout_dungeon=None, captura_hud=None, objetos_mundo=None, perfil=None):
        largura, altura = tela.get_size()
        slot = 50
        gap = 8
        total = (slot * self.SlotsVisiveis) + (gap * (self.SlotsVisiveis - 1))
        x0 = (largura - total) // 2
        y = altura - slot - 20
        if isinstance(estado_dungeon, dict):
            self._carregar_coracao()
            vida = estado_dungeon.get("vida_player") if isinstance(estado_dungeon.get("vida_player"), dict) else {}
            coracoes = max(0, int(vida.get("coracoes", estado_dungeon.get("coracoes", 0)) or 0))
            max_cor = max(coracoes, int(vida.get("coracoes_max", estado_dungeon.get("coracoes_max", 3)) or 3))
            gap_h = 6
            lado = self._coracao.get_width() if self._coracao is not None else 28
            total_h = (lado * max_cor) + (gap_h * max(0, max_cor - 1))
            hx = (largura - total_h) // 2
            hy = y - lado - 10
            for i in range(max_cor):
                img = self._coracao if i < coracoes else self._coracao_preto
                if img is not None:
                    tela.blit(img, (hx + i * (lado + gap_h), hy))

        for i in range(self.SlotsVisiveis):
            rect = pygame.Rect(x0 + i * (slot + gap), y, slot, slot)
            selecionado = i == inventario.SlotSelecionado
            bg = (64, 68, 80) if not selecionado else (220, 190, 90)
            pygame.draw.rect(tela, bg, rect, border_radius=6)
            pygame.draw.rect(tela, (20, 22, 30), rect, 2, border_radius=6)

            if i >= len(inventario.Itens):
                continue
            item = inventario.Itens[i]
            if item is None:
                continue
            sprite = ItemInventario.surface_item(item, lado_px=28)
            if sprite is not None:
                tela.blit(sprite, sprite.get_rect(center=rect.center))

            qtd = int(item.get("quantidade", 1)) if isinstance(item, dict) else 1
            if qtd > 1:
                self.TextoQtd.set_text(str(qtd))
                self.TextoQtd.set_pos((rect.right - 2, rect.bottom - 1))
                self.TextoQtd.draw(tela)

        if bool(mostrar_minimapa):
            self._minimapa.desenhar(tela, servico_mapa, pos_player_mundo, float(angulo_olhar or 0.0), layout_dungeon=layout_dungeon, estado_dungeon=estado_dungeon, objetos_mundo=objetos_mundo, perfil=perfil)
        self._painel_captura.desenhar(tela, captura=captura_hud, mostrar_minimapa=bool(mostrar_minimapa), dt=dt)

        if terminal is not None:
            terminal.desenhar(tela, eventos or [], dt)
        self._mensagens_ganhos.desenhar(tela)
