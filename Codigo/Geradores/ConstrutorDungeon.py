from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pygame
from Codigo.Geradores.Porta import renderizar as renderizar_porta

_DEBUG_HASHES = {}
_SPRITES_TRAPS = {}
_CORES_DEBUG = {
    "entrada": (60, 210, 105),
    "normal": (128, 128, 136),
    "comum": (128, 128, 136),
    "pacifica": (126, 212, 242),
    "dificil": (230, 94, 54),
    "piscina": (45, 118, 230),
    "escura": (76, 58, 112),
    "boss": (246, 214, 70),
    "": (0, 0, 0),
}


def _porta_rect(pos, direcao, bloco_w, bloco_h, tile, largura_tiles=4, espessura_tiles=1):
    x0, y0 = float(pos[0] * bloco_w), float(pos[1] * bloco_h)
    w = max(1, int(largura_tiles))
    e = max(1, int(espessura_tiles))
    if direcao in ("N", "S"):
        px = x0 + (bloco_w - w) * 0.5
        py = y0 if direcao == "N" else y0 + bloco_h - e
        return pygame.Rect(int(px * tile), int(py * tile), max(2, int(w * tile)), max(2, int(e * tile)))
    px = x0 if direcao == "O" else x0 + bloco_w - e
    py = y0 + (bloco_h - w) * 0.5
    return pygame.Rect(int(px * tile), int(py * tile), max(2, int(e * tile)), max(2, int(w * tile)))


def _sprite_trap(nome: str):
    chave = str(nome or "")
    if chave in _SPRITES_TRAPS:
        return _SPRITES_TRAPS[chave]
    caminho = Path("Recursos") / "Visual" / "Mundo" / "Outros" / chave
    try:
        surf = pygame.image.load(str(caminho)).convert_alpha()
    except Exception:
        surf = None
    _SPRITES_TRAPS[chave] = surf
    return surf


def _mundo_para_tela(camera, pos):
    return camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))


def _desenhar_espeto(tela, camera, pos, movel=False, escala=1.0):
    sprite = _sprite_trap("Espetos Movel.png" if movel else "Espetos.png")
    cx, cy = _mundo_para_tela(camera, pos)
    lado = max(10, int(float(getattr(camera, "TilePx", 50) or 50) * float(escala)))
    if sprite is not None:
        img = pygame.transform.smoothscale(sprite, (lado, lado))
        tela.blit(img, img.get_rect(center=(int(cx), int(cy))))
        return
    cor = (150, 150, 162) if not movel else (190, 180, 210)
    pts = [(int(cx), int(cy - lado * 0.45)), (int(cx - lado * 0.36), int(cy + lado * 0.32)), (int(cx + lado * 0.36), int(cy + lado * 0.32))]
    pygame.draw.polygon(tela, cor, pts)
    pygame.draw.polygon(tela, (44, 44, 52), pts, 2)


