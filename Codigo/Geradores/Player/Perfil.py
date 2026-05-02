"""Perfil simples do player com progressão e marcos."""

from __future__ import annotations

class Perfil:
    NIVEL_MAXIMO = 50
    TIPOS_ESTADIO = (
        "Normal", "Fogo", "Agua", "Planta", "Eletrico", "Gelo", "Lutador", "Venenoso", "Terrestre", "Voador",
        "Psiquico", "Inseto", "Pedra", "Fantasma", "Dragao", "Sombrio", "Metal", "Fada", "Cosmico", "Sonoro",
    )

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
        self.Fugas = 0
        self.DungeonsTerminadas = 0
        self.Elo = 0
        self.EternidadeDerrotada = False
        self.GrandeCampeaoDerrotado = False
        self.EstadiosLiderados = []
        self.MoedasMaximas = 0
        self.RecursosMiticosMaximos = 0
        self.LimiteConhecimento = 300
        self.Conhecimento = {"Efeitos": [], "Ataques": [], "Pokemons": [], "Itens": [], "Musicas": []}
        self.SkinsLiberadas = self._skins_liberadas_padrao()
        self.HabilidadesAprendidas = []
        self.PresentesResgatadosNPC = {}
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
        for tipo in self.TIPOS_ESTADIO:
            setattr(self, f"RespeitoEstadio{tipo}", 0)

    @staticmethod
    def _ordem_skin(nome: str) -> tuple[int, str]:
        base = str(nome or "").strip().lower()
        if base.endswith(".png"):
            base = base[:-4]
        if base.startswith("s") and base[1:].isdigit():
            base = base[1:]
        if base.isdigit():
            return (0, int(base))
        return (1, base)

    @classmethod
    def _skins_liberadas_padrao(cls):
        return [f"{i}.png" for i in range(1, 13)]

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

    @staticmethod
    def _quantidade_item(item) -> int:
        if not isinstance(item, dict):
            return 0
        try:
            return max(1, int(item.get("quantidade", item.get("Quantidade", 1)) or 1))
        except (TypeError, ValueError):
            return 1

    @classmethod
    def contar_recursos_miticos_itens(cls, itens) -> int:
        total = 0
        for item in list(itens or []):
            if not isinstance(item, dict):
                continue
            estilo = str(item.get("Estilo") or item.get("estilo") or "").strip().lower()
            if estilo != "recurso":
                continue
            raridade = item.get("Raridade", item.get("raridade", 0))
            try:
                eh_mitico = int(float(raridade or 0)) >= 6
            except (TypeError, ValueError):
                eh_mitico = "mitic" in str(raridade or "").strip().lower()
            if eh_mitico:
                total += cls._quantidade_item(item)
        return total

    def atualizar_moedas_maximas(self) -> None:
        novo = max(0, int(self.MoedasMaximas), int(self.Dinheiro))
        if novo != self.MoedasMaximas:
            self.MoedasMaximas = novo
            self._perfil_dirty = True

    def atualizar_recursos_miticos_maximos(self, itens) -> None:
        novo = max(0, int(self.RecursosMiticosMaximos), self.contar_recursos_miticos_itens(itens))
        if novo != self.RecursosMiticosMaximos:
            self.RecursosMiticosMaximos = novo
            self._perfil_dirty = True

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
        self.LimiteSlotsInventario = int(self._pegar(dados, "limite_slots_inventario", "LimiteSlotsInventario", padrao=self.LimiteSlotsInventario))
        self.LimitePokemons = int(self._pegar(dados, "limite_pokemons", "LimitePokemons", padrao=self.LimitePokemons))
        self.LimiteTimesPokemon = int(self._pegar(dados, "limite_times_pokemon", "LimiteTimesPokemon", padrao=self.LimiteTimesPokemon))
        self.BatalhasPVPVencidas = int(self._pegar(dados, "batalhas_pvp_vencidas", "BatalhasPVPVencidas", padrao=self.BatalhasPVPVencidas))
        self.BatalhasBotVencidas = int(self._pegar(dados, "batalhas_bot_vencidas", "BatalhasBotVencidas", padrao=self.BatalhasBotVencidas))
        self.Dinheiro = int(self._pegar(dados, "dinheiro", "Dinheiro", padrao=self.Dinheiro))
        self.BausAbertos = max(0, int(self._pegar(dados, "baus_abertos", "BausAbertos", padrao=self.BausAbertos)))
        self.MetrosAndados = max(0.0, float(self._pegar(dados, "metros_andados", "MetrosAndados", padrao=self.MetrosAndados)))
        self.TempoJogoSegundos = max(0.0, float(self._pegar(dados, "tempo_jogo_segundos", "TempoJogoSegundos", padrao=self.TempoJogoSegundos)))
        self.Insignias = list(self._pegar(dados, "insignias", "Insignias", padrao=self.Insignias) or [])
        self.Maestria = int(self._pegar(dados, "maestria", "Maestria", padrao=self.Maestria))
        self.Fugas = max(0, int(self._pegar(dados, "fugas", "Fugas", padrao=self.Fugas)))
        self.DungeonsTerminadas = max(0, int(self._pegar(dados, "dungeons_terminadas", "DungeonsTerminadas", padrao=self.DungeonsTerminadas)))
        self.Elo = int(self._pegar(dados, "elo", "Elo", padrao=self.Elo))
        self.EternidadeDerrotada = bool(self._pegar(dados, "eternidade_derrotada", "EternidadeDerrotada", padrao=self.EternidadeDerrotada))
        self.GrandeCampeaoDerrotado = bool(self._pegar(dados, "grande_campeao_derrotado", "GrandeCampeaoDerrotado", padrao=self.GrandeCampeaoDerrotado))
        self.EstadiosLiderados = list(dict.fromkeys(self._pegar(dados, "estadios_liderados", "EstadiosLiderados", padrao=self.EstadiosLiderados) or []))
        self.MoedasMaximas = max(0, int(self._pegar(dados, "moedas_maximas", "MoedasMaximas", padrao=self.MoedasMaximas)))
        self.RecursosMiticosMaximos = max(0, int(self._pegar(dados, "recursos_miticos_maximos", "RecursosMiticosMaximos", padrao=self.RecursosMiticosMaximos)))
        self.LimiteConhecimento = max(0, int(self._pegar(dados, "limite_conhecimento", "LimiteConhecimento", padrao=self.LimiteConhecimento)))
        conhecimento_raw = self._pegar(dados, "conhecimento", "Conhecimento", padrao=self.Conhecimento)
        conhecimento_norm = {"Efeitos": [], "Ataques": [], "Pokemons": [], "Itens": [], "Musicas": []}
        if isinstance(conhecimento_raw, dict):
            for chave in conhecimento_norm:
                vals = conhecimento_raw.get(chave)
                if isinstance(vals, list):
                    conhecimento_norm[chave] = list(dict.fromkeys(vals))
        self.Conhecimento = conhecimento_norm
        skins_raw = list(self._pegar(dados, "skins_liberadas", "SkinsLiberadas", padrao=self.SkinsLiberadas) or self._skins_liberadas_padrao())
        normalizadas = []
        for skin in skins_raw:
            nome = str(skin or "").strip()
            if not nome:
                continue
            if nome.lower().startswith("s") and nome[1:].isdigit():
                nome = nome[1:]
            if not nome.lower().endswith(".png"):
                nome = f"{nome}.png"
            normalizadas.append(nome)
        self.SkinsLiberadas = sorted(dict.fromkeys(normalizadas), key=self._ordem_skin) or self._skins_liberadas_padrao()
        self.HabilidadesAprendidas = list(self._pegar(dados, "habilidades_aprendidas", "HabilidadesAprendidas", padrao=self.HabilidadesAprendidas) or [])
        presentes_raw = self._pegar(dados, "presentes_resgatados_npc", "PresentesResgatadosNPC", padrao=self.PresentesResgatadosNPC)
        presentes_norm = {}
        if isinstance(presentes_raw, dict):
            for npc, presentes in presentes_raw.items():
                chave_npc = str(npc or "").strip()
                if not chave_npc:
                    continue
                lista = [str(p or "").strip() for p in list(presentes or []) if str(p or "").strip()]
                if lista:
                    presentes_norm[chave_npc] = sorted(dict.fromkeys(lista))
        self.PresentesResgatadosNPC = presentes_norm
        self.StaminaMax = float(self._pegar(dados, "stamina_max", "StaminaMax", padrao=self.StaminaMax))
        self.Stamina = max(0.0, min(self.StaminaMax, float(self._pegar(dados, "stamina", "Stamina", padrao=self.Stamina))))

        self.VelocidadeBaseTiles = float(self._pegar(dados, "velocidade_base_tiles", "VelocidadeBaseTiles", padrao=self.VelocidadeBaseTiles))
        self.BonusVelocidadeCorridaMin = float(self._pegar(dados, "bonus_velocidade_corrida_min", "BonusVelocidadeCorridaMin", padrao=self.BonusVelocidadeCorridaMin))
        self.BonusVelocidadeCorridaMax = float(self._pegar(dados, "bonus_velocidade_corrida_max", "BonusVelocidadeCorridaMax", padrao=self.BonusVelocidadeCorridaMax))
        self.TempoAceleracaoCorrida = float(self._pegar(dados, "tempo_aceleracao_corrida", "TempoAceleracaoCorrida", padrao=self.TempoAceleracaoCorrida))
        self.TempoDesaceleracaoCorrida = float(self._pegar(dados, "tempo_desaceleracao_corrida", "TempoDesaceleracaoCorrida", padrao=self.TempoDesaceleracaoCorrida))
        self.AtrasoRegeneracaoStamina = float(self._pegar(dados, "atraso_regeneracao_stamina", "AtrasoRegeneracaoStamina", padrao=self.AtrasoRegeneracaoStamina))
        self.RegeneracaoStaminaParado = float(self._pegar(dados, "regeneracao_stamina_parado", "RegeneracaoStaminaParado", padrao=self.RegeneracaoStaminaParado))
        self.RegeneracaoStaminaAndando = float(self._pegar(dados, "regeneracao_stamina_andando", "RegeneracaoStaminaAndando", padrao=self.RegeneracaoStaminaAndando))
        self.CustoStaminaCorrida = float(self._pegar(dados, "custo_stamina_corrida", "CustoStaminaCorrida", padrao=self.CustoStaminaCorrida))
        self.CustoStaminaCorridaMax = float(self._pegar(dados, "custo_stamina_corrida_max", "CustoStaminaCorridaMax", padrao=self.CustoStaminaCorridaMax))
        self.CustoStaminaAguaRasa = float(self._pegar(dados, "custo_stamina_agua_rasa", "CustoStaminaAguaRasa", padrao=self.CustoStaminaAguaRasa))
        self.CustoStaminaAguaFunda = float(self._pegar(dados, "custo_stamina_agua_funda", "CustoStaminaAguaFunda", padrao=self.CustoStaminaAguaFunda))
        self.TapaPorSegundo = float(self._pegar(dados, "tapa_por_segundo", "TapaPorSegundo", padrao=self.TapaPorSegundo))
        self.RaioTapa = float(self._pegar(dados, "raio_tapa", "RaioTapa", padrao=self.RaioTapa))
        self.MultiplicadorFerramentaTapa = float(self._pegar(dados, "multiplicador_ferramenta_tapa", "MultiplicadorFerramentaTapa", padrao=self.MultiplicadorFerramentaTapa))
        for tipo in self.TIPOS_ESTADIO:
            chave_snake = f"respeito_estadio_{tipo.lower()}"
            chave_camel = f"RespeitoEstadio{tipo}"
            valor = int(self._pegar(dados, chave_snake, chave_camel, padrao=getattr(self, chave_camel, 0)))
            setattr(self, chave_camel, max(0, min(4, valor)))
        self.normalizar_progresso_xp()

    def serializar(self):
        dados = {
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
            "fugas": self.Fugas,
            "dungeons_terminadas": self.DungeonsTerminadas,
            "elo": self.Elo,
            "eternidade_derrotada": bool(self.EternidadeDerrotada),
            "grande_campeao_derrotado": bool(self.GrandeCampeaoDerrotado),
            "estadios_liderados": list(self.EstadiosLiderados),
            "moedas_maximas": int(self.MoedasMaximas),
            "recursos_miticos_maximos": int(self.RecursosMiticosMaximos),
            "limite_conhecimento": self.LimiteConhecimento,
            "conhecimento": {k: list(v) for k, v in self.Conhecimento.items()},
            "skins_liberadas": list(self.SkinsLiberadas),
            "habilidades_aprendidas": list(self.HabilidadesAprendidas),
            "presentes_resgatados_npc": {str(npc): list(valores) for npc, valores in self.PresentesResgatadosNPC.items()},
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
        for tipo in self.TIPOS_ESTADIO:
            dados[f"respeito_estadio_{tipo.lower()}"] = int(max(0, min(4, getattr(self, f"RespeitoEstadio{tipo}", 0))))
        return dados

    def presente_npc_ja_resgatado(self, npc_code: str, presente_id: str) -> bool:
        npc = str(npc_code or "").strip()
        presente = str(presente_id or "").strip()
        if not npc or not presente:
            return False
        return presente in set(self.PresentesResgatadosNPC.get(npc, []))

    def registrar_presente_npc(self, npc_code: str, presente_id: str) -> None:
        npc = str(npc_code or "").strip()
        presente = str(presente_id or "").strip()
        if not npc or not presente:
            return
        atuais = set(self.PresentesResgatadosNPC.get(npc, []))
        atuais.add(presente)
        self.PresentesResgatadosNPC[npc] = sorted(atuais)


    def registrar_fuga(self, quantidade: int = 1) -> None:
        self.Fugas = max(0, int(self.Fugas) + max(0, int(quantidade)))
        self._perfil_dirty = True

    def registrar_batalha(self, vencedor=False, contra_bot=True, quantidade: int = 1) -> None:
        qtd = max(0, int(quantidade))
        if qtd <= 0:
            return
        self.BatalhasTotais = max(0, int(self.BatalhasTotais) + qtd)
        if bool(vencedor):
            if bool(contra_bot):
                self.BatalhasBotVencidas = max(0, int(self.BatalhasBotVencidas) + qtd)
            else:
                self.BatalhasPVPVencidas = max(0, int(self.BatalhasPVPVencidas) + qtd)
        self._perfil_dirty = True

    def registrar_conhecimento(self, categoria: str, conhecimento_id) -> bool:
        categoria_fmt = str(categoria or "").strip().title()
        if categoria_fmt not in self.Conhecimento:
            return False
        if conhecimento_id is None:
            return False
        total = sum(len(v) for v in self.Conhecimento.values())
        valor = int(conhecimento_id) if isinstance(conhecimento_id, (int, float)) else str(conhecimento_id).strip()
        if not valor:
            return False
        if valor in self.Conhecimento[categoria_fmt]:
            return False
        if total >= max(0, int(self.LimiteConhecimento)):
            return False
        self.Conhecimento[categoria_fmt].append(valor)
        self._perfil_dirty = True
        return True

    @staticmethod
    def _extrair_id_generico(valor):
        if isinstance(valor, dict):
            for chave in ("id", "ID", "code", "Code", "codigo", "Codigo", "nome", "Nome"):
                v = valor.get(chave)
                if v is not None and str(v).strip():
                    return v
            return None
        for chave in ("ID", "Id", "id", "Code", "code", "Codigo", "codigo", "Nome", "nome"):
            if hasattr(valor, chave):
                v = getattr(valor, chave)
                if v is not None and str(v).strip():
                    return v
        return valor

    @classmethod
    def _extrair_id_pokemon(cls, pokemon):
        fontes = []
        if isinstance(pokemon, dict):
            fontes.append(pokemon)
            for chave in ("dados", "Dados", "estado", "Estado"):
                valor = pokemon.get(chave)
                if isinstance(valor, dict):
                    fontes.append(valor)
        else:
            dados = getattr(pokemon, "Dados", None)
            if isinstance(dados, dict):
                fontes.append(dados)
        for fonte in fontes:
            for chave in ("code", "Code", "codigo", "Codigo", "especie", "Especie", "nome", "Nome"):
                v = fonte.get(chave)
                if v is not None and str(v).strip():
                    return v
        if not isinstance(pokemon, dict):
            for chave in ("Code", "code", "Codigo", "codigo", "Especie", "especie", "Nome", "nome"):
                if hasattr(pokemon, chave):
                    v = getattr(pokemon, chave)
                    if v is not None and str(v).strip():
                        return v
        return None

    def registrar_conhecimento_pokemon(self, pokemon) -> bool:
        pid = self._extrair_id_pokemon(pokemon)
        return self.registrar_conhecimento("Pokemons", pid)

    def registrar_conhecimento_ataques_pokemon(self, pokemon) -> None:
        for ataque in self._iter_ataques_pokemon(pokemon):
            aid = self._extrair_id_generico(ataque)
            self.registrar_conhecimento("Ataques", aid)

    @classmethod
    def _iter_ataques_pokemon(cls, pokemon):
        fontes = []
        if isinstance(pokemon, dict):
            fontes.append(pokemon)
            for chave in ("Dados", "dados", "estado", "Estado", "Build", "build"):
                valor = pokemon.get(chave)
                if isinstance(valor, dict):
                    fontes.append(valor)
                    estado = valor.get("estado") if isinstance(valor.get("estado"), dict) else None
                    if estado is not None:
                        fontes.append(estado)
        else:
            for chave in ("ListaAtaques", "Ataques", "ataques", "Moves", "moves", "Habilidades", "habilidades"):
                valor = getattr(pokemon, chave, None)
                if isinstance(valor, list):
                    yield from [a for a in valor if a is not None]
            dados = getattr(pokemon, "Dados", None)
            if isinstance(dados, dict):
                fontes.append(dados)

        for fonte in fontes:
            for chave in ("ListaAtaques", "Ataques", "ataques", "Moves", "moves", "Habilidades", "habilidades", "Ativos", "ativos", "Golpes", "golpes"):
                valor = fonte.get(chave) if isinstance(fonte, dict) else None
                if isinstance(valor, list):
                    for ataque in valor:
                        if ataque is not None:
                            yield ataque

    def registrar_conhecimento_item(self, item) -> bool:
        return self.registrar_conhecimento("Itens", self._extrair_id_generico(item))

    def registrar_conhecimento_efeito(self, efeito_id) -> bool:
        return self.registrar_conhecimento("Efeitos", efeito_id)

    def registrar_conhecimento_musica(self, musica_id) -> bool:
        return self.registrar_conhecimento("Musicas", musica_id)


PlayerPerfil = Perfil
