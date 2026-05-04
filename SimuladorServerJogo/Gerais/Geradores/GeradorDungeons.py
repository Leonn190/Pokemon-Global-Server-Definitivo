from __future__ import annotations

import hashlib
import json
import random
import re
from collections import deque
from pathlib import Path

from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_dungeons
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.DungeonGeometria import (
    ALTURA_BLOCO_SALA_TILES,
    LARGURA_BLOCO_SALA_TILES,
    TAMANHO_BLOCO_SALA_TILES,
    centro_sala_em_tiles,
    nome_dimensao_dungeon,
    posicao_sala_entrada,
    saida_sala_entrada,
    spawn_interno_entrada,
    tamanho_em_blocos,
)


_RAIZ = Path(__file__).resolve().parents[3]
_CATALOGO_PATH = _RAIZ / "Dados" / "Catalogos" / "Dungeon.json"
_CATALOGO_LEGADO_PATH = _RAIZ / "Dados" / "Catalogo" / "Dungeon.json"
_REGRAS = carregar_regras_dungeons()

_DIRECOES = {
    "N": (0, -1),
    "S": (0, 1),
    "L": (1, 0),
    "O": (-1, 0),
}


def _catalogo_default() -> dict:
    return {
        "catalogo_versao": "v1",
        "salas": [
            {"id": 1, "nome": "Entrada", "tipo": "entrada", "servo_rate": 0.0, "servo_max": 0, "bau_rate": 0.0},
            {"id": 2, "nome": "Sala Comum", "tipo": "comum", "servo_rate": 0.004, "servo_max": 1, "bau_rate": 0.0},
            {"id": 3, "nome": "Sala Pacifica", "tipo": "pacifica", "servo_rate": 0.0, "servo_max": 0, "bau_rate": 0.0},
            {"id": 4, "nome": "Sala Dificil", "tipo": "dificil", "servo_rate": 0.012, "servo_max": 2, "bau_rate": 0.0},
            {"id": 5, "nome": "Sala Piscina", "tipo": "piscina", "servo_rate": 0.003, "servo_max": 1, "bau_rate": 0.0},
            {"id": 6, "nome": "Sala de Boss", "tipo": "boss", "servo_rate": 0.0, "servo_max": 0, "bau_rate": 0.0},
        ],
    }


def _normalizar_catalogo(data: dict) -> dict:
    bruto = data.get("salas") if isinstance(data.get("salas"), (list, dict)) else data
    salas = []
    if isinstance(bruto, dict):
        iter_salas = bruto.values()
    else:
        iter_salas = bruto if isinstance(bruto, list) else []
    for item in iter_salas:
        if not isinstance(item, dict):
            continue
        tipo = str(item.get("tipo") or item.get("id") or "").strip().lower()
        if not tipo:
            continue
        try:
            id_catalogo = int(item.get("id", item.get("id_catalogo", len(salas) + 1)) or (len(salas) + 1))
        except (TypeError, ValueError):
            id_catalogo = len(salas) + 1
        salas.append(
            {
                "id": id_catalogo,
                "nome": str(item.get("nome") or item.get("Nome") or tipo.title()),
                "tipo": tipo,
                "servo_rate": float(item.get("servo_rate", 0.0) or 0.0),
                "servo_max": int(float(item.get("servo_max", 0) or 0)),
                "bau_rate": float(item.get("bau_rate", 0.0) or 0.0),
            }
        )
    if not salas:
        return _catalogo_default()
    tipos = {s["tipo"] for s in salas}
    for sala in _catalogo_default()["salas"]:
        if sala["tipo"] not in tipos:
            salas.append(dict(sala))
    return {"catalogo_versao": str(data.get("catalogo_versao") or "v1"), "salas": salas}


def carregar_catalogo_dungeons() -> dict:
    for path in (_CATALOGO_PATH, _CATALOGO_LEGADO_PATH):
        try:
            if path.exists():
                return _normalizar_catalogo(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"[Dungeons] Catalogo invalido em {path}: {exc}")
    return _catalogo_default()


def _catalogo_por_tipo(catalogo: dict) -> dict[str, dict]:
    return {str(s.get("tipo") or "").strip().lower(): dict(s) for s in catalogo.get("salas", []) if isinstance(s, dict)}


def _dungeons_csv():
    return carregar_csv_dict("Pokemon Global Server - Dungeons.csv")


def _lista_csv(valor) -> list[str]:
    return [p.strip() for p in re.split(r"[/,;|]+", str(valor or "")) if p.strip()]


