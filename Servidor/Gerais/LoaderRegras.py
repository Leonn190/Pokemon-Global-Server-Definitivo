from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tomllib

_RAIZ_PROJETO = Path(__file__).resolve().parents[2]
_BASE_REGRAS = _RAIZ_PROJETO / "Dados" / "Regras"
_AUSENTE = object()


def _ler_toml(nome: str) -> Dict[str, Any]:
    arq = _BASE_REGRAS / nome
    try:
        data = tomllib.loads(arq.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _flatten(dados: Dict[str, Any], prefixo: str = "") -> Dict[str, Any]:
    saida: Dict[str, Any] = {}
    for chave, valor in dados.items():
        chave_norm = f"{prefixo}{chave}" if not prefixo else f"{prefixo}_{chave}"
        if isinstance(valor, dict):
            saida.update(_flatten(valor, prefixo=chave_norm))
        else:
            saida[chave_norm] = valor
    return saida


def _ler_valor(origem: Dict[str, Any], chave: str, padrao: Any) -> Any:
    if not isinstance(origem, dict):
        return padrao
    valor = origem.get(chave, _AUSENTE)
    if valor is _AUSENTE or valor in (None, ""):
        return padrao
    return valor


def _int_cfg(origem: Dict[str, Any], chave: str, padrao: int) -> int:
    return int(_ler_valor(origem, chave, padrao))


def _float_cfg(origem: Dict[str, Any], chave: str, padrao: float) -> float:
    return float(_ler_valor(origem, chave, padrao))


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
        "InvulnerabilidadePadraoTicks": 90,
        "InvulnerabilidadeTicksPorSegundo": 30,
    }
    dados = _ler_toml("Player.toml")
    base.update(dados)
    invulnerabilidade = dados.get("invulnerabilidade") if isinstance(dados.get("invulnerabilidade"), dict) else {}
    base["InvulnerabilidadePadraoTicks"] = _int_cfg(invulnerabilidade, "duracao_padrao_ticks", int(base.get("InvulnerabilidadePadraoTicks", 90) or 90))
    base["InvulnerabilidadeTicksPorSegundo"] = _int_cfg(invulnerabilidade, "ticks_por_segundo", int(base.get("InvulnerabilidadeTicksPorSegundo", 30) or 30))
    return base


def carregar_regras_mundo() -> Dict[str, object]:
    base = {"ChunkTiles": 10}
    base.update(_ler_toml("Mundo.toml"))
    return base


def carregar_regras_estruturas_naturais() -> Dict[str, object]:
    base = {"tipos": {}}
    base.update(_ler_toml("EstruturasNaturais.toml"))
    tipos = base.get("tipos") if isinstance(base.get("tipos"), dict) else {}
    base["tipos"] = tipos
    return base


