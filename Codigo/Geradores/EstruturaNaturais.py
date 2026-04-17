"""Estruturas naturais do mundo (cliente visual)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from Codigo.ModulosGerais.Colisor import Colisor

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
    13: {"subtipo": "cacto", "nome": "Cacto", "sprite": "Recursos/Visual/Mundo/Objetos/Cacto.png"},
    14: {"subtipo": "concha", "nome": "Concha", "sprite": "Recursos/Visual/Mundo/Objetos/Concha.png"},
    15: {"subtipo": "aquamarine", "nome": "Aquamarine", "sprite": "Recursos/Visual/Mundo/Objetos/Aquamarine.png"},
    16: {"subtipo": "carvao", "nome": "Carvão", "sprite": "Recursos/Visual/Mundo/Objetos/Carvão.png"},
    17: {"subtipo": "ferro", "nome": "Ferro", "sprite": "Recursos/Visual/Mundo/Objetos/Ferro.png"},
    18: {"subtipo": "flor", "nome": "Flor", "sprite": "Recursos/Visual/Mundo/Objetos/Flor.png"},
    19: {"subtipo": "jade", "nome": "Jade", "sprite": "Recursos/Visual/Mundo/Objetos/Jade.png"},
    20: {"subtipo": "planta", "nome": "Planta", "sprite": "Recursos/Visual/Mundo/Objetos/Planta.png"},
    21: {"subtipo": "safira", "nome": "Safira", "sprite": "Recursos/Visual/Mundo/Objetos/Safira.png"},
    22: {"subtipo": "topazio", "nome": "Topázio", "sprite": "Recursos/Visual/Mundo/Objetos/Topazio.png"},
    23: {"subtipo": "arvore_trombosa", "nome": "Árvore Trombosa", "sprite": "Recursos/Visual/Mundo/Objetos/ArvoreTrombosa.png"},
}

ORDEM_CANONICA_ESTRUTURAS_NATURAIS: Tuple[str, ...] = (
    "lava", "pedra", "cobre", "ferro", "carvao", "ouro", "diamante", "ametista", "rubi", "esmeralda", "safira", "topazio", "aquamarine", "jade", "concha", "pinheiro", "palmeira", "cacto", "arvore_trombosa", "arvore", "planta", "flor", "arbusto",
)
_PRIORIDADE_SUBTIPO: Dict[str, int] = {nome: idx for idx, nome in enumerate(ORDEM_CANONICA_ESTRUTURAS_NATURAIS)}


_LIMITE_ESCALA_ESTRUTURA_MIN = 0.90
_LIMITE_ESCALA_ESTRUTURA_MAX = 1.10


def definir_limites_escala_estrutura_natural(minimo: object, maximo: object) -> None:
    global _LIMITE_ESCALA_ESTRUTURA_MIN, _LIMITE_ESCALA_ESTRUTURA_MAX
    try:
        min_val = float(minimo)
    except (TypeError, ValueError):
        min_val = 0.90
    try:
        max_val = float(maximo)
    except (TypeError, ValueError):
        max_val = 1.10
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    _LIMITE_ESCALA_ESTRUTURA_MIN = max(0.1, min_val)
    _LIMITE_ESCALA_ESTRUTURA_MAX = max(_LIMITE_ESCALA_ESTRUTURA_MIN, max_val)


def limites_escala_estrutura_natural() -> Tuple[float, float]:
    minimo = float(_LIMITE_ESCALA_ESTRUTURA_MIN)
    maximo = float(_LIMITE_ESCALA_ESTRUTURA_MAX)
    if minimo > maximo:
        minimo, maximo = maximo, minimo
    return (max(0.1, minimo), max(minimo, maximo))


def limitar_escala_estrutura_natural(valor: object) -> float:
    minimo, maximo = limites_escala_estrutura_natural()
    try:
        escala = float(valor)
    except (TypeError, ValueError):
        return float(minimo)
    return max(minimo, min(maximo, escala))


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
        self._escala_base = 1.0
        self._escala_render_atual = 1.0

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def vazio(self) -> bool:
        return self.Quantidade <= 0

    def atualizar_visual(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        if self._impacto_t > 0.0:
            self._impacto_t = max(0.0, self._impacto_t - dt)
            alvo = 1.0 if self._impacto_t <= 0.0 else 0.92
            self._escala_impacto += (alvo - self._escala_impacto) * min(1.0, dt * 18.0)
        else:
            self._escala_impacto += (1.0 - self._escala_impacto) * min(1.0, dt * 12.0)
        self._escala_render_atual = float(self._escala_base * self._escala_impacto)

    def escala_render(self, dt: float = 0.0) -> float:
        if dt > 0.0:
            self.atualizar_visual(dt)
        return float(self._escala_render_atual)

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
        if "escala_mundo" in estado:
            self._escala_base = limitar_escala_estrutura_natural(estado.get("escala_mundo", 1.0))


class EstruturaNaturalFake:
    """Estrutura visual simplificada para cenários de batalha."""

    def __init__(self, posicao: Vector2, sprite: str = "", codigo_natural: int = 0) -> None:
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Sprite = str(sprite or "")
        self.CodigoNatural = int(codigo_natural or 0)
