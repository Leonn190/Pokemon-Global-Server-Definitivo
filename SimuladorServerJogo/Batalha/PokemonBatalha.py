from __future__ import annotations

import csv
from pathlib import Path


def _f(valor, default=0.0):
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _i(valor, default=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


_CATALOGO_EFEITOS = None


def carregar_catalogo_efeitos():
    global _CATALOGO_EFEITOS
    if _CATALOGO_EFEITOS is not None:
        return _CATALOGO_EFEITOS
    _CATALOGO_EFEITOS = {}
    caminho = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - Efeitos.csv"
    if not caminho.exists():
        return _CATALOGO_EFEITOS
    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = _i(row.get("Code"), 0)
            if code <= 0:
                continue
            _CATALOGO_EFEITOS[code] = {
                "code": code,
                "nome": str(row.get("Efeito") or "").strip(),
                "passos_base": max(1, _i(row.get("Passos Base"), 1)),
            }
    return _CATALOGO_EFEITOS


class PokemonBatalha:
    ATRS = ["Vida", "Atk", "SpA", "Def", "SpD", "Mag", "Ene", "Vel", "Per", "Int", "Vamp", "CrC", "CrD", "Dur", "Amp", "EneM", "Acuracia", "Assertividade"]

    def __init__(self, dados: dict, partida):
        info = dict(dados.get("dados") or dados)
        estado = dict(info.get("estado") or {})
        stats = dict(estado.get("stats") or info.get("stats") or {})
        base = dict(estado.get("stats_base") or info.get("stats_base") or stats)
        self.partida = partida
        self.id_batalha = str(dados.get("id_batalha") or dados.get("id") or "")
        self.id_original = dados.get("id_original", info.get("id"))
        self.nome = str(info.get("nome") or info.get("Nome") or dados.get("nome") or "Pokemon")
        self.especie = str(info.get("especie") or info.get("Especie") or dados.get("especie") or self.nome)
        self.nivel = max(1, _i(info.get("nivel", info.get("Nivel", 1)), 1))
        self.lado_id = _i(dados.get("lado_id", 50), 50)
        self.ativo = bool(dados.get("ativo", False))
        self.reserva = bool(dados.get("em_reserva", False))
        self.area_id = dados.get("area_id")
        self.vivo = bool(dados.get("vivo", True))
        self.dados_originais = info
        self.tipos = list(info.get("tipos") or estado.get("tipos") or [])
        self.ataques = list(dados.get("ataques") or [])
        self.Build = dict(info.get("Build") or {})
        self.atributos_base = {}
        self.variacoes_temporarias = {}
        self.variacoes_permanentes = {}
        self.atributos_finais = {}
        for k in self.ATRS:
            v = _f(base.get(k, stats.get(k, 0.0)), 0.0)
            if k in {"Acuracia", "Assertividade"} and v <= 0:
                v = 100.0
            if k in {"Dur", "Amp", "Vamp"} and v == 0:
                v = 0.0
            self.atributos_base[k] = v
            self.variacoes_permanentes[k] = _f((info.get("variacoes") or {}).get(k), 0.0)
            self.variacoes_temporarias[k] = 0.0
        if self.atributos_base.get("EneM", 0) <= 0:
            self.atributos_base["EneM"] = max(1.0, self.atributos_base.get("Ene", 1.0) * 3.0)
        self.recalcular_atributos()
        vida_raw = estado.get("VidaAtual", info.get("VidaAtual", self.atributos_finais["Vida"]))
        ene_raw = estado.get("EnergiaAtual", info.get("EnergiaAtual", self.atributos_finais["EneM"] * 0.75))
        self.VidaAtual = max(0.0, min(self.atributos_finais["Vida"], _f(vida_raw, self.atributos_finais["Vida"])))
        self.EnergiaAtual = max(0.0, _f(ene_raw, self.atributos_finais["EneM"] * 0.75))
        self.BarreiraAtual = max(0.0, _f(info.get("BarreiraAtual", 0.0), 0.0))
        self.efeitos_formais: list[dict] = []
        self.estados_transitorios: dict[str, dict] = {}
        self.contadores_especiais: dict[str, float] = dict(info.get("contadores_especiais") or {})
        self.estatisticas_batalha = {
            "dano_causado_vida": 0.0,
            "dano_absorvido_barreira": 0.0,
            "energia_gasta": 0.0,
            "curas_feitas": 0.0,
            "abates": 0,
        }

    def Verificar(self):
        self.recalcular_atributos()
        self.VidaAtual = max(0.0, min(self.atributos_finais.get("Vida", 1.0), self.VidaAtual))
        max_ene = self.atributos_finais.get("EneM", 1.0)
        if not self.possui_efeito("Energizado"):
            self.EnergiaAtual = max(0.0, min(max_ene, self.EnergiaAtual))
        else:
            self.EnergiaAtual = max(0.0, self.EnergiaAtual)
        if self.VidaAtual <= 0 and self.vivo:
            self.Morrer()

    def recalcular_atributos(self):
        fins = {}
        for k in self.ATRS:
            fins[k] = _f(self.atributos_base.get(k, 0.0), 0.0) + _f(self.variacoes_permanentes.get(k, 0.0), 0.0) + _f(self.variacoes_temporarias.get(k, 0.0), 0.0)
        if fins.get("EneM", 0) <= 0:
            fins["EneM"] = max(1.0, fins.get("Ene", 1.0) * 3.0)
        self.atributos_finais = fins

    def AplicarDano(self, alvo, dados_dano, contexto=None):
        contexto = dict(contexto or {})
        dano = _f((dados_dano or {}).get("dano_bruto"), 0.0)
        tipo_ataque = (dados_dano or {}).get("tipo") or "normal"
        categoria = str((dados_dano or {}).get("categoria") or "normal")
        dano *= 1.0 + (self.atributos_finais.get("Amp", 0.0) / 100.0)
        dano *= self.partida.fr.obter_multiplicador(tipo_ataque, alvo.tipos)
        if str(tipo_ataque).casefold() in {str(t).casefold() for t in self.tipos}:
            dano *= 1.2
        critico = bool((dados_dano or {}).get("forcar_critico", False))
        chance_crit = min(100.0, max(0.0, _f((dados_dano or {}).get("chance_crit", self.atributos_finais.get("CrC", 0.0)), 0.0)))
        if alvo.possui_efeito("Cauterizado"):
            chance_crit = 0.0
        if (not critico) and self.partida.rng.random() * 100.0 <= chance_crit:
            critico = True
        if critico:
            dano *= 1.0 + (self.atributos_finais.get("CrD", 0.0) / 100.0)
        defesa = alvo.atributos_finais.get("SpD" if categoria == "especial" else "Def", 0.0)
        defesa_efetiva = max(0.0, defesa - (self.atributos_finais.get("Per", 0.0) / 2.0))
        dano = dano * (100.0 / (100.0 + defesa_efetiva))
        dano = max(0.0, dano - alvo.atributos_finais.get("Dur", 0.0))
        retorno = alvo.ReceberDano(dano, origem=self, dados={"tipo": tipo_ataque, "categoria": categoria, "critico": critico})
        dano_vida = _f(retorno.get("dano_vida"), 0.0)
        if dano_vida > 0:
            self.estatisticas_batalha["dano_causado_vida"] += dano_vida
            vamp = max(0.0, self.atributos_finais.get("Vamp", 0.0)) / 100.0
            if vamp > 0:
                self.ReceberCura(dano_vida * vamp, origem=self, dados={"motivo": "vamp"})
        return {"dano_final": round(dano, 4), **retorno, "critico": critico}

    def ReceberDano(self, valor, origem=None, dados=None):
        dano = max(0.0, _f(valor, 0.0))
        if dano <= 0:
            return {"dano_vida": 0.0, "dano_barreira": 0.0, "barreira_absorvida": False}
        if self.BarreiraAtual > 0:
            absorvido = min(self.BarreiraAtual, dano)
            self.BarreiraAtual = max(0.0, self.BarreiraAtual - absorvido)
            self.estatisticas_batalha["dano_absorvido_barreira"] += absorvido
            return {"dano_vida": 0.0, "dano_barreira": absorvido, "barreira_absorvida": True}
        vida_antes = self.VidaAtual
        self.VidaAtual = max(0.0, self.VidaAtual - dano)
        dano_vida = max(0.0, vida_antes - self.VidaAtual)
        if self.VidaAtual <= 0:
            self.Morrer(dados=dados)
            if origem is not None:
                origem.estatisticas_batalha["abates"] += 1
        return {"dano_vida": dano_vida, "dano_barreira": 0.0, "barreira_absorvida": False}

    def AplicarCura(self, alvo, valor, dados=None):
        retorno = alvo.ReceberCura(valor, origem=self, dados=dados)
        self.estatisticas_batalha["curas_feitas"] += _f(retorno.get("cura"), 0.0)
        return retorno

    def ReceberCura(self, valor, origem=None, dados=None):
        _ = (origem, dados)
        cura = max(0.0, _f(valor, 0.0))
        antes = self.VidaAtual
        self.VidaAtual = min(self.atributos_finais.get("Vida", 1.0), self.VidaAtual + cura)
        return {"cura": max(0.0, self.VidaAtual - antes)}

    def AplicarBarreira(self, alvo, valor, dados=None):
        return alvo.ReceberBarreira(valor, origem=self, dados=dados)

    def ReceberBarreira(self, valor, origem=None, dados=None):
        _ = (origem, dados)
        ganho = max(0.0, _f(valor, 0.0))
        self.BarreiraAtual += ganho
        return {"barreira": ganho}

    def AplicarEfeito(self, alvo, efeito, dados=None):
        return alvo.ReceberEfeito(efeito, origem=self, dados=dados)

    def ReceberEfeito(self, efeito, origem=None, dados=None):
        dados = dict(dados or {})
        mag_aplicador = _f((origem.atributos_finais if origem else {}).get("Mag"), 0.0)
        mag_alvo = _f(self.atributos_finais.get("Mag"), 0.0)
        if isinstance(efeito, dict):
            code = _i(efeito.get("code", efeito.get("Code")), 0)
            nome = str(efeito.get("nome") or "")
            base = max(1, _i(efeito.get("duracao", efeito.get("passos_base", 1)), 1))
            categoria = str(efeito.get("categoria") or "negativo")
        else:
            code = _i(efeito, 0)
            cfg = carregar_catalogo_efeitos().get(code, {})
            nome = cfg.get("nome") or str(efeito)
            base = max(1, _i(cfg.get("passos_base", 1), 1))
            categoria = str((dados or {}).get("categoria") or "negativo")
        if 1 <= code <= 34 and len(self.efeitos_formais) >= 4:
            if self.partida and self.partida.log_corrente is not None:
                self.partida.construtor_log.evento(self.partida.log_corrente, "efeito_bloqueado_por_limite", pokemon_id=self.id_batalha, efeito=nome, code=code)
            return {"aplicado": False, "motivo": "limite_efeitos"}
        duracao = base
        if categoria == "positivo":
            duracao = base + int(mag_aplicador / 5)
        elif origem is self:
            duracao = base
        else:
            duracao = max(int(base / 2), base + int(mag_aplicador / 5) - int(mag_alvo / 5))
        item = {"code": code, "nome": nome, "duracao": max(1, int(duracao)), "passo_criacao": int(self.partida.passo_atual), "categoria": categoria}
        self.efeitos_formais.append(item)
        if str(nome).casefold() == "provocando":
            self.RemoverEfeito("furtivo")
        return {"aplicado": True, "efeito": item}

    def RemoverEfeito(self, filtro):
        if isinstance(filtro, int):
            self.efeitos_formais = [e for e in self.efeitos_formais if _i(e.get("code"), -1) != int(filtro)]
            return
        alvo = str(filtro or "").casefold()
        self.efeitos_formais = [e for e in self.efeitos_formais if str(e.get("nome") or "").casefold() != alvo]

    def decrementar_efeitos(self, passo_atual):
        novos = []
        for e in self.efeitos_formais:
            if int(e.get("passo_criacao", -1)) == int(passo_atual):
                novos.append(e)
                continue
            e = dict(e)
            e["duracao"] = int(e.get("duracao", 1)) - 1
            if e["duracao"] > 0:
                novos.append(e)
        self.efeitos_formais = novos

    def GastarEnergia(self, valor, dados=None):
        _ = dados
        v = max(0.0, _f(valor, 0.0))
        if self.EnergiaAtual + 1e-6 < v:
            return False
        self.EnergiaAtual = max(0.0, self.EnergiaAtual - v)
        self.estatisticas_batalha["energia_gasta"] += v
        return True

    def GanharEnergia(self, valor, dados=None):
        _ = dados
        v = max(0.0, _f(valor, 0.0))
        teto = None if self.possui_efeito("Energizado") else self.atributos_finais.get("EneM", 1.0)
        self.EnergiaAtual = self.EnergiaAtual + v if teto is None else min(teto, self.EnergiaAtual + v)

    def Mover(self, area_id):
        return self.partida.mover_pokemon_para_area(self, area_id)

    def TrocarComReserva(self, pokemon_reserva):
        return self.partida.trocar_reserva(self, pokemon_reserva)

    def TrocarPosicao(self, outro_pokemon):
        return self.partida.trocar_posicao(self, outro_pokemon)

    def Morrer(self, dados=None):
        _ = dados
        self.vivo = False
        self.ativo = False
        self.reserva = True
        if self.area_id:
            self.partida.ocupacao_areas[self.area_id] = None
            self.area_id = None

    def esta_vivo(self):
        return bool(self.vivo and self.VidaAtual > 0)

    def esta_apto_para_agir(self):
        if not self.esta_vivo():
            return False
        if self.possui_efeito("Dormindo") or self.possui_efeito("Congelado") or self.possui_efeito("Paralisado"):
            return False
        return True

    def possui_efeito(self, nome_ou_code):
        if isinstance(nome_ou_code, int):
            code = int(nome_ou_code)
            return any(_i(e.get("code"), -1) == code for e in self.efeitos_formais)
        alvo = str(nome_ou_code or "").casefold()
        return any(str(e.get("nome") or "").casefold() == alvo for e in self.efeitos_formais)

    def adicionar_estado_transitorio(self, nome, dados=None):
        self.estados_transitorios[str(nome)] = dict(dados or {})

    def remover_estado_transitorio(self, nome):
        self.estados_transitorios.pop(str(nome), None)

    def limpar_transitorios_fim_rodada(self):
        self.estados_transitorios.pop("entrou_na_rodada", None)
        self.estados_transitorios.pop("recuado", None)

    def serializar(self):
        return {
            "id_batalha": self.id_batalha,
            "id_original": self.id_original,
            "nome": self.nome,
            "especie": self.especie,
            "nivel": self.nivel,
            "lado_id": self.lado_id,
            "ativo": self.ativo,
            "em_reserva": self.reserva,
            "area_id": self.area_id,
            "vivo": self.esta_vivo(),
            "dados": self.dados_originais,
            "tipos": list(self.tipos),
            "ataques": list(self.ataques),
            "atributos_base": dict(self.atributos_base),
            "atributos_finais": dict(self.atributos_finais),
            "variacoes_temporarias": dict(self.variacoes_temporarias),
            "variacoes_permanentes": dict(self.variacoes_permanentes),
            "VidaAtual": round(self.VidaAtual, 4),
            "EnergiaAtual": round(self.EnergiaAtual, 4),
            "BarreiraAtual": round(self.BarreiraAtual, 4),
            "efeitos_formais": [dict(e) for e in self.efeitos_formais],
            "estados_transitorios": dict(self.estados_transitorios),
            "contadores_especiais": dict(self.contadores_especiais),
            "estatisticas_batalha": dict(self.estatisticas_batalha),
        }
