"""Perfil simples do player com progressão e marcos."""

from __future__ import annotations


class Perfil:
    NIVEL_MAXIMO = 50

    def __init__(self):
        self.Nivel = 0
        self.XP = 0
        self.XPAlvo = self.calcular_xp_alvo_por_nivel(self.Nivel)
        self.BatalhasTotais = 0
        self.NivelMochila = 1
        self.BatalhasPVPVencidas = 0
        self.BatalhasBotVencidas = 0
        self.Ouro = 0
        self.BausAbertos = 0
        self.MetrosAndados = 0.0
        self.TempoJogoSegundos = 0.0
        self.Insignias = []
        self.Maestria = 0
        self.SkinsLiberadas = []
        self.StaminaMax = 100.0
        self.Stamina = 100.0
        self.LimiteSlotsInventario = 32

        self.VelocidadeBaseTiles = 5
        self.BonusVelocidadeCorridaMin = 0.25
        self.BonusVelocidadeCorridaMax = 0.5
        self.TempoAceleracaoCorrida = 2.5
        self.TempoDesaceleracaoCorrida = 2.0
        self.AtrasoRegeneracaoStamina = 1.5
        self.RegeneracaoStaminaParado = 12.0
        self.RegeneracaoStaminaAndando = 5.0
        self.CustoStaminaCorrida = 10.0
        self.CustoStaminaCorridaMax = 16.0
        self.CustoStaminaAguaRasa = 4.0
        self.CustoStaminaAguaFunda = 16.0
        self.TapaPorSegundo = 2.0

    @classmethod
    def calcular_xp_alvo_por_nivel(cls, nivel: int) -> int:
        nivel_atual = max(0, int(nivel))
        if nivel_atual >= cls.NIVEL_MAXIMO:
            return 0
        faixa = nivel_atual // 10
        incremento = (faixa + 1) * 100
        base_faixa = 100 + (500 * faixa * faixa) + (600 * faixa)
        return int(base_faixa + (nivel_atual - (faixa * 10)) * incremento)

    def normalizar_progresso_xp(self) -> None:
        self.Nivel = max(0, min(self.NIVEL_MAXIMO, int(self.Nivel)))
        self.XP = max(0, int(self.XP))
        while self.Nivel < self.NIVEL_MAXIMO:
            alvo = self.calcular_xp_alvo_por_nivel(self.Nivel)
            if self.XP < alvo:
                self.XPAlvo = alvo
                return
            self.XP -= alvo
            self.Nivel += 1
        self.Nivel = self.NIVEL_MAXIMO
        self.XP = 0
        self.XPAlvo = 0

    def registrar_bau_aberto(self, quantidade: int = 1) -> None:
        self.BausAbertos += max(0, int(quantidade))

    def registrar_movimento(self, distancia_tiles: float) -> None:
        distancia = max(0.0, float(distancia_tiles))
        self.MetrosAndados += distancia

    def registrar_tempo_jogo(self, dt: float) -> None:
        self.TempoJogoSegundos += max(0.0, float(dt))

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
        self.Nivel = int(dados.get("nivel", self.Nivel))
        self.XP = int(dados.get("xp", self.XP))
        self.XPAlvo = int(dados.get("xp_alvo", self.XPAlvo))
        self.BatalhasTotais = int(dados.get("batalhas_totais", self.BatalhasTotais))
        self.NivelMochila = int(dados.get("nivel_mochila", self.NivelMochila))
        self.BatalhasPVPVencidas = int(dados.get("batalhas_pvp_vencidas", self.BatalhasPVPVencidas))
        self.BatalhasBotVencidas = int(dados.get("batalhas_bot_vencidas", self.BatalhasBotVencidas))
        self.Ouro = int(dados.get("ouro", self.Ouro))
        self.BausAbertos = max(0, int(dados.get("baus_abertos", self.BausAbertos)))
        self.MetrosAndados = max(0.0, float(dados.get("metros_andados", self.MetrosAndados)))
        self.TempoJogoSegundos = max(0.0, float(dados.get("tempo_jogo_segundos", self.TempoJogoSegundos)))
        self.Insignias = list(dados.get("insignias", self.Insignias))
        self.Maestria = int(dados.get("maestria", self.Maestria))
        self.SkinsLiberadas = list(dados.get("skins_liberadas", self.SkinsLiberadas))
        self.StaminaMax = max(1.0, float(dados.get("stamina_max", self.StaminaMax)))
        self.Stamina = max(0.0, min(self.StaminaMax, float(dados.get("stamina", self.Stamina))))
        self.LimiteSlotsInventario = int(max(1, dados.get("limite_slots_inventario", self.LimiteSlotsInventario)))

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
        self.TapaPorSegundo = max(0.1, float(dados.get("tapa_por_segundo", self.TapaPorSegundo)))
        self.normalizar_progresso_xp()

    def serializar(self):
        return {
            "nivel": self.Nivel,
            "xp": self.XP,
            "xp_alvo": self.XPAlvo,
            "batalhas_totais": self.BatalhasTotais,
            "nivel_mochila": self.NivelMochila,
            "batalhas_pvp_vencidas": self.BatalhasPVPVencidas,
            "batalhas_bot_vencidas": self.BatalhasBotVencidas,
            "ouro": self.Ouro,
            "baus_abertos": self.BausAbertos,
            "metros_andados": self.MetrosAndados,
            "tempo_jogo_segundos": int(self.TempoJogoSegundos),
            "insignias": list(self.Insignias),
            "maestria": self.Maestria,
            "skins_liberadas": list(self.SkinsLiberadas),
            "stamina": self.Stamina,
            "stamina_max": self.StaminaMax,
            "limite_slots_inventario": self.LimiteSlotsInventario,
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
            "tapa_por_segundo": self.TapaPorSegundo,
        }


PlayerPerfil = Perfil
