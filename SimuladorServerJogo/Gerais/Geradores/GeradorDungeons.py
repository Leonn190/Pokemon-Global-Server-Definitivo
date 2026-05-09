from __future__ import annotations

import hashlib
import json
import math
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
            {"id": 7, "nome": "Sala Escura", "tipo": "escura", "chance": 0.20, "dificuldade": 2},
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
    por_porta = {}
    for obj in BANCO_DADOS.listar_objetos():
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        if str(estado.get("subtipo") or "").lower() != "dungeon":
            continue
        if str(estado.get("dungeon_code") or "").strip().lower() != str(dungeon_code).strip().lower():
            continue
        porta_idx = int(estado.get("porta_idx", len(entradas_reais) + 1) or len(entradas_reais) + 1)
        ativa = bool(estado.get("porta_ativa", False) or estado.get("estrutura_quebrada", False))
        por_porta[porta_idx] = {
            "porta_idx": porta_idx,
            "pedra_id": int(getattr(obj, "Id", 0) or 0),
            "ativa": ativa,
            "estrutura_quebrada": bool(estado.get("estrutura_quebrada", False)),
        }
    for item in BANCO_DADOS.listar_dungeons_registradas():
        if str(item.get("dungeon_code") or "").strip().lower() != str(dungeon_code).strip().lower():
            continue
        try:
            qtd_restante = int(item.get("quantidade_restante", -1))
        except (TypeError, ValueError):
            qtd_restante = -1
        porta_idx = int(item.get("porta_idx", len(por_porta) + 1) or len(por_porta) + 1)
        ativa = qtd_restante == 0
        existente = por_porta.get(porta_idx)
        if existente is not None:
            existente["ativa"] = bool(existente.get("ativa", False) or ativa)
            if not int(existente.get("pedra_id", 0) or 0):
                existente["pedra_id"] = int(item.get("pedra_id", 0) or 0)
            continue
        por_porta[porta_idx] = {
            "porta_idx": porta_idx,
            "pedra_id": int(item.get("pedra_id", 0) or 0),
            "ativa": ativa,
            "estrutura_quebrada": ativa,
        }
    entradas_reais = list(por_porta.values())
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
            "seed_mundo": int(getattr(BANCO_DADOS, "_seed_mundo", 0) or 0),
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


def _dentro_jogavel(pos: tuple[int, int], largura: int, altura: int, margem: int) -> bool:
    m = max(0, int(margem or 0))
    return m <= int(pos[0]) < int(largura) - m and m <= int(pos[1]) < int(altura) - m


def _proxima_posicao_livre_jogavel(pos: tuple[int, int], ocupadas: dict, largura: int, altura: int, margem: int) -> tuple[int, int] | None:
    if _livre(pos, ocupadas, largura, altura) and _dentro_jogavel(pos, largura, altura, margem):
        return pos
    fila = deque([pos])
    vistos = {pos}
    while fila:
        atual = fila.popleft()
        for viz in _vizinhos(atual, largura, altura):
            if viz in vistos:
                continue
            if _livre(viz, ocupadas, largura, altura) and _dentro_jogavel(viz, largura, altura, margem):
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


def _config_sala_vazia() -> dict:
    return {
        "servos": [],
        "armadilhas": [],
        "claridade": 10,
        "piscina": None,
        "buracao": None,
        "passagens": {},
        "passagens_trancadas": [],
    }


