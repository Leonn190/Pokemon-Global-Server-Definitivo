"""Perfil simples do player com progressão e marcos."""

from __future__ import annotations

from pathlib import Path


class Perfil:
    NIVEL_MAXIMO = 50

    def __init__(self):
        self.Nivel = 0
        self.XP = 0
        self.XPAlvo = self.calcular_xp_alvo_por_nivel(self.Nivel)
        self.BatalhasTotais = 0
        self.NivelMochila = 1
        self.LimiteSlotsInventario = 32
        self.LimitePokemons = 64
        self.LimiteTimesPokemon = 6
        self.BatalhasPVPVencidas = 0
        self.BatalhasBotVencidas = 0
        self.Dinheiro = 20
        self.BausAbertos = 0
        self.MetrosAndados = 0.0
        self.TempoJogoSegundos = 0.0
        self.Insignias = []
        self.Maestria = 0
        self.SkinsLiberadas = self._skins_liberadas_padrao()
        self.HabilidadesAprendidas = []
        self.StaminaMax = 100.0
        self.Stamina = 100.0

        self.VelocidadeBaseTiles = 5.0
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
        self.RaioTapa = 0.36
        self.MultiplicadorFerramentaTapa = 1.5

    @staticmethod
    def _skins_liberadas_padrao():
        pasta = Path("Recursos") / "Visual" / "Skins"
        if not pasta.exists():
            return ["1.png"]
        skins = sorted({p.name for p in pasta.glob("*.png") if p.is_file()})
        return skins or ["1.png"]

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
        self.MetrosAndados += max(0.0, float(distancia_tiles))

    def registrar_tempo_jogo(self, dt: float) -> None:
        self.TempoJogoSegundos += max(0.0, float(dt))

    def consumir_stamina(self, quantidade: float) -> float:
        self.Stamina = max(0.0, self.Stamina - max(0.0, float(quantidade)))
        return self.Stamina

    def regenerar_stamina(self, quantidade: float) -> float:
        self.Stamina = min(self.StaminaMax, self.Stamina + max(0.0, float(quantidade)))
        return self.Stamina

    @staticmethod
    def _pegar(dados, *chaves, padrao=None):
        for chave in chaves:
            if chave in dados:
                return dados[chave]
        return padrao

    def aplicar_serializado(self, dados):
        if not isinstance(dados, dict):
            return

        self.Nivel = int(self._pegar(dados, "nivel", "Nivel", padrao=self.Nivel))
        self.XP = int(self._pegar(dados, "xp", "XP", padrao=self.XP))
        self.XPAlvo = int(self._pegar(dados, "xp_alvo", "XPAlvo", padrao=self.XPAlvo))
        self.BatalhasTotais = int(self._pegar(dados, "batalhas_totais", "BatalhasTotais", padrao=self.BatalhasTotais))
        self.NivelMochila = int(self._pegar(dados, "nivel_mochila", "NivelMochila", padrao=self.NivelMochila))
        self.LimiteSlotsInventario = int(max(1, self._pegar(dados, "limite_slots_inventario", "LimiteSlotsInventario", padrao=self.LimiteSlotsInventario)))
        self.LimitePokemons = int(max(1, self._pegar(dados, "limite_pokemons", "LimitePokemons", padrao=self.LimitePokemons)))
        self.LimiteTimesPokemon = int(max(1, self._pegar(dados, "limite_times_pokemon", "LimiteTimesPokemon", padrao=self.LimiteTimesPokemon)))
        self.BatalhasPVPVencidas = int(self._pegar(dados, "batalhas_pvp_vencidas", "BatalhasPVPVencidas", padrao=self.BatalhasPVPVencidas))
        self.BatalhasBotVencidas = int(self._pegar(dados, "batalhas_bot_vencidas", "BatalhasBotVencidas", padrao=self.BatalhasBotVencidas))
        self.Dinheiro = int(self._pegar(dados, "dinheiro", "Dinheiro", padrao=self.Dinheiro))
        self.BausAbertos = max(0, int(self._pegar(dados, "baus_abertos", "BausAbertos", padrao=self.BausAbertos)))
        self.MetrosAndados = max(0.0, float(self._pegar(dados, "metros_andados", "MetrosAndados", padrao=self.MetrosAndados)))
        self.TempoJogoSegundos = max(0.0, float(self._pegar(dados, "tempo_jogo_segundos", "TempoJogoSegundos", padrao=self.TempoJogoSegundos)))
        self.Insignias = list(self._pegar(dados, "insignias", "Insignias", padrao=self.Insignias) or [])
        self.Maestria = int(self._pegar(dados, "maestria", "Maestria", padrao=self.Maestria))
        self.SkinsLiberadas = list(self._pegar(dados, "skins_liberadas", "SkinsLiberadas", padrao=self.SkinsLiberadas) or self._skins_liberadas_padrao())
        self.HabilidadesAprendidas = list(self._pegar(dados, "habilidades_aprendidas", "HabilidadesAprendidas", padrao=self.HabilidadesAprendidas) or [])
        self.StaminaMax = max(1.0, float(self._pegar(dados, "stamina_max", "StaminaMax", padrao=self.StaminaMax)))
        self.Stamina = max(0.0, min(self.StaminaMax, float(self._pegar(dados, "stamina", "Stamina", padrao=self.Stamina))))

        self.VelocidadeBaseTiles = max(0.1, float(self._pegar(dados, "velocidade_base_tiles", "VelocidadeBaseTiles", padrao=self.VelocidadeBaseTiles)))
        self.BonusVelocidadeCorridaMin = max(0.0, float(self._pegar(dados, "bonus_velocidade_corrida_min", "BonusVelocidadeCorridaMin", padrao=self.BonusVelocidadeCorridaMin)))
        self.BonusVelocidadeCorridaMax = max(self.BonusVelocidadeCorridaMin, float(self._pegar(dados, "bonus_velocidade_corrida_max", "BonusVelocidadeCorridaMax", padrao=self.BonusVelocidadeCorridaMax)))
        self.TempoAceleracaoCorrida = max(0.1, float(self._pegar(dados, "tempo_aceleracao_corrida", "TempoAceleracaoCorrida", padrao=self.TempoAceleracaoCorrida)))
        self.TempoDesaceleracaoCorrida = max(0.1, float(self._pegar(dados, "tempo_desaceleracao_corrida", "TempoDesaceleracaoCorrida", padrao=self.TempoDesaceleracaoCorrida)))
        self.AtrasoRegeneracaoStamina = max(0.0, float(self._pegar(dados, "atraso_regeneracao_stamina", "AtrasoRegeneracaoStamina", padrao=self.AtrasoRegeneracaoStamina)))
        self.RegeneracaoStaminaParado = max(0.0, float(self._pegar(dados, "regeneracao_stamina_parado", "RegeneracaoStaminaParado", padrao=self.RegeneracaoStaminaParado)))
        self.RegeneracaoStaminaAndando = max(0.0, float(self._pegar(dados, "regeneracao_stamina_andando", "RegeneracaoStaminaAndando", padrao=self.RegeneracaoStaminaAndando)))
        self.CustoStaminaCorrida = max(0.0, float(self._pegar(dados, "custo_stamina_corrida", "CustoStaminaCorrida", padrao=self.CustoStaminaCorrida)))
        self.CustoStaminaCorridaMax = max(self.CustoStaminaCorrida, float(self._pegar(dados, "custo_stamina_corrida_max", "CustoStaminaCorridaMax", padrao=self.CustoStaminaCorridaMax)))
        self.CustoStaminaAguaRasa = max(0.0, float(self._pegar(dados, "custo_stamina_agua_rasa", "CustoStaminaAguaRasa", padrao=self.CustoStaminaAguaRasa)))
        self.CustoStaminaAguaFunda = max(0.0, float(self._pegar(dados, "custo_stamina_agua_funda", "CustoStaminaAguaFunda", padrao=self.CustoStaminaAguaFunda)))
        self.TapaPorSegundo = max(0.1, float(self._pegar(dados, "tapa_por_segundo", "TapaPorSegundo", padrao=self.TapaPorSegundo)))
        self.RaioTapa = max(0.05, float(self._pegar(dados, "raio_tapa", "RaioTapa", padrao=self.RaioTapa)))
        self.MultiplicadorFerramentaTapa = max(1.0, float(self._pegar(dados, "multiplicador_ferramenta_tapa", "MultiplicadorFerramentaTapa", padrao=self.MultiplicadorFerramentaTapa)))
        self.normalizar_progresso_xp()

    def serializar(self):
        return {
            "nivel": self.Nivel,
            "xp": self.XP,
            "xp_alvo": self.XPAlvo,
            "batalhas_totais": self.BatalhasTotais,
            "nivel_mochila": self.NivelMochila,
            "limite_slots_inventario": self.LimiteSlotsInventario,
            "limite_pokemons": self.LimitePokemons,
            "limite_times_pokemon": self.LimiteTimesPokemon,
            "batalhas_pvp_vencidas": self.BatalhasPVPVencidas,
            "batalhas_bot_vencidas": self.BatalhasBotVencidas,
            "dinheiro": self.Dinheiro,
            "baus_abertos": self.BausAbertos,
            "metros_andados": self.MetrosAndados,
            "tempo_jogo_segundos": int(self.TempoJogoSegundos),
            "insignias": list(self.Insignias),
            "maestria": self.Maestria,
            "skins_liberadas": list(self.SkinsLiberadas),
            "habilidades_aprendidas": list(self.HabilidadesAprendidas),
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
            "tapa_por_segundo": self.TapaPorSegundo,
            "raio_tapa": self.RaioTapa,
            "multiplicador_ferramenta_tapa": self.MultiplicadorFerramentaTapa,
        }


PlayerPerfil = Perfil
