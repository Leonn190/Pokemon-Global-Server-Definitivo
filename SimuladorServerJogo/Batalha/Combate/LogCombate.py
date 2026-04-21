from __future__ import annotations

from typing import Any


def _fnum(valor: object, padrao: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


def _efeitos(pokemon) -> list[dict[str, Any]]:
    efeitos = getattr(pokemon, "Efeitos", [])
    return [dict(item) for item in list(efeitos or []) if isinstance(item, dict)]


def snapshot_pokemon(pokemon) -> dict[str, Any]:
    return {
        "id": str(getattr(pokemon, "Uid", "") or ""),
        "nome": str(getattr(pokemon, "Nome", "") or getattr(pokemon, "Especie", "") or ""),
        "lado": str(getattr(pokemon, "Lado", "") or ""),
        "vida": _fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0),
        "energia": _fnum(getattr(pokemon, "Energia", 0.0), 0.0),
        "barreira": _fnum(getattr(pokemon, "Barreira", 0.0), 0.0),
        "efeitos": _efeitos(pokemon),
        "fora_de_combate": bool(getattr(pokemon, "ForaDeCombate", False)),
    }


def snapshot_batalha(pokemons) -> dict[str, dict[str, Any]]:
    return {str(getattr(p, "Uid", "") or ""): snapshot_pokemon(p) for p in list(pokemons or [])}


def comparar_snapshots(antes: dict[str, Any], depois: dict[str, Any]) -> dict[str, Any]:
    ids = sorted(set(antes.keys()) | set(depois.keys()))
    diferencas: dict[str, Any] = {}
    for pokemon_id in ids:
        pre = dict(antes.get(pokemon_id) or {})
        pos = dict(depois.get(pokemon_id) or {})
        if pre == pos:
            continue
        diferencas[pokemon_id] = {
            "vida": {"antes": pre.get("vida"), "depois": pos.get("vida"), "delta": _fnum(pos.get("vida")) - _fnum(pre.get("vida"))},
            "energia": {"antes": pre.get("energia"), "depois": pos.get("energia"), "delta": _fnum(pos.get("energia")) - _fnum(pre.get("energia"))},
            "barreira": {"antes": pre.get("barreira"), "depois": pos.get("barreira"), "delta": _fnum(pos.get("barreira")) - _fnum(pre.get("barreira"))},
            "efeitos_antes": list(pre.get("efeitos") or []),
            "efeitos_depois": list(pos.get("efeitos") or []),
            "fora_de_combate": {"antes": bool(pre.get("fora_de_combate")), "depois": bool(pos.get("fora_de_combate"))},
        }
    return {"pokemons": diferencas, "quantidade_alterados": len(diferencas)}


class LogCombate:
    def __init__(self, rodada: int | None = None, tick: int | None = None) -> None:
        self.rodada = rodada
        self.tick = tick
        self.sumario: list[dict[str, Any]] = []
        self.historico: list[dict[str, Any]] = []
        self.resultados: list[dict[str, Any]] = []
        self.alertas: list[dict[str, Any]] = []

    def _evento(self, tipo: str, dados: dict[str, Any]) -> dict[str, Any]:
        base = {"tipo": str(tipo)}
        if self.rodada is not None:
            base["rodada"] = int(self.rodada)
        if self.tick is not None:
            base["tick"] = int(self.tick)
        base.update(dados)
        return base

    def adicionar_sumario(self, tipo: str, **dados) -> dict[str, Any]:
        evento = self._evento(tipo, dados)
        self.sumario.append(evento)
        return evento

    def adicionar_historico(self, tipo: str, **dados) -> dict[str, Any]:
        evento = self._evento(tipo, dados)
        self.historico.append(evento)
        return evento

    def adicionar_resultado(self, tipo: str, **dados) -> dict[str, Any]:
        evento = self._evento(tipo, dados)
        self.resultados.append(evento)
        return evento

    def adicionar_alerta(self, tipo: str, **dados) -> dict[str, Any]:
        evento = self._evento(tipo, dados)
        self.alertas.append(evento)
        return evento

    def como_dict(self) -> dict[str, Any]:
        return {
            "rodada": self.rodada,
            "tick": self.tick,
            "sumario": list(self.sumario),
            "historico": list(self.historico),
            "resultados": list(self.resultados),
            "alertas": list(self.alertas),
        }