def _criar_sala(pos: tuple[int, int], catalogo: dict, tipo: str, id_str: str, id_num: int, nome: str | None = None, pokemon_boss: str = "") -> dict:
    cfg = dict(catalogo.get(tipo) or catalogo.get("comum") or {})
    tipo_publico = "normal" if tipo in {"comum", "pacifica", "dificil", "piscina", "escura"} else tipo
    return {
        "id": id_str,
        "id_numerico": int(id_num),
        "id_catalogo": int(cfg.get("id", id_num) or id_num),
        "tipo": tipo_publico,
        "subtipo_procedural": tipo,
        "nome": str(nome or cfg.get("nome") or tipo.title()),
        "posicao_sala": [int(pos[0]), int(pos[1])],
        "largura_blocos": 1,
        "altura_blocos": 1,
        "chance": float(cfg.get("chance", 0.0) or 0.0),
        "dificuldade_sala": int(cfg.get("dificuldade", 0) or 0),
        "config": _config_sala_vazia(),
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
    for tipo in ("comum", "pacifica", "dificil", "piscina", "escura"):
        cfg = base.get(tipo, {}) if isinstance(base.get(tipo, {}), dict) else {}
        peso = float(cfg.get("chance", 1.0) or 0.0)
        alvo = int(cfg.get("dificuldade", 1) or 1)
        if tipo == "dificil":
            peso *= 0.55 + (dif * 0.35)
        elif tipo == "pacifica":
            peso *= max(0.15, 1.35 - (dif * 0.18))
        elif tipo == "escura":
            peso *= 0.75 + (dif * 0.12)
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
    return str(sala.get("tipo") or "") == "normal" and int(sala.get("chaves_da_sala", 0) or 0) < int(_REGRAS.get("chaves_por_sala_max", 2) or 2)


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
            tipo_pai = str(ocupadas.get(pai, {}).get("tipo") or "")
            chance_lock = float(_REGRAS.get("chance_porta_boss_trancada" if tipo == "boss" else "chance_porta_trancada", 0.24) or 0.24)
            candidatos_chave = [p for p in visitadas_antes if _elegivel_chave(ocupadas.get(p, {}))]
            if tipo != "entrada" and tipo_pai != "entrada" and candidatos_chave and rng.random() < chance_lock:
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
    for sala in ocupadas.values():
        cfg = sala.setdefault("config", _config_sala_vazia())
        cfg["passagens"] = {
            str(info.get("direcao") or ""): {
                "porta_id": str(info.get("id") or ""),
                "destino_sala_id": str(info.get("destino_sala_id") or ""),
                "trancada": bool(info.get("trancada", False)),
            }
            for info in list(sala.get("portas_info") or [])
            if str(info.get("direcao") or "")
        }
        cfg["passagens_trancadas"] = [
            str(info.get("id") or "")
            for info in list(sala.get("portas_info") or [])
            if bool(info.get("trancada", False))
        ]


def _rng_sala(seed_layout: int, sala_id: str, sal: str = "") -> random.Random:
    bruto = f"{int(seed_layout)}:{sala_id}:{sal}"
    return random.Random(int(hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16], 16))


