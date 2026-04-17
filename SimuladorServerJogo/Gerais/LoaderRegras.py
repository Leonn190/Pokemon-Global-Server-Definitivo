from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tomllib

_BASE_REGRAS = Path(__file__).resolve().parents[1] / "Logica" / "Regras"


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
    base.update(_ler_toml("Player.toml"))
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

    out["velocidade_base_pokemon_tiles_s"] = float(vel.get("base_tiles_s", 3.0) or 3.0)
    out["tamanho_diametro_base_tiles"] = float(tamanho.get("diametro_base_tiles", 0.6) or 0.6)
    out["tamanho_incremento_por_escala"] = float(tamanho.get("incremento_por_escala", tamanho.get("incremento_por_tamanho", 0.1)) or 0.1)
    out["tamanho_variacao_escala_min"] = int(tamanho.get("variacao_escala_min", -1) or -1)
    out["tamanho_variacao_escala_max"] = int(tamanho.get("variacao_escala_max", 1) or 1)
    # Compat legado (cliente antigo ainda pode ler esta chave).
    out["tamanho_incremento_por_tamanho"] = float(out["tamanho_incremento_por_escala"])
    out["combate_tamanho_diametro_base_tiles"] = float(batalha_tamanho.get("diametro_base_tiles", 1.0) or 1.0)
    out["combate_tamanho_incremento_por_escala"] = float(batalha_tamanho.get("incremento_por_escala", 0.1) or 0.1)
    out["animacao_intervalo_frame_ms"] = int(anim.get("intervalo_frame_ms", 85) or 85)
    out["captura_limite_frutas"] = int(captura.get("limite_frutas", 2) or 2)
    out["captura_cooldown_movimento_ticks"] = int(captura.get("cooldown_movimento_ticks", 36) or 36)
    out["captura_atraso_inventario_ticks"] = int(captura.get("atraso_inventario_ticks", 24) or 24)
    out["captura_atraso_spawn_xp_ticks"] = int(captura.get("atraso_spawn_xp_ticks", 16) or 16)
    out["captura_xp_particulas_min"] = int(captura.get("xp_particulas_min", 3) or 3)
    out["captura_xp_particulas_max"] = int(captura.get("xp_particulas_max", 4) or 4)
    out["captura_bonus_maestria"] = float(captura.get("bonus_maestria_por_ponto", 10.0) or 10.0)
    out["captura_chance_min"] = float(captura.get("chance_escape_min", 2.0) or 2.0)
    out["captura_chance_max"] = float(captura.get("chance_escape_max", 95.0) or 95.0)
    return out


def carregar_regras_spawn() -> Dict[str, object]:
    dados = _ler_toml("Spawn.toml")
    out = _flatten(dados)
    pok = dados.get("pokemons") if isinstance(dados.get("pokemons"), dict) else {}
    bau = dados.get("baus") if isinstance(dados.get("baus"), dict) else {}
    item_mundo = dados.get("item_mundo") if isinstance(dados.get("item_mundo"), dict) else {}
    xp_mundo = dados.get("xp_mundo") if isinstance(dados.get("xp_mundo"), dict) else {}

    out["chance_spawn_pokemon_por_tick"] = float(pok.get("chance_por_tick", 0.02) or 0.02)
    out["limite_spawn_pokemon_200_ticks"] = int(pok.get("limite_200_ticks", 4) or 4)
    out["tentativas_spawn_pokemon"] = int(pok.get("tentativas", 5) or 5)
    out["limite_pokemons_chunk"] = int(pok.get("limite_chunk", 2) or 2)
    out["limite_total_pokemons"] = int(pok.get("limite_total", 100) or 100)
    out["limite_total_pokemons_por_chunk_existente"] = float(pok.get("limite_total_por_chunk_existente", -1.0) or -1.0)
    out["chance_despawn_pokemon_simulado_por_tick"] = float(pok.get("chance_despawn_simulado_por_tick", 0.003) or 0.003)

    out["chance_spawn_bau_por_tick"] = float(bau.get("chance_por_tick", 0.010) or 0.010)
    out["limite_spawn_bau_200_ticks"] = int(bau.get("limite_200_ticks", 2) or 2)
    out["tentativas_spawn_bau"] = int(bau.get("tentativas", 5) or 5)
    out["limite_baus_chunk"] = int(bau.get("limite_chunk", 1) or 1)
    out["limite_total_baus"] = int(bau.get("limite_total", 60) or 60)
    out["limite_total_baus_por_chunk_existente"] = float(bau.get("limite_total_por_chunk_existente", -1.0) or -1.0)
    out["chance_despawn_bau_simulado_por_tick"] = float(bau.get("chance_despawn_simulado_por_tick", 0.002) or 0.002)

    out["item_mundo_ttl_ticks"] = int(item_mundo.get("ttl_ticks", 5000) or 5000)
    out["xp_mundo_ttl_ticks"] = int(xp_mundo.get("ttl_ticks", 600) or 600)
    return out


