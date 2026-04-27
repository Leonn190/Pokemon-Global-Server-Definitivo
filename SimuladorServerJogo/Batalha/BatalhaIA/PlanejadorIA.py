from __future__ import annotations

import copy
from typing import Iterable

from .AvaliadorIA import AvaliadorIA
from .ContextoIA import ContextoIA
from .GeradorCandidatosIA import CandidatoIA, GeradorCandidatosIA
from .SimuladorIA import SimuladorIA


class PlanejadorIA:
    def __init__(self, gerador: GeradorCandidatosIA | None = None, avaliador: AvaliadorIA | None = None, simulador: SimuladorIA | None = None):
        self.gerador = gerador or GeradorCandidatosIA()
        self.avaliador = avaliador or AvaliadorIA()
        self.simulador = simulador or SimuladorIA()

    def planejar(self, contexto: ContextoIA) -> list[dict]:
        candidatos = self.gerador.gerar(contexto)
        if not candidatos:
            return []
        for cand in candidatos:
            self.avaliador.avaliar(contexto, cand)

        candidatos = [c for c in candidatos if c.score > -900.0]
        if not candidatos:
            return []
        candidatos.sort(key=lambda c: c.score, reverse=True)
        candidatos = self._filtrar_por_qualidade(contexto, candidatos)

        combo_simulado = self.simulador.refinar(contexto, candidatos, contexto.rng)
        if combo_simulado:
            escolhidos = combo_simulado
        else:
            escolhidos = self._greedy(contexto, candidatos)

        return self._acoes_finais(contexto, escolhidos)

    def _filtrar_por_qualidade(self, contexto: ContextoIA, candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        qualidade = contexto.config.dificuldade.qualidade_decisao
        limite = max(8, int(contexto.config.max_candidatos_planejamento))
        if qualidade >= 0.85:
            return candidatos[:limite]
        if qualidade <= 0.15:
            # IA fraca enxerga menos opcoes e aceita bobagens.
            pool = candidatos[: max(6, limite // 3)]
            contexto.rng.shuffle(pool)
            return pool
        # Quanto maior qualidade, mais candidatos bons entram.
        n = max(8, int((limite * (0.35 + qualidade * 0.65))))
        pool = candidatos[:n]
        desordem = 1.0 - contexto.config.dificuldade.aleatoriedade_controlada
        if desordem > 0.05:
            faixa = max(2, int(len(pool) * desordem * 0.55))
            trecho = pool[:faixa]
            contexto.rng.shuffle(trecho)
            pool[:faixa] = trecho
        return pool

    def _greedy(self, contexto: ContextoIA, candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        escolhidos: list[CandidatoIA] = []
        contagem: dict[str, int] = {}
        energia_restante: dict[str, float] = {}
        dano_previsto: dict[str, float] = {}
        for cand in candidatos:
            if len(escolhidos) >= contexto.config.max_acoes_por_lado:
                break
            pid = cand.pokemon_id
            if not pid:
                continue
            if contagem.get(pid, 0) >= contexto.config.max_acoes_por_pokemon:
                continue
            if self._conflita_com_escolhidos(contexto, cand, escolhidos):
                continue
            ordem = contagem.get(pid, 0) + 1
            custo = float(cand.custo_base or 0.0) * (1.10 if ordem >= 2 else 1.0)
            energia = energia_restante.setdefault(pid, contexto.energia_atual(cand.pokemon))
            if energia < custo:
                continue
            if self._overkill_grave(contexto, cand, dano_previsto):
                continue
            energia_restante[pid] = energia - custo
            contagem[pid] = ordem
            escolhidos.append(cand)
            alvo_id = (cand.estimativa or {}).get("alvo_principal_id")
            if alvo_id:
                dano_previsto[alvo_id] = dano_previsto.get(alvo_id, 0.0) + float(cand.estimativa.get("melhor_dano") or 0.0)
        return escolhidos

    def _conflita_com_escolhidos(self, contexto: ContextoIA, cand: CandidatoIA, escolhidos: Iterable[CandidatoIA]) -> bool:
        for outro in escolhidos:
            if cand.pokemon_id == outro.pokemon_id:
                if cand.tipo == "troca_reserva" or outro.tipo == "troca_reserva":
                    return True
            if cand.tipo == "troca_reserva":
                reserva_id = cand.acao.get("pokemon_reserva_id") or cand.acao.get("troca_reserva_id")
                if reserva_id and reserva_id == outro.pokemon_id:
                    return True
        return False

    def _overkill_grave(self, contexto: ContextoIA, cand: CandidatoIA, dano_previsto: dict[str, float]) -> bool:
        if cand.categoria != "dano":
            return False
        alvo_id = (cand.estimativa or {}).get("alvo_principal_id")
        if not alvo_id:
            return False
        alvo = contexto.obter_pokemon(alvo_id)
        if alvo is None:
            return False
        vida = contexto.vida_atual(alvo)
        ja = dano_previsto.get(alvo_id, 0.0)
        margem = 1.0 + contexto.config.margem_overkill
        if ja >= vida * margem and contexto.config.dificuldade.foco_finalizacao > 0.45:
            return True
        return False

    def _acoes_finais(self, contexto: ContextoIA, escolhidos: list[CandidatoIA]) -> list[dict]:
        # Ordem local ainda pode ser rearranjada pelo ColetorAcoes, mas deixamos limpa.
        saida: list[dict] = []
        contagem: dict[str, int] = {}
        for idx, cand in enumerate(escolhidos[: contexto.config.max_acoes_por_lado], start=1):
            acao = cand.copia_acao()
            pid = str(acao.get("pokemon_id") or "")
            contagem[pid] = contagem.get(pid, 0) + 1
            acao["ordem_local"] = idx
            acao["ordem_pokemon"] = contagem[pid]
            acao.setdefault("origem_ia", True)
            acao.setdefault("score_ia", round(float(cand.score or 0.0), 4))
            if cand.estimativa:
                acao.setdefault("estimativa_ia", copy.deepcopy(cand.estimativa))
            saida.append(acao)
        return saida
