from __future__ import annotations

import copy
import math
import unicodedata

from SimuladorServerJogo.Batalha.FraquezasResistencia import obter_multiplicador


ATRIBUTOS_OFICIAIS = [
    "Vida", "Atk", "SpA", "Def", "SpD", "Mag", "Ene", "Vel", "Per", "Int",
    "Vamp", "CrC", "CrD", "Dur", "Amp", "EneM", "Acu", "Ass", "Let",
]
_ALIAS_ATRIBUTO_EFEITO = {
    "vidamaxima": "Vida",
    "vida": "Vida",
    "acuracia": "Acu",
    "acu": "Acu",
    "assertividade": "Ass",
    "ass": "Ass",
    "letalidade": "Let",
    "let": "Let",
}
EFEITOS_NEGATIVOS = {
    "queimado", "envenenado", "intoxicado", "congelado", "dormindo", "paralisado",
    "enraizado", "cauterizado", "descarregado", "encharcado", "atordoado",
    "quebrado", "enfraquecido", "confuso", "bloqueado", "amaldicoado",
}
VARIACOES_TEMPORARIAS_EFEITOS = {
    "amplificado": {"Amp": 50.0},
    "fortificado": {"Dur": 50.0},
    "congelado": {"Dur": 30.0},
    "encharcado": {"Vel": -0.20},
    "energizado": {"Ene": 0.50},
    "descarregado": {"Ene": -0.50},
    "quebrado": {"Dur": -50.0},
    "enfraquecido": {"Amp": -50.0},
    "confuso": {"Acu": -50.0},
    "voando": {"Ass": -40.0},
    "focado": {"Acu": 50.0},
}


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _atributo_oficial(chave: object) -> str:
    return _ALIAS_ATRIBUTO_EFEITO.get(_normalizar(chave), str(chave))


def _buscar_atributo(fontes: tuple[dict, ...], nomes: tuple[str, ...], default=None):
    for fonte in fontes:
        if not isinstance(fonte, dict):
            continue
        for nome in nomes:
            if nome in fonte:
                return fonte.get(nome)
    return default


