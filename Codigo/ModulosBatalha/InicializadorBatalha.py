from __future__ import annotations

import unicodedata
from copy import deepcopy
from typing import Iterable


class InicializadorBatalha:
    TIPOS_ESTADIO = {
        "normal": "Normal",
        "fogo": "Fogo",
        "agua": "Agua",
        "planta": "Planta",
        "eletrico": "Eletrico",
        "gelo": "Gelo",
        "lutador": "Lutador",
        "venenoso": "Venenoso",
        "terrestre": "Terrestre",
        "terra": "Terrestre",
        "voador": "Voador",
        "psiquico": "Psiquico",
        "inseto": "Inseto",
        "pedra": "Pedra",
        "fantasma": "Fantasma",
        "dragao": "Dragao",
        "sombrio": "Sombrio",
        "metal": "Metal",
        "fada": "Fada",
        "cosmico": "Cosmico",
        "sonoro": "Sonoro",
    }

    @staticmethod
    def _normalizar_tipo(valor: object) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
        texto = "".join(ch if ch.isalnum() else "_" for ch in texto.strip().lower())
        while "__" in texto:
            texto = texto.replace("__", "_")
        return texto.strip("_")

    @classmethod
    def tipo_estadio_valido(cls, valor: object) -> str:
        tipo = cls._normalizar_tipo(valor)
        return "terrestre" if tipo == "terra" else tipo if tipo in cls.TIPOS_ESTADIO and tipo != "terra" else ""

    @classmethod
    def nome_tipo_estadio(cls, valor: object) -> str:
        tipo = cls.tipo_estadio_valido(valor)
        return cls.TIPOS_ESTADIO.get(tipo, "")

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

    @classmethod
    def _tipos_pokemon(cls, pokemon: object) -> list[str]:
        if not isinstance(pokemon, dict):
            return []
        fontes = [pokemon]
        estado = pokemon.get("estado")
        if isinstance(estado, dict):
            fontes.append(estado)
        tipos: list[str] = []
        for fonte in fontes:
            bruto = fonte.get("tipos") or fonte.get("Tipos")
            if isinstance(bruto, (list, tuple, set)):
                tipos.extend(cls._normalizar_tipo(t) for t in bruto if str(t or "").strip())
            for chave in ("tipo", "Tipo", "tipo1", "tipo2", "Tipo1", "Tipo2", "Tipo 1", "Tipo 2"):
                valor = fonte.get(chave)
                if str(valor or "").strip():
                    tipos.append(cls._normalizar_tipo(valor))
        unicos: list[str] = []
        for tipo in tipos:
            if tipo and tipo not in unicos:
                unicos.append(tipo)
        return unicos

    @classmethod
    def _pokemon_tem_tipo(cls, pokemon: object, tipo_estadio: str) -> bool:
        tipo = cls.tipo_estadio_valido(tipo_estadio)
        if not tipo:
            return True
        tipos = cls._tipos_pokemon(pokemon)
        return tipo in tipos or (tipo == "terrestre" and "terra" in tipos)

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
    def times_completos_por_tipo(cls, times: Iterable[object], tipo_estadio: object = "", slots_por_time: int = 6) -> list[dict]:
        completos = cls.times_completos(times, slots_por_time=slots_por_time)
        tipo = cls.tipo_estadio_valido(tipo_estadio)
        if not tipo:
            return completos
        return [time for time in completos if all(cls._pokemon_tem_tipo(pokemon, tipo) for pokemon in cls._slots(time)[:slots_por_time])]

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
