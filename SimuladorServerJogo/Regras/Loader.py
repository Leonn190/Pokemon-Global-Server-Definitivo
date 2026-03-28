from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_BASE = Path(__file__).resolve().parent


def _ler_json(nome: str) -> Dict[str, object]:
    arq = _BASE / nome
    try:
        data = json.loads(arq.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def carregar_regras_player() -> Dict[str, object]:
    base = {
        "NivelMochila": 1,
        "LimiteSlotsInventario": 32,
        "LimitePokemons": 64,
        "LimiteTimesPokemon": 6,
        "Ouro": 0,
        "Maestria": 0,
        "StaminaMax": 100.0,
        "VelocidadeBaseTiles": 5.0,
        "BonusVelocidadeCorridaMin": 0.25,
        "BonusVelocidadeCorridaMax": 0.5,
        "TempoAceleracaoCorrida": 2.5,
        "TempoDesaceleracaoCorrida": 2.0,
        "AtrasoRegeneracaoStamina": 1.5,
        "RegeneracaoStaminaParado": 12.0,
        "RegeneracaoStaminaAndando": 5.0,
        "CustoStaminaCorrida": 10.0,
        "CustoStaminaCorridaMax": 16.0,
        "CustoStaminaAguaRasa": 4.0,
        "CustoStaminaAguaFunda": 16.0,
        "TapaPorSegundo": 2.0,
    }
    base.update(_ler_json("Player.json"))
    return base


def carregar_regras_cerebro() -> Dict[str, object]:
    base = {
        "tick_segundos": 0.0333,
        "chance_spawn_pokemon_por_tick": 0.02,
        "limite_spawn_pokemon_100_ticks": 4,
        "chance_spawn_bau_por_tick": 0.015,
        "limite_spawn_bau_100_ticks": 2,
        "limite_pokemons_chunk": 2,
        "limite_baus_chunk": 1,
        "limite_total_baus": 60,
        "limite_total_pokemons": 100,
        "tentativas_spawn_bau": 5,
        "tentativas_spawn_pokemon": 5,
        "chance_movimento_pokemon_por_tick": 0.008,
        "intervalo_minimo_apos_movimento_ticks": 40,
        "tempo_maximo_movimento_ticks": 150,
        "velocidade_base_pokemon_tiles_s": 3.0,
        "chance_despawn_bau_simulado_por_tick": 0.002,
        "chance_despawn_pokemon_simulado_por_tick": 0.003,
        "raio_chunks_simulados": 3,
        "raio_chunks_carregados": 4,
    }
    base.update(_ler_json("Cerebro.json"))
    return base


def carregar_regras_mundo() -> Dict[str, object]:
    base = {"ChunkTiles": 10}
    base.update(_ler_json("Mundo.json"))
    return base



def carregar_regras_estruturas_naturais() -> Dict[str, object]:
    base = {"tipos": {}}
    base.update(_ler_json("EstruturasNaturais.json"))
    tipos = base.get("tipos") if isinstance(base.get("tipos"), dict) else {}
    base["tipos"] = tipos
    return base
