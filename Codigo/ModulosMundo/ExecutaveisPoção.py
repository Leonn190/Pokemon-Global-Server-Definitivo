from __future__ import annotations

import csv
from pathlib import Path

from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import ganhar_xp_pokemon, aprender_ataque_aleatorio

_ARQ_ITENS = Path("Dados") / "Pokemon Global Server - Itens.csv"
_CACHE_POCOES = None


def _normalizar_nome(nome: str) -> str:
    return " ".join(str(nome or "").strip().lower().replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e").split())


def _valor_vida(pokemon: dict, chave, padrao=0.0) -> float:
    try:
        return float(pokemon.get(chave, padrao) or padrao)
    except (TypeError, ValueError):
        return float(padrao)


def _dados_pocao(nome_pocao: str) -> dict:
    global _CACHE_POCOES
    if _CACHE_POCOES is None:
        _CACHE_POCOES = {}
        try:
            with _ARQ_ITENS.open("r", encoding="utf-8") as arquivo:
                leitor = csv.DictReader(arquivo)
                for linha in leitor:
                    if _normalizar_nome(linha.get("Estilo", "")) != _normalizar_nome("poção"):
                        continue
                    _CACHE_POCOES[_normalizar_nome(linha.get("Nome", ""))] = dict(linha)
        except OSError:
            _CACHE_POCOES = {}
    alvo = _normalizar_nome(nome_pocao)
    return dict(_CACHE_POCOES.get(alvo, {}))


def _aplicar_xp(pokemon: dict, quantidade: float):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    ganho = int(max(0, round(float(quantidade))))
    ganhar_xp_pokemon(alvo, ganho)


def _curar(pokemon: dict, cura: float):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    vida_atual = _valor_vida(alvo, "VidaAtual", _valor_vida(alvo, "vida_atual", _valor_vida(alvo, "Vida", 0)))
    if vida_atual <= 0:
        return False
    stats = alvo.get("stats") if isinstance(alvo.get("stats"), dict) else {}
    vida_max = max(1.0, _valor_vida(alvo, "Vida", _valor_vida(stats, "Vida", vida_atual)))
    nova_vida = min(vida_max, vida_atual + max(0.0, float(cura)))
    alvo["VidaAtual"] = nova_vida
    alvo["vida_atual"] = nova_vida
    return True


def _reviver(pokemon: dict, percentual_vida: float):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    vida_atual = _valor_vida(alvo, "VidaAtual", _valor_vida(alvo, "vida_atual", _valor_vida(alvo, "Vida", 0)))
    if vida_atual > 0:
        return False
    stats = alvo.get("stats") if isinstance(alvo.get("stats"), dict) else {}
    vida_max = max(1.0, _valor_vida(alvo, "Vida", _valor_vida(stats, "Vida", 1)))
    revivido = max(1.0, vida_max * max(0.01, min(1.0, float(percentual_vida))))
    alvo["VidaAtual"] = revivido
    alvo["vida_atual"] = revivido
    return True


def executar_pocao(nome_pocao: str, pokemon: dict) -> dict:
    dados = _dados_pocao(nome_pocao)
    nome = str(dados.get("Nome") or nome_pocao or "").strip()
    fator = float(dados.get("Fator") or 0)
    desc = str(dados.get("Descrição") or "")
    n = _normalizar_nome(nome)

    tipos = {
        _normalizar_nome("Max Revival"): ("revival", 1.0),
        _normalizar_nome("Revival"): ("revival", 0.5),
        _normalizar_nome("Revive Maximo"): ("revival", 1.0),
        _normalizar_nome("Revive"): ("revival", 0.5),
        _normalizar_nome("Elixir"): ("xp", None),
        _normalizar_nome("Super Elixir"): ("xp", None),
        _normalizar_nome("Hiper Elixir"): ("xp", None),
        _normalizar_nome("Mega Elixir"): ("xp", None),
    }
    tipo_cfg = tipos.get(n)

    if tipo_cfg and tipo_cfg[0] == "revival":
        aplicado = _reviver(pokemon, float(tipo_cfg[1]))
        return {"ok": aplicado, "tipo": "revival", "nome": nome, "descricao": desc}
    if tipo_cfg and tipo_cfg[0] == "xp":
        _aplicar_xp(pokemon, fator)
        return {"ok": True, "tipo": "xp", "nome": nome, "valor": fator, "descricao": desc}

    aplicado = _curar(pokemon, fator)
    return {"ok": aplicado, "tipo": "cura", "nome": nome, "valor": fator, "descricao": desc}


def executar_pocao_pocao(pokemon: dict) -> dict:
    return executar_pocao("Poção", pokemon)


def executar_pocao_super(pokemon: dict) -> dict:
    return executar_pocao("Super Poção", pokemon)


def executar_pocao_hiper(pokemon: dict) -> dict:
    return executar_pocao("Hiper Poção", pokemon)


def executar_pocao_mega(pokemon: dict) -> dict:
    return executar_pocao("Mega Poção", pokemon)


def executar_pocao_maxima(pokemon: dict) -> dict:
    return executar_pocao("Poção Maxima", pokemon)


def executar_pocao_elixir(pokemon: dict) -> dict:
    return executar_pocao("Elixir", pokemon)


def executar_pocao_super_elixir(pokemon: dict) -> dict:
    return executar_pocao("Super Elixir", pokemon)


def executar_pocao_hiper_elixir(pokemon: dict) -> dict:
    return executar_pocao("Hiper Elixir", pokemon)


def executar_pocao_mega_elixir(pokemon: dict) -> dict:
    return executar_pocao("Mega Elixir", pokemon)


def executar_revive(pokemon: dict) -> dict:
    return executar_pocao("Revive", pokemon)


def executar_revive_maximo(pokemon: dict) -> dict:
    return executar_pocao("Revive Maximo", pokemon)


def executar_doce(item_doce: dict, pokemon: dict) -> dict:
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    try:
        xp_alvo = int(alvo.get("XPAlvo", 0) or 0)
    except (TypeError, ValueError):
        xp_alvo = 0
    if xp_alvo <= 0:
        try:
            nivel = int(alvo.get("nivel", 1) or 1)
        except (TypeError, ValueError):
            nivel = 1
        xp_alvo = max(1, (max(0, min(100, nivel)) + 1) * 100)
    ganho = max(1, int(round(xp_alvo * 0.10)))
    ganhar_xp_pokemon(alvo, ganho)
    novo_ataque = aprender_ataque_aleatorio(alvo, forcar=False)
    return {"ok": True, "tipo": "doce", "xp": ganho, "novo_ataque": bool(novo_ataque), "grupo": str(item_doce.get("Grupo") or "")}
