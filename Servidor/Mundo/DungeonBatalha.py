from __future__ import annotations


def contexto_batalha_dungeon(layout: dict, sala: dict | None, tipo_batalha: str, estado_pokemon: dict | None = None, base: dict | None = None) -> dict:
    contexto = dict(base or {})
    layout = layout if isinstance(layout, dict) else {}
    sala = sala if isinstance(sala, dict) else {}
    estado_pokemon = estado_pokemon if isinstance(estado_pokemon, dict) else {}
    bloco = int(layout.get("tamanho_bloco_sala_tiles", 34) or 34)
    bloco_w = int(layout.get("largura_bloco_sala_tiles", bloco) or bloco)
    bloco_h = int(layout.get("altura_bloco_sala_tiles", bloco) or bloco)
    largura = max(int(contexto.get("largura", 80) or 80), bloco_w)
    altura = max(int(contexto.get("altura", 40) or 40), bloco_h)
    pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) and len(sala.get("posicao_sala")) == 2 else estado_pokemon.get("sala_posicao", [0, 0])
    sx, sy = int(pos[0]), int(pos[1])
    x0, y0 = sx * bloco_w, sy * bloco_h
    off_x, off_y = max(0, (largura - bloco_w) // 2), max(0, (altura - bloco_h) // 2)
    grid = layout.get("grid_tiles") if isinstance(layout.get("grid_tiles"), list) else []
    tile_chao = int(layout.get("tile_chao_dungeon", 8) or 8)
    tiles = []
    for ly in range(bloco_h):
        gy = y0 + ly
        for lx in range(bloco_w):
            tiles.append({"x": int(off_x + lx), "y": int(off_y + ly), "bloco": tile_chao})
    tipo_sala = str(sala.get("tipo") or "")
    contexto.update(
        {
            "tipo_dimensao": "dungeon",
            "contexto_dungeon": True,
            "dungeon_code": str(layout.get("dungeon_code") or estado_pokemon.get("dungeon_code") or ""),
            "dungeon_nome": str(layout.get("dungeon_nome") or ""),
            "sala_id": str(sala.get("id") or estado_pokemon.get("sala_id") or ""),
            "tipo_sala": tipo_sala,
            "sala_posicao": [sx, sy],
            "sala_escura": tipo_sala == "escura",
            "darkness_bonus": 0.18 if tipo_sala == "escura" else 0.0,
            "tipo": str(tipo_batalha or ""),
            "tipo_batalha": str(tipo_batalha or ""),
            "largura": int(largura),
            "altura": int(altura),
            "centro": [float(largura) * 0.5, float(altura) * 0.5],
            "origem": [x0 - off_x, y0 - off_y],
            "tiles": tiles,
            "estruturas": [],
        }
    )
    return contexto
