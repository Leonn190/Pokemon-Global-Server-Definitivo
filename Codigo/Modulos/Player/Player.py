"""Composição final de Player: Ator + Controle + Perfil + Inventário."""

from __future__ import annotations

from Codigo.Modulos.Player.PlayerControle import PlayerController
from Codigo.Modulos.Player.PlayerInventario import PlayerInventario
from Codigo.Modulos.Player.PlayerPerfil import PlayerPerfil


class Player:
    def __init__(self, ator, callback_diff=None, velocidade_tiles=4.8):
        self.Ator = ator
        self.Controle = PlayerController(ator=ator, velocidade_tiles=velocidade_tiles, callback_diff=callback_diff)
        self.Perfil = PlayerPerfil()
        self.Inventario = PlayerInventario()
