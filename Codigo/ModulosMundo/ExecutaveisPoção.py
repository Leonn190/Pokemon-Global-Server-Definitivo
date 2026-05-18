from __future__ import annotations

import unicodedata

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict

from Codigo.ModulosGerais.GerenciadorPokemons import ganhar_xp_pokemon, aprender_ataque_aleatorio, aprender_ataque_tm

_CACHE_POCOES = None
_CACHE_ITENS = None


def _normalizar_nome(nome: str) -> str:
    base = unicodedata.normalize("NFKD", str(nome or "").strip().lower())
    base = "".join(c for c in base if not unicodedata.combining(c))
    return " ".join(base.replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e").split())


def _valor_vida(pokemon: dict, chave, padrao=0.0) -> float:
    try:
        return float(pokemon.get(chave, padrao) or padrao)
    except (TypeError, ValueError):
        return float(padrao)


def _vida_absoluta(alvo: dict, vida_max: float) -> float:
    valor = _valor_vida(alvo, "VidaAtual", _valor_vida(alvo, "vida_atual", vida_max))
    if 0.0 <= valor <= 1.0:
        return valor * max(1.0, vida_max)
    return valor


def _definir_vida_percentual(alvo: dict, vida: float, vida_max: float):
    percentual = max(0.0, min(1.0, float(vida) / max(1.0, float(vida_max))))
    alvo["VidaAtual"] = percentual
    alvo["vida_atual"] = percentual


def _dados_pocao(nome_pocao: str) -> dict:
    global _CACHE_POCOES
    if _CACHE_POCOES is None:
        _CACHE_POCOES = {}
        try:
            for linha in carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8"):
                    if _normalizar_nome(linha.get("Estilo", "")) != _normalizar_nome("poção"):
                        continue
                    _CACHE_POCOES[_normalizar_nome(linha.get("Nome", ""))] = dict(linha)
        except OSError:
            _CACHE_POCOES = {}
    alvo = _normalizar_nome(nome_pocao)
    return dict(_CACHE_POCOES.get(alvo, {}))


def _dados_item_por_nome(nome_item: str) -> dict:
    global _CACHE_ITENS
    if _CACHE_ITENS is None:
        _CACHE_ITENS = {}
        try:
            for linha in carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8"):
                nome = str(linha.get("Nome") or "").strip()
                if nome:
                    _CACHE_ITENS[_normalizar_nome(nome)] = dict(linha)
        except OSError:
            _CACHE_ITENS = {}
    return dict(_CACHE_ITENS.get(_normalizar_nome(nome_item), {}))


def _aplicar_xp(pokemon: dict, quantidade: float):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    ganho = int(max(0, round(float(quantidade))))
    ganhar_xp_pokemon(alvo, ganho)


def _curar(pokemon: dict, cura: float):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    stats = alvo.get("stats") if isinstance(alvo.get("stats"), dict) else {}
    vida_max = max(1.0, _valor_vida(alvo, "Vida", _valor_vida(stats, "Vida", 1)))
    vida_atual = _vida_absoluta(alvo, vida_max)
    if vida_atual <= 0:
        return False
    nova_vida = min(vida_max, vida_atual + max(0.0, float(cura)))
    _definir_vida_percentual(alvo, nova_vida, vida_max)
    return True


def _reviver(pokemon: dict, percentual_vida: float):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    stats = alvo.get("stats") if isinstance(alvo.get("stats"), dict) else {}
    vida_max = max(1.0, _valor_vida(alvo, "Vida", _valor_vida(stats, "Vida", 1)))
    vida_atual = _vida_absoluta(alvo, vida_max)
    if vida_atual > 0:
        return False
    revivido = max(1.0, vida_max * max(0.01, min(1.0, float(percentual_vida))))
    _definir_vida_percentual(alvo, revivido, vida_max)
    return True


def _aplicar_pocao_suprema(pokemon: dict):
    alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    alvo["pocao_suprema"] = True
    alvo["PocaoSuprema"] = True
    if alvo is not pokemon:
        pokemon["pocao_suprema"] = True
        pokemon["PocaoSuprema"] = True
    return True


def executar_pocao(nome_pocao: str, pokemon: dict) -> dict:
    dados = _dados_pocao(nome_pocao)
    nome = str(dados.get("Nome") or nome_pocao or "").strip()
    try:
        fator = float(dados.get("Fator") or 0)
    except (TypeError, ValueError):
        fator = 0.0
    desc = str(dados.get("Descrição") or "")
    n = _normalizar_nome(nome)

    if n == _normalizar_nome("Pocao Suprema"):
        aplicado = _aplicar_pocao_suprema(pokemon)
        return {"ok": aplicado, "tipo": "pocao_suprema", "nome": nome, "descricao": desc}

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


def executar_tm(pokemon: dict, elite: bool = False) -> dict:
    nome_item = "Elite TM" if elite else "TM"
    dados = _dados_item_por_nome(nome_item)
    nome = str(dados.get("Nome") or nome_item).strip()
    desc = ""
    for chave, valor in dados.items():
        if _normalizar_nome(chave) == _normalizar_nome("Descricao"):
            desc = str(valor or "")
            break
    resultado = aprender_ataque_tm(pokemon, elite=elite)
    if not bool(resultado.get("ok", False)):
        return {
            "ok": False,
            "tipo": "tm",
            "elite": bool(elite),
            "nome": nome,
            "motivo": str(resultado.get("motivo") or "sem_opcoes"),
        }
    return {
        "ok": True,
        "tipo": "tm",
        "elite": bool(elite),
        "nome": nome,
        "ataque": resultado.get("ataque"),
        "descricao": desc,
    }


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


def executar_pocao_suprema(pokemon: dict) -> dict:
    return executar_pocao("Pocao Suprema", pokemon)


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


def executar_tm_comum(pokemon: dict) -> dict:
    return executar_tm(pokemon, elite=False)


def executar_elite_tm(pokemon: dict) -> dict:
    return executar_tm(pokemon, elite=True)


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
