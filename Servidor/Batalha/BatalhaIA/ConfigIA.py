from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


def clamp01(valor: Any, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            valor = valor.replace(",", ".")
        numero = float(valor)
    except (TypeError, ValueError):
        numero = float(default)
    return max(0.0, min(1.0, numero))


CRITERIOS_DIFICULDADE = (
    "inteligencia",
    "conhecimento",
    "raciocinio",
    "micro_simulacoes",
    "macro_simulacoes",
    "previsao",
    "tatica",
    "memoria",
    "profissionalismo",
)

CRITERIOS_HACKER = (
    "intuicao",
    "leitura",
    "manipulacao",
)

CRITERIOS_PERSONALIDADE = (
    "agressividade",
    "cautela",
    "suporte",
    "troca",
    "foco",
    "area",
    "ousadia",
)


@dataclass(slots=True)
class CriteriosDificuldade:
    inteligencia: float = 0.60
    conhecimento: float = 0.55
    raciocinio: float = 0.60
    micro_simulacoes: float = 0.35
    macro_simulacoes: float = 0.20
    previsao: float = 0.45
    tatica: float = 0.15
    memoria: float = 0.25
    profissionalismo: float = 0.70

    @classmethod
    def from_dict(cls, dados: Mapping[str, Any] | None) -> "CriteriosDificuldade":
        base = cls()
        if not isinstance(dados, Mapping):
            return base
        for chave in CRITERIOS_DIFICULDADE:
            if chave in dados:
                setattr(base, chave, clamp01(dados.get(chave), getattr(base, chave)))
        return base

    def as_dict(self) -> dict[str, float]:
        return {chave: float(getattr(self, chave)) for chave in CRITERIOS_DIFICULDADE}


@dataclass(slots=True)
class CriteriosHacker:
    intuicao: float = 0.0
    leitura: float = 0.0
    manipulacao: float = 0.0

    @classmethod
    def from_dict(cls, dados: Mapping[str, Any] | None) -> "CriteriosHacker":
        base = cls()
        if not isinstance(dados, Mapping):
            return base
        for chave in CRITERIOS_HACKER:
            if chave in dados:
                setattr(base, chave, clamp01(dados.get(chave), getattr(base, chave)))
        return base

    def as_dict(self) -> dict[str, float]:
        return {chave: float(getattr(self, chave)) for chave in CRITERIOS_HACKER}


@dataclass(slots=True)
class CriteriosPersonalidade:
    agressividade: float = 0.50
    cautela: float = 0.50
    suporte: float = 0.45
    troca: float = 0.35
    foco: float = 0.55
    area: float = 0.40
    ousadia: float = 0.35

    @classmethod
    def from_dict(cls, dados: Mapping[str, Any] | None) -> "CriteriosPersonalidade":
        base = cls()
        if not isinstance(dados, Mapping):
            return base
        for chave in CRITERIOS_PERSONALIDADE:
            if chave in dados:
                setattr(base, chave, clamp01(dados.get(chave), getattr(base, chave)))
        return base

    def as_dict(self) -> dict[str, float]:
        return {chave: float(getattr(self, chave)) for chave in CRITERIOS_PERSONALIDADE}


@dataclass(slots=True)
class ConfigIA:
    dificuldade: CriteriosDificuldade = field(default_factory=CriteriosDificuldade)
    hacker: CriteriosHacker = field(default_factory=CriteriosHacker)
    personalidade: CriteriosPersonalidade = field(default_factory=CriteriosPersonalidade)

    max_acoes_por_lado: int = 5
    max_acoes_por_pokemon: int = 2
    max_candidatos_por_pokemon: int = 24
    max_candidatos_planejamento: int = 42
    margem_overkill: float = 0.18

    @classmethod
    def padrao(cls) -> "ConfigIA":
        return cls()

    @classmethod
    def from_dict(cls, dados: Mapping[str, Any] | None) -> "ConfigIA":
        if not isinstance(dados, Mapping):
            return cls()

        dificuldade = dados.get("dificuldade") or dados.get("criterios_dificuldade") or {}
        hacker = dados.get("hacker") or dados.get("criterios_hacker") or {}
        personalidade = dados.get("personalidade") or dados.get("criterios_personalidade") or {}

        dificuldade_composta = dict(dificuldade) if isinstance(dificuldade, Mapping) else {}
        hacker_composto = dict(hacker) if isinstance(hacker, Mapping) else {}
        personalidade_composta = dict(personalidade) if isinstance(personalidade, Mapping) else {}
        for chave in CRITERIOS_DIFICULDADE:
            if chave in dados:
                dificuldade_composta[chave] = dados[chave]
        for chave in CRITERIOS_HACKER:
            if chave in dados:
                hacker_composto[chave] = dados[chave]
        for chave in CRITERIOS_PERSONALIDADE:
            if chave in dados:
                personalidade_composta[chave] = dados[chave]

        cfg = cls(
            dificuldade=CriteriosDificuldade.from_dict(dificuldade_composta),
            hacker=CriteriosHacker.from_dict(hacker_composto),
            personalidade=CriteriosPersonalidade.from_dict(personalidade_composta),
        )

        for chave in ("max_acoes_por_lado", "max_acoes_por_pokemon", "max_candidatos_por_pokemon", "max_candidatos_planejamento"):
            if chave in dados:
                try:
                    setattr(cfg, chave, max(1, int(float(dados.get(chave)))))
                except (TypeError, ValueError):
                    pass
        if "margem_overkill" in dados:
            cfg.margem_overkill = clamp01(dados.get("margem_overkill"), cfg.margem_overkill)
        return cfg

    def mesclar(self, override: Mapping[str, Any] | None = None, *, permitir_override: bool = False) -> "ConfigIA":
        if not permitir_override or not isinstance(override, Mapping):
            return self
        dados = self.as_dict()
        for bloco in ("dificuldade", "hacker", "personalidade"):
            if isinstance(override.get(bloco), Mapping):
                dados.setdefault(bloco, {}).update(override[bloco])
        if "criterios_dificuldade" in override and isinstance(override["criterios_dificuldade"], Mapping):
            dados.setdefault("dificuldade", {}).update(override["criterios_dificuldade"])
        if "criterios_hacker" in override and isinstance(override["criterios_hacker"], Mapping):
            dados.setdefault("hacker", {}).update(override["criterios_hacker"])
        if "criterios_personalidade" in override and isinstance(override["criterios_personalidade"], Mapping):
            dados.setdefault("personalidade", {}).update(override["criterios_personalidade"])
        return ConfigIA.from_dict(dados)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dificuldade": self.dificuldade.as_dict(),
            "hacker": self.hacker.as_dict(),
            "personalidade": self.personalidade.as_dict(),
            "max_acoes_por_lado": int(self.max_acoes_por_lado),
            "max_acoes_por_pokemon": int(self.max_acoes_por_pokemon),
            "max_candidatos_por_pokemon": int(self.max_candidatos_por_pokemon),
            "max_candidatos_planejamento": int(self.max_candidatos_planejamento),
            "margem_overkill": float(self.margem_overkill),
        }

    @property
    def orcamento_micro_simulacoes(self) -> int:
        uso = self.dificuldade.micro_simulacoes
        if uso <= 0.02:
            return 0
        return int(round(4 + 36 * (uso ** 2)))

    @property
    def orcamento_macro_simulacoes(self) -> int:
        uso = self.dificuldade.macro_simulacoes
        if uso <= 0.02:
            return 0
        return int(round(4 + 96 * (uso ** 2)))

    @property
    def orcamento_tatica(self) -> int:
        uso = self.dificuldade.tatica
        if uso <= 0.02:
            return 0
        return int(round(2 + 32 * (uso ** 2)))

    @property
    def orcamento_hacker(self) -> int:
        uso = self.hacker.manipulacao
        if uso <= 0.02:
            return 0
        return int(round(2 + 80 * (uso ** 2)))