def carregar_regras_npcs() -> Dict[str, object]:
    dados = _ler_toml("NPCs.toml")
    out = _flatten(dados)
    interacao = dados.get("interacao") if isinstance(dados.get("interacao"), dict) else {}
    rotas = dados.get("rotas") if isinstance(dados.get("rotas"), dict) else {}
    movimento = dados.get("movimento") if isinstance(dados.get("movimento"), dict) else {}

    out["npc_raio_interacao"] = float(interacao.get("raio_padrao", 1.1) or 1.1)
    out["npc_rota_tamanho_min"] = float(rotas.get("tamanho_min", 200.0) or 200.0)
    out["npc_rota_tamanho_max"] = float(rotas.get("tamanho_max", 1000.0) or 1000.0)
    out["npc_rota_tentativas_replanejamento"] = int(rotas.get("tentativas_replanejamento", 3) or 3)
    out["npc_velocidade_base"] = float(movimento.get("velocidade_base_tiles_s", 4.5) or 4.5)
    return out


def carregar_regras_projeteis() -> Dict[str, object]:
    dados = _ler_toml("Projeteis.toml")
    out = _flatten(dados)
    vel = dados.get("velocidade") if isinstance(dados.get("velocidade"), dict) else {}
    alcance = dados.get("alcance") if isinstance(dados.get("alcance"), dict) else {}
    mira = dados.get("mira") if isinstance(dados.get("mira"), dict) else {}

    out["projetil_velocidade_pokebola_tiles_s"] = float(vel.get("pokebola_tiles_s", 7.0) or 7.0)
    out["projetil_velocidade_fastball_tiles_s"] = float(vel.get("fastball_tiles_s", 10.0) or 10.0)
    out["projetil_velocidade_sniperball_tiles_s"] = float(vel.get("sniperball_tiles_s", 8.0) or 8.0)
    out["projetil_velocidade_fruta_tiles_s"] = float(vel.get("fruta_tiles_s", 6.0) or 6.0)
    out["projetil_velocidade_item_mundo_tiles_s"] = float(vel.get("item_mundo_tiles_s", 3.0) or 3.0)

    out["projetil_alcance_pokebola_tiles"] = float(alcance.get("pokebola_tiles", 7.0) or 7.0)
    out["projetil_alcance_fastball_tiles"] = float(alcance.get("fastball_tiles", 7.0) or 7.0)
    out["projetil_alcance_sniperball_tiles"] = float(alcance.get("sniperball_tiles", 9.0) or 9.0)
    out["projetil_alcance_fruta_tiles"] = float(alcance.get("fruta_tiles", 6.0) or 6.0)

    out["projetil_mira_multiplicador_velocidade"] = float(mira.get("multiplicador_velocidade", 1.10) or 1.10)
    out["projetil_mira_multiplicador_alcance"] = float(mira.get("multiplicador_alcance", 1.15) or 1.15)
    return out


