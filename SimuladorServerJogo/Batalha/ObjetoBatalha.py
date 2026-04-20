from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


Vec2 = Tuple[float, float]


@dataclass
class ObjetoBatalha:
    Id: str
    Tipo: str
    Subtipo: str
    DonoId: str = ""
    Lado: str = ""
    Ataque: Dict[str, object] = field(default_factory=dict)
    Fluxo: Dict[str, object] = field(default_factory=dict)
    Posicao: Vec2 = (0.0, 0.0)
    PosicaoAnterior: Vec2 = (0.0, 0.0)
    Direcao: Vec2 = (1.0, 0.0)
    VelocidadeTilesTick: float = 0.0
    VelocidadeAtualTilesTick: float = 0.0
    AceleracaoTilesTick2: float = 0.0
    Raio: float = 0.25
    DiametroProjetil: float = 0.5
    InicioTick: int = 0
    TickAtual: int = 0
    DuracaoTicks: int = 0
    RicochetesRestantes: int = 0
    AtravessadasRestantes: int = 0
    AtravessaObjetos: bool = False
    AtravessaPokemons: bool = False
    RicocheteiaObjetos: bool = False
    RicocheteiaPokemons: bool = False
    AtingeSiMesmo: bool = False
    IntensidadeDano: float = 1.0
    MultiplicadorDanoAtual: float = 1.0
    MultiplicadorDanoPorRicochet: float = 1.0
    MultiplicadorDanoPorAtravessada: float = 1.0
    MultiplicadorDanoPorTileMovido: float = 1.0
    AumentoAlcancePorRicochet: float = 0.0
    AumentoAlcancePorAtravessada: float = 0.0
    DistanciaPercorrida: float = 0.0
    AlcanceRestante: float = 0.0
    TipoFluxo: str = ""
    Subfluxos: List[Dict[str, object]] = field(default_factory=list)
    Ativo: bool = True
    AlvosAtingidos: set[str] = field(default_factory=set)
    DadosExtras: Dict[str, object] = field(default_factory=dict)
    HistoricoPosicoes: List[Vec2] = field(default_factory=list)

    def avancar_tick(self) -> None:
        self.TickAtual = int(self.TickAtual) + 1
        self.PosicaoAnterior = (float(self.Posicao[0]), float(self.Posicao[1]))
        self.HistoricoPosicoes.append(self.PosicaoAnterior)

    def serializar(self) -> Dict[str, object]:
        return {
            "id": str(self.Id),
            "tipo": str(self.Tipo),
            "subtipo": str(self.Subtipo),
            "dono_id": str(self.DonoId),
            "lado": str(self.Lado),
            "posicao": [float(self.Posicao[0]), float(self.Posicao[1])],
            "posicao_anterior": [float(self.PosicaoAnterior[0]), float(self.PosicaoAnterior[1])],
            "direcao": [float(self.Direcao[0]), float(self.Direcao[1])],
            "velocidade_tiles_tick": float(self.VelocidadeTilesTick),
            "velocidade_atual_tiles_tick": float(self.VelocidadeAtualTilesTick or self.VelocidadeTilesTick),
            "aceleracao_tiles_tick2": float(self.AceleracaoTilesTick2),
            "raio": float(self.Raio),
            "diametro_projetil": float(self.DiametroProjetil),
            "inicio_tick": int(self.InicioTick),
            "tick_atual": int(self.TickAtual),
            "duracao_ticks": int(self.DuracaoTicks),
            "ricochetes_restantes": int(self.RicochetesRestantes),
            "atravessadas_restantes": int(self.AtravessadasRestantes),
            "atravessa_objetos": bool(self.AtravessaObjetos),
            "atravessa_pokemons": bool(self.AtravessaPokemons),
            "ricocheteia_objetos": bool(self.RicocheteiaObjetos),
            "ricocheteia_pokemons": bool(self.RicocheteiaPokemons),
            "atinge_si_mesmo": bool(self.AtingeSiMesmo),
            "intensidade_dano": float(self.IntensidadeDano),
            "multiplicador_dano_atual": float(self.MultiplicadorDanoAtual),
            "multiplicador_dano_por_ricochet": float(self.MultiplicadorDanoPorRicochet),
            "multiplicador_dano_por_atravessada": float(self.MultiplicadorDanoPorAtravessada),
            "multiplicador_dano_por_tile_movido": float(self.MultiplicadorDanoPorTileMovido),
            "aumento_alcance_por_ricochet": float(self.AumentoAlcancePorRicochet),
            "aumento_alcance_por_atravessada": float(self.AumentoAlcancePorAtravessada),
            "distancia_percorrida": float(self.DistanciaPercorrida),
            "alcance_restante": float(self.AlcanceRestante),
            "tipo_fluxo": str(self.TipoFluxo or self.Subtipo),
            "subfluxos": [dict(item) for item in list(self.Subfluxos or []) if isinstance(item, dict)],
            "ativo": bool(self.Ativo),
            "dados_extras": dict(self.DadosExtras),
        }
