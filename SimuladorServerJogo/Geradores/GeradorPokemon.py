"""Gerador de Pokémon do servidor (baseado em Dados/Pokemon Global Server - Pokemons.csv)."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

from SimuladorServerJogo.Controle.ObjetosMundoServer import PokemonServer
from SimuladorServerJogo.Controle.LoaderRegras import carregar_regras_pokemons

ARQUIVO_POKEMONS = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - Pokemons.csv"
ARQUIVO_ATAQUES = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - Ataques.csv"
ARQUIVO_ITENS = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - Itens.csv"
STATS_BASE = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int", "CrD", "CrC"]
STATS_VARIAVEIS_IV = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int"]
_REGRAS_POKEMON = carregar_regras_pokemons()


def _fnum(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _inum(v, default=0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return int(default)


def _normalizar_escala_pokemon(v, default: int = 3) -> int:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        n = int(default)
    return max(0, min(15, n))


def _diametro_tiles_por_escala(escala: int) -> float:
    base = float(_REGRAS_POKEMON.get("tamanho_diametro_base_tiles", 0.6) or 0.6)
    incremento = float(_REGRAS_POKEMON.get("tamanho_incremento_por_escala", _REGRAS_POKEMON.get("tamanho_incremento_por_tamanho", 0.1)) or 0.1)
    return base + (max(0, int(escala)) * incremento)


def _raio_colisao_por_escala(escala: int) -> float:
    return _diametro_tiles_por_escala(escala) * 0.5


def _normalizar_variacao_tamanho(v, default: int = 0) -> int:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        n = int(default)
    if n > 0:
        return 1
    if n < 0:
        return -1
    return 0


def _sigla_tamanho_por_variacao(variacao: int) -> str:
    if int(variacao) > 0:
        return "G"
    if int(variacao) < 0:
        return "S"
    return "M"


def _sortear_escala_e_tamanho(escala_base: int) -> tuple[int, int, str]:
    base = _normalizar_escala_pokemon(escala_base, default=3)
    var_min = int(_REGRAS_POKEMON.get("tamanho_variacao_escala_min", -1) or -1)
    var_max = int(_REGRAS_POKEMON.get("tamanho_variacao_escala_max", 1) or 1)
    if var_min > var_max:
        var_min, var_max = var_max, var_min
    pool = [v for v in range(var_min, var_max + 1) if v in (-1, 0, 1)] or [-1, 0, 1]
    variacao = int(random.choice(pool))
    escala = _normalizar_escala_pokemon(base + variacao, default=base)
    return (escala, variacao, _sigla_tamanho_por_variacao(variacao))


def _nivel_baixo_comum(max_nivel: int = 60) -> int:
    r = random.random() ** 2.35
    return max(0, min(int(max_nivel), int(round(r * max_nivel))))


def _xp_alvo_por_nivel(nivel: int) -> int:
    nivel_ajustado = max(0, min(100, int(nivel)))
    if nivel_ajustado >= 100:
        return 0
    return int((nivel_ajustado + 1) * 100)


def _recalcular_total(stats: Dict[str, float]) -> float:
    vida = _fnum(stats.get("Vida"), 0.0)
    soma_basicos = sum(_fnum(stats.get(k), 0.0) for k in STATS_VARIAVEIS_IV if k != "Vida")
    crc = _fnum(stats.get("CrC"), 0.0)
    crd = _fnum(stats.get("CrD"), 0.0)
    return round(vida + (soma_basicos * 2.0) + ((crc + crd) * 3.0), 2)


def _recalcular_poder(stats: Dict[str, float]) -> float:
    vida = _fnum(stats.get("Vida"), 0.0)
    demais = sum(_fnum(v, 0.0) for k, v in stats.items() if k != "Vida")
    return round(vida + (demais * 2.0), 2)


def _recalcular_poder_relativo(stats: Dict[str, float]) -> float:
    if not isinstance(stats, dict):
        return 0.0
    ranking = []
    for chave, valor in stats.items():
        real = _fnum(valor, 0.0)
        relativo = (real / 2.0) if chave == "Vida" else real
        ranking.append((relativo, chave, real))
    ranking.sort(key=lambda x: x[0], reverse=True)
    total = 0.0
    for _, chave, real in ranking[:6]:
        total += real if chave == "Vida" else (real * 2.0)
    return round(total * 2.0, 2)


def _carregar_frutas() -> List[str]:
    if not ARQUIVO_ITENS.exists():
        return []
    frutas: List[str] = []
    with ARQUIVO_ITENS.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if str(row.get("Estilo", "")).strip().lower() != "fruta":
                continue
            nome = str(row.get("Nome", "")).strip()
            if nome:
                frutas.append(nome)
    return frutas


def _gerar_subivs_media(iv_global: int) -> Dict[str, int]:
    alvo = max(0, min(100, int(iv_global)))
    subivs = {k: alvo for k in STATS_VARIAVEIS_IV}
    for k in STATS_VARIAVEIS_IV:
        subivs[k] = max(0, min(100, alvo + random.randint(-24, 24)))

    soma_alvo = alvo * len(STATS_VARIAVEIS_IV)
    diff = soma_alvo - sum(subivs.values())
    while diff != 0:
        alterado = False
        ordem = STATS_VARIAVEIS_IV[:]
        random.shuffle(ordem)
        passo = 1 if diff > 0 else -1
        for k in ordem:
            if diff == 0:
                break
            nv = subivs[k] + passo
            if 0 <= nv <= 100:
                subivs[k] = nv
                diff -= passo
                alterado = True
        if not alterado:
            break
    return subivs


def _sortear_tipos(row: Dict[str, str]) -> List[str]:
    tipos: List[str] = []
    tipo1 = str(row.get("Tipo1", "") or "").strip()
    for idx in (1, 2, 3):
        tipo = str(row.get(f"Tipo{idx}", "") or "").strip()
        chance = max(0.0, min(100.0, _fnum(row.get(f"%{idx}"), 0.0)))
        if tipo and random.random() <= (chance / 100.0):
            tipos.append(tipo)
    if not tipos and tipo1:
        tipos.append(tipo1)
    return tipos


def _carregar_ataques() -> List[Dict[str, object]]:
    if not ARQUIVO_ATAQUES.exists():
        return []
    ataques: List[Dict[str, object]] = []
    with ARQUIVO_ATAQUES.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ataque = str(row.get("Ataque", "")).strip()
            if not ataque:
                continue
            dados = dict(row)
            dados["Ataque"] = ataque
            dados["Custo"] = _inum(dados.get("Custo"), 0)
            ataques.append(dados)
    return ataques


_ATAQUES_DISPONIVEIS = _carregar_ataques()
_FRUTAS_DISPONIVEIS = _carregar_frutas()


def _ataque_com_nivel(ataque: Dict[str, object]) -> Dict[str, object]:
    dados = dict(ataque or {})
    dados["Nivel"] = int(dados.get("Nivel", 1) or 1)
    return dados


def aprender_ataque_aleatorio(estado_pokemon: Dict[str, object], forcar: bool = False) -> bool:
    if not isinstance(estado_pokemon, dict) or not _ATAQUES_DISPONIVEIS:
        return False
    if (not forcar) and random.random() > 0.25:
        return False

    memorias = estado_pokemon.get("memorias")
    if not isinstance(memorias, list):
        memorias = [None, None, None, None, None]
    if len(memorias) < 5:
        memorias = list(memorias) + ([None] * (5 - len(memorias)))
    memorias = memorias[:5]

    indice_livre = next((i for i, valor in enumerate(memorias) if valor is None), None)
    if indice_livre is None:
        estado_pokemon["memorias"] = memorias
        return False

    habilidades = estado_pokemon.get("habilidades")
    if not isinstance(habilidades, list):
        habilidades = [None, None, None, None, None]
    if len(habilidades) < 5:
        habilidades = list(habilidades) + ([None] * (5 - len(habilidades)))
    habilidades = habilidades[:5]

    conhecidos = {
        str(x.get("Ataque", "")).strip().lower()
        for x in memorias
        if isinstance(x, dict) and str(x.get("Ataque", "")).strip()
    }
    conhecidos.update(
        str(x.get("Ataque", "")).strip().lower()
        for x in habilidades
        if isinstance(x, dict) and str(x.get("Ataque", "")).strip()
    )
    opcoes = [atk for atk in _ATAQUES_DISPONIVEIS if str(atk.get("Ataque", "")).strip().lower() not in conhecidos]
    if not opcoes:
        estado_pokemon["memorias"] = memorias
        return False
    memorias[indice_livre] = _ataque_com_nivel(random.choice(opcoes))
    estado_pokemon["memorias"] = memorias
    return True


def preencher_habilidades_iniciais(estado_pokemon: Dict[str, object], total_slots: int = 5) -> None:
    if not isinstance(estado_pokemon, dict):
        return
    quantidade = max(1, min(5, int(total_slots or 5)))
    habilidades = [None] * quantidade
    if _ATAQUES_DISPONIVEIS:
        escolhidos = random.sample(_ATAQUES_DISPONIVEIS, k=min(quantidade, len(_ATAQUES_DISPONIVEIS)))
        for i, ataque in enumerate(escolhidos):
            habilidades[i] = _ataque_com_nivel(ataque)
    estado_pokemon["habilidades"] = habilidades
    estado_pokemon["memorias"] = [None] * quantidade


def normalizar_habilidades_memorias(estado_pokemon: Dict[str, object], total_slots: int = 5) -> None:
    if not isinstance(estado_pokemon, dict):
        return
    quantidade = max(1, min(5, int(total_slots or 5)))
    habilidades = estado_pokemon.get("habilidades")
    memorias = estado_pokemon.get("memorias")
    if not isinstance(habilidades, list):
        habilidades = []
    if not isinstance(memorias, list):
        memorias = []
    habilidades = list(habilidades[:quantidade]) + [None] * max(0, quantidade - len(habilidades))
    memorias = [None] * quantidade

    conhecidos = {
        str(x.get("Ataque", "")).strip().lower()
        for x in habilidades
        if isinstance(x, dict) and str(x.get("Ataque", "")).strip()
    }
    opcoes = [atk for atk in _ATAQUES_DISPONIVEIS if str(atk.get("Ataque", "")).strip().lower() not in conhecidos]
    for i, ataque in enumerate(habilidades):
        if ataque is None and opcoes:
            escolhido = random.choice(opcoes)
            habilidades[i] = _ataque_com_nivel(escolhido)
            chave = str(escolhido.get("Ataque", "")).strip().lower()
            opcoes = [atk for atk in opcoes if str(atk.get("Ataque", "")).strip().lower() != chave]

    estado_pokemon["habilidades"] = habilidades
    estado_pokemon["memorias"] = memorias


def subir_nivel_pokemon(pokemon: Dict[str, object], vezes: int = 1) -> Dict[str, object]:
    dados = pokemon if isinstance(pokemon, dict) else {}
    estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else dados
    stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
    stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}
    nivel_atual = max(0, min(100, _inum(estado.get("nivel", 0), 0)))
    estado["XP"] = max(0, _inum(estado.get("XP", 0), 0))
    estado["XPAlvo"] = _xp_alvo_por_nivel(nivel_atual)

    ordem = STATS_VARIAVEIS_IV[:]
    for _ in range(max(0, int(vezes))):
        if nivel_atual >= 100:
            break
        stat = ordem[nivel_atual % len(ordem)]
        base = _fnum(stats_base.get(stat), _fnum(stats.get(stat), 0.0))
        stats[stat] = round(_fnum(stats.get(stat), base) + (base * 0.10), 2)
        nivel_atual += 1
        estado["nivel"] = nivel_atual
        estado["XPAlvo"] = _xp_alvo_por_nivel(nivel_atual)
        estado["poder"] = _recalcular_poder(stats)
        estado["poder_relativo"] = _recalcular_poder_relativo(stats)
    estado["vida_atual"] = round(_fnum(stats.get("Vida"), 0.0), 2)
    estado["stats"] = stats
    return dados


def materializar_pokemon(pokemon_mundo: Dict[str, object], efeitos_captura: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    bruto = dict(pokemon_mundo or {})
    estado = bruto.get("estado") if isinstance(bruto.get("estado"), dict) else bruto
    efeitos = efeitos_captura if isinstance(efeitos_captura, dict) else {}

    nivel_original = max(0, min(100, _inum(estado.get("nivel", 0), 0)))
    bonus_nivel = _inum(efeitos.get("bonus_nivel", 0), 0)
    bonus_iv = _inum(efeitos.get("bonus_iv", 0), 0)
    bonus_amizade = _inum(efeitos.get("bonus_amizade", 0), 0)
    escala_pokemon = _normalizar_escala_pokemon(estado.get("escala", bruto.get("escala", estado.get("tamanho", bruto.get("tamanho", 3)))), default=3)
    variacao_tamanho = _normalizar_variacao_tamanho(estado.get("variacao_tamanho", bruto.get("variacao_tamanho", 0)), default=0)
    tamanho_sigla = str(estado.get("tamanho", bruto.get("tamanho", _sigla_tamanho_por_variacao(variacao_tamanho))) or _sigla_tamanho_por_variacao(variacao_tamanho)).strip().upper()
    if tamanho_sigla not in {"S", "M", "G"}:
        tamanho_sigla = _sigla_tamanho_por_variacao(variacao_tamanho)

    iv = max(0, min(100, _inum(estado.get("iv", 0), 0) + bonus_iv))
    stats_base = {}
    stats_base_origem = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}
    for k in STATS_BASE:
        stats_base[k] = _fnum(stats_base_origem.get(k), _fnum(estado.get(k), 0.0))

    subivs = _gerar_subivs_media(iv)
    stats_final = {}
    for stat in STATS_VARIAVEIS_IV:
        base = _fnum(stats_base.get(stat), 0.0)
        mult = 0.75 + (_inum(subivs.get(stat), iv) / 200.0)
        stats_final[stat] = round(base * mult, 2)
    stats_final["CrC"] = round(_fnum(stats_base.get("CrC"), 0.0), 2)
    stats_final["CrD"] = round(_fnum(stats_base.get("CrD"), 0.0), 2)

    amizade_base = random.randint(15, 70) + bonus_amizade
    amizade = max(1, amizade_base - nivel_original)

    estado["iv"] = iv
    estado["subivs"] = subivs
    estado["stats_base"] = stats_base
    estado["stats"] = stats_final
    estado["amizade"] = int(amizade)
    estado["tipos"] = list(estado.get("tipos", [])) if isinstance(estado.get("tipos"), list) else []
    estado["nivel"] = 0
    estado["XP"] = 0
    estado["XPAlvo"] = _xp_alvo_por_nivel(0)
    estado["poder"] = _recalcular_poder(stats_final)
    estado["poder_relativo"] = _recalcular_poder_relativo(stats_final)
    estado["vida_atual"] = round(_fnum(stats_final.get("Vida"), 0.0), 2)
    estado["equipaveis"] = max(1, min(4, _inum(estado.get("equipaveis", 1), 1)))
    preencher_habilidades_iniciais(estado, total_slots=5)
    estado["fruta_favorita"] = random.choice(_FRUTAS_DISPONIVEIS) if _FRUTAS_DISPONIVEIS else ""
    estado["escala"] = int(escala_pokemon)
    estado["variacao_tamanho"] = int(variacao_tamanho)
    estado["tamanho"] = str(tamanho_sigla)
    estado["tamanho_tiles"] = round(_diametro_tiles_por_escala(escala_pokemon), 2)
    bruto["escala"] = int(escala_pokemon)
    bruto["variacao_tamanho"] = int(variacao_tamanho)
    bruto["tamanho"] = str(tamanho_sigla)

    subir_nivel_pokemon(estado, vezes=max(0, min(100, nivel_original + bonus_nivel)))
    normalizar_habilidades_memorias(estado, total_slots=5)
    return bruto


MaterializarPokemon = materializar_pokemon
SubirNivel = subir_nivel_pokemon


def criar_pokemon_inicial_materializado(especie: str) -> Dict[str, object]:
    row = _escolher_especie(especie)
    escala, variacao_tamanho, tamanho_sigla = _sortear_escala_e_tamanho(_normalizar_escala_pokemon(row.get("Tamanho", 3), default=3))
    bruto = {
        "id": 0,
        "especie": str(row.get("Nome", "Pokemon")),
        "nome": str(row.get("Nome", "Pokemon")),
        "nivel": 0,
        "iv": random.randint(10, 45),
        "subivs": {},
        "stats_base": {k: _fnum(row.get(k), 0.0) for k in STATS_BASE},
        "stats": {k: _fnum(row.get(k), 0.0) for k in STATS_BASE},
        "altura": round(_fnum(row.get("Altura"), 1.0), 3),
        "peso": round(_fnum(row.get("Peso"), 1.0), 3),
        "tipos": _sortear_tipos(row),
        "grupo": str(row.get("Grupo", "")),
        "raridade": int(_fnum(row.get("Raridade"), 1)),
        "estagio": int(_fnum(row.get("Estagio"), 1)),
        "escala": int(escala),
        "variacao_tamanho": int(variacao_tamanho),
        "tamanho": str(tamanho_sigla),
        "tamanho_tiles": round(_diametro_tiles_por_escala(escala), 2),
        "code": str(row.get("Code", "")),
        "linhagem": str(row.get("Linhagem", "")),
        "equipaveis": max(1, min(4, _inum(row.get("Equipaveis", 1), 1))),
        "chunk_origem": [0, 0],
    }
    return materializar_pokemon(bruto, efeitos_captura=None)


def _carregar_base() -> List[Dict[str, object]]:
    if not ARQUIVO_POKEMONS.exists():
        return []
    linhas: List[Dict[str, object]] = []
    with ARQUIVO_POKEMONS.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row.get("Nome"):
                continue
            raridade_raw = str(row.get("Raridade", "")).strip()
            if not raridade_raw:
                continue
            raridade = _fnum(raridade_raw, 0.0)
            if raridade < 1.0 or raridade > 10.0:
                continue
            linhas.append({"row": row, "peso_spawn": 1.0 / raridade})
    return linhas


_BASE_POKEMONS = _carregar_base()


def _escolher_especie(especie=None) -> Dict[str, str]:
    if not _BASE_POKEMONS:
        return {"Nome": "MissingNo", "Raridade": "10", "Altura": "1.0", "Peso": "1.0", **{k: "10" for k in STATS_BASE}}
    alvo = str(especie or "").strip().lower()
    if alvo:
        for item in _BASE_POKEMONS:
            row = item.get("row", {}) if isinstance(item, dict) else {}
            if str(row.get("Code", "")).strip().lower() == alvo or str(row.get("Nome", "")).strip().lower() == alvo:
                return row
    item = random.choices(_BASE_POKEMONS, weights=[x["peso_spawn"] for x in _BASE_POKEMONS], k=1)[0]
    return item["row"]


def gerar_pokemon_server(novo_id: int, posicao, chunk_xy, especie=None) -> PokemonServer:
    row = _escolher_especie(especie)
    iv_global = random.randint(0, 100)
    nivel = _nivel_baixo_comum(60)

    coef_genetico = random.uniform(0.5, 1.5)
    coef_altura = random.uniform(0.75, 1.25)
    coef_peso = random.uniform(0.75, 1.25)

    altura_base = _fnum(row.get("Altura"), 1.0)
    peso_base = _fnum(row.get("Peso"), 1.0)
    altura = round(altura_base * coef_genetico * coef_altura, 3)
    peso = round(peso_base * coef_genetico * coef_peso, 3)

    stats_base = {k: _fnum(row.get(k), 0.0) for k in STATS_BASE}
    tipos = _sortear_tipos(row)
    poder_base = _recalcular_poder(stats_base)
    dificuldade = round(poder_base * (iv_global / 100.0) * (nivel / 10.0), 2)
    tamanho_barra = round(max(0.05, 0.46 - (nivel / 160.0)), 3)
    velocidade_barra = round(min(260.0, 40.0 + (iv_global * 1.7)), 2)

    escala, variacao_tamanho, tamanho_sigla = _sortear_escala_e_tamanho(_normalizar_escala_pokemon(row.get("Tamanho", 3), default=3))
    raio_colisao = _raio_colisao_por_escala(escala)
    poke = PokemonServer(
        id_objeto=novo_id,
        especie=str(row.get("Nome", "Desconhecido")),
        posicao=posicao,
        raio_colisao=raio_colisao,
        raio_interacao=max(raio_colisao, 1.2),
    )
    poke.estado_extra.update(
        {
            "nivel": nivel,
            "iv": iv_global,
            "subivs": {},
            "stats_base": stats_base,
            "stats": dict(stats_base),
            "altura": altura,
            "peso": peso,
            "coeficiente_genetico": round(coef_genetico, 5),
            "coeficiente_altura": round(coef_altura, 5),
            "coeficiente_peso": round(coef_peso, 5),
            "tipos": tipos,
            "grupo": str(row.get("Grupo", "")),
            "raridade": int(_fnum(row.get("Raridade"), 1)),
            "estagio": int(_fnum(row.get("Estagio"), 1)),
            "escala": int(escala),
            "variacao_tamanho": int(variacao_tamanho),
            "tamanho": str(tamanho_sigla),
            "tamanho_tiles": round(_diametro_tiles_por_escala(escala), 2),
            "code": str(row.get("Code", "")),
            "linhagem": str(row.get("Linhagem", "")),
            "equipaveis": max(1, min(4, _inum(row.get("Equipaveis", 1), 1))),
            "poder": poder_base,
            "poder_relativo": _recalcular_poder_relativo(stats_base),
            "vida_atual": round(_fnum(stats_base.get("Vida"), 0.0), 2),
            "dificuldade_captura": dificuldade,
            "tamanho_barra_captura": tamanho_barra,
            "velocidade_barra_captura": velocidade_barra,
            "chunk_origem": [int(chunk_xy[0]), int(chunk_xy[1])],
        }
    )
    return poke
