"""Composição final de Player: Ator + Controle + Perfil + Inventário."""

from __future__ import annotations

from Codigo.Modulos.Player.PlayerControle import PlayerController
from Codigo.Modulos.Player.PlayerInventario import PlayerInventario
from Codigo.Modulos.Player.PlayerPerfil import PlayerPerfil
from Codigo.Modulos.Player.ElementosHud import ElementosHud


class Player:
    def __init__(self, ator, callback_diff=None, velocidade_tiles=4.8):
        self.Ator = ator
        self.Perfil = PlayerPerfil()
        self.Inventario = PlayerInventario(limite_itens=32)
        self.Controle = PlayerController(
            ator=ator,
            perfil=self.Perfil,
            inventario=self.Inventario,
            velocidade_tiles=velocidade_tiles,
            callback_diff=callback_diff,
        )
        self.Hud = ElementosHud()
