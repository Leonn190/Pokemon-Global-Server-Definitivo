from __future__ import annotations

from copy import deepcopy
from typing import Iterable


class InicializadorBatalha:
    @staticmethod
    def _slots(time: object) -> list:
        if isinstance(time, dict):
            return list(time.get("Slots") or time.get("slots") or [])
        if isinstance(time, list):
            return list(time)
        return []

    @staticmethod
    def _pokemon_vivo(pokemon: object) -> bool:
        if not isinstance(pokemon, dict):
            return False
        fonte = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
        for chave in ("HP", "hp", "Vida", "vida"):
            if chave not in fonte:
                continue
            try:
                return float(fonte.get(chave) or 0) > 0
            except (TypeError, ValueError):
                return True
        return True

    @classmethod
    def time_tem_pokemon_vivo(cls, time: object) -> bool:
        return any(cls._pokemon_vivo(pokemon) for pokemon in cls._slots(time))

    @classmethod
    def times_completos(cls, times: Iterable[object], slots_por_time: int = 6) -> list[dict]:
        saida = []
        slots_por_time = max(1, int(slots_por_time or 6))
        for indice, time in enumerate(list(times or [])):
            slots = cls._slots(time)
            if len(slots) < slots_por_time or any(slot is None for slot in slots[:slots_por_time]):
                continue
            if not any(cls._pokemon_vivo(slot) for slot in slots[:slots_por_time]):
                continue
            if isinstance(time, dict):
                normalizado = deepcopy(time)
                normalizado["Slots"] = deepcopy(slots[:slots_por_time])
            else:
                normalizado = {"Nome": f"Time {indice + 1}", "Slots": deepcopy(slots[:slots_por_time])}
            saida.append(normalizado)
        return saida

    @classmethod
    def escolher_time_confronto_com_indice(
        cls,
        times: Iterable[object],
        _pokemons_jogador: Iterable[object] | None = None,
        slots_por_time: int = 6,
    ) -> tuple[int, dict]:
        slots_por_time = max(1, int(slots_por_time or 6))
        for indice, time in enumerate(list(times or [])):
            slots = cls._slots(time)
            if len(slots) < slots_por_time or any(slot is None for slot in slots[:slots_por_time]):
                continue
            if not any(cls._pokemon_vivo(slot) for slot in slots[:slots_por_time]):
                continue
            escolhido = deepcopy(time) if isinstance(time, dict) else {"Nome": f"Time {indice + 1}", "Slots": deepcopy(slots[:slots_por_time])}
            escolhido["Slots"] = deepcopy(slots[:slots_por_time])
            return indice, escolhido
        return -1, {"Nome": "Time 1", "Slots": [None] * slots_por_time}
