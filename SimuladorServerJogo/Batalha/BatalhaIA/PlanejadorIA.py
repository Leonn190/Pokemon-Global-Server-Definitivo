from __future__ import annotations

import copy
from typing import Iterable

from .AvaliadorIA import AvaliadorIA
from .ContextoIA import ContextoIA
from .GeradorAcoesIA import CandidatoIA, GeradorAcoesIA
from .MacroSimulador import MacroSimulador
from .MicroSimulador import MicroSimulador


class PlanejadorIA:
    """Orquestra Inteligência → Micro → Macro → Tática → Jogada base."""

    def __init__(
        self,
        gerador: GeradorAcoesIA | None = None,
        avaliador: AvaliadorIA | None = None,
        micro: MicroSimulador | None = None,
        macro: MacroSimulador | None = None,
    ):
        self.gerador = gerador or GeradorAcoesIA()
        self.avaliador = avaliador or AvaliadorIA()
        self.micro = micro or MicroSimulador()
        self.macro = macro or MacroSimulador()

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
        candidatos = self._filtrar_por_profissionalismo(contexto, candidatos)

        self._rodar_micro_simulacoes(contexto, candidatos)
        candidatos.sort(key=lambda c: c.score, reverse=True)

        base = self._rodar_macro_simulacoes(contexto, candidatos)
        if not base:
            base = self._greedy(contexto, candidatos)

        base = self._aplicar_tatica(contexto, base, candidatos)
        return self._acoes_finais(contexto, base)

    def _filtrar_por_profissionalismo(self, contexto: ContextoIA, candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        profissionalismo = contexto.config.dificuldade.profissionalismo
        limite = max(8, int(contexto.config.max_candidatos_planejamento))
        if profissionalismo >= 0.85:
            return candidatos[:limite]
        if profissionalismo <= 0.15:
            pool = candidatos[: max(6, limite // 3)]
            contexto.rng.shuffle(pool)
            return pool

        n = max(8, int(limite * (0.35 + profissionalismo * 0.65)))
        pool = candidatos[:n]
        desordem = 1.0 - profissionalismo
        if desordem > 0.05 and len(pool) > 2:
            faixa = max(2, int(len(pool) * desordem * 0.45))
            trecho = pool[:faixa]
            contexto.rng.shuffle(trecho)
            pool[:faixa] = trecho
        return pool

    def _rodar_micro_simulacoes(self, contexto: ContextoIA, candidatos: list[CandidatoIA]) -> None:
        budget = min(len(candidatos), int(contexto.config.orcamento_micro_simulacoes))
        if budget <= 0:
            return

        # Prioriza ações fortes e ações com metadados pedindo simulação.
        ordenados = sorted(
            candidatos,
            key=lambda c: (
                float((c.metadados or {}).get("prioridade_simulacao") or 0.0),
                float(c.score or 0.0),
            ),
            reverse=True,
        )
        for cand in ordenados[:budget]:
            resultado = self.micro.simular(contexto, cand)
            ajuste = self.avaliador.avaliar_resultado_micro(contexto, cand, resultado)
            cand.score = float(cand.score or 0.0) + ajuste
            cand.estimativa.setdefault("micro_simulacao", resultado)
            cand.estimativa.setdefault("ajuste_micro", round(ajuste, 4))

    def _rodar_macro_simulacoes(self, contexto: ContextoIA, candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        combo = self.macro.refinar(contexto, candidatos, contexto.rng)
        if combo:
            return combo
        return []

    def _aplicar_tatica(self, contexto: ContextoIA, base: list[CandidatoIA], candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        budget = int(contexto.config.orcamento_tatica)
        if budget <= 0 or not base or not candidatos:
            return base

        melhor = list(base)
        melhor_score = self.macro.simular_jogada(contexto, melhor).get("score", float("-inf"))
        tentativas = 0

        # Variações locais: substituir ação fraca por candidato parecido ou recarga/movimento melhor.
        for idx, atual in enumerate(list(melhor)):
            if tentativas >= budget:
                break
            similares = self._candidatos_taticos(contexto, atual, candidatos)
            for novo in similares[: max(1, budget - tentativas)]:
                variacao = list(melhor)
                variacao[idx] = novo
                variacao = self.macro._normalizar_combo(contexto, variacao)
                if not variacao:
                    continue
                resultado = self.macro.simular_jogada(contexto, variacao)
                score = float(resultado.get("score", float("-inf")))
                tentativas += 1
                if score > melhor_score:
                    melhor_score = score
                    melhor = variacao
                if tentativas >= budget:
                    break

        return melhor

    def _candidatos_taticos(self, contexto: ContextoIA, atual: CandidatoIA, candidatos: list[CandidatoIA]) -> list[CandidatoIA]:
        saida: list[CandidatoIA] = []
        alvo_atual = (atual.estimativa or {}).get("alvo_principal_id")
        for cand in candidatos:
            if cand is atual:
                continue
            if cand.pokemon_id == atual.pokemon_id:
                saida.append(cand)
                continue
            if alvo_atual and (cand.estimativa or {}).get("alvo_principal_id") == alvo_atual:
                saida.append(cand)
                continue
            if atual.categoria == cand.categoria and cand.score >= atual.score * 0.85:
                saida.append(cand)
        saida.sort(key=lambda c: c.score, reverse=True)
        return saida

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
        if ja >= vida * margem and contexto.config.dificuldade.raciocinio > 0.45:
            return True
        return False

    def _acoes_finais(self, contexto: ContextoIA, escolhidos: list[CandidatoIA]) -> list[dict]:
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
                estimativa = copy.deepcopy(cand.estimativa)
                # Não despeja cópia gigante de simulação real no pacote da jogada.
                if isinstance(estimativa.get("micro_simulacao"), dict):
                    estimativa["micro_simulacao"] = {
                        "origem": estimativa["micro_simulacao"].get("origem"),
                        "dano_causado": estimativa["micro_simulacao"].get("dano_causado"),
                        "cura_feita": estimativa["micro_simulacao"].get("cura_feita"),
                        "alvos_mortos": estimativa["micro_simulacao"].get("alvos_mortos"),
                    }
                acao.setdefault("estimativa_ia", estimativa)
            saida.append(acao)
        return saida
