from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any



FATOR_DANO_COLISAO = 0.08
FATOR_MASSA_COLISAO = 0.03
FATOR_VELOCIDADE_COLISAO = 0.15
FATOR_ATK_COLISAO = 0.10


@dataclass(slots=True)
class ContextoDano:
    atacante: object | None = None
    defensor: object | None = None
    ataque_spec: dict = field(default_factory=dict)
    jogada: dict = field(default_factory=dict)
    evento_colisao: object | None = None
    categoria: str = "normal"
    tipo_ataque: str | None = None
    momento: str = ""
    contexto_batalha: dict = field(default_factory=dict)
    dados: dict = field(default_factory=dict)


@dataclass(slots=True)
class ResultadoDano:
    dano_base: float = 0.0
    dano_apos_modificadores: float = 0.0
    dano_apos_defesa: float = 0.0
    dano_apos_durabilidade: float = 0.0
    dano_final: float = 0.0
    dano_barreira: float = 0.0
    dano_vida: float = 0.0
    foi_critico: bool = False
    multiplicador_critico: float = 1.0
    acertou: bool = True
    bloqueado_por_barreira: bool = False
    bloqueado_por_efeito: str | None = None
    tipo_dano: str = "ataque"
    categoria: str = "normal"
    tipo_ataque: str | None = None
    logs: list[str] = field(default_factory=list)
    dados: dict = field(default_factory=dict)


def _norm(v: object) -> str:
    return str(v or "").strip().casefold()


def _fnum(v: object, padrao: float = 0.0) -> float:
    try:
        if isinstance(v, str):
            return float(v.replace(",", "."))
        return float(v)
    except (TypeError, ValueError):
        return float(padrao)


def _obter(obj, nome: str, padrao=None):
    if obj is None:
        return padrao
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def efeitos_ativos(entidade) -> list:
    return list(_obter(entidade, "Efeitos", _obter(entidade, "efeitos", [])) or [])


def possui_efeito(entidade, nome: str) -> bool:
    alvo = _norm(nome)
    for ef in efeitos_ativos(entidade):
        if _norm(_obter(ef, "nome", "")) == alvo:
            return True
    return False


def obter_variacao_atributo(entidade, atributo: str) -> float:
    var_fixa = _obter(entidade, "VariacoesFixas", _obter(entidade, "variacoes_fixas", {}))
    var_temp = _obter(entidade, "VariacoesTemporarias", _obter(entidade, "variacoes_temporarias", {}))
    bonus = 0.0
    for bloco in (var_fixa, var_temp):
        if isinstance(bloco, dict):
            bonus += _fnum(bloco.get(atributo, bloco.get(atributo.lower(), 0.0)), 0.0)
    return bonus


def atributo_total(entidade, atributo: str, permitir_negativo: bool = False) -> float:
    if entidade is None:
        return 0.0
    base = 0.0
    if hasattr(entidade, "obter_atributo"):
        try:
            base = _fnum(entidade.obter_atributo(atributo), 0.0)
        except Exception:
            base = 0.0
    if base == 0.0:
        base = _fnum(_obter(entidade, atributo, _obter(entidade, atributo.lower(), 0.0)), 0.0)
        dados = _obter(entidade, "Dados", {})
        if base == 0.0 and isinstance(dados, dict):
            base = _fnum(dados.get(atributo, dados.get(atributo.lower(), 0.0)), 0.0)
    total = base + obter_variacao_atributo(entidade, atributo)
    return total if permitir_negativo else max(0.0, total)


def _rng(contexto: dict | None):
    ctx = contexto or {}
    if isinstance(ctx.get("rng"), random.Random):
        return ctx["rng"]
    seed = ctx.get("seed")
    return random.Random(seed) if seed is not None else random


def _chance_acerto(atacante, defensor, ataque_spec, contexto: dict | None) -> bool:
    if possui_efeito(atacante, "Focado"):
        return True
    assertividade = (
        atributo_total(atacante, "Precisao", permitir_negativo=True)
        or atributo_total(atacante, "Assertividade", permitir_negativo=True)
        or 100.0
    )
    tipo_ataque = _norm((ataque_spec or {}).get("tipo") or (ataque_spec or {}).get("categoria"))
    if possui_efeito(defensor, "Flutuando") and tipo_ataque in {"normal", "fisico", "físico"}:
        assertividade *= 0.5
    if possui_efeito(defensor, "Voando"):
        assertividade *= 0.5
    chance = max(0.0, min(100.0, assertividade)) / 100.0
    return _rng(contexto).random() <= chance


