"""Subcérebro de tempo e clima do mundo."""

from __future__ import annotations

import random
from typing import Dict

from SimuladorServerJogo.Gerais.EstadoServidor import obter_tempo_mundo_estado, atualizar_tempo_mundo_estado


class CerebroTempo:
    TPS = 30.0

    def __init__(self, regras: Dict[str, object] | None = None) -> None:
        self._regras = dict(regras or {})
        self._acumulador_tempo_ticks = 0
        inicial = obter_tempo_mundo_estado()
        self._estado: Dict[str, object] = {
            "total_segundos_mundo": int(inicial.get("total_segundos_mundo", 8 * 3600) or (8 * 3600)),
            "dia": int(inicial.get("dia", 0) or 0),
            "hora": int(inicial.get("hora", 8) or 8),
            "minuto": int(inicial.get("minuto", 0) or 0),
            "chuva_intensidade": int(max(0, min(100, int(inicial.get("chuva_intensidade", 0) or 0)))),
            "chuva_alvo": int(max(0, min(100, int(inicial.get("chuva_alvo", 0) or 0)))),
            "chuva_estado": str(inicial.get("chuva_estado", "seco") or "seco"),
            "chuva_habilitada": bool(inicial.get("chuva_habilitada", True)),
            "ticks_chuva_restantes": 0,
            "ticks_ate_nova_variacao": 0,
            "ticks_seco_restantes": 0,
        }

    def snapshot(self) -> Dict[str, object]:
        return {
            "total_segundos_mundo": int(self._estado.get("total_segundos_mundo", 0) or 0),
            "dia": int(self._estado.get("dia", 0) or 0),
            "hora": int(self._estado.get("hora", 0) or 0),
            "minuto": int(self._estado.get("minuto", 0) or 0),
            "chuva_intensidade": int(self._estado.get("chuva_intensidade", 0) or 0),
            "chuva_alvo": int(self._estado.get("chuva_alvo", 0) or 0),
            "chuva_estado": str(self._estado.get("chuva_estado", "seco") or "seco"),
            "chuva_habilitada": bool(self._estado.get("chuva_habilitada", True)),
        }

    def executar_tick(self, rng: random.Random) -> Dict[str, object]:
        self._avancar_tempo()
        self._atualizar_chuva(rng)
        snap = self.snapshot()
        atualizar_tempo_mundo_estado(snap, force=False)
        return snap

    def _avancar_tempo(self) -> None:
        self._acumulador_tempo_ticks += 1
        ticks_por_ciclo = max(1, self._i("tempo_ticks_por_ciclo", 1))
        if self._acumulador_tempo_ticks < ticks_por_ciclo:
            return
        self._acumulador_tempo_ticks = 0
        total = float(self._estado.get("total_segundos_mundo", 0) or 0) + float(self._f("tempo_segundos_mundo_por_tick", 2.0))
        total_int = int(max(0, total))
        self._estado["total_segundos_mundo"] = total_int
        self._estado["dia"] = int(total_int // 86400)
        segundos_dia = int(total_int % 86400)
        self._estado["hora"] = int(segundos_dia // 3600)
        self._estado["minuto"] = int((segundos_dia % 3600) // 60)

    def _atualizar_chuva(self, rng: random.Random) -> None:
        if not bool(self._estado.get("chuva_habilitada", True)):
            self._estado["chuva_intensidade"] = 0
            self._estado["chuva_alvo"] = 0
            self._estado["chuva_estado"] = "desativada"
            self._estado["ticks_chuva_restantes"] = 0
            self._estado["ticks_ate_nova_variacao"] = 0
            return

        intensidade = int(self._estado.get("chuva_intensidade", 0) or 0)
        alvo = int(max(0, min(100, int(self._estado.get("chuva_alvo", 0) or 0))))

        if intensidade <= 0:
            seco_rest = int(self._estado.get("ticks_seco_restantes", 0) or 0)
            if seco_rest > 0:
                self._estado["ticks_seco_restantes"] = seco_rest - 1
            else:
                chance_inicio = self._f("chuva_chance_inicio_por_tick", 0.000025)
                if rng.random() < chance_inicio:
                    self._iniciar_evento_chuva(rng)
                    intensidade = int(self._estado.get("chuva_intensidade", 0) or 0)
                    alvo = int(self._estado.get("chuva_alvo", 0) or 0)

        if int(self._estado.get("ticks_chuva_restantes", 0) or 0) > 0:
            self._estado["ticks_chuva_restantes"] = int(self._estado.get("ticks_chuva_restantes", 1) or 1) - 1
            ticks_var = int(self._estado.get("ticks_ate_nova_variacao", 0) or 0)
            if ticks_var <= 0:
                alvo = self._novo_alvo_chuva(rng)
                self._estado["chuva_alvo"] = alvo
                self._estado["ticks_ate_nova_variacao"] = rng.randint(
                    self._i("chuva_variacao_min_ticks", 450),
                    self._i("chuva_variacao_max_ticks", 2700),
                )
            else:
                self._estado["ticks_ate_nova_variacao"] = ticks_var - 1
        elif intensidade > 0:
            self._estado["chuva_alvo"] = 0
            self._estado["chuva_estado"] = "encerrando"

        intensidade = int(self._estado.get("chuva_intensidade", 0) or 0)
        alvo = int(self._estado.get("chuva_alvo", 0) or 0)
        passo = self._i("chuva_passo_suave", 1) if abs(alvo - intensidade) <= self._i("chuva_delta_passo_suave_limite", 12) else self._i("chuva_passo_forte", 2)
        if intensidade < alvo:
            intensidade = min(alvo, intensidade + passo)
        elif intensidade > alvo:
            intensidade = max(alvo, intensidade - passo)

        if intensidade <= 0 and alvo <= 0 and int(self._estado.get("ticks_chuva_restantes", 0) or 0) <= 0:
            intensidade = 0
            self._estado["chuva_estado"] = "seco"
            if int(self._estado.get("ticks_seco_restantes", 0) or 0) <= 0:
                self._estado["ticks_seco_restantes"] = rng.randint(
                    self._i("chuva_tempo_seco_min_ticks", 14400),
                    self._i("chuva_tempo_seco_max_ticks", 63000),
                )
        elif intensidade > 0:
            self._estado["chuva_estado"] = "chovendo"

        self._estado["chuva_intensidade"] = int(max(0, min(100, intensidade)))
        self._estado["chuva_alvo"] = int(max(0, min(100, int(self._estado.get("chuva_alvo", 0) or 0))))

    def _iniciar_evento_chuva(self, rng: random.Random) -> None:
        self._estado["ticks_chuva_restantes"] = rng.randint(
            self._i("chuva_duracao_min_ticks", 7200),
            self._i("chuva_duracao_max_ticks", 50400),
        )
        self._estado["ticks_ate_nova_variacao"] = rng.randint(
            self._i("chuva_variacao_min_ticks", 450),
            self._i("chuva_variacao_max_ticks", 2700),
        )
        self._estado["chuva_alvo"] = self._novo_alvo_chuva(rng)
        self._estado["chuva_intensidade"] = max(1, int(self._estado.get("chuva_intensidade", 0) or 0))
        self._estado["chuva_estado"] = "iniciando"
        self._estado["ticks_seco_restantes"] = 0

    def _novo_alvo_chuva(self, rng: random.Random) -> int:
        p1 = max(0.0, self._f("chuva_faixa1_peso", 0.60))
        p2 = max(0.0, self._f("chuva_faixa2_peso", 0.30))
        p3 = max(0.0, self._f("chuva_faixa3_peso", 0.10))
        total = max(0.0001, p1 + p2 + p3)
        rol = rng.random()
        c1 = p1 / total
        c2 = (p1 + p2) / total
        if rol < c1:
            return rng.randint(self._i("chuva_intensidade_faixa1_min", 18), self._i("chuva_intensidade_faixa1_max", 45))
        if rol < c2:
            return rng.randint(self._i("chuva_intensidade_faixa2_min", 46), self._i("chuva_intensidade_faixa2_max", 72))
        return rng.randint(self._i("chuva_intensidade_faixa3_min", 73), self._i("chuva_intensidade_faixa3_max", 100))

    def alternar_chuva_habilitada(self) -> bool:
        ativo = not bool(self._estado.get("chuva_habilitada", True))
        self._estado["chuva_habilitada"] = ativo
        if not ativo:
            self._estado["chuva_intensidade"] = 0
            self._estado["chuva_alvo"] = 0
            self._estado["chuva_estado"] = "desativada"
            self._estado["ticks_chuva_restantes"] = 0
            self._estado["ticks_ate_nova_variacao"] = 0
        atualizar_tempo_mundo_estado(self.snapshot(), force=True)
        return ativo

    def chuva_habilitada(self) -> bool:
        return bool(self._estado.get("chuva_habilitada", True))

    def definir_chuva_alvo_manual(self, alvo: int) -> bool:
        if not self.chuva_habilitada():
            return False
        alvo_norm = int(max(0, min(100, int(alvo))))
        self._estado["chuva_alvo"] = alvo_norm
        if alvo_norm > 0:
            self._estado["ticks_chuva_restantes"] = max(
                int(self._estado.get("ticks_chuva_restantes", 0) or 0),
                self._i("chuva_variacao_min_ticks", 450),
            )
            if int(self._estado.get("chuva_intensidade", 0) or 0) <= 0:
                self._estado["chuva_intensidade"] = 1
            self._estado["chuva_estado"] = "chovendo"
        atualizar_tempo_mundo_estado(self.snapshot(), force=True)
        return True

    def _i(self, chave: str, padrao: int) -> int:
        try:
            return int(self._regras.get(chave, padrao))
        except Exception:
            return int(padrao)

    def _f(self, chave: str, padrao: float) -> float:
        try:
            return float(self._regras.get(chave, padrao))
        except Exception:
            return float(padrao)
