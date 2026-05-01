from __future__ import annotations

import random
from typing import Dict, List

from SimuladorServerJogo.Logica.Executes.ExecutesFrutas import executar_fruta
from SimuladorServerJogo.Logica.Executes.ExecutesPokebolas import executar_pokebola


def resolver_fruta(pokemon, nome_fruta, contexto=None):
    retorno = executar_fruta(nome_fruta, pokemon, contexto=contexto)
    return {
        "evento": "pokemon_frutificado",
        "payload": {
            "pokemon_id": int(getattr(pokemon, "Id", 0) or 0),
            "aplicou": bool(retorno.get("aplicou", False)),
            "efeitos": dict(retorno.get("efeitos", {})),
            "frutas_aplicadas": list(retorno.get("frutas_aplicadas", [])),
            "estado_frutificacao": dict(retorno.get("estado_frutificacao", {})),
        },
    }


def _normalizar_checks(checks: List[bool]) -> List[bool]:
    base = [bool(x) for x in list(checks or [])[:3]]
    while len(base) < 3:
        base.append(False)
    primeira_falha = next((i for i, ok in enumerate(base) if not bool(ok)), None)
    if primeira_falha is not None:
        for i in range(primeira_falha, 3):
            base[i] = False
    return base[:3]


def resolver_captura(pokemon, nome_bola, contexto=None):
    ctx = dict(contexto or {})
    captura = pokemon.estado_extra.setdefault("captura", {})
    if bool(captura.get("captura_pendente", False)):
        return {"iniciada": False, "motivo": "captura_em_andamento", "eventos": []}

    bola = executar_pokebola(nome_bola, pokemon, contexto=ctx)
    poder_base_captura = float(ctx.get("captura_poder_poder_base_captura", 5.0) if ctx.get("captura_poder_poder_base_captura", 5.0) not in (None, "") else 5.0)
    poder_base = float(bola.get("poder_base", 0.0) or 0.0)

    estado_fruta = pokemon.estado_extra.get("estado_frutificacao") if isinstance(pokemon.estado_extra.get("estado_frutificacao"), dict) else {}
    bonus_frutas = float(estado_fruta.get("bonus_captura_frutas", 0.0) or 0.0)
    bonus_bioma = estado_fruta.get("bonus_captura_bioma") if isinstance(estado_fruta.get("bonus_captura_bioma"), dict) else {}
    bonus_bioma_valor = float(bonus_bioma.get(str(ctx.get("bioma", "")).lower(), 0.0) or 0.0)

    maestria = float(ctx.get("maestria", 0.0) if ctx.get("maestria", 0.0) not in (None, "") else 0.0)
    maestria_max = float(ctx.get("captura_poder_maestria_max", 10.0) if ctx.get("captura_poder_maestria_max", 10.0) not in (None, "") else 10.0)
    bonus_maestria_max = float(ctx.get("captura_poder_bonus_maestria_max", 30.0) if ctx.get("captura_poder_bonus_maestria_max", 30.0) not in (None, "") else 30.0)
    expoente_maestria = float(ctx.get("captura_poder_expoente_maestria", 0.70) if ctx.get("captura_poder_expoente_maestria", 0.70) not in (None, "") else 0.70)
    maestria_p = max(0.0, min(1.0, maestria / max(0.0001, maestria_max)))
    bonus_maestria_total = bonus_maestria_max * (maestria_p ** expoente_maestria)
    poder_linear = poder_base_captura + poder_base + bonus_frutas + bonus_bioma_valor + bonus_maestria_total
    multiplicador_critico = float(ctx.get("captura_poder_multiplicador_critico", 1.35) if ctx.get("captura_poder_multiplicador_critico", 1.35) not in (None, "") else 1.35)
    critica_cliente = bool(ctx.get("captura_critica_cliente", False))
    poder = poder_linear * multiplicador_critico if critica_cliente else poder_linear

    dificuldade = float(pokemon.estado_extra.get("dificuldade_captura", 50.0) or 50.0)
    garantida = bool(bola.get("captura_garantida", False))
    base_check = float(ctx.get("captura_chance_base_check", 58.0) if ctx.get("captura_chance_base_check", 58.0) not in (None, "") else 58.0)
    escala_diferenca = float(ctx.get("captura_chance_escala_diferenca", 0.82) if ctx.get("captura_chance_escala_diferenca", 0.82) not in (None, "") else 0.82)
    check_min = float(ctx.get("captura_chance_check_min", 3.0) if ctx.get("captura_chance_check_min", 3.0) not in (None, "") else 3.0)
    check_max = float(ctx.get("captura_chance_check_max", 98.0) if ctx.get("captura_chance_check_max", 98.0) not in (None, "") else 98.0)
    checks_necessarios = max(1, int(ctx.get("captura_chance_checks_necessarios", 3) if ctx.get("captura_chance_checks_necessarios", 3) not in (None, "") else 3))
    chance_check = 100.0 if garantida else max(check_min, min(check_max, base_check + ((poder - dificuldade) * escala_diferenca)))
    chance_real_checks = 100.0 if garantida else (chance_check / 100.0) ** checks_necessarios * 100.0

    dono_pos = ctx.get("dono_posicao") if isinstance(ctx.get("dono_posicao"), (list, tuple)) and len(ctx.get("dono_posicao")) == 2 else None
    bola_pos = [float(pokemon.posicao[0]), float(pokemon.posicao[1])]
    retorno_destino = [float(dono_pos[0]), float(dono_pos[1])] if dono_pos else list(bola_pos)

    checks: List[bool] = []
    rolagens: List[float] = []
    falhou = False
    for _idx in range(1, checks_necessarios + 1):
        if falhou:
            checks.append(False)
            continue
        passou = bool(garantida)
        if not passou:
            rolagem = random.uniform(0.0, 100.0)
            rolagens.append(float(rolagem))
            passou = rolagem <= chance_check
        checks.append(bool(passou))
        if not passou:
            falhou = True
    checks = _normalizar_checks(checks)

    sucesso = bool(all(checks))
    resultado = "sucesso" if sucesso else "falha"
    tick_atual = int(ctx.get("tick_atual", 0) or 0)
    cooldown_ticks = int(ctx.get("cooldown_movimento_ticks", 36) if ctx.get("cooldown_movimento_ticks", 36) not in (None, "") else 36)
    liberar_tick = int(tick_atual + cooldown_ticks)

    captura.clear()
    captura.update(
        {
            "captura_pendente": True,
            "checks_total": 3,
            "checagens": list(checks),
            "resultado": str(resultado),
            "capturador_id": int(ctx.get("dono_id", 0) or 0),
            "dono_id": int(ctx.get("dono_id", 0) or 0),
            "token_arremesso": str(ctx.get("token_arremesso") or ""),
            "bola_nome": str(nome_bola or ""),
            "bola_posicao": list(bola_pos),
            "retorno_inicio": list(bola_pos),
            "retorno_destino": list(retorno_destino),
            "poder_total": float(poder),
            "chance_check": float(chance_check),
            "chance_real_3_checks": float(chance_real_checks),
            "captura_garantida": bool(garantida),
            "liberar_movimento_tick": int(liberar_tick),
            "efeitos_bola": dict(bola.get("efeitos", {})) if isinstance(bola.get("efeitos"), dict) else {},
        }
    )

    pokemon.estado_extra["captura_fase"] = "resolvida"
    pokemon.estado_extra["ativo"] = not sucesso
    pokemon.estado_extra["capturado"] = bool(sucesso)
    pokemon.estado_extra["cooldown_movimento_ate_tick"] = int(liberar_tick)

    print(
        "[CAPTURA_MATEMATICA_SERVER] "
        f"pokemon_id={int(getattr(pokemon, 'Id', 0) or 0)} especie={pokemon.estado_extra.get('especie', '')} "
        f"token={ctx.get('token_arremesso', '')} bola={nome_bola} garantida={garantida} "
        f"poder_base_captura={poder_base_captura:.3f} poder_base={poder_base:.3f} bonus_frutas={bonus_frutas:.3f} bonus_bioma={bonus_bioma_valor:.3f} "
        f"maestria={maestria:.3f} bonus_maestria_total={bonus_maestria_total:.3f} "
        f"critica_cliente={critica_cliente} multiplicador_critico={multiplicador_critico:.3f} "
        f"poder_total={poder:.3f} dificuldade={dificuldade:.3f} "
        f"formula_chance='clamp(base_check + (poder_total - dificuldade) * escala_diferenca, check_min, check_max)' "
        f"chance_check={chance_check:.3f}% chance_real_3_checks={chance_real_checks:.3f}% "
        f"rolagens={[round(x, 3) for x in rolagens]} checagens={checks} resultado={resultado}"
    )

    return {
        "iniciada": True,
        "eventos": [],
        "resultado": str(resultado),
        "checagens": list(checks),
        "sucesso": bool(sucesso),
        "cooldown_tick": int(liberar_tick),
    }
