"""Perfil simples do player com progressão e marcos."""

from __future__ import annotations


class PlayerPerfil:
    def __init__(self):
        self.NivelMochila = 1
        self.BatalhasPVPVencidas = 0
        self.BatalhasBotVencidas = 0
        self.Ouro = 0
        self.PassosCaminhados = 0
        self.Insignias = []
        self.Maestria = 0
        self.SkinsLiberadas = []

    def adicionar_passos(self, quantidade: int) -> None:
        self.PassosCaminhados += max(0, int(quantidade))

    def serializar(self):
        return {
            "nivel_mochila": self.NivelMochila,
            "batalhas_pvp_vencidas": self.BatalhasPVPVencidas,
            "batalhas_bot_vencidas": self.BatalhasBotVencidas,
            "ouro": self.Ouro,
            "passos_caminhados": self.PassosCaminhados,
            "insignias": list(self.Insignias),
            "maestria": self.Maestria,
            "skins_liberadas": list(self.SkinsLiberadas),
        }