def carregar_regras_pokemons() -> Dict[str, object]:
    dados = _ler_toml("Pokemons.toml")
    out = _flatten(dados)
    vel = dados.get("velocidade") if isinstance(dados.get("velocidade"), dict) else {}
    tamanho = dados.get("tamanho") if isinstance(dados.get("tamanho"), dict) else {}
    batalha_tamanho = dados.get("batalha_tamanho") if isinstance(dados.get("batalha_tamanho"), dict) else {}
    anim = dados.get("animacao") if isinstance(dados.get("animacao"), dict) else {}
    captura = dados.get("captura") if isinstance(dados.get("captura"), dict) else {}
    captura_dificuldade = captura.get("dificuldade") if isinstance(captura.get("dificuldade"), dict) else {}
    captura_poder = captura.get("poder") if isinstance(captura.get("poder"), dict) else {}
    captura_chance = captura.get("chance") if isinstance(captura.get("chance"), dict) else {}
    captura_falhas = captura.get("falhas") if isinstance(captura.get("falhas"), dict) else {}
    captura_sniperball = captura.get("sniperball") if isinstance(captura.get("sniperball"), dict) else {}
    personalidade = dados.get("personalidade_mundo") if isinstance(dados.get("personalidade_mundo"), dict) else {}
    personalidade_curioso = personalidade.get("curioso") if isinstance(personalidade.get("curioso"), dict) else {}
    personalidade_medroso = personalidade.get("medroso") if isinstance(personalidade.get("medroso"), dict) else {}
    personalidade_irritado = personalidade.get("irritado") if isinstance(personalidade.get("irritado"), dict) else {}
    personalidade_super_bravo = personalidade.get("super_bravo") if isinstance(personalidade.get("super_bravo"), dict) else {}

    out["velocidade_base_pokemon_tiles_s"] = _float_cfg(vel, "base_tiles_s", 3.0)
    out["pokemon_mundo_vel_min_tiles_s"] = _float_cfg(vel, "mundo_min_tiles_s", 1.0)
    out["pokemon_mundo_vel_max_tiles_s"] = _float_cfg(vel, "mundo_max_tiles_s", 4.8)
    out["pokemon_mundo_vel_base_tiles_s"] = _float_cfg(vel, "mundo_base_tiles_s", 1.0)
    out["pokemon_mundo_vel_divisor"] = _float_cfg(vel, "mundo_divisor", 90.0)
    out["tamanho_diametro_base_tiles"] = _float_cfg(tamanho, "diametro_base_tiles", 0.6)
    out["tamanho_incremento_por_escala"] = float(
        _ler_valor(tamanho, "incremento_por_escala", _ler_valor(tamanho, "incremento_por_tamanho", 0.1))
    )
    out["tamanho_variacao_escala_min"] = _int_cfg(tamanho, "variacao_escala_min", -1)
    out["tamanho_variacao_escala_max"] = _int_cfg(tamanho, "variacao_escala_max", 1)
    # Compat legado (cliente antigo ainda pode ler esta chave).
    out["tamanho_incremento_por_tamanho"] = float(out["tamanho_incremento_por_escala"])
    out["combate_tamanho_diametro_base_tiles"] = _float_cfg(batalha_tamanho, "diametro_base_tiles", 1.0)
    out["combate_tamanho_incremento_por_escala"] = _float_cfg(batalha_tamanho, "incremento_por_escala", 0.15)
    out["animacao_intervalo_frame_ms"] = _int_cfg(anim, "intervalo_frame_ms", 85)
    out["captura_limite_frutas"] = _int_cfg(captura, "limite_frutas", 2)
    out["captura_jujuca_bonus_limite_frutas"] = _int_cfg(captura, "jujuca_bonus_limite_frutas", 2)
    out["captura_jujuca_max_por_pokemon"] = _int_cfg(captura, "jujuca_max_por_pokemon", 1)
    out["captura_cooldown_movimento_ticks"] = _int_cfg(captura, "cooldown_movimento_ticks", 36)
    out["captura_atraso_inventario_ticks"] = _int_cfg(captura, "atraso_inventario_ticks", 24)
    out["captura_atraso_spawn_xp_ticks"] = _int_cfg(captura, "atraso_spawn_xp_ticks", 16)
    out["captura_xp_particulas_min"] = _int_cfg(captura, "xp_particulas_min", 3)
    out["captura_xp_particulas_max"] = _int_cfg(captura, "xp_particulas_max", 4)
    out["captura_bonus_maestria"] = _float_cfg(captura, "bonus_maestria_por_ponto", 10.0)
    out["captura_chance_min"] = _float_cfg(captura, "chance_escape_min", 2.0)
    out["captura_chance_max"] = _float_cfg(captura, "chance_escape_max", 95.0)
    out["captura_dificuldade_min"] = _float_cfg(captura_dificuldade, "min", 10.0)
    out["captura_dificuldade_max"] = _float_cfg(captura_dificuldade, "max", 120.0)
    out["captura_dificuldade_peso_total"] = _float_cfg(captura_dificuldade, "peso_total", 0.70)
    out["captura_dificuldade_peso_nivel"] = _float_cfg(captura_dificuldade, "peso_nivel", 0.20)
    out["captura_dificuldade_peso_iv"] = _float_cfg(captura_dificuldade, "peso_iv", 0.10)
    out["captura_dificuldade_expoente_total"] = _float_cfg(captura_dificuldade, "expoente_total", 1.18)
    out["captura_dificuldade_expoente_nivel"] = _float_cfg(captura_dificuldade, "expoente_nivel", 0.85)
    out["captura_dificuldade_expoente_iv"] = _float_cfg(captura_dificuldade, "expoente_iv", 0.90)
    out["captura_poder_poder_base_captura"] = _float_cfg(captura_poder, "poder_base_captura", 5.0)
    out["captura_poder_maestria_max"] = _float_cfg(captura_poder, "maestria_max", 10.0)
    out["captura_poder_bonus_maestria_max"] = _float_cfg(captura_poder, "bonus_maestria_max", 30.0)
    out["captura_poder_expoente_maestria"] = _float_cfg(captura_poder, "expoente_maestria", 0.70)
    out["captura_poder_multiplicador_critico"] = _float_cfg(captura_poder, "multiplicador_critico", 1.35)
    out["captura_chance_base_check"] = _float_cfg(captura_chance, "base_check", 58.0)
    out["captura_chance_escala_diferenca"] = _float_cfg(captura_chance, "escala_diferenca", 0.82)
    out["captura_chance_check_min"] = _float_cfg(captura_chance, "check_min", 3.0)
    out["captura_chance_check_max"] = _float_cfg(captura_chance, "check_max", 98.0)
    out["captura_chance_checks_necessarios"] = _int_cfg(captura_chance, "checks_necessarios", 3)
    mult_checks = _ler_valor(captura_chance, "multiplicadores_checks", [2.5, 1.5, 1.0])
    out["captura_chance_multiplicadores_checks"] = list(mult_checks) if isinstance(mult_checks, (list, tuple)) else [2.5, 1.5, 1.0]
    out["captura_sniperball_distancia_max_tiles"] = _float_cfg(captura_sniperball, "distancia_max_tiles", 9.0)
    out["captura_sniperball_poder_max"] = _float_cfg(captura_sniperball, "poder_max", 100.0)
    out["captura_falhas_incremento_dificuldade_por_falha"] = _float_cfg(captura_falhas, "incremento_dificuldade_por_falha", 3.0)
    out["captura_falhas_falhas_para_irritar"] = _int_cfg(captura_falhas, "falhas_para_irritar", 5)
    out["captura_falhas_limiar_dificuldade_irritado"] = _float_cfg(captura_falhas, "limiar_dificuldade_irritado", 85.0)
    out["captura_falhas_dificuldade_irritado_fixa"] = _float_cfg(captura_falhas, "dificuldade_irritado_fixa", 130.0)
    out["personalidade_mundo_peso_normal"] = _float_cfg(personalidade, "peso_normal", 0.25)
    out["personalidade_mundo_peso_curioso"] = _float_cfg(personalidade, "peso_curioso", 0.35)
    out["personalidade_mundo_peso_medroso"] = _float_cfg(personalidade, "peso_medroso", 0.35)
    out["personalidade_mundo_peso_bravo"] = _float_cfg(personalidade, "peso_bravo", 0.20)
    out["personalidade_mundo_peso_super_bravo"] = _float_cfg(personalidade, "peso_super_bravo", 0.10)
    out["personalidade_mundo_curioso_raio_percepcao_tiles"] = _float_cfg(personalidade_curioso, "raio_percepcao_tiles", 5.0)
    out["personalidade_mundo_curioso_distancia_segura_tiles"] = _float_cfg(personalidade_curioso, "distancia_segura_tiles", 2.4)
    out["personalidade_mundo_curioso_multiplicador_velocidade"] = _float_cfg(personalidade_curioso, "multiplicador_velocidade", 0.95)
    out["personalidade_mundo_medroso_raio_percepcao_tiles"] = _float_cfg(personalidade_medroso, "raio_percepcao_tiles", 5.5)
    out["personalidade_mundo_medroso_multiplicador_velocidade"] = _float_cfg(personalidade_medroso, "multiplicador_velocidade", 1.05)
    out["personalidade_mundo_irritado_raio_busca_tiles"] = _float_cfg(personalidade_irritado, "raio_busca_tiles", 6.0)
    out["personalidade_mundo_irritado_multiplicador_velocidade"] = _float_cfg(personalidade_irritado, "multiplicador_velocidade", 1.20)
    out["personalidade_mundo_irritado_cooldown_movimento_mult"] = _float_cfg(personalidade_irritado, "cooldown_movimento_mult", 0.70)
    out["personalidade_mundo_irritado_chance_movimento_mult"] = _float_cfg(personalidade_irritado, "chance_movimento_mult", 2.0)
    out["personalidade_mundo_super_bravo_raio_ativacao_tiles"] = _float_cfg(personalidade_super_bravo, "raio_ativacao_tiles", 7.0)
    out["personalidade_mundo_super_bravo_raio_busca_irritado_tiles"] = _float_cfg(personalidade_super_bravo, "raio_busca_irritado_tiles", 9.0)
    out["personalidade_mundo_super_bravo_multiplicador_velocidade_irritado"] = _float_cfg(personalidade_super_bravo, "multiplicador_velocidade_irritado", 1.35)
    return out


