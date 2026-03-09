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
    }
    base.update(_ler_json("Player.json"))
    return base


def carregar_regras_cerebro() -> Dict[str, object]:
    base = {
        "tick_segundos": 0.2,
        "anel_render_chunks": 7,
        "anel_simulado_chunks": 13,
        "chance_spawn_por_tick": 0.35,
        "chance_mover_por_tick": 0.45,
        "max_pokemon_por_chunk_simulado": 3,
        "max_pokemon_por_chunk_carregado": 0.12,
        "maior_vetor_movimento_pokemon": 3.0,
        "velocidade_pokemon_tiles_s": 5.5,
        "raio_colisao_pokemon": 0.725,
        "tentativas_spawn_chunk": 12,
        "tiles_bloqueados": [0, 1, 2],
        "chance_spawn_bau_por_tick": 0.03,
        "max_bau_por_chunk_simulado": 1,
        "max_bau_por_chunk_carregado": 0.03,
        "tentativas_spawn_bau_chunk": 8,
        "ttl_bau_aberto_segundos": 5.0,
    }
    base.update(_ler_json("Cerebro.json"))
    return base


def carregar_regras_mundo() -> Dict[str, object]:
    base = {"ChunkTiles": 10}
    base.update(_ler_json("Mundo.json"))
    return base
