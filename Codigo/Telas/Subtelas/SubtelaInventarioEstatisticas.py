from __future__ import annotations

from Codigo.Paineis.PainelEstatisticas import PainelEstatisticas


class InventarioPerfil:
    def __init__(self, ator=None):
        self.Ator = ator
        self._painel_estatisticas = PainelEstatisticas(ator)

    def on_open(self):
        self._painel_estatisticas.on_open()

    def on_close(self):
        self._painel_estatisticas.on_close()

    def renderizar(self, tela, rect, inventario=None, eventos=None, dt=0.0):
        self._painel_estatisticas.Ator = self.Ator
        self._painel_estatisticas.renderizar(tela, rect, inventario=inventario, eventos=eventos, dt=dt)
