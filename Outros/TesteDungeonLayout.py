from __future__ import annotations

import re
import sys
import os
from collections import deque
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

try:
    import pygame
except ModuleNotFoundError:
    import types

    class _Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)

        @property
        def top(self):
            return self.y

        @property
        def bottom(self):
            return self.y + self.h

        @property
        def left(self):
            return self.x

        @property
        def right(self):
            return self.x + self.w

        @property
        def center(self):
            return (self.x + self.w // 2, self.y + self.h // 2)

    class _Surface:
        def __init__(self, size, flags=0):
            self._size = tuple(size)

        def fill(self, *_args, **_kwargs):
            return None

        def get_size(self):
            return self._size

    class _Draw:
        @staticmethod
        def rect(*_args, **_kwargs):
            return None

        @staticmethod
        def line(*_args, **_kwargs):
            return None

        @staticmethod
        def circle(*_args, **_kwargs):
            return None

    pygame = types.SimpleNamespace(Surface=_Surface, Rect=_Rect, SRCALPHA=1, draw=_Draw())
    sys.modules["pygame"] = pygame

from SimuladorServerJogo.Gerais.Geradores.GeradorDungeons import carregar_catalogo_dungeons, gerar_dungeon_layout, resolver_dungeon_por_code
from Codigo.Geradores.ConstrutorDungeon import construir_surface_mapa_dungeon_local


def _lista(valor):
    return [p.strip() for p in re.split(r"[/,;|]+", str(valor or "")) if p.strip()]


def _validar_conectividade(layout):
    salas = layout.get("salas") if isinstance(layout.get("salas"), list) else []
    por_pos = {tuple(s.get("posicao_sala", [])): s for s in salas if isinstance(s, dict)}
    entradas = [tuple(e.get("posicao_sala", [])) for e in layout.get("entradas", []) if isinstance(e, dict)]
    assert entradas, "layout sem entradas"
    inicio = next((e for e in entradas if e in por_pos), None)
    assert inicio is not None, "entrada sem sala correspondente"
    fila = deque([inicio])
    vistos = {inicio}
    dirs = {"N": (0, -1), "S": (0, 1), "L": (1, 0), "O": (-1, 0)}
    while fila:
        pos = fila.popleft()
        sala = por_pos[pos]
        for porta in sala.get("portas") or []:
            dx, dy = dirs[str(porta)]
            prox = (pos[0] + dx, pos[1] + dy)
            if prox in por_pos and prox not in vistos:
                vistos.add(prox)
                fila.append(prox)
    assert len(vistos) == len(por_pos), f"salas inalcancaveis: {len(por_pos) - len(vistos)}"


def _validar_piscina(layout, sala):
    bloco_w = int(layout.get("largura_bloco_sala_tiles") or 34)
    bloco_h = int(layout.get("altura_bloco_sala_tiles") or 22)
    tile_agua = int(layout.get("tile_agua_funda", 0) or 0)
    pos = sala.get("posicao_sala")
    cx = int(pos[0]) * bloco_w + bloco_w // 2
    cy = int(pos[1]) * bloco_h + bloco_h // 2
    assert int(layout["grid_tiles"][cy][cx]) == tile_agua, "sala piscina sem agua funda no centro"


def validar(code):
    row = resolver_dungeon_por_code(str(code)) or {}
    layout = gerar_dungeon_layout(str(code), [{"porta_idx": 1, "pedra_id": 0}])
    bosses_csv = _lista(row.get("Pokemons"))
    bosses_layout = list(layout.get("bosses") or [])
    entradas = list(layout.get("entradas") or [])
    grid_ids = layout.get("grid_salas_ids")
    grid_tiles = layout.get("grid_tiles")
    largura = int(layout.get("largura_blocos") or 0)
    altura = int(layout.get("altura_blocos") or 0)
    bloco_w = int(layout.get("largura_bloco_sala_tiles") or 34)
    bloco_h = int(layout.get("altura_bloco_sala_tiles") or 22)
    margem = int(layout.get("margem_blocos") or 0)

    assert bloco_w == 34 and bloco_h == 22, "bloco da sala deve ser 34x22"
    assert margem == 1, "layout deve ter margem de 1 bloco"
    assert largura == int(layout.get("largura_blocos_jogaveis") or 0) + 2, "largura total nao inclui margem esperada"
    assert altura == int(layout.get("altura_blocos_jogaveis") or 0) + 2, "altura total nao inclui margem esperada"
    assert len(bosses_layout) == len(bosses_csv), f"bosses esperados={len(bosses_csv)} gerados={len(bosses_layout)}"
    assert entradas, "sem entradas"
    assert isinstance(grid_ids, list) and len(grid_ids) == altura and all(len(r) == largura for r in grid_ids), "grid_salas_ids com dimensoes incorretas"
    assert isinstance(grid_tiles, list) and len(grid_tiles) == altura * bloco_h and all(len(r) == largura * bloco_w for r in grid_tiles), "grid_tiles com dimensoes incorretas"
    for sala in layout.get("salas") or []:
        tipo = str(sala.get("tipo") or "")
        servos = list(sala.get("servos") or [])
        chaves = int(sala.get("chaves_da_sala", 0) or 0)
        if tipo in {"entrada", "pacifica", "boss"}:
            assert not servos and chaves == 0, f"sala {tipo} nao pode ter servo/chave"
        if tipo == "comum":
            assert 0 <= len(servos) <= 2, "sala comum fora da faixa 0..2 servos"
        if tipo == "dificil":
            assert 2 <= len(servos) <= 4, "sala dificil fora da faixa 2..4 servos"
        assert sum(1 for s in servos if s.get("possui_chave")) == chaves, "quantidade de chaves nao bate com servos-chave"
        if tipo == "piscina":
            _validar_piscina(layout, sala)
    dist_min = 3
    for boss in bosses_layout:
        sala = next((s for s in layout.get("salas") or [] if str(s.get("id") or "") == str(boss.get("sala_id") or "")), None)
        if not isinstance(sala, dict):
            continue
        pos = tuple(sala.get("posicao_sala") or [])
        if pos and entradas:
            dist = min(abs(pos[0] - int(e.get("posicao_sala", [0, 0])[0])) + abs(pos[1] - int(e.get("posicao_sala", [0, 0])[1])) for e in entradas)
            assert dist >= min(dist_min, max(largura, altura) - 3), "boss ficou perto demais da entrada"
    assert len(layout.get("chaves") or []) >= len({p.get("id") for p in layout.get("portas_trancadas") or [] if p.get("trancada")}) or not layout.get("portas_trancadas"), "porta trancada sem chave gerada"
    _validar_conectividade(layout)
    estado = {"salas_exploradas": [str(entradas[0].get("sala_id") or "")], "sala_posicao": list(entradas[0].get("posicao_sala") or [])}
    surface = construir_surface_mapa_dungeon_local(layout, estado, cell=16, raio=1)
    assert surface is not None and surface.get_size() == (48, 48), "mapa local 3x3 nao foi criado corretamente"
    print(f"Code {code}: {largura}x{altura} blocos, salas={len(layout.get('salas') or [])}, bosses={len(bosses_layout)}, entradas={len(entradas)}")
    return layout


def main():
    catalogo = carregar_catalogo_dungeons()
    tipos = {str(s.get("tipo") or "") for s in catalogo.get("salas", []) if isinstance(s, dict)}
    assert "escura" in tipos, "catalogo sem sala escura"
    viu_piscina = False
    for code in (30, 19, 1):
        layout = validar(code)
        viu_piscina = viu_piscina or any(str(s.get("tipo") or "") == "piscina" for s in layout.get("salas") or [])
    assert viu_piscina, "nenhum layout de teste gerou sala piscina"
    print("Layouts de dungeon OK")


if __name__ == "__main__":
    main()
