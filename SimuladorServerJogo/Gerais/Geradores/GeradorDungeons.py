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
_CATALOGO_PATH = _RAIZ / "Dados" / "Catalogo" / "Dungeon.json"
_REGRAS = carregar_regras_dungeons()

_DIRECOES = {
    "N": (0, -1),
    "S": (0, 1),
    "L": (1, 0),
    "O": (-1, 0),
}
_OPOSTA = {"N": "S", "S": "N", "L": "O", "O": "L"}


def _catalogo_default() -> dict:
    return {
        "catalogo_versao": "v1",
        "salas": [
            {"id": 1, "nome": "Entrada", "tipo": "entrada", "chance": 0.0, "dificuldade": 0},
            {"id": 2, "nome": "Sala Comum", "tipo": "comum", "chance": 1.0, "dificuldade": 1},
            {"id": 3, "nome": "Sala Pacifica", "tipo": "pacifica", "chance": 0.28, "dificuldade": 0},
            {"id": 4, "nome": "Sala Dificil", "tipo": "dificil", "chance": 0.35, "dificuldade": 3},
            {"id": 5, "nome": "Sala Piscina", "tipo": "piscina", "chance": 0.18, "dificuldade": 1},
            {"id": 6, "nome": "Sala de Boss", "tipo": "boss", "chance": 0.0, "dificuldade": 0},
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
                "chance": float(item.get("chance", 0.0) or 0.0),
                "dificuldade": int(float(item.get("dificuldade", 0) or 0)),
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
    try:
        if _CATALOGO_PATH.exists():
            return _normalizar_catalogo(json.loads(_CATALOGO_PATH.read_text(encoding="utf-8")))
    except Exception as exc:
        print(f"[Dungeons] Catalogo invalido em {_CATALOGO_PATH}: {exc}")
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
    return {
        "id": id_str,
        "id_numerico": int(id_num),
        "id_catalogo": int(cfg.get("id", id_num) or id_num),
        "tipo": tipo,
        "nome": str(nome or cfg.get("nome") or tipo.title()),
        "posicao_sala": [int(pos[0]), int(pos[1])],
        "largura_blocos": 1,
        "altura_blocos": 1,
        "chance": float(cfg.get("chance", 0.0) or 0.0),
        "dificuldade_sala": int(cfg.get("dificuldade", 0) or 0),
        "portas": [],
        "portas_bloqueadas": [],
        "portas_info": [],
        "chaves_da_sala": 0,
        "chaves_ids": [],
        "servos": [],
        **({"pokemon_boss": str(pokemon_boss)} if pokemon_boss else {}),
    }


def _dificuldade_num(valor) -> int:
    mapa = {"facil": 1, "fácil": 1, "media": 2, "média": 2, "normal": 2, "dificil": 4, "difícil": 4, "lendaria": 6, "lendária": 6}
    txt = str(valor or "").strip().lower()
    if txt in mapa:
        return mapa[txt]
    try:
        return int(float(txt))
    except (TypeError, ValueError):
        return 2


def _tipo_sala_comum(rng: random.Random, catalogo: dict | None = None, dificuldade=2) -> str:
    base = catalogo or {}
    dif = max(1, min(6, _dificuldade_num(dificuldade)))
    pesos = {}
    for tipo in ("comum", "pacifica", "dificil", "piscina"):
        cfg = base.get(tipo, {}) if isinstance(base.get(tipo, {}), dict) else {}
        peso = float(cfg.get("chance", 1.0) or 0.0)
        alvo = int(cfg.get("dificuldade", 1) or 1)
        if tipo == "dificil":
            peso *= 0.55 + (dif * 0.35)
        elif tipo == "pacifica":
            peso *= max(0.15, 1.35 - (dif * 0.18))
        else:
            peso *= max(0.35, 1.10 - abs(dif - alvo) * 0.08)
        pesos[tipo] = max(0.0, peso)
    tipos = [t for t, p in pesos.items() if p > 0.0] or ["comum"]
    return rng.choices(tipos, weights=[pesos.get(t, 1.0) for t in tipos], k=1)[0]


def _adicionar_caminho(ocupadas: dict, origem: tuple[int, int], destino: tuple[int, int], rng: random.Random, catalogo: dict, proximo_id: list[int], sala_final: dict | None = None, dificuldade=2) -> None:
    for pos in _caminho_manhattan(origem, destino, rng):
        if pos in ocupadas:
            continue
        if sala_final is not None and pos == destino:
            ocupadas[pos] = sala_final
        else:
            tipo = _tipo_sala_comum(rng, catalogo, dificuldade)
            ocupadas[pos] = _criar_sala(pos, catalogo, tipo, f"sala_{pos[0]}_{pos[1]}", proximo_id[0])
            proximo_id[0] += 1
    if destino not in ocupadas and sala_final is not None:
        ocupadas[destino] = sala_final


def _dir_entre(a: tuple[int, int], b: tuple[int, int]) -> str:
    dx, dy = int(b[0] - a[0]), int(b[1] - a[1])
    for nome, delta in _DIRECOES.items():
        if delta == (dx, dy):
            return nome
    return ""


def _edge(a: tuple[int, int], b: tuple[int, int]):
    return tuple(sorted((tuple(a), tuple(b))))


def _arvore_conexoes(ocupadas: dict, entradas_pos: list[tuple[int, int]], rng: random.Random) -> tuple[set, dict, list]:
    if not ocupadas:
        return set(), {}, []
    inicio = next((p for p in entradas_pos if p in ocupadas), next(iter(ocupadas)))
    visitados = {inicio}
    pais = {}
    ordem = [inicio]
    conexoes = set()
    fronteira = [inicio]
    while fronteira:
        atual = fronteira.pop()
        vizinhos = [v for v in _vizinhos(atual, 9999, 9999) if v in ocupadas]
        rng.shuffle(vizinhos)
        for viz in vizinhos:
            if viz in visitados:
                continue
            visitados.add(viz)
            pais[viz] = atual
            ordem.append(viz)
            conexoes.add(_edge(atual, viz))
            fronteira.append(viz)
    for pos in list(ocupadas):
        if pos in visitados:
            continue
        alvo = min(visitados, key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1]))
        pais[pos] = alvo
        ordem.append(pos)
        conexoes.add(_edge(alvo, pos))
        visitados.add(pos)
    return conexoes, pais, ordem


