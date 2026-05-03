from __future__ import annotations
import pygame
class ControladorDungeons:
    def __init__(self): self._ultima_dim='Mundo'; self._texto_ate=0; self._texto='Dungeon'
    def atualizar_dimensao(self, dimensao:str, layout:dict|None=None):
        if str(dimensao).startswith('Dungeon') and not str(self._ultima_dim).startswith('Dungeon'):
            self._texto=(layout or {}).get('dungeon_nome','Dungeon'); self._texto_ate=pygame.time.get_ticks()+2400
        self._ultima_dim=dimensao
    def renderizar_texto(self, tela):
        if pygame.time.get_ticks()>self._texto_ate: return
        f=pygame.font.SysFont('arial',42); img=f.render(self._texto,True,(240,240,240)); tela.blit(img,img.get_rect(center=tela.get_rect().center))
    def renderizar_mascara_sala(self, tela, camera, player_pos, layout):
        if not str(self._ultima_dim).startswith("Dungeon") or not isinstance(layout, dict) or player_pos is None:
            return
        bloco = int(layout.get("tamanho_bloco_sala_tiles", 30) or 30)
        salas = layout.get("salas") if isinstance(layout.get("salas"), list) else []
        sala_atual = (int(float(player_pos[0]) // bloco), int(float(player_pos[1]) // bloco))
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
        sx = int(sala_valida[0]) * bloco
        sy = int(sala_valida[1]) * bloco
        x, y = camera.mundo_para_tela_px((sx, sy))
        tile = float(getattr(camera, "TilePx", 50) or 50)
        vis = pygame.Rect(int(x), int(y), int(bloco * tile), int(bloco * tile))
        W, H = tela.get_size()
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(0, 0, W, max(0, vis.top)))
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(0, vis.bottom, W, max(0, H - vis.bottom)))
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(0, vis.top, max(0, vis.left), max(0, vis.height)))
        pygame.draw.rect(tela, (0, 0, 0), pygame.Rect(vis.right, vis.top, max(0, W - vis.right), max(0, vis.height)))
