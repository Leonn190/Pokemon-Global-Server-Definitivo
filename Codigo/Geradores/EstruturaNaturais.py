"""Estruturas naturais do mundo (cliente visual)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from Codigo.Modulos.Colisor import Colisor

Vector2 = Tuple[float, float]


ESTRUTURAS_NATURAIS_TIPOS: Dict[int, Dict[str, object]] = {
    1: {"subtipo": "arvore", "nome": "Árvore", "sprite": "Recursos/Visual/Mundo/Objetos/Arvore.png"},
    2: {"subtipo": "pedra", "nome": "Pedra", "sprite": "Recursos/Visual/Mundo/Objetos/Pedra.png"},
    3: {"subtipo": "arbusto", "nome": "Arbusto", "sprite": "Recursos/Visual/Mundo/Objetos/Arbusto.png"},
    4: {"subtipo": "ouro", "nome": "Ouro", "sprite": "Recursos/Visual/Mundo/Objetos/Ouro.png"},
    5: {"subtipo": "ametista", "nome": "Ametista", "sprite": "Recursos/Visual/Mundo/Objetos/Ametista.png"},
    6: {"subtipo": "diamante", "nome": "Diamante", "sprite": "Recursos/Visual/Mundo/Objetos/Diamante.png"},
    7: {"subtipo": "rubi", "nome": "Rubi", "sprite": "Recursos/Visual/Mundo/Objetos/Rubi.png"},
    8: {"subtipo": "esmeralda", "nome": "Esmeralda", "sprite": "Recursos/Visual/Mundo/Objetos/Esmeralda.png"},
    9: {"subtipo": "palmeira", "nome": "Palmeira", "sprite": "Recursos/Visual/Mundo/Objetos/Palmeira.png"},
    10: {"subtipo": "pinheiro", "nome": "Pinheiro", "sprite": "Recursos/Visual/Mundo/Objetos/Pinheiro.png"},
    11: {"subtipo": "cobre", "nome": "Cobre", "sprite": "Recursos/Visual/Mundo/Objetos/Cobre.png"},
    12: {"subtipo": "lava", "nome": "Lava", "sprite": "Recursos/Visual/Mundo/Objetos/Lava.png"},
}

ORDEM_CANONICA_ESTRUTURAS_NATURAIS: Tuple[str, ...] = (
    "lava", "pedra", "cobre", "ouro", "diamante", "ametista", "rubi", "esmeralda", "pinheiro", "palmeira", "arvore", "arbusto",
)
_PRIORIDADE_SUBTIPO: Dict[str, int] = {nome: idx for idx, nome in enumerate(ORDEM_CANONICA_ESTRUTURAS_NATURAIS)}


def tipo_estrutura_natural_por_codigo(codigo: object) -> Optional[Dict[str, object]]:
    try:
        chave = int(codigo)
    except (TypeError, ValueError):
        return None
    dados = ESTRUTURAS_NATURAIS_TIPOS.get(chave)
    return dict(dados) if isinstance(dados, dict) else None


def prioridade_estrutura_natural(codigo: object = None, subtipo: object = None) -> int:
    nome = str(subtipo or "").strip().lower()
    if not nome:
        cfg = tipo_estrutura_natural_por_codigo(codigo)
        nome = str(cfg.get("subtipo", "")).strip().lower() if isinstance(cfg, dict) else ""
    return int(_PRIORIDADE_SUBTIPO.get(nome, len(_PRIORIDADE_SUBTIPO)))


class EstruturaNatural:
    def __init__(self, tipo: str, posicao: Vector2 = (0.0, 0.0), raio_colisao: float = 16.0, raio_interacao: Optional[float] = 20.0, campo: float = 0.0, intensidade: float = 0.0, id_objeto: Optional[int] = None, quantidade: int = 0, material: str = "", estilo: str = "", dureza: int = 1) -> None:
        self.Id = int(id_objeto or 0)
        self.id_objeto = self.Id
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Campo = float(campo)
        self.Intensidade = float(intensidade)
        self.Colisor = Colisor(x=self.Posicao[0], y=self.Posicao[1], raio_colisao=float(raio_colisao), raio_interacao=raio_interacao)
        self.Tipo = str(tipo)
        self.Quantidade = max(0, int(quantidade or 0))
        self.Material = str(material or "")
        self.Estilo = str(estilo or "")
        self.Dureza = max(1, int(dureza or 1))
        self._impacto_t = 0.0
        self._escala_impacto = 1.0

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def vazio(self) -> bool:
        return self.Quantidade <= 0

    def escala_render(self, dt: float = 0.0) -> float:
        dt = max(0.0, float(dt))
        if self._impacto_t > 0.0:
            self._impacto_t = max(0.0, self._impacto_t - dt)
            alvo = 1.0 if self._impacto_t <= 0.0 else 0.92
            self._escala_impacto += (alvo - self._escala_impacto) * min(1.0, dt * 18.0)
        else:
            self._escala_impacto += (1.0 - self._escala_impacto) * min(1.0, dt * 12.0)
        return self._escala_impacto

    def update(self, payload: Dict[str, object]) -> None:
        dados = payload if isinstance(payload, dict) else {}
        pos = dados.get("posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            self.definir_posicao(float(pos[0]), float(pos[1]))
        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        if "quantidade" in estado:
            anterior = int(self.Quantidade)
            self.Quantidade = max(0, int(estado.get("quantidade", self.Quantidade)))
            if self.Quantidade < anterior:
                self._impacto_t = 0.12


class EstruturaNaturalFake:
    """Estrutura visual simplificada para cenários de batalha."""

    def __init__(self, posicao: Vector2, sprite: str = "", codigo_natural: int = 0) -> None:
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Sprite = str(sprite or "")
        self.CodigoNatural = int(codigo_natural or 0)