def carregar_regras_ciclo() -> Dict[str, object]:
    dados = _ler_toml("Ciclo.toml")
    out = _flatten(dados)
    chuva = dados.get("chuva") if isinstance(dados.get("chuva"), dict) else {}
    tempo = dados.get("tempo") if isinstance(dados.get("tempo"), dict) else {}
    iluminacao = dados.get("iluminacao") if isinstance(dados.get("iluminacao"), dict) else {}

    def _int_cfg(origem: Dict[str, object], chave: str, padrao: int) -> int:
        valor = origem.get(chave, padrao)
        if valor in (None, ""):
            return int(padrao)
        return int(valor)

    out["tempo_segundos_mundo_por_tick"] = float(tempo.get("segundos_mundo_por_tick", 2.0) or 2.0)
    out["tempo_ticks_por_ciclo"] = int(tempo.get("ticks_por_ciclo", 1) or 1)
    out["iluminacao_inicio_escurecer_hora"] = _int_cfg(iluminacao, "inicio_escurecer_hora", 17)
    out["iluminacao_inicio_escurecer_minuto"] = _int_cfg(iluminacao, "inicio_escurecer_minuto", 0)
    out["iluminacao_escuro_maximo_hora"] = _int_cfg(iluminacao, "escuro_maximo_hora", 1)
    out["iluminacao_escuro_maximo_minuto"] = _int_cfg(iluminacao, "escuro_maximo_minuto", 0)
    out["iluminacao_inicio_clarear_hora"] = _int_cfg(iluminacao, "inicio_clarear_hora", 1)
    out["iluminacao_inicio_clarear_minuto"] = _int_cfg(iluminacao, "inicio_clarear_minuto", 0)
    out["iluminacao_fim_clarear_hora"] = _int_cfg(iluminacao, "fim_clarear_hora", 8)
    out["iluminacao_fim_clarear_minuto"] = _int_cfg(iluminacao, "fim_clarear_minuto", 0)

    out["chuva_chance_inicio_por_tick"] = float(chuva.get("chance_inicio_por_tick", 0.000025) or 0.000025)
    out["chuva_tempo_seco_min_ticks"] = int(chuva.get("tempo_seco_min_ticks", 14400) or 14400)
    out["chuva_tempo_seco_max_ticks"] = int(chuva.get("tempo_seco_max_ticks", 63000) or 63000)
    out["chuva_duracao_min_ticks"] = int(chuva.get("duracao_min_ticks", 7200) or 7200)
    out["chuva_duracao_max_ticks"] = int(chuva.get("duracao_max_ticks", 50400) or 50400)
    out["chuva_variacao_min_ticks"] = int(chuva.get("variacao_min_ticks", 450) or 450)
    out["chuva_variacao_max_ticks"] = int(chuva.get("variacao_max_ticks", 2700) or 2700)
    out["chuva_intensidade_faixa1_min"] = int(chuva.get("intensidade_faixa1_min", 18) or 18)
    out["chuva_intensidade_faixa1_max"] = int(chuva.get("intensidade_faixa1_max", 45) or 45)
    out["chuva_intensidade_faixa2_min"] = int(chuva.get("intensidade_faixa2_min", 46) or 46)
    out["chuva_intensidade_faixa2_max"] = int(chuva.get("intensidade_faixa2_max", 72) or 72)
    out["chuva_intensidade_faixa3_min"] = int(chuva.get("intensidade_faixa3_min", 73) or 73)
    out["chuva_intensidade_faixa3_max"] = int(chuva.get("intensidade_faixa3_max", 100) or 100)
    out["chuva_faixa1_peso"] = float(chuva.get("faixa1_peso", 0.60) or 0.60)
    out["chuva_faixa2_peso"] = float(chuva.get("faixa2_peso", 0.30) or 0.30)
    out["chuva_faixa3_peso"] = float(chuva.get("faixa3_peso", 0.10) or 0.10)
    out["chuva_passo_suave"] = int(chuva.get("passo_suave", 1) or 1)
    out["chuva_passo_forte"] = int(chuva.get("passo_forte", 2) or 2)
    out["chuva_delta_passo_suave_limite"] = int(chuva.get("delta_passo_suave_limite", 12) or 12)
    return out


def carregar_regras_server() -> Dict[str, object]:
    dados = _ler_toml("Server.toml")
    out = _flatten(dados)
    ticks = dados.get("ticks") if isinstance(dados.get("ticks"), dict) else {}
    chunks = dados.get("chunks") if isinstance(dados.get("chunks"), dict) else {}
    out["tick_segundos"] = float(ticks.get("segundos", 0.0333) or 0.0333)
    out["raio_chunks_simulados"] = int(chunks.get("raio_simulados", 3) or 3)
    out["raio_chunks_carregados"] = int(chunks.get("raio_carregados", 4) or 4)
    return out