def carregar_regras_spawn() -> Dict[str, object]:
    dados = _ler_toml("Spawn.toml")
    out = _flatten(dados)
    pok = dados.get("pokemons") if isinstance(dados.get("pokemons"), dict) else {}
    bau = dados.get("baus") if isinstance(dados.get("baus"), dict) else {}
    item_mundo = dados.get("item_mundo") if isinstance(dados.get("item_mundo"), dict) else {}
    xp_mundo = dados.get("xp_mundo") if isinstance(dados.get("xp_mundo"), dict) else {}

    out["chance_spawn_pokemon_por_tick"] = _float_cfg(pok, "chance_por_tick", 0.02)
    out["limite_spawn_pokemon_200_ticks"] = _int_cfg(pok, "limite_200_ticks", 4)
    out["tentativas_spawn_pokemon"] = _int_cfg(pok, "tentativas", 5)
    out["limite_pokemons_chunk"] = _int_cfg(pok, "limite_chunk", 2)
    out["limite_pokemons_chunk_3x3"] = _int_cfg(pok, "limite_chunk_3x3", 7)
    out["limite_total_pokemons"] = _int_cfg(pok, "limite_total", 100)
    out["limite_total_pokemons_por_chunk_existente"] = _float_cfg(pok, "limite_total_por_chunk_existente", -1.0)
    out["chance_despawn_pokemon_simulado_por_tick"] = _float_cfg(pok, "chance_despawn_simulado_por_tick", 0.003)
    progressao = dados.get("progressao_raridade") if isinstance(dados.get("progressao_raridade"), dict) else {}
    out["progressao_raridade"] = {str(k): _int_cfg(progressao, str(k), 0) for k in range(1, 11)}
    multiplicadores = dados.get("multiplicadores_spawn") if isinstance(dados.get("multiplicadores_spawn"), dict) else {}
    out["multiplicadores_spawn"] = dict(multiplicadores)

    out["chance_spawn_bau_por_tick"] = _float_cfg(bau, "chance_por_tick", 0.010)
    out["limite_spawn_bau_200_ticks"] = _int_cfg(bau, "limite_200_ticks", 2)
    out["tentativas_spawn_bau"] = _int_cfg(bau, "tentativas", 5)
    out["limite_baus_chunk"] = _int_cfg(bau, "limite_chunk", 1)
    out["limite_total_baus"] = _int_cfg(bau, "limite_total", 60)
    out["limite_total_baus_por_chunk_existente"] = _float_cfg(bau, "limite_total_por_chunk_existente", -1.0)
    out["chance_despawn_bau_simulado_por_tick"] = _float_cfg(bau, "chance_despawn_simulado_por_tick", 0.002)

    out["item_mundo_ttl_ticks"] = _int_cfg(item_mundo, "ttl_ticks", 5000)
    out["xp_mundo_ttl_ticks"] = _int_cfg(xp_mundo, "ttl_ticks", 600)
    return out


