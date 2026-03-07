"""Estruturas naturais do mundo com drop de recursos por interação."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from Codigo.Geradores.Estrutura import Estrutura

Vector2 = Tuple[float, float]


ESTRUTURAS_NATURAIS_TIPOS: Dict[int, Dict[str, object]] = {
    1: {
        "subtipo": "arvore",
        "nome": "Árvore",
        "sprite": "Recursos/Visual/Mundo/Objetos/Arvore.png",
        "raio_colisao": 0.75,
        "raio_interacao": 0.75,
        "campo": 0.70,
        "intensidade": 3,
    },
    2: {
        "subtipo": "pedra",
        "nome": "Pedra",
        "sprite": "Recursos/Visual/Mundo/Objetos/Pedra.png",
        "raio_colisao": 1,
        "raio_interacao": 0.7,
        "campo": 0.75,
        "intensidade": 3.5,
    },
    3: {
        "subtipo": "arbusto",
        "nome": "Arbusto",
        "sprite": "Recursos/Visual/Mundo/Objetos/Arbusto.png",
        "raio_colisao": 0.5,
        "raio_interacao": 0.55,
        "campo": 0.4,
        "intensidade": 2.3,
    },
}


def tipo_estrutura_natural_por_codigo(codigo: object) -> Optional[Dict[str, object]]:
    try:
        chave = int(codigo)
    except (TypeError, ValueError):
        return None
    dados = ESTRUTURAS_NATURAIS_TIPOS.get(chave)
    return dict(dados) if isinstance(dados, dict) else None


class EstruturaNatural(Estrutura):
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
    ) -> None:
        super().__init__(
            posicao=posicao,
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
            campo=campo,
            intensidade=intensidade,
            hitbox=hitbox,
            id_objeto=id_objeto,
        )
        self.Tipo = str(tipo)
        self.Recursos = {nome: max(0, int(qtd)) for nome, qtd in (recursos or {}).items()}

    def vazio(self) -> bool:
        """Retorna ``True`` quando todos os recursos da estrutura acabaram."""
        return all(quantidade <= 0 for quantidade in self.Recursos.values())

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
