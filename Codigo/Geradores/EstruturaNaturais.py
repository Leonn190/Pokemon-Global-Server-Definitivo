"""Estruturas naturais do mundo com drop de recursos por interação."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from Codigo.Modulos.Colisor import Colisor

Vector2 = Tuple[float, float]


# Metadados visuais mínimos no cliente.
# Regras completas (colisão/campo/coleta) são autoritativas no simulador.
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


def tipo_estrutura_natural_por_codigo(codigo: object) -> Optional[Dict[str, object]]:
    try:
        chave = int(codigo)
    except (TypeError, ValueError):
        return None
    dados = ESTRUTURAS_NATURAIS_TIPOS.get(chave)
    return dict(dados) if isinstance(dados, dict) else None


class EstruturaNatural:
    """Estrutura fixa que pode fornecer recursos quando recebe um tapa."""

    def __init__(
        self,
        tipo: str,
        posicao: Vector2 = (0.0, 0.0),
        recursos: Optional[Dict[str, int]] = None,
        raio_colisao: float = 16.0,
        raio_interacao: Optional[float] = 20.0,
        campo: float = 0.0,
        intensidade: float = 0.0,
        hitbox=None,
        id_objeto: Optional[int] = None,
        quantidade: int = 0,
        material: str = "",
        estilo: str = "",
        dureza: int = 1,
    ) -> None:
        self.Id = int(id_objeto or 0)
        self.id_objeto = self.Id
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Campo = float(campo)
        self.Intensidade = float(intensidade)
        self.HitBox = hitbox
        self.Colisor = Colisor(x=self.Posicao[0], y=self.Posicao[1], raio_colisao=float(raio_colisao), raio_interacao=raio_interacao)
        self.Tipo = str(tipo)
        self.Recursos = {nome: max(0, int(qtd)) for nome, qtd in (recursos or {}).items()}
        self.Quantidade = max(0, int(quantidade or 0))
        self.Material = str(material or "")
        self.Estilo = str(estilo or "")
        self.Dureza = max(1, int(dureza or 1))

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def update(self, payload: Dict[str, object]) -> None:
        dados = payload if isinstance(payload, dict) else {}
        pos = dados.get("posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            self.definir_posicao(float(pos[0]), float(pos[1]))
        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        if "quantidade" in estado:
            self.Quantidade = max(0, int(estado.get("quantidade", self.Quantidade) or self.Quantidade))

    def vazio(self) -> bool:
        """Retorna ``True`` quando todos os recursos da estrutura acabaram."""
        return self.Quantidade <= 0 or all(quantidade <= 0 for quantidade in self.Recursos.values())

    def receber_tapa(self, player=None, quantidade: int = 1) -> Dict[str, int]:
        """Entrega recursos ao player e retorna o que foi coletado no tapa."""
        if quantidade <= 0 or not self.Recursos:
            return {}

        coletado = {}
        restante = int(quantidade)
        for nome in sorted(self.Recursos.keys()):
            disponivel = self.Recursos[nome]
            if disponivel <= 0 or restante <= 0:
                continue

            extraido = min(disponivel, restante)
            self.Recursos[nome] -= extraido
            coletado[nome] = extraido
            restante -= extraido

        if player is not None and coletado:
            adicionar = getattr(player, "adicionar_recurso", None)
            if callable(adicionar):
                for recurso, qtd in coletado.items():
                    adicionar(recurso, qtd)

        return coletado

    def ReceberTapa(self, player=None, quantidade: int = 1) -> Dict[str, int]:
        """Alias para manter compatibilidade de convenções antigas."""
        return self.receber_tapa(player=player, quantidade=quantidade)
