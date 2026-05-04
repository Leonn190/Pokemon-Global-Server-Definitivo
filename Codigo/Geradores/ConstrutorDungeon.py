from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pygame
from Codigo.Geradores.Porta import renderizar as renderizar_porta

_DEBUG_HASHES = {}
_CORES_DEBUG = {
    "entrada": (60, 210, 105),
    "comum": (128, 128, 136),
    "pacifica": (126, 212, 242),
    "dificil": (230, 94, 54),
    "piscina": (45, 118, 230),
    "boss": (246, 214, 70),
    "": (0, 0, 0),
}

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


def salvar_debug_layout(layout: dict, dimensao: str) -> bool:
    if not isinstance(layout, dict) or not str(dimensao or "").startswith("Dungeon_"):
        return False
    grid_tipos = layout.get("grid_salas_tipos") if isinstance(layout.get("grid_salas_tipos"), list) else []
    grid_ids = layout.get("grid_salas_ids") if isinstance(layout.get("grid_salas_ids"), list) else []
    if not grid_tipos and not grid_ids:
        return False
    bruto = json.dumps({"dimensao": dimensao, "ids": grid_ids, "tipos": grid_tipos}, sort_keys=True, ensure_ascii=True)
    h = hashlib.sha1(bruto.encode("utf-8")).hexdigest()
    if _DEBUG_HASHES.get(str(dimensao)) == h:
        return False
    _DEBUG_HASHES[str(dimensao)] = h

    linhas = grid_tipos or [["" for _ in row] for row in grid_ids]
    altura = len(linhas)
    largura = max((len(r) for r in linhas if isinstance(r, list)), default=0)
    if largura <= 0 or altura <= 0:
        return False
    cell = 28
    surface = pygame.Surface((largura * cell, altura * cell), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 255))
    for y, row in enumerate(linhas):
        if not isinstance(row, list):
            continue
        for x, tipo in enumerate(row):
            tipo_norm = str(tipo or "")
            cor = _CORES_DEBUG.get(tipo_norm, _CORES_DEBUG[""])
            rect = pygame.Rect(x * cell, y * cell, cell, cell)
            pygame.draw.rect(surface, cor, rect)
            if tipo_norm:
                pygame.draw.rect(surface, (235, 235, 235), rect, 1)

    for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
        if not isinstance(sala, dict):
            continue
        pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
        if not pos or len(pos) != 2:
            continue
        x, y = int(pos[0]), int(pos[1])
        cx = x * cell + cell // 2
        cy = y * cell + cell // 2
        for porta in list(sala.get("portas") or []):
            p = str(porta)
            if p == "N":
                pygame.draw.line(surface, (255, 255, 255), (cx - 4, y * cell), (cx + 4, y * cell), 3)
            elif p == "S":
                pygame.draw.line(surface, (255, 255, 255), (cx - 4, (y + 1) * cell - 1), (cx + 4, (y + 1) * cell - 1), 3)
            elif p == "L":
                pygame.draw.line(surface, (255, 255, 255), ((x + 1) * cell - 1, cy - 4), ((x + 1) * cell - 1, cy + 4), 3)
            elif p == "O":
                pygame.draw.line(surface, (255, 255, 255), (x * cell, cy - 4), (x * cell, cy + 4), 3)

    pasta = Path("Saves") / "DungeonDebug"
    pasta.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(pasta / f"{dimensao}.png"))
    return True
