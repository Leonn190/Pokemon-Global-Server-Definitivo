from __future__ import annotations

from typing import Dict

from Codigo.ModulosBatalha.Arena import Arena


class ControladorBatalha:
    def __init__(self, contexto: Dict[str, object]):
        self.Contexto = dict(contexto or {})
        self.Arena = Arena(self.Contexto)

    def atualizar(self, eventos, dt: float) -> None:
        return

    def renderizar(self, tela, camera) -> None:
        self.Arena.renderizar(tela, camera)
