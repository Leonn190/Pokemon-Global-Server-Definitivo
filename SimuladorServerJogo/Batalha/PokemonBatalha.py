from __future__ import annotations

import copy
import math
import unicodedata

from SimuladorServerJogo.Batalha.FraquezasResistencia import obter_multiplicador


ATRIBUTOS_OFICIAIS = [
    "Vida", "Atk", "SpA", "Def", "SpD", "Mag", "Ene", "Vel", "Per", "Int",
    "Vamp", "CrC", "CrD", "Dur", "Amp", "EneM", "Acuracia", "Assertividade",
]


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


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
        info = dict(bruto.get("dados") or bruto.get("Dados") or {})
        estado = info.get("estado") if isinstance(info.get("estado"), dict) else {}
        self.partida = partida
        self.id_original = bruto.get("id_original", info.get("id", info.get("ID", bruto.get("id"))))
        self.id_batalha = str(bruto.get("id_batalha") or bruto.get("uid") or bruto.get("Uid") or self.id_original or f"P{indice}")
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
        self.ataques = list(bruto.get("ataques") or bruto.get("ListaAtaques") or info.get("ataques") or info.get("Ataques") or [])
        self.Build = copy.deepcopy(info.get("Build") or info.get("build") or bruto.get("Build") or {})
        self.atributos_base = {}
        self.variacoes_temporarias = {}
        self.variacoes_permanentes = {}
        self.atributos_finais = {}
        self.efeitos_formais = list(bruto.get("efeitos") or bruto.get("efeitos_formais") or info.get("efeitos") or [])
        self.estados_transitorios = dict(bruto.get("estados_transitorios") or {})
        self.contadores_especiais = dict(bruto.get("contadores_especiais") or {})
        self.estatisticas_batalha = dict(bruto.get("estatisticas_batalha") or {})
        self._carregar_atributos(info, estado, bruto)
        self.recalcular_atributos()
        self.VidaAtual = _clamp(_f(bruto.get("VidaAtual", info.get("VidaAtual", estado.get("VidaAtual", self.atributos_finais["Vida"]))), self.atributos_finais["Vida"]), 0.0, self.atributos_finais["Vida"])
        energia_padrao = round(self.atributos_finais["EneM"] * 0.75, 2)
        self.EnergiaAtual = _clamp(_f(bruto.get("Energia", bruto.get("EnergiaAtual", info.get("EnergiaAtual", estado.get("EnergiaAtual", energia_padrao)))), energia_padrao), 0.0, self.atributos_finais["EneM"])
        self.BarreiraAtual = max(0.0, _f(bruto.get("BarreiraAtual", info.get("BarreiraAtual", estado.get("BarreiraAtual", 0.0))), 0.0))
        if self.VidaAtual <= 0:
            self.vivo = False

    def _carregar_atributos(self, info: dict, estado: dict, bruto: dict) -> None:
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else info.get("stats") if isinstance(info.get("stats"), dict) else {}
        stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else info.get("stats_base") if isinstance(info.get("stats_base"), dict) else {}
        attrs = bruto.get("Atributos") if isinstance(bruto.get("Atributos"), dict) else {}
        attrs_base = bruto.get("AtributosBase") if isinstance(bruto.get("AtributosBase"), dict) else {}
        variacoes = bruto.get("Variacoes") if isinstance(bruto.get("Variacoes"), dict) else info.get("variacoes") if isinstance(info.get("variacoes"), dict) else {}
        aliases = {"Amp": "Amplificacao", "Dur": "Durabilidade"}
        for chave in ATRIBUTOS_OFICIAIS:
            alt = aliases.get(chave, chave)
            base = _f(attrs_base.get(chave, stats_base.get(chave, stats_base.get(alt, stats.get(chave, stats.get(alt, attrs.get(chave, 0.0)))))), 0.0)
            atual = _f(attrs.get(chave, stats.get(chave, stats.get(alt, base))), base)
            self.atributos_base[chave] = atual if base == 0.0 else base
            self.variacoes_permanentes[chave] = _f(variacoes.get(chave, 0.0), 0.0)
            self.variacoes_temporarias[chave] = 0.0
        self.atributos_base["Dur"] = self.atributos_base.get("Dur", 0.0)
        self.atributos_base["Amp"] = self.atributos_base.get("Amp", 0.0)
        self.atributos_base["Vamp"] = self.atributos_base.get("Vamp", 0.0)
        self.atributos_base["Acuracia"] = self.atributos_base.get("Acuracia") or 100.0
        self.atributos_base["Assertividade"] = self.atributos_base.get("Assertividade") or 100.0
        ene = self.atributos_base.get("Ene", 1.0) or 1.0
        self.atributos_base["EneM"] = self.atributos_base.get("EneM") or ene * 3.0

    def Verificar(self):
        if self.VidaAtual <= 0 and self.vivo:
            self.Morrer()
        self.recalcular_atributos()
        return self.vivo

    def recalcular_atributos(self):
        finais = {}
        for chave in ATRIBUTOS_OFICIAIS:
            finais[chave] = _f(self.atributos_base.get(chave, 0.0)) + _f(self.variacoes_permanentes.get(chave, 0.0)) + _f(self.variacoes_temporarias.get(chave, 0.0))
        for efeito in self.efeitos_formais:
            nome = _normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
            dados = (efeito or {}).get("dados") if isinstance((efeito or {}).get("dados"), dict) else {}
            valor = _f((efeito or {}).get("valor", dados.get("valor", 0.0)), 0.0)
            if nome == "amplificado":
                finais["Amp"] += valor if valor else 15.0
            elif nome == "fortificado":
                atributo = str(dados.get("atributo") or "Def")
                if atributo in finais:
                    finais[atributo] += valor
            elif nome == "energizado":
                finais["EneM"] += valor if valor else max(1.0, finais.get("Ene", 1.0))
            elif nome == "descarregado":
                finais["EneM"] = max(1.0, finais["EneM"] - (valor if valor else max(1.0, finais.get("Ene", 1.0))))
        finais["Vida"] = max(1.0, finais.get("Vida", 1.0))
        finais["EneM"] = max(1.0, finais.get("EneM", 1.0))
        finais["Acuracia"] = finais.get("Acuracia") or 100.0
        finais["Assertividade"] = finais.get("Assertividade") or 100.0
        self.atributos_finais = finais
        if hasattr(self, "VidaAtual"):
            self.VidaAtual = _clamp(self.VidaAtual, 0.0, finais["Vida"])
        if hasattr(self, "EnergiaAtual"):
            self.EnergiaAtual = _clamp(self.EnergiaAtual, 0.0, finais["EneM"])

    def obter_atributo(self, chave: str, default: float = 0.0) -> float:
        return _f(self.atributos_finais.get(str(chave), default), default)

    def AplicarDano(self, alvo, dados_dano, contexto=None):
        if alvo is None or not alvo.esta_vivo():
            return {"aplicado": False, "motivo": "alvo_invalido", "dano_vida": 0.0}
        contexto = dict(contexto or {})
        dados = dict(dados_dano or {})
        dano = max(0.0, _f(dados.get("dano_bruto", dados.get("dano", 0.0)), 0.0))
        tipo = dados.get("tipo") or contexto.get("tipo_ataque") or "normal"
        categoria = _normalizar(dados.get("categoria") or "normal")
        dano *= 1.0 + (self.obter_atributo("Amp") / 100.0)
        dano *= obter_multiplicador(tipo, alvo.tipos)
        if _normalizar(tipo) in {_normalizar(t) for t in self.tipos}:
            dano *= 1.20
        rng = contexto.get("rng") or getattr(getattr(self, "partida", None), "rng", None)
        chance_crit = _f(dados.get("chance_critico", self.obter_atributo("CrC")), 0.0)
        chance_crit = min(chance_crit, _f(dados.get("chance_critico_max", 999.0), 999.0))
        critico = False
        if not alvo.possui_efeito("Cauterizado") and chance_crit > 0:
            sorte = rng.random() * 100.0 if rng is not None else 100.0
            critico = sorte <= chance_crit
        if critico:
            dano *= 1.0 + (self.obter_atributo("CrD") / 100.0)
        defesa_chave = "SpD" if categoria in {"especial", "spa", "magico"} else "Def"
        defesa = alvo.obter_atributo(defesa_chave)
        defesa_efetiva = max(0.0, defesa - (self.obter_atributo("Per") / 2.0))
        dano *= 100.0 / (100.0 + defesa_efetiva)
        dano = max(0.0, dano - alvo.obter_atributo("Dur"))
        recebido = alvo.ReceberDano(dano, origem=self, dados={**dados, "critico": critico, "tipo": tipo})
        dano_vida = _f(recebido.get("dano_vida"), 0.0)
        if dano_vida > 0 and self.obter_atributo("Vamp") > 0:
            self.ReceberCura(dano_vida * (self.obter_atributo("Vamp") / 100.0), origem=self, dados={"vampirismo": True})
        self.estatisticas_batalha["dano_causado"] = _f(self.estatisticas_batalha.get("dano_causado"), 0.0) + dano_vida
        recebido.update({"critico": critico, "dano_calculado": round(dano, 4)})
        return recebido

    def ReceberDano(self, valor, origem=None, dados=None):
        dados = dict(dados or {})
        if not self.esta_vivo():
            return {"aplicado": False, "motivo": "morto", "dano_vida": 0.0, "dano_barreira": 0.0}
        dano = max(0.0, _f(valor, 0.0))
        if self.estados_transitorios.get("protegido"):
            self.estados_transitorios.pop("protegido", None)
            return {"aplicado": True, "protegido": True, "dano_vida": 0.0, "dano_barreira": 0.0}
        if self.BarreiraAtual > 0:
            absorvido = min(self.BarreiraAtual, dano)
            self.BarreiraAtual = max(0.0, self.BarreiraAtual - absorvido)
            return {"aplicado": True, "dano_vida": 0.0, "dano_barreira": round(absorvido, 4), "barreira_absorveu_instancia": True}
        antes = self.VidaAtual
        self.VidaAtual = max(0.0, self.VidaAtual - dano)
        dano_vida = max(0.0, antes - self.VidaAtual)
        self.estatisticas_batalha["dano_recebido"] = _f(self.estatisticas_batalha.get("dano_recebido"), 0.0) + dano_vida
        if self.VidaAtual <= 0:
            self.Morrer({"origem_id": getattr(origem, "id_batalha", None), **dados})
        return {"aplicado": True, "dano_vida": round(dano_vida, 4), "dano_barreira": 0.0}

    def AplicarCura(self, alvo, valor, dados=None):
        return alvo.ReceberCura(valor, origem=self, dados=dados) if alvo is not None else {"aplicado": False}

    def ReceberCura(self, valor, origem=None, dados=None):
        _ = origem
        if not self.esta_vivo():
            return {"aplicado": False, "motivo": "morto", "cura": 0.0}
        cura = max(0.0, _f(valor, 0.0))
        if self.possui_efeito("Queimado"):
            cura *= 0.65
        antes = self.VidaAtual
        self.VidaAtual = min(self.obter_atributo("Vida", 1.0), self.VidaAtual + cura)
        real = max(0.0, self.VidaAtual - antes)
        self.estatisticas_batalha["cura_recebida"] = _f(self.estatisticas_batalha.get("cura_recebida"), 0.0) + real
        if origem is not None:
            origem.estatisticas_batalha["cura_feita"] = _f(origem.estatisticas_batalha.get("cura_feita"), 0.0) + real
        return {"aplicado": True, "cura": round(real, 4), "dados": dict(dados or {})}

    def AplicarBarreira(self, alvo, valor, dados=None):
        return alvo.ReceberBarreira(valor, origem=self, dados=dados) if alvo is not None else {"aplicado": False}

    def ReceberBarreira(self, valor, origem=None, dados=None):
        _ = origem
        ganho = max(0.0, _f(valor, 0.0))
        self.BarreiraAtual += ganho
        return {"aplicado": True, "barreira": round(ganho, 4), "dados": dict(dados or {})}

    def AplicarEfeito(self, alvo, efeito, dados=None):
        return alvo.ReceberEfeito(efeito, origem=self, dados=dados) if alvo is not None else {"aplicado": False}

    def ReceberEfeito(self, efeito, origem=None, dados=None):
        if not self.esta_vivo():
            return {"aplicado": False, "motivo": "morto"}
        base = dict(efeito or {})
        nome = str(base.get("nome") or base.get("Nome") or base.get("code") or "").strip()
        if not nome:
            return {"aplicado": False, "motivo": "efeito_sem_nome"}
        if len(self.efeitos_formais) >= 4:
            aviso = {"pokemon_id": self.id_batalha, "efeito": nome, "motivo": "limite_efeitos_formais"}
            if self.partida is not None:
                self.partida.avisos.append(aviso)
            return {"aplicado": False, "motivo": "limite_efeitos_formais", "aviso": aviso}
        duracao_base = max(1, _i(base.get("duracao", base.get("passos", base.get("passos_restantes", 3))), 3))
        negativo = bool(base.get("negativo", _normalizar(nome) in {"queimado", "envenenado", "intoxicado", "provocando", "congelado", "dormindo", "paralisado", "enraizado", "cauterizado", "descarregado"}))
        mag_origem = origem.obter_atributo("Mag") if origem is not None and hasattr(origem, "obter_atributo") else 0.0
        mag_alvo = self.obter_atributo("Mag")
        if negativo and origem is self:
            duracao = duracao_base
        elif negativo:
            duracao = max(math.ceil(duracao_base / 2.0), int(round(duracao_base + mag_origem / 5.0 - mag_alvo / 5.0)))
        else:
            duracao = int(round(duracao_base + mag_origem / 5.0))
        formal = {
            "nome": nome,
            "code": base.get("code", nome),
            "passos_restantes": max(1, int(duracao)),
            "dados": dict(dados or base.get("dados") or {}),
            "valor": base.get("valor", (dados or {}).get("valor") if isinstance(dados, dict) else 0.0),
        }
        self.efeitos_formais.append(formal)
        self.recalcular_atributos()
        return {"aplicado": True, "efeito": dict(formal)}

    def RemoverEfeito(self, filtro):
        alvo = _normalizar(filtro)
        antes = len(self.efeitos_formais)
        self.efeitos_formais = [e for e in self.efeitos_formais if _normalizar((e or {}).get("nome") or (e or {}).get("code")) != alvo]
        self.recalcular_atributos()
        return antes - len(self.efeitos_formais)

    def decrementar_efeitos(self, passo_atual):
        _ = passo_atual
        restantes = []
        for efeito in self.efeitos_formais:
            nome = _normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
            vida = self.obter_atributo("Vida", 1.0)
            if nome == "queimado":
                self.ReceberDano(vida * 0.01, dados={"efeito": "Queimado"})
            elif nome == "envenenado":
                self.ReceberDano(vida * 0.02, dados={"efeito": "Envenenado"})
            elif nome == "intoxicado":
                self.ReceberDano(vida * 0.03, dados={"efeito": "Intoxicado"})
            elif nome in {"regeneracao", "abencoado"}:
                self.ReceberCura(vida * 0.02, dados={"efeito": nome})
            efeito = dict(efeito)
            efeito["passos_restantes"] = _i(efeito.get("passos_restantes"), 1) - 1
            if efeito["passos_restantes"] > 0 and self.esta_vivo():
                restantes.append(efeito)
        self.efeitos_formais = restantes
        self.recalcular_atributos()

    def GastarEnergia(self, valor, dados=None):
        custo = max(0.0, _f(valor, 0.0))
        if self.EnergiaAtual < custo:
            return False
        self.EnergiaAtual = max(0.0, self.EnergiaAtual - custo)
        self.estatisticas_batalha["energia_gasta"] = _f(self.estatisticas_batalha.get("energia_gasta"), 0.0) + custo
        return True

    def GanharEnergia(self, valor, dados=None):
        ganho = max(0.0, _f(valor, 0.0))
        self.EnergiaAtual = min(self.obter_atributo("EneM", 1.0), self.EnergiaAtual + ganho)
        return {"aplicado": True, "energia": round(ganho, 4), "dados": dict(dados or {})}

    def Mover(self, area_id):
        if self.partida is None:
            self.area_id = area_id
            self.ativo = True
            self.reserva = False
            return True
        return self.partida.mover_pokemon_para_area(self, area_id)

    def TrocarComReserva(self, pokemon_reserva):
        return self.partida.trocar_reserva(self, pokemon_reserva) if self.partida is not None else False

    def TrocarPosicao(self, outro_pokemon):
        return self.partida.trocar_posicao(self, outro_pokemon) if self.partida is not None else False

    def Morrer(self, dados=None):
        self.vivo = False
        self.VidaAtual = 0.0
        self.estados_transitorios["morto_na_rodada"] = dict(dados or {})
        return True

    def esta_vivo(self):
        return bool(self.vivo) and self.VidaAtual > 0

    def esta_apto_para_agir(self):
        if not self.esta_vivo():
            return False
        bloqueios = {"dormindo", "congelado", "paralisado"}
        return not any(self.possui_efeito(nome) for nome in bloqueios)

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

