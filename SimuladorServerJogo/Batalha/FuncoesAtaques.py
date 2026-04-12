from __future__ import annotations

import math
import unicodedata
from typing import Dict


_REGISTRO_ATAQUES: dict[str, dict[str, object]] = {}

_PONTOS_ALIAS = {
    "ini": "INI",
    "aoiniciaracao": "INI",
    "pre": "PRE",
    "antesdoimpacto": "PRE",
    "cri": "CRI",
    "critico": "CRI",
    "antescritico": "CRI",
    "dmg": "DMG",
    "antesaplicardano": "DMG",
    "aux": "AUX",
    "antesaplicarauxiliares": "AUX",
    "antesaplicarsuporte": "AUX",
    "pos": "POS",
    "aposaplicardano": "POS",
    "fim": "FIM",
    "aofinalizaracao": "FIM",
}

_MAPA_CLIMA_TIPO = {
    "sol": "fogo",
    "ensolarado": "fogo",
    "sun": "fogo",
    "chuva": "agua",
    "rain": "agua",
    "neve": "gelo",
    "hail": "gelo",
    "granizo": "gelo",
    "tempestadedeareia": "pedra",
    "sandstorm": "pedra",
    "tempestadeeletrica": "eletrico",
    "storm": "eletrico",
    "vendaval": "voador",
    "wind": "voador",
}


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _normalizar_ponto(valor: object) -> str:
    chave = _normalizar(valor)
    return _PONTOS_ALIAS.get(chave, str(valor or "").strip().upper())


