from __future__ import annotations
from Codigo.Geradores.Porta import renderizar as renderizar_porta

def estrutura_eh_porta_dungeon(payload:dict)->bool:
    estado = payload.get('estado') if isinstance(payload.get('estado'),dict) else {}
    return str(estado.get('subtipo') or '').lower()=='dungeon' and bool(estado.get('estrutura_quebrada', False) or estado.get('porta_ativa', False))

def renderizar_entrada_mundo(tela, camera, payload:dict)->None:
    if not estrutura_eh_porta_dungeon(payload):
        return
    pos = payload.get('posicao')
    if isinstance(pos,(list,tuple)) and len(pos)==2:
        renderizar_porta(tela,camera,pos,modo='dungeon')