def _dificuldade_sala(rng: random.Random, dificuldade_dungeon: int, tipo: str) -> int:
    dif = max(1, min(6, int(dificuldade_dungeon or 2)))
    leve = rng.random() < max(0.12, 0.34 - dif * 0.025)
    if leve:
        return max(0, min(3, rng.randint(0, 1 + dif // 3)))
    base = rng.triangular(0.0, 6.0, float(dif))
    if tipo == "boss":
        base += 0.5
    return max(0, min(6, int(round(base))))


def _retangulo_interno_sala(pos: tuple[int, int], margem_extra: int = 0) -> tuple[int, int, int, int]:
    parede = max(1, int(_REGRAS.get("parede_largura_tiles", 2) or 2))
    margem = parede + max(0, int(margem_extra))
    x0 = int(pos[0]) * LARGURA_BLOCO_SALA_TILES + margem
    y0 = int(pos[1]) * ALTURA_BLOCO_SALA_TILES + margem
    x1 = (int(pos[0]) + 1) * LARGURA_BLOCO_SALA_TILES - margem - 1
    y1 = (int(pos[1]) + 1) * ALTURA_BLOCO_SALA_TILES - margem - 1
    return x0, y0, max(x0, x1), max(y0, y1)


def _posicao_interna(rng: random.Random, pos_sala: tuple[int, int], ocupados: set[tuple[int, int]], margem_extra: int = 1) -> list[float]:
    x0, y0, x1, y1 = _retangulo_interno_sala(pos_sala, margem_extra=margem_extra)
    for _ in range(80):
        x = rng.randint(x0, x1)
        y = rng.randint(y0, y1)
        if (x, y) in ocupados:
            continue
        ocupados.add((x, y))
        return [float(x) + 0.5, float(y) + 0.5]
    return [float((x0 + x1) * 0.5), float((y0 + y1) * 0.5)]


def _nivel_servo(rng: random.Random, dificuldade_dungeon: int, dificuldade_sala: int) -> int:
    base = 4 + max(1, int(dificuldade_dungeon or 1)) * 5 + max(0, int(dificuldade_sala or 0)) * 4
    variacao = rng.randint(-3, 5)
    return max(2, min(100, int(base + variacao)))


def _gerar_armadilha(sala: dict, idx: int, rng: random.Random, dificuldade_sala: int, ocupados: set[tuple[int, int]]) -> dict:
    pos_sala = tuple(sala.get("posicao_sala", [0, 0]))
    dif = max(0, min(6, int(dificuldade_sala or 0)))
    tipos = ["espeto", "quebradinho"]
    pesos = [1.4, 1.1]
    if dif >= 2:
        tipos.extend(["espeto_movel", "barra_fogo"])
        pesos.extend([0.75 + dif * 0.12, 0.55 + dif * 0.13])
    if dif >= 3:
        tipos.extend(["torreta", "espeto_ricochete"])
        pesos.extend([0.35 + dif * 0.14, 0.45 + dif * 0.11])
    tipo = rng.choices(tipos, weights=pesos, k=1)[0]
    tid = f"trap_{pos_sala[0]}_{pos_sala[1]}_{idx}"
    pos = _posicao_interna(rng, pos_sala, ocupados, margem_extra=3)
    cfg: dict[str, object] = {"seed": int(rng.randrange(1 << 30))}
    if tipo == "espeto":
        cfg["escala"] = round(rng.uniform(1.65, 2.20), 3)
        cfg["raio_dano"] = round(0.58 * float(cfg["escala"]), 3)
        cfg["raio_colisao"] = round(0.48 * float(cfg["escala"]), 3)
        cfg["solido"] = True
    elif tipo == "espeto_movel":
        ang = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        cfg.update({"direcao": [ang[0], ang[1]], "velocidade": round(2.1 + dif * 0.34 + rng.random() * 0.55, 3), "escala": round(rng.uniform(1.08, 1.34), 3), "raio_dano": 0.50, "solido": False, "limites_sala": list(_retangulo_interno_sala(pos_sala, margem_extra=3))})
    elif tipo == "espeto_ricochete":
        ang = rng.random() * math.tau
        cfg.update({"direcao": [round(math.cos(ang), 4), round(math.sin(ang), 4)], "velocidade": round(2.3 + dif * 0.30 + rng.random() * 0.65, 3), "escala": round(rng.uniform(1.05, 1.28), 3), "raio_dano": 0.50, "raio_colisao": 0.42, "solido": False})
    elif tipo == "quebradinho":
        cfg.update({"tempo_rachando_ticks": 45, "tile_original": int(_REGRAS.get("tile_chao_dungeon", 8) or 8)})
    elif tipo == "barra_fogo":
        cfg.update({"bolas": rng.randint(5, min(10, 6 + dif)), "velocidade_giro": round(rng.uniform(0.9, 1.7) + dif * 0.07, 3), "comprimento": round(rng.uniform(2.2, 3.8) + dif * 0.22, 3), "barras": rng.randint(1, 3 if dif >= 5 else 2), "raio_bola": 0.34, "raio_colisao": 0.58, "solido_centro": True})
    elif tipo == "torreta":
        cfg.update({"cooldown_ticks": max(24, int(72 - dif * 6 + rng.randint(-6, 10))), "velocidade_tiro": round(4.2 + dif * 0.45, 3), "alcance": round(7.0 + dif * 1.2, 3), "raio_tiro": 0.24, "raio_colisao": 0.58, "solido": True})
    return {"id": tid, "tipo": tipo, "posicao": pos, "config": cfg}


def _gerar_conteudo_salas(ocupadas: dict, servos_pool: list[str], rng: random.Random, dificuldade_dungeon: int, seed_layout: int) -> list[dict]:
    pool = [str(p).strip() for p in servos_pool if str(p).strip()] or ["Pokemon"]
    todos_servos: list[dict] = []
    for sala in sorted(ocupadas.values(), key=lambda s: int(s.get("id_numerico", 0) or 0)):
        cfg = sala.setdefault("config", _config_sala_vazia())
        tipo = str(sala.get("tipo") or "")
        srng = _rng_sala(seed_layout, str(sala.get("id") or ""), "conteudo")
        if tipo == "entrada":
            cfg.update({"servos": [], "armadilhas": [], "claridade": 10, "piscina": None, "buracao": None})
            sala["servos"] = []
            continue
        dif_sala = _dificuldade_sala(srng, dificuldade_dungeon, tipo)
        sala["dificuldade_sala"] = int(dif_sala)
        cfg["claridade"] = max(0, min(10, 10 - srng.randint(0, max(1, min(8, dif_sala + 1)))))
        ocupados: set[tuple[int, int]] = set()
        qtd_servos = 0 if srng.random() < max(0.12, 0.34 - dif_sala * 0.025) else srng.randint(1, min(5, 1 + max(1, dif_sala)))
        if tipo == "boss":
            qtd_servos = srng.randint(0, min(3, max(1, dif_sala)))
        chaves = list(sala.get("chaves_ids") or [])
        qtd_servos = max(qtd_servos, len(chaves))
        servos = []
        for i in range(qtd_servos):
            uid = f"servo_{sala.get('id')}_{i+1}"
            chave_id = chaves[i] if i < len(chaves) else ""
            item = {
                "pokemon": srng.choice(pool),
                "uid": uid,
                "nivel": _nivel_servo(srng, dificuldade_dungeon, dif_sala),
                "posicao": _posicao_interna(srng, tuple(sala.get("posicao_sala", [0, 0])), ocupados, margem_extra=4),
                "possui_chave": bool(chave_id),
                "chave_id": chave_id,
            }
            servos.append(item)
            todos_servos.append({"sala_id": sala.get("id"), **item})
        sala["servos"] = servos
        cfg["servos"] = [dict(s) for s in servos]
        qtd_traps = 0 if srng.random() < max(0.10, 0.32 - dif_sala * 0.03) else srng.randint(1, min(5, 1 + dif_sala))
        armadilhas = [_gerar_armadilha(sala, i + 1, srng, dif_sala, ocupados) for i in range(qtd_traps)]
        cfg["armadilhas"] = armadilhas
        chance_piscina = min(0.55, 0.08 + dif_sala * 0.045)
        chance_buracao = min(0.42, 0.04 + dif_sala * 0.04)
        if srng.random() < chance_piscina:
            cfg["piscina"] = {"tipo": "agua_funda", "retangulo_rel": [0.36, 0.35, 0.28, 0.30]}
        else:
            cfg["piscina"] = None
        if srng.random() < chance_buracao:
            cfg["buracao"] = {"tipo": "buraco", "retangulo_rel": [0.40, 0.38, 0.20, 0.24]}
        else:
            cfg["buracao"] = None
    return todos_servos


def _marcar_porta_grid(grid: list[list[int]], pos: tuple[int, int], direcao: str, tile: int) -> None:
    porta_w = max(1, int(_REGRAS.get("porta_largura_tiles", 4) or 4))
    parede = max(1, int(_REGRAS.get("parede_largura_tiles", 2) or 2))
    x0 = int(pos[0]) * LARGURA_BLOCO_SALA_TILES
    y0 = int(pos[1]) * ALTURA_BLOCO_SALA_TILES
    cx = x0 + (LARGURA_BLOCO_SALA_TILES // 2)
    cy = y0 + (ALTURA_BLOCO_SALA_TILES // 2)
    meio = porta_w // 2
    pontos = []
    if direcao in {"N", "S"}:
        ys = range(y0, y0 + parede) if direcao == "N" else range(y0 + ALTURA_BLOCO_SALA_TILES - parede, y0 + ALTURA_BLOCO_SALA_TILES)
        pontos = [(x, y) for y in ys for x in range(cx - meio, cx - meio + porta_w)]
    elif direcao in {"L", "O"}:
        xs = range(x0 + LARGURA_BLOCO_SALA_TILES - parede, x0 + LARGURA_BLOCO_SALA_TILES) if direcao == "L" else range(x0, x0 + parede)
        pontos = [(x, y) for x in xs for y in range(cy - meio, cy - meio + porta_w)]
    for x, y in pontos:
        if 0 <= y < len(grid) and 0 <= x < len(grid[y]):
            grid[y][x] = int(tile)


def _grid_tiles(ocupadas: dict, largura: int, altura: int) -> list[list[int]]:
    tile_vazio = int(_REGRAS.get("tile_vazio_dungeon", 9) or 9)
    tile_chao = int(_REGRAS.get("tile_chao_dungeon", 8) or 8)
    tile_agua = int(_REGRAS.get("tile_agua_funda", 0) or 0)
    tile_buraco = int(_REGRAS.get("tile_buraco", 10) or 10)
    tile_quebradinho = int(_REGRAS.get("tile_quebradinho", tile_chao) or tile_chao)
    parede = max(1, int(_REGRAS.get("parede_largura_tiles", 2) or 2))
    largura_tiles = largura * LARGURA_BLOCO_SALA_TILES
    altura_tiles = altura * ALTURA_BLOCO_SALA_TILES
    grid = [[tile_vazio for _ in range(largura_tiles)] for _ in range(altura_tiles)]

    def _aplicar_ret_rel(sala: dict, tile: int, ret_rel: list[float]) -> None:
        pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
        x0 = int(pos[0]) * LARGURA_BLOCO_SALA_TILES
        y0 = int(pos[1]) * ALTURA_BLOCO_SALA_TILES
        rx, ry, rw, rh = [float(v) for v in list(ret_rel or [0.40, 0.40, 0.20, 0.20])[:4]]
        ax0 = x0 + max(parede + 2, int(round(LARGURA_BLOCO_SALA_TILES * rx)))
        ay0 = y0 + max(parede + 2, int(round(ALTURA_BLOCO_SALA_TILES * ry)))
        ax1 = min(x0 + LARGURA_BLOCO_SALA_TILES - parede - 3, x0 + int(round(LARGURA_BLOCO_SALA_TILES * (rx + rw))))
        ay1 = min(y0 + ALTURA_BLOCO_SALA_TILES - parede - 3, y0 + int(round(ALTURA_BLOCO_SALA_TILES * (ry + rh))))
        for yy in range(min(ay0, ay1), max(ay0, ay1) + 1):
            for xx in range(min(ax0, ax1), max(ax0, ax1) + 1):
                if 0 <= yy < len(grid) and 0 <= xx < len(grid[yy]):
                    grid[yy][xx] = int(tile)

    for (bx, by), sala in ocupadas.items():
        x0 = bx * LARGURA_BLOCO_SALA_TILES
        y0 = by * ALTURA_BLOCO_SALA_TILES
        for y in range(y0 + parede, y0 + ALTURA_BLOCO_SALA_TILES - parede):
            for x in range(x0 + parede, x0 + LARGURA_BLOCO_SALA_TILES - parede):
                grid[y][x] = tile_chao
        cfg = sala.get("config") if isinstance(sala.get("config"), dict) else {}
        piscina = cfg.get("piscina") if isinstance(cfg.get("piscina"), dict) else None
        if piscina is not None:
            _aplicar_ret_rel(sala, tile_agua, list(piscina.get("retangulo_rel") or [0.36, 0.35, 0.28, 0.30]))
        buracao = cfg.get("buracao") if isinstance(cfg.get("buracao"), dict) else None
        if buracao is not None:
            _aplicar_ret_rel(sala, tile_buraco, list(buracao.get("retangulo_rel") or [0.40, 0.38, 0.20, 0.24]))
        for trap in list(cfg.get("armadilhas") or []):
            if not isinstance(trap, dict) or str(trap.get("tipo") or "") != "quebradinho":
                continue
            pos = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) and len(trap.get("posicao")) == 2 else None
            if pos is None:
                continue
            tx, ty = int(float(pos[0])), int(float(pos[1]))
            if 0 <= ty < len(grid) and 0 <= tx < len(grid[ty]):
                grid[ty][tx] = tile_quebradinho
    for pos, sala in ocupadas.items():
        for info in list(sala.get("portas_info") or []):
            if bool(info.get("trancada", False)):
                _marcar_porta_grid(grid, pos, str(info.get("direcao") or ""), tile_vazio)
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
        elif tipo in {"comum", "piscina", "escura"}:
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
    margem = max(0, int(_REGRAS.get("margem_blocos_dungeon", 1) or 1))
    largura_jogavel = altura_jogavel = tamanho_em_blocos(tamanho)
    largura = largura_jogavel + (margem * 2)
    altura = altura_jogavel + (margem * 2)
    nome = str(row.get("Nome") or dungeon_code)
    dificuldade = str(row.get("Dificuldade") or "")
    dificuldade_num = _dificuldade_num(dificuldade or tamanho)
    bosses_nomes = _lista_csv(row.get("Pokemons"))
    servos_pool = _lista_csv(row.get("Servos"))

    dungeons_registradas_code = [
        item for item in BANCO_DADOS.listar_dungeons_registradas()
        if str(item.get("dungeon_code") or "").strip().lower() == str(dungeon_code).strip().lower()
    ]
    entradas_reais = _coletar_entradas_dungeon_no_banco(dungeon_code) or list(entradas or [])
    if not entradas_reais and not dungeons_registradas_code:
        qtd_csv = max(1, _int_csv(row.get("Entradas", 1), 1))
        entradas_reais = [{"porta_idx": i, "pedra_id": 0} for i in range(1, qtd_csv + 1)]

    # Compatibilidade: o loader antigo continua existindo para ferramentas legadas,
    # mas a geracao nova nao escolhe salas a partir de catalogo fixo.
    catalogo_raw = _catalogo_default()
    catalogo = _catalogo_por_tipo(catalogo_raw)
    seed_layout = _seed_layout(str(dungeon_code), row, entradas_reais)
    rng = random.Random(seed_layout)

    ocupadas: dict[tuple[int, int], dict] = {}
    entradas_out = []
    proximo_id = [1]

    for i, entrada in enumerate(entradas_reais, start=1):
        porta_idx = int(entrada.get("porta_idx", i) or i)
        base_entrada = posicao_sala_entrada(porta_idx, tamanho)
        pos = _proxima_posicao_livre_jogavel((base_entrada[0] + margem, base_entrada[1] + margem), ocupadas, largura, altura, margem)
        if pos is None:
            continue
        sala = _criar_sala(pos, catalogo, "entrada", f"sala_{pos[0]}_{pos[1]}", proximo_id[0], "Entrada")
        proximo_id[0] += 1
        ocupadas[pos] = sala
        ativa = bool(entrada.get("ativa", True) if "ativa" not in entrada else entrada.get("ativa", False))
        ativa = bool(ativa or entrada.get("porta_ativa", False) or entrada.get("estrutura_quebrada", False))
        saida = saida_sala_entrada(pos) if ativa else None
        entradas_out.append(
            {
                "porta_idx": porta_idx,
                "sala_id": sala["id"],
                "posicao_sala": [pos[0], pos[1]],
                "spawn": spawn_interno_entrada(pos),
                "saida": saida,
                "saida_pos": saida_sala_entrada(pos),
                "ativa": bool(ativa),
                "pedra_id": int(entrada.get("pedra_id", 0) or 0),
            }
        )

    if not ocupadas and not dungeons_registradas_code:
        pos = (margem, margem)
        sala = _criar_sala(pos, catalogo, "entrada", f"sala_{pos[0]}_{pos[1]}", proximo_id[0], "Entrada")
        proximo_id[0] += 1
        ocupadas[pos] = sala
        entradas_out.append({"porta_idx": 1, "sala_id": sala["id"], "posicao_sala": [pos[0], pos[1]], "spawn": spawn_interno_entrada(pos), "saida": saida_sala_entrada(pos), "saida_pos": saida_sala_entrada(pos), "ativa": True, "pedra_id": 0})

    entradas_pos = [tuple(e["posicao_sala"]) for e in entradas_out]
    if not entradas_pos:
        bosses_nomes = []
    for destino in entradas_pos[1:]:
        origem = entradas_pos[0]
        _adicionar_caminho(ocupadas, origem, destino, rng, catalogo, proximo_id, dificuldade=dificuldade_num)

    for boss in bosses_nomes:
        candidatos = [(x, y) for y in range(altura) for x in range(largura) if (x, y) not in ocupadas and _dentro_jogavel((x, y), largura, altura, margem)]
        if not candidatos:
            break
        entradas_pos = [tuple(e["posicao_sala"]) for e in entradas_out]
        bosses_pos = [tuple(s.get("posicao_sala", [0, 0])) for s in ocupadas.values() if isinstance(s, dict) and str(s.get("tipo") or "") == "boss"]
        dist_min = int(_REGRAS.get("dungeon_distancia_min_boss_entrada", 3) or 3)
        candidatos.sort(key=lambda p: min(abs(p[0] - e[0]) + abs(p[1] - e[1]) for e in entradas_pos), reverse=True)
        distantes = [p for p in candidatos if min(abs(p[0] - e[0]) + abs(p[1] - e[1]) for e in entradas_pos) >= dist_min]
        if distantes:
            candidatos = distantes
        separados = [p for p in candidatos if not bosses_pos or min(abs(p[0] - b[0]) + abs(p[1] - b[1]) for b in bosses_pos) >= max(2, dist_min)]
        if separados:
            candidatos = separados
        alvo = rng.choice(candidatos[: max(1, min(6, len(candidatos)))])
        origem = min(ocupadas.keys(), key=lambda p: abs(p[0] - alvo[0]) + abs(p[1] - alvo[1]))
        sala_boss = _criar_sala(alvo, catalogo, "boss", f"sala_{alvo[0]}_{alvo[1]}", proximo_id[0], f"Sala de Boss - {boss}", boss)
        proximo_id[0] += 1
        _adicionar_caminho(ocupadas, origem, alvo, rng, catalogo, proximo_id, sala_final=sala_boss, dificuldade=dificuldade_num)

    fill_min = float(_REGRAS.get("dungeon_preenchimento_min", 0.32) or 0.32)
    fill_max = float(_REGRAS.get("dungeon_preenchimento_max", 0.52) or 0.52)
    if fill_max < fill_min:
        fill_min, fill_max = fill_max, fill_min
    alvo_total = min(largura_jogavel * altura_jogavel, max(len(ocupadas), int(round(largura_jogavel * altura_jogavel * rng.uniform(fill_min, fill_max)))))
    tentativas = 0
    chance_ramificacao = float(_REGRAS.get("dungeon_chance_ramificacao", 0.35) or 0.35)
    while len(ocupadas) < alvo_total and tentativas < largura_jogavel * altura_jogavel * 8:
        tentativas += 1
        origem = rng.choice(list(ocupadas.keys()))
        passos = rng.randint(1, max(2, min(5, largura_jogavel // 2)))
        for _ in range(passos):
            livres = [v for v in _vizinhos(origem, largura, altura) if v not in ocupadas and _dentro_jogavel(v, largura, altura, margem)]
            if not livres:
                break
            pos = rng.choice(livres)
            tipo = _tipo_sala_comum(rng, catalogo, dificuldade_num)
            ocupadas[pos] = _criar_sala(pos, catalogo, tipo, f"sala_{pos[0]}_{pos[1]}", proximo_id[0])
            proximo_id[0] += 1
            origem = pos
            if len(ocupadas) >= alvo_total or rng.random() > chance_ramificacao:
                break

    _gerar_conexoes_e_portas(ocupadas, [tuple(e["posicao_sala"]) for e in entradas_out], rng)
    servos_layout = _gerar_conteudo_salas(ocupadas, servos_pool, rng, dificuldade_num, seed_layout)

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
        "largura_blocos_jogaveis": largura_jogavel,
        "altura_blocos_jogaveis": altura_jogavel,
        "margem_blocos": margem,
        "tamanho_bloco_sala_tiles": TAMANHO_BLOCO_SALA_TILES,
        "largura_bloco_sala_tiles": LARGURA_BLOCO_SALA_TILES,
        "altura_bloco_sala_tiles": ALTURA_BLOCO_SALA_TILES,
        "porta_largura_tiles": int(_REGRAS.get("porta_largura_tiles", 4) or 4),
        "parede_largura_tiles": int(_REGRAS.get("parede_largura_tiles", 2) or 2),
        "tile_vazio_dungeon": int(_REGRAS.get("tile_vazio_dungeon", 9) or 9),
        "tile_chao_dungeon": int(_REGRAS.get("tile_chao_dungeon", 8) or 8),
        "tile_agua_funda": int(_REGRAS.get("tile_agua_funda", 0) or 0),
        "tile_agua_rasa": int(_REGRAS.get("tile_agua_rasa", 1) or 1),
        "tile_buraco": int(_REGRAS.get("tile_buraco", 10) or 10),
        "tile_quebradinho": int(_REGRAS.get("tile_quebradinho", int(_REGRAS.get("tile_chao_dungeon", 8) or 8)) or int(_REGRAS.get("tile_chao_dungeon", 8) or 8)),
        "salas": salas,
        "entradas": entradas_out,
        "grid_salas_ids": grid_ids,
        "grid_salas_tipos": grid_tipos,
        "grid_tiles": _grid_tiles(ocupadas, largura, altura),
        "bosses": bosses,
        "servos": servos_layout,
        "armadilhas": [
            {"sala_id": sala.get("id"), **trap}
            for sala in salas
            for trap in list((sala.get("config") or {}).get("armadilhas") or [])
            if isinstance(trap, dict)
        ],
        "seed": int(seed_layout),
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
