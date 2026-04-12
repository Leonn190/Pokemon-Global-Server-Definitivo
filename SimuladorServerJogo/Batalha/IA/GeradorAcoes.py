from __future__ import annotations

from typing import List

from SimuladorServerJogo.Batalha.IA.EstadoIA import AcaoCandidata, CombatenteIA, EstadoBatalhaIA, PosicaoIA


class GeradorAcoes:
    def gerar_para_executor(self, estado: EstadoBatalhaIA, executor: CombatenteIA) -> List[AcaoCandidata]:
        if not executor.pode_agir():
            return [AcaoCandidata(tipo_acao="esperar", executor_id=executor.uid, prioridade=-1.0)]

        acoes: List[AcaoCandidata] = []
        acoes.extend(self._gerar_acoes_habilidade(estado, executor))
        acoes.extend(self._gerar_acoes_troca(estado, executor))
        if not acoes:
            acoes.append(AcaoCandidata(tipo_acao="esperar", executor_id=executor.uid, prioridade=-0.25))
        return acoes

    def _gerar_acoes_habilidade(self, estado: EstadoBatalhaIA, executor: CombatenteIA) -> List[AcaoCandidata]:
        acoes: List[AcaoCandidata] = []
        inimigos = [alvo for alvo in estado.inimigos_ativos if not alvo.fora_de_combate]
        aliados = [aliado for aliado in estado.aliados_ativos if not aliado.fora_de_combate]
        for habilidade in executor.habilidades:
            if float(habilidade.custo_energia) > float(executor.energia):
                continue

            if habilidade.efeito_principal in {"cura", "protecao"}:
                for aliado in aliados:
                    if habilidade.efeito_principal == "cura" and aliado.percentual_vida >= 0.98:
                        continue
                    acoes.append(
                        AcaoCandidata(
                            tipo_acao="usar_habilidade",
                            executor_id=executor.uid,
                            acao_chave=habilidade.chave,
                            habilidade_nome=habilidade.nome,
                            estilo=habilidade.estilo,
                            destino_posicao=self._destino_por_estilo(habilidade.estilo, aliado.posicao),
                            alvo_ids=[aliado.uid] if habilidade.estilo == "alvo" else [],
                            custo_energia=habilidade.custo_energia,
                            prioridade=0.15 if habilidade.efeito_principal == "protecao" else 0.2,
                            tags=[habilidade.efeito_principal, "suporte"],
                            dados_extras={"efeito_principal": habilidade.efeito_principal, "alvo_preferencial": "aliado"},
                            habilidade_bruta=dict(habilidade.dados_brutos),
                        )
                    )
                continue

            if habilidade.efeito_principal == "mobilidade":
                alvo_ref = self._alvo_mais_proximo(executor, inimigos)
                destino = alvo_ref.posicao if alvo_ref is not None else executor.posicao
                acoes.append(
                    AcaoCandidata(
                        tipo_acao="usar_habilidade",
                        executor_id=executor.uid,
                        acao_chave=habilidade.chave,
                        habilidade_nome=habilidade.nome,
                        estilo=habilidade.estilo,
                        destino_posicao=destino,
                        custo_energia=habilidade.custo_energia,
                        prioridade=0.1,
                        tags=["mobilidade"],
                        dados_extras={"efeito_principal": habilidade.efeito_principal},
                        habilidade_bruta=dict(habilidade.dados_brutos),
                    )
                )
                continue

            for inimigo in inimigos:
                acoes.append(
                    AcaoCandidata(
                        tipo_acao="usar_habilidade",
                        executor_id=executor.uid,
                        acao_chave=habilidade.chave,
                        habilidade_nome=habilidade.nome,
                        estilo=habilidade.estilo,
                        destino_posicao=self._destino_por_estilo(habilidade.estilo, inimigo.posicao),
                        alvo_ids=[inimigo.uid] if habilidade.estilo == "alvo" else [],
                        custo_energia=habilidade.custo_energia,
                        prioridade=0.05,
                        tags=["dano", habilidade.estilo],
                        dados_extras={"efeito_principal": habilidade.efeito_principal, "alvo_preferencial": "inimigo"},
                        habilidade_bruta=dict(habilidade.dados_brutos),
                    )
                )
        return acoes

    def _gerar_acoes_troca(self, estado: EstadoBatalhaIA, executor: CombatenteIA) -> List[AcaoCandidata]:
        if executor.percentual_vida > 0.35 and executor.percentual_energia > 0.1:
            return []
        reservas_validas = [reserva for reserva in estado.aliados_reserva if not reserva.fora_de_combate]
        reservas_validas.sort(key=lambda reserva: (reserva.percentual_vida, reserva.percentual_energia), reverse=True)
        acoes: List[AcaoCandidata] = []
        for reserva in reservas_validas[:2]:
            acoes.append(
                AcaoCandidata(
                    tipo_acao="trocar",
                    executor_id=executor.uid,
                    troca_reserva_id=reserva.uid,
                    prioridade=0.12,
                    tags=["troca", "protecao"],
                )
            )
        return acoes

    def _destino_por_estilo(self, estilo: str, posicao: PosicaoIA) -> PosicaoIA | None:
        if estilo in {"movimento", "area", "tiro", "zona"}:
            return posicao
        return None

    def _alvo_mais_proximo(self, executor: CombatenteIA, inimigos: List[CombatenteIA]) -> CombatenteIA | None:
        if not inimigos:
            return None
        return min(inimigos, key=lambda alvo: executor.posicao.distancia_ate(alvo.posicao))