def _fnum(valor: object, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _contar_stacks(pokemon, nome_efeito: str) -> int:
    alvo = _normalizar(nome_efeito)
    total = 0
    for efeito in list(getattr(pokemon, "Efeitos", []) or []):
        if _normalizar(dict(efeito).get("nome")) == alvo:
            total += 1
    return total


def _empurrar_alvo(sistema, executor, alvo, distancia_tiles: float) -> None:
    try:
        ox, oy = float(executor.Posicao[0]), float(executor.Posicao[1])
        ax, ay = float(alvo.Posicao[0]), float(alvo.Posicao[1])
    except Exception:
        return
    dx = ax - ox
    dy = ay - oy
    norma = math.hypot(dx, dy)
    if norma <= 1e-9:
        dx, dy, norma = 1.0, 0.0, 1.0
    destino = (ax + (dx / norma) * float(distancia_tiles), ay + (dy / norma) * float(distancia_tiles))
    largura = _fnum(getattr(sistema, "Contexto", {}).get("largura"), 80.0)
    altura = _fnum(getattr(sistema, "Contexto", {}).get("altura"), 40.0)
    raio = _fnum(getattr(alvo, "RaioColisao", 0.3), 0.3)
    alvo.Posicao = (
        max(raio, min(largura - raio, destino[0])),
        max(raio, min(altura - raio, destino[1])),
    )


def _alvo_mais_proximo(sistema, executor, destino=None):
    lado_alvo = "inimigo" if str(getattr(executor, "Lado", "") or "") == "jogador" else "jogador"
    candidatos = [p for p in list(sistema.listar_ativos(lado_alvo) or []) if not bool(getattr(p, "ForaDeCombate", False))]
    if not candidatos:
        return None
    if not (isinstance(destino, (list, tuple)) and len(destino) == 2):
        return min(candidatos, key=lambda alvo: math.hypot(float(alvo.Posicao[0]) - float(executor.Posicao[0]), float(alvo.Posicao[1]) - float(executor.Posicao[1])))
    return min(candidatos, key=lambda alvo: math.hypot(float(alvo.Posicao[0]) - float(destino[0]), float(alvo.Posicao[1]) - float(destino[1])))


def registrar_funcao_ataque(nome_ataque: str, ponto_analise: str, funcao) -> None:
    nome = _normalizar(nome_ataque)
    ponto = _normalizar_ponto(ponto_analise)
    if not nome or not ponto or not callable(funcao):
        return
    _REGISTRO_ATAQUES.setdefault(nome, {})[ponto] = funcao


def registrar_ataque(nome_ataque: str, ponto_analise: str):
    def _decorador(funcao):
        registrar_funcao_ataque(nome_ataque, ponto_analise, funcao)
        return funcao

    return _decorador


def executar_ponto_ataque(nome_ataque: object, ponto_analise: str, contexto: Dict[str, object] | None = None) -> Dict[str, object]:
    nome = _normalizar(nome_ataque)
    ponto = _normalizar_ponto(ponto_analise)
    if not nome or not ponto:
        return {}
    funcao = _REGISTRO_ATAQUES.get(nome, {}).get(ponto)
    if not callable(funcao):
        return {}
    retorno = funcao(dict(contexto or {}))
    return dict(retorno) if isinstance(retorno, dict) else {}


@registrar_ataque("Investida", "INI")
def ataque_investida__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Biscoito", "AUX")
def ataque_biscoito__aux(ctx: Dict[str, object]) -> Dict[str, object]:
    executor = ctx.get("executor")
    alvo = ctx.get("alvo")
    if executor is None or alvo is None:
        return {}
    stacks = _contar_stacks(executor, "Biscoito") + _contar_stacks(alvo, "Biscoito")
    if stacks <= 0:
        return {}
    bonus = _fnum(getattr(executor, "obter_atributo", lambda *_: 0.0)("Mag"), 0.0) * 0.05 * float(stacks)
    return {"cura_bonus_fixa": bonus}


@registrar_ataque("Enraivecer", "INI")
def ataque_enraivecer__ini(ctx: Dict[str, object]) -> Dict[str, object]:
    executor = ctx.get("executor")
    spec = ctx.get("spec") if isinstance(ctx.get("spec"), dict) else None
    if executor is None or spec is None:
        return {}
    vida_max = max(1.0, _fnum(getattr(executor, "obter_atributo", lambda *_: 1.0)("Vida"), 1.0))
    percentual = _fnum(getattr(executor, "VidaAtual", 0.0), 0.0) / vida_max
    spec["efeitos_self"] = []
    if percentual >= 0.5:
        return {}
    efeito = "Aprimorado" if _fnum(executor.obter_atributo("SpA"), 0.0) > _fnum(executor.obter_atributo("Atk"), 0.0) else "Amplificado"
    spec["efeitos_self"] = [efeito]
    return {"efeito_condicional": efeito}


@registrar_ataque("Provocar", "INI")
def ataque_provocar__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Proteger", "INI")
def ataque_proteger__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Arranhar", "INI")
def ataque_arranhar__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Recarga", "INI")
def ataque_recarga__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Energia", "INI")
def ataque_energia__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Hiper Raio", "INI")
def ataque_hiper_raio__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Guilhotina", "POS")
def ataque_guilhotina__pos(ctx: Dict[str, object]) -> Dict[str, object]:
    pacote = ctx.get("pacote") if isinstance(ctx.get("pacote"), dict) else {}
    if not bool(pacote.get("critico", False)):
        return {}
    executor = ctx.get("executor")
    alvo = ctx.get("alvo")
    sistema = ctx.get("sistema")
    tick = int(_fnum(ctx.get("tick"), 0))
    if executor is None or alvo is None or bool(getattr(alvo, "ForaDeCombate", False)):
        return {}
    vida_max = max(1.0, _fnum(getattr(alvo, "obter_atributo", lambda *_: 1.0)("Vida"), 1.0))
    percentual = _fnum(getattr(alvo, "VidaAtual", 0.0), 0.0) / vida_max
    if percentual > 0.30:
        return {}
    if percentual <= 0.25:
        return {}
    detalhe = alvo.TomarDano({"dano_final": _fnum(getattr(alvo, "VidaAtual", 0.0), 0.0), "origem": executor, "origem_id": getattr(executor, "Uid", "")}, sistema=sistema, tick=tick)
    return {"execucao_critica": True, "detalhe_execucao": detalhe}


@registrar_ataque("Disparo", "INI")
def ataque_disparo__ini(ctx: Dict[str, object]) -> Dict[str, object]:
    spec = ctx.get("spec") if isinstance(ctx.get("spec"), dict) else None
    if spec is None:
        return {}
    for fluxo in list(spec.get("subfluxos") or []):
        if isinstance(fluxo, dict):
            fluxo["numero_ricochets"] = 1
    fluxo_base = spec.get("fluxo")
    if isinstance(fluxo_base, dict):
        fluxo_base["numero_ricochets"] = 1
    return {"ricochetes_nivel_1": 1}


@registrar_ataque("Chifrada", "INI")
def ataque_chifrada__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Resetar", "INI")
def ataque_resetar__ini(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {}


@registrar_ataque("Tankar", "INI")
def ataque_tankar__ini(ctx: Dict[str, object]) -> Dict[str, object]:
    executor = ctx.get("executor")
    if executor is None or not hasattr(executor, "ModificarStatus"):
        return {}
    bonus = _fnum(executor.obter_atributo("Mag"), 0.0) * 0.10
    defesa = _fnum(executor.obter_atributo("Def"), 0.0)
    defesa_especial = _fnum(executor.obter_atributo("SpD"), 0.0)
    aplicados = []
    if defesa <= defesa_especial:
        aplicados.append(executor.ModificarStatus("Def", bonus, temporario=False))
    if defesa_especial <= defesa:
        aplicados.append(executor.ModificarStatus("SpD", bonus, temporario=False))
    return {"buff_defensivo": aplicados}


@registrar_ataque("Estocada", "INI")
def ataque_estocada__ini(ctx: Dict[str, object]) -> Dict[str, object]:
    spec = ctx.get("spec") if isinstance(ctx.get("spec"), dict) else None
    log = ctx.get("log") if isinstance(ctx.get("log"), dict) else {}
    if spec is None:
        return {}
    ja_houve_ataque = any(str(evento.get("tipo") or "") in {"dano", "execucao"} for evento in list(log.get("eventos") or []))
    spec["_estocada_primeiro_ataque_turno"] = not ja_houve_ataque
    return {"primeiro_ataque_turno": bool(spec["_estocada_primeiro_ataque_turno"])}


@registrar_ataque("Estocada", "DMG")
def ataque_estocada__dmg(ctx: Dict[str, object]) -> Dict[str, object]:
    spec = ctx.get("spec") if isinstance(ctx.get("spec"), dict) else {}
    if not bool(spec.get("_estocada_primeiro_ataque_turno", False)):
        return {}
    return {"multiplicador_dano": 1.30}


@registrar_ataque("Bola Climática", "INI")
def ataque_bola_climatica__ini(ctx: Dict[str, object]) -> Dict[str, object]:
    sistema = ctx.get("sistema")
    spec = ctx.get("spec") if isinstance(ctx.get("spec"), dict) else None
    if sistema is None or spec is None:
        return {}
    clima = _normalizar(getattr(sistema, "ClimaAtual", ""))
    tipo = _MAPA_CLIMA_TIPO.get(clima)
    if tipo:
        spec["tipo"] = tipo
        spec["_bola_climatica_bonus"] = 1.10
        return {"tipo_adaptado": tipo, "bonus_clima": 1.10}
    spec["_bola_climatica_bonus"] = 1.0
    return {}


@registrar_ataque("Bola Climática", "DMG")
def ataque_bola_climatica__dmg(ctx: Dict[str, object]) -> Dict[str, object]:
    spec = ctx.get("spec") if isinstance(ctx.get("spec"), dict) else {}
    bonus = _fnum(spec.get("_bola_climatica_bonus"), 1.0)
    if bonus <= 1.0:
        return {}
    return {"multiplicador_dano": bonus}


@registrar_ataque("Hiper Presa", "CRI")
def ataque_hiper_presa__cri(_ctx: Dict[str, object]) -> Dict[str, object]:
    return {"chance_maxima": 80.0}


@registrar_ataque("Hiper Presa", "POS")
def ataque_hiper_presa__pos(ctx: Dict[str, object]) -> Dict[str, object]:
    pacote = ctx.get("pacote") if isinstance(ctx.get("pacote"), dict) else {}
    if not bool(pacote.get("critico", False)):
        return {}
    sistema = ctx.get("sistema")
    executor = ctx.get("executor")
    alvo = ctx.get("alvo")
    if sistema is None or executor is None or alvo is None or bool(getattr(alvo, "ForaDeCombate", False)):
        return {}
    _empurrar_alvo(sistema, executor, alvo, 1.25)
    return {"recuo_critico": True, "nova_posicao": [float(alvo.Posicao[0]), float(alvo.Posicao[1])]}


@registrar_ataque("Investida Selvagem", "FIM")
def ataque_investida_selvagem__fim(ctx: Dict[str, object]) -> Dict[str, object]:
    if int(_fnum(ctx.get("acertos_total"), 0)) > 0:
        return {}
    sistema = ctx.get("sistema")
    executor = ctx.get("executor")
    jogada = ctx.get("jogada") if isinstance(ctx.get("jogada"), dict) else {}
    if sistema is None or executor is None or not hasattr(executor, "TomarDano"):
        return {}
    alvo_ref = _alvo_mais_proximo(sistema, executor, jogada.get("destino_mundo"))
    dano_base = _fnum(executor.obter_atributo("Atk"), 0.0) * 1.8
    if alvo_ref is not None and hasattr(alvo_ref, "obter_atributo"):
        dano_base = max(1.0, dano_base - (_fnum(alvo_ref.obter_atributo("Def"), 0.0) * 0.18))
    recoil = max(1.0, dano_base * 0.50)
    detalhe = executor.TomarDano({"dano_final": recoil, "origem": executor, "origem_id": getattr(executor, "Uid", "")}, sistema=sistema, tick=int(_fnum(ctx.get("tick"), 0)))
    return {"recoil_erro": round(recoil, 4), "detalhe_recoil": detalhe}