def _desenhar_quebradinho(tela, camera, pos, fase="inteiro"):
    cx, cy = _mundo_para_tela(camera, pos)
    tile = int(getattr(camera, "TilePx", 50) or 50)
    rect = pygame.Rect(0, 0, max(6, int(tile * 0.82)), max(6, int(tile * 0.82)))
    rect.center = (int(cx), int(cy))
    cor = (64, 64, 70) if fase != "buraco" else (0, 0, 0)
    pygame.draw.rect(tela, cor, rect, border_radius=max(1, tile // 18))
    if fase != "buraco":
        pygame.draw.line(tela, (26, 26, 30), rect.midtop, rect.center, 2)
        pygame.draw.line(tela, (26, 26, 30), rect.center, rect.bottomright, 2)
        pygame.draw.line(tela, (26, 26, 30), rect.center, rect.midleft, 2)


def _desenhar_barra_fogo(tela, camera, trap, estado):
    pos = trap.get("posicao", [0, 0])
    cx, cy = _mundo_para_tela(camera, pos)
    tile = float(getattr(camera, "TilePx", 50) or 50)
    pygame.draw.rect(tela, (54, 46, 44), pygame.Rect(int(cx - tile * 0.28), int(cy - tile * 0.28), int(tile * 0.56), int(tile * 0.56)))
    for bola in list(estado.get("bolas_posicoes") or []):
        bx, by = _mundo_para_tela(camera, bola)
        r = max(4, int(tile * 0.18))
        pygame.draw.circle(tela, (255, 100, 28), (int(bx), int(by)), r)
        pygame.draw.circle(tela, (255, 218, 74), (int(bx), int(by)), max(2, r // 2))


def _desenhar_torreta(tela, camera, trap, estado):
    pos = trap.get("posicao", [0, 0])
    cx, cy = _mundo_para_tela(camera, pos)
    tile = float(getattr(camera, "TilePx", 50) or 50)
    rect = pygame.Rect(0, 0, int(tile * 0.78), int(tile * 0.78))
    rect.center = (int(cx), int(cy))
    pygame.draw.rect(tela, (52, 58, 66), rect)
    pygame.draw.rect(tela, (180, 190, 205), rect, 2)
    for proj in list(estado.get("projeteis") or []):
        p = proj.get("posicao") if isinstance(proj.get("posicao"), (list, tuple)) else None
        if p is None:
            continue
        px, py = _mundo_para_tela(camera, p)
        pygame.draw.circle(tela, (255, 114, 46), (int(px), int(py)), max(4, int(tile * 0.16)))


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


def construir_surface_mapa_dungeon_local(layout: dict, estado_dungeon: dict | None = None, sala_atual=None, cell: int = 28, raio: int = 1):
    if not isinstance(layout, dict):
        return None
    lado = int(raio) * 2 + 1
    if lado <= 0:
        return None
    salas_por_pos = {}
    salas_por_id = {}
    for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
        if not isinstance(sala, dict):
            continue
        pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
        if pos and len(pos) == 2:
            salas_por_pos[(int(pos[0]), int(pos[1]))] = sala
        salas_por_id[str(sala.get("id") or "")] = sala

    centro = sala_atual if isinstance(sala_atual, (list, tuple)) and len(sala_atual) == 2 else None
    if centro is None and isinstance(estado_dungeon, dict):
        centro = estado_dungeon.get("sala_posicao") if isinstance(estado_dungeon.get("sala_posicao"), (list, tuple)) and len(estado_dungeon.get("sala_posicao")) == 2 else None
    if centro is None and isinstance(estado_dungeon, dict):
        sala = salas_por_id.get(str(estado_dungeon.get("sala_id") or ""))
        centro = sala.get("posicao_sala") if isinstance(sala, dict) else None
    if not (isinstance(centro, (list, tuple)) and len(centro) == 2):
        return None

    exploradas = set()
    if isinstance(estado_dungeon, dict):
        exploradas = {str(x) for x in list(estado_dungeon.get("salas_exploradas") or [])}
        if not exploradas and str(estado_dungeon.get("sala_id") or ""):
            exploradas.add(str(estado_dungeon.get("sala_id") or ""))
    mostrar_tudo = not isinstance(estado_dungeon, dict)
    surface = pygame.Surface((lado * cell, lado * cell), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 255))
    cx0, cy0 = int(centro[0]), int(centro[1])
    for dy in range(-int(raio), int(raio) + 1):
        for dx in range(-int(raio), int(raio) + 1):
            sala = salas_por_pos.get((cx0 + dx, cy0 + dy))
            lx, ly = dx + int(raio), dy + int(raio)
            rect = pygame.Rect(lx * cell, ly * cell, cell, cell)
            if not isinstance(sala, dict):
                continue
            if not mostrar_tudo and str(sala.get("id") or "") not in exploradas:
                continue
            pygame.draw.rect(surface, _CORES_DEBUG.get(str(sala.get("tipo") or ""), _CORES_DEBUG[""]), rect)
            pygame.draw.rect(surface, (235, 235, 235), rect, 1)
            ccx, ccy = rect.center
            for porta in list(sala.get("portas_info") or []):
                p = str(porta.get("direcao") or "")
                locked = bool(porta.get("trancada", False))
                cor = (255, 190, 45) if locked else (255, 255, 255)
                if p == "N":
                    pygame.draw.line(surface, cor, (ccx - 4, rect.top), (ccx + 4, rect.top), 3)
                elif p == "S":
                    pygame.draw.line(surface, cor, (ccx - 4, rect.bottom - 1), (ccx + 4, rect.bottom - 1), 3)
                elif p == "L":
                    pygame.draw.line(surface, cor, (rect.right - 1, ccy - 4), (rect.right - 1, ccy + 4), 3)
                elif p == "O":
                    pygame.draw.line(surface, cor, (rect.left, ccy - 4), (rect.left, ccy + 4), 3)
    return surface

def renderizar_dungeon(tela, camera, layout:dict):
    tile=float(getattr(camera,'TilePx',50) or 50)
    bloco = int(layout.get("tamanho_bloco_sala_tiles", 30) or 30) if isinstance(layout, dict) else 30
    bloco_w = int(layout.get("largura_bloco_sala_tiles", bloco) or bloco) if isinstance(layout, dict) else bloco
    bloco_h = int(layout.get("altura_bloco_sala_tiles", bloco) or bloco) if isinstance(layout, dict) else bloco
    parede = max(1, int(layout.get("parede_largura_tiles", 2) or 2)) if isinstance(layout, dict) else 2
    for sala in layout.get('salas',[]) if isinstance(layout,dict) else []:
        for info in list(sala.get("portas_info") or []):
            if not bool(info.get("trancada", False)):
                continue
            pos = sala.get("posicao_sala") or [0, 0]
            pr = _porta_rect(pos, str(info.get("direcao") or ""), bloco_w, bloco_h, tile, int(layout.get("porta_largura_tiles", 4) or 4), parede)
            pr.x += int(-camera.PosicaoTiles[0] * tile)
            pr.y += int(-camera.PosicaoTiles[1] * tile)
            pygame.draw.rect(tela, (58, 52, 48), pr)
            pygame.draw.rect(tela, (246, 196, 64), pr, max(1, int(tile * 0.06)))
    for ent in layout.get('entradas',[]) if isinstance(layout,dict) else []:
        saida=ent.get('saida')
        if isinstance(saida,(list,tuple)) and len(saida)==2:
            renderizar_porta(tela,camera,saida,modo='dungeon')
    estado_armadilhas = layout.get("estado_armadilhas") if isinstance(layout.get("estado_armadilhas"), dict) else {}
    traps_estado = estado_armadilhas.get("traps") if isinstance(estado_armadilhas.get("traps"), dict) else {}
    for sala in layout.get("salas", []) if isinstance(layout, dict) else []:
        cfg = sala.get("config") if isinstance(sala.get("config"), dict) else {}
        for trap in list(cfg.get("armadilhas") or []):
            if not isinstance(trap, dict):
                continue
            tid = str(trap.get("id") or "")
            estado = traps_estado.get(tid) if isinstance(traps_estado.get(tid), dict) else {}
            tipo = str(trap.get("tipo") or "")
            if tipo == "espeto":
                _desenhar_espeto(tela, camera, trap.get("posicao", [0, 0]), movel=False, escala=float((trap.get("config") or {}).get("escala", 1.0) if isinstance(trap.get("config"), dict) else 1.0))
            elif tipo == "espeto_movel":
                _desenhar_espeto(tela, camera, estado.get("posicao", trap.get("posicao", [0, 0])), movel=True)
            elif tipo == "quebradinho":
                _desenhar_quebradinho(tela, camera, trap.get("posicao", [0, 0]), fase=str(estado.get("fase") or "inteiro"))
            elif tipo == "barra_fogo":
                _desenhar_barra_fogo(tela, camera, trap, estado)
            elif tipo == "torreta":
                _desenhar_torreta(tela, camera, trap, estado)


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
