from __future__ import annotations

import csv
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from SimuladorServerJogo.Batalha.Combate.DebugCombate import dbg_combate

from SimuladorServerJogo.Batalha.Combate.CalculadorDano import (
    ResultadoDano,
    atributo_total,
    calcular_cura,
    calcular_dano_por_efeito,
)
from SimuladorServerJogo.Batalha.Combate.ResolvedorCondicoes import (
    pode_receber_efeito_negativo,
    pode_receber_efeito_positivo,
)


@dataclass(slots=True)
class EstadoEfeito:
    nome: str
    codigo: int
    positivo: bool
    ticks_base: int
    ticks_restantes: int
    aplicador_id: str
    alvo_id: str
    stacks: int = 1
    dados: dict = field(default_factory=dict)


@dataclass(slots=True)
class ResultadoAplicacao:
    aplicado: bool
    motivo: str | None = None
    eventos: list[dict] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    dados: dict = field(default_factory=dict)


def _fnum(v: object, padrao: float = 0.0) -> float:
    try:
        if isinstance(v, str):
            return float(v.replace(",", "."))
        return float(v)
    except (TypeError, ValueError):
        return float(padrao)


def _norm(v: object) -> str:
    return str(v or "").strip().casefold()


def _obter(obj, nome: str, padrao=None):
    if obj is None:
        return padrao
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def _setar(obj, nome: str, valor) -> None:
    if isinstance(obj, dict):
        obj[nome] = valor
    else:
        setattr(obj, nome, valor)


def _id(entidade) -> str:
    return str(_obter(entidade, "Uid", _obter(entidade, "id", _obter(entidade, "ID", f"ent:{id(entidade)}"))))


FALLBACK_EFEITOS = {
    "Queimado": {"codigo": 1, "ticks_base": 60, "positivo": False},
    "Dormindo": {"codigo": 2, "ticks_base": 120, "positivo": False},
    "Envenenado": {"codigo": 3, "ticks_base": 60, "positivo": False},
    "Intoxicado": {"codigo": 4, "ticks_base": 60, "positivo": False},
    "Paralisado": {"codigo": 5, "ticks_base": 60, "positivo": False},
    "Vampirico": {"codigo": 6, "ticks_base": 60, "positivo": False},
    "Encharcado": {"codigo": 7, "ticks_base": 60, "positivo": False},
    "Quebrado": {"codigo": 8, "ticks_base": 60, "positivo": False},
    "Enfraquecido": {"codigo": 9, "ticks_base": 60, "positivo": False},
    "Confuso": {"codigo": 10, "ticks_base": 60, "positivo": False},
    "Congelado": {"codigo": 11, "ticks_base": 60, "positivo": False},
    "Atordoado": {"codigo": 12, "ticks_base": 60, "positivo": False},
    "Cauterizado": {"codigo": 13, "ticks_base": 60, "positivo": False},
    "Descarregado": {"codigo": 14, "ticks_base": 60, "positivo": False},
    "Bloqueado": {"codigo": 15, "ticks_base": 60, "positivo": False},
    "Amaldiçoado": {"codigo": 16, "ticks_base": 60, "positivo": False},
    "Recuo": {"codigo": 17, "ticks_base": 20, "positivo": False},
    "Enraizado": {"codigo": 18, "ticks_base": 60, "positivo": False},
    "Regeneração": {"codigo": 19, "ticks_base": 60, "positivo": True},
    "Abençoado": {"codigo": 20, "ticks_base": 60, "positivo": True},
    "Imortal": {"codigo": 21, "ticks_base": 60, "positivo": True},
    "Fortificado": {"codigo": 22, "ticks_base": 60, "positivo": True},
    "Amplificado": {"codigo": 23, "ticks_base": 60, "positivo": True},
    "Voando": {"codigo": 24, "ticks_base": 60, "positivo": True},
    "Flutuando": {"codigo": 25, "ticks_base": 60, "positivo": True},
    "Imune": {"codigo": 26, "ticks_base": 60, "positivo": True},
    "Energizado": {"codigo": 27, "ticks_base": 60, "positivo": True},
    "Preparado": {"codigo": 28, "ticks_base": 60, "positivo": True},
    "Provocando": {"codigo": 29, "ticks_base": 60, "positivo": True},
    "Furtivo": {"codigo": 30, "ticks_base": 60, "positivo": True},
    "Encantado": {"codigo": 31, "ticks_base": 60, "positivo": True},
    "Refletindo": {"codigo": 32, "ticks_base": 60, "positivo": True},
    "Evasivo": {"codigo": 33, "ticks_base": 60, "positivo": True},
    "Focado": {"codigo": 34, "ticks_base": 60, "positivo": True},
    "Protegido": {"codigo": 35, "ticks_base": 20, "positivo": True},
    "Imparavel": {"codigo": 36, "ticks_base": 60, "positivo": True},
}


