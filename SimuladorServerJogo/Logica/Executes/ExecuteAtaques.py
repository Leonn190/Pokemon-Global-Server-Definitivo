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


# Interface autoritativa da Batalha v7. O registro antigo acima continua
# disponivel para sistemas legados, mas a nova rodada server-side chama apenas
# as funcoes abaixo.


def obter_execute_principal(nome_ou_code):
    nome = _normalizar(nome_ou_code)
    aliases = {
        "1": "investida",
        "2": "biscoito",
        "3": "enraivecer",
        "4": "provocar",
        "5": "proteger",
        "6": "arranhar",
        "7": "recarga",
        "8": "energia",
        "9": "hiperraio",
        "10": "guilhotina",
        "11": "disparo",
        "12": "chifrada",
        "13": "resetar",
        "14": "tankar",
        "15": "estocada",
        "16": "bolaclimatica",
        "17": "hiperpresa",
        "18": "acumulador",
    }
    chave = aliases.get(str(nome_ou_code), nome)
    return _EXECUTES_BATALHA_V7.get(chave)


def executar_execute_principal(nome_ou_code, contexto, alvo=None):
    props = (contexto or {}).get("propriedades") if isinstance((contexto or {}).get("propriedades"), dict) else {}
    ataque = (contexto or {}).get("ataque") if isinstance((contexto or {}).get("ataque"), dict) else {}
    func = obter_execute_principal(nome_ou_code) or obter_execute_principal(props.get("Code")) or obter_execute_principal(ataque.get("Code"))
    if not callable(func):
        return {"falha": True, "motivo": "execute_nao_encontrado"}
    return dict(func(dict(contexto or {}), alvo) or {})


def executar_alvificacao(nome_ou_code, contexto):
    props = (contexto or {}).get("propriedades") if isinstance((contexto or {}).get("propriedades"), dict) else {}
    estilo = str(props.get("estilo_logico") or "").strip().lower()
    if estilo == "ativo":
        return []
    partida = (contexto or {}).get("partida")
    acao = (contexto or {}).get("acao") if isinstance((contexto or {}).get("acao"), dict) else {}
    alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    area_id = alvo.get("area_id")
    if partida is None or not area_id:
        return []
    tipo_alvo = str((props.get("alvificacao") or {}).get("tipo") if isinstance(props.get("alvificacao"), dict) else "").strip().lower()
    if tipo_alvo in {"linha", "fileira", "row", "line"}:
        return [p for p in _alvos_linha(partida, area_id) if p is not None]
    if tipo_alvo in {"coluna", "column"}:
        return [p for p in _alvos_coluna(partida, area_id) if p is not None]
    ocupante = partida.pokemon_na_area(area_id)
    return [ocupante] if ocupante is not None else []


def obter_executes_perifericos(nome_ou_code):
    _ = nome_ou_code
    return []


