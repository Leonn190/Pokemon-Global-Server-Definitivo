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
    def _pokemons_vivos(cls, pokemons: Iterable[object] | None) -> list[dict]:
        vivos = []
        for pokemon in list(pokemons or []):
            if cls._pokemon_vivo(pokemon):
                vivos.append(deepcopy(pokemon))
        return vivos

    @staticmethod
    def _normalizar_time(indice: int, slots: list[object], base: object | None = None) -> dict:
        if isinstance(base, dict):
            normalizado = deepcopy(base)
            normalizado["Slots"] = deepcopy(slots)
            return normalizado
        return {"Nome": f"Time {int(indice) + 1}" if int(indice) >= 0 else "Inventario", "Slots": deepcopy(slots)}

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
            if not all(cls._pokemon_vivo(slot) for slot in slots[:slots_por_time]):
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

        times_lista = list(times or [])
        if times_lista:
            slots_time_1 = cls._pokemons_vivos(cls._slots(times_lista[0]))
            if slots_time_1:
                return 0, cls._normalizar_time(0, slots_time_1[:slots_por_time], times_lista[0])

        for indice, time in enumerate(times_lista):
            slots = cls._slots(time)
            if len(slots) < slots_por_time or any(slot is None for slot in slots[:slots_por_time]):
                continue
            if not all(cls._pokemon_vivo(slot) for slot in slots[:slots_por_time]):
                continue
            return indice, cls._normalizar_time(indice, list(slots[:slots_por_time]), time)

        vivos_inventario = cls._pokemons_vivos(_pokemons_jogador)
        if vivos_inventario:
            return -1, {"Nome": "Inventario", "Slots": vivos_inventario[:slots_por_time]}

        return -1, {"Nome": "Time 1", "Slots": [None] * slots_por_time}
