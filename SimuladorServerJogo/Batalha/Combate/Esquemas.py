from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PreparoSpec:
    tipo: str = ""
    indicador: str = ""
    alcance: float | None = None
    largura: float | None = None
    raio: float | None = None
    angulo: float | None = None
    intensidade_min: float | None = None
    intensidade_max: float | None = None
    dados: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecucaoSpec:
    forma: str = ""
    alcance: float | None = None
    largura: float | None = None
    raio: float | None = None
    angulo: float | None = None
    velocidade_pct: float | None = None
    velocidade_tiles_tick: float | None = None
    desaceleracao: float | None = None
    ricochetes_paredes: int | None = None
    ricochetes_pokemons: int | None = None
    atravessa_pokemons: bool | None = None
    atravessa_paredes: bool | None = None
    atinge: str = ""
    instantaneo: bool | None = None
    dados: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ComponenteDanoSpec:
    atributo: str = ""
    escala: float = 0.0
    categoria: str = ""


@dataclass(slots=True)
class EfeitoSpec:
    tipo: str = ""
    alvo: str = ""
    valor: float | int | None = None
    status: str = ""
    atributo: str = ""
    componentes: list[ComponenteDanoSpec] = field(default_factory=list)
    condicao: dict[str, Any] = field(default_factory=dict)
    dados: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AtaqueCombateSpec:
    id: str = ""
    nome: str = ""
    preparo: PreparoSpec = field(default_factory=PreparoSpec)
    execucao: ExecucaoSpec = field(default_factory=ExecucaoSpec)
    efeitos_ao_acertar: list[EfeitoSpec] = field(default_factory=list)
    efeitos_ao_falhar: list[EfeitoSpec] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    bruto: dict[str, Any] = field(default_factory=dict)
