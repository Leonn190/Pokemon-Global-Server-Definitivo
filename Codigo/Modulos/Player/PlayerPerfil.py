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
        self.StaminaMax = 100.0
        self.Stamina = 100.0

    def adicionar_passos(self, quantidade: int) -> None:
        self.PassosCaminhados += max(0, int(quantidade))

    def consumir_stamina(self, quantidade: float) -> float:
        valor = max(0.0, float(quantidade))
        self.Stamina = max(0.0, self.Stamina - valor)
        return self.Stamina

    def regenerar_stamina(self, quantidade: float) -> float:
        valor = max(0.0, float(quantidade))
        self.Stamina = min(self.StaminaMax, self.Stamina + valor)
        return self.Stamina

    def aplicar_serializado(self, dados):
        if not isinstance(dados, dict):
            return
        self.NivelMochila = int(dados.get("nivel_mochila", self.NivelMochila))
        self.BatalhasPVPVencidas = int(dados.get("batalhas_pvp_vencidas", self.BatalhasPVPVencidas))
        self.BatalhasBotVencidas = int(dados.get("batalhas_bot_vencidas", self.BatalhasBotVencidas))
        self.Ouro = int(dados.get("ouro", self.Ouro))
        self.PassosCaminhados = int(dados.get("passos_caminhados", self.PassosCaminhados))
        self.Insignias = list(dados.get("insignias", self.Insignias))
        self.Maestria = int(dados.get("maestria", self.Maestria))
        self.SkinsLiberadas = list(dados.get("skins_liberadas", self.SkinsLiberadas))
        self.StaminaMax = max(1.0, float(dados.get("stamina_max", self.StaminaMax)))
        self.Stamina = max(0.0, min(self.StaminaMax, float(dados.get("stamina", self.Stamina))))

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
            "stamina": self.Stamina,
            "stamina_max": self.StaminaMax,
        }
