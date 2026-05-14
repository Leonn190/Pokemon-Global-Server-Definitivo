from __future__ import annotations

import hashlib
import json
import random
import re
from collections import deque

from Servidor.Gerais.LoaderCatalogos import carregar_catalogo
from Servidor.Gerais.LoaderRegras import carregar_regras_dungeons
from Servidor.Gerais.LoaderTabelas import carregar_csv_dict
from Servidor.Mundo.BancoDados import BANCO_DADOS
from Servidor.Mundo.DungeonGeometria import (
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
        "catalogo_versao": "v2_modelos_salas",
        "tamanho_sala_tiles": {
            "largura": LARGURA_BLOCO_SALA_TILES,
            "altura": ALTURA_BLOCO_SALA_TILES,
        },
        "calculo_dificuldade_sala": {
            "pesos_recomendados": {"armadilhas": 1.0, "servos": 1.0, "claridade": 0.35}
        },
        "configuracoes_armadilhas": {},
        "salas": [
            {
                "id": 1,
                "modelo_id": "entrada",
                "nome": "Entrada",
                "tipo": "entrada",
                "categoria": "fixa",
                "chance_spawn": 0.0,
                "dificuldade_base": 0,
                "servos": {"min": 0, "max": 0},
                "claridade": {"min": 10, "max": 10},
                "armadilhas": [],
            },
            {
                "id": 2,
                "modelo_id": "boss",
                "nome": "Sala de Boss",
                "tipo": "boss",
                "categoria": "fixa",
                "chance_spawn": 0.0,
                "dificuldade_base": 0,
                "servos": {"min": 0, "max": 0},
                "claridade": {"min": 8, "max": 10},
                "armadilhas": [],
            },
            {
                "id": 3,
                "modelo_id": "sala_comum",
                "nome": "Sala Comum",
                "tipo": "servos",
                "categoria": "combate",
                "chance_spawn": 1.0,
                "dificuldade_base": 1,
                "servos": {"min": 0, "max": 2},
                "claridade": {"min": 7, "max": 10},
                "armadilhas": [],
            },
        ],
    }


