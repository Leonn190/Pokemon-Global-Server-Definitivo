from __future__ import annotations

from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_dungeons

_REGRAS = carregar_regras_dungeons()
TAMANHO_BLOCO_SALA_TILES = int(_REGRAS.get("tamanho_bloco_sala_tiles", 32) or 32)
LARGURA_BLOCO_SALA_TILES = int(_REGRAS.get("largura_bloco_sala_tiles", TAMANHO_BLOCO_SALA_TILES) or TAMANHO_BLOCO_SALA_TILES)
ALTURA_BLOCO_SALA_TILES = int(_REGRAS.get("altura_bloco_sala_tiles", TAMANHO_BLOCO_SALA_TILES) or TAMANHO_BLOCO_SALA_TILES)

def normalizar_dimensao_dungeon(dimensao:str)->str:
    return str(dimensao or "").strip()

def eh_dimensao_dungeon(dimensao:str)->bool:
    return normalizar_dimensao_dungeon(dimensao).startswith("Dungeon_")

def nome_dimensao_dungeon(dungeon_code)->str:
    return f"Dungeon_{str(dungeon_code or '').strip()}"

def tamanho_em_blocos(tamanho:int)->int:
    try:
        t = max(1, min(6, int(tamanho or 1)))
    except (TypeError, ValueError):
        t = 1
    return int(_REGRAS.get(f"tamanho_{t}_blocos", 4 + t) or (4 + t))

def posicao_sala_entrada(porta_idx:int, tamanho:int)->tuple[int,int]:
    t=tamanho_em_blocos(tamanho); i=max(0,int(porta_idx or 1)-1); return (i%t,i//t)

def retangulo_sala_em_tiles(pos_bloco):
    bx,by=int(pos_bloco[0]),int(pos_bloco[1]); return (bx*LARGURA_BLOCO_SALA_TILES,by*ALTURA_BLOCO_SALA_TILES,LARGURA_BLOCO_SALA_TILES,ALTURA_BLOCO_SALA_TILES)

def centro_sala_em_tiles(pos_bloco):
    x,y,w,h=retangulo_sala_em_tiles(pos_bloco); return [x+w/2.0,y+h/2.0]

def spawn_interno_entrada(pos_bloco):
    x,y,w,h=retangulo_sala_em_tiles(pos_bloco); return [x+w/2.0,y+h-3.0]

def saida_sala_entrada(pos_bloco):
    return spawn_interno_entrada(pos_bloco)

def sala_atual_por_posicao(pos):
    return (int(float(pos[0])//LARGURA_BLOCO_SALA_TILES),int(float(pos[1])//ALTURA_BLOCO_SALA_TILES))