def _stab(atacante, tipo_ataque: str | None) -> float:
    if not tipo_ataque:
        return 1.0
    tipos = _obter(atacante, "Tipos", _obter(atacante, "tipos", None))
    if tipos is None:
        tipos = _obter(atacante, "Tipo", _obter(atacante, "tipo", None))
    dados = _obter(atacante, "Dados", {})
    if tipos is None and isinstance(dados, dict):
        tipos = dados.get("Tipos", dados.get("tipos", dados.get("Tipo", dados.get("tipo", []))))
    if isinstance(tipos, str):
        tipos = [tipos]
    elif isinstance(tipos, tuple):
        tipos = list(tipos)
    elif not isinstance(tipos, list):
        tipos = []
    tipos_set = {_norm(t) for t in list(tipos or [])}
    return 1.2 if _norm(tipo_ataque) in tipos_set else 1.0


def _multiplicador_amplificacao(entidade) -> float:
    amp = atributo_total(entidade, "Amplificacao", permitir_negativo=True)
    if possui_efeito(entidade, "Enfraquecido"):
        amp -= 50.0
    if possui_efeito(entidade, "Amplificado"):
        amp += 50.0
    return max(0.0, 1.0 + (amp / 100.0))


def _multiplicador_durabilidade(entidade) -> float:
    dur = atributo_total(entidade, "Durabilidade", permitir_negativo=True)
    if possui_efeito(entidade, "Quebrado"):
        dur -= 50.0
    if possui_efeito(entidade, "Fortificado"):
        dur += 50.0
    if possui_efeito(entidade, "Congelado"):
        dur += 30.0
    return 1.0 - (dur / 100.0)


def resolver_critico(atacante, defensor, ataque_spec, contexto=None) -> tuple[bool, float]:
    _ = defensor
    if possui_efeito(atacante, "Cauterizado"):
        return False, 1.0
    crc = atributo_total(atacante, "CrC")
    limite = _fnum((ataque_spec or {}).get("limite_crc", 100.0), 100.0)
    crc = max(0.0, min(crc, limite))
    critou = _rng((contexto or {}).get("contexto_batalha", contexto or {})).random() <= (crc / 100.0)
    crd = atributo_total(atacante, "CrD")
    mult = 1.0 + (crd / 100.0)
    return critou, max(1.0, mult)


def _resultado_vazio(tipo_dano: str, categoria: str, tipo_ataque: str | None) -> ResultadoDano:
    return ResultadoDano(tipo_dano=tipo_dano, categoria=categoria, tipo_ataque=tipo_ataque)


def _aplicar_barreira(resultado: ResultadoDano, defensor) -> None:
    barreira = _fnum(_obter(defensor, "Barreira", _obter(defensor, "barreira", 0.0)), 0.0)
    if barreira > 0.0 and resultado.dano_final > 0.0:
        resultado.bloqueado_por_barreira = True
        resultado.dano_barreira = barreira
        resultado.dano_vida = 0.0
        resultado.logs.append("barreira_bloqueou_instancia")
    else:
        resultado.dano_vida = resultado.dano_final


def calcular_dano_ataque(atacante, defensor, ataque_spec, contexto=None) -> ResultadoDano:
    spec = dict(ataque_spec or {})
    categoria = str(spec.get("categoria") or "normal")
    tipo_ataque = spec.get("tipo") or spec.get("tipo_ataque")
    r = _resultado_vazio("ataque", categoria, str(tipo_ataque) if tipo_ataque else None)

    if possui_efeito(defensor, "Evasivo"):
        r.acertou = False
        r.bloqueado_por_efeito = "evasivo"
        r.logs.append("alvo_evasivo")
        return r

    if not _chance_acerto(atacante, defensor, spec, (contexto or {}).get("contexto_batalha", contexto or {})):
        r.acertou = False
        r.logs.append("erro_por_assertividade")
        return r

    atk = atributo_total(atacante, "Atk") if _norm(categoria) != "especial" else atributo_total(atacante, "SpA")
    poder = _fnum(spec.get("poder", 1.0), 1.0)
    r.dano_base = max(0.0, atk * poder)

    foi_critico, mult_crit = resolver_critico(atacante, defensor, spec, contexto=contexto)
    r.foi_critico = foi_critico
    r.multiplicador_critico = mult_crit

    mult = _multiplicador_amplificacao(atacante) * _stab(atacante, r.tipo_ataque)
    if foi_critico:
        mult *= mult_crit
    r.dano_apos_modificadores = max(0.0, r.dano_base * mult)

    defesa = atributo_total(defensor, "Def") if _norm(categoria) != "especial" else atributo_total(defensor, "SpD")
    r.dano_apos_defesa = max(0.0, r.dano_apos_modificadores - defesa)

    r.dano_apos_durabilidade = max(0.0, r.dano_apos_defesa * _multiplicador_durabilidade(defensor))
    r.dano_final = r.dano_apos_durabilidade
    _aplicar_barreira(r, defensor)
    return r


