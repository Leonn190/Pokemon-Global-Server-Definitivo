from __future__ import annotations

import random
from typing import Dict, List

from SimuladorServerJogo.Batalha.IA.AdaptadorJogo import AdaptadorJogo
from SimuladorServerJogo.Batalha.IA.AvaliadorAcoes import AvaliadorAcoes
from SimuladorServerJogo.Batalha.IA.DificuldadeIA import normalizar_dificuldade, sortear_dificuldade
from SimuladorServerJogo.Batalha.IA.EstadoIA import AcaoCandidata, CombatenteIA, EstadoBatalhaIA
from SimuladorServerJogo.Batalha.IA.GeradorAcoes import GeradorAcoes


class BotBatalha:
    def __init__(
        self,
        *,
        gerador: GeradorAcoes | None = None,
        avaliador: AvaliadorAcoes | None = None,
        adaptador: AdaptadorJogo | None = None,
        rng: random.Random | None = None,
        dificuldade: Dict[str, float] | None = None,
        nome_dificuldade: str = "",
    ) -> None:
        self._rng = rng if isinstance(rng, random.Random) else random.Random()
        self.Gerador = gerador if isinstance(gerador, GeradorAcoes) else GeradorAcoes()
        self.Avaliador = avaliador if isinstance(avaliador, AvaliadorAcoes) else AvaliadorAcoes()
        self.Adaptador = adaptador if isinstance(adaptador, AdaptadorJogo) else AdaptadorJogo()

        if dificuldade is not None:
            self.NomeDificuldade = str(nome_dificuldade or "custom")
            self.Dificuldade = normalizar_dificuldade(dificuldade)
        else:
            self.NomeDificuldade, self.Dificuldade = sortear_dificuldade(self._rng)

    def escolher_acao(self, estado: EstadoBatalhaIA, executor_id: str) -> AcaoCandidata | None:
        executor = estado.buscar_combatente(executor_id)
        if executor is None or executor.lado != estado.lado_controlado:
            return None
        return self._escolher_para_executor(estado, executor)

    def escolher_jogadas(self, sistema, lado_controlado: str) -> List[Dict[str, object]]:
        estado = self.Adaptador.criar_estado(sistema, lado_controlado=lado_controlado, dificuldade=self.Dificuldade)
        acoes: List[AcaoCandidata] = []
        for executor in list(estado.aliados_ativos):
            acao = self._escolher_para_executor(estado, executor)
            if acao is not None:
                acoes.append(acao)
        return self.Adaptador.traduzir_acoes(acoes)

    def _escolher_para_executor(self, estado: EstadoBatalhaIA, executor: CombatenteIA) -> AcaoCandidata | None:
        candidatas = self.Gerador.gerar_para_executor(estado, executor)
        if not candidatas:
            return None

        avaliacoes = [self.Avaliador.avaliar(estado, acao) for acao in candidatas]
        melhor_score = max(avaliacao.score for avaliacao in avaliacoes)
        melhores = [avaliacao.acao for avaliacao in avaliacoes if abs(avaliacao.score - melhor_score) <= 1e-6]
        return melhores[self._rng.randrange(0, len(melhores))]
