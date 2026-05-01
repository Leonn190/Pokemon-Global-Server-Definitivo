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
    poder_base = float(bola.get("poder_base", 0.0) or 0.0)
    poder = float(poder_base)

    estado_fruta = pokemon.estado_extra.get("estado_frutificacao") if isinstance(pokemon.estado_extra.get("estado_frutificacao"), dict) else {}
    bonus_frutas = float(estado_fruta.get("bonus_captura_frutas", 0.0) or 0.0)
    poder += bonus_frutas
    bonus_bioma = estado_fruta.get("bonus_captura_bioma") if isinstance(estado_fruta.get("bonus_captura_bioma"), dict) else {}
    bonus_bioma_valor = float(bonus_bioma.get(str(ctx.get("bioma", "")).lower(), 0.0) or 0.0)
    poder += bonus_bioma_valor

    maestria = float(ctx.get("maestria", 0.0) if ctx.get("maestria", 0.0) not in (None, "") else 0.0)
    bonus_maestria = float(ctx.get("captura_bonus_maestria", 10.0) if ctx.get("captura_bonus_maestria", 10.0) not in (None, "") else 10.0)
    bonus_maestria_total = maestria * bonus_maestria
    poder += bonus_maestria_total
    bonus_critica = 0.0
    if bool(ctx.get("captura_critica_cliente", False)):
        bonus_critica = float(ctx.get("captura_bonus_critica_cliente", 15.0) if ctx.get("captura_bonus_critica_cliente", 15.0) not in (None, "") else 15.0)
        poder += bonus_critica

    dificuldade = float(pokemon.estado_extra.get("dificuldade_captura", 50.0) or 50.0)
    garantida = bool(bola.get("captura_garantida", False))
    chance_min = float(ctx.get("captura_chance_min", 2.0) if ctx.get("captura_chance_min", 2.0) not in (None, "") else 2.0)
    chance_max = float(ctx.get("captura_chance_max", 95.0) if ctx.get("captura_chance_max", 95.0) not in (None, "") else 95.0)
    chance_escape = 0.0 if garantida else max(chance_min, min(chance_max, dificuldade - poder))
    chance_captura_check = 100.0 - chance_escape
    chance_captura_total = 100.0 if garantida else (chance_captura_check / 100.0) ** 3 * 100.0

    dono_pos = ctx.get("dono_posicao") if isinstance(ctx.get("dono_posicao"), (list, tuple)) and len(ctx.get("dono_posicao")) == 2 else None
    bola_pos = [float(pokemon.posicao[0]), float(pokemon.posicao[1])]
    retorno_destino = [float(dono_pos[0]), float(dono_pos[1])] if dono_pos else list(bola_pos)

    checks: List[bool] = []
    rolagens: List[float] = []
    falhou = False
    for _idx in range(1, 4):
        if falhou:
            checks.append(False)
            continue
        passou = bool(garantida)
        if not passou:
            rolagem = random.uniform(0.0, 100.0)
            rolagens.append(float(rolagem))
            passou = rolagem > chance_escape
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
            "chance_escape": float(chance_escape),
            "captura_garantida": bool(garantida),
            "liberar_movimento_tick": int(liberar_tick),
            "efeitos_bola": dict(bola.get("efeitos", {})) if isinstance(bola.get("efeitos"), dict) else {},
        }
    )

    pokemon.estado_extra["captura_fase"] = "resolvida"
    pokemon.estado_extra["ativo"] = not sucesso
    pokemon.estado_extra["capturado"] = bool(sucesso)
    pokemon.estado_extra["cooldown_movimento_ate_tick"] = int(liberar_tick)
    if not sucesso:
        pokemon.estado_extra["tentativas_falhas_captura"] = int(pokemon.estado_extra.get("tentativas_falhas_captura", 0) or 0) + 1

    print(
        "[CAPTURA_MATEMATICA_SERVER] "
        f"pokemon_id={int(getattr(pokemon, 'Id', 0) or 0)} especie={pokemon.estado_extra.get('especie', '')} "
        f"token={ctx.get('token_arremesso', '')} bola={nome_bola} garantida={garantida} "
        f"poder_base={poder_base:.3f} bonus_frutas={bonus_frutas:.3f} bonus_bioma={bonus_bioma_valor:.3f} "
        f"maestria={maestria:.3f} bonus_maestria_por_ponto={bonus_maestria:.3f} bonus_maestria_total={bonus_maestria_total:.3f} "
        f"critica_cliente={bool(ctx.get('captura_critica_cliente', False))} bonus_critica={bonus_critica:.3f} "
        f"poder_total={poder:.3f} dificuldade={dificuldade:.3f} chance_min={chance_min:.3f} chance_max={chance_max:.3f} "
        f"formula_escape='clamp(dificuldade - poder_total, chance_min, chance_max)' chance_escape_por_check={chance_escape:.3f}% "
        f"chance_captura_por_check={chance_captura_check:.3f}% chance_captura_3_checks={chance_captura_total:.3f}% "
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
