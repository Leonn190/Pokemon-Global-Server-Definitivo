from __future__ import annotations

import re
import sys
from collections import deque
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from SimuladorServerJogo.Gerais.Geradores.GeradorDungeons import gerar_dungeon_layout, resolver_dungeon_por_code


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
    bloco_w = int(layout.get("largura_bloco_sala_tiles") or 32)
    bloco_h = int(layout.get("altura_bloco_sala_tiles") or 24)

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
    assert len(layout.get("chaves") or []) >= len({p.get("id") for p in layout.get("portas_trancadas") or [] if p.get("trancada")}) or not layout.get("portas_trancadas"), "porta trancada sem chave gerada"
    _validar_conectividade(layout)
    print(f"Code {code}: {largura}x{altura} blocos, salas={len(layout.get('salas') or [])}, bosses={len(bosses_layout)}, entradas={len(entradas)}")


def main():
    for code in (30, 19, 1):
        validar(code)
    print("Layouts de dungeon OK")


if __name__ == "__main__":
    main()
