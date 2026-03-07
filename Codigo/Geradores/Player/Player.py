"""Composição final de Player: Ator + Controle + Perfil + Inventário."""

from __future__ import annotations

from Codigo.Geradores.Player.PlayerControle import PlayerController
from Codigo.Geradores.Player.PlayerInventario import PlayerInventario
from Codigo.Geradores.Player.PlayerPerfil import PlayerPerfil
from Codigo.Modulos.ElementosHud import ElementosHud


class Player:
    def __init__(self, ator, velocidade_tiles=4.8):
        self.Ator = ator
        self.Perfil = PlayerPerfil()
        self.Inventario = PlayerInventario(limite_itens=32)
        self.Controle = PlayerController(
            ator=ator,
            perfil=self.Perfil,
            inventario=self.Inventario,
            velocidade_tiles=velocidade_tiles,
        )
        self.Hud = ElementosHud()
