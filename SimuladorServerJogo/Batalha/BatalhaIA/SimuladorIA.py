from __future__ import annotations

from itertools import combinations
from typing import Iterable

from .ContextoIA import ContextoIA
from .GeradorCandidatosIA import CandidatoIA


class SimuladorIA:
    """Simulador leve para a IA.

    Ele nao substitui o RodadorTurno oficial. A ideia aqui e barata: testar muitas
    combinacoes candidatas sem clonar Partida e sem gerar log. A resolucao real
    continua sendo feita pelo servidor depois que a IA devolver o pacote.
    """

    def refinar(self, contexto: ContextoIA, candidatos: list[CandidatoIA], rng) -> list[CandidatoIA]:
        budget = int(contexto.config.orcamento_simulacoes)
        if budget <= 0 or not candidatos:
            return []

        pool = sorted(candidatos, key=lambda c: c.score, reverse=True)[: max(8, contexto.config.max_candidatos_planejamento)]
        melhor_combo: list[CandidatoIA] = []
        melhor_score = float("-inf")
        simuladas = 0

        # Primeira passada deterministica: prefixos dos melhores candidatos.
        for tamanho in range(1, min(contexto.config.max_acoes_por_lado, len(pool)) + 1):
            combo = self._normalizar_combo(contexto, pool[:tamanho])
            if not combo:
                continue
            score = self._pontuar_combo(contexto, combo)
            simuladas += 1
            if score > melhor_score:
                melhor_score = score
                melhor_combo = combo
            if simuladas >= budget:
                return melhor_combo

        # Segunda passada combinatoria limitada.
        tamanho_max = min(contexto.config.max_acoes_por_lado, 5, len(pool))
        for tamanho in range(2, tamanho_max + 1):
            for combo_bruto in combinations(pool[: min(len(pool), 18)], tamanho):
                combo = self._normalizar_combo(contexto, combo_bruto)
                if len(combo) != tamanho:
                    continue
                score = self._pontuar_combo(contexto, combo)
                simuladas += 1
                if score > melhor_score:
                    melhor_score = score
                    melhor_combo = combo
                if simuladas >= budget:
                    return melhor_combo

        # Terceira passada aleatoria guiada se ainda houver orcamento.
        while simuladas < budget:
            combo = []
            embaralhado = list(pool)
            rng.shuffle(embaralhado)
            for cand in embaralhado:
                tent = self._normalizar_combo(contexto, combo + [cand])
                if len(tent) > len(combo):
                    combo = tent
                if len(combo) >= contexto.config.max_acoes_por_lado:
                    break
            score = self._pontuar_combo(contexto, combo)
            simuladas += 1
            if score > melhor_score:
                melhor_score = score
                melhor_combo = combo
        return melhor_combo

    def _normalizar_combo(self, contexto: ContextoIA, candidatos: Iterable[CandidatoIA]) -> list[CandidatoIA]:
        combo: list[CandidatoIA] = []
        contagem: dict[str, int] = {}
        energia_restante: dict[str, float] = {}
        alvos_troca = set()
        for cand in sorted(candidatos, key=lambda c: c.score, reverse=True):
            pid = cand.pokemon_id
            if not pid:
                continue
            if len(combo) >= contexto.config.max_acoes_por_lado:
                break
            if contagem.get(pid, 0) >= contexto.config.max_acoes_por_pokemon:
                continue
            if pid in alvos_troca:
                continue
            if cand.tipo == "troca_reserva":
                # Evita atacar e trocar o mesmo pokemon no mesmo pacote simulado.
                if contagem.get(pid, 0) > 0:
                    continue
                reserva_id = cand.acao.get("pokemon_reserva_id") or cand.acao.get("troca_reserva_id")
                if reserva_id:
                    alvos_troca.add(str(reserva_id))
            ordem_pokemon = contagem.get(pid, 0) + 1
            mult = 1.10 if ordem_pokemon >= 2 else 1.0
            custo = float(cand.custo_base or 0.0) * mult
            energia = energia_restante.setdefault(pid, contexto.energia_atual(cand.pokemon))
            if energia < custo:
                continue
            energia_restante[pid] = energia - custo
            contagem[pid] = ordem_pokemon
            combo.append(cand)
        return combo

    def _pontuar_combo(self, contexto: ContextoIA, combo: list[CandidatoIA]) -> float:
        score = sum(float(c.score or 0.0) for c in combo)
        dano_por_alvo: dict[str, float] = {}
        cura_por_alvo: dict[str, float] = {}
        protegidos = set()
        trocados = set()
        atacantes_por_alvo: dict[str, int] = {}

        for cand in combo:
            if cand.tipo == "troca_reserva":
                trocados.add(cand.pokemon_id)
            if cand.categoria == "defesa":
                for alvo in cand.alvos or [cand.pokemon]:
                    protegidos.add(contexto.pid(alvo))
            alvo_id = (cand.estimativa or {}).get("alvo_principal_id")
            if alvo_id:
                dano_por_alvo[alvo_id] = dano_por_alvo.get(alvo_id, 0.0) + float((cand.estimativa or {}).get("melhor_dano") or 0.0)
                atacantes_por_alvo[alvo_id] = atacantes_por_alvo.get(alvo_id, 0) + 1
            if "cura_total" in cand.estimativa:
                for alvo in cand.alvos:
                    pid = contexto.pid(alvo)
                    cura_por_alvo[pid] = cura_por_alvo.get(pid, 0.0) + float(cand.estimativa.get("cura_total") or 0.0)

        # Overkill: se o alvo ja morreria, repetir dano tem valor menor.
        for pid, dano in dano_por_alvo.items():
            alvo = contexto.obter_pokemon(pid)
            if alvo is None:
                continue
            vida = contexto.vida_atual(alvo)
            excesso = max(0.0, dano - vida * (1.0 + contexto.config.margem_overkill))
            if excesso > 0:
                score -= excesso * (0.15 + 0.35 * contexto.config.dificuldade.foco_finalizacao)
            if atacantes_por_alvo.get(pid, 0) > 1:
                score += 10.0 * contexto.config.personalidade.preferencia_foco_unico

        # Cura duplicada tambem perde valor.
        for pid, cura in cura_por_alvo.items():
            alvo = contexto.obter_pokemon(pid)
            if alvo is None:
                continue
            faltante = max(0.0, contexto.vida_max(alvo) - contexto.vida_atual(alvo))
            excesso = max(0.0, cura - faltante)
            score -= excesso * 0.18

        # Leitura hacker: recompensa proteger/trocar pokemon que seriam alvos do player.
        if contexto.usar_leitura_player:
            for pid, ameaca in contexto.ameacas_por_pokemon.items():
                if pid in protegidos:
                    score += ameaca * 0.45
                if pid in trocados:
                    score += ameaca * 0.55
        return score
