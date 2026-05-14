"""Gerador de Pokémon do servidor (baseado em Dados/Pokemon Global Server - Pokemons.csv)."""

from __future__ import annotations

import random
import unicodedata
from copy import deepcopy
from Servidor.Gerais.LoaderTabelas import carregar_csv_dict
from typing import Dict, List, Optional

from Servidor.Mundo.ObjetosMundoServer import PokemonServer
from Servidor.Gerais.LoaderRegras import carregar_regras_pokemons

STATS_BASE = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int", "CrD", "CrC"]
STATS_VARIAVEIS_IV = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int"]
_REGRAS_POKEMON = carregar_regras_pokemons()


def _fnum(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _clamp01(v) -> float:
    return max(0.0, min(1.0, _fnum(v, 0.0)))


def _vida_atual_percentual(estado: Dict[str, object], vida_max: float) -> float:
    bruto = estado.get("VidaAtual", estado.get("vida_atual", None))
    if bruto is None:
        return 1.0
    valor = _fnum(bruto, 1.0)
    if 0.0 <= valor <= 1.0:
        return _clamp01(valor)
    return _clamp01(valor / max(1.0, float(vida_max)))


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
    base = float(_REGRAS_POKEMON.get("tamanho_diametro_base_tiles", 0.6))
    incremento = float(
        _REGRAS_POKEMON.get("tamanho_incremento_por_escala")
        if _REGRAS_POKEMON.get("tamanho_incremento_por_escala") is not None
        else _REGRAS_POKEMON.get("tamanho_incremento_por_tamanho", 0.1)
    )
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
    var_min = int(_REGRAS_POKEMON.get("tamanho_variacao_escala_min", -1))
    var_max = int(_REGRAS_POKEMON.get("tamanho_variacao_escala_max", 1))
    if var_min > var_max:
        var_min, var_max = var_max, var_min
    pool = list(range(var_min, var_max + 1))
    if not pool:
        pool = [0]
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


def _estado_pokemon(pokemon: Dict[str, object]) -> Dict[str, object]:
    if not isinstance(pokemon, dict):
        return {}
    return pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon


def _linhagem_regular(linhagem: str) -> List[Dict[str, str]]:
    alvo = str(linhagem or "").strip()
    if not alvo:
        return []
    rows: List[Dict[str, str]] = []
    for item in _BASE_POKEMONS:
        row = item.get("row", {}) if isinstance(item, dict) else {}
        if not isinstance(row, dict):
            continue
        if str(row.get("Linhagem", "") or "").strip() != alvo:
            continue
        if _row_eh_forma(row):
            continue
        rows.append(row)
    rows.sort(key=lambda r: (_inum(r.get("Estagio"), 0), _inum(r.get("Code"), 0)))
    return rows


def _sortear_pode_evoluir(estado: Dict[str, object], nivel_anterior: int) -> bool:
    if not isinstance(estado, dict) or bool(estado.get("PodeEvoluir", estado.get("pode_evoluir", False))):
        return False
    linhagem = str(estado.get("linhagem") or "").strip()
    rows = _linhagem_regular(linhagem)
    estagios = sorted({_inum(row.get("Estagio"), 0) for row in rows if _inum(row.get("Estagio"), 0) > 0})
    total = len(estagios)
    estagio_atual = _inum(estado.get("estagio"), 0)
    if total <= 1 or estagio_atual >= total:
        return False

    nivel_base = max(0, int(nivel_anterior))
    chance = 0.0
    if total == 2:
        chance = float(nivel_base)
    elif total == 3:
        if estagio_atual == 1:
            chance = 5.0 + float(nivel_base)
        elif estagio_atual == 2:
            chance = -10.0 + float(nivel_base)

    chance = max(0.0, min(100.0, chance))
    if chance > 0.0 and random.random() <= (chance / 100.0):
        estado["PodeEvoluir"] = True
        estado["pode_evoluir"] = True
        return True
    return False


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


def _total_csv_ou_stats(row: Dict[str, str]) -> float:
    total = _fnum(row.get("Total"), -1.0)
    if total >= 0.0:
        return float(total)
    return _recalcular_total({k: _fnum(row.get(k), 0.0) for k in STATS_BASE})


def _percentil_total_capturavel(row: Dict[str, str]) -> float:
    if len(_TOTAIS_CAPTURAVEIS_ORDENADOS) <= 1:
        return 0.0
    total = _total_csv_ou_stats(row)
    indices = [idx for idx, valor in enumerate(_TOTAIS_CAPTURAVEIS_ORDENADOS) if abs(float(valor) - total) <= 1e-9]
    if not indices:
        menores = sum(1 for valor in _TOTAIS_CAPTURAVEIS_ORDENADOS if float(valor) < total)
        return max(0.0, min(1.0, menores / max(1, len(_TOTAIS_CAPTURAVEIS_ORDENADOS) - 1)))
    rank_medio = (indices[0] + indices[-1]) / 2.0
    return max(0.0, min(1.0, rank_medio / max(1, len(_TOTAIS_CAPTURAVEIS_ORDENADOS) - 1)))


def _calcular_dificuldade_captura(row: Dict[str, str], iv: int, nivel: int) -> float:
    total_p = _percentil_total_capturavel(row)
    iv_p = _clamp01(float(iv) / 100.0)
    nivel_p = _clamp01(float(nivel) / 100.0)
    peso_total = float(_REGRAS_POKEMON.get("captura_dificuldade_peso_total", 0.70))
    peso_nivel = float(_REGRAS_POKEMON.get("captura_dificuldade_peso_nivel", 0.20))
    peso_iv = float(_REGRAS_POKEMON.get("captura_dificuldade_peso_iv", 0.10))
    exp_total = float(_REGRAS_POKEMON.get("captura_dificuldade_expoente_total", 1.18))
    exp_nivel = float(_REGRAS_POKEMON.get("captura_dificuldade_expoente_nivel", 0.85))
    exp_iv = float(_REGRAS_POKEMON.get("captura_dificuldade_expoente_iv", 0.90))
    dif_min = float(_REGRAS_POKEMON.get("captura_dificuldade_min", 10.0))
    dif_max = float(_REGRAS_POKEMON.get("captura_dificuldade_max", 120.0))
    score = (peso_total * (total_p ** exp_total)) + (peso_nivel * (nivel_p ** exp_nivel)) + (peso_iv * (iv_p ** exp_iv))
    return round(dif_min + ((dif_max - dif_min) * score), 2)


def _sortear_personalidade_mundo() -> str:
    opcoes = ["normal", "curioso", "medroso", "bravo", "super_bravo"]
    pesos = [
        max(0.0, float(_REGRAS_POKEMON.get("personalidade_mundo_peso_normal", 0.25))),
        max(0.0, float(_REGRAS_POKEMON.get("personalidade_mundo_peso_curioso", 0.35))),
        max(0.0, float(_REGRAS_POKEMON.get("personalidade_mundo_peso_medroso", 0.35))),
        max(0.0, float(_REGRAS_POKEMON.get("personalidade_mundo_peso_bravo", 0.20))),
        max(0.0, float(_REGRAS_POKEMON.get("personalidade_mundo_peso_super_bravo", 0.10))),
    ]
    if sum(pesos) <= 0.0:
        pesos = [0.25, 0.35, 0.35, 0.20, 0.10]
    return random.choices(opcoes, weights=pesos, k=1)[0]


def _carregar_frutas() -> List[str]:
    frutas: List[str] = []
    try:
        linhas = carregar_csv_dict("Pokemon Global Server - Itens.csv")
    except OSError:
        return frutas
    for row in linhas:
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
    ataques: List[Dict[str, object]] = []
    try:
        linhas = carregar_csv_dict("Pokemon Global Server - Ataques.csv")
    except OSError:
        return ataques
    for row in linhas:
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

def gerar_ataque_aleatorio(excluir: Optional[set[str]] = None) -> Optional[Dict[str, object]]:
    if not _ATAQUES_DISPONIVEIS:
        return None
    pool = _ATAQUES_DISPONIVEIS
    if excluir:
        pool = [atk for atk in _ATAQUES_DISPONIVEIS if str(atk.get("Ataque", "")).strip().lower() not in excluir]
    if not pool:
        return None
    return _ataque_com_nivel(random.choice(pool))


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
    estado["vida_atual"] = round(_vida_atual_percentual(estado, _fnum(stats.get("Vida"), 1.0)), 4)
    estado["stats"] = stats
    return dados


def ganhar_xp_pokemon(pokemon: Dict[str, object], quantidade_xp: int = 0) -> Dict[str, int]:
    estado = _estado_pokemon(pokemon)
    if not estado:
        return {"xp_ganho": 0, "niveis_ganhos": 0, "nivel_atual": 0, "xp_atual": 0, "xp_alvo": 0}

    ganho = max(0, _inum(quantidade_xp, 0))
    nivel = max(0, min(100, _inum(estado.get("nivel", estado.get("Nivel", 0)), 0)))
    xp = max(0, _inum(estado.get("XP", estado.get("xp", 0)), 0)) + ganho
    niveis = 0

    while nivel < 100:
        xp_alvo = _xp_alvo_por_nivel(nivel)
        if xp_alvo <= 0 or xp < xp_alvo:
            break
        nivel_anterior = nivel
        xp -= xp_alvo
        estado["XP"] = xp
        estado["xp"] = xp
        subir_nivel_pokemon(estado, vezes=1)
        nivel = max(0, min(100, _inum(estado.get("nivel", nivel + 1), nivel + 1)))
        niveis += 1
        _sortear_pode_evoluir(estado, nivel_anterior)

    if nivel >= 100:
        xp = 0
    xp_alvo = _xp_alvo_por_nivel(nivel)
    estado["nivel"] = int(nivel)
    estado["XP"] = int(xp)
    estado["xp"] = int(xp)
    estado["XPAlvo"] = int(xp_alvo)
    estado["xp_alvo"] = int(xp_alvo)
    return {
        "xp_ganho": int(ganho),
        "niveis_ganhos": int(niveis),
        "nivel_atual": int(nivel),
        "xp_atual": int(xp),
        "xp_alvo": int(xp_alvo),
    }


def evoluir_pokemon(pokemon: Dict[str, object]) -> Dict[str, object]:
    dados = pokemon if isinstance(pokemon, dict) else {}
    estado = _estado_pokemon(dados)
    if not estado or not bool(estado.get("PodeEvoluir", estado.get("pode_evoluir", False))):
        return {"evoluiu": False}

    row_base = _row_base_por_pokemon(dados)
    linhagem = str(row_base.get("Linhagem") or estado.get("linhagem") or "").strip()
    estagio_atual = _inum(estado.get("estagio", row_base.get("Estagio", 1)), 1)
    candidatos = [row for row in _linhagem_regular(linhagem) if _inum(row.get("Estagio"), 0) == estagio_atual + 1]
    if not candidatos:
        return {"evoluiu": False}
    row = candidatos[0]

    nivel = max(0, min(100, _inum(estado.get("nivel", 0), 0)))
    xp = max(0, _inum(estado.get("XP", estado.get("xp", 0)), 0))
    iv = max(0, min(100, _inum(estado.get("iv", 0), 0)))
    subivs = deepcopy(estado.get("subivs")) if isinstance(estado.get("subivs"), dict) else _gerar_subivs_media(iv)
    coef_genetico = _fnum(estado.get("coeficiente_genetico"), 1.0)
    coef_altura = _fnum(estado.get("coeficiente_altura"), 1.0)
    coef_peso = _fnum(estado.get("coeficiente_peso"), 1.0)
    tamanho_sigla = str(estado.get("tamanho", "M") or "M").strip().upper()
    if tamanho_sigla not in {"S", "M", "G"}:
        tamanho_sigla = "M"
    variacao_tamanho = {"S": -1, "M": 0, "G": 1}.get(tamanho_sigla, 0)
    escala = _normalizar_escala_pokemon(_normalizar_escala_pokemon(row.get("Tamanho", 3), default=3) + variacao_tamanho, default=3)
    ataques = {
        chave: deepcopy(estado.get(chave))
        for chave in ("habilidades", "memorias", "Habilidades", "Memoria", "Ataques")
        if isinstance(estado.get(chave), list)
    }

    stats_base = {k: _fnum(row.get(k), 0.0) for k in STATS_BASE}
    stats = {}
    for stat in STATS_VARIAVEIS_IV:
        base = _fnum(stats_base.get(stat), 0.0)
        mult = 0.75 + (_inum(subivs.get(stat), iv) / 200.0)
        stats[stat] = round(base * mult, 2)
    stats["CrC"] = round(_fnum(stats_base.get("CrC"), 0.0), 2)
    stats["CrD"] = round(_fnum(stats_base.get("CrD"), 0.0), 2)

    nome_anterior = str(estado.get("especie") or estado.get("nome") or dados.get("especie") or dados.get("nome") or "")
    nome_novo = str(row.get("Nome", "Pokemon"))
    estado.update(
        {
            "especie": nome_novo,
            "nome": nome_novo,
            "nivel": 0,
            "iv": iv,
            "subivs": subivs,
            "stats_base": stats_base,
            "stats": stats,
            "altura": round(_fnum(row.get("Altura"), 1.0) * coef_genetico * coef_altura, 3),
            "peso": round(_fnum(row.get("Peso"), 1.0) * coef_genetico * coef_peso, 3),
            "coeficiente_genetico": round(coef_genetico, 5),
            "coeficiente_altura": round(coef_altura, 5),
            "coeficiente_peso": round(coef_peso, 5),
            "tipos": _sortear_tipos(row),
            "Grupo": str(row.get("Grupo", "")),
            "grupo": str(row.get("Grupo", "")),
            "raridade": int(_fnum(row.get("Raridade"), 1)),
            "estagio": int(_fnum(row.get("Estagio"), estagio_atual + 1)),
            "escala": int(escala),
            "variacao_tamanho": int(variacao_tamanho),
            "tamanho": str(tamanho_sigla),
            "tamanho_tiles": round(_diametro_tiles_por_escala(escala), 2),
            "code": str(row.get("Code", "")),
            "linhagem": str(row.get("Linhagem", "")),
            "equipaveis": max(1, min(4, _inum(row.get("Equipaveis", 1), 1))),
            "XP": 0,
            "xp": 0,
            "XPAlvo": _xp_alvo_por_nivel(0),
            "xp_alvo": _xp_alvo_por_nivel(0),
            "PodeEvoluir": False,
            "pode_evoluir": False,
        }
    )
    estado.update(ataques)
    subir_nivel_pokemon(estado, vezes=nivel)
    estado["XP"] = int(xp)
    estado["xp"] = int(xp)
    estado["XPAlvo"] = _xp_alvo_por_nivel(nivel)
    estado["xp_alvo"] = estado["XPAlvo"]
    estado["poder"] = _recalcular_poder(estado.get("stats", {}))
    estado["poder_relativo"] = _recalcular_poder_relativo(estado.get("stats", {}))
    estado["vida_atual"] = round(_vida_atual_percentual(estado, _fnum(estado.get("stats", {}).get("Vida"), 1.0)), 4)
    if isinstance(dados, dict) and dados is not estado:
        dados["especie"] = nome_novo
        dados["nome"] = nome_novo
        dados["code"] = str(row.get("Code", ""))
    return {"evoluiu": True, "de": nome_anterior, "para": nome_novo}


def materializar_pokemon(pokemon_mundo: Dict[str, object], efeitos_captura: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    bruto = dict(pokemon_mundo or {})
    estado = bruto.get("estado") if isinstance(bruto.get("estado"), dict) else bruto
    efeitos = efeitos_captura if isinstance(efeitos_captura, dict) else {}
    for chave in (
        "personalidade_mundo",
        "esta_irritado",
        "motivo_irritado",
        "alvo_player_id",
        "comportamento_mundo",
        "destino_fuga",
        "destino_perseguicao",
        "tentativas_falhas_captura",
        "dificuldade_captura",
        "dificuldade_captura_base",
        "captura",
        "captura_fase",
        "cooldown_movimento_ate_tick",
    ):
        estado.pop(chave, None)
        bruto.pop(chave, None)

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
    estado["Grupo"] = str(estado.get("Grupo", estado.get("grupo", "")))
    estado["grupo"] = str(estado.get("grupo", estado.get("Grupo", "")))
    estado["nivel"] = 0
    estado["XP"] = 0
    estado["xp"] = 0
    estado["XPAlvo"] = _xp_alvo_por_nivel(0)
    estado["xp_alvo"] = estado["XPAlvo"]
    estado["PodeEvoluir"] = False
    estado["pode_evoluir"] = False
    estado["poder"] = _recalcular_poder(stats_final)
    estado["poder_relativo"] = _recalcular_poder_relativo(stats_final)
    estado["vida_atual"] = 1.0
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
GanharXP = ganhar_xp_pokemon
EvoluirPokemon = evoluir_pokemon


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
        "Grupo": str(row.get("Grupo", "")),
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


def _row_eh_forma(row: Dict[str, str]) -> bool:
    estagio = str(row.get("Estagio", "") or "").strip().upper()
    ff = str(row.get("FF", "") or row.get("F", "") or "").strip().upper()
    if estagio in {"F", "FF"}:
        return True
    return bool(ff and ff not in {"0", "N", "NAO", "NÃO", "FALSE"})


def _row_base_por_pokemon(pokemon_base: Dict[str, object]) -> Dict[str, str]:
    estado = pokemon_base.get("estado") if isinstance(pokemon_base.get("estado"), dict) else pokemon_base
    code = str(estado.get("code") or pokemon_base.get("code") or "").strip()
    especie = str(estado.get("especie") or estado.get("nome") or pokemon_base.get("especie") or pokemon_base.get("nome") or "").strip()
    return _escolher_especie(code or especie)


def _especies_bando_possiveis(pokemon_base: Dict[str, object]) -> List[Dict[str, str]]:
    row_base = _row_base_por_pokemon(pokemon_base)
    linhagem = str(row_base.get("Linhagem", "") or "").strip()
    try:
        estagio_base = int(float(row_base.get("Estagio", 1) or 1))
    except (TypeError, ValueError):
        estagio_base = 1
    if not linhagem:
        return []
    candidatos: List[Dict[str, str]] = []
    for item in _BASE_POKEMONS:
        row = item.get("row", {}) if isinstance(item, dict) else {}
        if not isinstance(row, dict):
            continue
        if str(row.get("Linhagem", "") or "").strip() != linhagem:
            continue
        if _row_eh_forma(row):
            continue
        try:
            estagio = int(float(row.get("Estagio", 1) or 1))
        except (TypeError, ValueError):
            continue
        if estagio <= estagio_base:
            candidatos.append(row)
    return candidatos


def _materializar_membro_bando(row: Dict[str, str], pokemon_base: Dict[str, object], indice: int) -> Dict[str, object]:
    estado_base = pokemon_base.get("estado") if isinstance(pokemon_base.get("estado"), dict) else pokemon_base
    nivel_base = max(0, _inum(estado_base.get("nivel", pokemon_base.get("nivel", 0)), 0))
    delta = max(1, int(round(max(1, nivel_base) * 0.20)))
    nivel = max(0, min(100, nivel_base + random.randint(-delta, delta)))
    escala, variacao_tamanho, tamanho_sigla = _sortear_escala_e_tamanho(_normalizar_escala_pokemon(row.get("Tamanho", 3), default=3))
    bruto = {
        "id": f"bando_{estado_base.get('code') or row.get('Code')}_{random.randint(100000, 999999)}_{indice}",
        "especie": str(row.get("Nome", "Pokemon")),
        "nome": str(row.get("Nome", "Pokemon")),
        "nivel": nivel,
        "iv": max(0, min(100, _inum(estado_base.get("iv", random.randint(0, 100)), random.randint(0, 100)) + random.randint(-10, 10))),
        "stats_base": {k: _fnum(row.get(k), 0.0) for k in STATS_BASE},
        "stats": {k: _fnum(row.get(k), 0.0) for k in STATS_BASE},
        "altura": round(_fnum(row.get("Altura"), 1.0), 3),
        "peso": round(_fnum(row.get("Peso"), 1.0), 3),
        "tipos": _sortear_tipos(row),
        "Grupo": str(row.get("Grupo", "")),
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
        "chunk_origem": list(estado_base.get("chunk_origem", [])) if isinstance(estado_base.get("chunk_origem"), list) else [],
    }
    return materializar_pokemon(bruto, efeitos_captura=None)


def gerar_bando_confronto(pokemon_confrontado: Dict[str, object], max_extras: int = 5) -> List[Dict[str, object]]:
    """Gera o time selvagem ao redor do Pokemon confrontado.

    O primeiro membro sempre e o Pokemon encontrado; os extras tentam seguir a
    mesma linhagem, sem formas especiais, com estagio igual ou inferior.
    """
    if not isinstance(pokemon_confrontado, dict):
        return []
    time = [dict(pokemon_confrontado)]
    candidatos = _especies_bando_possiveis(pokemon_confrontado)
    if not candidatos:
        return time
    total_desejado = random.choices([1, 2, 3, 4, 5, 6], weights=[7, 18, 45, 21, 7, 2], k=1)[0]
    total_desejado = max(1, min(1 + max(0, int(max_extras or 5)), int(total_desejado)))
    contagem = {}
    estado_base = pokemon_confrontado.get("estado") if isinstance(pokemon_confrontado.get("estado"), dict) else pokemon_confrontado
    nome_base = str(estado_base.get("especie") or estado_base.get("nome") or pokemon_confrontado.get("especie") or pokemon_confrontado.get("nome") or "").strip()
    if nome_base:
        contagem[nome_base.casefold()] = 1
    tentativas = 0
    while len(time) < total_desejado and tentativas < 80:
        tentativas += 1
        row = random.choice(candidatos)
        nome = str(row.get("Nome", "Pokemon")).strip()
        chave = nome.casefold()
        if contagem.get(chave, 0) >= 3:
            continue
        time.append(_materializar_membro_bando(row, pokemon_confrontado, len(time)))
        contagem[chave] = contagem.get(chave, 0) + 1
    return time


def _carregar_base() -> List[Dict[str, object]]:
    linhas: List[Dict[str, object]] = []
    try:
        base_rows = carregar_csv_dict("Pokemon Global Server - Pokemons.csv")
    except OSError:
        return linhas
    for row in base_rows:
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
_TOTAIS_CAPTURAVEIS_ORDENADOS = sorted(_total_csv_ou_stats(item.get("row", {})) for item in _BASE_POKEMONS if isinstance(item, dict))


def _escolher_especie(especie=None) -> Dict[str, str]:
    if not _BASE_POKEMONS:
        return {"Nome": "MissingNo", "Raridade": "10", "Altura": "1.0", "Peso": "1.0", **{k: "10" for k in STATS_BASE}}
    alvo = str(especie or "").strip().lower()
    if alvo:
        alvo_slug = "".join(ch for ch in unicodedata.normalize("NFKD", alvo).encode("ascii", "ignore").decode("ascii") if ch.isalnum())
        for item in _BASE_POKEMONS:
            row = item.get("row", {}) if isinstance(item, dict) else {}
            if str(row.get("Code", "")).strip().lower() == alvo or str(row.get("Nome", "")).strip().lower() == alvo:
                return row
            nome_slug = "".join(ch for ch in unicodedata.normalize("NFKD", str(row.get("Nome", "")).strip().lower()).encode("ascii", "ignore").decode("ascii") if ch.isalnum())
            if nome_slug and nome_slug == alvo_slug:
                return row
        return {"Nome": "MissingNo", "Raridade": "10", "Altura": "1.0", "Peso": "1.0", **{k: "10" for k in STATS_BASE}}
    item = random.choices(_BASE_POKEMONS, weights=[x["peso_spawn"] for x in _BASE_POKEMONS], k=1)[0]
    return item["row"]


def listar_candidatos_spawn_pokemon() -> List[Dict[str, str]]:
    return [dict(item.get("row", {})) for item in _BASE_POKEMONS if isinstance(item, dict)]


def gerar_pokemon_server(novo_id: int, posicao, chunk_xy, especie=None, row_pokemon: Optional[Dict[str, str]] = None) -> PokemonServer:
    row = dict(row_pokemon) if isinstance(row_pokemon, dict) else _escolher_especie(especie)
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
    dificuldade = _calcular_dificuldade_captura(row, iv_global, nivel)
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
            "Grupo": str(row.get("Grupo", "")),
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
            "vida_atual": 1.0,
            "PodeEvoluir": False,
            "pode_evoluir": False,
            "dificuldade_captura": dificuldade,
            "dificuldade_captura_base": dificuldade,
            "tentativas_falhas_captura": 0,
            "esta_irritado": False,
            "personalidade_mundo": _sortear_personalidade_mundo(),
            "tamanho_barra_captura": tamanho_barra,
            "velocidade_barra_captura": velocidade_barra,
            "chunk_origem": [int(chunk_xy[0]), int(chunk_xy[1])],
        }
    )
    return poke
