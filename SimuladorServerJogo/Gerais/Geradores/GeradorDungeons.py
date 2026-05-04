from __future__ import annotations
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.DungeonGeometria import nome_dimensao_dungeon, posicao_sala_entrada, spawn_interno_entrada, saida_sala_entrada, tamanho_em_blocos, TAMANHO_BLOCO_SALA_TILES


def _dungeons_csv():
    return carregar_csv_dict("Pokemon Global Server - Dungeons.csv")


def _coletar_entradas_dungeon_no_banco(dungeon_code: str) -> list[dict]:
    entradas_reais = []
    vistos = set()
    for obj in BANCO_DADOS.listar_objetos():
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        if str(estado.get("subtipo") or "").lower() != "dungeon":
            continue
        if str(estado.get("dungeon_code") or "").strip().lower() != str(dungeon_code).strip().lower():
            continue
        porta_idx = int(estado.get("porta_idx", len(entradas_reais)+1) or len(entradas_reais)+1)
        entradas_reais.append({"porta_idx": porta_idx, "pedra_id": int(getattr(obj, "Id", 0) or 0)})
        vistos.add(porta_idx)
    for item in BANCO_DADOS.listar_dungeons_registradas():
        if str(item.get("dungeon_code") or "").strip().lower() != str(dungeon_code).strip().lower():
            continue
        porta_idx = int(item.get("porta_idx", len(entradas_reais)+1) or len(entradas_reais)+1)
        if porta_idx in vistos:
            continue
        entradas_reais.append({"porta_idx": porta_idx, "pedra_id": int(item.get("pedra_id", 0) or 0)})
        vistos.add(porta_idx)
    return entradas_reais


def resolver_dungeon_por_code(code:str)->dict|None:
    alvo=str(code or "").strip().lower()
    for row in _dungeons_csv():
        if str(row.get("Code") or "").strip().lower()==alvo:
            return row
    return None


def gerar_dungeon_layout(dungeon_code:str, entradas:list[dict])->dict:
    row=resolver_dungeon_por_code(dungeon_code) or {}
    tamanho=int(float(row.get("Tamanho",1) or 1))
    largura=altura=tamanho_em_blocos(tamanho)
    nome=str(row.get("Nome") or dungeon_code)
    dificuldade=str(row.get("Dificuldade") or "")
    entradas_out=[]; salas=[]
    entradas_reais = _coletar_entradas_dungeon_no_banco(dungeon_code)
    if not entradas_reais:
        entradas_reais = list(entradas or [])
    for i,e in enumerate(entradas_reais, start=1):
        porta_idx=int(e.get("porta_idx",i) or i)
        pos_bloco=posicao_sala_entrada(porta_idx,tamanho)
        ent={"porta_idx":porta_idx,"sala_id":f"entrada_{porta_idx}","posicao_sala":[pos_bloco[0],pos_bloco[1]],"spawn":spawn_interno_entrada(pos_bloco),"saida":saida_sala_entrada(pos_bloco)}
        entradas_out.append(ent)
        salas.append({"id":ent["sala_id"],"tipo":"entrada","largura_blocos":1,"altura_blocos":1,"posicao_sala":[pos_bloco[0],pos_bloco[1]]})
    return {"dimensao":nome_dimensao_dungeon(dungeon_code),"dungeon_code":str(dungeon_code),"dungeon_nome":nome,"tamanho":tamanho,"dificuldade":dificuldade,"largura_blocos":largura,"altura_blocos":altura,"tamanho_bloco_sala_tiles":TAMANHO_BLOCO_SALA_TILES,"salas":salas,"entradas":entradas_out,"catalogo_versao":"v1"}
