from __future__ import annotations

import math
import unicodedata


TERRENO_DANO_INCENDIADA_PCT_VIDA = 0.02
TERRENO_DANO_CONTAMINADA_PCT_VIDA = 0.02
TERRENO_CURA_ABENCOADA_PCT_VIDA = 0.03


def _normalizar(valor):
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


class AmbienteBatalhaServer:
    def __init__(self, partida):
        self.partida = partida

    def mudar_clima(self, nome, origem=None, dados=None):
        antes = self.partida.clima_atual
        self.partida.clima_atual = nome
        self.partida.clima_turnos_ativo = 0
        self.partida.registrar_evento_log(
            "clima_alterado",
            {
                "clima_antes": antes,
                "clima_depois": nome,
                "clima": nome,
                "origem_id": getattr(origem, "id_batalha", None),
                "origem_nome": getattr(origem, "nome", None),
                **(dict(dados or {})),
            },
        )
        self.partida.disparar_flag("AoMudarClima", {"partida": self.partida, "usuario": origem, "pokemon_evento": origem, "clima_antes": antes, "clima_depois": nome})
        return {"aplicado": True, "clima_antes": antes, "clima_depois": nome}

    def limpar_clima(self, motivo=None):
        antes = self.partida.clima_atual
        if not antes:
            return False
        self.partida.clima_atual = None
        self.partida.clima_turnos_ativo = 0
        self.partida.registrar_evento_log("clima_expirou", {"clima": antes, "motivo": motivo or "expirou"})
        return True

    def aplicar_variacoes_temporarias_clima(self, pokemon):
        clima = _normalizar(self.partida.clima_atual)
        if pokemon is None or not pokemon.esta_vivo():
            return
        tipos = {_normalizar(t) for t in getattr(pokemon, "tipos", [])}
        if clima == "nevasca" and "gelo" in tipos:
            pokemon.aplicar_variacao_temporaria("Def", pokemon.atributos_base.get("Def", 0.0) * 0.30)
            pokemon.aplicar_variacao_temporaria("SpD", pokemon.atributos_base.get("SpD", 0.0) * 0.30)
        elif clima in {"tempestadedeareia", "tempestadeareia"}:
            if "terrestre" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
        elif clima == "nevoa":
            pokemon.aplicar_variacao_temporaria("Ass", -30.0)
            if "fantasma" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
        elif clima == "gravidadeanomala":
            if "cosmico" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
            bonus = min(32, math.floor(float(getattr(pokemon, "dados_originais", {}).get("Peso", getattr(pokemon, "dados_originais", {}).get("peso", 0)) or 0) / 50.0) * 4)
            if bonus > 0:
                pokemon.aplicar_variacao_temporaria("Def", pokemon.atributos_base.get("Def", 0.0) * bonus / 100.0)
                pokemon.aplicar_variacao_temporaria("SpD", pokemon.atributos_base.get("SpD", 0.0) * bonus / 100.0)
        elif clima in {"tempestadederaios", "tempestaderaios"} and "eletrico" in tipos:
            pokemon.aplicar_variacao_temporaria("Ene", max(1.0, pokemon.atributos_base.get("Ene", 1.0)) * 0.50)
        elif clima == "noitedensa":
            if "sombrio" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
            else:
                pokemon.aplicar_variacao_temporaria("Acu", -pokemon.atributos_base.get("Acu", 100.0) * 0.25)
        if clima == "chuva" and self._pokemon_possui_ataque_code(pokemon, "51"):
            pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * self._parametro_ataque_code("51", "percentual_vel", 0.50))

    def _pokemon_possui_ataque_code(self, pokemon, code):
        alvo = str(code or "").strip()
        return bool(alvo) and any(str((ataque or {}).get("Code") or (ataque or {}).get("ID") or "").strip() == alvo for ataque in list(getattr(pokemon, "ataques", []) or []))

    def _parametro_ataque_code(self, code, chave, default=0.0):
        props = None
        mapa = getattr(getattr(self.partida, "coletor_acoes", None), "propriedades_ataques", {}) or {}
        code = str(code or "").strip()
        if code:
            props = mapa.get(code)
        if not isinstance(props, dict):
            props = {}
        parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
        try:
            return float(str(parametros.get(chave, default)).replace(",", "."))
        except (TypeError, ValueError):
            return float(default)

    def aplicar_clima_em_pokemon_por_passo(self, pokemon):
        clima = _normalizar(self.partida.clima_atual)
        if pokemon is None or not pokemon.esta_vivo():
            return
        tipos = {_normalizar(t) for t in getattr(pokemon, "tipos", [])}
        vida = pokemon.obter_atributo("Vida", 1.0)
        if clima == "chuva" and "gelo" in tipos:
            pokemon.ReceberCura(vida * 0.01, dados={"efeito": "Chuva"})
        elif clima == "solforte" and "gelo" in tipos:
            pokemon.ReceberDano(vida * 0.01, dados={"efeito": "Sol Forte", "ignorar_defensivos": True})
        elif clima in {"tempestadedeareia", "tempestadeareia"} and not (tipos & {"terrestre", "metal", "pedra"}):
            pokemon.ReceberDano(vida * 0.02, dados={"efeito": "Tempestade de Areia", "ignorar_defensivos": True})
        elif clima == "gravidadeanomala" and pokemon.possui_efeito("Voando"):
            pokemon.ReceberDano(vida * 0.02, dados={"efeito": "Gravidade Anomala", "ignorar_defensivos": True})
        elif clima == "chuvaacida":
            if "venenoso" in tipos or "veneno" in tipos:
                pokemon.ReceberCura(vida * 0.01, dados={"efeito": "Chuva Acida"})
            else:
                pokemon.ReceberDano(vida * 0.01, dados={"efeito": "Chuva Acida", "ignorar_defensivos": True})

    def aplicar_modificadores_dano_clima(self, tipo_ataque, dano):
        clima = _normalizar(self.partida.clima_atual)
        tipo = _normalizar(tipo_ataque)
        mult = 1.0
        if clima == "chuva":
            mult = 1.25 if tipo == "agua" else 0.75 if tipo == "fogo" else 1.0
        elif clima == "solforte":
            mult = 0.75 if tipo == "agua" else 1.25 if tipo == "fogo" else 1.0
        return max(0.0, float(dano or 0.0)) * mult, mult

    def processar_fim_de_turno_clima(self):
        if not self.partida.clima_atual:
            return False
        self.partida.clima_turnos_ativo += 1
        chance = min(100.0, 10.0 + max(0, self.partida.clima_turnos_ativo - 1) * 5.0)
        if self.partida.rng.random() * 100.0 <= chance:
            return self.limpar_clima(motivo="rng_fim_turno")
        return False

    def processar_clima_por_passo(self):
        if _normalizar(self.partida.clima_atual) not in {"tempestadederaios", "tempestaderaios"}:
            return
        if self.partida.passo_atual <= 0 or self.partida.passo_atual % 2 != 0 or self.partida._ultimo_passo_raios == self.partida.passo_atual:
            return
        self.partida._ultimo_passo_raios = self.partida.passo_atual
        por_lado = {}
        for area_id, area in self.partida.areas.items():
            por_lado.setdefault(int(area.get("lado_id", 0)), []).append(area_id)
        for lado_id, areas in por_lado.items():
            area_id = self.partida.rng.choice(list(areas))
            self.partida.registrar_evento_log("clima_raio_area", {"clima": self.partida.clima_atual, "lado_id": lado_id, "area_id": area_id})
            alvo = self.partida.pokemon_na_area(area_id)
            if alvo is not None and alvo.esta_vivo():
                dano = alvo.obter_atributo("Vida", 1.0) * 0.35
                alvo.ReceberDano(dano, dados={"efeito": "Tempestade de Raios", "ignorar_defensivos": True})

    def mudar_terreno(self, area_id, terreno, origem=None, dados=None):
        area_id = str(area_id or "").upper()
        if not self.partida.area_existe(area_id):
            return False
        antes = self.partida.efeitos_area.get(area_id)
        self.partida.efeitos_area[area_id] = {"terreno": terreno, "nome": terreno, **(dict(dados or {}))}
        self.partida.registrar_evento_log("terreno_alterado", {"area_id": area_id, "terreno_antes": antes, "terreno": terreno, "origem_id": getattr(origem, "id_batalha", None)})
        ocupante = self.partida.pokemon_na_area(area_id)
        if ocupante is not None:
            self.aplicar_terreno_ao_entrar(ocupante, area_id, dados=dados)
        return True

    def limpar_terreno(self, area_id, motivo=None):
        area_id = str(area_id or "").upper()
        terreno = self.partida.efeitos_area.pop(area_id, None)
        if terreno is None:
            return False
        self.partida.registrar_evento_log("terreno_removido", {"area_id": area_id, "terreno": terreno, "motivo": motivo})
        return True

    def obter_terreno_area(self, area_id):
        dado = self.partida.efeitos_area.get(str(area_id or "").upper())
        if isinstance(dado, dict):
            return dado.get("terreno") or dado.get("nome") or dado.get("efeito")
        return dado

    def aplicar_terreno_ao_entrar(self, pokemon, area_id, dados=None):
        dados = dict(dados or {})
        terreno_bruto = self.obter_terreno_area(area_id)
        terreno = _normalizar(terreno_bruto)
        if pokemon is None or not pokemon.esta_vivo():
            return
        if terreno:
            self.partida.disparar_flag(
                "AoEntrarEmTerreno",
                {
                    "partida": self.partida,
                    "pokemon_evento": pokemon,
                    "alvo": pokemon,
                    "area_id": str(area_id or "").upper(),
                    "terreno": terreno_bruto,
                    "dados": dict(dados),
                    "reativos_acao": dados.get("reativos_acao"),
                },
                reativos=dados.get("reativos_acao"),
            )
        if terreno == "contaminada":
            pokemon.ReceberEfeito({"nome": "Envenenado", "duracao": 3, "negativo": True}, origem=pokemon, dados={"terreno": "Contaminada"})
            self.partida.registrar_evento_log("terreno_aplicou_efeito", {"area_id": area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Contaminada", "efeito": "Envenenado"})

    def aplicar_terreno_por_passo(self, pokemon):
        terreno = _normalizar(self.obter_terreno_area(getattr(pokemon, "area_id", None)))
        if pokemon is None or not pokemon.esta_vivo():
            return
        vida = pokemon.obter_atributo("Vida", 1.0)
        if terreno == "incendiada":
            pokemon.ReceberDano(vida * TERRENO_DANO_INCENDIADA_PCT_VIDA, dados={"efeito": "Terreno Incendiada", "ignorar_defensivos": True})
            self.partida.registrar_evento_log("terreno_tickou", {"area_id": pokemon.area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Incendiada"})
        elif terreno == "contaminada":
            pokemon.ReceberDano(vida * TERRENO_DANO_CONTAMINADA_PCT_VIDA, dados={"efeito": "Terreno Contaminada", "ignorar_defensivos": True})
            self.partida.registrar_evento_log("terreno_tickou", {"area_id": pokemon.area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Contaminada"})
        elif terreno == "abencoada":
            pokemon.ReceberCura(vida * TERRENO_CURA_ABENCOADA_PCT_VIDA, dados={"efeito": "Terreno Abencoada"})
            self.partida.registrar_evento_log("terreno_tickou", {"area_id": pokemon.area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Abencoada"})

    def aplicar_variacoes_temporarias_terreno(self, pokemon):
        terreno = _normalizar(self.obter_terreno_area(getattr(pokemon, "area_id", None)))
        if pokemon is None or not pokemon.esta_vivo():
            return
        if terreno == "destruida":
            pokemon.aplicar_variacao_temporaria("Amp", -15.0)
            pokemon.aplicar_variacao_temporaria("Dur", -15.0)
        elif terreno == "energizada":
            pokemon.aplicar_variacao_temporaria("Ene", pokemon.atributos_base.get("Ene", 1.0))
        elif terreno == "sagrada":
            pokemon.aplicar_variacao_temporaria("Amp", 30.0)
        elif terreno == "elevada":
            pokemon.aplicar_variacao_temporaria("Acu", 35.0)
            pokemon.aplicar_variacao_temporaria("Ass", -15.0)
