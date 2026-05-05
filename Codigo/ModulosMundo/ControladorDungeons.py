from __future__ import annotations
import pygame
from Codigo.Geradores.ConstrutorDungeon import salvar_debug_layout
from Codigo.Prefabs.TextoCinematico import TextoCinematico


class ControladorDungeons:
    def __init__(self):
        self._ultima_dim = "Mundo"
        self._ultimo_nome = ""
        self._texto = TextoCinematico("Dungeon", tamanho=42)

    def atualizar_dimensao(self, dimensao:str, layout:dict|None=None):
        dentro_dungeon = str(dimensao).startswith("Dungeon")
        nome = str((layout or {}).get("dungeon_nome") or "").strip()
        if dentro_dungeon and (not str(self._ultima_dim).startswith("Dungeon") or (nome and nome != self._ultimo_nome)):
            self._ultimo_nome = nome or self._ultimo_nome or "Dungeon"
            self._texto.iniciar(self._ultimo_nome, duracao_ms=2400)
        if dentro_dungeon and isinstance(layout, dict):
            salvar_debug_layout(layout, str(dimensao))
        self._ultima_dim=dimensao

    def renderizar_texto(self, tela):
        self._texto.atualizar()
        if not self._texto.ativo():
            return
        self._texto.desenhar(tela, tela.get_rect().center)

    def efeito_shader(self) -> dict:
        return self._texto.efeito_shader(modo=1.0)

    def renderizar_mascara_sala(self, tela, camera, player_pos, layout):
        if not str(self._ultima_dim).startswith("Dungeon") or not isinstance(layout, dict) or player_pos is None:
            return
        bloco = int(layout.get("tamanho_bloco_sala_tiles", 30) or 30)
        bloco_w = int(layout.get("largura_bloco_sala_tiles", bloco) or bloco)
        bloco_h = int(layout.get("altura_bloco_sala_tiles", bloco) or bloco)
        salas = layout.get("salas") if isinstance(layout.get("salas"), list) else []
        sala_atual = (int(float(player_pos[0]) // bloco_w), int(float(player_pos[1]) // bloco_h))
        sala_valida = None
        for sala in salas:
            pos = sala.get("posicao_sala") if isinstance(sala, dict) else None
            if isinstance(pos, (list, tuple)) and len(pos) == 2 and int(pos[0]) == sala_atual[0] and int(pos[1]) == sala_atual[1]:
                sala_valida = (int(pos[0]), int(pos[1]))
                break
        if sala_valida is None:
            entradas = layout.get("entradas") if isinstance(layout.get("entradas"), list) else []
            if entradas:
                pos_e = entradas[0].get("posicao_sala") if isinstance(entradas[0], dict) else None
                if isinstance(pos_e, (list, tuple)) and len(pos_e) == 2:
                    sala_valida = (int(pos_e[0]), int(pos_e[1]))
        if sala_valida is None:
            return
        sx = int(sala_valida[0]) * bloco_w
        sy = int(sala_valida[1]) * bloco_h
        x, y = camera.mundo_para_tela_px((sx, sy))
        tile = float(getattr(camera, "TilePx", 50) or 50)
        vis = pygame.Rect(int(x), int(y), int(bloco_w * tile), int(bloco_h * tile))
        W, H = tela.get_size()
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(0, 0, W, max(0, vis.top)))
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(0, vis.bottom, W, max(0, H - vis.bottom)))
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(0, vis.top, max(0, vis.left), max(0, vis.height)))
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(vis.right, vis.top, max(0, W - vis.right), max(0, vis.height)))