def carregar_regras_batalha() -> Dict[str, object]:
    dados = _ler_toml("Batalha.toml")
    out = _flatten(dados)
    timeline = dados.get("timeline") if isinstance(dados.get("timeline"), dict) else {}
    colisao = dados.get("colisao_movimento") if isinstance(dados.get("colisao_movimento"), dict) else {}
    multiplas_acoes = dados.get("multiplas_acoes") if isinstance(dados.get("multiplas_acoes"), dict) else {}

    out["batalha_tick_segundos"] = float(timeline.get("tick_segundos", 0.2) or 0.2)

    out["batalha_colisao_restituicao"] = float(colisao.get("restituicao", 0.35) or 0.35)
    out["batalha_colisao_deslocamento_base_min"] = float(colisao.get("deslocamento_base_min", 0.25) or 0.25)
    out["batalha_colisao_deslocamento_por_velocidade_relativa"] = float(colisao.get("deslocamento_por_velocidade_relativa", 6.0) or 6.0)
    out["batalha_colisao_velocidade_reacao_min"] = float(colisao.get("velocidade_reacao_min", 0.03) or 0.03)
    out["batalha_colisao_dano_base_min"] = float(colisao.get("dano_base_min", 1.0) or 1.0)
    out["batalha_colisao_velocidade_referencia_min"] = float(colisao.get("velocidade_referencia_min", 0.1) or 0.1)
    out["batalha_colisao_dano_por_massa_velocidade"] = float(colisao.get("dano_por_massa_velocidade", 8.0) or 8.0)
    out["batalha_colisao_dano_por_ataque"] = float(colisao.get("dano_por_ataque", 0.35) or 0.35)

    out["batalha_multiplas_acoes_multiplicador_base"] = float(multiplas_acoes.get("multiplicador_base", 1.0) or 1.0)
    out["batalha_multiplas_acoes_acrescimo_por_acao_extra"] = float(multiplas_acoes.get("acrescimo_multiplicador_por_acao_extra", 0.2) or 0.2)
    return out


def carregar_regras_batalha_publicas() -> Dict[str, object]:
    regras_batalha = carregar_regras_batalha()
    return {
        "tick_segundos": float(regras_batalha.get("batalha_tick_segundos", 0.2) or 0.2),
        "colisao": {
            "restituicao": float(regras_batalha.get("batalha_colisao_restituicao", 0.35) or 0.35),
            "deslocamento_base_min": float(regras_batalha.get("batalha_colisao_deslocamento_base_min", 0.25) or 0.25),
            "deslocamento_por_velocidade_relativa": float(regras_batalha.get("batalha_colisao_deslocamento_por_velocidade_relativa", 6.0) or 6.0),
            "velocidade_reacao_min": float(regras_batalha.get("batalha_colisao_velocidade_reacao_min", 0.03) or 0.03),
            "dano_base_min": float(regras_batalha.get("batalha_colisao_dano_base_min", 1.0) or 1.0),
            "velocidade_referencia_min": float(regras_batalha.get("batalha_colisao_velocidade_referencia_min", 0.1) or 0.1),
            "dano_por_massa_velocidade": float(regras_batalha.get("batalha_colisao_dano_por_massa_velocidade", 8.0) or 8.0),
            "dano_por_ataque": float(regras_batalha.get("batalha_colisao_dano_por_ataque", 0.35) or 0.35),
        },
        "multiplas_acoes": {
            "multiplicador_base": float(regras_batalha.get("batalha_multiplas_acoes_multiplicador_base", 1.0) or 1.0),
            "acrescimo_multiplicador_por_acao_extra": float(regras_batalha.get("batalha_multiplas_acoes_acrescimo_por_acao_extra", 0.2) or 0.2),
        },
    }


def carregar_regras_gerais() -> Dict[str, object]:
    dados = _ler_toml("Gerais.toml")
    out = _flatten(dados)
    camera = dados.get("camera") if isinstance(dados.get("camera"), dict) else {}
    combate = dados.get("combate") if isinstance(dados.get("combate"), dict) else {}
    out["camera_px_por_tile"] = int(camera.get("px_por_tile", 50) or 50)
    out["combate_camera_px_por_tile"] = int(combate.get("camera_px_por_tile", 40) or 40)
    out["combate_camera_zoom_min"] = int(combate.get("camera_zoom_min", 30) or 30)
    out["combate_camera_zoom_max"] = int(combate.get("camera_zoom_max", 50) or 50)
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
    ):
        regras.update(bloco)
    return regras


