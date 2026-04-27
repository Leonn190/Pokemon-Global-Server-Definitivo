from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .ContextoIA import ContextoIA, normalizar


@dataclass(slots=True)
class EstadoMemoriaPartida:
    rodada_atualizada: int = 0
    foco_player: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    ataques_player: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    areas_player: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class MemoriaIA:
    def __init__(self):
        self._por_partida: dict[str, EstadoMemoriaPartida] = {}

    def obter(self, contexto: ContextoIA) -> EstadoMemoriaPartida:
        return self._por_partida.setdefault(contexto.id_partida, EstadoMemoriaPartida())

    def atualizar_com_contexto(self, contexto: ContextoIA) -> None:
        memoria = self.obter(contexto)
        if memoria.rodada_atualizada == contexto.rodada:
            return
        memoria.rodada_atualizada = contexto.rodada
        for acao in contexto.jogadas_visiveis_para_memoria:
            tipo = str(acao.get("tipo") or "").lower()
            if tipo != "ataque":
                continue
            ataque = acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {}
            nome = normalizar(ataque.get("nome") or ataque.get("Nome") or ataque.get("Ataque") or ataque.get("Code") or ataque.get("ID"))
            if nome:
                memoria.ataques_player[nome] += 1
            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            pid = alvo.get("pokemon_id")
            if pid:
                memoria.foco_player[str(pid)] += 1
            area_id = alvo.get("area_id")
            if area_id:
                memoria.areas_player[str(area_id)] += 1
                for aid in contexto.areas_afetadas(area_id, contexto.buscar_propriedades_ataque(ataque) or {}):
                    poke = contexto.pokemon_na_area(aid)
                    if poke is not None and contexto.lado(poke) == contexto.lado_id:
                        memoria.foco_player[contexto.pid(poke)] += 1

    def ameaca_memoria(self, contexto: ContextoIA, pokemon) -> float:
        memoria = self.obter(contexto)
        pid = contexto.pid(pokemon)
        return float(memoria.foco_player.get(pid, 0))

    def limpar_partida(self, id_partida: str) -> None:
        self._por_partida.pop(str(id_partida or ""), None)