def _tipo_contexto(ctx):
    props = ctx.get("propriedades") if isinstance(ctx.get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return parametros.get("tipo") or props.get("tipo") or "normal"


def _dano(ctx, alvo, bruto, categoria="normal", **extra):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    ataque = ctx.get("ataque") if isinstance(ctx.get("ataque"), dict) else {}
    props = ctx.get("propriedades") if isinstance(ctx.get("propriedades"), dict) else {}
    dados = {
        "dano_bruto": max(0.0, float(bruto or 0.0)),
        "tipo": _tipo_contexto(ctx),
        "categoria": categoria,
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID") or props.get("Code"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
        **extra,
    }
    return usuario.AplicarDano(alvo, dados, contexto=ctx)


def _aplicar_efeito(usuario, alvo, nome, duracao=3, dados=None, valor=0.0, negativo=None):
    efeito = {"nome": nome, "duracao": duracao, "valor": valor}
    if negativo is not None:
        efeito["negativo"] = bool(negativo)
    return usuario.AplicarEfeito(alvo, efeito, dados=dados or {})


def _critico_simples(usuario, ctx, maximo=None):
    chance = float(usuario.obter_atributo("CrC", 0.0))
    if maximo is not None:
        chance = min(chance, float(maximo))
    rng = ctx.get("rng")
    return bool(chance > 0 and rng is not None and rng.random() * 100.0 <= chance)


def _exec_investida(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = _dano(ctx, alvo, usuario.obter_atributo("Atk") * 1.20, "normal")
    dano_vida = float(ret.get("dano_vida") or 0.0)
    if dano_vida > 0:
        usuario.ReceberDano(dano_vida * 0.20, origem=usuario, dados={"recuo": "Investida"})
    return ret


def _exec_biscoito(ctx, alvo):
    usuario = ctx.get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    stacks = int(alvo.contadores_especiais.get("Biscoito", 0) or 0)
    critico = _critico_simples(usuario, ctx)
    cura = usuario.obter_atributo("Mag") * 0.55
    cura += stacks * usuario.obter_atributo("Mag") * (0.15 if critico else 0.10)
    ret = usuario.AplicarCura(alvo, cura, dados={"ataque": "Biscoito", "ataque_id": 2, "ataque_nome": "Biscoito", "critico": critico})
    alvo.contadores_especiais["Biscoito"] = stacks + 1
    if usuario is not alvo:
        usuario.contadores_especiais["Biscoito"] = int(usuario.contadores_especiais.get("Biscoito", 0) or 0) + 1
    return ret


def _exec_enraivecer(ctx, alvo):
    usuario = ctx.get("usuario")
    vida_max = max(1.0, usuario.obter_atributo("Vida", 1.0))
    if usuario.VidaAtual / vida_max < 0.40:
        return _aplicar_efeito(usuario, usuario, "Amplificado", duracao=3, valor=max(10.0, usuario.obter_atributo("Mag") * 0.20), negativo=False)
    return {"aplicado": True, "sem_efeito": True}


def _exec_provocar(ctx, alvo):
    usuario = ctx.get("usuario")
    return _aplicar_efeito(usuario, usuario, "Provocando", duracao=3, negativo=False)


def _exec_proteger(ctx, alvo):
    usuario = ctx.get("usuario")
    alvo = alvo or usuario
    alvo.adicionar_estado_transitorio("protegido", {"passo": ctx.get("passo")})
    return {"aplicado": True, "estado": "protegido"}


def _exec_arranhar(ctx, alvo):
    usuario = ctx.get("usuario")
    return _dano(ctx, alvo, usuario.obter_atributo("Atk") * 1.35, "normal")


def _exec_recarga(ctx, alvo):
    usuario = ctx.get("usuario")
    return usuario.GanharEnergia(float(ctx.get("custo_real") or 0.0) * 2.0, dados={"ataque": "Recarga", "motivo": "Recarga"})


def _exec_energia(ctx, alvo):
    usuario = ctx.get("usuario")
    return _dano(ctx, alvo, usuario.obter_atributo("SpA") * 1.15, "especial")


def _exec_hiper_raio(ctx, alvo):
    usuario = ctx.get("usuario")
    alvos = [a for a in list(ctx.get("alvos") or []) if a is not None and a.esta_vivo()]
    atingidos = max(1, len(alvos))
    bruto = max(0.0, usuario.obter_atributo("SpA") * 1.50 - ((atingidos - 1) * usuario.obter_atributo("SpA") * 0.15))
    return _dano(ctx, alvo, bruto, "especial")


def _exec_guilhotina(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = _dano(ctx, alvo, usuario.obter_atributo("Atk") * 0.80, "normal")
    if ret.get("critico") and alvo is not None and int(alvo.lado_id) != int(usuario.lado_id):
        if alvo.VidaAtual < alvo.obter_atributo("Vida", 1.0) * 0.25:
            alvo.Morrer({"ataque": "Guilhotina"})
            ret["execucao_guilhotina"] = True
    return ret


def _exec_disparo(ctx, alvo):
    usuario = ctx.get("usuario")
    return _dano(ctx, alvo, usuario.obter_atributo("Atk") * 1.00, "normal")


def _exec_chifrada(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * 0.90 + usuario.obter_atributo("Per") * 0.40
    return _dano(ctx, alvo, bruto, "normal")


def _exec_resetar(ctx, alvo):
    if alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    alvo.variacoes_permanentes = {k: 0.0 for k in alvo.variacoes_permanentes}
    alvo.recalcular_atributos()
    return {"aplicado": True, "resetou_variacoes": True}


def _exec_tankar(ctx, alvo):
    usuario = ctx.get("usuario")
    defesa = "Dur"
    bonus = usuario.obter_atributo("Mag") * 0.20
    ret = _aplicar_efeito(usuario, usuario, "Fortificado", duracao=3, dados={"atributo": defesa, "valor": bonus}, valor=bonus, negativo=False)
    if _critico_simples(usuario, ctx):
        usuario.ReceberBarreira(bonus, origem=usuario, dados={"ataque": "Tankar", "ataque_id": 14, "ataque_nome": "Tankar", "critico": True})
        ret["barreira_critica"] = bonus
    return ret


def _exec_estocada(ctx, alvo):
    usuario = ctx.get("usuario")
    bruto = usuario.obter_atributo("Atk") * 1.05
    if bool(ctx.get("primeiro_ataque_da_rodada")):
        bruto *= 1.25
    return _dano(ctx, alvo, bruto, "normal")


def _exec_bola_climatica(ctx, alvo):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    bruto = usuario.obter_atributo("SpA") * (1.30 if getattr(partida, "clima_atual", None) else 1.05)
    ret = _dano(ctx, alvo, bruto, "especial")
    dano_vida = float(ret.get("dano_vida") or 0.0)
    if alvo is not None and dano_vida > 0 and partida is not None:
        for adj in _adjacentes(partida, alvo.area_id):
            poke = partida.pokemon_na_area(adj)
            if poke is not None and int(poke.lado_id) != int(usuario.lado_id) and poke is not alvo:
                poke.ReceberDano(dano_vida * 0.50, origem=usuario, dados={"splash": "Bola Climática"})
    return ret


def _exec_hiper_presa(ctx, alvo):
    usuario = ctx.get("usuario")
    ret = _dano(ctx, alvo, usuario.obter_atributo("Atk") * 1.40, "normal", chance_critico_max=80.0)
    if ret.get("critico") and alvo is not None:
        alvo.adicionar_estado_transitorio("recuado", {"ataque": "Hiper Presa"})
    return ret


def _exec_acumulador(ctx, alvo):
    return {"falha": True, "motivo": "passiva_nao_manual"}


def _coords_area(area_id):
    texto = str(area_id or "")
    if len(texto) < 2:
        return None
    try:
        idx = int(texto[1:]) - 1
    except ValueError:
        return None
    return texto[0], idx // 3, idx % 3


def _area_por_coords(prefixo, row, col):
    if row < 0 or row > 2 or col < 0 or col > 2:
        return None
    return f"{prefixo}{row * 3 + col + 1}"


def _adjacentes(partida, area_id):
    coords = _coords_area(area_id)
    if coords is None:
        return []
    prefixo, row, col = coords
    areas = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            aid = _area_por_coords(prefixo, row + dr, col + dc)
            if aid and partida.area_existe(aid):
                areas.append(aid)
    return areas


def _alvos_linha(partida, area_id):
    coords = _coords_area(area_id)
    if coords is None:
        return []
    prefixo, row, _col = coords
    return [partida.pokemon_na_area(_area_por_coords(prefixo, row, col)) for col in range(3)]


def _alvos_coluna(partida, area_id):
    coords = _coords_area(area_id)
    if coords is None:
        return []
    prefixo, _row, col = coords
    return [partida.pokemon_na_area(_area_por_coords(prefixo, row, col)) for row in range(3)]


_EXECUTES_BATALHA_V7 = {
    "investida": _exec_investida,
    "biscoito": _exec_biscoito,
    "enraivecer": _exec_enraivecer,
    "provocar": _exec_provocar,
    "proteger": _exec_proteger,
    "arranhar": _exec_arranhar,
    "recarga": _exec_recarga,
    "energia": _exec_energia,
    "hiperraio": _exec_hiper_raio,
    "guilhotina": _exec_guilhotina,
    "disparo": _exec_disparo,
    "chifrada": _exec_chifrada,
    "resetar": _exec_resetar,
    "tankar": _exec_tankar,
    "estocada": _exec_estocada,
    "bolaclimatica": _exec_bola_climatica,
    "hiperpresa": _exec_hiper_presa,
    "acumulador": _exec_acumulador,
}