def carregar_regras_npcs() -> Dict[str, object]:
    dados = _ler_toml("NPCs.toml")
    out = _flatten(dados)
    interacao = dados.get("interacao") if isinstance(dados.get("interacao"), dict) else {}
    rotas = dados.get("rotas") if isinstance(dados.get("rotas"), dict) else {}
    movimento = dados.get("movimento") if isinstance(dados.get("movimento"), dict) else {}

    out["npc_raio_interacao"] = _float_cfg(interacao, "raio_padrao", 1.1)
    out["npc_rota_tamanho_min"] = _float_cfg(rotas, "tamanho_min", 200.0)
    out["npc_rota_tamanho_max"] = _float_cfg(rotas, "tamanho_max", 1000.0)
    out["npc_rota_tentativas_replanejamento"] = _int_cfg(rotas, "tentativas_replanejamento", 3)
    out["npc_rota_chance_variacao_por_tick"] = _float_cfg(rotas, "chance_variacao_por_tick", 0.04)
    out["npc_velocidade_base"] = _float_cfg(movimento, "velocidade_base_tiles_s", 4.5)
    return out


def carregar_regras_projeteis() -> Dict[str, object]:
    dados = _ler_toml("Projeteis.toml")
    out = _flatten(dados)
    vel = dados.get("velocidade") if isinstance(dados.get("velocidade"), dict) else {}
    alcance = dados.get("alcance") if isinstance(dados.get("alcance"), dict) else {}
    mira = dados.get("mira") if isinstance(dados.get("mira"), dict) else {}

    out["projetil_velocidade_pokebola_tiles_s"] = _float_cfg(vel, "pokebola_tiles_s", 7.0)
    out["projetil_velocidade_fastball_tiles_s"] = _float_cfg(vel, "fastball_tiles_s", 10.0)
    out["projetil_velocidade_sniperball_tiles_s"] = _float_cfg(vel, "sniperball_tiles_s", 8.0)
    out["projetil_velocidade_fruta_tiles_s"] = _float_cfg(vel, "fruta_tiles_s", 6.0)
    out["projetil_velocidade_item_mundo_tiles_s"] = _float_cfg(vel, "item_mundo_tiles_s", 3.0)

    out["projetil_alcance_pokebola_tiles"] = _float_cfg(alcance, "pokebola_tiles", 7.0)
    out["projetil_alcance_fastball_tiles"] = _float_cfg(alcance, "fastball_tiles", 7.0)
    out["projetil_alcance_sniperball_tiles"] = _float_cfg(alcance, "sniperball_tiles", 9.0)
    out["projetil_alcance_fruta_tiles"] = _float_cfg(alcance, "fruta_tiles", 6.0)

    out["projetil_mira_multiplicador_velocidade"] = _float_cfg(mira, "multiplicador_velocidade", 1.10)
    out["projetil_mira_multiplicador_alcance"] = _float_cfg(mira, "multiplicador_alcance", 1.15)
    return out


def carregar_regras_skils() -> Dict[str, object]:
    dados = _ler_toml("Skils.toml")
    meta = dados.get("meta") if isinstance(dados.get("meta"), dict) else {}
    base = dados.get("base") if isinstance(dados.get("base"), dict) else {}
    skills = dados.get("skills") if isinstance(dados.get("skills"), dict) else {}
    return {
        "meta": dict(meta),
        "base": dict(base),
        "skills": {str(k): dict(v) for k, v in skills.items() if isinstance(v, dict)},
    }


