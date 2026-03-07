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

        self.VelocidadeBaseTiles = 4.8
        self.BonusVelocidadeCorridaMin = 0.30
        self.BonusVelocidadeCorridaMax = 0.60
        self.TempoAceleracaoCorrida = 3.0
        self.TempoDesaceleracaoCorrida = 3.0
        self.AtrasoRegeneracaoStamina = 2.0
        self.RegeneracaoStaminaParado = 12.0
        self.RegeneracaoStaminaAndando = 6.0
        self.CustoStaminaCorrida = 10.0
        self.CustoStaminaCorridaMax = 15.0
        self.CustoStaminaAguaRasa = 4.0
        self.CustoStaminaAguaFunda = 16.0

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

        self.VelocidadeBaseTiles = max(0.1, float(dados.get("velocidade_base_tiles", self.VelocidadeBaseTiles)))
        self.BonusVelocidadeCorridaMin = max(0.0, float(dados.get("bonus_velocidade_corrida_min", self.BonusVelocidadeCorridaMin)))
        self.BonusVelocidadeCorridaMax = max(self.BonusVelocidadeCorridaMin, float(dados.get("bonus_velocidade_corrida_max", self.BonusVelocidadeCorridaMax)))
        self.TempoAceleracaoCorrida = max(0.1, float(dados.get("tempo_aceleracao_corrida", self.TempoAceleracaoCorrida)))
        self.TempoDesaceleracaoCorrida = max(0.1, float(dados.get("tempo_desaceleracao_corrida", self.TempoDesaceleracaoCorrida)))
        self.AtrasoRegeneracaoStamina = max(0.0, float(dados.get("atraso_regeneracao_stamina", self.AtrasoRegeneracaoStamina)))
        self.RegeneracaoStaminaParado = max(0.0, float(dados.get("regeneracao_stamina_parado", self.RegeneracaoStaminaParado)))
        self.RegeneracaoStaminaAndando = max(0.0, float(dados.get("regeneracao_stamina_andando", self.RegeneracaoStaminaAndando)))
        self.CustoStaminaCorrida = max(0.0, float(dados.get("custo_stamina_corrida", self.CustoStaminaCorrida)))
        self.CustoStaminaCorridaMax = max(self.CustoStaminaCorrida, float(dados.get("custo_stamina_corrida_max", self.CustoStaminaCorridaMax)))
        self.CustoStaminaAguaRasa = max(0.0, float(dados.get("custo_stamina_agua_rasa", self.CustoStaminaAguaRasa)))
        self.CustoStaminaAguaFunda = max(0.0, float(dados.get("custo_stamina_agua_funda", self.CustoStaminaAguaFunda)))

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
            "velocidade_base_tiles": self.VelocidadeBaseTiles,
            "bonus_velocidade_corrida_min": self.BonusVelocidadeCorridaMin,
            "bonus_velocidade_corrida_max": self.BonusVelocidadeCorridaMax,
            "tempo_aceleracao_corrida": self.TempoAceleracaoCorrida,
            "tempo_desaceleracao_corrida": self.TempoDesaceleracaoCorrida,
            "atraso_regeneracao_stamina": self.AtrasoRegeneracaoStamina,
            "regeneracao_stamina_parado": self.RegeneracaoStaminaParado,
            "regeneracao_stamina_andando": self.RegeneracaoStaminaAndando,
            "custo_stamina_corrida": self.CustoStaminaCorrida,
            "custo_stamina_corrida_max": self.CustoStaminaCorridaMax,
            "custo_stamina_agua_rasa": self.CustoStaminaAguaRasa,
            "custo_stamina_agua_funda": self.CustoStaminaAguaFunda,
        }
