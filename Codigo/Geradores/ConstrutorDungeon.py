from __future__ import annotations
import pygame
from Codigo.Geradores.Porta import renderizar as renderizar_porta

def renderizar_dungeon(tela, camera, layout:dict):
    tile=float(getattr(camera,'TilePx',50) or 50)
    bloco = int(layout.get("tamanho_bloco_sala_tiles", 30) or 30) if isinstance(layout, dict) else 30
    bloco_w = int(layout.get("largura_bloco_sala_tiles", bloco) or bloco) if isinstance(layout, dict) else bloco
    bloco_h = int(layout.get("altura_bloco_sala_tiles", bloco) or bloco) if isinstance(layout, dict) else bloco
    for sala in layout.get('salas',[]) if isinstance(layout,dict) else []:
        pos = sala.get('posicao_sala') or [0,0]
        mundo_x, mundo_y = float(pos[0]*bloco_w), float(pos[1]*bloco_h)
        tela_x, tela_y = camera.mundo_para_tela_px((mundo_x, mundo_y))
        r=pygame.Rect(int(tela_x), int(tela_y), int(bloco_w*tile), int(bloco_h*tile))
        pygame.draw.rect(tela,(60,60,68),r)
        pygame.draw.rect(tela,(130,130,140),r,4)
    for ent in layout.get('entradas',[]) if isinstance(layout,dict) else []:
        saida=ent.get('saida')
        if isinstance(saida,(list,tuple)) and len(saida)==2:
            renderizar_porta(tela,camera,saida,modo='dungeon')
