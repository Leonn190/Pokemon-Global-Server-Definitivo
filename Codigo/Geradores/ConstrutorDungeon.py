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


def _porta_rect(pos, direcao, bloco_w, bloco_h, tile, largura_tiles=4):
    x0, y0 = float(pos[0] * bloco_w), float(pos[1] * bloco_h)
    w = max(1, int(largura_tiles))
    if direcao in ("N", "S"):
        px = x0 + (bloco_w - w) * 0.5
        py = y0 if direcao == "N" else y0 + bloco_h - 1
        return pygame.Rect(int(px * tile), int(py * tile), max(2, int(w * tile)), max(2, int(tile)))
    px = x0 if direcao == "O" else x0 + bloco_w - 1
    py = y0 + (bloco_h - w) * 0.5
    return pygame.Rect(int(px * tile), int(py * tile), max(2, int(tile)), max(2, int(w * tile)))


def construir_surface_mapa_dungeon(layout: dict, estado_dungeon: dict | None = None, debug: bool = False, cell: int = 28):
    if not isinstance(layout, dict):
        return None
    grid_tipos = layout.get("grid_salas_tipos") if isinstance(layout.get("grid_salas_tipos"), list) else []
    if not grid_tipos:
        return None
    exploradas = set()
    if isinstance(estado_dungeon, dict):
        exploradas = {str(x) for x in list(estado_dungeon.get("salas_exploradas") or [])}
    mostrar_tudo = bool(debug) or not exploradas
    salas_por_pos = {}
    for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
        if not isinstance(sala, dict):
            continue
        pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
        if pos and len(pos) == 2:
            salas_por_pos[(int(pos[0]), int(pos[1]))] = sala
    altura = len(grid_tipos)
    largura = max((len(r) for r in grid_tipos if isinstance(r, list)), default=0)
    if largura <= 0 or altura <= 0:
        return None
    surface = pygame.Surface((largura * cell, altura * cell), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 255))
    for y, row in enumerate(grid_tipos):
        if not isinstance(row, list):
            continue
        for x, tipo in enumerate(row):
            sala = salas_por_pos.get((x, y), {})
            if not mostrar_tudo and str(sala.get("id") or "") not in exploradas:
                continue
            tipo_norm = str(tipo or "")
            rect = pygame.Rect(x * cell, y * cell, cell, cell)
            pygame.draw.rect(surface, _CORES_DEBUG.get(tipo_norm, _CORES_DEBUG[""]), rect)
            if tipo_norm:
                pygame.draw.rect(surface, (235, 235, 235), rect, 1)
    for sala in salas_por_pos.values():
        if not mostrar_tudo and str(sala.get("id") or "") not in exploradas:
            continue
        pos = sala.get("posicao_sala")
        x, y = int(pos[0]), int(pos[1])
        cx, cy = x * cell + cell // 2, y * cell + cell // 2
        if debug and int(sala.get("chaves_da_sala", 0) or 0) > 0:
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(3, cell // 7))
        for porta in list(sala.get("portas_info") or []):
            p = str(porta.get("direcao") or "")
            locked = bool(porta.get("trancada", False))
            cor = (255, 190, 45) if locked else (255, 255, 255)
            if p == "N":
                pygame.draw.line(surface, cor, (cx - 4, y * cell), (cx + 4, y * cell), 3)
            elif p == "S":
                pygame.draw.line(surface, cor, (cx - 4, (y + 1) * cell - 1), (cx + 4, (y + 1) * cell - 1), 3)
            elif p == "L":
                pygame.draw.line(surface, cor, ((x + 1) * cell - 1, cy - 4), ((x + 1) * cell - 1, cy + 4), 3)
            elif p == "O":
                pygame.draw.line(surface, cor, (x * cell, cy - 4), (x * cell, cy + 4), 3)
    return surface

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
        for info in list(sala.get("portas_info") or []):
            pos = sala.get("posicao_sala") or [0, 0]
            pr = _porta_rect(pos, str(info.get("direcao") or ""), bloco_w, bloco_h, tile, int(layout.get("porta_largura_tiles", 4) or 4))
            pr.x += int(-camera.PosicaoTiles[0] * tile)
            pr.y += int(-camera.PosicaoTiles[1] * tile)
            pygame.draw.rect(tela, (74, 58, 48) if bool(info.get("trancada", False)) else (94, 86, 76), pr)
            if bool(info.get("trancada", False)):
                pygame.draw.rect(tela, (246, 196, 64), pr, max(1, int(tile * 0.06)))
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
    bruto = json.dumps({"dimensao": dimensao, "ids": grid_ids, "tipos": grid_tipos, "portas": layout.get("portas_trancadas"), "chaves": layout.get("chaves")}, sort_keys=True, ensure_ascii=True)
    h = hashlib.sha1(bruto.encode("utf-8")).hexdigest()
    if _DEBUG_HASHES.get(str(dimensao)) == h:
        return False
    _DEBUG_HASHES[str(dimensao)] = h

    surface = construir_surface_mapa_dungeon(layout, debug=True, cell=28)
    if surface is None:
        return False

    pasta = Path("Saves") / "DungeonDebug"
    pasta.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(pasta / f"{dimensao}.png"))
    return True