def calcular_dano_colisao(atacante, defensor, evento_colisao, contexto=None) -> ResultadoDano:
    _ = contexto
    r = _resultado_vazio("colisao", "fisico", None)
    massa = _fnum(_obter(evento_colisao, "massa_objeto", atributo_total(atacante, "Peso")), 1.0)
    vel = _fnum(_obter(evento_colisao, "velocidade_relativa", atributo_total(atacante, "Vel")), 0.0)
    atk = atributo_total(atacante, "Atk")
    aceleracao = _fnum(_obter(atacante, "Aceleracao", 1.0), 1.0)

    bruto = (
        aceleracao * FATOR_DANO_COLISAO
        + massa * FATOR_MASSA_COLISAO
        + vel * FATOR_VELOCIDADE_COLISAO
        + atk * FATOR_ATK_COLISAO
    )
    r.dano_base = max(0.0, bruto)
    r.dano_apos_modificadores = r.dano_base
    r.dano_apos_defesa = max(0.0, r.dano_apos_modificadores - atributo_total(defensor, "Def"))
    r.dano_apos_durabilidade = max(0.0, r.dano_apos_defesa * _multiplicador_durabilidade(defensor))
    r.dano_final = r.dano_apos_durabilidade
    r.foi_critico = False
    r.multiplicador_critico = 1.0
    _aplicar_barreira(r, defensor)
    return r


def calcular_cura(aplicador, alvo, efeito, contexto=None) -> float:
    _ = contexto
    ef = dict(efeito or {})
    valor_fixo = _fnum(ef.get("valor", 0.0), 0.0)
    total = valor_fixo
    for comp in list(ef.get("componentes") or []):
        total += atributo_total(aplicador, str(comp.get("atributo") or "Mag")) * _fnum(comp.get("escala", 0.0), 0.0)
    if possui_efeito(alvo, "Queimado"):
        total *= 0.65
    if possui_efeito(alvo, "Abençoado"):
        total *= 1.35
    return max(0.0, total)


def calcular_dano_por_efeito(atacante, defensor, efeito, ataque_spec=None, contexto=None) -> ResultadoDano:
    ef = dict(efeito or {})
    spec = dict(ataque_spec or {})
    categoria = str(
        ef.get("categoria")
        or ef.get("tipo_dano")
        or spec.get("categoria")
        or "normal"
    )
    tipo_ataque = ef.get("tipo") or ef.get("tipo_ataque") or spec.get("tipo") or spec.get("tipo_ataque")
    r = _resultado_vazio("efeito", categoria, str(tipo_ataque) if tipo_ataque else None)

    if possui_efeito(defensor, "Evasivo"):
        r.acertou = False
        r.bloqueado_por_efeito = "evasivo"
        return r
    if not _chance_acerto(atacante, defensor, {**spec, **ef}, (contexto or {}).get("contexto_batalha", contexto or {})):
        r.acertou = False
        return r

    r.dano_base = _fnum(ef.get("valor", 0.0), 0.0)
    for comp in list(ef.get("componentes") or []):
        atributo_base = str(comp.get("atributo") or ("SpA" if _norm(categoria) == "especial" else "Atk"))
        r.dano_base += atributo_total(atacante, atributo_base, permitir_negativo=True) * _fnum(comp.get("escala", 0.0), 0.0)

    foi_critico, mult_crit = resolver_critico(atacante, defensor, {**spec, **ef}, contexto=contexto)
    r.foi_critico = foi_critico
    r.multiplicador_critico = mult_crit

    mult = _multiplicador_amplificacao(atacante) * _stab(atacante, r.tipo_ataque)
    if foi_critico and bool(ef.get("permite_critico", True)):
        mult *= mult_crit
    r.dano_apos_modificadores = max(0.0, r.dano_base * mult)

    defesa_attr = "SpD" if _norm(categoria) == "especial" else "Def"
    r.dano_apos_defesa = max(0.0, r.dano_apos_modificadores - atributo_total(defensor, defesa_attr, permitir_negativo=True))
    r.dano_apos_durabilidade = max(0.0, r.dano_apos_defesa * _multiplicador_durabilidade(defensor))
    r.dano_final = r.dano_apos_durabilidade
    _aplicar_barreira(r, defensor)
    return r
