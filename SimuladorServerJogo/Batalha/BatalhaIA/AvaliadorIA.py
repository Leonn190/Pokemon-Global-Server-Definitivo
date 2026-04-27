from __future__ import annotations

import math
from typing import Any, Mapping

from .ContextoIA import ContextoIA, fnum, inteiro, normalizar
from .GeradorCandidatosIA import CandidatoIA

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
        candidato.score = float(score)
        return candidato.score

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
                ameaca = self._ameaca_pokemon(contexto, alvo)
                chance_finalizar = min(1.0, dano / max(1.0, vida))
                if dano >= vida:
                    finalizacoes += 1
                valor = dano * (0.85 + 0.45 * per.agressividade)
                valor += chance_finalizar * 55.0 * dif.foco_finalizacao
                valor += (1.0 - vida_pct) * 20.0 * dif.foco_finalizacao
                valor += ameaca * (0.10 + 0.25 * dif.controle_risco)
                if contexto.usar_leitura_player and self._usuario_age_antes(contexto, usuario, alvo):
                    valor += ameaca * 0.18 * dif.previsao_ordem
                if dano > melhor_dano:
                    melhor_dano = dano
                    melhor_alvo_id = contexto.pid(alvo)
                total += valor
            else:
                aliados_atingidos += 1
                total -= dano * (1.0 + dif.controle_risco + per.aversao_risco)

        if inimigos_atingidos == 0:
            total -= 75.0
        if inimigos_atingidos > 1:
            total += (inimigos_atingidos - 1) * 20.0 * per.preferencia_area
        if inimigos_atingidos == 1:
            total += 12.0 * per.preferencia_foco_unico
        if aliados_atingidos:
            total -= aliados_atingidos * 35.0 * dif.controle_risco

        custo = max(0.0, candidato.custo_base)
        total -= self._penalidade_custo(contexto, usuario, custo)
        if candidato.area_id in contexto.areas_miradas and contexto.usar_leitura_player:
            # O jogador mirou ali; ataques no mesmo foco podem virar corrida de velocidade.
            total += 8.0 * dif.previsao_ordem

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
            ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(alvo), 0.0)
            valor = cura * (0.92 + dif.uso_suporte + per.preferencia_suporte)
            valor += (1.0 - contexto.vida_pct(alvo)) * 65.0 * (dif.controle_risco + per.defensividade) / 2.0
            valor += ameaca * (0.18 + 0.34 * contexto.config.criterio_hacker)
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
            ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(alvo), 0.0)
            total += 18.0
            total += hp_baixo * 58.0 * (dif.controle_risco + per.defensividade) / 2.0
            total += ameaca * (0.55 + 0.45 * contexto.config.criterio_hacker)
            total += contexto.barreira(alvo) * 0.05
        total -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * (0.55 + 0.45 * per.aversao_risco)
        candidato.estimativa.update({"protecao": True})
        return total

    def _avaliar_recarga(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        usuario = candidato.pokemon
        energia_pct = contexto.energia_pct(usuario)
        maior_custo = self._maior_custo_ataque(contexto, usuario)
        necessidade = max(0.0, 1.0 - energia_pct)
        valor = necessidade * 70.0 * (0.35 + dif.gestao_energia)
        if contexto.energia_atual(usuario) < maior_custo:
            valor += 28.0 * dif.gestao_energia
        if contexto.ameacas_por_pokemon.get(contexto.pid(usuario), 0.0) > 0:
            valor -= 20.0 * dif.controle_risco
        valor -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * 0.35
        candidato.estimativa.update({"recarga": True})
        return valor

    def _avaliar_buff(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        nome = normalizar((candidato.propriedades or {}).get("nome") or (candidato.ataque or {}).get("nome"))
        hp = contexto.vida_pct(usuario)
        valor = 12.0 + 28.0 * dif.uso_suporte + 18.0 * per.preferencia_suporte
        if nome == "enraivecer":
            valor += max(0.0, 0.55 - hp) * 110.0 * (per.ousadia + per.agressividade) / 2.0
        elif nome == "tankar":
            valor += (1.0 - hp) * 60.0 * (per.defensividade + dif.controle_risco) / 2.0
            valor += contexto.ameacas_por_pokemon.get(contexto.pid(usuario), 0.0) * 0.25
        valor -= self._penalidade_custo(contexto, usuario, candidato.custo_base) * 0.62
        candidato.estimativa.update({"buff": nome})
        return valor

    def _avaliar_controle(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        usuario = candidato.pokemon
        nome = normalizar((candidato.propriedades or {}).get("nome") or (candidato.ataque or {}).get("nome"))
        valor = 12.0 + 16.0 * dif.uso_suporte
        if nome == "provocar":
            duravel = contexto.vida_pct(usuario) + min(1.0, contexto.barreira(usuario) / max(1.0, contexto.vida_max(usuario)))
            valor += duravel * 28.0 * (per.defensividade + per.ousadia) / 2.0
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
        ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0)
        efeitos = contexto.qtd_efeitos_negativos(pokemon)
        valor = 0.0
        valor += max(0.0, 0.58 - hp) * 95.0 * (dif.uso_troca + per.preferencia_troca) / 2.0
        valor += max(0.0, 0.28 - energia) * 45.0 * dif.gestao_energia
        valor += ameaca * (0.28 + 0.32 * dif.controle_risco)
        valor += efeitos * 18.0 * dif.controle_risco
        valor += (hp_reserva - hp) * 34.0
        valor += (energia_reserva - energia) * 14.0
        if hp > 0.72 and energia > 0.45 and ameaca <= 0:
            valor -= 42.0 * (1.0 - per.preferencia_troca)
        valor -= self._penalidade_custo(contexto, pokemon, candidato.custo_base) * 0.55
        candidato.estimativa.update({"preservacao": round(max(0.0, valor), 4)})
        return valor

    def _avaliar_movimento(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        pokemon = candidato.pokemon
        ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0)
        origem_mirada = str(contexto.area_id(pokemon)) in contexto.areas_miradas
        destino_mirado = str(candidato.area_id) in contexto.areas_miradas
        valor = 4.0
        if origem_mirada or ameaca > 0:
            valor += 36.0 * dif.controle_risco + ameaca * 0.30
        if destino_mirado:
            valor -= 30.0 * (dif.controle_risco + per.aversao_risco)
        if contexto.vida_pct(pokemon) < 0.35:
            valor += 18.0 * per.defensividade
        valor -= self._penalidade_custo(contexto, pokemon, candidato.custo_base) * 0.85
        candidato.estimativa.update({"reposicionamento": True})
        return valor

    def _avaliar_troca_posicao(self, contexto: ContextoIA, candidato: CandidatoIA) -> float:
        dif = contexto.config.dificuldade
        pokemon = candidato.pokemon
        outro = candidato.alvos[0] if candidato.alvos else None
        if outro is None:
            return -999.0
        ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(pokemon), 0.0)
        valor = ameaca * 0.32 * dif.controle_risco
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
        nome = normalizar(props.get("nome") or (candidato.ataque or {}).get("nome"))
        code = inteiro(props.get("Code") or props.get("ID") or (candidato.ataque or {}).get("Code"), 0)
        atk = contexto.atributo(usuario, "Atk")
        spa = contexto.atributo(usuario, "SpA")
        per = contexto.atributo(usuario, "Per")
        categoria = "normal"
        bruto = max(atk, spa) * 0.85
        if code == 1 or nome == "investida":
            bruto = atk * 1.20
        elif code == 6 or nome == "arranhar":
            bruto = atk * 1.35
        elif code == 8 or nome == "energia":
            bruto = spa * 1.15
            categoria = "especial"
        elif code == 9 or nome == "hiperraio":
            qtd = max(1, len([a for a in candidato.alvos if contexto.lado(a) != contexto.lado(usuario)]))
            bruto = max(0.0, spa * 1.50 - ((qtd - 1) * spa * 0.15))
            categoria = "especial"
        elif code == 10 or nome == "guilhotina":
            bruto = atk * 0.80
        elif code == 11 or nome == "disparo":
            bruto = atk * 1.00
        elif code == 12 or nome == "chifrada":
            bruto = atk * 0.90 + per * 0.40
        elif code == 15 or nome == "estocada":
            bruto = atk * 1.05
            if self._provavel_primeiro_ataque(contexto, usuario):
                bruto *= 1.25
        elif code == 16 or nome == "bolaclimatica":
            bruto = spa * (1.30 if getattr(contexto.partida, "clima_atual", None) else 1.05)
            categoria = "especial"
        elif code == 17 or nome == "hiperpresa":
            bruto = atk * 1.40

        tipo = ((props.get("parametros") or {}).get("tipo") if isinstance(props.get("parametros"), dict) else None) or props.get("tipo") or "normal"
        dano = max(0.0, bruto)
        dano *= 1.0 + contexto.atributo(usuario, "Amp") / 100.0
        try:
            dano *= float(obter_multiplicador(tipo, list(getattr(alvo, "tipos", getattr(alvo, "Tipos", [])) or [])))
        except Exception:
            pass
        if normalizar(tipo) in contexto.tipos(usuario):
            dano *= 1.20
        defesa_chave = "SpD" if categoria in {"especial", "spa", "magico"} else "Def"
        defesa = max(0.0, contexto.atributo(alvo, defesa_chave) - (contexto.atributo(usuario, "Per") / 2.0))
        dano *= 100.0 / (100.0 + defesa)
        dano = max(0.0, dano - contexto.atributo(alvo, "Dur"))
        barreira = contexto.barreira(alvo)
        if barreira > 0:
            return max(0.0, dano - barreira) * 0.40 + min(dano, barreira) * 0.15
        return max(0.0, dano)

    def _penalidade_custo(self, contexto: ContextoIA, pokemon, custo: float) -> float:
        dif = contexto.config.dificuldade
        per = contexto.config.personalidade
        energia = max(1.0, contexto.energia_atual(pokemon))
        frac = max(0.0, custo) / energia
        return frac * 28.0 * (0.25 + dif.gestao_energia) * (1.10 - 0.45 * per.ousadia)

    def _maior_custo_ataque(self, contexto: ContextoIA, pokemon) -> float:
        maior = 0.0
        for ataque in contexto.ataques(pokemon):
            props = contexto.buscar_propriedades_ataque(ataque) or {}
            maior = max(maior, fnum(props.get("custo", ataque.get("Custo", 0.0)), 0.0))
        return maior

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