def carregar_regras_ciclo() -> Dict[str, object]:
    dados = _ler_toml("Ciclo.toml")
    out = _flatten(dados)
    chuva = dados.get("chuva") if isinstance(dados.get("chuva"), dict) else {}
    tempo = dados.get("tempo") if isinstance(dados.get("tempo"), dict) else {}
    iluminacao = dados.get("iluminacao") if isinstance(dados.get("iluminacao"), dict) else {}

    out["tempo_segundos_mundo_por_tick"] = _float_cfg(tempo, "segundos_mundo_por_tick", 2.0)
    out["tempo_ticks_por_ciclo"] = _int_cfg(tempo, "ticks_por_ciclo", 1)
    out["iluminacao_inicio_escurecer_hora"] = _int_cfg(iluminacao, "inicio_escurecer_hora", 17)
    out["iluminacao_inicio_escurecer_minuto"] = _int_cfg(iluminacao, "inicio_escurecer_minuto", 0)
    out["iluminacao_escuro_maximo_hora"] = _int_cfg(iluminacao, "escuro_maximo_hora", 1)
    out["iluminacao_escuro_maximo_minuto"] = _int_cfg(iluminacao, "escuro_maximo_minuto", 0)
    out["iluminacao_inicio_clarear_hora"] = _int_cfg(iluminacao, "inicio_clarear_hora", 1)
    out["iluminacao_inicio_clarear_minuto"] = _int_cfg(iluminacao, "inicio_clarear_minuto", 0)
    out["iluminacao_fim_clarear_hora"] = _int_cfg(iluminacao, "fim_clarear_hora", 8)
    out["iluminacao_fim_clarear_minuto"] = _int_cfg(iluminacao, "fim_clarear_minuto", 0)

    out["chuva_chance_inicio_por_tick"] = _float_cfg(chuva, "chance_inicio_por_tick", 0.000025)
    out["chuva_tempo_seco_min_ticks"] = _int_cfg(chuva, "tempo_seco_min_ticks", 14400)
    out["chuva_tempo_seco_max_ticks"] = _int_cfg(chuva, "tempo_seco_max_ticks", 63000)
    out["chuva_duracao_min_ticks"] = _int_cfg(chuva, "duracao_min_ticks", 7200)
    out["chuva_duracao_max_ticks"] = _int_cfg(chuva, "duracao_max_ticks", 50400)
    out["chuva_variacao_min_ticks"] = _int_cfg(chuva, "variacao_min_ticks", 450)
    out["chuva_variacao_max_ticks"] = _int_cfg(chuva, "variacao_max_ticks", 2700)
    out["chuva_intensidade_faixa1_min"] = _int_cfg(chuva, "intensidade_faixa1_min", 18)
    out["chuva_intensidade_faixa1_max"] = _int_cfg(chuva, "intensidade_faixa1_max", 45)
    out["chuva_intensidade_faixa2_min"] = _int_cfg(chuva, "intensidade_faixa2_min", 46)
    out["chuva_intensidade_faixa2_max"] = _int_cfg(chuva, "intensidade_faixa2_max", 72)
    out["chuva_intensidade_faixa3_min"] = _int_cfg(chuva, "intensidade_faixa3_min", 73)
    out["chuva_intensidade_faixa3_max"] = _int_cfg(chuva, "intensidade_faixa3_max", 100)
    out["chuva_faixa1_peso"] = _float_cfg(chuva, "faixa1_peso", 0.60)
    out["chuva_faixa2_peso"] = _float_cfg(chuva, "faixa2_peso", 0.30)
    out["chuva_faixa3_peso"] = _float_cfg(chuva, "faixa3_peso", 0.10)
    out["chuva_passo_suave"] = _int_cfg(chuva, "passo_suave", 1)
    out["chuva_passo_forte"] = _int_cfg(chuva, "passo_forte", 2)
    out["chuva_delta_passo_suave_limite"] = _int_cfg(chuva, "delta_passo_suave_limite", 12)
    return out


def carregar_regras_server() -> Dict[str, object]:
    dados = _ler_toml("Server.toml")
    out = _flatten(dados)
    ticks = dados.get("ticks") if isinstance(dados.get("ticks"), dict) else {}
    chunks = dados.get("chunks") if isinstance(dados.get("chunks"), dict) else {}
    out["tick_segundos"] = _float_cfg(ticks, "segundos", 0.0333)
    out["raio_chunks_simulados"] = _int_cfg(chunks, "raio_simulados", 3)
    out["raio_chunks_carregados"] = _int_cfg(chunks, "raio_carregados", 4)
    return out


