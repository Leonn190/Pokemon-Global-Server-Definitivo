from __future__ import annotations

import math
from typing import Any, Mapping

from .ContextoIA import ContextoIA, fnum, normalizar
from .GeradorAcoesIA import CandidatoIA

try:
    from SimuladorServerJogo.Batalha.FraquezasResistencia import obter_multiplicador
except Exception:  # pragma: no cover - fallback para testes isolados da pasta IA
    def obter_multiplicador(_tipo, _tipos_alvo):
        return 1.0


class AvaliadorIA:
    def avaliar(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        tipo = candidato.tipo
        if tipo == "ataque":
            score = self._avaliar_ataque(contexto, candidato)
        elif tipo == "troca_reserva":
            score = self._avaliar_troca_reserva(contexto, candidato)
        elif tipo == "movimento":
            score = self._avaliar_movimento(contexto, candidato)
        elif tipo == "troca_posicao":
            score = self._avaliar_troca_posicao(contexto, candidato)
        else:
            score = -9999.0
        score += self._bonus_metadados(contexto, candidato)
        candidato.score = float(score)
        return candidato.score

    def _bonus_metadados(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        """Usa metadados só como orientação estratégica, nunca como execute."""
        meta = candidato.metadados if isinstance(candidato.metadados, dict) else {}
        if not meta:
            return 0.0

        score = 0.0
        personalidade = contexto.config.personalidade
        papeis = {normalizar(p) for p in list(meta.get("papeis") or [])}
        alvos_pref = {normalizar(a) for a in list(meta.get("alvos_preferidos") or [])}
        efeitos = {normalizar(e) for e in list(meta.get("efeitos_relevantes") or [])}
        condicoes = {normalizar(c) for c in list(meta.get("condicoes") or [])}

        prioridade = fnum(meta.get("prioridade_simulacao"), 0.35)
        score += prioridade * 2.0 * contexto.config.dificuldade.conhecimento

        if candidato.categoria == "dano":
            score += 3.0 * personalidade.agressividade
            if "finalizacao" in papeis or "execucao" in papeis:
                score += 4.0 * personalidade.foco
        if candidato.categoria in {"cura", "defesa"} or papeis.intersection({"cura", "protecao", "barreira", "sobrevivencia"}):
            score += 4.0 * personalidade.suporte
            score += 2.0 * personalidade.cautela
        if papeis.intersection({"area", "linha"}):
            score += 3.0 * personalidade.area
        if papeis.intersection({"troca", "movimento"}):
            score += 2.5 * personalidade.troca

        if "inimigoferido" in alvos_pref:
            for alvo in candidato.alvos:
                if contexto.lado(alvo) != contexto.lado_id and contexto.vida_pct(alvo) <= 0.35:
                    score += 5.0 * personalidade.foco
        if "aliadofocado" in alvos_pref:
            for alvo in candidato.alvos or [candidato.pokemon]:
                if contexto.lado(alvo) == contexto.lado_id:
                    score += min(5.0, contexto.ameacas_por_pokemon.get(contexto.pid(alvo), 0.0) / 20.0) * personalidade.cautela

        if efeitos.intersection({"recoil", "recuo", "danoousuario"}):
            score -= 2.0 * personalidade.cautela * (1.0 - personalidade.ousadia * 0.45)
        if "melhoremimigosagrupados" in condicoes and len(candidato.alvos or []) >= 2:
            score += 4.0 * personalidade.area
        return float(score)

    def avaliar_resultado_micro(self, contexto: ContextoIA, candidato: CandidatoIA, resultado: Mapping[str, Any] | None) -> float:
        """Transforma resultado da micro simulação em ajuste de score."""
        if not isinstance(resultado, Mapping):
            return 0.0

        raciocinio = contexto.config.dificuldade.raciocinio
        personalidade = contexto.config.personalidade
        ajuste = 0.0

        camadas = set(resultado.get("camadas_consideradas") or ["vida", "dano", "cura"])
        dano = fnum(resultado.get("dano_causado"), 0.0)
        cura = fnum(resultado.get("cura_feita"), 0.0)
        barreira = fnum(resultado.get("barreira_gerada"), 0.0) if "barreira" in camadas else 0.0
        energia_rec = fnum(resultado.get("energia_recuperada"), 0.0) if "energia" in camadas else 0.0
        energia_gasta = fnum(resultado.get("energia_gasta"), 0.0) if "energia" in camadas else 0.0
        risco = fnum(resultado.get("risco_usuario"), 0.0)
        overkill = fnum(resultado.get("overkill"), 0.0) if "overkill" in camadas else 0.0

        ajuste += dano * 0.055 * (0.65 + personalidade.agressividade)
        ajuste -= fnum(resultado.get("dano_aliado"), 0.0) * 0.070 * (0.70 + personalidade.cautela)
        ajuste += cura * 0.060 * (0.65 + personalidade.suporte)
        ajuste -= fnum(resultado.get("cura_inimigo"), 0.0) * 0.050 * (0.60 + personalidade.agressividade)
        ajuste += barreira * 0.045 * (0.65 + personalidade.cautela)
        ajuste += energia_rec * 0.030 * contexto.config.dificuldade.raciocinio
        ajuste -= energia_gasta * 0.020 * contexto.config.dificuldade.raciocinio
        ajuste -= risco * 0.10 * (0.70 + personalidade.cautela - personalidade.ousadia * 0.35)
        ajuste -= overkill * 0.020 * (0.40 + contexto.config.dificuldade.raciocinio)

        mortos = list(resultado.get("alvos_mortos") or []) if "morte" in camadas else []
        aliados_mortos = list(resultado.get("aliados_mortos") or []) if "morte" in camadas else []
        salvos = list(resultado.get("aliados_salvos") or [])
        ajuste += len(mortos) * 22.0 * (0.60 + personalidade.foco)
        ajuste -= len(aliados_mortos) * 26.0 * (0.60 + personalidade.cautela)
        ajuste += len(salvos) * 16.0 * (0.60 + personalidade.suporte + personalidade.cautela * 0.5)
        if "efeitos" in camadas:
            ajuste += fnum(resultado.get("efeitos_positivos"), 0.0) * 5.0 * personalidade.suporte
            ajuste += fnum(resultado.get("efeitos_negativos"), 0.0) * 5.0 * (0.50 + personalidade.agressividade)
            ajuste += fnum(resultado.get("efeitos_removidos"), 0.0) * 2.5 * raciocinio

        if "posicionamento" in camadas and resultado.get("posicionamento_melhor"):
            ajuste += 6.0 * (0.50 + personalidade.cautela)
        if resultado.get("acao_invalida"):
            ajuste -= 40.0
        if resultado.get("origem") == "micro_real":
            ajuste *= 1.20
        return float(ajuste * (0.35 + 0.65 * raciocinio))

    def _avaliar_ataque(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        categoria = candidato.categoria
        if categoria == "dano":
            return self._avaliar_ataque_dano(contexto, candidato)
        if categoria == "cura":
            return self._avaliar_cura(contexto, candidato)
        if categoria == "defesa":
            return self._avaliar_defesa(contexto, candidato)
        if categoria == "energia":
            return self._avaliar_recarga(contexto, candidato)
        if categoria == "buff":
            return self._avaliar_buff(contexto, candidato)
        if categoria == "controle":
            return self._avaliar_controle(contexto, candidato)
        return 0.0

    def _avaliar_ataque_dano(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        total = 0.0
        dano_total = 0.0
        finalizacoes = 0
        aliados_atingidos = 0
        inimigos_atingidos = 0
        melhor_alvo_id = None
        melhor_dano = 0.0
        for alvo in candidato.alvos:
            if alvo is None or not contexto.vivo(alvo):
                continue
            dano = self.estimar_dano(contexto, usuario, alvo, candidato)
            dano_total += dano
            vida = contexto.vida_atual(alvo)
            alvo_inimigo = contexto.lado(alvo) != contexto.lado(usuario)
            if alvo_inimigo:
                inimigos_atingidos += 1
                vida_pct = contexto.vida_pct(alvo)
                ameaca = self._ameaca_pokemon(contexto, alvo) + self._memoria_protegido(contexto, alvo) * 6.0
                chance_finalizar = min(1.0, dano / max(1.0, vida))
                if dano >= vida:
                    finalizacoes += 1
                valor = dano * (0.85 + 0.45 * per.agressividade)
                valor += chance_finalizar * 55.0 * dif.raciocinio
                valor += (1.0 - vida_pct) * 20.0 * dif.raciocinio
                valor += ameaca * (0.10 + 0.25 * ((dif.raciocinio + dif.previsao) / 2.0))
                if contexto.usar_leitura_player and self._usuario_age_antes(contexto, usuario, alvo):
                    valor += ameaca * 0.18 * dif.previsao
                if dano > melhor_dano:
                    melhor_dano = dano
                    melhor_alvo_id = contexto.pid(alvo)
                total += valor
            else:
                aliados_atingidos += 1
                total -= dano * (1.0 + ((dif.raciocinio + dif.previsao) / 2.0) + per.cautela)

        if inimigos_atingidos == 0:
            total -= 75.0
        if inimigos_atingidos > 1:
            total += (inimigos_atingidos - 1) * 20.0 * per.area
        if inimigos_atingidos == 1:
            total += 12.0 * per.foco
        if aliados_atingidos:
            total -= aliados_atingidos * 35.0 * ((dif.raciocinio + dif.previsao) / 2.0)

        custo = max(0.0, candidato.custo_base)
        total -= self._penalidade_custo(contexto, usuario, custo)
        if candidato.area_id in contexto.areas_miradas and contexto.usar_leitura_player:
            # O jogador mirou ali; ataques no mesmo foco podem virar corrida de velocidade.
            total += 8.0 * dif.previsao

        candidato.estimativa.update({
            "dano_total": round(dano_total, 4),
            "finalizacoes": finalizacoes,
            "alvo_principal_id": melhor_alvo_id,
            "melhor_dano": round(melhor_dano, 4),
        })
        return total

    def _avaliar_cura(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        total = 0.0
        cura_total = 0.0
        for alvo in candidato.alvos:
            if alvo is None or contexto.lado(alvo) != contexto.lado(usuario):
                total -= 50.0
                continue
            faltante = max(0.0, contexto.vida_max(alvo) - contexto.vida_atual(alvo))
            cura = min(faltante, max(1.0, contexto.atributo(usuario, "Mag") * 0.55))
            ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(alvo), 0.0) + self._memoria_foco(contexto, alvo) * 14.0
            valor = cura * (0.92 + ((dif.conhecimento + dif.raciocinio) / 2.0) + per.suporte)
            valor += (1.0 - contexto.vida_pct(alvo)) * 65.0 * (((dif.raciocinio + dif.previsao) / 2.0) + per.cautela) / 2.0
            valor += ameaca * (0.18 + 0.34 * contexto.config.hacker.intuicao)
            if contexto.possui_efeito(alvo, "Cauterizado"):
                valor *= 0.25
            total += valor
            cura_total += cura
        total -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * 0.75
        candidato.estimativa.update({"cura_total": round(cura_total, 4)})
        return total

    def _avaliar_defesa(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        alvos = candidato.alvos or [usuario]
        total = 0.0
        for alvo in alvos:
            if alvo is None or contexto.lado(alvo) != contexto.lado(usuario):
                total -= 30.0
                continue
            hp_baixo = 1.0 - contexto.vida_pct(alvo)
            ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(alvo), 0.0) + self._memoria_foco(contexto, alvo) * 14.0
            total += 18.0
            total += hp_baixo * 58.0 * (((dif.raciocinio + dif.previsao) / 2.0) + per.cautela) / 2.0
            total += ameaca * (0.55 + 0.45 * contexto.config.hacker.intuicao)
            total += contexto.barreira(alvo) * 0.05
        total -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * (0.55 + 0.45 * per.cautela)
        candidato.estimativa.update({"protecao": True})
        return total

    def _avaliar_recarga(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        usuario = candidato.pokemon
        energia_pct = contexto.energia_pct(usuario)
        maior_custo = self._maior_custo_ataque(contexto, usuario)
        necessidade = max(0.0, 1.0 - energia_pct)
        valor = necessidade * 70.0 * (0.35 + dif.raciocinio)
        if contexto.energia_atual(usuario) < maior_custo:
            valor += 28.0 * dif.raciocinio
        if contexto.ameacas_por_pokemon.get(contexto.pid(usuario), 0.0) > 0:
            valor -= 20.0 * ((dif.raciocinio + dif.previsao) / 2.0)
        valor -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * 0.35
        candidato.estimativa.update({"recarga": True})
        return valor

    def _avaliar_buff(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        nome = normalizar((candidato.propriedades or {}).get("nome") or (candidato.ataque or {}).get("nome"))
        hp = contexto.vida_pct(usuario)
        valor = 12.0 + 28.0 * ((dif.conhecimento + dif.raciocinio) / 2.0) + 18.0 * per.suporte
        if nome == "enraivecer":
            valor += max(0.0, 0.55 - hp) * 110.0 * (per.ousadia + per.agressividade) / 2.0
        elif nome == "tankar":
            valor += (1.0 - hp) * 60.0 * (per.cautela + ((dif.raciocinio + dif.previsao) / 2.0)) / 2.0
            valor += contexto.ameacas_por_pokemon.get(contexto.pid(usuario), 0.0) * 0.25
        valor -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * 0.62
        candidato.estimativa.update({"buff": nome})
        return valor

    def _avaliar_controle(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        nome = normalizar((candidato.propriedades or {}).get("nome") or (candidato.ataque or {}).get("nome"))
        valor = 12.0 + 16.0 * ((dif.conhecimento + dif.raciocinio) / 2.0)
        if nome == "provocar":
            duravel = contexto.vida_pct(usuario) + min(1.0, contexto.barreira(usuario) / max(1.0, contexto.vida_max(usuario)))
            valor += duravel * 28.0 * (per.cautela + per.ousadia) / 2.0
        elif nome == "resetar":
            for alvo in candidato.alvos:
                if contexto.lado(alvo) != contexto.lado(usuario):
                    valor += contexto.qtd_efeitos_positivos(alvo) * 28.0 + self._ameaca_pokemon(contexto, alvo) * 0.08
                else:
                    valor += contexto.qtd_efeitos_negativos(alvo) * 20.0
        valor -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * 0.65
        candidato.estimativa.update({"controle": nome})
        return valor

    def _avaliar_troca_reserva(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        pokemon = candidato.pokemon
        reserva = (candidato.estimativa or {}).get("reserva") or (candidato.alvos[0] if candidato.alvos else None)
        if reserva is None:
            return -999.0
        hp = contexto.vida_pct(pokemon)
        energia = contexto.energia_pct(pokemon)
        hp_reserva = contexto.vida_pct(reserva)
        energia_reserva = contexto.energia_pct(reserva)
        ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0) + self._memoria_foco(contexto, pokemon) * 14.0
        efeitos = contexto.qtd_efeitos_negativos(pokemon)
        valor = 0.0
        valor += max(0.0, 0.58 - hp) * 95.0 * (((dif.inteligencia + dif.raciocinio) / 2.0) + per.troca) / 2.0
        valor += max(0.0, 0.28 - energia) * 45.0 * dif.raciocinio
        valor += ameaca * (0.28 + 0.32 * ((dif.raciocinio + dif.previsao) / 2.0))
        valor += efeitos * 18.0 * ((dif.raciocinio + dif.previsao) / 2.0)
        valor += (hp_reserva - hp) * 34.0
        valor += (energia_reserva - energia) * 14.0
        if hp > 0.72 and energia > 0.45 and ameaca <= 0:
            valor -= 42.0 * (1.0 - per.troca)
        valor -= self._penalidade_custo(contexto, pokemon, candidato.custo_base) * 0.55
        candidato.estimativa.update({"preservacao": round(max(0.0, valor), 4)})
        return valor

    def _avaliar_movimento(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        pokemon = candidato.pokemon
        ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0) + self._memoria_foco(contexto, pokemon) * 14.0
        origem_mirada = str(contexto.area_id(pokemon)) in contexto.areas_miradas
        destino_mirado = str(candidato.area_id) in contexto.areas_miradas
        destino_memoria = self._memoria_area(contexto, candidato.area_id)
        valor = 4.0
        if origem_mirada or ameaca > 0:
            valor += 36.0 * ((dif.raciocinio + dif.previsao) / 2.0) + ameaca * 0.30
        if destino_mirado:
            valor -= 30.0 * (((dif.raciocinio + dif.previsao) / 2.0) + per.cautela)
        if destino_memoria > 0:
            valor -= destino_memoria * 10.0 * (0.4 + dif.memoria)
        if contexto.vida_pct(pokemon) < 0.35:
            valor += 18.0 * per.cautela
        valor -= self._penalidade_custo(contexto, pokemon, candidato.custo_base) * 0.85
        candidato.estimativa.update({"reposicionamento": True})
        return valor

    def _avaliar_troca_posicao(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        pokemon = candidato.pokemon
        outro = candidato.alvos[0] if candidato.alvos else None
        if outro is None:
            return -999.0
        ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0) + self._memoria_foco(contexto, pokemon) * 14.0
        valor = ameaca * 0.32 * ((dif.raciocinio + dif.previsao) / 2.0)
        valor += max(0.0, contexto.vida_pct(outro) - contexto.vida_pct(pokemon)) * 30.0
        valor += max(0.0, contexto.barreira(outro) - contexto.barreira(pokemon)) * 0.18
        valor -= self._penalidade_custo(contexto, pokemon, candidato.custo_base) * 0.80
        candidato.estimativa.update({"troca_posicao": True})
        return valor

    def estimar_dano(self, contexto: ContextoIA, usuario, alvo, candidato: CandidatoIA) -> float:
        if alvo is None or not contexto.vivo(alvo):
            return 0.0
        if getattr(alvo, "estados_transitorios", {}).get("protegido"):
            return 0.0
        props = candidato.propriedades or {}
        params = props.get("parametros") if isinstance(props.get("parametros"), Mapping) else {}
        meta = candidato.metadados if isinstance(candidato.metadados, dict) else {}
        atk = contexto.atributo(usuario, "Atk")
        spa = contexto.atributo(usuario, "SpA")
        per = contexto.atributo(usuario, "Per")
        mag = contexto.atributo(usuario, "Mag")
        papeis = {normalizar(p) for p in list(meta.get("papeis") or [])}
        efeitos = {normalizar(e) for e in list(meta.get("efeitos_relevantes") or [])}
        categoria = normalizar(params.get("categoria") or props.get("categoria") or props.get("classe"))
        estilo_dano = normalizar(params.get("estilo_dano") or params.get("dano") or props.get("estilo_dano"))
        especial = categoria in {"especial", "magico"} or estilo_dano in {"especial", "spa", "magico"} or "especial" in papeis
        if not especial and ("energia" in efeitos or "projetil" in efeitos):
            especial = spa >= atk
        ofensivo = spa if especial else atk
        if ofensivo <= 0:
            ofensivo = max(atk, spa, mag)

        mult = self._multiplicador_heuristico_dano(params, props, meta)
        qtd_inimigos = max(1, len([a for a in candidato.alvos if contexto.lado(a) != contexto.lado(usuario)]))
        if qtd_inimigos > 1:
            mult *= max(0.55, 1.0 - (qtd_inimigos - 1) * 0.12)
        if "finalizacao" in papeis or "execucao" in papeis:
            mult *= 1.08
        if "recoil" in efeitos or "recuo" in efeitos:
            mult *= 1.06
        if "contato" in efeitos:
            mult *= 1.03
        if self._provavel_primeiro_ataque(contexto, usuario):
            mult *= 1.0 + 0.05 * contexto.config.dificuldade.previsao

        bruto = ofensivo * mult + per * fnum(params.get("escala_percepcao", props.get("escala_percepcao", 0.0)), 0.0)
        if mag > ofensivo and especial:
            bruto += mag * 0.12

        tipo = params.get("tipo") or props.get("tipo") or "normal"
        dano = max(0.0, bruto)
        dano *= 1.0 + contexto.atributo(usuario, "Amp") / 100.0
        try:
            dano *= float(obter_multiplicador(tipo, list(getattr(alvo, "tipos", getattr(alvo, "Tipos", [])) or [])))
        except Exception:
            pass
        if normalizar(tipo) in contexto.tipos(usuario):
            dano *= 1.20
        defesa_chave = "SpD" if especial else "Def"
        defesa = max(0.0, contexto.atributo(alvo, defesa_chave) - (contexto.atributo(usuario, "Per") / 2.0))
        dano *= 100.0 / (100.0 + defesa)
        dano = max(0.0, dano - contexto.atributo(alvo, "Dur") * (0.45 if especial else 0.70))
        custo = max(0.0, candidato.custo_base)
        if custo > 0:
            dano *= 1.0 + min(0.22, custo / max(1.0, contexto.energia_max(usuario)) * 0.18)
        barreira = contexto.barreira(alvo)
        if barreira > 0:
            return max(0.0, dano - barreira) * 0.40 + min(dano, barreira) * 0.15
        return max(0.0, dano)

    @staticmethod
    def _multiplicador_heuristico_dano(params: Mapping[str, Any], props: Mapping[str, Any], meta: Mapping[str, Any]) -> float:
        for fonte in (params, props, meta):
            for chave in ("multiplicador_dano", "multiplicador", "potencia", "power", "forca"):
                if chave in fonte:
                    valor = fnum(fonte.get(chave), 0.0)
                    if valor > 5.0:
                        return max(0.35, min(2.20, valor / 100.0))
                    if valor > 0.0:
                        return max(0.35, min(2.20, valor))
        prioridade = fnum(meta.get("prioridade_simulacao"), 0.45)
        return 0.75 + prioridade * 0.85

    def _penalidade_custo(self, contexto: ContextoIA, pokemon, custo: float) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        energia = max(1.0, contexto.energia_atual(pokemon))
        frac = max(0.0, custo) / energia
        return frac * 28.0 * (0.25 + dif.raciocinio) * (1.10 - 0.45 * per.ousadia)

    def _maior_custo_ataque(self, contexto: ContextoIA, pokemon) -> float:
        maior = 0.0
        for ataque in contexto.ataques(pokemon):
            props = contexto.buscar_propriedades_ataque(ataque) or {}
            maior = max(maior, fnum(props.get("custo", ataque.get("Custo", 0.0)), 0.0))
        return maior

    def _memoria_foco(self, contexto: ContextoIA, pokemon) -> float:
        memoria = getattr(contexto, "memoria_ia", None)
        if memoria is None or pokemon is None:
            return 0.0
        return float(getattr(memoria, "foco_player", {}).get(contexto.pid(pokemon), 0) or 0) * float(contexto.config.dificuldade.memoria or 0.0)

    def _memoria_area(self, contexto: ContextoIA, area_id: object) -> float:
        memoria = getattr(contexto, "memoria_ia", None)
        if memoria is None:
            return 0.0
        return float(getattr(memoria, "areas_player", {}).get(str(area_id or ""), 0) or 0) * float(contexto.config.dificuldade.memoria or 0.0)

    def _memoria_protegido(self, contexto: ContextoIA, pokemon) -> float:
        memoria = getattr(contexto, "memoria_ia", None)
        if memoria is None or pokemon is None:
            return 0.0
        return float(getattr(memoria, "protegidos_player", {}).get(contexto.pid(pokemon), 0) or 0) * float(contexto.config.dificuldade.memoria or 0.0)

    def _ameaca_pokemon(self, contexto: ContextoIA, pokemon) -> float:
        ofensivo = max(contexto.atributo(pokemon, "Atk"), contexto.atributo(pokemon, "SpA"))
        energia = contexto.energia_pct(pokemon)
        vida = contexto.vida_pct(pokemon)
        return ofensivo * (0.20 + energia * 0.35) + contexto.atributo(pokemon, "Int") * 0.12 + vida * 8.0

    def _usuario_age_antes(self, contexto: ContextoIA, usuario, alvo) -> bool:
        return (contexto.atributo(usuario, "Int"), contexto.atributo(usuario, "Vel")) >= (contexto.atributo(alvo, "Int"), contexto.atributo(alvo, "Vel"))

    def _provavel_primeiro_ataque(self, contexto: ContextoIA, usuario) -> bool:
        for inimigo in contexto.inimigos_ativos:
            if (contexto.atributo(inimigo, "Int"), contexto.atributo(inimigo, "Vel")) > (contexto.atributo(usuario, "Int"), contexto.atributo(usuario, "Vel")):
                return False
        for aliado in contexto.aliados_ativos:
            if aliado is usuario:
                continue
            if (contexto.atributo(aliado, "Int"), contexto.atributo(aliado, "Vel")) > (contexto.atributo(usuario, "Int"), contexto.atributo(usuario, "Vel")):
                return False
        return True
