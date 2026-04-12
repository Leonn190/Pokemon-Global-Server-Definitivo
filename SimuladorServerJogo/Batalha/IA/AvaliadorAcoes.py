from __future__ import annotations

from typing import Dict, List

from SimuladorServerJogo.Batalha.IA.EstadoIA import AcaoCandidata, CombatenteIA, EstadoBatalhaIA, ResultadoAvaliacaoIA


_TYPE_CHART: Dict[str, Dict[str, float]] = {
    "normal": {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5, "ice": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5},
    "poison": {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0, "fairy": 2.0},
    "ground": {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying": {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost": {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark": {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
    "fairy": {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5},
}


class AvaliadorAcoes:
    def avaliar(self, estado: EstadoBatalhaIA, acao: AcaoCandidata) -> ResultadoAvaliacaoIA:
        executor = estado.buscar_combatente(acao.executor_id)
        if executor is None:
            return ResultadoAvaliacaoIA(acao=acao, score=-999.0, motivos=["executor_invalido"])

        componentes: Dict[str, float] = {}
        motivos: List[str] = []

        if acao.tipo_acao == "esperar":
            score = -1.0 if executor.pode_agir() else 0.5
            return ResultadoAvaliacaoIA(acao=acao, score=score, componentes={"passividade": score}, motivos=["esperar"])

        if acao.tipo_acao == "trocar":
            score_troca = self._avaliar_troca(estado, executor, acao)
            componentes["troca"] = score_troca
            return ResultadoAvaliacaoIA(acao=acao, score=score_troca, componentes=componentes, motivos=["troca"])

        alvo = self._resolver_alvo(estado, acao)
        efeito = str(acao.dados_extras.get("efeito_principal") or "dano")

        if efeito == "cura":
            componentes["cura"] = self._avaliar_cura(estado, executor, alvo)
            motivos.append("cura")
        elif efeito == "protecao":
            componentes["protecao"] = self._avaliar_protecao(estado, executor, alvo)
            motivos.append("protecao")
        elif efeito == "mobilidade":
            componentes["mobilidade"] = self._avaliar_mobilidade(estado, executor, acao)
            motivos.append("mobilidade")
        else:
            componentes["dano"] = self._avaliar_dano(estado, executor, alvo, acao)
            motivos.append("dano")

        componentes["custo"] = self._avaliar_custo(executor, acao)
        componentes["passivas"] = self._avaliar_passivas(estado, executor, acao)
        componentes["previsao"] = self._avaliar_previsao(estado, acao)
        score = sum(componentes.values()) + float(acao.prioridade or 0.0)
        return ResultadoAvaliacaoIA(acao=acao, score=score, componentes=componentes, motivos=motivos)

    def _avaliar_dano(self, estado: EstadoBatalhaIA, executor: CombatenteIA, alvo: CombatenteIA | None, acao: AcaoCandidata) -> float:
        if alvo is None:
            return -2.0
        fatores = estado.dificuldade
        dano = self._estimar_dano(estado, executor, alvo, acao)
        score = dano / max(10.0, alvo.vida_max)

        if fatores.get("considerar_kill", 0.0) > 0.0 and dano >= alvo.vida_atual:
            score += 1.5 * float(fatores.get("considerar_kill", 0.0))

        if fatores.get("considerar_area", 0.0) > 0.0 and acao.estilo in {"area", "zona"}:
            score += self._bonus_area(estado, alvo, acao) * float(fatores.get("considerar_area", 0.0))

        if fatores.get("considerar_posicionamento", 0.0) > 0.0 and acao.destino_posicao is not None:
            distancia = executor.posicao.distancia_ate(acao.destino_posicao)
            score += max(0.0, 1.0 - (distancia / 8.0)) * 0.5 * float(fatores.get("considerar_posicionamento", 0.0))

        if fatores.get("considerar_risco", 0.0) > 0.0:
            score -= self._risco_local(estado, executor, alvo, acao) * float(fatores.get("considerar_risco", 0.0))
        return score

    def _avaliar_cura(self, estado: EstadoBatalhaIA, executor: CombatenteIA, alvo: CombatenteIA | None) -> float:
        if alvo is None:
            alvo = executor
        falta = max(0.0, 1.0 - alvo.percentual_vida)
        score = falta * 1.5
        score += max(0.0, 0.35 - alvo.percentual_vida) * float(estado.dificuldade.get("considerar_protecao", 0.0)) * 2.0
        return score

    def _avaliar_protecao(self, estado: EstadoBatalhaIA, executor: CombatenteIA, alvo: CombatenteIA | None) -> float:
        protegido = alvo if alvo is not None else executor
        score = max(0.0, 0.55 - protegido.percentual_vida) * 2.0
        score += self._risco_para_combatente(estado, protegido) * float(estado.dificuldade.get("considerar_protecao", 0.0))
        return score

    def _avaliar_mobilidade(self, estado: EstadoBatalhaIA, executor: CombatenteIA, acao: AcaoCandidata) -> float:
        if acao.destino_posicao is None:
            return -0.2
        alvo_ref = self._inimigo_mais_proximo(estado, executor)
        if alvo_ref is None:
            return 0.1
        dist_atual = executor.posicao.distancia_ate(alvo_ref.posicao)
        dist_futura = acao.destino_posicao.distancia_ate(alvo_ref.posicao)
        score = max(-1.0, min(1.0, (dist_atual - dist_futura) / 5.0))
        score += (1.0 - executor.percentual_vida) * 0.2
        return score

    def _avaliar_troca(self, estado: EstadoBatalhaIA, executor: CombatenteIA, acao: AcaoCandidata) -> float:
        reserva = estado.buscar_combatente(acao.troca_reserva_id)
        if reserva is None:
            return -1.5
        score = max(0.0, 0.4 - executor.percentual_vida) * 3.0
        score += max(0.0, 0.15 - executor.percentual_energia) * 1.5
        score += reserva.percentual_vida * 0.75
        score += reserva.percentual_energia * 0.35
        return score

    def _avaliar_custo(self, executor: CombatenteIA, acao: AcaoCandidata) -> float:
        if acao.custo_energia <= 0:
            return 0.0
        restante = max(0.0, executor.energia - acao.custo_energia)
        custo_relativo = acao.custo_energia / max(1.0, executor.energia_max)
        restante_relativo = restante / max(1.0, executor.energia_max)
        return -(custo_relativo * 0.6) - max(0.0, 0.1 - restante_relativo)

    def _avaliar_passivas(self, estado: EstadoBatalhaIA, executor: CombatenteIA, acao: AcaoCandidata) -> float:
        fator = float(estado.dificuldade.get("considerar_passivas_habilidade", 0.0))
        if fator <= 0.0:
            return 0.0
        texto = " ".join(str(item) for item in list(acao.habilidade_bruta.values()))
        bonus = 0.0
        if "crit" in texto.casefold() or "crÃ­t" in texto.casefold():
            bonus += 0.2
        if "barreira" in texto.casefold() or "prote" in texto.casefold():
            bonus += 0.15
        if executor.flags.get("focado", False):
            bonus += 0.1
        return bonus * fator

    def _avaliar_previsao(self, estado: EstadoBatalhaIA, acao: AcaoCandidata) -> float:
        leitura = float(estado.dificuldade.get("permitir_leitura_preparacao_inimiga", 0.0))
        previsao = float(estado.dificuldade.get("considerar_previsao_inimiga", 0.0))
        hack = float(estado.dificuldade.get("permitir_contrajogada_hack", 0.0))
        if not estado.preparacoes_inimigas or max(leitura, previsao, hack) <= 0.0:
            return 0.0
        bonus = 0.0
        for preparo in estado.preparacoes_inimigas:
            if preparo.acao_chave and preparo.acao_chave == acao.acao_chave:
                bonus += 0.2 * preparo.confianca
        return bonus * max(previsao, leitura * 0.5, hack * 0.25)

    def _resolver_alvo(self, estado: EstadoBatalhaIA, acao: AcaoCandidata) -> CombatenteIA | None:
        if acao.alvo_ids:
            return estado.buscar_combatente(acao.alvo_ids[0])
        if acao.destino_posicao is None:
            return None
        alvo_preferencial = str(acao.dados_extras.get("alvo_preferencial") or "inimigo")
        base = estado.aliados_ativos if alvo_preferencial == "aliado" else estado.inimigos_ativos
        candidatos = [alvo for alvo in base if not alvo.fora_de_combate]
        if not candidatos:
            return None
        return min(candidatos, key=lambda combatente: combatente.posicao.distancia_ate(acao.destino_posicao))

    def _estimar_dano(self, estado: EstadoBatalhaIA, executor: CombatenteIA, alvo: CombatenteIA, acao: AcaoCandidata) -> float:
        fatores = estado.dificuldade
        habilidade = dict(acao.habilidade_bruta or {})
        descricao = " ".join(str(valor) for valor in habilidade.values())
        usa_spa = "especial" in descricao.casefold()
        considerar_tipo_dano = float(fatores.get("considerar_tipo_dano", 0.0))
        considerar_defesa = float(fatores.get("considerar_defesa_correta", 0.0))
        considerar_tipo = float(fatores.get("considerar_fraqueza_resistencia", 0.0))

        ataque_fisico = float(executor.atributos.get("Atk", 0.0))
        ataque_especial = float(executor.atributos.get("SpA", 0.0))
        defesa_fisica = float(alvo.atributos.get("Def", 0.0))
        defesa_especial = float(alvo.atributos.get("SpD", 0.0))

        if considerar_tipo_dano <= 0.0:
            ataque = (ataque_fisico + ataque_especial) * 0.5
        else:
            ataque = ataque_fisico * (1.0 - considerar_tipo_dano) + (ataque_especial if usa_spa else ataque_fisico) * considerar_tipo_dano

        if considerar_defesa <= 0.0:
            defesa = (defesa_fisica + defesa_especial) * 0.5
        else:
            defesa_escolhida = defesa_especial if usa_spa else defesa_fisica
            defesa = ((defesa_fisica + defesa_especial) * 0.5) * (1.0 - considerar_defesa) + defesa_escolhida * considerar_defesa

        dano = max(1.0, (ataque * 0.6) - (defesa * 0.22) + 8.0)
        if "executa" in descricao.casefold() and alvo.percentual_vida <= 0.25:
            dano += alvo.vida_atual * 0.8

        tipo = str(habilidade.get("Tipo") or habilidade.get("tipo") or "normal").strip().casefold() or "normal"
        modificador_tipo = self._modificador_tipo(tipo, alvo.tipos)
        dano *= 1.0 + ((modificador_tipo - 1.0) * considerar_tipo)
        return max(1.0, dano)

    def _modificador_tipo(self, tipo_ataque: str, tipos_alvo: List[str]) -> float:
        tabela = _TYPE_CHART.get(str(tipo_ataque or "").casefold(), {})
        modificador = 1.0
        for tipo in list(tipos_alvo or []):
            modificador *= float(tabela.get(str(tipo or "").casefold(), 1.0))
        return max(0.0, modificador)

    def _bonus_area(self, estado: EstadoBatalhaIA, alvo_referencia: CombatenteIA, acao: AcaoCandidata) -> float:
        if acao.destino_posicao is None:
            return 0.0
        raio = 1.75
        bonus = 0.0
        for alvo in estado.inimigos_ativos:
            if alvo.fora_de_combate:
                continue
            if acao.destino_posicao.distancia_ate(alvo.posicao) <= raio:
                bonus += 0.35
        if alvo_referencia.posicao.distancia_ate(acao.destino_posicao) <= raio:
            bonus += 0.15
        return bonus

    def _risco_local(self, estado: EstadoBatalhaIA, executor: CombatenteIA, alvo: CombatenteIA, acao: AcaoCandidata) -> float:
        destino = acao.destino_posicao if acao.destino_posicao is not None else executor.posicao
        risco = 0.0
        for inimigo in estado.inimigos_ativos:
            if inimigo.fora_de_combate:
                continue
            distancia = destino.distancia_ate(inimigo.posicao)
            risco += max(0.0, 1.4 - (distancia / 3.5)) * 0.25
        if alvo.percentual_vida > 0.6:
            risco += 0.1
        return risco

    def _risco_para_combatente(self, estado: EstadoBatalhaIA, combatente: CombatenteIA) -> float:
        risco = 0.0
        for inimigo in estado.inimigos_ativos:
            if inimigo.uid == combatente.uid or inimigo.fora_de_combate:
                continue
            distancia = combatente.posicao.distancia_ate(inimigo.posicao)
            risco += max(0.0, 1.2 - (distancia / 4.0)) * 0.35
        return risco

    def _inimigo_mais_proximo(self, estado: EstadoBatalhaIA, executor: CombatenteIA) -> CombatenteIA | None:
        inimigos = [inimigo for inimigo in estado.inimigos_ativos if not inimigo.fora_de_combate]
        if not inimigos:
            return None
        return min(inimigos, key=lambda inimigo: executor.posicao.distancia_ate(inimigo.posicao))