def _int_csv(valor, default=1) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _coletar_entradas_dungeon_no_banco(dungeon_code: str) -> list[dict]:
    entradas_reais = []
    vistos = set()
    for obj in BANCO_DADOS.listar_objetos():
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        if str(estado.get("subtipo") or "").lower() != "dungeon":
            continue
        if str(estado.get("dungeon_code") or "").strip().lower() != str(dungeon_code).strip().lower():
            continue
        porta_idx = int(estado.get("porta_idx", len(entradas_reais) + 1) or len(entradas_reais) + 1)
        entradas_reais.append({"porta_idx": porta_idx, "pedra_id": int(getattr(obj, "Id", 0) or 0)})
        vistos.add(porta_idx)
    for item in BANCO_DADOS.listar_dungeons_registradas():
        if str(item.get("dungeon_code") or "").strip().lower() != str(dungeon_code).strip().lower():
            continue
        porta_idx = int(item.get("porta_idx", len(entradas_reais) + 1) or len(entradas_reais) + 1)
        if porta_idx in vistos:
            continue
        entradas_reais.append({"porta_idx": porta_idx, "pedra_id": int(item.get("pedra_id", 0) or 0)})
        vistos.add(porta_idx)
    entradas_reais.sort(key=lambda e: int(e.get("porta_idx", 0) or 0))
    return entradas_reais


def resolver_dungeon_por_code(code: str) -> dict | None:
    alvo = str(code or "").strip().lower()
    for row in _dungeons_csv():
        if str(row.get("Code") or "").strip().lower() == alvo:
            return row
    return None


def _seed_layout(dungeon_code: str, row: dict, entradas: list[dict]) -> int:
    bruto = json.dumps(
        {
            "code": str(dungeon_code),
            "nome": row.get("Nome", ""),
            "pokemons": row.get("Pokemons", ""),
            "servos": row.get("Servos", ""),
            "tamanho": row.get("Tamanho", ""),
            "entradas": [int(e.get("porta_idx", 0) or 0) for e in entradas],
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return int(hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16], 16)


def _livre(pos: tuple[int, int], ocupadas: dict, largura: int, altura: int) -> bool:
    return 0 <= pos[0] < largura and 0 <= pos[1] < altura and pos not in ocupadas


def _vizinhos(pos: tuple[int, int], largura: int, altura: int):
    x, y = pos
    for dx, dy in _DIRECOES.values():
        nx, ny = x + dx, y + dy
        if 0 <= nx < largura and 0 <= ny < altura:
            yield (nx, ny)


def _proxima_posicao_livre(pos: tuple[int, int], ocupadas: dict, largura: int, altura: int) -> tuple[int, int] | None:
    if _livre(pos, ocupadas, largura, altura):
        return pos
    fila = deque([pos])
    vistos = {pos}
    while fila:
        atual = fila.popleft()
        for viz in _vizinhos(atual, largura, altura):
            if viz in vistos:
                continue
            if _livre(viz, ocupadas, largura, altura):
                return viz
            vistos.add(viz)
            fila.append(viz)
    return None


def _caminho_manhattan(origem: tuple[int, int], destino: tuple[int, int], rng: random.Random) -> list[tuple[int, int]]:
    x, y = origem
    tx, ty = destino
    caminho = []
    while (x, y) != (tx, ty):
        opcoes = []
        if x < tx:
            opcoes.append((x + 1, y))
        elif x > tx:
            opcoes.append((x - 1, y))
        if y < ty:
            opcoes.append((x, y + 1))
        elif y > ty:
            opcoes.append((x, y - 1))
        x, y = rng.choice(opcoes)
        caminho.append((x, y))
    return caminho


def _slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(nome or "").strip().lower()).strip("_") or "boss"


def _criar_sala(pos: tuple[int, int], catalogo: dict, tipo: str, id_str: str, id_num: int, nome: str | None = None, pokemon_boss: str = "") -> dict:
    cfg = dict(catalogo.get(tipo) or catalogo.get("comum") or {})
    if tipo == "boss":
        cfg.update({"servo_rate": 0.0, "servo_max": 0, "bau_rate": 0.0})
    return {
        "id": id_str,
        "id_numerico": int(id_num),
        "id_catalogo": int(cfg.get("id", id_num) or id_num),
        "tipo": tipo,
        "nome": str(nome or cfg.get("nome") or tipo.title()),
        "posicao_sala": [int(pos[0]), int(pos[1])],
        "largura_blocos": 1,
        "altura_blocos": 1,
        "servo_rate": float(cfg.get("servo_rate", 0.0) or 0.0),
        "servo_max": int(cfg.get("servo_max", 0) or 0),
        "bau_rate": float(cfg.get("bau_rate", 0.0) or 0.0),
        "portas": [],
        "portas_bloqueadas": [],
        **({"pokemon_boss": str(pokemon_boss)} if pokemon_boss else {}),
    }