def carregar_regras_batalha() -> Dict[str, object]:
    dados = _ler_toml("Batalha.toml")
    out = _flatten(dados)
    timeline = dados.get("timeline") if isinstance(dados.get("timeline"), dict) else {}
    colisao = dados.get("colisao_movimento") if isinstance(dados.get("colisao_movimento"), dict) else {}
    multiplas_acoes = dados.get("multiplas_acoes") if isinstance(dados.get("multiplas_acoes"), dict) else {}

    out["batalha_tick_segundos"] = _float_cfg(timeline, "tick_segundos", 0.2)

    out["batalha_colisao_restituicao"] = _float_cfg(colisao, "restituicao", 0.35)
    out["batalha_colisao_deslocamento_base_min"] = _float_cfg(colisao, "deslocamento_base_min", 0.25)
    out["batalha_colisao_deslocamento_por_velocidade_relativa"] = _float_cfg(colisao, "deslocamento_por_velocidade_relativa", 6.0)
    out["batalha_colisao_velocidade_reacao_min"] = _float_cfg(colisao, "velocidade_reacao_min", 0.03)
    out["batalha_colisao_dano_base_min"] = _float_cfg(colisao, "dano_base_min", 1.0)
    out["batalha_colisao_velocidade_referencia_min"] = _float_cfg(colisao, "velocidade_referencia_min", 0.1)
    out["batalha_colisao_dano_por_massa_velocidade"] = _float_cfg(colisao, "dano_por_massa_velocidade", 8.0)
    out["batalha_colisao_dano_por_ataque"] = _float_cfg(colisao, "dano_por_ataque", 0.35)

    out["batalha_multiplas_acoes_multiplicador_base"] = _float_cfg(multiplas_acoes, "multiplicador_base", 1.0)
    out["batalha_multiplas_acoes_acrescimo_por_acao_extra"] = _float_cfg(multiplas_acoes, "acrescimo_multiplicador_por_acao_extra", 0.2)
    return out


def carregar_regras_batalha_publicas() -> Dict[str, object]:
    regras_batalha = carregar_regras_batalha()
    regras_pokemons = carregar_regras_pokemons()
    return {
        "tick_segundos": float(_ler_valor(regras_batalha, "batalha_tick_segundos", 0.2)),
        "animacao": {
            "intervalo_frame_ms": int(_ler_valor(regras_pokemons, "animacao_intervalo_frame_ms", 85)),
        },
        "colisao": {
            "restituicao": float(_ler_valor(regras_batalha, "batalha_colisao_restituicao", 0.35)),
            "deslocamento_base_min": float(_ler_valor(regras_batalha, "batalha_colisao_deslocamento_base_min", 0.25)),
            "deslocamento_por_velocidade_relativa": float(_ler_valor(regras_batalha, "batalha_colisao_deslocamento_por_velocidade_relativa", 6.0)),
            "velocidade_reacao_min": float(_ler_valor(regras_batalha, "batalha_colisao_velocidade_reacao_min", 0.03)),
            "dano_base_min": float(_ler_valor(regras_batalha, "batalha_colisao_dano_base_min", 1.0)),
            "velocidade_referencia_min": float(_ler_valor(regras_batalha, "batalha_colisao_velocidade_referencia_min", 0.1)),
            "dano_por_massa_velocidade": float(_ler_valor(regras_batalha, "batalha_colisao_dano_por_massa_velocidade", 8.0)),
            "dano_por_ataque": float(_ler_valor(regras_batalha, "batalha_colisao_dano_por_ataque", 0.35)),
        },
        "multiplas_acoes": {
            "multiplicador_base": float(_ler_valor(regras_batalha, "batalha_multiplas_acoes_multiplicador_base", 1.0)),
            "acrescimo_multiplicador_por_acao_extra": float(_ler_valor(regras_batalha, "batalha_multiplas_acoes_acrescimo_por_acao_extra", 0.2)),
        },
    }


def carregar_regras_gerais() -> Dict[str, object]:
    dados = _ler_toml("Camera.toml")
    if not dados:
        dados = _ler_toml("Gerais.toml")
    out = _flatten(dados)
    camera = dados.get("camera") if isinstance(dados.get("camera"), dict) else {}
    combate = dados.get("combate") if isinstance(dados.get("combate"), dict) else {}
    out["camera_px_por_tile"] = _int_cfg(camera, "px_por_tile", 50)
    out["dungeon_camera_px_por_tile"] = _int_cfg(camera, "dungeon_px_por_tile", 60)
    out["combate_camera_px_por_tile"] = _int_cfg(combate, "camera_px_por_tile", 40)
    out["combate_camera_zoom_min"] = _int_cfg(combate, "camera_zoom_min", 30)
    out["combate_camera_zoom_max"] = _int_cfg(combate, "camera_zoom_max", 50)
    return out


