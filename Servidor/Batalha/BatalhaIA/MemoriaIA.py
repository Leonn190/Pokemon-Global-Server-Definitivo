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
    tipos_acao_player: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    protegidos_player: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    sacrificados_player: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    trocas_player: int = 0
    suporte_player: int = 0


class MemoriaIA:
    """Histórico justo: só usa turnos/jogadas já visíveis, nunca a jogada secreta atual."""

    def __init__(self):
        self._por_partida: dict[str, EstadoMemoriaPartida] = {}

    def obter(self, contexto: ContextoIA) -> EstadoMemoriaPartida:
        return self._por_partida.setdefault(contexto.id_partida, EstadoMemoriaPartida())

    def atualizar_com_contexto(self, contexto: ContextoIA) -> None:
        # Mantido por compatibilidade, mas no fluxo novo normalmente não registra nada aqui.
        # A jogada atual do player é registrada explicitamente depois que a IA já decidiu.
        self.registrar_jogadas_player(contexto, contexto.jogadas_visiveis_para_memoria)

    def registrar_jogadas_player(self, contexto: ContextoIA, acoes_player) -> None:
        memoria = self.obter(contexto)
        if memoria.rodada_atualizada == contexto.rodada:
            return
        memoria.rodada_atualizada = contexto.rodada

        for acao in list(acoes_player or []):
            if not isinstance(acao, dict):
                continue
            tipo = normalizar(acao.get("tipo"))
            if tipo:
                memoria.tipos_acao_player[tipo] += 1

            if tipo == "trocareserva" or "troca" in tipo:
                memoria.trocas_player += 1

            ataque = acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {}
            nome = normalizar(ataque.get("nome") or ataque.get("Nome") or ataque.get("Ataque") or ataque.get("Code") or ataque.get("ID"))
            if nome:
                memoria.ataques_player[nome] += 1
                if nome in {"biscoito", "proteger", "tankar", "resetar"}:
                    memoria.suporte_player += 1

            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            pid = alvo.get("pokemon_id")
            if pid:
                memoria.foco_player[str(pid)] += 1
                if nome in {"biscoito", "proteger", "tankar"}:
                    memoria.protegidos_player[str(pid)] += 1

            area_id = alvo.get("area_id")
            if area_id:
                memoria.areas_player[str(area_id)] += 1
                props = contexto.buscar_propriedades_ataque(ataque) or {}
                for aid in contexto.areas_afetadas(area_id, props):
                    poke = contexto.pokemon_na_area(aid)
                    if poke is not None and contexto.lado(poke) == contexto.lado_id:
                        memoria.foco_player[contexto.pid(poke)] += 1

        for pokemon in contexto.inimigos:
            if not contexto.vivo(pokemon):
                memoria.sacrificados_player[contexto.pid(pokemon)] += 1

    def ameaca_memoria(self, contexto: ContextoIA, pokemon) -> float:
        memoria = self.obter(contexto)
        pid = contexto.pid(pokemon)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        return float(memoria.foco_player.get(pid, 0)) * peso

    def bonus_alvo_repetido(self, contexto: ContextoIA, alvo) -> float:
        memoria = self.obter(contexto)
        pid = contexto.pid(alvo)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        return min(12.0, float(memoria.protegidos_player.get(pid, 0)) * 2.0 * peso)

    def area_perigosa(self, contexto: ContextoIA, area_id: object) -> float:
        memoria = self.obter(contexto)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        return float(memoria.areas_player.get(str(area_id or ""), 0)) * peso

    def frequencia_tipo_acao(self, contexto: ContextoIA, tipo: str) -> float:
        memoria = self.obter(contexto)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        return float(memoria.tipos_acao_player.get(normalizar(tipo), 0)) * peso

    def pokemon_costuma_ser_protegido(self, contexto: ContextoIA, pokemon) -> float:
        memoria = self.obter(contexto)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        return float(memoria.protegidos_player.get(contexto.pid(pokemon), 0)) * peso

    def pokemon_costuma_ser_sacrificado(self, contexto: ContextoIA, pokemon) -> float:
        memoria = self.obter(contexto)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        return float(memoria.sacrificados_player.get(contexto.pid(pokemon), 0)) * peso

    def padrao_foco_pokemon_fraco(self, contexto: ContextoIA) -> float:
        memoria = self.obter(contexto)
        peso = float(contexto.config.dificuldade.memoria or 0.0)
        total_focos = sum(int(v) for v in memoria.foco_player.values())
        if total_focos <= 0:
            return 0.0
        focos_fracos = 0
        for pokemon in list(contexto.aliados) + list(contexto.inimigos):
            if contexto.vida_pct(pokemon) <= 0.35:
                focos_fracos += int(memoria.foco_player.get(contexto.pid(pokemon), 0))
        return min(1.0, focos_fracos / max(1, total_focos)) * peso

    def limpar_partida(self, id_partida: str) -> None:
        self._por_partida.pop(str(id_partida or ""), None)
