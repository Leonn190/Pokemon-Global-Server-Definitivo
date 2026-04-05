from __future__ import annotations

import random
from typing import Dict


class CerebroCiclo:
    TICKS_POR_SEGUNDO = 30
    SEGUNDOS_MUNDO_POR_TICK = 2

    def __init__(self) -> None:
        self.DiaServidor = 0
        self.HoraServidor = 8
        self.MinutoServidor = 0
        self.ChuvaIntensidade = 0.0
        self._segundos_rel_mundo = (self.HoraServidor * 3600) + (self.MinutoServidor * 60)
        self._chovendo = False
        self._chance_iniciar_chuva_por_tick = 0.00045
        self._ticks_ate_reavaliar = random.randint(120, 240)
        self._alvo_chuva = 0.0

    def executar_tick(self) -> None:
        self._avancar_relogio()
        self._atualizar_chuva()

    def _avancar_relogio(self) -> None:
        self._segundos_rel_mundo += self.SEGUNDOS_MUNDO_POR_TICK
        while self._segundos_rel_mundo >= 86400:
            self._segundos_rel_mundo -= 86400
            self.DiaServidor += 1
        self.HoraServidor = int(self._segundos_rel_mundo // 3600)
        self.MinutoServidor = int((self._segundos_rel_mundo % 3600) // 60)

    def _atualizar_chuva(self) -> None:
        self._ticks_ate_reavaliar -= 1
        if self._ticks_ate_reavaliar <= 0:
            if not self._chovendo and random.random() < self._chance_iniciar_chuva_por_tick * 180:
                self._chovendo = True
                self._alvo_chuva = float(random.randint(18, 62))
                self._ticks_ate_reavaliar = random.randint(240, 540)
            elif self._chovendo:
                if random.random() < 0.16:
                    self._chovendo = False
                    self._alvo_chuva = 0.0
                    self._ticks_ate_reavaliar = random.randint(240, 600)
                else:
                    delta = random.randint(-12, 14)
                    self._alvo_chuva = float(max(8, min(100, int(round(self._alvo_chuva + delta)))))
                    self._ticks_ate_reavaliar = random.randint(90, 240)
            else:
                self._alvo_chuva = 0.0
                self._ticks_ate_reavaliar = random.randint(150, 360)

        passo = 0.22 if self._chovendo else 0.35
        self.ChuvaIntensidade += (self._alvo_chuva - self.ChuvaIntensidade) * passo
        self.ChuvaIntensidade = max(0.0, min(100.0, self.ChuvaIntensidade))

    def snapshot(self) -> Dict[str, int]:
        return {
            "dia": int(self.DiaServidor),
            "hora": int(self.HoraServidor),
            "minuto": int(self.MinutoServidor),
            "chuva_intensidade": int(round(self.ChuvaIntensidade)),
        }
