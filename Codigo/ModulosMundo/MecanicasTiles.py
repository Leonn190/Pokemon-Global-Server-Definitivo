from __future__ import annotations


class MecanicasTiles:
    TILE_AGUA_FUNDA = 0
    TILE_AGUA_RASA = 1
    TILE_BURACO = 10

    @classmethod
    def multiplicador_velocidade(cls, tile_id) -> float:
        try:
            tile = int(tile_id)
        except (TypeError, ValueError):
            return 1.0
        if tile == cls.TILE_AGUA_RASA:
            return 0.95
        if tile == cls.TILE_AGUA_FUNDA:
            return 0.80
        return 1.0

    @classmethod
    def estado_visual(cls, tile_id) -> dict:
        try:
            tile = int(tile_id)
        except (TypeError, ValueError):
            return {"agua": "", "buraco": False}
        if tile == cls.TILE_AGUA_RASA:
            return {"agua": "rasa", "buraco": False}
        if tile == cls.TILE_AGUA_FUNDA:
            return {"agua": "funda", "buraco": False}
        if tile == cls.TILE_BURACO:
            return {"agua": "", "buraco": True}
        return {"agua": "", "buraco": False}

    @classmethod
    def aplicar_no_ator(cls, ator, tile_id) -> dict:
        estado = cls.estado_visual(tile_id)
        if ator is not None:
            setattr(ator, "TileAtualMecanica", int(tile_id) if tile_id is not None else None)
            setattr(ator, "EstadoAgua", estado.get("agua", ""))
            setattr(ator, "SobreBuraco", bool(estado.get("buraco", False)))
        return estado
