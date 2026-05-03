from __future__ import annotations
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_dungeons

_REGRAS=carregar_regras_dungeons()
TAMANHO_BLOCO_SALA_TILES=int(_REGRAS.get("tamanho_bloco_sala_tiles",30) or 30)

def normalizar_dimensao_dungeon(dimensao:str)->str:
    return str(dimensao or "").strip()

def eh_dimensao_dungeon(dimensao:str)->bool:
    return normalizar_dimensao_dungeon(dimensao).startswith("Dungeon_")

def nome_dimensao_dungeon(dungeon_code)->str:
    return f"Dungeon_{str(dungeon_code or '').strip()}"

def tamanho_em_blocos(tamanho:int)->int:
    m={1:int(_REGRAS.get('tamanho_1_blocos',4)),2:int(_REGRAS.get('tamanho_2_blocos',5)),3:int(_REGRAS.get('tamanho_3_blocos',6))}
    return m.get(int(tamanho or 1),m[1])

def posicao_sala_entrada(porta_idx:int, tamanho:int)->tuple[int,int]:
    t=tamanho_em_blocos(tamanho); i=max(0,int(porta_idx or 1)-1); return (i%t,i//t)

def retangulo_sala_em_tiles(pos_bloco):
    bx,by=int(pos_bloco[0]),int(pos_bloco[1]); s=TAMANHO_BLOCO_SALA_TILES; return (bx*s,by*s,s,s)

def spawn_interno_entrada(pos_bloco):
    x,y,w,h=retangulo_sala_em_tiles(pos_bloco); return [x+w/2.0,y+h-3.0]

def saida_sala_entrada(pos_bloco):
    return spawn_interno_entrada(pos_bloco)

def sala_atual_por_posicao(pos):
    s=TAMANHO_BLOCO_SALA_TILES; return (int(float(pos[0])//s),int(float(pos[1])//s))