def calcular_parametros_projetil(regras: Dict[str, object], subtipo: str, variante: str, mirando: bool = False) -> tuple[float, float]:
    d = dict(regras or {})

    def _g(*chaves: str, default: float) -> float:
        for chave in chaves:
            if chave in d:
                try:
                    return float(d.get(chave, default))
                except Exception:
                    return float(default)
        return float(default)

    subtipo_norm = str(subtipo or "").strip().lower()
    variante_norm = str(variante or "").strip().lower()
    if subtipo_norm == "fruta":
        velocidade = _g("projetil_velocidade_fruta_tiles_s", "velocidade_fruta_tiles_s", default=6.0)
        alcance = _g("projetil_alcance_fruta_tiles", "alcance_fruta_tiles", default=6.0)
    elif variante_norm == "sniperball":
        velocidade = _g("projetil_velocidade_sniperball_tiles_s", "velocidade_sniperball_tiles_s", default=8.0)
        alcance = _g("projetil_alcance_sniperball_tiles", "alcance_sniperball_tiles", default=9.0)
    elif variante_norm == "fastball":
        velocidade = _g("projetil_velocidade_fastball_tiles_s", "velocidade_fastball_tiles_s", default=10.0)
        alcance = _g("projetil_alcance_fastball_tiles", "alcance_fastball_tiles", default=7.0)
    else:
        velocidade = _g("projetil_velocidade_pokebola_tiles_s", "velocidade_pokebola_tiles_s", default=7.0)
        alcance = _g("projetil_alcance_pokebola_tiles", "alcance_pokebola_tiles", default=7.0)

    if bool(mirando):
        velocidade *= _g("projetil_mira_multiplicador_velocidade", "mira_multiplicador_velocidade", default=1.10)
        alcance *= _g("projetil_mira_multiplicador_alcance", "mira_multiplicador_alcance", default=1.15)
    return (float(velocidade), float(alcance))


def carregar_regras_runtime_servidor() -> Dict[str, object]:
    regras: Dict[str, object] = {}
    for bloco in (
        carregar_regras_server(),
        carregar_regras_batalha(),
        carregar_regras_spawn(),
        carregar_regras_pokemons(),
        carregar_regras_projeteis(),
        carregar_regras_ciclo(),
        carregar_regras_npcs(),
        carregar_regras_gerais(),
        carregar_regras_dungeons(),
    ):
        regras.update(bloco)
    regras["skils"] = carregar_regras_skils()
    return regras


def carregar_regras_cliente_mundo() -> Dict[str, object]:
    regras_pokemons = carregar_regras_pokemons()
    regras_projeteis = carregar_regras_projeteis()
    regras_npcs = carregar_regras_npcs()
    regras_ciclo = carregar_regras_ciclo()
    regras_gerais = carregar_regras_gerais()
    regras_batalha = carregar_regras_batalha_publicas()
    regras_skils = carregar_regras_skils()
    return {
        "mundo": {"chunk_tiles": int(_ler_valor(carregar_regras_mundo(), "ChunkTiles", 10))},
        "animacao": {
            "intervalo_frame_ms": int(_ler_valor(regras_pokemons, "animacao_intervalo_frame_ms", 85)),
        },
        "pokemons": {
            "animacao_intervalo_frame_ms": int(_ler_valor(regras_pokemons, "animacao_intervalo_frame_ms", 85)),
            "tamanho_diametro_base_tiles": float(_ler_valor(regras_pokemons, "tamanho_diametro_base_tiles", 0.6)),
            "tamanho_incremento_por_escala": float(_ler_valor(regras_pokemons, "tamanho_incremento_por_escala", 0.1)),
            "tamanho_incremento_por_tamanho": float(_ler_valor(regras_pokemons, "tamanho_incremento_por_tamanho", 0.1)),
            "combate_tamanho_diametro_base_tiles": float(_ler_valor(regras_pokemons, "combate_tamanho_diametro_base_tiles", 1.0)),
            "combate_tamanho_incremento_por_escala": float(_ler_valor(regras_pokemons, "combate_tamanho_incremento_por_escala", 0.15)),
        },
        "projeteis": {
            "velocidade_pokebola_tiles_s": float(_ler_valor(regras_projeteis, "projetil_velocidade_pokebola_tiles_s", 7.0)),
            "velocidade_fastball_tiles_s": float(_ler_valor(regras_projeteis, "projetil_velocidade_fastball_tiles_s", 10.0)),
            "velocidade_sniperball_tiles_s": float(_ler_valor(regras_projeteis, "projetil_velocidade_sniperball_tiles_s", 8.0)),
            "velocidade_fruta_tiles_s": float(_ler_valor(regras_projeteis, "projetil_velocidade_fruta_tiles_s", 6.0)),
            "velocidade_item_mundo_tiles_s": float(_ler_valor(regras_projeteis, "projetil_velocidade_item_mundo_tiles_s", 3.0)),
            "alcance_pokebola_tiles": float(_ler_valor(regras_projeteis, "projetil_alcance_pokebola_tiles", 7.0)),
            "alcance_fastball_tiles": float(_ler_valor(regras_projeteis, "projetil_alcance_fastball_tiles", 7.0)),
            "alcance_sniperball_tiles": float(_ler_valor(regras_projeteis, "projetil_alcance_sniperball_tiles", 9.0)),
            "alcance_fruta_tiles": float(_ler_valor(regras_projeteis, "projetil_alcance_fruta_tiles", 6.0)),
            "mira_multiplicador_velocidade": float(_ler_valor(regras_projeteis, "projetil_mira_multiplicador_velocidade", 1.10)),
            "mira_multiplicador_alcance": float(_ler_valor(regras_projeteis, "projetil_mira_multiplicador_alcance", 1.15)),
        },
        "npcs": {
            "raio_interacao": float(_ler_valor(regras_npcs, "npc_raio_interacao", 1.1)),
            "velocidade_base_tiles_s": float(_ler_valor(regras_npcs, "npc_velocidade_base", 4.5)),
        },
        "ciclo": {
            "iluminacao": {
                "inicio_escurecer_hora": int(regras_ciclo.get("iluminacao_inicio_escurecer_hora", 17) if regras_ciclo.get("iluminacao_inicio_escurecer_hora", 17) not in (None, "") else 17),
                "inicio_escurecer_minuto": int(regras_ciclo.get("iluminacao_inicio_escurecer_minuto", 0) if regras_ciclo.get("iluminacao_inicio_escurecer_minuto", 0) not in (None, "") else 0),
                "escuro_maximo_hora": int(regras_ciclo.get("iluminacao_escuro_maximo_hora", 1) if regras_ciclo.get("iluminacao_escuro_maximo_hora", 1) not in (None, "") else 1),
                "escuro_maximo_minuto": int(regras_ciclo.get("iluminacao_escuro_maximo_minuto", 0) if regras_ciclo.get("iluminacao_escuro_maximo_minuto", 0) not in (None, "") else 0),
                "inicio_clarear_hora": int(regras_ciclo.get("iluminacao_inicio_clarear_hora", 1) if regras_ciclo.get("iluminacao_inicio_clarear_hora", 1) not in (None, "") else 1),
                "inicio_clarear_minuto": int(regras_ciclo.get("iluminacao_inicio_clarear_minuto", 0) if regras_ciclo.get("iluminacao_inicio_clarear_minuto", 0) not in (None, "") else 0),
                "fim_clarear_hora": int(regras_ciclo.get("iluminacao_fim_clarear_hora", 8) if regras_ciclo.get("iluminacao_fim_clarear_hora", 8) not in (None, "") else 8),
                "fim_clarear_minuto": int(regras_ciclo.get("iluminacao_fim_clarear_minuto", 0) if regras_ciclo.get("iluminacao_fim_clarear_minuto", 0) not in (None, "") else 0),
            }
        },
        "gerais": {
            "camera_px_por_tile": int(_ler_valor(regras_gerais, "camera_px_por_tile", 50)),
            "dungeon_camera_px_por_tile": int(_ler_valor(regras_gerais, "dungeon_camera_px_por_tile", 60)),
            "combate_camera_px_por_tile": int(_ler_valor(regras_gerais, "combate_camera_px_por_tile", 40)),
            "combate_camera_zoom_min": int(_ler_valor(regras_gerais, "combate_camera_zoom_min", 30)),
            "combate_camera_zoom_max": int(_ler_valor(regras_gerais, "combate_camera_zoom_max", 50)),
        },
        "batalha": dict(regras_batalha),
        "skils": regras_skils,
    }


