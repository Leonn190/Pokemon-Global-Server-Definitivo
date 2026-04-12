from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PosicaoIA:
    x: float
    y: float

    def distancia_ate(self, outra: "PosicaoIA") -> float:
        dx = float(self.x) - float(outra.x)
        dy = float(self.y) - float(outra.y)
        return ((dx * dx) + (dy * dy)) ** 0.5

    def como_lista(self) -> list[float]:
        return [float(self.x), float(self.y)]


@dataclass
class HabilidadeIA:
    nome: str
    chave: str
    estilo: str
    tipo: str = "normal"
    custo_energia: float = 0.0
    alcance: float = 0.0
    raio: float = 0.0
    usa_atributo: str = "Atk"
    efeito_principal: str = "dano"
    alvo_preferencial: str = "inimigo"
    descricao: str = ""
    dados_brutos: Dict[str, object] = field(default_factory=dict)


@dataclass
class CombatenteIA:
    uid: str
    nome: str
    lado: str
    ativo: bool
    fora_de_combate: bool
    posicao: PosicaoIA
    vida_atual: float
    vida_max: float
    energia: float
    energia_max: float
    barreira: float
    tipos: List[str] = field(default_factory=list)
    atributos: Dict[str, float] = field(default_factory=dict)
    efeitos: List[str] = field(default_factory=list)
    flags: Dict[str, bool] = field(default_factory=dict)
    habilidades: List[HabilidadeIA] = field(default_factory=list)

    @property
    def percentual_vida(self) -> float:
        if self.vida_max <= 0:
            return 0.0
        return max(0.0, min(1.0, float(self.vida_atual) / float(self.vida_max)))

    @property
    def percentual_energia(self) -> float:
        if self.energia_max <= 0:
            return 0.0
        return max(0.0, min(1.0, float(self.energia) / float(self.energia_max)))

    def pode_agir(self) -> bool:
        return bool(self.ativo) and not bool(self.fora_de_combate) and bool(self.flags.get("pode_agir", True))


@dataclass
class ArenaIA:
    largura: float = 40.0
    altura: float = 20.0
    centro: PosicaoIA = field(default_factory=lambda: PosicaoIA(20.0, 10.0))
    tiles_bloqueados: List[PosicaoIA] = field(default_factory=list)


@dataclass
class PreparacaoInimigaIA:
    executor_id: str
    acao_chave: str
    confianca: float = 0.0


@dataclass
class EstadoBatalhaIA:
    batalha_id: str
    turno_atual: int
    tick_global: int
    lado_controlado: str
    clima: str = ""
    arena: ArenaIA = field(default_factory=ArenaIA)
    aliados_ativos: List[CombatenteIA] = field(default_factory=list)
    aliados_reserva: List[CombatenteIA] = field(default_factory=list)
    inimigos_ativos: List[CombatenteIA] = field(default_factory=list)
    inimigos_reserva: List[CombatenteIA] = field(default_factory=list)
    preparacoes_inimigas: List[PreparacaoInimigaIA] = field(default_factory=list)
    dificuldade: Dict[str, float] = field(default_factory=dict)

    def buscar_combatente(self, uid: str) -> CombatenteIA | None:
        todos = (
            list(self.aliados_ativos)
            + list(self.aliados_reserva)
            + list(self.inimigos_ativos)
            + list(self.inimigos_reserva)
        )
        for combatente in todos:
            if combatente.uid == str(uid):
                return combatente
        return None


@dataclass
class AcaoCandidata:
    tipo_acao: str
    executor_id: str
    acao_chave: str = ""
    habilidade_nome: str = ""
    estilo: str = ""
    destino_posicao: PosicaoIA | None = None
    alvo_ids: List[str] = field(default_factory=list)
    troca_reserva_id: str = ""
    custo_energia: float = 0.0
    prioridade: float = 0.0
    tags: List[str] = field(default_factory=list)
    dados_extras: Dict[str, object] = field(default_factory=dict)
    habilidade_bruta: Dict[str, object] = field(default_factory=dict)


@dataclass
class ResultadoAvaliacaoIA:
    acao: AcaoCandidata
    score: float
    componentes: Dict[str, float] = field(default_factory=dict)
    motivos: List[str] = field(default_factory=list)