def _float_seguro(valor, default=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _int_seguro(valor, default=0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _intervalo_dict(valor, padrao_min=0, padrao_max=0) -> dict:
    bruto = valor if isinstance(valor, dict) else {}
    mn = _float_seguro(bruto.get("min"), padrao_min)
    mx = _float_seguro(bruto.get("max"), padrao_max)
    if mx < mn:
        mn, mx = mx, mn
    return {"min": mn, "max": mx, **({"peso_dificuldade": _float_seguro(bruto.get("peso_dificuldade"), 0.35)} if "peso_dificuldade" in bruto else {})}


def _normalizar_modelo_sala(item: dict, indice: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    modelo_id = str(item.get("modelo_id") or item.get("id") or "").strip()
    if not modelo_id:
        return None
    tipo = str(item.get("tipo") or "servos").strip().lower() or "servos"
    try:
        id_catalogo = int(item.get("id", indice) or indice)
    except (TypeError, ValueError):
        id_catalogo = int(indice)
    return {
        "id": id_catalogo,
        "modelo_id": modelo_id,
        "nome": str(item.get("nome") or item.get("Nome") or modelo_id),
        "tipo": tipo,
        "categoria": str(item.get("categoria") or "").strip().lower(),
        "chance_spawn": max(0.0, _float_seguro(item.get("chance_spawn", item.get("chance", 0.0)), 0.0)),
        "dificuldade_base": _float_seguro(item.get("dificuldade_base", item.get("dificuldade", 0)), 0.0),
        "servos": _intervalo_dict(item.get("servos"), 0, 0),
        "claridade": _intervalo_dict(item.get("claridade"), 10, 10),
        "armadilhas": [dict(a) for a in list(item.get("armadilhas") or []) if isinstance(a, dict)],
        "conteudo_especial": dict(item.get("conteudo_especial") or {}) if isinstance(item.get("conteudo_especial"), dict) else {},
        "variacao_dificuldade": dict(item.get("variacao_dificuldade") or {}) if isinstance(item.get("variacao_dificuldade"), dict) else {},
    }


def _normalizar_catalogo(data: dict) -> dict:
    if not isinstance(data, dict):
        return _catalogo_default()
    bruto = data.get("salas") if isinstance(data.get("salas"), (list, dict)) else []
    salas = []
    if isinstance(bruto, dict):
        iter_salas = bruto.values()
    else:
        iter_salas = bruto if isinstance(bruto, list) else []
    for idx, item in enumerate(iter_salas, start=1):
        modelo = _normalizar_modelo_sala(item, idx)
        if modelo is not None:
            salas.append(modelo)
    if not salas:
        return _catalogo_default()
    por_id = {str(s.get("modelo_id") or "") for s in salas}
    for sala in _catalogo_default()["salas"]:
        if str(sala.get("modelo_id") or "") not in por_id:
            salas.append(dict(sala))
    tamanho = data.get("tamanho_sala_tiles") if isinstance(data.get("tamanho_sala_tiles"), dict) else {}
    calculo = data.get("calculo_dificuldade_sala") if isinstance(data.get("calculo_dificuldade_sala"), dict) else {}
    configs = data.get("configuracoes_armadilhas") if isinstance(data.get("configuracoes_armadilhas"), dict) else {}
    return {
        "catalogo_versao": str(data.get("catalogo_versao") or "v2_modelos_salas"),
        "tamanho_sala_tiles": {
            "largura": _int_seguro(tamanho.get("largura"), LARGURA_BLOCO_SALA_TILES),
            "altura": _int_seguro(tamanho.get("altura"), ALTURA_BLOCO_SALA_TILES),
        },
        "calculo_dificuldade_sala": dict(calculo),
        "configuracoes_armadilhas": dict(configs),
        "salas": salas,
    }


def carregar_catalogo_dungeons() -> dict:
    try:
        dados = carregar_catalogo("Dungeon")
        if dados:
            return _normalizar_catalogo(dados)
    except Exception as exc:
        print(f"[Dungeons] Catalogo invalido: {exc}")
    return _catalogo_default()


def _modelos_catalogo(catalogo: dict) -> list[dict]:
    return [dict(s) for s in list(catalogo.get("salas") or []) if isinstance(s, dict)]


def _modelo_por_id(catalogo: dict) -> dict[str, dict]:
    return {str(s.get("modelo_id") or "").strip(): dict(s) for s in _modelos_catalogo(catalogo) if str(s.get("modelo_id") or "").strip()}


def _modelos_alocaveis(catalogo: dict) -> list[dict]:
    return [
        dict(s)
        for s in _modelos_catalogo(catalogo)
        if str(s.get("tipo") or "").strip().lower() not in {"entrada", "boss"}
        and str(s.get("modelo_id") or "").strip() not in {"entrada", "boss"}
        and float(s.get("chance_spawn", 0.0) or 0.0) > 0.0
    ]


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


def _tipo_publico_modelo(tipo: str) -> str:
    tipo = str(tipo or "").strip().lower()
    if tipo in {"entrada", "boss", "piscina", "buracao", "inundada"}:
        return tipo
    return "normal"


def _modelo_para_tipo(catalogo: dict, tipo: str) -> dict:
    tipo_norm = str(tipo or "").strip().lower()
    for modelo in _modelos_catalogo(catalogo):
        if str(modelo.get("tipo") or "").strip().lower() == tipo_norm or str(modelo.get("modelo_id") or "").strip().lower() == tipo_norm:
            return modelo
    alocaveis = _modelos_alocaveis(catalogo)
    return alocaveis[0] if alocaveis else _catalogo_default()["salas"][2]


def _criar_sala(pos: tuple[int, int], catalogo: dict, tipo: str, id_str: str, id_num: int, nome: str | None = None, pokemon_boss: str = "", modelo: dict | None = None) -> dict:
    cfg = dict(modelo or _modelo_para_tipo(catalogo, tipo))
    tipo_real = str(cfg.get("tipo") or tipo or "servos").strip().lower()
    tipo_publico = _tipo_publico_modelo(tipo_real)
    return {
        "id": id_str,
        "id_numerico": int(id_num),
        "id_catalogo": int(cfg.get("id", id_num) or id_num),
        "tipo": tipo_publico,
        "subtipo_procedural": tipo_real,
        "nome": str(nome or cfg.get("nome") or tipo.title()),
        "posicao_sala": [int(pos[0]), int(pos[1])],
        "largura_blocos": 1,
        "altura_blocos": 1,
        "chance": float(cfg.get("chance_spawn", 0.0) or 0.0),
        "dificuldade_sala": int(round(float(cfg.get("dificuldade_base", 0) or 0))),
        "modelo_id": str(cfg.get("modelo_id") or tipo_real),
        "categoria_modelo": str(cfg.get("categoria") or ""),
        "dificuldade_base": float(cfg.get("dificuldade_base", 0.0) or 0.0),
        "dificuldade_componentes": {"base": float(cfg.get("dificuldade_base", 0.0) or 0.0), "armadilhas": 0.0, "servos": 0.0, "claridade": 0.0},
        "servos_min_modelo": int(_intervalo_dict(cfg.get("servos"), 0, 0).get("min", 0) or 0),
        "servos_max_modelo": int(_intervalo_dict(cfg.get("servos"), 0, 0).get("max", 0) or 0),
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


def _escolher_modelo_sala(rng: random.Random, catalogo: dict, dificuldade=2) -> dict:
    modelos = _modelos_alocaveis(catalogo)
    if not modelos:
        return _catalogo_default()["salas"][2]
    dif = max(1, min(6, _dificuldade_num(dificuldade)))
    pesos = []
    for modelo in modelos:
        peso = max(0.0, float(modelo.get("chance_spawn", 0.0) or 0.0))
        distancia = abs(float(modelo.get("dificuldade_base", 1.0) or 1.0) - float(dif))
        pesos.append(peso * max(0.20, 1.0 - distancia * 0.16))
    if not any(p > 0.0 for p in pesos):
        pesos = [1.0 for _ in modelos]
    return dict(rng.choices(modelos, weights=pesos, k=1)[0])


def _adicionar_caminho(ocupadas: dict, origem: tuple[int, int], destino: tuple[int, int], rng: random.Random, catalogo: dict, proximo_id: list[int], sala_final: dict | None = None, dificuldade=2) -> None:
    for pos in _caminho_manhattan(origem, destino, rng):
        if pos in ocupadas:
            continue
        if sala_final is not None and pos == destino:
            ocupadas[pos] = sala_final
        else:
            modelo = _escolher_modelo_sala(rng, catalogo, dificuldade)
            ocupadas[pos] = _criar_sala(pos, catalogo, str(modelo.get("tipo") or "servos"), f"sala_{pos[0]}_{pos[1]}", proximo_id[0], modelo=modelo)
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
    if str(sala.get("tipo") or "") != "normal":
        return False
    limite_regras = int(_REGRAS.get("chaves_por_sala_max", 2) or 2)
    limite_modelo = max(0, int(sala.get("servos_max_modelo", 0) or 0))
    limite = min(limite_regras, limite_modelo)
    return limite > 0 and int(sala.get("chaves_da_sala", 0) or 0) < limite


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


def _clamp(valor: float, mn: float, mx: float) -> float:
    return max(float(mn), min(float(mx), float(valor)))


def _fator_variacao_sala(rng: random.Random, dificuldade_dungeon: int, dificuldade_base: float) -> float:
    dif = _clamp(float(dificuldade_dungeon or 2), 1.0, 6.0)
    base = _clamp(float(dificuldade_base or 0.0), 0.0, 6.0)
    moda = _clamp(0.46 + (dif - base) * 0.08 + (dif - 2.0) * 0.035, 0.16, 0.86)
    valor = rng.triangular(0.0, 1.0, moda)
    jitter = rng.uniform(-0.10, 0.10)
    return _clamp(valor + jitter, 0.0, 1.0)


def _interp(mn, mx, fator: float):
    a = _float_seguro(mn, 0.0)
    b = _float_seguro(mx, a)
    return a + (b - a) * _clamp(fator, 0.0, 1.0)


def _interp_intervalo(intervalo: dict, fator: float, padrao_min=0.0, padrao_max=0.0) -> float:
    bruto = intervalo if isinstance(intervalo, dict) else {}
    return _interp(bruto.get("min", padrao_min), bruto.get("max", padrao_max), fator)


def _config_interpolada(armadilha: dict, fator: float) -> dict:
    fixa = dict(armadilha.get("config") or {}) if isinstance(armadilha.get("config"), dict) else {}
    cfg_min = armadilha.get("config_min") if isinstance(armadilha.get("config_min"), dict) else {}
    cfg_max = armadilha.get("config_max") if isinstance(armadilha.get("config_max"), dict) else {}
    if not cfg_min and not cfg_max:
        return fixa
    inteiros = {"numero_bolas", "numero_cabos", "bolas", "barras", "cooldown_ticks", "tempo_rachando_ticks"}
    for chave in sorted(set(cfg_min) | set(cfg_max)):
        a = cfg_min.get(chave, cfg_max.get(chave))
        b = cfg_max.get(chave, a)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            valor = _interp(a, b, fator)
            fixa[chave] = int(round(valor)) if chave in inteiros else round(float(valor), 3)
        else:
            fixa[chave] = b if fator >= 0.5 else a
    return fixa


def _pos_abs_sala(sala: dict, posicao_local) -> list[float]:
    pos_sala = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
    lx, ly = list(posicao_local or [0, 0])[:2]
    x = int(pos_sala[0]) * LARGURA_BLOCO_SALA_TILES + float(lx)
    y = int(pos_sala[1]) * ALTURA_BLOCO_SALA_TILES + float(ly)
    return [round(float(x), 3), round(float(y), 3)]


def _retangulo_local_abs(sala: dict, retangulo_local) -> list[int]:
    pos_sala = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
    vals = list(retangulo_local or [0, 0, 0, 0])[:4]
    while len(vals) < 4:
        vals.append(0)
    bx = int(pos_sala[0]) * LARGURA_BLOCO_SALA_TILES
    by = int(pos_sala[1]) * ALTURA_BLOCO_SALA_TILES
    parede = max(1, int(_REGRAS.get("parede_largura_tiles", 2) or 2))
    x0 = int(round(bx + float(vals[0])))
    y0 = int(round(by + float(vals[1])))
    x1 = int(round(bx + float(vals[2])))
    y1 = int(round(by + float(vals[3])))
    mnx, mxx = bx + parede, bx + LARGURA_BLOCO_SALA_TILES - parede - 1
    mny, mxy = by + parede, by + ALTURA_BLOCO_SALA_TILES - parede - 1
    return [int(_clamp(x0, mnx, mxx)), int(_clamp(y0, mny, mxy)), int(_clamp(x1, mnx, mxx)), int(_clamp(y1, mny, mxy))]


def _limites_local_abs(sala: dict, limites_local) -> list[float] | None:
    if not isinstance(limites_local, (list, tuple)) or len(limites_local) != 4:
        return None
    pos_sala = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
    bx = int(pos_sala[0]) * LARGURA_BLOCO_SALA_TILES
    by = int(pos_sala[1]) * ALTURA_BLOCO_SALA_TILES
    return [round(bx + float(limites_local[0]), 3), round(by + float(limites_local[1]), 3), round(bx + float(limites_local[2]), 3), round(by + float(limites_local[3]), 3)]


def _tipo_armadilha_runtime(tipo: str) -> str:
    mapa = {
        "espeto": "espeto",
        "espeto_movel": "espeto_movel",
        "espeto_ricochete": "espeto_ricochete",
        "torreta": "torreta",
        "barra_fogo": "barra_fogo",
        "quebradico": "quebradinho",
        "quebradinho": "quebradinho",
    }
    return mapa.get(str(tipo or "").strip().lower(), str(tipo or "").strip().lower())


def _converter_config_armadilha(sala: dict, armadilha: dict, fator: float) -> tuple[str, dict]:
    tipo = _tipo_armadilha_runtime(str(armadilha.get("tipo") or ""))
    cfg_base = _config_interpolada(armadilha, fator)
    movimento = armadilha.get("movimento") if isinstance(armadilha.get("movimento"), dict) else {}
    cfg: dict[str, object] = {}
    if tipo == "espeto":
        tamanho = _float_seguro(cfg_base.get("tamanho"), 1.0)
        cfg.update({"escala": round(tamanho, 3), "raio_dano": round(0.58 * tamanho, 3), "raio_colisao": round(0.48 * tamanho, 3), "solido": True})
    elif tipo == "espeto_movel":
        tamanho = _float_seguro(cfg_base.get("tamanho"), 1.0)
        limites = _limites_local_abs(sala, movimento.get("limites_local"))
        cfg.update({
            "escala": round(tamanho, 3),
            "velocidade": round(_float_seguro(cfg_base.get("velocidade"), 1.8), 3),
            "direcao": list(movimento.get("direcao") or cfg_base.get("direcao") or [1, 0])[:2],
            "raio_dano": round(0.50 * tamanho, 3),
            "raio_colisao": round(0.42 * tamanho, 3),
            "solido": False,
        })
        if limites is not None:
            cfg["limites_sala"] = limites
    elif tipo == "espeto_ricochete":
        tamanho = _float_seguro(cfg_base.get("tamanho"), 1.0)
        cfg.update({
            "escala": round(tamanho, 3),
            "velocidade": round(_float_seguro(cfg_base.get("velocidade"), 1.8), 3),
            "direcao": list(movimento.get("direcao") or cfg_base.get("direcao") or [1, 0])[:2],
            "raio_dano": round(0.50 * tamanho, 3),
            "raio_colisao": round(0.42 * tamanho, 3),
            "solido": False,
        })
    elif tipo == "torreta":
        freq = max(0.01, _float_seguro(cfg_base.get("frequencia_tiros"), 0.5))
        cfg.update({
            "raio_tiro": round(_float_seguro(cfg_base.get("tamanho_tiro"), 0.22), 3),
            "velocidade_tiro": round(_float_seguro(cfg_base.get("velocidade_tiro"), 4.0), 3),
            "cooldown_ticks": max(12, int(round(30.0 / freq))),
            "raio_colisao": 0.58,
            "solido": True,
            "alcance": round(_float_seguro(cfg_base.get("alcance"), 8.0), 3),
        })
    elif tipo == "barra_fogo":
        cfg.update({
            "bolas": max(1, int(round(_float_seguro(cfg_base.get("numero_bolas"), 4)))),
            "barras": max(1, int(round(_float_seguro(cfg_base.get("numero_cabos"), 1)))),
            "raio_bola": round(_float_seguro(cfg_base.get("tamanho_bolas"), 0.30), 3),
            "velocidade_giro": round(_float_seguro(cfg_base.get("velocidade_giro"), 1.0), 3),
            "comprimento": round(_float_seguro(cfg_base.get("comprimento"), 3.0 + (fator - 0.5) * 0.4), 3),
            "raio_colisao": 0.58,
            "solido_centro": True,
        })
    elif tipo == "quebradinho":
        cfg.update({
            "tempo_rachando_ticks": int(round(_float_seguro(cfg_base.get("tempo_rachando_ticks"), 45))),
            "tile_original": int(_REGRAS.get("tile_chao_dungeon", 8) or 8),
        })
    return tipo, cfg


def _converter_armadilhas_modelo(sala: dict, modelo: dict, fator: float) -> list[dict]:
    armadilhas = []
    pos_sala = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
    for idx, item in enumerate(list(modelo.get("armadilhas") or []), start=1):
        if not isinstance(item, dict):
            continue
        pos_local = item.get("posicao_local") if isinstance(item.get("posicao_local"), (list, tuple)) and len(item.get("posicao_local")) == 2 else None
        if pos_local is None:
            continue
        tipo, cfg = _converter_config_armadilha(sala, item, fator)
        if not tipo:
            continue
        id_local = str(item.get("id_local") or idx).strip() or str(idx)
        armadilhas.append({
            "id": f"trap_{int(pos_sala[0])}_{int(pos_sala[1])}_{id_local}",
            "tipo": tipo,
            "posicao": _pos_abs_sala(sala, pos_local),
            "config": cfg,
        })
    return armadilhas


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


def _aplicar_especial_modelo(sala: dict, modelo: dict) -> None:
    cfg = sala.setdefault("config", _config_sala_vazia())
    cfg["piscina"] = None
    cfg["buracao"] = None
    cfg["inundada"] = None
    especial = modelo.get("conteudo_especial") if isinstance(modelo.get("conteudo_especial"), dict) else {}
    tipo = str(especial.get("tipo") or modelo.get("tipo") or "").strip().lower()
    if tipo == "inundada":
        cfg["inundada"] = {"tipo": "agua_funda"}
    elif tipo == "piscina":
        ret = list(especial.get("retangulo_local") or [])
        cfg["piscina"] = {"tipo": "agua_funda", "retangulo_local": ret, "retangulo_abs": _retangulo_local_abs(sala, ret)}
    elif tipo == "buracao":
        ret = list(especial.get("retangulo_local") or [])
        cfg["buracao"] = {"tipo": "buraco", "retangulo_local": ret, "retangulo_abs": _retangulo_local_abs(sala, ret)}


def _variacao_modelo(modelo: dict, chave: str, fator: float, fallback_max: float = 0.0) -> float:
    variacao = modelo.get("variacao_dificuldade") if isinstance(modelo.get("variacao_dificuldade"), dict) else {}
    item = variacao.get(chave) if isinstance(variacao.get(chave), dict) else None
    if item is None:
        return round(float(fallback_max) * _clamp(fator, 0.0, 1.0), 3)
    return round(_interp_intervalo(item, fator), 3)


def _aplicar_modelo_sala(sala: dict, modelo: dict, seed_layout: int, dificuldade_dungeon: int, pokemons_servos: list[str], rng: random.Random) -> list[dict]:
    del rng
    pool = [str(p).strip() for p in pokemons_servos if str(p).strip()] or ["Pokemon"]
    srng = _rng_sala(seed_layout, str(sala.get("id") or ""), "conteudo_modelo")
    cfg = sala.setdefault("config", _config_sala_vazia())
    cfg.update({"servos": [], "armadilhas": [], "piscina": None, "buracao": None, "inundada": None})
    tipo_publico = str(sala.get("tipo") or "")
    if tipo_publico == "entrada":
        cfg["claridade"] = 10
        sala["servos"] = []
        sala["dificuldade_sala"] = 0
        sala["dificuldade_componentes"] = {"base": 0.0, "armadilhas": 0.0, "servos": 0.0, "claridade": 0.0}
        return []
    if tipo_publico == "boss":
        claridade_boss = _intervalo_dict(modelo.get("claridade"), 8, 10)
        cfg["claridade"] = int(round(_interp_intervalo(claridade_boss, srng.random(), 8, 10)))
        sala["servos"] = []
        sala["dificuldade_sala"] = int(round(float(modelo.get("dificuldade_base", 0) or 0)))
        sala["dificuldade_componentes"] = {"base": float(modelo.get("dificuldade_base", 0) or 0), "armadilhas": 0.0, "servos": 0.0, "claridade": 0.0}
        return []

    dificuldade_base = float(modelo.get("dificuldade_base", 0.0) or 0.0)
    fator = _fator_variacao_sala(srng, dificuldade_dungeon, dificuldade_base)
    claridade_cfg = _intervalo_dict(modelo.get("claridade"), 10, 10)
    claridade_min = float(claridade_cfg.get("min", 10) or 10)
    claridade_max = float(claridade_cfg.get("max", 10) or 10)
    claridade = int(round(_interp(claridade_max, claridade_min, fator)))
    cfg["claridade"] = int(_clamp(claridade, 0, 10))

    servos_cfg = _intervalo_dict(modelo.get("servos"), 0, 0)
    servo_min = max(0, int(round(float(servos_cfg.get("min", 0) or 0))))
    servo_max = max(servo_min, int(round(float(servos_cfg.get("max", 0) or 0))))
    chaves = list(sala.get("chaves_ids") or [])
    qtd_servos = int(round(_interp(servo_min, servo_max, fator))) if servo_max > 0 else 0
    qtd_servos = max(qtd_servos, min(len(chaves), servo_max))
    qtd_servos = max(servo_min, min(servo_max, qtd_servos))

    ocupados: set[tuple[int, int]] = set()
    dif_previa = int(round(dificuldade_base))
    servos = []
    todos_servos = []
    for i in range(qtd_servos):
        uid = f"servo_{sala.get('id')}_{i+1}"
        chave_id = chaves[i] if i < len(chaves) else ""
        item = {
            "pokemon": srng.choice(pool),
            "uid": uid,
            "nivel": _nivel_servo(srng, dificuldade_dungeon, dif_previa),
            "posicao": _posicao_interna(srng, tuple(sala.get("posicao_sala", [0, 0])), ocupados, margem_extra=4),
            "possui_chave": bool(chave_id),
            "chave_id": chave_id,
        }
        servos.append(item)
        todos_servos.append({"sala_id": sala.get("id"), **item})
    sala["servos"] = servos
    cfg["servos"] = [dict(s) for s in servos]
    cfg["armadilhas"] = _converter_armadilhas_modelo(sala, modelo, fator)
    _aplicar_especial_modelo(sala, modelo)

    variacao_armadilhas = _variacao_modelo(modelo, "armadilhas", fator, fallback_max=len(cfg["armadilhas"]) * 0.45)
    variacao_servos = _variacao_modelo(modelo, "servos", fator, fallback_max=(qtd_servos / max(1, servo_max)) * 1.5 if servo_max else 0.0)
    peso_claridade = _float_seguro(claridade_cfg.get("peso_dificuldade"), 0.35)
    escuro = 0.0 if claridade_max <= claridade_min else (claridade_max - cfg["claridade"]) / max(1.0, claridade_max - claridade_min)
    variacao_claridade = _variacao_modelo(modelo, "claridade", fator, fallback_max=escuro * peso_claridade)
    componentes = {
        "base": round(dificuldade_base, 3),
        "armadilhas": round(variacao_armadilhas, 3),
        "servos": round(variacao_servos, 3),
        "claridade": round(variacao_claridade, 3),
    }
    sala["dificuldade_componentes"] = componentes
    sala["dificuldade_sala"] = int(round(sum(componentes.values())))
    return todos_servos


def _gerar_conteudo_salas(ocupadas: dict, catalogo: dict, servos_pool: list[str], rng: random.Random, dificuldade_dungeon: int, seed_layout: int) -> list[dict]:
    pool = [str(p).strip() for p in servos_pool if str(p).strip()] or ["Pokemon"]
    todos_servos: list[dict] = []
    modelos = _modelo_por_id(catalogo)
    for sala in sorted(ocupadas.values(), key=lambda s: int(s.get("id_numerico", 0) or 0)):
        modelo = modelos.get(str(sala.get("modelo_id") or "")) or _modelo_para_tipo(catalogo, str(sala.get("subtipo_procedural") or "servos"))
        todos_servos.extend(_aplicar_modelo_sala(sala, modelo, seed_layout, dificuldade_dungeon, pool, rng))
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

    def _aplicar_ret_abs(tile: int, ret_abs: list[int]) -> None:
        vals = list(ret_abs or [0, 0, 0, 0])[:4]
        while len(vals) < 4:
            vals.append(0)
        ax0, ay0, ax1, ay1 = [int(round(float(v))) for v in vals]
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
        inundada = cfg.get("inundada") if isinstance(cfg.get("inundada"), dict) else None
        if inundada is not None:
            for y in range(y0 + parede, y0 + ALTURA_BLOCO_SALA_TILES - parede):
                for x in range(x0 + parede, x0 + LARGURA_BLOCO_SALA_TILES - parede):
                    grid[y][x] = tile_agua
        piscina = cfg.get("piscina") if isinstance(cfg.get("piscina"), dict) else None
        if piscina is not None:
            ret_abs = piscina.get("retangulo_abs") if isinstance(piscina.get("retangulo_abs"), list) else _retangulo_local_abs(sala, piscina.get("retangulo_local"))
            _aplicar_ret_abs(tile_agua, ret_abs)
        buracao = cfg.get("buracao") if isinstance(cfg.get("buracao"), dict) else None
        if buracao is not None:
            ret_abs = buracao.get("retangulo_abs") if isinstance(buracao.get("retangulo_abs"), list) else _retangulo_local_abs(sala, buracao.get("retangulo_local"))
            _aplicar_ret_abs(tile_buraco, ret_abs)
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

    catalogo = carregar_catalogo_dungeons()
    seed_layout = _seed_layout(str(dungeon_code), row, entradas_reais)
    rng = random.Random(seed_layout)
    alvo_musica = " ".join([str(dungeon_code), nome, " ".join(bosses_nomes)]).lower()
    musica_dungeon = (
        "EternatusDungeon"
        if ("eternatus" in alvo_musica or "eternatos" in alvo_musica)
        else random.Random(f"{seed_layout}:musica").choice(["Dungeon1", "Dungeon2", "Dungeon3"])
    )

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
            modelo = _escolher_modelo_sala(rng, catalogo, dificuldade_num)
            ocupadas[pos] = _criar_sala(pos, catalogo, str(modelo.get("tipo") or "servos"), f"sala_{pos[0]}_{pos[1]}", proximo_id[0], modelo=modelo)
            proximo_id[0] += 1
            origem = pos
            if len(ocupadas) >= alvo_total or rng.random() > chance_ramificacao:
                break

    _gerar_conexoes_e_portas(ocupadas, [tuple(e["posicao_sala"]) for e in entradas_out], rng)
    servos_layout = _gerar_conteudo_salas(ocupadas, catalogo, servos_pool, rng, dificuldade_num, seed_layout)

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
        "musica_dungeon": musica_dungeon,
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
        "catalogo_versao": str(catalogo.get("catalogo_versao") or "v2_modelos_salas"),
    }
