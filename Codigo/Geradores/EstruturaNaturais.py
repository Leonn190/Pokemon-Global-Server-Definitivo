"""Estruturas naturais do mundo com drop de recursos por interação."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from Codigo.Geradores.Estrutura import Estrutura

Vector2 = Tuple[float, float]


from Codigo.Modulos.ConfigEstruturasNaturais import (
    ESTRUTURAS_NATURAIS_TIPOS,
    tipo_estrutura_natural_por_codigo,
)


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