def _porta_id(a: tuple[int, int], b: tuple[int, int]) -> str:
    p0, p1 = sorted((tuple(a), tuple(b)))
    return f"porta_{int(p0[0])}_{int(p0[1])}_{int(p1[0])}_{int(p1[1])}"


def _elegivel_chave(sala: dict) -> bool:
    return str(sala.get("tipo") or "") in {"comum", "dificil", "piscina"} and int(sala.get("chaves_da_sala", 0) or 0) < int(_REGRAS.get("chaves_por_sala_max", 2) or 2)


def _gerar_conexoes_e_portas(ocupadas: dict, entradas_pos: list[tuple[int, int]], rng: random.Random) -> None:
    for pos, sala in ocupadas.items():
        sala["portas"] = []
        sala["portas_bloqueadas"] = []
        sala["portas_info"] = []
        sala["chaves_da_sala"] = 0
        sala["chaves_ids"] = []

    conexoes, pais, ordem = _arvore_conexoes(ocupadas, entradas_pos, rng)
    chance_extra = float(_REGRAS.get("chance_porta_extra", 0.18) or 0.18)
    for pos in list(ocupadas):
        for nome, (dx, dy) in _DIRECOES.items():
            viz = (pos[0] + dx, pos[1] + dy)
            if viz not in ocupadas or _edge(pos, viz) in conexoes:
                continue
            if str(ocupadas[pos].get("tipo")) == "boss" or str(ocupadas[viz].get("tipo")) == "boss":
                continue
            if rng.random() < chance_extra:
                conexoes.add(_edge(pos, viz))

    trancadas = set()
    visitadas_antes = set()
    for pos in ordem:
        pai = pais.get(pos)
        sala = ocupadas.get(pos, {})
        if pai is not None:
            tipo = str(sala.get("tipo") or "")
            chance_lock = float(_REGRAS.get("chance_porta_boss_trancada" if tipo == "boss" else "chance_porta_trancada", 0.24) or 0.24)
            candidatos_chave = [p for p in visitadas_antes if _elegivel_chave(ocupadas.get(p, {}))]
            if candidatos_chave and rng.random() < chance_lock:
                edge = _edge(pai, pos)
                trancadas.add(edge)
                sala_key_pos = rng.choice(candidatos_chave)
                sala_key = ocupadas[sala_key_pos]
                chave_id = f"chave_{_porta_id(pai, pos)}"
                sala_key["chaves_da_sala"] = int(sala_key.get("chaves_da_sala", 0) or 0) + 1
                sala_key.setdefault("chaves_ids", []).append(chave_id)
        visitadas_antes.add(pos)

    for a, b in sorted(conexoes):
        for origem, destino in ((a, b), (b, a)):
            sala = ocupadas.get(origem)
            if not isinstance(sala, dict):
                continue
            direcao = _dir_entre(origem, destino)
            if not direcao:
                continue
            pid = _porta_id(origem, destino)
            bloqueada = _edge(origem, destino) in trancadas
            if direcao not in sala["portas"]:
                sala["portas"].append(direcao)
            if bloqueada and direcao not in sala["portas_bloqueadas"]:
                sala["portas_bloqueadas"].append(direcao)
            sala["portas_info"].append({"id": pid, "direcao": direcao, "destino_sala_id": ocupadas[destino].get("id"), "trancada": bool(bloqueada)})


