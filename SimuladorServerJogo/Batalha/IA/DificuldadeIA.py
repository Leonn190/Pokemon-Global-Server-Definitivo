from __future__ import annotations

import random
from typing import Dict, Mapping


FATORES_PADRAO: Dict[str, float] = {
    "considerar_tipo_dano": 0.0,
    "considerar_defesa_correta": 0.0,
    "considerar_fraqueza_resistencia": 0.0,
    "considerar_passivas_habilidade": 0.0,
    "considerar_posicionamento": 0.0,
    "considerar_area": 0.0,
    "considerar_risco": 0.0,
    "considerar_kill": 0.0,
    "considerar_protecao": 0.0,
    "considerar_previsao_inimiga": 0.0,
    "permitir_leitura_preparacao_inimiga": 0.0,
    "permitir_contrajogada_hack": 0.0,
}


DIFICULDADES_BASE: Dict[str, Dict[str, float]] = {
    "impulsiva": {
        **FATORES_PADRAO,
        "considerar_tipo_dano": 0.25,
        "considerar_defesa_correta": 0.15,
        "considerar_fraqueza_resistencia": 0.2,
        "considerar_posicionamento": 0.15,
        "considerar_area": 0.1,
        "considerar_risco": 0.1,
        "considerar_kill": 0.45,
        "considerar_protecao": 0.1,
    },
    "equilibrada": {
        **FATORES_PADRAO,
        "considerar_tipo_dano": 0.55,
        "considerar_defesa_correta": 0.55,
        "considerar_fraqueza_resistencia": 0.55,
        "considerar_passivas_habilidade": 0.2,
        "considerar_posicionamento": 0.45,
        "considerar_area": 0.35,
        "considerar_risco": 0.35,
        "considerar_kill": 0.65,
        "considerar_protecao": 0.35,
    },
    "tatica": {
        **FATORES_PADRAO,
        "considerar_tipo_dano": 0.8,
        "considerar_defesa_correta": 0.85,
        "considerar_fraqueza_resistencia": 0.85,
        "considerar_passivas_habilidade": 0.45,
        "considerar_posicionamento": 0.75,
        "considerar_area": 0.65,
        "considerar_risco": 0.7,
        "considerar_kill": 0.85,
        "considerar_protecao": 0.65,
        "considerar_previsao_inimiga": 0.25,
        "permitir_leitura_preparacao_inimiga": 0.2,
    },
    "trapaceira": {
        **FATORES_PADRAO,
        "considerar_tipo_dano": 0.9,
        "considerar_defesa_correta": 0.9,
        "considerar_fraqueza_resistencia": 0.9,
        "considerar_passivas_habilidade": 0.6,
        "considerar_posicionamento": 0.8,
        "considerar_area": 0.75,
        "considerar_risco": 0.8,
        "considerar_kill": 0.95,
        "considerar_protecao": 0.7,
        "considerar_previsao_inimiga": 0.7,
        "permitir_leitura_preparacao_inimiga": 0.75,
        "permitir_contrajogada_hack": 0.9,
    },
}


def _clamp(valor: object, padrao: float = 0.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = float(padrao)
    return max(0.0, min(1.0, numero))


def normalizar_dificuldade(fatores: Mapping[str, object] | None = None) -> Dict[str, float]:
    base = dict(FATORES_PADRAO)
    for chave, valor in dict(fatores or {}).items():
        base[str(chave)] = _clamp(valor)
    for chave in list(FATORES_PADRAO):
        base[chave] = _clamp(base.get(chave, 0.0))
    return base


def obter_dificuldade_base(nome: str) -> Dict[str, float]:
    return normalizar_dificuldade(DIFICULDADES_BASE.get(str(nome or "").strip().casefold(), FATORES_PADRAO))


def mesclar_dificuldade(base: Mapping[str, object] | None = None, sobrescritas: Mapping[str, object] | None = None) -> Dict[str, float]:
    fatores = normalizar_dificuldade(base)
    for chave, valor in dict(sobrescritas or {}).items():
        fatores[str(chave)] = _clamp(valor, fatores.get(str(chave), 0.0))
    return normalizar_dificuldade(fatores)


def sortear_dificuldade(rng: random.Random | None = None) -> tuple[str, Dict[str, float]]:
    gerador = rng if isinstance(rng, random.Random) else random.Random()
    nomes = list(DIFICULDADES_BASE)
    nome = nomes[gerador.randrange(0, len(nomes))]
    return nome, obter_dificuldade_base(nome)