def carregar_regras_dungeons() -> Dict[str, object]:
    base = {
        "tamanho_bloco_sala_tiles": 32,
        "largura_bloco_sala_tiles": 32,
        "altura_bloco_sala_tiles": 18,
        "tile_vazio_dungeon": 9,
        "tile_chao_dungeon": 8,
        "tile_agua_funda": 0,
        "porta_largura_tiles": 4,
        "parede_largura_tiles": 2,
        "margem_blocos_dungeon": 1,
        "coracoes_iniciais": 3,
        "coracoes_maximos": 3,
        "tamanho_1_blocos": 5,
        "tamanho_2_blocos": 6,
        "tamanho_3_blocos": 7,
        "tamanho_4_blocos": 8,
        "tamanho_5_blocos": 9,
        "tamanho_6_blocos": 10,
        "raio_interacao_porta": 1.25,
        "invulnerabilidade_dungeon_ticks": 90,
        "servo_raio_busca_tiles": 10.0,
        "servo_velocidade_tiles_s": 3.6,
        "servo_vel_min_tiles_s": 2.0,
        "servo_vel_max_tiles_s": 7.0,
        "servo_vel_mult_dungeon": 1.0,
        "servo_vel_base_tiles_s": 1.8,
        "servo_vel_divisor": 55.0,
        "servo_cooldown_colisao_ticks": 30,
        "servo_batalha_lock_timeout_ticks": 180,
        "servo_comum_min": 0,
        "servo_comum_max": 2,
        "servo_dificil_min": 2,
        "servo_dificil_max": 4,
        "chance_porta_extra": 0.10,
        "chance_porta_trancada": 0.24,
        "chance_porta_boss_trancada": 0.72,
        "chaves_por_sala_max": 2,
        "dungeon_preenchimento_min": 0.32,
        "dungeon_preenchimento_max": 0.52,
        "dungeon_chance_ramificacao": 0.35,
        "dungeon_tortuosidade": 0.65,
        "dungeon_distancia_min_boss_entrada": 3,
    }
    base.update(_ler_toml("Dungeons.toml"))
    return base