def _marcar_porta_grid(grid: list[list[int]], pos: tuple[int, int], direcao: str, tile: int) -> None:
    porta_w = max(1, int(_REGRAS.get("porta_largura_tiles", 4) or 4))
    x0 = int(pos[0]) * LARGURA_BLOCO_SALA_TILES
    y0 = int(pos[1]) * ALTURA_BLOCO_SALA_TILES
    cx = x0 + (LARGURA_BLOCO_SALA_TILES // 2)
    cy = y0 + (ALTURA_BLOCO_SALA_TILES // 2)
    meio = porta_w // 2
    pontos = []
    if direcao in {"N", "S"}:
        y = y0 if direcao == "N" else y0 + ALTURA_BLOCO_SALA_TILES - 1
        pontos = [(x, y) for x in range(cx - meio, cx - meio + porta_w)]
    elif direcao in {"L", "O"}:
        x = x0 + LARGURA_BLOCO_SALA_TILES - 1 if direcao == "L" else x0
        pontos = [(x, y) for y in range(cy - meio, cy - meio + porta_w)]
    for x, y in pontos:
        if 0 <= y < len(grid) and 0 <= x < len(grid[y]):
            grid[y][x] = int(tile)


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
    for pos, sala in ocupadas.items():
        for info in list(sala.get("portas_info") or []):
            if bool(info.get("trancada", False)):
                _marcar_porta_grid(grid, pos, str(info.get("direcao") or ""), 0)
            else:
                _marcar_porta_grid(grid, pos, str(info.get("direcao") or ""), tile_chao)
    return grid


def _gerar_servos_salas(ocupadas: dict, servos_pool: list[str], rng: random.Random) -> list[dict]:
    pool = [str(p).strip() for p in servos_pool if str(p).strip()] or ["Pokemon"]
    todos = []
    for sala in sorted(ocupadas.values(), key=lambda s: int(s.get("id_numerico", 0) or 0)):
        tipo = str(sala.get("tipo") or "")
        if tipo == "dificil":
            mn = int(_REGRAS.get("servo_dificil_min", 2) or 2)
            mx = int(_REGRAS.get("servo_dificil_max", 4) or 4)
        elif tipo in {"comum", "piscina"}:
            mn = int(_REGRAS.get("servo_comum_min", 0) or 0)
            mx = int(_REGRAS.get("servo_comum_max", 2) or 2)
        else:
            sala["servos"] = []
            continue
        chaves = list(sala.get("chaves_ids") or [])
        qtd = max(len(chaves), rng.randint(max(0, mn), max(max(0, mn), mx)))
        servos = []
        for i in range(qtd):
            uid = f"servo_{sala.get('id')}_{i+1}"
            chave_id = chaves[i] if i < len(chaves) else ""
            item = {"pokemon": rng.choice(pool), "uid": uid, "possui_chave": bool(chave_id), "chave_id": chave_id}
            servos.append(item)
            todos.append({"sala_id": sala.get("id"), **item})
        sala["servos"] = servos
    return todos


def gerar_dungeon_layout(dungeon_code: str, entradas: list[dict]) -> dict:
    row = resolver_dungeon_por_code(dungeon_code) or {}
    tamanho = max(1, min(6, _int_csv(row.get("Tamanho", 1), 1)))
    largura = altura = tamanho_em_blocos(tamanho)
    nome = str(row.get("Nome") or dungeon_code)
    dificuldade = str(row.get("Dificuldade") or "")
    dificuldade_num = _dificuldade_num(dificuldade or tamanho)
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

    entradas_pos = [tuple(e["posicao_sala"]) for e in entradas_out]
    for destino in entradas_pos[1:]:
        origem = entradas_pos[0]
        _adicionar_caminho(ocupadas, origem, destino, rng, catalogo, proximo_id, dificuldade=dificuldade_num)

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
        _adicionar_caminho(ocupadas, origem, alvo, rng, catalogo, proximo_id, sala_final=sala_boss, dificuldade=dificuldade_num)

    alvo_total = min(largura * altura, max(len(ocupadas), int(round(largura * altura * rng.uniform(0.40, 0.58)))))
    tentativas = 0
    while len(ocupadas) < alvo_total and tentativas < largura * altura * 6:
        tentativas += 1
        origem = rng.choice(list(ocupadas.keys()))
        livres = [v for v in _vizinhos(origem, largura, altura) if v not in ocupadas]
        if not livres:
            continue
        pos = rng.choice(livres)
        tipo = _tipo_sala_comum(rng, catalogo, dificuldade_num)
        ocupadas[pos] = _criar_sala(pos, catalogo, tipo, f"sala_{pos[0]}_{pos[1]}", proximo_id[0])
        proximo_id[0] += 1

    _gerar_conexoes_e_portas(ocupadas, [tuple(e["posicao_sala"]) for e in entradas_out], rng)
    servos_layout = _gerar_servos_salas(ocupadas, servos_pool, rng)

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
        "porta_largura_tiles": int(_REGRAS.get("porta_largura_tiles", 4) or 4),
        "salas": salas,
        "entradas": entradas_out,
        "grid_salas_ids": grid_ids,
        "grid_salas_tipos": grid_tipos,
        "grid_tiles": _grid_tiles(ocupadas, largura, altura),
        "bosses": bosses,
        "servos": servos_layout,
        "portas_trancadas": [
            {"sala_id": sala.get("id"), **info}
            for sala in salas
            for info in list(sala.get("portas_info") or [])
            if bool(info.get("trancada", False))
        ],
        "chaves": [
            {"sala_id": sala.get("id"), "chave_id": chave}
            for sala in salas
            for chave in list(sala.get("chaves_ids") or [])
        ],
        "servos_pool": servos_pool,
        "catalogo_versao": str(catalogo_raw.get("catalogo_versao") or "v1"),
    }