class AplicadorEfeitos:
    def __init__(self, definicoes_efeitos=None):
        self.definicoes = dict(FALLBACK_EFEITOS)
        self.definicoes.update(self._carregar_definicoes_csv())
        if isinstance(definicoes_efeitos, dict):
            self.definicoes.update(definicoes_efeitos)
        self._handlers = {
            "dano": self._h_dano,
            "cura": self._h_cura,
            "status": self._h_status,
            "stack": self._h_stack,
            "recoil": self._h_recoil,
            "recoil_se_errar": self._h_recoil_se_errar,
            "execucao": self._h_execucao,
            "remover_variacoes_atributos": self._h_remover_variacoes,
            "recuperar_energia_gasta": self._h_recuperar_energia,
            "barreira": self._h_barreira,
            "buff_menor_defesa": self._h_buff_menor_defesa,
            "status_condicional_maior_atributo": self._h_status_condicional,
            "adaptar_tipo_clima": self._h_noop,
            "bonus_se_clima_ativo": self._h_noop,
            "bonus_primeiro_ataque_turno": self._h_noop,
            "recuo_se_critico": self._h_recuo_se_critico,
            "limite_crc": self._h_limite_crc,
        }

    def _carregar_definicoes_csv(self) -> dict:
        caminho = Path(__file__).resolve().parents[3] / "Dados" / "Pokemon Global Server - Efeitos.csv"
        if not caminho.exists():
            return {}
        saida = {}
        with caminho.open("r", encoding="utf-8-sig") as f:
            for linha in csv.DictReader(f):
                nome = str(linha.get("Efeito") or "").strip()
                if not nome:
                    continue
                ticks = 60
                for c in ("Ticks Base", "TicksBase", "Duracao", "Duração", "Ticks"):
                    if linha.get(c):
                        ticks = int(_fnum(linha.get(c), 60))
                        break
                base = self.definicoes.get(nome, {"codigo": 0, "positivo": False})
                saida[nome] = {
                    "codigo": int(_fnum(linha.get("Código", base.get("codigo", 0)), base.get("codigo", 0))),
                    "ticks_base": max(1, ticks),
                    "positivo": bool(base.get("positivo", False)),
                }
        return saida

    def aplicar_efeitos(self, efeitos, contexto) -> list[ResultadoAplicacao]:
        return [self.aplicar_efeito(efeito, contexto) for efeito in list(efeitos or [])]

    def aplicar_efeito(self, efeito, contexto) -> ResultadoAplicacao:
        ef = dict(efeito or {})
        tipo = _norm(ef.get("tipo"))
        handler = self._handlers.get(tipo)
        if not callable(handler):
            return ResultadoAplicacao(aplicado=False, motivo="tipo_nao_suportado", logs=[f"efeito:{tipo}"])
        dbg_combate("AplicadorEfeitos", "efeito recebido", tipo=tipo)
        return handler(ef, contexto or {})

    def aplicar_estado(self, alvo, nome_efeito, aplicador=None, contexto=None, positivo=None) -> ResultadoAplicacao:
        nome = str(nome_efeito or "").strip()
        if not nome:
            return ResultadoAplicacao(aplicado=False, motivo="status_vazio")
        definicao = self.definicoes.get(nome, {"codigo": 0, "ticks_base": 60, "positivo": bool(positivo)})
        eh_positivo = bool(definicao.get("positivo", False) if positivo is None else positivo)

        if eh_positivo:
            ok, motivo = pode_receber_efeito_positivo(alvo)
        else:
            ok, motivo = pode_receber_efeito_negativo(alvo)
        if not ok:
            return ResultadoAplicacao(aplicado=False, motivo=motivo)

        lista = list(_obter(alvo, "Efeitos", []))
        existente = next((e for e in lista if _norm(e.get("nome")) == _norm(nome)), None)
        ticks_base = int(definicao.get("ticks_base", 60))
        ticks_rest = self._calcular_duracao_status(ticks_base, aplicador, alvo, eh_positivo)
        if existente is not None:
            existente["ticks_restantes"] = max(int(existente.get("ticks_restantes", 0)), ticks_rest)
            existente["stacks"] = int(existente.get("stacks", 1)) + 1
            _setar(alvo, "Efeitos", lista)
            return ResultadoAplicacao(aplicado=True, eventos=[{"tipo": "status_renovado", "nome": nome}])

        estado = EstadoEfeito(
            nome=nome,
            codigo=int(definicao.get("codigo", 0)),
            positivo=eh_positivo,
            ticks_base=ticks_base,
            ticks_restantes=ticks_rest,
            aplicador_id=_id(aplicador),
            alvo_id=_id(alvo),
            stacks=1,
            dados={},
        )
        lista.append(asdict(estado))
        if len(lista) > 3:
            idx = min(range(len(lista)), key=lambda i: int(lista[i].get("ticks_restantes", 0)))
            removido = lista.pop(idx)
            evento = {"tipo": "status_substituido", "removido": removido.get("nome")}
        else:
            evento = {"tipo": "status_aplicado", "nome": nome}
        _setar(alvo, "Efeitos", lista)
        return ResultadoAplicacao(aplicado=True, eventos=[evento])

    def atualizar_efeitos_por_tick(self, pokemons, contexto=None, ticks=1) -> list[dict]:
        eventos: list[dict] = []
        for _ in range(max(1, int(ticks))):
            for pkm in list(pokemons or []):
                lista = list(_obter(pkm, "Efeitos", []))
                nova = []
                for ef in lista:
                    nome = str(ef.get("nome") or "")
                    rest = int(ef.get("ticks_restantes", 0)) - 1
                    ef["ticks_restantes"] = rest
                    self._processar_tick_efeito(pkm, ef, eventos)
                    if rest <= 0:
                        eventos.append({"tipo": "efeito_expirou", "alvo": _id(pkm), "efeito": nome})
                    else:
                        nova.append(ef)
                _setar(pkm, "Efeitos", nova)
        return eventos

    def aplicar_resultado_dano(self, resultado_dano, contexto) -> ResultadoAplicacao:
        r: ResultadoDano = resultado_dano
        alvo = (contexto or {}).get("alvo")
        atacante = (contexto or {}).get("atacante")
        if alvo is None:
            return ResultadoAplicacao(aplicado=False, motivo="alvo_ausente")

        eventos = []
        dano = _fnum(r.dano_vida, 0.0)
        if r.bloqueado_por_barreira:
            _setar(alvo, "Barreira", 0.0)
            eventos.append({"tipo": "barreira_quebrada", "alvo": _id(alvo), "valor": r.dano_barreira})
            dano = 0.0

        efeitos_alvo = list(_obter(alvo, "Efeitos", []))
        if any(_norm(e.get("nome")) == "evasivo" for e in efeitos_alvo) and dano > 0:
            dano = 0.0
            efeitos_alvo = [e for e in efeitos_alvo if _norm(e.get("nome")) != "evasivo"]
            eventos.append({"tipo": "evasivo_consumido", "alvo": _id(alvo)})

        if any(_norm(e.get("nome")) == "preparado" for e in efeitos_alvo) and dano > 0:
            dano *= 0.4
            vel = atributo_total(alvo, "Vel")
            eventos.append({"tipo": "contra_dano_preparado", "alvo": _id(alvo), "valor": vel * 0.4})

        if any(_norm(e.get("nome")) == "refletindo" for e in efeitos_alvo) and dano > 0:
            refletido = dano * 0.75
            dano *= 0.25
            eventos.append({"tipo": "dano_refletido", "origem": _id(alvo), "alvo": _id(atacante), "valor": refletido})

        vida_atual = _fnum(_obter(alvo, "VidaAtual", 0.0), 0.0)
        vida_pos = max(0.0, vida_atual - dano)
        if any(_norm(e.get("nome")) == "imortal" for e in efeitos_alvo) and dano > 0 and vida_pos <= 0:
            vida_pos = 1.0
            efeitos_alvo = [e for e in efeitos_alvo if _norm(e.get("nome")) != "imortal"]
            eventos.append({"tipo": "imortal_consumido", "alvo": _id(alvo)})

        _setar(alvo, "VidaAtual", vida_pos)

        if dano > 0:
            efeitos_alvo = [e for e in efeitos_alvo if _norm(e.get("nome")) != "dormindo"]
            vamp = atributo_total(atacante, "Vamp") if atacante is not None else 0.0
            if vamp > 0 and atacante is not None:
                cura = dano * (vamp / 100.0)
                self.aplicar_cura(atacante, atacante, cura)
            if any(_norm(e.get("nome")) == "vampirico" for e in efeitos_alvo) and atacante is not None:
                self.aplicar_cura(atacante, atacante, dano * 0.25)

        _setar(alvo, "Efeitos", efeitos_alvo)
        dbg_combate("AplicadorEfeitos", "dano/vida/barreira antes e depois", dano=dano, vida_pos=vida_pos)
        return ResultadoAplicacao(aplicado=True, eventos=eventos, dados={"dano_aplicado": dano})

    def aplicar_cura(self, aplicador, alvo, valor, contexto=None) -> ResultadoAplicacao:
        _ = aplicador, contexto
        cura = _fnum(valor, 0.0)
        efeitos = list(_obter(alvo, "Efeitos", []))
        if any(_norm(e.get("nome")) == "queimado" for e in efeitos):
            cura *= 0.65
        if any(_norm(e.get("nome")) == "abençoado" for e in efeitos):
            cura *= 1.35
        vida = _fnum(_obter(alvo, "VidaAtual", 0.0), 0.0)
        vida_max = max(1.0, atributo_total(alvo, "Vida"))
        nova = min(vida_max, vida + max(0.0, cura))
        _setar(alvo, "VidaAtual", nova)
        return ResultadoAplicacao(aplicado=True, dados={"cura": nova - vida})

    def aplicar_barreira(self, alvo, valor, contexto=None) -> ResultadoAplicacao:
        _ = contexto
        atual = _fnum(_obter(alvo, "Barreira", 0.0), 0.0)
        nova = max(0.0, atual + _fnum(valor, 0.0))
        _setar(alvo, "Barreira", nova)
        return ResultadoAplicacao(aplicado=True, dados={"barreira": nova})

    def _calcular_duracao_status(self, ticks_base: int, aplicador, alvo, positivo: bool) -> int:
        mag_apl = atributo_total(aplicador, "Mag") if aplicador is not None else 0.0
        mag_alvo = atributo_total(alvo, "Mag") if alvo is not None else 0.0
        if positivo:
            dur = ticks_base + (0.5 * mag_apl)
            if self._tem_efeito(alvo, "Encantado"):
                dur *= 1.5
        else:
            dur = max(ticks_base * 0.5, ticks_base + mag_apl - mag_alvo)
            if self._tem_efeito(alvo, "Amaldiçoado"):
                dur *= 1.5
        return max(1, int(dur))

    def _tem_efeito(self, entidade, nome: str) -> bool:
        return any(_norm(e.get("nome")) == _norm(nome) for e in list(_obter(entidade, "Efeitos", [])))

    def _processar_tick_efeito(self, pkm, ef, eventos: list[dict]) -> None:
        nome = _norm(ef.get("nome"))
        ticks_rest = int(ef.get("ticks_restantes", 0))
        if ticks_rest <= 0:
            return
        if ticks_rest % 10 == 0:
            vida_max = max(1.0, atributo_total(pkm, "Vida"))
            vida = _fnum(_obter(pkm, "VidaAtual", 0.0), 0.0)
            if nome == "queimado":
                _setar(pkm, "VidaAtual", max(0.0, vida - vida_max * 0.01))
            elif nome == "envenenado":
                _setar(pkm, "VidaAtual", max(0.0, vida - vida_max * 0.02))
            elif nome == "intoxicado":
                _setar(pkm, "VidaAtual", max(0.0, vida - vida_max * 0.03))
            elif nome == "regeneração":
                perdido = max(0.0, vida_max - vida)
                _setar(pkm, "VidaAtual", min(vida_max, vida + perdido * 0.05))
            elif nome == "abençoado":
                perdido = max(0.0, vida_max - vida)
                _setar(pkm, "VidaAtual", min(vida_max, vida + perdido * 0.03))
        if nome == "intoxicado" and ticks_rest % 20 == 0:
            eventos.append({"tipo": "gas_intoxicado", "origem": _id(pkm), "alcance": atributo_total(pkm, "RaioColisao") * 2})

    # handlers genéricos
    def _h_dano(self, efeito, contexto) -> ResultadoAplicacao:
        atacante = contexto.get("usuario")
        alvo = contexto.get("alvo")
        rd = calcular_dano_por_efeito(
            atacante=atacante,
            defensor=alvo,
            efeito=efeito,
            ataque_spec=contexto.get("ataque_spec"),
            contexto=contexto,
        )
        return self.aplicar_resultado_dano(rd, {"alvo": alvo, "atacante": atacante})

    def _h_cura(self, efeito, contexto) -> ResultadoAplicacao:
        aplicador = contexto.get("usuario")
        alvo = contexto.get("alvo")
        total = calcular_cura(aplicador, alvo, efeito, contexto=contexto)
        bonus_por_stack = _fnum(efeito.get("bonus_por_stack", 0.0), 0.0)
        if bonus_por_stack:
            stacks = int(efeito.get("stacks", 0) or contexto.get("stacks", 0) or 0)
            total += max(0, stacks) * bonus_por_stack
        return self.aplicar_cura(aplicador, alvo, total)

    def _h_status(self, efeito, contexto) -> ResultadoAplicacao:
        return self.aplicar_estado(contexto.get("alvo"), efeito.get("status") or efeito.get("nome"), aplicador=contexto.get("usuario"), contexto=contexto)

    def _h_stack(self, efeito, contexto) -> ResultadoAplicacao:
        return self.aplicar_estado(contexto.get("alvo"), efeito.get("status") or "Stack", aplicador=contexto.get("usuario"), contexto=contexto)

    def _h_recoil(self, efeito, contexto) -> ResultadoAplicacao:
        valor = _fnum(efeito.get("valor", 0.0), 0.0) * _fnum(contexto.get("dano_causado", 0.0), 0.0)
        rd = ResultadoDano(dano_final=valor, dano_vida=valor)
        return self.aplicar_resultado_dano(rd, {"alvo": contexto.get("usuario"), "atacante": contexto.get("usuario")})

    def _h_recoil_se_errar(self, efeito, contexto) -> ResultadoAplicacao:
        if bool(contexto.get("acertou", True)):
            return ResultadoAplicacao(aplicado=False, motivo="nao_errou")
        return self._h_recoil(efeito, contexto)

    def _h_execucao(self, efeito, contexto) -> ResultadoAplicacao:
        alvo = contexto.get("alvo")
        vida = _fnum(_obter(alvo, "VidaAtual", 0.0), 0.0)
        rd = ResultadoDano(dano_final=vida, dano_vida=vida)
        return self.aplicar_resultado_dano(rd, {"alvo": alvo, "atacante": contexto.get("usuario")})

    def _h_remover_variacoes(self, efeito, contexto) -> ResultadoAplicacao:
        _ = efeito
        alvo = contexto.get("alvo")
        for campo in ("VariacoesFixas", "VariacoesTemporarias"):
            val = _obter(alvo, campo, None)
            if isinstance(val, dict):
                for k in list(val.keys()):
                    val[k] = 0.0
        return ResultadoAplicacao(aplicado=True)

    def _h_recuperar_energia(self, efeito, contexto) -> ResultadoAplicacao:
        alvo = contexto.get("alvo")
        gasto = _fnum(contexto.get("energia_gasta", 0.0), 0.0)
        ganho = gasto * _fnum(efeito.get("valor", 0.0), 0.0)
        energia = _fnum(_obter(alvo, "Energia", 0.0), 0.0)
        energia_max = _fnum(_obter(alvo, "EnergiaMax", 100.0), 100.0)
        if self._tem_efeito(alvo, "Descarregado"):
            ganho *= 0.5
        if self._tem_efeito(alvo, "Energizado"):
            ganho *= 1.5
        sem_limite = self._tem_efeito(alvo, "Energizado")
        _setar(alvo, "Energia", energia + ganho if sem_limite else min(energia_max, energia + ganho))
        return ResultadoAplicacao(aplicado=True)

    def _h_barreira(self, efeito, contexto) -> ResultadoAplicacao:
        alvo = contexto.get("alvo")
        valor = _fnum(efeito.get("valor", 0.0), 0.0)
        aplicador = contexto.get("usuario")
        for comp in list(efeito.get("componentes") or []):
            valor += atributo_total(aplicador, str(comp.get("atributo") or "Mag"), permitir_negativo=True) * _fnum(comp.get("escala", 0.0), 0.0)
        return self.aplicar_barreira(alvo, valor)

    def _h_buff_menor_defesa(self, efeito, contexto) -> ResultadoAplicacao:
        _ = efeito
        alvo = contexto.get("alvo")
        bonus = atributo_total(contexto.get("usuario"), "Mag") * 0.10
        defs = {"Def": atributo_total(alvo, "Def"), "SpD": atributo_total(alvo, "SpD")}
        menor = min(defs, key=defs.get)
        bloco = _obter(alvo, "VariacoesFixas", {})
        if isinstance(bloco, dict):
            bloco[menor] = _fnum(bloco.get(menor, 0.0), 0.0) + bonus
        return ResultadoAplicacao(aplicado=True, dados={"atributo": menor, "bonus": bonus})

    def _h_status_condicional(self, efeito, contexto) -> ResultadoAplicacao:
        cond = dict(efeito.get("condicao") or {})
        alvo = contexto.get("alvo")
        vida_pct = _fnum(_obter(alvo, "VidaAtual", 0.0), 0.0) / max(1.0, atributo_total(alvo, "Vida"))
        limite = _fnum(cond.get("vida_pct_menor_que", 1.0), 1.0)
        if vida_pct >= limite:
            return ResultadoAplicacao(aplicado=False, motivo="condicao_falhou")
        attr_a = atributo_total(alvo, str(cond.get("atributo_a") or "SpA"))
        attr_b = atributo_total(alvo, str(cond.get("atributo_b") or "Atk"))
        nome = cond.get("status_se_maior") if attr_a > attr_b else cond.get("status_caso_contrario")
        return self.aplicar_estado(alvo, nome, aplicador=contexto.get("usuario"), contexto=contexto)

    def _h_recuo_se_critico(self, efeito, contexto) -> ResultadoAplicacao:
        _ = efeito
        if not bool(contexto.get("foi_critico", False)):
            return ResultadoAplicacao(aplicado=False, motivo="nao_critico")
        return self.aplicar_estado(contexto.get("alvo"), "Recuo", aplicador=contexto.get("usuario"), contexto=contexto, positivo=False)

    def _h_limite_crc(self, efeito, contexto) -> ResultadoAplicacao:
        contexto.setdefault("dados", {})["limite_crc"] = _fnum(efeito.get("valor", efeito.get("limite", 100.0)), 100.0)
        return ResultadoAplicacao(aplicado=True)

    def _h_noop(self, efeito, contexto) -> ResultadoAplicacao:
        _ = efeito, contexto
        return ResultadoAplicacao(aplicado=True, motivo="noop_fase4")
