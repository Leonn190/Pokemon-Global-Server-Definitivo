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
        "Dinheiro": 20,
        "Maestria": 0,
        "SkinInicialMin": 1,
        "SkinInicialMax": 12,
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
        "RaioTapa": 0.36,
        "MultiplicadorFerramentaTapa": 1.5,
    }
    base.update(_ler_json("Player.json"))
    return base


def carregar_regras_cerebro() -> Dict[str, object]:
    base = {
        "tick_segundos": 0.0333,
        "chance_spawn_pokemon_por_tick": 0.02,
        "limite_spawn_pokemon_200_ticks": 4,
        "chance_spawn_bau_por_tick": 0.010,
        "limite_spawn_bau_200_ticks": 2,
        "limite_pokemons_chunk": 2,
        "limite_baus_chunk": 1,
        "limite_total_baus": 60,
        "limite_total_pokemons": 100,
        "limite_total_baus_por_chunk_existente": -1.0,
        "limite_total_pokemons_por_chunk_existente": -1.0,
        "tentativas_spawn_bau": 5,
        "tentativas_spawn_pokemon": 5,
        "chance_movimento_pokemon_por_tick": 0.008,
        "intervalo_minimo_apos_movimento_ticks": 40,
        "tempo_maximo_movimento_ticks": 150,
        "velocidade_base_pokemon_tiles_s": 3.0,
        "chance_despawn_bau_simulado_por_tick": 0.002,
        "chance_despawn_pokemon_simulado_por_tick": 0.003,
        "cooldown_movimento_apos_tentativa_captura_ticks": 36,
        "atraso_inventario_captura_ticks": 24,
        "atraso_spawn_xp_captura_ticks": 16,
        "xp_captura_particulas_min": 3,
        "xp_captura_particulas_max": 4,
        "raio_chunks_simulados": 3,
        "raio_chunks_carregados": 4,
        "chuva_chance_inicio_por_tick": 0.000025,
        "chuva_tempo_seco_min_ticks": 14400,
        "chuva_tempo_seco_max_ticks": 63000,
        "chuva_duracao_min_ticks": 7200,
        "chuva_duracao_max_ticks": 50400,
        "chuva_variacao_min_ticks": 450,
        "chuva_variacao_max_ticks": 2700,
        "chuva_intensidade_faixa1_min": 18,
        "chuva_intensidade_faixa1_max": 45,
        "chuva_intensidade_faixa2_min": 46,
        "chuva_intensidade_faixa2_max": 72,
        "chuva_intensidade_faixa3_min": 73,
        "chuva_intensidade_faixa3_max": 100,
        "chuva_faixa1_peso": 0.60,
        "chuva_faixa2_peso": 0.30,
        "chuva_faixa3_peso": 0.10,
        "chuva_passo_suave": 1,
        "chuva_passo_forte": 2,
        "chuva_delta_passo_suave_limite": 12,
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