def _f(valor: object, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _i(valor: object, default: int = 0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


class PokemonBatalha:
    def __init__(self, dados: dict, partida=None, lado_id: int | None = None, indice: int = 1):
        bruto = dict(dados or {})
        info_bruto = bruto.get("dados") or bruto.get("Dados")
        info = dict(info_bruto) if isinstance(info_bruto, dict) else dict(bruto)
        estado = info.get("estado") if isinstance(info.get("estado"), dict) else {}
        self.partida = partida
        self.id_original = bruto.get("id_original", info.get("id", info.get("ID", bruto.get("id"))))
        if self.partida is not None and hasattr(self.partida, "novo_id_pokemon"):
            self.id_batalha = str(self.partida.novo_id_pokemon(lado_id if lado_id is not None else bruto.get("lado_id", 50)))
        else:
            self.id_batalha = str(bruto.get("id_batalha") or f"P{indice}")
        self.nome = str(info.get("nome") or info.get("Nome") or bruto.get("nome") or bruto.get("Nome") or "Pokemon")
        self.especie = str(info.get("especie") or info.get("Especie") or bruto.get("especie") or self.nome)
        self.nivel = max(1, _i(info.get("nivel", info.get("Nivel", bruto.get("nivel", 1))), 1))
        self.lado_id = int(lado_id if lado_id is not None else bruto.get("lado_id", 50))
        self.ativo = bool(bruto.get("ativo", bruto.get("Ativo", False)))
        self.reserva = bool(bruto.get("em_reserva", bruto.get("EmReserva", not self.ativo)))
        self.area_id = bruto.get("area_id", bruto.get("AreaId"))
        self.vivo = bool(bruto.get("vivo", bruto.get("Vivo", True)))
        self.dados_originais = copy.deepcopy(info or bruto)
        self.tipos = list(info.get("tipos") or info.get("Tipos") or estado.get("tipos") or bruto.get("tipos") or [])
        self.ataques = self._coletar_ataques(bruto, info, estado)
        self._instanciar_ids_ataques()
        self.Build = copy.deepcopy(info.get("Build") or info.get("build") or bruto.get("Build") or {})
        self.atributos_base = {}
        self.variacoes_temporarias = {}
        self.variacoes_permanentes = {}
        self.atributos_finais = {}
        self.efeitos_formais = list(bruto.get("efeitos") or bruto.get("efeitos_formais") or info.get("efeitos") or [])
        self.estados_transitorios = dict(bruto.get("estados_transitorios") or {})
        self.contadores_especiais = dict(bruto.get("contadores_especiais") or {})
        self.estatisticas_batalha = dict(bruto.get("estatisticas_batalha") or {})
        for chave in ("dano_causado", "dano_recebido", "cura_feita", "cura_recebida", "energia_gasta", "abates"):
            self.estatisticas_batalha.setdefault(chave, 0.0)
        self._carregar_atributos(info, estado, bruto)
        self.recalcular_atributos()
        vida_atual = _f(bruto.get("VidaAtual", info.get("VidaAtual", info.get("vida_atual", estado.get("VidaAtual", estado.get("vida_atual", self.atributos_finais["Vida"]))))), self.atributos_finais["Vida"])
        if 0.0 <= vida_atual <= 1.0:
            vida_atual *= self.atributos_finais["Vida"]
        self.VidaAtual = _clamp(vida_atual, 0.0, self.atributos_finais["Vida"])
        energia_padrao = round(self.atributos_finais["EneM"] * 0.75, 2)
        self.EnergiaAtual = _clamp(_f(bruto.get("Energia", bruto.get("EnergiaAtual", info.get("EnergiaAtual", info.get("energia_atual", estado.get("EnergiaAtual", estado.get("energia_atual", energia_padrao)))))), energia_padrao), 0.0, self.atributos_finais["EneM"])
        self.BarreiraAtual = max(0.0, _f(bruto.get("BarreiraAtual", info.get("BarreiraAtual", estado.get("BarreiraAtual", 0.0))), 0.0))
        if self.VidaAtual <= 0:
            self.vivo = False

    @staticmethod
    def _coletar_ataques(bruto: dict, info: dict, estado: dict) -> list:
        for fonte in (bruto, info, estado):
            for chave in ("ataques", "ListaAtaques", "Ataques", "habilidades", "Habilidades"):
                valor = fonte.get(chave) if isinstance(fonte, dict) else None
                if isinstance(valor, list) and any(isinstance(item, dict) for item in valor):
                    return [copy.deepcopy(item) for item in valor if isinstance(item, dict)]
        alvo = estado if isinstance(estado, dict) and estado else info
        try:
            from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import normalizar_habilidades_memorias

            normalizar_habilidades_memorias(alvo, total_slots=5)
        except Exception:
            return []
        valor = alvo.get("habilidades") if isinstance(alvo, dict) else None
        return [copy.deepcopy(item) for item in list(valor or []) if isinstance(item, dict)]

    def _registrar_evento(self, tipo, dados=None):
        if self.partida is None or not hasattr(self.partida, "registrar_evento_log"):
            return None
        return self.partida.registrar_evento_log(tipo, dados or {})

    def _disparar_flag(self, flag, contexto, reativos=None):
        if self.partida is None or not hasattr(self.partida, "disparar_flag"):
            return []
        return self.partida.disparar_flag(flag, contexto, reativos=reativos)

    def _instanciar_ids_ataques(self):
        for ataque in list(self.ataques or []):
            if not isinstance(ataque, dict):
                continue
            ataque.setdefault("id_original", ataque.get("ID") or ataque.get("Code"))
            if self.partida is not None and hasattr(self.partida, "novo_id_ataque"):
                ataque["id_batalha"] = str(self.partida.novo_id_ataque(self.lado_id))
                ataque["id_ataque_batalha"] = ataque["id_batalha"]

    def _dados_origem(self, origem):
        return {
            "origem_id": getattr(origem, "id_batalha", None),
            "origem_nome": getattr(origem, "nome", None),
        }

    def _carregar_atributos(self, info: dict, estado: dict, bruto: dict) -> None:
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else info.get("stats") if isinstance(info.get("stats"), dict) else {}
        stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else info.get("stats_base") if isinstance(info.get("stats_base"), dict) else {}
        attrs = bruto.get("Atributos") if isinstance(bruto.get("Atributos"), dict) else {}
        attrs_base = bruto.get("AtributosBase") if isinstance(bruto.get("AtributosBase"), dict) else {}
        variacoes = bruto.get("Variacoes") if isinstance(bruto.get("Variacoes"), dict) else info.get("variacoes") if isinstance(info.get("variacoes"), dict) else {}
        aliases = {"Amp": ("Amplificacao",), "Dur": ("Durabilidade",), "Acu": ("Acuracia",), "Ass": ("Assertividade",), "Let": ("Letalidade",)}
        for chave in ATRIBUTOS_OFICIAIS:
            nomes = (chave, *aliases.get(chave, ()))
            padrao = 100.0 if chave in {"Acu", "Ass"} else 0.0
            base = _f(_buscar_atributo((attrs_base, stats_base, stats, attrs), nomes, padrao), padrao)
            atual = _f(_buscar_atributo((attrs, stats), nomes, base), base)
            self.atributos_base[chave] = atual
            self.variacoes_permanentes[chave] = _f(_buscar_atributo((variacoes,), nomes, 0.0), 0.0)
            self.variacoes_temporarias[chave] = 0.0
        self.atributos_base["Dur"] = self.atributos_base.get("Dur", 0.0)
        self.atributos_base["Amp"] = self.atributos_base.get("Amp", 0.0)
        self.atributos_base["Vamp"] = self.atributos_base.get("Vamp", 0.0)
        self.atributos_base["Acu"] = self.atributos_base.get("Acu") or 100.0
        self.atributos_base["Ass"] = self.atributos_base.get("Ass") or 100.0
        self.atributos_base["Let"] = self.atributos_base.get("Let", 0.0)
        ene = self.atributos_base.get("Ene", 1.0) or 1.0
        self.atributos_base["EneM"] = self.atributos_base.get("EneM") or ene * 3.0

    def Verificar(self):
        if self.VidaAtual <= 0:
            if self.vivo:
                self.Morrer()
            return False
        if not self.vivo:
            return False
        self.resetar_variacoes_temporarias()
        self.aplicar_efeitos_temporarios()
        if self.partida is not None and hasattr(self.partida, "aplicar_variacoes_temporarias_clima"):
            self.partida.aplicar_variacoes_temporarias_clima(self)
        if self.partida is not None and hasattr(self.partida, "aplicar_variacoes_temporarias_terreno"):
            self.partida.aplicar_variacoes_temporarias_terreno(self)
        self.recalcular_atributos()
        if self.VidaAtual <= 0 and self.vivo:
            self.Morrer()
        return self.vivo

    def recalcular_atributos(self):
        finais = {}
        for chave in ATRIBUTOS_OFICIAIS:
            finais[chave] = _f(self.atributos_base.get(chave, 0.0)) + _f(self.variacoes_permanentes.get(chave, 0.0)) + _f(self.variacoes_temporarias.get(chave, 0.0))
        finais["Vida"] = max(1.0, finais.get("Vida", 1.0))
        finais["EneM"] = max(1.0, finais.get("EneM", 1.0))
        finais["Acu"] = finais.get("Acu") or 100.0
        finais["Ass"] = finais.get("Ass") or 100.0
        finais["Let"] = finais.get("Let", 0.0)
        self.atributos_finais = finais
        if hasattr(self, "VidaAtual"):
            self.VidaAtual = _clamp(self.VidaAtual, 0.0, finais["Vida"])
        if hasattr(self, "EnergiaAtual"):
            if self.possui_efeito("Energizado") or self._reservatorio_ignora_limite_energia():
                self.EnergiaAtual = max(0.0, self.EnergiaAtual)
            elif self._reservatorio_preserva_excedente_energia(finais["EneM"]):
                self.EnergiaAtual = max(0.0, self.EnergiaAtual)
            else:
                self.EnergiaAtual = _clamp(self.EnergiaAtual, 0.0, finais["EneM"])

    def _possui_ataque_code(self, code):
        alvo = str(code or "").strip()
        return bool(alvo) and any(str((ataque or {}).get("Code") or (ataque or {}).get("ID") or "").strip() == alvo for ataque in list(getattr(self, "ataques", []) or []))

    def _reservatorio_ignora_limite_energia(self):
        clima = _normalizar(getattr(getattr(self, "partida", None), "clima_atual", None))
        return clima == "chuva" and self._possui_ataque_code("55")

    def _reservatorio_preserva_excedente_energia(self, limite):
        return self._possui_ataque_code("55") and _f(getattr(self, "EnergiaAtual", 0.0), 0.0) > _f(limite, 1.0)

    def modificar_atributo_permanente(self, alvo, atributo, valor, origem=None, dados=None):
        alvo = alvo or self
        atributo = _atributo_oficial(atributo)
        if atributo not in ATRIBUTOS_OFICIAIS:
            return {"aplicado": False, "motivo": "atributo_invalido"}
        valor = _f(valor, 0.0)
        antes = alvo.obter_atributo(atributo)
        variacao_antes = _f(alvo.variacoes_permanentes.get(atributo), 0.0)
        alvo.variacoes_permanentes[atributo] = variacao_antes + valor
        alvo.recalcular_atributos()
        depois = alvo.obter_atributo(atributo)
        if abs(valor) > 0.001:
            info = dict(dados or {})
            alvo._registrar_evento(
                "pokemon_variou_atributo",
                {
                    "pokemon_id": alvo.id_batalha,
                    "pokemon_nome": alvo.nome,
                    "alvo_id": alvo.id_batalha,
                    "alvo_nome": alvo.nome,
                    **alvo._dados_origem(origem or self),
                    "atributo": atributo,
                    "valor": round(valor, 4),
                    "variacao": round(valor, 4),
                    "valor_antes": round(antes, 4),
                    "valor_depois": round(depois, 4),
                    "variacao_antes": round(variacao_antes, 4),
                    "variacao_total": round(alvo.variacoes_permanentes.get(atributo, 0.0), 4),
                    **info,
                },
            )
        return {"aplicado": True, "atributo": atributo, "valor": valor, "valor_antes": antes, "valor_depois": depois}

    def aplicar_variacao_temporaria(self, atributo, valor):
        atributo = _atributo_oficial(atributo)
        if atributo not in ATRIBUTOS_OFICIAIS:
            return False
        self.variacoes_temporarias[atributo] = _f(self.variacoes_temporarias.get(atributo), 0.0) + _f(valor, 0.0)
        return True

    def resetar_variacoes_temporarias(self):
        for chave in ATRIBUTOS_OFICIAIS:
            self.variacoes_temporarias[chave] = 0.0

    def aplicar_efeitos_temporarios(self):
        for efeito in list(self.efeitos_formais or []):
            nome = _normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
            variacoes = VARIACOES_TEMPORARIAS_EFEITOS.get(nome)
            if not variacoes:
                continue
            for atributo, valor in variacoes.items():
                if abs(valor) < 1.0 and atributo in {"Vel", "Ene", "EneM", "Acu", "Def", "SpD"}:
                    base = self.atributos_base.get(atributo, 0.0)
                    self.aplicar_variacao_temporaria(atributo, base * valor)
                else:
                    self.aplicar_variacao_temporaria(atributo, valor)

    def aplicar_efeitos_por_passo(self):
        if not self.esta_vivo():
            return
        vida = self.obter_atributo("Vida", 1.0)
        faltante = max(0.0, vida - self.VidaAtual)
        for efeito in list(self.efeitos_formais or []):
            nome = _normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
            if nome == "queimado":
                self.ReceberDano(vida * 0.03, dados={"efeito": "Queimado", "ignorar_defensivos": True})
            elif nome == "envenenado":
                self.ReceberDano(vida * 0.02, dados={"efeito": "Envenenado", "ignorar_defensivos": True})
            elif nome == "intoxicado":
                self.ReceberDano(vida * 0.03, dados={"efeito": "Intoxicado", "ignorar_defensivos": True})
            elif nome == "regeneracao":
                self.ReceberCura(faltante * 0.05, dados={"efeito": "Regeneracao"})
            elif nome == "abencoado":
                self.ReceberCura(faltante * 0.03, dados={"efeito": "Abencoado"})
        if self.partida is not None and hasattr(self.partida, "aplicar_clima_em_pokemon_por_passo"):
            self.partida.aplicar_clima_em_pokemon_por_passo(self)
        if self.partida is not None and hasattr(self.partida, "aplicar_terreno_por_passo"):
            self.partida.aplicar_terreno_por_passo(self)

    def obter_atributo(self, chave: str, default: float = 0.0) -> float:
        chave = _atributo_oficial(chave)
        return _f(self.atributos_finais.get(str(chave), default), default)

    def AplicarDano(self, alvo, dados_dano, contexto=None):
        if alvo is None or not alvo.esta_vivo():
            return {"aplicado": False, "motivo": "alvo_invalido", "dano_vida": 0.0}
        contexto = dict(contexto or {})
        dados = dict(dados_dano or {})
        dano = max(0.0, _f(dados.get("dano_bruto", dados.get("dano", 0.0)), 0.0))
        calculo = [f"Dano bruto = {round(dano, 4)}"]
        self._disparar_flag(
            "AntesAplicarDano",
            {
                "partida": self.partida,
                "usuario": self,
                "alvo": alvo,
                "pokemon_evento": self,
                "dados_dano": dados,
                **contexto,
            },
            reativos=contexto.get("reativos_acao"),
        )
        for item in list(dados.get("multiplicadores_condicionais") or []):
            if not isinstance(item, dict):
                continue
            mult = _f(item.get("multiplicador", item.get("valor", 1.0)), 1.0)
            if abs(mult - 1.0) <= 0.001:
                continue
            antes = dano
            dano *= mult
            label = "Multiplicador Condicional"
            calculo.append(f"{label}: {round(antes, 4)} * {round(mult, 4)} = {round(dano, 4)}")
        for item in list(dados.get("ajustes_condicionais") or []):
            if not isinstance(item, dict):
                continue
            valor = _f(item.get("valor"), 0.0)
            if abs(valor) <= 0.001:
                continue
            antes = dano
            op = str(item.get("op") or "add").strip().lower()
            dano = max(0.0, dano - valor) if op in {"sub", "subtract", "-"} else max(0.0, dano + valor)
            sinal = "-" if op in {"sub", "subtract", "-"} else "+"
            label = "Ajuste Condicional"
            calculo.append(f"{label}: {round(antes, 4)} {sinal} {round(valor, 4)} = {round(dano, 4)}")
        dano_pos_condicional = dano
        tipo = dados.get("tipo") or contexto.get("tipo_ataque") or "normal"
        categoria = _normalizar(dados.get("categoria") or "normal")
        if self.partida is not None and hasattr(self.partida, "aplicar_modificadores_dano_clima"):
            antes = dano
            dano, mult_clima = self.partida.aplicar_modificadores_dano_clima(tipo, dano)
            if abs(mult_clima - 1.0) > 0.001:
                calculo.append(f"Clima: {round(antes, 4)} * {round(mult_clima, 4)} = {round(dano, 4)}")
        mult_amp = 1.0 + (self.obter_atributo("Amp") / 100.0)
        if abs(mult_amp - 1.0) > 0.001:
            antes = dano
            dano *= mult_amp
            calculo.append(f"Amplificacao: {round(antes, 4)} * {round(mult_amp, 4)} = {round(dano, 4)}")
        mult_tipo = obter_multiplicador(tipo, alvo.tipos)
        if abs(mult_tipo - 1.0) > 0.001:
            antes = dano
            dano *= mult_tipo
            calculo.append(f"Tipo: {round(antes, 4)} * {round(mult_tipo, 4)} = {round(dano, 4)}")
        if _normalizar(tipo) in {_normalizar(t) for t in self.tipos}:
            antes = dano
            dano *= 1.20
            calculo.append(f"STAB: {round(antes, 4)} * 1.2 = {round(dano, 4)}")
        rng = contexto.get("rng") or getattr(getattr(self, "partida", None), "rng", None)
        chance_crit_bruta = _f(dados.get("chance_critico", self.obter_atributo("CrC")), 0.0) + _f(dados.get("bonus_critico_acerto", contexto.get("bonus_critico_acerto", 0.0)), 0.0)
        chance_crit_bruta = min(chance_crit_bruta, _f(dados.get("chance_critico_max", 999.0), 999.0))
        excedente_crit = max(0.0, chance_crit_bruta - 100.0)
        chance_crit = _clamp(chance_crit_bruta, 0.0, 100.0)
        critico = False
        if not self.possui_efeito("Cauterizado") and chance_crit > 0:
            sorte = rng.random() * 100.0 if rng is not None else 100.0
            critico = sorte <= chance_crit
        if critico:
            crd_contexto = self.obter_atributo("CrD") + (excedente_crit / 2.0)
            mult_crit = 1.0 + (crd_contexto / 100.0)
            antes = dano
            dano *= mult_crit
            calculo.append(f"Critico: {round(antes, 4)} * {round(mult_crit, 4)} = {round(dano, 4)}")
        defesa_chave = "SpD" if categoria in {"especial", "spa", "magico"} else "Def"
        defesa = alvo.obter_atributo(defesa_chave)
        ignora_defesa = bool(dados.get("ignorar_defesa") or dados.get("ignora_defesa"))
        defesa_efetiva = 0.0 if ignora_defesa else max(0.0, defesa - (self.obter_atributo("Per") / 2.0))
        calculo.append(f"Defesa bruta ({defesa_chave}) = {round(defesa, 4)}")
        if ignora_defesa:
            calculo.append("Defesa ignorada = 0")
        elif self.obter_atributo("Per") > 0:
            calculo.append(f"Defesa apos perfuracao = {round(defesa, 4)} - {round(self.obter_atributo('Per') / 2.0, 4)} = {round(defesa_efetiva, 4)}")
        mult_defesa = 100.0 / (100.0 + defesa_efetiva)
        antes = dano
        dano *= mult_defesa
        calculo.append(f"Defesa: {round(antes, 4)} * {round(mult_defesa, 4)} = {round(dano, 4)}")
        dur_alvo = alvo.obter_atributo("Dur")
        if dur_alvo > 0:
            antes = dano
            mult_dur = max(0.0, 1.0 - (dur_alvo / 100.0))
            dano *= mult_dur
            calculo.append(f"Durabilidade: {round(antes, 4)} * {round(mult_dur, 4)} = {round(dano, 4)}")
        calculo.append(f"Dano final = {round(dano, 4)}")
        detalhes = {
            "dano_bruto": round(_f(dados.get("dano_bruto", dados.get("dano", 0.0)), 0.0), 4),
            "dano_pos_condicional": round(dano_pos_condicional, 4),
            "multiplicador_amp": round(mult_amp, 4),
            "multiplicador_tipo": round(mult_tipo, 4),
            "multiplicador_stab": 1.2 if _normalizar(tipo) in {_normalizar(t) for t in self.tipos} else 1.0,
            "multiplicador_critico": round(1.0 + (self.obter_atributo("CrD") / 100.0), 4) if critico else 1.0,
            "chance_critico": round(chance_crit, 4),
            "bonus_crd_excedente": round(excedente_crit / 2.0, 4),
            "defesa_base": round(defesa, 4),
            "defesa_aplicada": round(defesa_efetiva, 4),
            "ignora_defesa": ignora_defesa,
            "multiplicador_defesa": round(mult_defesa, 4),
            "durabilidade": round(dur_alvo, 4),
            "multiplicador_durabilidade": round(max(0.0, 1.0 - (dur_alvo / 100.0)), 4),
        }
        recebido = alvo.ReceberDano(dano, origem=self, dados={**dados, "critico": critico, "tipo": tipo, "detalhes": detalhes, "calculo": calculo})
        dano_vida = _f(recebido.get("dano_vida"), 0.0)
        if dano_vida > 0 and self.obter_atributo("Vamp") > 0:
            self.ReceberCura(dano_vida * (self.obter_atributo("Vamp") / 100.0), origem=self, dados={"vampirismo": True})
        self.estatisticas_batalha["dano_causado"] = _f(self.estatisticas_batalha.get("dano_causado"), 0.0) + dano_vida
        recebido.update({"critico": critico, "dano_calculado": round(dano, 4)})
        self._disparar_flag(
            "AoAplicarDano",
            {"partida": self.partida, "usuario": self, "alvo": alvo, "pokemon_evento": self, "resultado": dict(recebido), "dados_dano": dict(dados), **contexto},
            reativos=contexto.get("reativos_acao"),
        )
        return recebido

    def _aplicar_letalidade(self, origem, dano_vida: float, dados=None) -> bool:
        if dano_vida <= 0 or origem is None or origem is self or self.VidaAtual <= 0:
            return False
        let = max(0.0, origem.obter_atributo("Let", 0.0) if hasattr(origem, "obter_atributo") else 0.0)
        vida_max = max(1.0, self.obter_atributo("Vida", 1.0))
        if let <= 0 or self.VidaAtual > vida_max * (let / 100.0):
            return False
        self.Morrer({"origem_id": getattr(origem, "id_batalha", None), "origem": origem, "letalidade": True, **dict(dados or {})})
        return True

    def ReceberDano(self, valor, origem=None, dados=None):
        dados = dict(dados or {})
        if not self.esta_vivo():
            return {"aplicado": False, "motivo": "morto", "dano_vida": 0.0, "dano_barreira": 0.0}
        dano = max(0.0, _f(valor, 0.0))
        dano_original_defensivo = dano
        if not bool(dados.get("ignorar_defensivos")):
            if self.possui_efeito("Evasivo"):
                self.RemoverEfeito("Evasivo")
                self._registrar_evento(
                    "evasivo_consumido",
                    {
                        "pokemon_id": self.id_batalha,
                        "pokemon_nome": self.nome,
                        **self._dados_origem(origem),
                        "dano_original": round(dano, 4),
                    },
                )
                return {"aplicado": True, "evasivo": True, "dano_vida": 0.0, "dano_barreira": 0.0}
            if self.possui_efeito("Preparado"):
                dano = dano_original_defensivo * 0.40
                percentual_devolucao = max(0.0, self.obter_atributo("Vel", 0.0) * 0.40) / 100.0
                retorno = dano_original_defensivo * percentual_devolucao
                self._registrar_evento(
                    "preparado_ativou",
                    {
                        "pokemon_id": self.id_batalha,
                        "pokemon_nome": self.nome,
                        **self._dados_origem(origem),
                        "dano_original": round(dano_original_defensivo, 4),
                        "dano_reduzido": round(dano, 4),
                        "percentual_devolucao": round(percentual_devolucao * 100.0, 4),
                        "dano_retorno": round(retorno, 4),
                    },
                )
                if origem is not None and origem is not self and retorno > 0:
                    origem.ReceberDano(retorno, origem=self, dados={"efeito": "Preparado", "ignorar_defensivos": True})
            elif self.possui_efeito("Refletindo"):
                dano = dano_original_defensivo * 0.35
                retorno = dano_original_defensivo * 0.70
                self._registrar_evento(
                    "refletindo_ativou",
                    {
                        "pokemon_id": self.id_batalha,
                        "pokemon_nome": self.nome,
                        **self._dados_origem(origem),
                        "dano_original": round(dano_original_defensivo, 4),
                        "dano_reduzido": round(dano, 4),
                        "dano_refletido": round(retorno, 4),
                    },
                )
                if origem is not None and origem is not self and retorno > 0:
                    origem.ReceberDano(retorno, origem=self, dados={"efeito": "Refletindo", "ignorar_defensivos": True})
        if self.estados_transitorios.get("protegido"):
            self.estados_transitorios.pop("protegido", None)
            self._registrar_evento(
                "barreira_absorveu",
                {
                    "alvo_id": self.id_batalha,
                    "alvo_nome": self.nome,
                    **self._dados_origem(origem),
                    "dano_original": round(dano, 4),
                    "dano_barreira": round(dano, 4),
                    "barreira_antes": self.BarreiraAtual,
                    "barreira_depois": self.BarreiraAtual,
                    "protegido": True,
                    "critico": bool(dados.get("critico", False)),
                    "ataque_id": dados.get("ataque_id") or dados.get("Code"),
                    "ataque_nome": dados.get("ataque_nome") or dados.get("ataque"),
                    "alvo_principal_id": dados.get("alvo_principal_id"),
                    "alvos_secundarios_ids": list(dados.get("alvos_secundarios_ids") or []),
                    "impacto_principal": bool(dados.get("impacto_principal", False)),
                    "impacto_secundario": bool(dados.get("impacto_secundario", False)),
                    "detalhes": dict(dados.get("detalhes") or {}),
                    "calculo": list(dados.get("calculo") or []),
                },
            )
            return {"aplicado": True, "protegido": True, "dano_vida": 0.0, "dano_barreira": 0.0}
        if self.BarreiraAtual > 0:
            antes_barreira = self.BarreiraAtual
            absorvido = min(self.BarreiraAtual, dano)
            self.BarreiraAtual = max(0.0, self.BarreiraAtual - absorvido)
            self._registrar_evento(
                "barreira_absorveu",
                {
                    "alvo_id": self.id_batalha,
                    "alvo_nome": self.nome,
                    **self._dados_origem(origem),
                    "dano_original": round(dano, 4),
                    "dano_barreira": round(absorvido, 4),
                    "barreira_antes": round(antes_barreira, 4),
                    "barreira_depois": round(self.BarreiraAtual, 4),
                    "critico": bool(dados.get("critico", False)),
                    "tipo": dados.get("tipo"),
                    "categoria": dados.get("categoria"),
                    "ataque_id": dados.get("ataque_id") or dados.get("Code"),
                    "ataque_nome": dados.get("ataque_nome") or dados.get("ataque"),
                    "alvo_principal_id": dados.get("alvo_principal_id"),
                    "alvos_secundarios_ids": list(dados.get("alvos_secundarios_ids") or []),
                    "impacto_principal": bool(dados.get("impacto_principal", False)),
                    "impacto_secundario": bool(dados.get("impacto_secundario", False)),
                    "detalhes": dict(dados.get("detalhes") or {}),
                    "calculo": list(dados.get("calculo") or []),
                },
            )
            return {"aplicado": True, "dano_vida": 0.0, "dano_barreira": round(absorvido, 4), "barreira_absorveu_instancia": True}
        antes = self.VidaAtual
        self.VidaAtual = max(0.0, self.VidaAtual - dano)
        dano_vida = max(0.0, antes - self.VidaAtual)
        self.estatisticas_batalha["dano_recebido"] = _f(self.estatisticas_batalha.get("dano_recebido"), 0.0) + dano_vida
        deve_registrar_zero = dano <= 0.001 and (dados.get("ataque_id") is not None or dados.get("ataque_nome") or dados.get("ataque"))
        if dano_vida > 0 or deve_registrar_zero:
            self._registrar_evento(
                "pokemon_sofreu_dano",
                {
                    "alvo_id": self.id_batalha,
                    "alvo_nome": self.nome,
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    **self._dados_origem(origem),
                    "valor": round(dano_vida, 4),
                    "vida_antes": round(antes, 4),
                    "vida_depois": round(self.VidaAtual, 4),
                    "critico": bool(dados.get("critico", False)),
                    "tipo": dados.get("tipo"),
                    "categoria": dados.get("categoria"),
                    "ataque_id": dados.get("ataque_id") or dados.get("Code"),
                    "ataque_nome": dados.get("ataque_nome") or dados.get("ataque"),
                    "alvo_principal_id": dados.get("alvo_principal_id"),
                    "alvos_secundarios_ids": list(dados.get("alvos_secundarios_ids") or []),
                    "impacto_principal": bool(dados.get("impacto_principal", False)),
                    "impacto_secundario": bool(dados.get("impacto_secundario", False)),
                    "dano_barreira": round(_f(dados.get("dano_barreira"), 0.0), 4),
                    "detalhes": dict(dados.get("detalhes") or {}),
                    "calculo": list(dados.get("calculo") or []),
                },
            )
        letalidade = self._aplicar_letalidade(origem, dano_vida, dados)
        if self.VidaAtual <= 0 and self.vivo:
            self.Morrer({"origem_id": getattr(origem, "id_batalha", None), **dados})
        retorno = {"aplicado": True, "dano_vida": round(dano_vida, 4), "dano_barreira": 0.0}
        if letalidade:
            retorno["letalidade"] = True
        if dano_vida > 0 and self.possui_efeito("Dormindo"):
            self.RemoverEfeito("Dormindo")
            self._registrar_evento("pokemon_removeu_efeito", {"pokemon_id": self.id_batalha, "pokemon_nome": self.nome, "efeito_nome": "Dormindo", "motivo": "dano_real"})
        if dano_vida > 0 and self.possui_efeito("Vampirico") and origem is not None and origem is not self and int(getattr(origem, "lado_id", -1)) != int(getattr(self, "lado_id", -1)):
            cura = dano_vida * 0.25
            origem.ReceberCura(cura, origem=self, dados={"efeito": "Vampirico", "motivo": "defensor_vampirico"})
            self._registrar_evento(
                "vampirico_curou_atacante",
                {
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    "atacante_id": getattr(origem, "id_batalha", None),
                    "atacante_nome": getattr(origem, "nome", None),
                    "dano_vida": round(dano_vida, 4),
                    "cura": round(cura, 4),
                },
            )
        if dano_vida > 0:
            self._disparar_flag(
                "AoReceberDano",
                {
                    "partida": self.partida,
                    "usuario": origem,
                    "origem": origem,
                    "alvo": self,
                    "pokemon_evento": self,
                    "dano_vida": round(dano_vida, 4),
                    "resultado": dict(retorno),
                    "dados_dano": dict(dados),
                    "reativos_acao": dados.get("reativos_acao"),
                },
                reativos=dados.get("reativos_acao"),
            )
        return retorno

    def AplicarCura(self, alvo, valor, dados=None):
        retorno = alvo.ReceberCura(valor, origem=self, dados=dados) if alvo is not None else {"aplicado": False}
        valor_cura = _f((retorno or {}).get("cura"), 0.0)
        if valor_cura > 0:
            self._disparar_flag(
                "AoCurar",
                {"partida": self.partida, "usuario": self, "alvo": alvo, "pokemon_evento": self, "valor_cura": round(valor_cura, 4), "resultado": dict(retorno)},
                reativos=(dados or {}).get("reativos_acao"),
            )
        return retorno

    def ReceberCura(self, valor, origem=None, dados=None):
        dados = dict(dados or {})
        if not self.esta_vivo():
            return {"aplicado": False, "motivo": "morto", "cura": 0.0}
        cura = max(0.0, _f(valor, 0.0))
        calculo = [f"Cura bruta = {round(cura, 4)}"]
        for item in list(dados.get("multiplicadores_condicionais") or []):
            if not isinstance(item, dict):
                continue
            mult = _f(item.get("multiplicador", item.get("valor", 1.0)), 1.0)
            if abs(mult - 1.0) <= 0.001:
                continue
            antes_calc = cura
            cura *= mult
            label = "Multiplicador Condicional"
            calculo.append(f"{label}: {round(antes_calc, 4)} * {round(mult, 4)} = {round(cura, 4)}")
        for item in list(dados.get("ajustes_condicionais") or []):
            if not isinstance(item, dict):
                continue
            valor_ajuste = _f(item.get("valor"), 0.0)
            if abs(valor_ajuste) <= 0.001:
                continue
            antes_calc = cura
            op = str(item.get("op") or "add").strip().lower()
            cura = max(0.0, cura - valor_ajuste) if op in {"sub", "subtract", "-"} else max(0.0, cura + valor_ajuste)
            sinal = "-" if op in {"sub", "subtract", "-"} else "+"
            label = "Ajuste Condicional"
            calculo.append(f"{label}: {round(antes_calc, 4)} {sinal} {round(valor_ajuste, 4)} = {round(cura, 4)}")
        if self.possui_efeito("Queimado"):
            antes_calc = cura
            cura *= 0.65
            calculo.append(f"Queimado: {round(antes_calc, 4)} * 0.65 = {round(cura, 4)}")
        if self.possui_efeito("Abencoado"):
            antes_calc = cura
            cura *= 1.35
            calculo.append(f"Abencoado: {round(antes_calc, 4)} * 1.35 = {round(cura, 4)}")
        terreno = None
        if self.partida is not None and hasattr(self.partida, "obter_terreno_area"):
            terreno = _normalizar(self.partida.obter_terreno_area(getattr(self, "area_id", None)))
        if terreno == "incendiada":
            antes_calc = cura
            cura *= 0.50
            calculo.append(f"Terreno Incendiada: {round(antes_calc, 4)} * 0.5 = {round(cura, 4)}")
        elif terreno == "abencoada":
            antes_calc = cura
            cura *= 1.50
            calculo.append(f"Terreno Abencoada: {round(antes_calc, 4)} * 1.5 = {round(cura, 4)}")
        antes = self.VidaAtual
        self.VidaAtual = min(self.obter_atributo("Vida", 1.0), self.VidaAtual + cura)
        real = max(0.0, self.VidaAtual - antes)
        excedente = max(0.0, cura - real)
        if excedente > 0.001:
            calculo.append(f"Excedente = {round(excedente, 4)}")
        calculo.append(f"Cura final = {round(real, 4)}")
        self.estatisticas_batalha["cura_recebida"] = _f(self.estatisticas_batalha.get("cura_recebida"), 0.0) + real
        if origem is not None:
            origem.estatisticas_batalha["cura_feita"] = _f(origem.estatisticas_batalha.get("cura_feita"), 0.0) + real
        deve_registrar_zero = real <= 0.001 and cura > 0.001 and (dados.get("ataque_id") is not None or dados.get("ataque_nome") or dados.get("ataque"))
        if real > 0 or deve_registrar_zero:
            self._registrar_evento(
                "pokemon_recebeu_cura",
                {
                    "alvo_id": self.id_batalha,
                    "alvo_nome": self.nome,
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    **self._dados_origem(origem),
                    "valor": round(real, 4),
                    "cura_bruta": round(max(0.0, _f(valor, 0.0)), 4),
                    "cura_calculada": round(cura, 4),
                    "excedente": round(excedente, 4),
                    "vida_antes": round(antes, 4),
                    "vida_depois": round(self.VidaAtual, 4),
                    "critico": bool(dados.get("critico", False)),
                    "ataque_id": dados.get("ataque_id") or dados.get("Code"),
                    "ataque_nome": dados.get("ataque_nome") or dados.get("ataque"),
                    "calculo": list(dados.get("calculo") or calculo),
                },
            )
        retorno = {"aplicado": True, "cura": round(real, 4), "dados": dict(dados or {})}
        if real > 0:
            self._disparar_flag(
                "AoReceberCura",
                {"partida": self.partida, "usuario": origem, "origem": origem, "alvo": self, "pokemon_evento": self, "valor_cura": round(real, 4), "resultado": dict(retorno)},
                reativos=(dados or {}).get("reativos_acao"),
            )
        return retorno

    def AplicarBarreira(self, alvo, valor, dados=None):
        return alvo.ReceberBarreira(valor, origem=self, dados=dados) if alvo is not None else {"aplicado": False}

    def ReceberBarreira(self, valor, origem=None, dados=None):
        dados = dict(dados or {})
        ganho = max(0.0, _f(valor, 0.0))
        antes = self.BarreiraAtual
        self.BarreiraAtual += ganho
        calculo = list(dados.get("calculo") or [f"Barreira bruta = {round(ganho, 4)}", f"Barreira final = {round(ganho, 4)}"])
        self._registrar_evento(
            "pokemon_ganhou_barreira",
            {
                "alvo_id": self.id_batalha,
                "alvo_nome": self.nome,
                "pokemon_id": self.id_batalha,
                "pokemon_nome": self.nome,
                **self._dados_origem(origem),
                "valor": round(ganho, 4),
                "barreira_antes": round(antes, 4),
                "barreira_depois": round(self.BarreiraAtual, 4),
                "critico": bool(dados.get("critico", False)),
                "ataque_id": dados.get("ataque_id") or dados.get("Code"),
                "ataque_nome": dados.get("ataque_nome") or dados.get("ataque"),
                "calculo": calculo,
            },
        )
        return {"aplicado": True, "barreira": round(ganho, 4), "dados": dict(dados or {})}

    def AplicarEfeito(self, alvo, efeito, dados=None):
        retorno = alvo.ReceberEfeito(efeito, origem=self, dados=dados) if alvo is not None else {"aplicado": False}
        if bool(retorno.get("aplicado")):
            efeito_final = dict(retorno.get("efeito") or efeito or {})
            negativo = str(efeito_final.get("tipo") or "").lower() == "negativo" or bool(efeito_final.get("negativo"))
            self._disparar_flag(
                "AoAplicarEfeito",
                {
                    "partida": self.partida,
                    "usuario": self,
                    "origem": self,
                    "alvo": alvo,
                    "pokemon_evento": self,
                    "efeito": efeito_final,
                    "positivo": not negativo,
                    "negativo": negativo,
                    "resultado": dict(retorno),
                },
                reativos=(dados or {}).get("reativos_acao"),
            )
        return retorno

    def ReceberEfeito(self, efeito, origem=None, dados=None):
        if not self.esta_vivo():
            return {"aplicado": False, "motivo": "morto"}
        base = dict(efeito or {})
        nome = str(base.get("nome") or base.get("Nome") or base.get("code") or "").strip()
        if not nome:
            return {"aplicado": False, "motivo": "efeito_sem_nome"}
        duracao_base = max(1, _i(base.get("duracao", base.get("passos", base.get("passos_restantes", 3))), 3))
        nome_norm = _normalizar(nome)
        negativo = bool(base.get("negativo", nome_norm in EFEITOS_NEGATIVOS))
        base_dados = base.get("dados") if isinstance(base.get("dados"), dict) else {}
        dados_recebidos = dados if isinstance(dados, dict) else {}
        permanente = bool(base.get("permanente") or base_dados.get("permanente") or dados_recebidos.get("permanente"))
        if negativo and self.possui_efeito("Imune"):
            self._registrar_evento(
                "efeito_bloqueado_por_imunidade",
                {
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    "efeito_nome": nome,
                    "efeito_code": base.get("code", nome),
                    "bloqueador_nome": "Imune",
                    "bloqueador_code": "Imune",
                    **self._dados_origem(origem),
                },
            )
            return {"aplicado": False, "motivo": "imune"}
        if (not negativo) and self.possui_efeito("Bloqueado"):
            self._registrar_evento(
                "efeito_bloqueado_por_bloqueado",
                {
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    "efeito_nome": nome,
                    "efeito_code": base.get("code", nome),
                    "bloqueador_nome": "Bloqueado",
                    "bloqueador_code": "Bloqueado",
                    **self._dados_origem(origem),
                },
            )
            return {"aplicado": False, "motivo": "bloqueado"}
        mag_origem = origem.obter_atributo("Mag") if origem is not None and hasattr(origem, "obter_atributo") else 0.0
        mag_alvo = self.obter_atributo("Mag")
        if negativo and origem is self:
            duracao = duracao_base
        elif negativo:
            duracao = max(math.ceil(duracao_base / 2.0), int(round(duracao_base + mag_origem / 5.0 - mag_alvo / 5.0)))
        else:
            duracao = int(round(duracao_base + mag_origem / 5.0))
        duracao_antes_modificadores = max(1, int(duracao))
        if negativo and self.possui_efeito("Amaldicoado"):
            duracao = math.ceil(duracao * 1.5)
        if (not negativo) and self.possui_efeito("Encantado"):
            duracao = math.ceil(duracao * 1.5)
        if negativo and self.partida is not None and hasattr(self.partida, "obter_terreno_area") and _normalizar(self.partida.obter_terreno_area(getattr(self, "area_id", None))) == "amaldicoada":
            duracao = math.ceil(duracao * 2.0)
        formal = {
            "nome": nome,
            "code": base.get("code", nome),
            "passos_restantes": -1 if permanente else max(1, int(duracao)),
            "passos_totais": -1 if permanente else max(1, int(duracao)),
            "dados": dict(dados or base.get("dados") or {}),
            "valor": 0.0,
            "stacks": 1,
            "tipo": "negativo" if negativo else "positivo",
            "permanente": permanente,
        }
        chave = _normalizar(formal.get("code") or formal.get("nome"))
        existente = next((e for e in self.efeitos_formais if _normalizar((e or {}).get("code") or (e or {}).get("nome")) == chave), None)
        if existente is not None:
            if bool(existente.get("permanente")) or permanente:
                existente["permanente"] = True
                existente["passos_restantes"] = -1
                existente["passos_totais"] = -1
                existente["dados"] = {**dict(existente.get("dados") or {}), **dict(formal.get("dados") or {})}
                formal = dict(existente)
                self.recalcular_atributos()
                retorno = {"aplicado": True, "efeito": dict(formal), "ja_existia": True}
                self._disparar_flag(
                    "AoReceberEfeito",
                    {
                        "partida": self.partida,
                        "usuario": origem,
                        "origem": origem,
                        "alvo": self,
                        "pokemon_evento": self,
                        "efeito": dict(formal),
                        "duracao": formal.get("passos_restantes"),
                        "resultado": dict(retorno),
                    },
                    reativos=(dados or {}).get("reativos_acao") if isinstance(dados, dict) else None,
                )
                return retorno
            passos_anteriores = max(0, _i(existente.get("passos_restantes"), 0))
            passos_novos = max(1, _i(formal.get("passos_restantes"), 1))
            existente["stacks"] = 1
            existente["passos_restantes"] = passos_anteriores + passos_novos
            existente["passos_totais"] = max(_i(existente.get("passos_totais"), 0), passos_anteriores) + passos_novos
            existente["valor"] = formal.get("valor", existente.get("valor", 0.0))
            existente["dados"] = {**dict(existente.get("dados") or {}), **dict(formal.get("dados") or {})}
            existente["tipo"] = formal["tipo"]
            formal = dict(existente)
            formal["duracao_antes_soma"] = passos_anteriores
        else:
            efeitos_temporarios = [e for e in self.efeitos_formais if not bool((e or {}).get("permanente"))]
            if (not permanente) and len(efeitos_temporarios) >= 4:
                aviso = {"pokemon_id": self.id_batalha, "efeito": nome, "motivo": "limite_efeitos_formais"}
                if self.partida is not None:
                    self.partida.avisos.append(aviso)
                self._registrar_evento(
                    "efeito_bloqueado_por_limite",
                    {
                        "pokemon_id": self.id_batalha,
                        "pokemon_nome": self.nome,
                        "efeito_nome": nome,
                        "efeito_code": base.get("code", nome),
                        **self._dados_origem(origem),
                    },
                )
                return {"aplicado": False, "motivo": "limite_efeitos_formais", "aviso": aviso}
            self.efeitos_formais.append(formal)
        self.recalcular_atributos()
        self._registrar_evento(
            "pokemon_recebeu_efeito",
            {
                "pokemon_id": self.id_batalha,
                "pokemon_nome": self.nome,
                "efeito_nome": formal.get("nome"),
                "efeito_code": formal.get("code"),
                "tipo": "negativo" if negativo else "positivo",
                "passos_restantes": formal.get("passos_restantes"),
                "passos_totais": formal.get("passos_totais"),
                "duracao_base": duracao_base,
                "duracao_antes_modificadores": duracao_antes_modificadores,
                "duracao_antes_soma": formal.get("duracao_antes_soma"),
                "stacks": formal.get("stacks", 1),
                **self._dados_origem(origem),
                "efeito": dict(formal),
            },
        )
        retorno = {"aplicado": True, "efeito": dict(formal)}
        self._disparar_flag(
            "AoReceberEfeito",
            {
                "partida": self.partida,
                "usuario": origem,
                "origem": origem,
                "alvo": self,
                "pokemon_evento": self,
                "efeito": dict(formal),
                "duracao": formal.get("passos_restantes"),
                "resultado": dict(retorno),
            },
            reativos=(dados or {}).get("reativos_acao") if isinstance(dados, dict) else None,
        )
        return retorno

    def RemoverEfeito(self, filtro):
        alvo = _normalizar(filtro)
        antes = len(self.efeitos_formais)
        self.efeitos_formais = [e for e in self.efeitos_formais if _normalizar((e or {}).get("nome") or (e or {}).get("code")) != alvo]
        self.recalcular_atributos()
        return antes - len(self.efeitos_formais)

    def _decremento_efeito_por_passo(self, nome):
        clima = _normalizar(getattr(self.partida, "clima_atual", None)) if self.partida is not None else ""
        terreno = _normalizar(self.partida.obter_terreno_area(getattr(self, "area_id", None))) if self.partida is not None and hasattr(self.partida, "obter_terreno_area") else ""
        if clima == "chuva" and nome == "encharcado":
            return 0
        if clima == "chuva" and nome == "queimado":
            return 3
        if clima == "solforte" and nome == "queimado":
            return 0
        if clima == "solforte" and nome == "encharcado":
            return 3
        if clima == "chuvaacida" and nome in {"envenenado", "intoxicado"}:
            return 0
        if terreno == "contaminada" and nome == "envenenado":
            return 0
        return 1

    def decrementar_efeitos(self, passo_atual):
        restantes = []
        for efeito in self.efeitos_formais:
            nome = _normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
            duracao_antes = _i((efeito or {}).get("passos_restantes"), 1)
            efeito = dict(efeito)
            if bool(efeito.get("permanente")):
                restantes.append(efeito)
                continue
            decremento = self._decremento_efeito_por_passo(nome)
            efeito["passos_restantes"] = duracao_antes - decremento
            self._registrar_evento(
                "efeito_tickou",
                {
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    "efeito_nome": efeito.get("nome"),
                    "efeito_code": efeito.get("code"),
                    "passos_antes": duracao_antes,
                    "passos_depois": efeito["passos_restantes"],
                    "decremento": decremento,
                    "passos_totais": efeito.get("passos_totais", duracao_antes),
                    "passo": passo_atual,
                },
            )
            if efeito["passos_restantes"] > 0 and self.esta_vivo():
                restantes.append(efeito)
            else:
                self._registrar_evento(
                    "efeito_expirou",
                    {
                        "pokemon_id": self.id_batalha,
                        "pokemon_nome": self.nome,
                        "efeito_nome": efeito.get("nome"),
                        "efeito_code": efeito.get("code"),
                    },
                )
        self.efeitos_formais = restantes
        self.recalcular_atributos()

    def GastarEnergia(self, valor, dados=None):
        custo = max(0.0, _f(valor, 0.0))
        if self.EnergiaAtual < custo:
            return {"aplicado": False, "motivo": "energia_insuficiente", "energia_antes": round(self.EnergiaAtual, 4), "energia_depois": round(self.EnergiaAtual, 4)}
        antes = self.EnergiaAtual
        self.EnergiaAtual = max(0.0, self.EnergiaAtual - custo)
        self.estatisticas_batalha["energia_gasta"] = _f(self.estatisticas_batalha.get("energia_gasta"), 0.0) + custo
        return {"aplicado": True, "valor": round(custo, 4), "energia_antes": round(antes, 4), "energia_depois": round(self.EnergiaAtual, 4), "dados": dict(dados or {})}

    def GanharEnergia(self, valor, dados=None):
        dados = dict(dados or {})
        ganho = max(0.0, _f(valor, 0.0))
        antes = self.EnergiaAtual
        if self.possui_efeito("Energizado") or self._reservatorio_ignora_limite_energia():
            self.EnergiaAtual = max(0.0, self.EnergiaAtual + ganho)
        elif self._reservatorio_preserva_excedente_energia(self.obter_atributo("EneM", 1.0)):
            self.EnergiaAtual = max(0.0, self.EnergiaAtual)
        else:
            self.EnergiaAtual = min(self.obter_atributo("EneM", 1.0), self.EnergiaAtual + ganho)
        real = max(0.0, self.EnergiaAtual - antes)
        if real > 0:
            self._registrar_evento(
                "pokemon_ganhou_energia",
                {
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    "valor": round(real, 4),
                    "energia_antes": round(antes, 4),
                    "energia_depois": round(self.EnergiaAtual, 4),
                    "motivo": dados.get("motivo") or ("fim_rodada" if dados.get("fim_rodada") else dados.get("ataque")),
                },
            )
        retorno = {"aplicado": True, "energia": round(ganho, 4), "dados": dict(dados or {})}
        self._disparar_flag("AoGanharEnergia", {"partida": self.partida, "usuario": self, "alvo": self, "pokemon_evento": self, "resultado": dict(retorno)}, reativos=(dados or {}).get("reativos_acao"))
        return retorno

    def Mover(self, area_id, dados=None):
        if self.partida is None:
            self.area_id = area_id
            self.ativo = True
            self.reserva = False
            return True
        return self.partida.mover_pokemon_para_area(self, area_id, dados=dados)

    def TrocarComReserva(self, pokemon_reserva, dados=None):
        return self.partida.trocar_reserva(self, pokemon_reserva, dados=dados) if self.partida is not None else False

    def TrocarPosicao(self, outro_pokemon, dados=None):
        return self.partida.trocar_posicao(self, outro_pokemon, dados=dados) if self.partida is not None else False

    def Morrer(self, dados=None):
        if not self.vivo and self.VidaAtual <= 0:
            return False
        dados = dict(dados or {})
        self.vivo = False
        self.VidaAtual = 0.0
        self.estados_transitorios["morto_na_rodada"] = dict(dados or {})
        origem_id = dados.get("origem_id")
        origem = dados.get("origem")
        if origem is None:
            origem = self.partida.obter_pokemon(origem_id) if self.partida is not None and origem_id is not None else None
        if origem is not None and origem.id_batalha != self.id_batalha:
            origem.estatisticas_batalha["abates"] = _f(origem.estatisticas_batalha.get("abates"), 0.0) + 1
        self._registrar_evento(
            "pokemon_morreu",
            {
                "pokemon_id": self.id_batalha,
                "pokemon_nome": self.nome,
                "origem_id": origem_id,
                "ataque_nome": dados.get("ataque_nome") or dados.get("ataque"),
                "area_id": self.area_id,
            },
        )
        if origem is not None and origem.id_batalha != self.id_batalha:
            self._disparar_flag("AoMatar", {"partida": self.partida, "usuario": origem, "alvo": self, "pokemon_evento": origem, "dados": dict(dados)}, reativos=dados.get("reativos_acao"))
            self._disparar_flag("AoAbater", {"partida": self.partida, "usuario": origem, "origem": origem, "alvo": self, "pokemon_evento": origem, "dados": dict(dados)}, reativos=dados.get("reativos_acao"))
        self._disparar_flag("AoMorrer", {"partida": self.partida, "usuario": origem, "origem": origem, "alvo": self, "pokemon_evento": self, "dados": dict(dados)}, reativos=dados.get("reativos_acao"))
        return True

    def esta_vivo(self):
        return bool(self.vivo) and self.VidaAtual > 0

    def esta_apto_para_agir(self):
        if not self.esta_vivo():
            return False
        bloqueios = {"dormindo", "congelado"}
        return not any(self.possui_efeito(nome) for nome in bloqueios)

    def pode_ser_movido_por_ataque(self):
        return not self.possui_efeito("Imparavel")

    def receber_recuo(self, origem=None, dados=None):
        dados = dict(dados or {})
        if not self.pode_ser_movido_por_ataque():
            self._registrar_evento(
                "recuo_bloqueado_por_imparavel",
                {
                    "pokemon_id": self.id_batalha,
                    "pokemon_nome": self.nome,
                    "bloqueador_nome": "Imparavel",
                    "bloqueador_code": "Imparavel",
                    **self._dados_origem(origem),
                    **dados,
                },
            )
            return {"aplicado": False, "motivo": "imparavel"}
        self.adicionar_estado_transitorio("recuado", dados or {"ativo": True})
        self._registrar_evento(
            "pokemon_recuou",
            {
                "pokemon_id": self.id_batalha,
                "pokemon_nome": self.nome,
                **self._dados_origem(origem),
                **dados,
            },
        )
        return {"aplicado": True, "estado": "recuado"}

    def possui_efeito(self, nome_ou_code):
        alvo = _normalizar(nome_ou_code)
        return any(_normalizar((e or {}).get("nome") or (e or {}).get("code")) == alvo for e in self.efeitos_formais)

    def adicionar_estado_transitorio(self, nome, dados=None):
        self.estados_transitorios[str(nome)] = dict(dados or {"ativo": True})

    def remover_estado_transitorio(self, nome):
        self.estados_transitorios.pop(str(nome), None)

    def limpar_transitorios_fim_rodada(self):
        self.estados_transitorios = {k: v for k, v in self.estados_transitorios.items() if k in {"morto_na_rodada"}}

    def serializar(self):
        self.recalcular_atributos()
        lado_visual = "jogador" if int(self.lado_id) == int(getattr(self.partida, "lado_jogador", 50)) else "inimigo"
        return {
            "id_batalha": self.id_batalha,
            "id_original": self.id_original,
            "nome": self.nome,
            "especie": self.especie,
            "nivel": self.nivel,
            "lado_id": self.lado_id,
            "lado_visual": lado_visual,
            "ativo": bool(self.ativo),
            "Ativo": bool(self.ativo),
            "em_reserva": bool(self.reserva),
            "EmReserva": bool(self.reserva),
            "vivo": self.esta_vivo(),
            "Vivo": self.esta_vivo(),
            "area_id": self.area_id,
            "AreaId": self.area_id,
            "VidaAtual": round(self.VidaAtual, 4),
            "VidaMax": round(self.obter_atributo("Vida", 1.0), 4),
            "Energia": round(self.EnergiaAtual, 4),
            "EnergiaMax": round(self.obter_atributo("EneM", 1.0), 4),
            "BarreiraAtual": round(self.BarreiraAtual, 4),
            "Atributos": dict(self.atributos_finais),
            "AtributosBase": dict(self.atributos_base),
            "Variacoes": dict(self.variacoes_permanentes),
            "Tipos": list(self.tipos),
            "ListaAtaques": copy.deepcopy(self.ataques),
            "ataques": copy.deepcopy(self.ataques),
            "efeitos": copy.deepcopy(self.efeitos_formais),
            "estados_transitorios": copy.deepcopy(self.estados_transitorios),
            "contadores_especiais": copy.deepcopy(self.contadores_especiais),
            "estatisticas_batalha": copy.deepcopy(self.estatisticas_batalha),
            "dados": {
                **copy.deepcopy(self.dados_originais),
                "estado": {
                    "stats": dict(self.atributos_finais),
                    "stats_base": dict(self.atributos_base),
                    "VidaAtual": round(self.VidaAtual, 4),
                    "EnergiaAtual": round(self.EnergiaAtual, 4),
                    "BarreiraAtual": round(self.BarreiraAtual, 4),
                    "tipos": list(self.tipos),
                },
            },
        }
