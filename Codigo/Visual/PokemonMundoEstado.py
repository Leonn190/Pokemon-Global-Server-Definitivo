from __future__ import annotations

import math

import pygame


class PokemonMundoEstado:
    _CORES = {
        "normal": ((70, 155, 245), (24, 84, 190)),
        "irritado": ((235, 64, 58), (155, 20, 28)),
        "fruta_1": ((255, 166, 206), (210, 94, 160)),
        "fruta_2": ((255, 92, 188), (210, 40, 145)),
    }

    def __init__(self, pokemon) -> None:
        self.pokemon = pokemon
        self._estado = "normal"
        self._fill = tuple(self._CORES["normal"][0])
        self._borda = tuple(self._CORES["normal"][1])

    def _estado_alvo(self) -> str:
        if bool(getattr(self.pokemon, "EstaIrritado", False)):
            return "irritado"
        frutas = getattr(self.pokemon, "FrutasAplicadas", []) or []
        qtd = min(2, len(frutas) if isinstance(frutas, list) else 0)
        if qtd >= 2:
            return "fruta_2"
        if qtd == 1:
            return "fruta_1"
        return "normal"

    @staticmethod
    def _lerp_cor(atual, alvo, k: float):
        k = max(0.0, min(1.0, float(k)))
        return tuple(int(round(float(a) + (float(b) - float(a)) * k)) for a, b in zip(atual, alvo))

    def atualizar(self, dt: float) -> None:
        self._estado = self._estado_alvo()
        fill_alvo, borda_alvo = self._CORES.get(self._estado, self._CORES["normal"])
        k = min(1.0, max(0.02, float(dt) * 8.0))
        self._fill = self._lerp_cor(self._fill, fill_alvo, k)
        self._borda = self._lerp_cor(self._borda, borda_alvo, k)

    def estado_barra_critica(self):
        p = self.pokemon
        decorrido_s = max(0.0, (pygame.time.get_ticks() - int(getattr(p, "_inicio_barra_local_ms", 0))) / 1000.0)
        ang = (decorrido_s * float(getattr(p, "VelocidadeBarraCaptura", 90.0))) % 360.0
        janela = max(8.0, min(120.0, float(getattr(p, "TamanhoBarraCaptura", 0.32)) * 360.0))
        inicio = ang % 360.0
        fim = (ang + janela) % 360.0
        return inicio, fim, janela

    def captura_critica(self, pos_projetil) -> bool:
        p = self.pokemon
        dx = float(pos_projetil[0]) - float(p.Posicao[0])
        dy = float(pos_projetil[1]) - float(p.Posicao[1])
        ang_impacto = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
        inicio, fim, _janela = self.estado_barra_critica()
        if inicio <= fim:
            return bool(inicio <= ang_impacto <= fim)
        return bool(ang_impacto >= inicio or ang_impacto <= fim)

    def desenhar_circulo_base(self, tela, centro, raio_base):
        pulso = 1.0 + math.sin(pygame.time.get_ticks() * 0.008) * 0.06
        rr = max(3, int(float(raio_base) * pulso))
        pygame.draw.circle(tela, self._fill, centro, rr)
        pygame.draw.circle(tela, self._borda, centro, rr, 2)
        return rr

    def desenhar_barra_critica(self, tela, centro, raio):
        inicio, fim, _janela = self.estado_barra_critica()
        rect = pygame.Rect(0, 0, int(raio) * 2, int(raio) * 2)
        rect.center = centro
        ini = math.radians(-inicio)
        fim_rad = math.radians(-fim)
        pygame.draw.arc(tela, (255, 210, 76), rect, fim_rad, ini, 4)
