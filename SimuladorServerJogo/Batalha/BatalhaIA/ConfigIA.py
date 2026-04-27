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
    "qualidade_decisao",
    "uso_simulacao",
    "gestao_energia",
    "foco_finalizacao",
    "uso_troca",
    "uso_suporte",
    "controle_risco",
    "previsao_ordem",
    "aleatoriedade_controlada",
)

CRITERIOS_PERSONALIDADE = (
    "agressividade",
    "defensividade",
    "preferencia_suporte",
    "preferencia_troca",
    "preferencia_foco_unico",
    "preferencia_area",
    "ousadia",
    "aversao_risco",
)


@dataclass(slots=True)
class CriteriosDificuldade:
    """Criterios de competencia da IA.

    Todos variam de 0.0 a 1.0. Nao existem presets aqui de proposito:
    quem instancia a IA pode ajustar criterio por criterio. Os valores abaixo sao
    apenas o fallback atual para a IA funcionar sem receber configuracao externa.
    """

    qualidade_decisao: float = 0.62
    uso_simulacao: float = 0.32
    gestao_energia: float = 0.58
    foco_finalizacao: float = 0.68
    uso_troca: float = 0.52
    uso_suporte: float = 0.56
    controle_risco: float = 0.60
    previsao_ordem: float = 0.55
    aleatoriedade_controlada: float = 0.62

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
class CriteriosPersonalidade:
    """Criterios de estilo da IA.

    Estes criterios nao sao dificuldade pura. Eles definem como a IA gosta de
    jogar: agressiva, defensiva, suporteira, ousada, etc.
    """

    agressividade: float = 0.58
    defensividade: float = 0.46
    preferencia_suporte: float = 0.46
    preferencia_troca: float = 0.42
    preferencia_foco_unico: float = 0.62
    preferencia_area: float = 0.48
    ousadia: float = 0.48
    aversao_risco: float = 0.55

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
    personalidade: CriteriosPersonalidade = field(default_factory=CriteriosPersonalidade)
    criterio_hacker: float = 0.0
    max_acoes_por_lado: int = 5
    max_acoes_por_pokemon: int = 2
    max_candidatos_por_pokemon: int = 24
    max_candidatos_planejamento: int = 42
    margem_overkill: float = 0.18

    @classmethod
    def from_dict(cls, dados: Mapping[str, Any] | None) -> "ConfigIA":
        if not isinstance(dados, Mapping):
            return cls()

        dificuldade = dados.get("dificuldade") or dados.get("criterios_dificuldade") or {}
        personalidade = dados.get("personalidade") or dados.get("criterios_personalidade") or dados.get("comportamento") or {}
        hacker = dados.get("criterio_hacker", dados.get("hacker", dados.get("leitura_player", 0.0)))

        cfg = cls(
            dificuldade=CriteriosDificuldade.from_dict(dificuldade),
            personalidade=CriteriosPersonalidade.from_dict(personalidade),
            criterio_hacker=clamp01(hacker, 0.0),
        )

        for chave in ("max_acoes_por_lado", "max_acoes_por_pokemon", "max_candidatos_por_pokemon", "max_candidatos_planejamento"):
            if chave in dados:
                try:
                    valor = int(float(dados.get(chave)))
                    setattr(cfg, chave, max(1, valor))
                except (TypeError, ValueError):
                    pass
        if "margem_overkill" in dados:
            cfg.margem_overkill = clamp01(dados.get("margem_overkill"), cfg.margem_overkill)
        return cfg

    def mesclar(self, override: Mapping[str, Any] | None = None) -> "ConfigIA":
        if not isinstance(override, Mapping):
            return self
        dados = self.as_dict()
        for bloco in ("dificuldade", "personalidade"):
            if isinstance(override.get(bloco), Mapping):
                dados.setdefault(bloco, {}).update(override[bloco])
        if "criterios_dificuldade" in override and isinstance(override["criterios_dificuldade"], Mapping):
            dados.setdefault("dificuldade", {}).update(override["criterios_dificuldade"])
        if "criterios_personalidade" in override and isinstance(override["criterios_personalidade"], Mapping):
            dados.setdefault("personalidade", {}).update(override["criterios_personalidade"])
        if "comportamento" in override and isinstance(override["comportamento"], Mapping):
            dados.setdefault("personalidade", {}).update(override["comportamento"])
        for chave in ("criterio_hacker", "hacker", "leitura_player", "max_acoes_por_lado", "max_acoes_por_pokemon", "max_candidatos_por_pokemon", "max_candidatos_planejamento", "margem_overkill"):
            if chave not in override:
                continue
            if chave in {"criterio_hacker", "hacker", "leitura_player"}:
                dados["criterio_hacker"] = override[chave]
            else:
                dados[chave] = override[chave]
        return ConfigIA.from_dict(dados)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dificuldade": self.dificuldade.as_dict(),
            "personalidade": self.personalidade.as_dict(),
            "criterio_hacker": float(self.criterio_hacker),
            "max_acoes_por_lado": int(self.max_acoes_por_lado),
            "max_acoes_por_pokemon": int(self.max_acoes_por_pokemon),
            "max_candidatos_por_pokemon": int(self.max_candidatos_por_pokemon),
            "max_candidatos_planejamento": int(self.max_candidatos_planejamento),
            "margem_overkill": float(self.margem_overkill),
        }

    @property
    def orcamento_simulacoes(self) -> int:
        uso = self.dificuldade.uso_simulacao
        if uso <= 0.02:
            return 0
        # Crescimento quadratico: valores medios nao explodem, valores altos ficam fortes.
        return int(round(6 + 294 * (uso ** 2)))
