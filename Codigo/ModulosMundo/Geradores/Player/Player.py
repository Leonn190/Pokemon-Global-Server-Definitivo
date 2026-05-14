"""Compatibilidade de player local: wrapper mínimo do ator."""

from __future__ import annotations


class Player:
    def __init__(self, ator, velocidade_tiles=None):
        self.Ator = ator
        self.Perfil = ator.Perfil
        self.Inventario = ator.Inventario
        self.Controle = ator.Controle
