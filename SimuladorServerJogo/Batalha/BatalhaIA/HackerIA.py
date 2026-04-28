from __future__ import annotations

import copy
from typing import Any

from .AvaliadorIA import AvaliadorIA
from .ContextoIA import ContextoIA
from .GeradorAcoesIA import CandidatoIA, GeradorAcoesIA
from .MacroSimulador import MacroSimulador


class HackerIA:
    """Etapa hacker isolada.

    Com defaults atuais (intuicao/leitura/manipulacao = 0), este módulo nunca
    altera a jogada. Ele existe pronto para quando a integração decidir ativar.
    """

    def __init__(
        self,
        gerador: GeradorAcoesIA | None = None,
        avaliador: AvaliadorIA | None = None,
        macro: MacroSimulador | None = None,
    ):
        self.gerador = gerador or GeradorAcoesIA()
        self.avaliador = avaliador or AvaliadorIA()
        self.macro = macro or MacroSimulador()

    def deve_ativar(self, contexto: ContextoIA) -> bool:
        intuicao = float(contexto.config.hacker.intuicao or 0.0)
        return intuicao > 0.0 and contexto.rng.random() < intuicao

    def refinar(self, contexto: ContextoIA, jogada_base: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.deve_ativar(contexto):
            return jogada_base

        acoes_lidas = self._acoes_lidas(contexto)
        if not acoes_lidas:
            return jogada_base

        budget = int(contexto.config.orcamento_hacker)
        if budget <= 0:
            return jogada_base

        candidatos = self.gerador.gerar(contexto)
        for cand in candidatos:
            self.avaliador.avaliar(contexto, cand)

        candidatos.sort(key=lambda c: c.score, reverse=True)
        foco_player = self._inferir_foco_player(contexto, acoes_lidas)
        candidatos = self._bonificar_respostas(contexto, candidatos, foco_player)
        candidatos.sort(key=lambda c: c.score, reverse=True)

        melhor_jogada = jogada_base
        melhor_score = self._score_jogada_dict(contexto, jogada_base)
        simuladas = 0

        for combo in self._gerar_variacoes_hacker(contexto, candidatos, jogada_base, foco_player):
            if simuladas >= budget:
                break
            resultado = self.macro.simular_jogada(contexto, combo, acoes_oponente=acoes_lidas)
            score = float(resultado.get("score", float("-inf")))
            simuladas += 1
            if score > melhor_score:
                melhor_score = score
                melhor_jogada = [c.copia_acao() for c in combo]

        for idx, acao in enumerate(melhor_jogada, start=1):
            acao.setdefault("origem_ia", True)
            acao.setdefault("ajuste_hacker_ia", True)
            acao.setdefault("ordem_local", idx)
        return melhor_jogada

    def _acoes_lidas(self, contexto: ContextoIA) -> list[dict[str, Any]]:
        todas = list(contexto.jogadas_player or [])
        if not todas:
            return []
        leitura = float(contexto.config.hacker.leitura or 0.0)
        quantidade = int(round(len(todas) * leitura))
        if leitura > 0.0 and quantidade <= 0:
            quantidade = 1
        if quantidade >= len(todas):
            return todas
        # Leitura parcial: mistura primeiras ações com amostra determinística do RNG da rodada.
        pool = list(todas)
        contexto.rng.shuffle(pool)
        return pool[:quantidade]

    def _inferir_foco_player(self, contexto: ContextoIA, acoes_lidas: list[dict[str, Any]]) -> dict[str, float]:
        foco: dict[str, float] = {}
        for acao in acoes_lidas:
            if not isinstance(acao, dict):
                continue
            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            pid = alvo.get("pokemon_id")
            if pid:
                foco[str(pid)] = foco.get(str(pid), 0.0) + 1.0
            area_id = alvo.get("area_id")
            if area_id:
                ataque = acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {}
                props = contexto.buscar_propriedades_ataque(ataque) or {}
                for aid in contexto.areas_afetadas(area_id, props):
                    poke = contexto.pokemon_na_area(aid)
                    if poke is not None and contexto.lado(poke) == contexto.lado_id:
                        foco[contexto.pid(poke)] = foco.get(contexto.pid(poke), 0.0) + 1.0
        return foco

    def _bonificar_respostas(self, contexto: ContextoIA, candidatos: list[CandidatoIA], foco_player: dict[str, float]) -> list[CandidatoIA]:
        for cand in candidatos:
            bonus = 0.0
            if cand.pokemon_id in foco_player:
                if cand.categoria in {"cura", "defesa"} or cand.tipo in {"troca_reserva", "movimento"}:
                    bonus += 18.0 * foco_player[cand.pokemon_id]
            for alvo in cand.alvos or []:
                pid = contexto.pid(alvo)
                if pid in foco_player and contexto.lado(alvo) == contexto.lado_id and cand.categoria in {"cura", "defesa"}:
                    bonus += 16.0 * foco_player[pid]
            cand.score += bonus
            if bonus:
                cand.estimativa["bonus_hacker"] = round(bonus, 4)
        return candidatos

    def _gerar_variacoes_hacker(
        self,
        contexto: ContextoIA,
        candidatos: list[CandidatoIA],
        jogada_base: list[dict[str, Any]],
        foco_player: dict[str, float],
    ):
        # Candidatos defensivos contra foco roubado vêm primeiro.
        defensivos = [
            c for c in candidatos
            if c.pokemon_id in foco_player and (c.categoria in {"cura", "defesa"} or c.tipo in {"troca_reserva", "movimento"})
        ]
        ofensivos = [c for c in candidatos if c.categoria == "dano"]
        pool = (defensivos + ofensivos + candidatos)[: max(8, contexto.config.max_candidatos_planejamento)]

        for tamanho in range(1, min(contexto.config.max_acoes_por_lado, len(pool)) + 1):
            combo = self.macro._normalizar_combo(contexto, pool[:tamanho])
            if combo:
                yield combo

        # Variações localizadas: troca uma ação base por uma resposta hacker.
        base_ids = {str(a.get("pokemon_id") or "") for a in jogada_base if isinstance(a, dict)}
        respostas = [c for c in pool if c.pokemon_id not in base_ids or c.pokemon_id in foco_player]
        for resposta in respostas:
            combo = self.macro._normalizar_combo(contexto, [resposta] + pool[: contexto.config.max_acoes_por_lado])
            if combo:
                yield combo

    def _score_jogada_dict(self, contexto: ContextoIA, jogada: list[dict[str, Any]]) -> float:
        total = 0.0
        for acao in jogada or []:
            if not isinstance(acao, dict):
                continue
            total += float(acao.get("score_ia") or 0.0)
        return total
