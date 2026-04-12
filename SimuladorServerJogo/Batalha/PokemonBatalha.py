from __future__ import annotations

import math
from copy import deepcopy
from typing import Dict, List, Tuple

from SimuladorServerJogo.Batalha.PassivasEquipaveis import executar_passivas_equipaveis
from SimuladorServerJogo.Batalha.PassivasHabilidades import executar_passivas_habilidades


Vec2 = Tuple[float, float]
ATRIBUTOS_PADRAO = (
    "Vida",
    "Atk",
    "Def",
    "SpA",
    "SpD",
    "Vel",
    "Mag",
    "Per",
    "Ene",
    "Int",
    "CrC",
    "CrD",
    "Vamp",
    "Precisao",
    "Amplificacao",
    "Durabilidade",
)


class PokemonBatalha:
    _ALIASES = {
        "vida": "Vida",
        "vidamax": "Vida",
        "atk": "Atk",
        "ataque": "Atk",
        "def": "Def",
        "defesa": "Def",
        "spa": "SpA",
        "ataqueespecial": "SpA",
        "spd": "SpD",
        "defesaespecial": "SpD",
        "vel": "Vel",
        "velocidade": "Vel",
        "mag": "Mag",
        "magia": "Mag",
        "per": "Per",
        "perfuracao": "Per",
        "ene": "Ene",
        "energia": "Ene",
        "int": "Int",
        "inteligencia": "Int",
        "crc": "CrC",
        "crd": "CrD",
        "vamp": "Vamp",
        "precisao": "Precisao",
        "amplificacao": "Amplificacao",
        "durabilidade": "Durabilidade",
    }

    def __init__(
        self,
        dados: Dict[str, object] | None = None,
        lado: str = "",
        *,
        posicao: Vec2 = (0.0, 0.0),
        ativo: bool = True,
        slot_time: int = 0,
        slot_ativo: int = 0,
    ) -> None:
        bruto = deepcopy(dict(dados or {}))
        estado = bruto.get("estado") if isinstance(bruto.get("estado"), dict) else bruto
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
        stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}

        self.Dados = bruto
        self.Estado = estado
        self.Uid = str(bruto.get("uid") or bruto.get("id") or bruto.get("ID") or estado.get("uid") or estado.get("id") or estado.get("ID") or f"poke:{id(self)}")
        self.Nome = str(estado.get("nome") or estado.get("Nome") or bruto.get("nome") or bruto.get("Nome") or estado.get("especie") or bruto.get("especie") or "Pokemon")
        self.Especie = str(estado.get("especie") or estado.get("Especie") or bruto.get("especie") or bruto.get("Especie") or self.Nome)
        self.Lado = str(lado or bruto.get("lado") or estado.get("lado") or "")
        self.Ativo = bool(ativo)
        self.SlotTime = int(slot_time)
        self.SlotAtivo = int(slot_ativo)
        self.ForaDeCombate = False
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.PosicaoAnterior = self.Posicao
        self.VelocidadeAtualTilesTick = 0.0
        self.Peso = max(0.1, self._fnum(estado.get("peso", bruto.get("peso", 1.0)), 1.0))
        self.Escala = max(0, int(self._fnum(estado.get("escala", bruto.get("escala", 3)), 3)))
        self.TamanhoTiles = max(0.4, self._fnum(estado.get("tamanho_tiles", bruto.get("tamanho_tiles", 0.6)), 0.6))
        self.RaioColisao = float(self.TamanhoTiles) * 0.5
        self.Tipos = [str(item).strip() for item in list(estado.get("tipos") or bruto.get("tipos") or []) if str(item).strip()]
        self.Habilidades = [deepcopy(item) for item in list(estado.get("habilidades") or bruto.get("habilidades") or bruto.get("ataques") or []) if item]
        self.Memorias = [deepcopy(item) for item in list(estado.get("memorias") or bruto.get("memorias") or []) if item]
        self.ItensBuild = [deepcopy(item) for item in list(estado.get("build") or estado.get("itens_build") or bruto.get("build") or bruto.get("itens_build") or []) if item]

        self.AtributosBase: Dict[str, float] = {}
        for chave in ATRIBUTOS_PADRAO:
            self.AtributosBase[chave] = max(0.0, self._fnum(stats.get(chave, stats_base.get(chave, estado.get(chave, bruto.get(chave, 0.0)))), 0.0))
        self.AtributosBase["Precisao"] = max(0.0, self.AtributosBase.get("Precisao", 100.0) or 100.0)
        if self.AtributosBase.get("Vamp", 0.0) <= 0.0:
            self.AtributosBase["Vamp"] = max(0.0, self._fnum(estado.get("vamp", bruto.get("vamp", 0.0)), 0.0))

        self.VariacoesFixas = {chave: 0.0 for chave in ATRIBUTOS_PADRAO}
        self.VariacoesTemporarias = {chave: 0.0 for chave in ATRIBUTOS_PADRAO}
        self.MultiplicadoresTemporarios = {
            "dano_causado": 1.0,
            "dano_recebido": 1.0,
            "cura_recebida": 1.0,
            "energia_ganho": 1.0,
            "critico_chance": 1.0,
            "critico_dano": 1.0,
            "precisao": 1.0,
        }
        self.Flags = {
            "pode_agir": True,
            "pode_atacar": True,
            "pode_mover": True,
            "pode_usar_habilidade": True,
            "pode_passiva_item": True,
            "imune_efeito_negativo": False,
            "bloqueia_efeito_positivo": False,
            "focado": False,
            "evasivo": False,
            "imortal": False,
        }
        self.Efeitos: List[Dict[str, object]] = []

        vida_atual_bruta = estado.get("vida_atual", estado.get("VidaAtual", bruto.get("vida_atual", bruto.get("VidaAtual", self.AtributosBase.get("Vida", 1.0)))))
        self.VidaAtual = max(0.0, min(self.AtributosBase.get("Vida", 1.0), self._fnum(vida_atual_bruta, self.AtributosBase.get("Vida", 1.0))))

        energia_max_bruta = estado.get("EnergiaMaxima", estado.get("energia_maxima", bruto.get("EnergiaMaxima", self.AtributosBase.get("Ene", 1.0) * 3.0)))
        self.EnergiaMax = max(1.0, self._fnum(energia_max_bruta, self.AtributosBase.get("Ene", 1.0) * 3.0))
        energia_bruta = estado.get("energia_atual", estado.get("EnergiaAtual", estado.get("energia", bruto.get("energia_atual", bruto.get("EnergiaAtual", self.EnergiaMax * 0.5)))))
        self.Energia = max(0.0, min(self.EnergiaMax, self._fnum(energia_bruta, self.EnergiaMax * 0.5)))
        self.Barreira = max(0.0, self._fnum(estado.get("barreira", bruto.get("barreira", 0.0)), 0.0))

        self.AtributosAtuais = dict(self.AtributosBase)
        self.Verifica()

    @staticmethod
    def _fnum(valor, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @classmethod
    def _norm(cls, chave: object) -> str:
        base = "".join(ch for ch in str(chave or "").strip().lower() if ch.isalnum())
        return cls._ALIASES.get(base, str(chave or "").strip())

    def obter_atributo(self, chave: str) -> float:
        canon = self._norm(chave)
        if canon == "Vida":
            return float(self.AtributosAtuais.get("Vida", 1.0))
        return float(self.AtributosAtuais.get(canon, 0.0))

    def serializar(self) -> Dict[str, object]:
        return {
            "uid": self.Uid,
            "nome": self.Nome,
            "especie": self.Especie,
            "lado": self.Lado,
            "ativo": bool(self.Ativo),
            "slot_time": int(self.SlotTime),
            "slot_ativo": int(self.SlotAtivo),
            "fora_de_combate": bool(self.ForaDeCombate),
            "posicao": [round(self.Posicao[0], 4), round(self.Posicao[1], 4)],
            "raio_colisao": round(self.RaioColisao, 4),
            "peso": round(self.Peso, 4),
            "escala": int(self.Escala),
            "tipos": list(self.Tipos),
            "vida_atual": round(self.VidaAtual, 4),
            "vida_max": round(self.AtributosAtuais.get("Vida", 1.0), 4),
            "energia": round(self.Energia, 4),
            "energia_max": round(self.EnergiaMax, 4),
            "barreira": round(self.Barreira, 4),
            "atributos": {ch: round(float(v), 4) for ch, v in self.AtributosAtuais.items()},
            "variacoes_fixas": {ch: round(float(v), 4) for ch, v in self.VariacoesFixas.items() if abs(float(v)) > 1e-9},
            "efeitos": [dict(item) for item in self.Efeitos],
            "flags": dict(self.Flags),
            "habilidades": [deepcopy(item) for item in self.Habilidades],
            "itens_build": [deepcopy(item) for item in self.ItensBuild],
        }

    def Verifica(self) -> Dict[str, object]:
        self.VariacoesTemporarias = {chave: 0.0 for chave in ATRIBUTOS_PADRAO}
        self.MultiplicadoresTemporarios = {
            "dano_causado": 1.0,
            "dano_recebido": 1.0,
            "cura_recebida": 1.0,
            "energia_ganho": 1.0,
            "critico_chance": 1.0,
            "critico_dano": 1.0,
            "precisao": 1.0,
        }
        self.Flags = {
            "pode_agir": True,
            "pode_atacar": True,
            "pode_mover": True,
            "pode_usar_habilidade": True,
            "pode_passiva_item": True,
            "imune_efeito_negativo": False,
            "bloqueia_efeito_positivo": False,
            "focado": False,
            "evasivo": False,
            "imortal": False,
        }

        for efeito in list(self.Efeitos):
            nome = str(efeito.get("nome") or "").strip().casefold()
            if not nome:
                continue
            if nome == "dormindo":
                self.Flags["pode_agir"] = False
                self.Flags["pode_mover"] = False
                self.Flags["pode_atacar"] = False
            elif nome == "paralisado":
                self.Flags["pode_atacar"] = False
            elif nome == "incapacitado":
                self.Flags["pode_usar_habilidade"] = False
            elif nome == "enraizado":
                self.Flags["pode_mover"] = False
            elif nome == "congelado":
                self.Flags["pode_agir"] = False
                self.Flags["pode_mover"] = False
                self.Flags["pode_atacar"] = False
                self.MultiplicadoresTemporarios["dano_recebido"] *= 0.7
            elif nome == "atordoado":
                self.Flags["pode_passiva_item"] = False
            elif nome == "bloqueado":
                self.Flags["bloqueia_efeito_positivo"] = True
            elif nome == "imune":
                self.Flags["imune_efeito_negativo"] = True
            elif nome == "focado":
                self.Flags["focado"] = True
            elif nome == "evasivo":
                self.Flags["evasivo"] = True
            elif nome == "imortal":
                self.Flags["imortal"] = True
            elif nome == "queimado":
                self.MultiplicadoresTemporarios["cura_recebida"] *= 0.7
            elif nome == "encharcado":
                efeito["multiplicador_custo_energia"] = 1.25
            elif nome == "quebrado":
                self.VariacoesTemporarias["Def"] -= self.AtributosBase.get("Def", 0.0) * 0.5
            elif nome == "fragilizado":
                self.VariacoesTemporarias["SpD"] -= self.AtributosBase.get("SpD", 0.0) * 0.5
            elif nome == "enfraquecido":
                self.VariacoesTemporarias["Atk"] -= self.AtributosBase.get("Atk", 0.0) * 0.5
            elif nome == "neutralizado":
                self.VariacoesTemporarias["SpA"] -= self.AtributosBase.get("SpA", 0.0) * 0.5
            elif nome == "confuso":
                self.MultiplicadoresTemporarios["precisao"] *= 0.5
            elif nome == "enfeiticado" or nome == "enfeitiçado":
                self.VariacoesTemporarias["Mag"] -= self.AtributosBase.get("Mag", 0.0) * 0.5
            elif nome == "descarregado":
                self.MultiplicadoresTemporarios["energia_ganho"] *= 0.5
            elif nome == "fortificado":
                self.VariacoesTemporarias["Def"] += self.AtributosBase.get("Def", 0.0) * 0.5
            elif nome == "reforcado" or nome == "reforçado":
                self.VariacoesTemporarias["SpD"] += self.AtributosBase.get("SpD", 0.0) * 0.5
            elif nome == "amplificado":
                self.MultiplicadoresTemporarios["dano_causado"] *= 1.5
            elif nome == "aprimorado":
                self.MultiplicadoresTemporarios["dano_causado"] *= 1.5
            elif nome == "voando":
                efeito["bonus_evasao_mirado"] = 0.5
            elif nome == "flutuando":
                efeito["bonus_evasao_normal"] = 0.5
            elif nome == "energizado":
                self.MultiplicadoresTemporarios["energia_ganho"] *= 1.5
            elif nome == "encantado":
                self.VariacoesTemporarias["Mag"] += self.AtributosBase.get("Mag", 0.0) * 0.5

        self.AtributosAtuais = {}
        for chave in ATRIBUTOS_PADRAO:
            base = float(self.AtributosBase.get(chave, 0.0))
            fixa = float(self.VariacoesFixas.get(chave, 0.0))
            temporaria = float(self.VariacoesTemporarias.get(chave, 0.0))
            valor = base + fixa + temporaria
            if chave in {"CrC", "CrD"}:
                valor = max(0.0, valor)
            elif chave == "Precisao":
                valor = max(0.0, valor * self.MultiplicadoresTemporarios.get("precisao", 1.0))
            else:
                valor = max(0.0, valor)
            self.AtributosAtuais[chave] = round(valor, 4)

        self.AtributosAtuais["Vida"] = max(1.0, self.AtributosAtuais.get("Vida", 1.0))
        self.VidaAtual = max(0.0, min(self.VidaAtual, self.AtributosAtuais["Vida"]))
        self.EnergiaMax = max(1.0, max(self.EnergiaMax, self.AtributosAtuais.get("Ene", 1.0)))
        self.Energia = max(0.0, min(self.Energia, self.EnergiaMax))
        self.ForaDeCombate = self.ForaDeCombate or self.VidaAtual <= 0.0
        return self.serializar()

    def passivas_habilidade_ativas(self, ativacao: str) -> list[object]:
        saida = []
        for ataque in self.Habilidades:
            if not isinstance(ataque, dict):
                continue
            estilo = str(ataque.get("Estilo") or ataque.get("estilo") or "").strip().casefold()
            gatilho = str(ataque.get("Ativacao") or ataque.get("Ativação") or "").strip().casefold()
            if estilo != "habilidade":
                continue
            if gatilho and gatilho != str(ativacao or "").strip().casefold():
                continue
            nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
            if nome:
                saida.append(nome)
        return saida

    def passivas_equipaveis_ativas(self, ativacao: str) -> list[object]:
        saida = []
        for item in self.ItensBuild:
            if not isinstance(item, dict):
                continue
            gatilho = str(item.get("Ativacao") or item.get("Ativação") or "").strip().casefold()
            if gatilho and gatilho != str(ativacao or "").strip().casefold():
                continue
            nome = str(item.get("Nome") or item.get("nome") or item.get("Equipavel") or item.get("equipavel") or "").strip()
            if nome:
                saida.append(nome)
        return saida

    def _registrar_passivas(self, ativacao: str, contexto: Dict[str, object]) -> Dict[str, object]:
        retorno = {"habilidades": [], "equipaveis": []}
        if self.Flags.get("pode_usar_habilidade", True):
            retorno["habilidades"] = executar_passivas_habilidades(self.passivas_habilidade_ativas(ativacao), ativacao, contexto)
        if self.Flags.get("pode_passiva_item", True):
            retorno["equipaveis"] = executar_passivas_equipaveis(self.passivas_equipaveis_ativas(ativacao), ativacao, contexto)
        return retorno

    def ModificarStatus(self, atributo: str, delta: float, *, temporario: bool = False) -> Dict[str, object]:
        canon = self._norm(atributo)
        if canon not in ATRIBUTOS_PADRAO:
            return {"status": "ignorado", "atributo": canon, "delta": float(delta)}
        alvo = self.VariacoesTemporarias if temporario else self.VariacoesFixas
        alvo[canon] = float(alvo.get(canon, 0.0) + float(delta))
        self.Verifica()
        return {"status": "ok", "atributo": canon, "delta": float(delta), "temporario": bool(temporario)}

    def ReceberBarreira(self, valor: float) -> Dict[str, object]:
        ganho = max(0.0, float(valor))
        self.Barreira = round(self.Barreira + ganho, 4)
        return {"status": "ok", "barreira_ganha": round(ganho, 4), "barreira_total": round(self.Barreira, 4)}

    def Curar(self, valor: float, *, origem=None, motivo: str = "") -> Dict[str, object]:
        return self.ReceberCura(valor, origem=origem, motivo=motivo)

    def ReceberCura(self, valor: float, *, origem=None, motivo: str = "") -> Dict[str, object]:
        bruto = max(0.0, float(valor))
        final = bruto * float(self.MultiplicadoresTemporarios.get("cura_recebida", 1.0))
        antes = self.VidaAtual
        self.VidaAtual = min(self.AtributosAtuais.get("Vida", 1.0), self.VidaAtual + final)
        curado = max(0.0, self.VidaAtual - antes)
        contexto = {
            "origem": getattr(origem, "Uid", ""),
            "alvo": self.Uid,
            "valor_bruto": bruto,
            "valor_final": curado,
            "motivo": str(motivo or ""),
        }
        self._registrar_passivas("AoCurar", contexto)
        return {"status": "ok", "cura_bruta": round(bruto, 4), "cura_final": round(curado, 4), "vida_atual": round(self.VidaAtual, 4)}

    def GanharEnergia(self, valor: float, *, motivo: str = "") -> Dict[str, object]:
        ganho_bruto = max(0.0, float(valor))
        ganho_final = ganho_bruto * float(self.MultiplicadoresTemporarios.get("energia_ganho", 1.0))
        antes = self.Energia
        self.Energia = min(self.EnergiaMax, self.Energia + ganho_final)
        ganho = max(0.0, self.Energia - antes)
        return {"status": "ok", "ganho_bruto": round(ganho_bruto, 4), "ganho_final": round(ganho, 4), "energia": round(self.Energia, 4), "motivo": str(motivo or "")}

    def gastar_energia(self, valor: float) -> float:
        custo = max(0.0, float(valor))
        for efeito in self.Efeitos:
            if str(efeito.get("nome") or "").strip().casefold() == "encharcado":
                custo *= float(efeito.get("multiplicador_custo_energia", 1.25) or 1.25)
        custo = round(custo, 4)
        self.Energia = max(0.0, self.Energia - custo)
        return custo

    def AplicarEfeito(self, alvo, nome_efeito: str, *, origem=None, positivo: bool | None = None) -> Dict[str, object]:
        return alvo.ReceberEfeito(nome_efeito, origem=origem or self, positivo=positivo)

    def ReceberEfeito(self, nome_efeito: str, *, origem=None, positivo: bool | None = None) -> Dict[str, object]:
        nome = str(nome_efeito or "").strip()
        if not nome:
            return {"status": "ignorado"}
        positivo_real = bool(positivo) if positivo is not None else nome.casefold() in {
            "regeneração",
            "regeneracao",
            "abençoado",
            "abencoado",
            "imortal",
            "fortificado",
            "reforçado",
            "reforcado",
            "amplificado",
            "aprimorado",
            "voando",
            "flutuando",
            "imune",
            "energizado",
            "preparado",
            "provocando",
            "furtivo",
            "ilimitado",
            "encantado",
            "refletido",
            "evasivo",
            "focado",
        }
        if (not positivo_real) and self.Flags.get("imune_efeito_negativo", False):
            return {"status": "bloqueado_imune", "efeito": nome}
        if positivo_real and self.Flags.get("bloqueia_efeito_positivo", False):
            return {"status": "bloqueado_positivo", "efeito": nome}

        mag_origem = origem.obter_atributo("Mag") if origem is not None and hasattr(origem, "obter_atributo") else 20.0
        mag_defesa = self.obter_atributo("Mag")
        duracao = max(20, int(round(mag_origem if positivo_real else max(20.0, (mag_origem + 5.0) - mag_defesa))))
        if any(str(efeito.get("nome") or "").strip().casefold() == "amaldiçoado" for efeito in self.Efeitos):
            duracao = int(math.ceil(duracao * 1.5))

        efeito = {
            "nome": nome,
            "positivo": bool(positivo_real),
            "duracao_ticks": int(duracao),
            "duracao_inicial_ticks": int(duracao),
            "origem_id": getattr(origem, "Uid", ""),
        }
        self.Efeitos.append(efeito)
        self.Verifica()
        return {"status": "ok", "efeito": nome, "duracao_ticks": int(duracao), "positivo": bool(positivo_real)}

    def _consumir_efeito(self, nome: str) -> bool:
        alvo = str(nome or "").strip().casefold()
        for indice, efeito in enumerate(list(self.Efeitos)):
            if str(efeito.get("nome") or "").strip().casefold() != alvo:
                continue
            self.Efeitos.pop(indice)
            self.Verifica()
            return True
        return False

    def TomarDano(self, pacote: Dict[str, object], *, sistema=None, tick: int = 0) -> Dict[str, object]:
        self.Verifica()
        dano = max(0.0, self._fnum(pacote.get("dano_final"), pacote.get("dano", 0.0)))
        origem = pacote.get("origem")
        origem_id = getattr(origem, "Uid", pacote.get("origem_id", ""))
        if self.Flags.get("evasivo", False):
            self._consumir_efeito("Evasivo")
            return {"status": "evadido", "alvo": self.Uid, "origem_id": origem_id, "tick": int(tick)}

        if any(str(efeito.get("nome") or "").strip().casefold() == "refletido" for efeito in self.Efeitos):
            refletido = dano * 0.75
            dano *= 0.25
            if origem is not None and hasattr(origem, "TomarDano"):
                origem.TomarDano({"dano_final": refletido, "origem_id": self.Uid, "origem": self, "ignorar_refletido": True}, sistema=sistema, tick=tick)

        if any(str(efeito.get("nome") or "").strip().casefold() == "preparado" for efeito in self.Efeitos):
            dano *= 0.4
            if origem is not None and hasattr(origem, "TomarDano"):
                origem.TomarDano({"dano_final": self.obter_atributo("Vel") * 0.4, "origem_id": self.Uid, "origem": self, "ignorar_refletido": True}, sistema=sistema, tick=tick)

        dano *= float(self.MultiplicadoresTemporarios.get("dano_recebido", 1.0))
        antes_barreira = self.Barreira
        dano_barreira = min(self.Barreira, dano)
        self.Barreira = max(0.0, self.Barreira - dano_barreira)
        dano_hp = max(0.0, dano - dano_barreira)

        if dano_hp >= self.VidaAtual and self.Flags.get("imortal", False):
            self._consumir_efeito("Imortal")
            dano_hp = max(0.0, self.VidaAtual - 1.0)

        antes_vida = self.VidaAtual
        self.VidaAtual = max(0.0, self.VidaAtual - dano_hp)
        if dano_hp > 0.0:
            self._consumir_efeito("Dormindo")

        contexto = {
            "origem": origem_id,
            "alvo": self.Uid,
            "tick": int(tick),
            "dano_bruto": round(dano, 4),
            "dano_hp": round(dano_hp, 4),
            "dano_barreira": round(dano_barreira, 4),
        }
        self._registrar_passivas("AoReceberDano", contexto)

        if any(str(efeito.get("nome") or "").strip().casefold() == "vampirico" for efeito in self.Efeitos):
            if origem is not None and hasattr(origem, "ReceberCura"):
                origem.ReceberCura(dano_hp * 0.25, origem=self, motivo="Vampirico")

        if self.VidaAtual <= 0.0:
            self.ForaDeCombate = True
            self._registrar_passivas("AoMorrer", contexto)

        return {
            "status": "ok",
            "alvo": self.Uid,
            "origem_id": origem_id,
            "tick": int(tick),
            "vida_antes": round(antes_vida, 4),
            "vida_depois": round(self.VidaAtual, 4),
            "barreira_antes": round(antes_barreira, 4),
            "barreira_depois": round(self.Barreira, 4),
            "dano_hp": round(dano_hp, 4),
            "dano_barreira": round(dano_barreira, 4),
            "morto": bool(self.ForaDeCombate),
        }

    def Mover(self, posicao: Vec2) -> Dict[str, object]:
        self.PosicaoAnterior = self.Posicao
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        return {
            "status": "ok",
            "uid": self.Uid,
            "origem": [round(self.PosicaoAnterior[0], 4), round(self.PosicaoAnterior[1], 4)],
            "destino": [round(self.Posicao[0], 4), round(self.Posicao[1], 4)],
        }

    def AplicarDano(self, alvo, pacote: Dict[str, object], *, sistema=None, tick: int = 0) -> Dict[str, object]:
        if alvo is None or not hasattr(alvo, "TomarDano"):
            return {"status": "ignorado"}
        contexto = {
            "origem": self.Uid,
            "alvo": getattr(alvo, "Uid", ""),
            "tick": int(tick),
            "pacote": dict(pacote),
        }
        self._registrar_passivas("AoCausarDano", contexto)
        return alvo.TomarDano({**dict(pacote), "origem": self, "origem_id": self.Uid}, sistema=sistema, tick=tick)

    def AlterarClima(self, clima: str) -> Dict[str, object]:
        return {"status": "ok", "clima": str(clima or "")}

    def ModificarArena(self, dados: Dict[str, object] | None = None) -> Dict[str, object]:
        return {"status": "ok", "arena": dict(dados or {})}

    def FimTurno(self, *, sistema=None, tick: int = 0) -> List[Dict[str, object]]:
        eventos: List[Dict[str, object]] = []
        vida_max = max(1.0, self.AtributosAtuais.get("Vida", 1.0))
        vida_perdida = max(0.0, vida_max - self.VidaAtual)

        for efeito in list(self.Efeitos):
            nome = str(efeito.get("nome") or "").strip().casefold()
            if nome == "queimado":
                eventos.append(self.TomarDano({"dano_final": vida_max * 0.05, "origem_id": efeito.get("origem_id", ""), "origem": None}, sistema=sistema, tick=tick))
            elif nome == "envenenado":
                eventos.append(self.TomarDano({"dano_final": vida_max * 0.08, "origem_id": efeito.get("origem_id", ""), "origem": None}, sistema=sistema, tick=tick))
            elif nome == "intoxicado":
                eventos.append(self.TomarDano({"dano_final": vida_max * 0.12, "origem_id": efeito.get("origem_id", ""), "origem": None}, sistema=sistema, tick=tick))
            elif nome == "regeneração" or nome == "regeneracao":
                eventos.append(self.ReceberCura(vida_perdida * 0.15, origem=self, motivo="Regeneracao"))
            elif nome == "abençoado" or nome == "abencoado":
                eventos.append(self.ReceberCura(vida_perdida * 0.05 * 1.3, origem=self, motivo="Abencoado"))

        energia_turno = self.obter_atributo("Ene")
        eventos.append(self.GanharEnergia(energia_turno, motivo="FimTurno"))
        self.Verifica()
        return eventos

    def passar_ticks(self, quantidade: int) -> List[Dict[str, object]]:
        eventos: List[Dict[str, object]] = []
        total = max(0, int(quantidade))
        if total <= 0:
            return eventos
        expirados = []
        for efeito in self.Efeitos:
            efeito["duracao_ticks"] = max(0, int(efeito.get("duracao_ticks", 0)) - total)
            if int(efeito.get("duracao_ticks", 0)) <= 0:
                expirados.append(str(efeito.get("nome") or ""))
        if expirados:
            self.Efeitos = [efeito for efeito in self.Efeitos if int(efeito.get("duracao_ticks", 0)) > 0]
            eventos.extend({"tipo": "efeito_expirado", "pokemon_id": self.Uid, "efeito": nome} for nome in expirados)
        self.Verifica()
        return eventos
