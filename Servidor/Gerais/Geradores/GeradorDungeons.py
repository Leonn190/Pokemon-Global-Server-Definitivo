from __future__ import annotations

import hashlib
import json
import random
import re

from Servidor.Gerais.LoaderRegras import carregar_regras_dungeons
from Servidor.Gerais.LoaderTabelas import carregar_csv_dict
from Servidor.Gerais.Geradores.DungeonCatalogo import carregar_catalogo_dungeons, _escolher_modelo_sala
from Servidor.Gerais.Geradores.DungeonLayout import (
    _adicionar_caminho,
    _criar_sala,
    _dentro_jogavel,
    _dificuldade_num,
    _gerar_conexoes_e_portas,
    _gerar_conteudo_salas,
    _grid_tiles,
    _proxima_posicao_livre_jogavel,
    _vizinhos,
)
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