def _tipo_sala_comum(rng: random.Random) -> str:
    return rng.choices(["comum", "pacifica", "dificil", "piscina"], weights=[62, 14, 16, 8], k=1)[0]


def _adicionar_caminho(ocupadas: dict, origem: tuple[int, int], destino: tuple[int, int], rng: random.Random, catalogo: dict, proximo_id: list[int], sala_final: dict | None = None) -> None:
    for pos in _caminho_manhattan(origem, destino, rng):
        if pos in ocupadas:
            continue
        if sala_final is not None and pos == destino:
            ocupadas[pos] = sala_final
        else:
            tipo = _tipo_sala_comum(rng)
            ocupadas[pos] = _criar_sala(pos, catalogo, tipo, f"sala_{pos[0]}_{pos[1]}", proximo_id[0])
            proximo_id[0] += 1
    if destino not in ocupadas and sala_final is not None:
        ocupadas[destino] = sala_final


def _portas_por_sala(ocupadas: dict) -> None:
    for pos, sala in ocupadas.items():
        portas = []
        for nome, (dx, dy) in _DIRECOES.items():
            if (pos[0] + dx, pos[1] + dy) in ocupadas:
                portas.append(nome)
        sala["portas"] = portas
        sala["portas_bloqueadas"] = []


def _grid_tiles(ocupadas: dict, largura: int, altura: int) -> list[list[int]]:
    tile_chao = int(_REGRAS.get("tile_chao_dungeon", 8) or 8)
    tile_agua = int(_REGRAS.get("tile_agua_funda", 0) or 0)
    largura_tiles = largura * LARGURA_BLOCO_SALA_TILES
    altura_tiles = altura * ALTURA_BLOCO_SALA_TILES
    grid = [[0 for _ in range(largura_tiles)] for _ in range(altura_tiles)]
    for (bx, by), sala in ocupadas.items():
        x0 = bx * LARGURA_BLOCO_SALA_TILES
        y0 = by * ALTURA_BLOCO_SALA_TILES
        for y in range(y0, y0 + ALTURA_BLOCO_SALA_TILES):
            for x in range(x0, x0 + LARGURA_BLOCO_SALA_TILES):
                grid[y][x] = tile_chao
        if str(sala.get("tipo")) == "piscina":
            margem_x = max(5, LARGURA_BLOCO_SALA_TILES // 4)
            margem_y = max(4, ALTURA_BLOCO_SALA_TILES // 4)
            for y in range(y0 + margem_y, y0 + ALTURA_BLOCO_SALA_TILES - margem_y):
                for x in range(x0 + margem_x, x0 + LARGURA_BLOCO_SALA_TILES - margem_x):
                    grid[y][x] = tile_agua
    return grid


def gerar_dungeon_layout(dungeon_code: str, entradas: list[dict]) -> dict:
    row = resolver_dungeon_por_code(dungeon_code) or {}
    tamanho = max(1, min(6, _int_csv(row.get("Tamanho", 1), 1)))
    largura = altura = tamanho_em_blocos(tamanho)
    nome = str(row.get("Nome") or dungeon_code)
    dificuldade = str(row.get("Dificuldade") or "")
    bosses_nomes = _lista_csv(row.get("Pokemons"))
    servos_pool = _lista_csv(row.get("Servos"))

    entradas_reais = _coletar_entradas_dungeon_no_banco(dungeon_code) or list(entradas or [])
    if not entradas_reais:
        qtd_csv = max(1, _int_csv(row.get("Entradas", 1), 1))
        entradas_reais = [{"porta_idx": i, "pedra_id": 0} for i in range(1, qtd_csv + 1)]

    catalogo_raw = carregar_catalogo_dungeons()
    catalogo = _catalogo_por_tipo(catalogo_raw)
    rng = random.Random(_seed_layout(str(dungeon_code), row, entradas_reais))

    ocupadas: dict[tuple[int, int], dict] = {}
    entradas_out = []
    proximo_id = [1]

    for i, entrada in enumerate(entradas_reais, start=1):
        porta_idx = int(entrada.get("porta_idx", i) or i)
        pos = _proxima_posicao_livre(posicao_sala_entrada(porta_idx, tamanho), ocupadas, largura, altura)
        if pos is None:
            continue
        sala = _criar_sala(pos, catalogo, "entrada", f"entrada_{porta_idx}", proximo_id[0], "Entrada")
        proximo_id[0] += 1
        ocupadas[pos] = sala
        entradas_out.append(
            {
                "porta_idx": porta_idx,
                "sala_id": sala["id"],
                "posicao_sala": [pos[0], pos[1]],
                "spawn": spawn_interno_entrada(pos),
                "saida": saida_sala_entrada(pos),
                "pedra_id": int(entrada.get("pedra_id", 0) or 0),
            }
        )

    if not ocupadas:
        pos = (0, 0)
        sala = _criar_sala(pos, catalogo, "entrada", "entrada_1", proximo_id[0], "Entrada")
        proximo_id[0] += 1
        ocupadas[pos] = sala
        entradas_out.append({"porta_idx": 1, "sala_id": sala["id"], "posicao_sala": [0, 0], "spawn": spawn_interno_entrada(pos), "saida": saida_sala_entrada(pos), "pedra_id": 0})

    for boss in bosses_nomes:
        candidatos = [(x, y) for y in range(altura) for x in range(largura) if (x, y) not in ocupadas]
        if not candidatos:
            break
        entradas_pos = [tuple(e["posicao_sala"]) for e in entradas_out]
        candidatos.sort(key=lambda p: min(abs(p[0] - e[0]) + abs(p[1] - e[1]) for e in entradas_pos), reverse=True)
        alvo = rng.choice(candidatos[: max(1, min(6, len(candidatos)))])
        origem = min(ocupadas.keys(), key=lambda p: abs(p[0] - alvo[0]) + abs(p[1] - alvo[1]))
        sala_boss = _criar_sala(alvo, catalogo, "boss", f"boss_{_slug(boss)}", proximo_id[0], f"Sala de Boss - {boss}", boss)
        proximo_id[0] += 1
        _adicionar_caminho(ocupadas, origem, alvo, rng, catalogo, proximo_id, sala_final=sala_boss)

    alvo_total = min(largura * altura, max(len(ocupadas), int(round(largura * altura * rng.uniform(0.40, 0.58)))))
    tentativas = 0
    while len(ocupadas) < alvo_total and tentativas < largura * altura * 6:
        tentativas += 1
        origem = rng.choice(list(ocupadas.keys()))
        livres = [v for v in _vizinhos(origem, largura, altura) if v not in ocupadas]
        if not livres:
            continue
        pos = rng.choice(livres)
        tipo = _tipo_sala_comum(rng)
        ocupadas[pos] = _criar_sala(pos, catalogo, tipo, f"sala_{pos[0]}_{pos[1]}", proximo_id[0])
        proximo_id[0] += 1

    _portas_por_sala(ocupadas)

    grid_ids = [[0 for _ in range(largura)] for _ in range(altura)]
    grid_tipos = [["" for _ in range(largura)] for _ in range(altura)]
    for (x, y), sala in ocupadas.items():
        grid_ids[y][x] = int(sala.get("id_numerico", 0) or 0)
        grid_tipos[y][x] = str(sala.get("tipo") or "")

    salas = sorted(ocupadas.values(), key=lambda s: int(s.get("id_numerico", 0) or 0))
    bosses = []
    for sala in salas:
        if str(sala.get("tipo")) != "boss":
            continue
        boss = str(sala.get("pokemon_boss") or "")
        bosses.append({"pokemon": boss, "sala_id": sala.get("id"), "posicao": centro_sala_em_tiles(sala.get("posicao_sala", [0, 0]))})

    return {
        "dimensao": nome_dimensao_dungeon(dungeon_code),
        "dungeon_code": str(dungeon_code),
        "dungeon_nome": nome,
        "tamanho": tamanho,
        "dificuldade": dificuldade,
        "largura_blocos": largura,
        "altura_blocos": altura,
        "tamanho_bloco_sala_tiles": TAMANHO_BLOCO_SALA_TILES,
        "largura_bloco_sala_tiles": LARGURA_BLOCO_SALA_TILES,
        "altura_bloco_sala_tiles": ALTURA_BLOCO_SALA_TILES,
        "salas": salas,
        "entradas": entradas_out,
        "grid_salas_ids": grid_ids,
        "grid_salas_tipos": grid_tipos,
        "grid_tiles": _grid_tiles(ocupadas, largura, altura),
        "bosses": bosses,
        "servos_pool": servos_pool,
        "catalogo_versao": str(catalogo_raw.get("catalogo_versao") or "v1"),
    }
