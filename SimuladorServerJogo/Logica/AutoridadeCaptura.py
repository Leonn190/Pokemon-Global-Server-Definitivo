from __future__ import annotations

import random
from typing import Dict, List

from SimuladorServerJogo.Logica.ExecutesFrutas import executar_fruta
from SimuladorServerJogo.Logica.ExecutesPokebolas import executar_pokebola


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


def _evento_fase(pokemon_id: int, captura: Dict[str, object], fase: str) -> Dict[str, object]:
    return {
        "evento": f"pokemon_captura_{fase}",
        "payload": {
            "pokemon_id": int(pokemon_id),
            "captura": dict(captura) | {"fase": fase},
        },
    }


def _agendar_desfecho(agenda: List[Dict[str, object]], base_ms: int, sucesso: bool) -> None:
    agenda.extend(
        [
            {"fase": "sucesso", "at_ms": int(base_ms + 220)},
            {"fase": "retorno_bola", "at_ms": int(base_ms + 460)},
            {"fase": "finalizada", "at_ms": int(base_ms + 720)},
        ]
        if sucesso
        else [
            {"fase": "escape", "at_ms": int(base_ms + 220)},
            {"fase": "escape_reaparecendo", "at_ms": int(base_ms + 460)},
            {"fase": "finalizada", "at_ms": int(base_ms + 720)},
        ]
    )


def resolver_captura(pokemon, nome_bola, contexto=None):
    ctx = dict(contexto or {})
    captura = pokemon.estado_extra.setdefault("captura", {})
    if bool(captura.get("ativa", False)):
        return {"iniciada": False, "motivo": "captura_em_andamento", "eventos": []}

    bola = executar_pokebola(nome_bola, pokemon, contexto=ctx)
    poder = float(bola.get("poder_base", 0.0) or 0.0)

    estado_fruta = pokemon.estado_extra.get("estado_frutificacao") if isinstance(pokemon.estado_extra.get("estado_frutificacao"), dict) else {}
    poder += float(estado_fruta.get("bonus_captura_frutas", 0.0) or 0.0)
    bonus_bioma = estado_fruta.get("bonus_captura_bioma") if isinstance(estado_fruta.get("bonus_captura_bioma"), dict) else {}
    poder += float(bonus_bioma.get(str(ctx.get("bioma", "")).lower(), 0.0) or 0.0)

    maestria = float(ctx.get("maestria", 0.0) or 0.0)
    poder += maestria * 10.0

    dificuldade = float(pokemon.estado_extra.get("dificuldade_captura", 50.0) or 50.0)
    garantida = bool(bola.get("captura_garantida", False))
    chance_escape = 0.0 if garantida else max(2.0, min(95.0, dificuldade - poder))

    agora_ms = int(ctx.get("servidor_agora_ms", 0) or 0)
    if agora_ms <= 0:
        return {"iniciada": False, "motivo": "tempo_invalido", "eventos": []}

    dono_pos = ctx.get("dono_posicao") if isinstance(ctx.get("dono_posicao"), (list, tuple)) and len(ctx.get("dono_posicao")) == 2 else None
    bola_pos = [float(pokemon.posicao[0]), float(pokemon.posicao[1])]
    retorno_destino = [float(dono_pos[0]), float(dono_pos[1])] if dono_pos else list(bola_pos)

    base = {
        "inicio_ms_servidor": agora_ms,
        "fase_inicio_ms": agora_ms,
        "poder_total": poder,
        "chance_escape": chance_escape,
        "bola_nome": nome_bola,
        "dono_id": int(ctx.get("dono_id", 0) or 0),
        "critico": bool(ctx.get("critico", False)),
        "bola_posicao": list(bola_pos),
        "retorno_inicio": list(bola_pos),
        "retorno_destino": list(retorno_destino),
    }

    agenda: List[Dict[str, object]] = [
        {"fase": "iniciada", "at_ms": int(agora_ms)},
        {"fase": "absorcao", "at_ms": int(agora_ms + 180)},
        {"fase": "bola_no_chao", "at_ms": int(agora_ms + 420)},
        {"fase": "tremida1", "at_ms": int(agora_ms + 700)},
        {"fase": "tremida2", "at_ms": int(agora_ms + 930)},
        {"fase": "tremida3", "at_ms": int(agora_ms + 1160)},
    ]

    plano_tremidas: List[bool] = []
    falhou = False
    for _ in range(3):
        if falhou:
            plano_tremidas.append(False)
            continue
        passou = bool(garantida)
        if not passou:
            passou = random.uniform(0.0, 100.0) > chance_escape
        plano_tremidas.append(bool(passou))
        if not passou:
            falhou = True

    captura.clear()
    captura.update(base)
    captura.update(
        {
            "fase": "iniciada",
            "ativa": True,
            "captura_garantida": garantida,
            "tentativas_tremida": [],
            "plano_tremidas": plano_tremidas,
            "agenda": agenda,
        }
    )
    pokemon.estado_extra["captura_fase"] = "iniciada"

    return {"iniciada": True, "eventos": []}


def coletar_eventos_captura_agendada(pokemon, servidor_agora_ms: int):
    captura = pokemon.estado_extra.get("captura") if isinstance(pokemon.estado_extra.get("captura"), dict) else None
    if not captura or not bool(captura.get("ativa", False)):
        return []

    agenda = captura.get("agenda") if isinstance(captura.get("agenda"), list) else []
    if not agenda:
        captura["ativa"] = False
        return []

    pokemon_id = int(getattr(pokemon, "Id", 0) or 0)
    eventos = []
    while agenda and int(agenda[0].get("at_ms", 0) or 0) <= int(servidor_agora_ms):
        item = dict(agenda.pop(0))
        fase = str(item.get("fase") or "")
        if not fase:
            continue

        captura["fase"] = fase
        captura["fase_inicio_ms"] = int(item.get("at_ms", servidor_agora_ms) or servidor_agora_ms)
        pokemon.estado_extra["captura_fase"] = fase

        if fase.startswith("tremida"):
            try:
                idx = int(fase.replace("tremida", ""))
            except Exception:
                idx = 0
            captura["tremida_atual"] = idx
            plano = captura.get("plano_tremidas") if isinstance(captura.get("plano_tremidas"), list) else []
            sucesso_tentativa = bool(plano[idx - 1]) if 0 < idx <= len(plano) else False

            tentativas = captura.get("tentativas_tremida") if isinstance(captura.get("tentativas_tremida"), list) else []
            tentativas.append({"tremida": idx, "sucesso": bool(sucesso_tentativa)})
            captura["tentativas_tremida"] = tentativas

            if not sucesso_tentativa:
                agenda[:] = [a for a in agenda if str(a.get("fase", "")).strip().lower() not in {"tremida2", "tremida3", "sucesso", "retorno_bola", "finalizada"}]
                _agendar_desfecho(agenda, captura["fase_inicio_ms"], sucesso=False)
            elif idx >= 3:
                _agendar_desfecho(agenda, captura["fase_inicio_ms"], sucesso=True)

        if fase == "escape":
            pokemon.estado_extra["tentativas_falhas_captura"] = int(pokemon.estado_extra.get("tentativas_falhas_captura", 0) or 0) + 1
        if fase == "sucesso":
            pokemon.estado_extra["capturado"] = True
            pokemon.estado_extra["ativo"] = False
        if fase == "finalizada":
            captura["ativa"] = False

        eventos.append(_evento_fase(pokemon_id, captura, fase))

    captura["agenda"] = agenda
    return eventos