def carregar_regras_cliente_mundo() -> Dict[str, object]:
    regras_pokemons = carregar_regras_pokemons()
    regras_projeteis = carregar_regras_projeteis()
    regras_npcs = carregar_regras_npcs()
    regras_ciclo = carregar_regras_ciclo()
    regras_gerais = carregar_regras_gerais()
    regras_batalha = carregar_regras_batalha_publicas()
    return {
        "mundo": {"chunk_tiles": int(carregar_regras_mundo().get("ChunkTiles", 10) or 10)},
        "pokemons": {
            "animacao_intervalo_frame_ms": int(regras_pokemons.get("animacao_intervalo_frame_ms", 85) or 85),
            "tamanho_diametro_base_tiles": float(regras_pokemons.get("tamanho_diametro_base_tiles", 0.6) or 0.6),
            "tamanho_incremento_por_escala": float(regras_pokemons.get("tamanho_incremento_por_escala", 0.1) or 0.1),
            "tamanho_incremento_por_tamanho": float(regras_pokemons.get("tamanho_incremento_por_tamanho", 0.1) or 0.1),
            "combate_tamanho_diametro_base_tiles": float(regras_pokemons.get("combate_tamanho_diametro_base_tiles", 1.0) or 1.0),
            "combate_tamanho_incremento_por_escala": float(regras_pokemons.get("combate_tamanho_incremento_por_escala", 0.1) or 0.1),
        },
        "projeteis": {
            "velocidade_pokebola_tiles_s": float(regras_projeteis.get("projetil_velocidade_pokebola_tiles_s", 7.0) or 7.0),
            "velocidade_fastball_tiles_s": float(regras_projeteis.get("projetil_velocidade_fastball_tiles_s", 10.0) or 10.0),
            "velocidade_sniperball_tiles_s": float(regras_projeteis.get("projetil_velocidade_sniperball_tiles_s", 8.0) or 8.0),
            "velocidade_fruta_tiles_s": float(regras_projeteis.get("projetil_velocidade_fruta_tiles_s", 6.0) or 6.0),
            "velocidade_item_mundo_tiles_s": float(regras_projeteis.get("projetil_velocidade_item_mundo_tiles_s", 3.0) or 3.0),
            "alcance_pokebola_tiles": float(regras_projeteis.get("projetil_alcance_pokebola_tiles", 7.0) or 7.0),
            "alcance_fastball_tiles": float(regras_projeteis.get("projetil_alcance_fastball_tiles", 7.0) or 7.0),
            "alcance_sniperball_tiles": float(regras_projeteis.get("projetil_alcance_sniperball_tiles", 9.0) or 9.0),
            "alcance_fruta_tiles": float(regras_projeteis.get("projetil_alcance_fruta_tiles", 6.0) or 6.0),
            "mira_multiplicador_velocidade": float(regras_projeteis.get("projetil_mira_multiplicador_velocidade", 1.10) or 1.10),
            "mira_multiplicador_alcance": float(regras_projeteis.get("projetil_mira_multiplicador_alcance", 1.15) or 1.15),
        },
        "npcs": {
            "raio_interacao": float(regras_npcs.get("npc_raio_interacao", 1.1) or 1.1),
            "velocidade_base_tiles_s": float(regras_npcs.get("npc_velocidade_base", 4.5) or 4.5),
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
            "camera_px_por_tile": int(regras_gerais.get("camera_px_por_tile", 50) or 50),
            "combate_camera_px_por_tile": int(regras_gerais.get("combate_camera_px_por_tile", 40) or 40),
            "combate_camera_zoom_min": int(regras_gerais.get("combate_camera_zoom_min", 30) or 30),
            "combate_camera_zoom_max": int(regras_gerais.get("combate_camera_zoom_max", 50) or 50),
        },
        "batalha": dict(regras_batalha),
    }
