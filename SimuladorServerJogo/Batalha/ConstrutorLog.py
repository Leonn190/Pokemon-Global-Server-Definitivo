from __future__ import annotations


class ConstrutorLog:
    def __init__(self, partida):
        self.partida = partida

    def construir_resultado(self, rodada_anterior: int, avisos=None, erros_acoes=None, acoes_falhas=None):
        partida = self.partida
        resultado = {
            "rodada_anterior": int(rodada_anterior),
            "rodada_atual": int(partida.rodada_atual),
            "estado_batalha": str(partida.estado_partida),
            "finalizada": bool(partida.finalizada),
            "vencedor": partida.vencedor,
            "perdedor": partida.perdedor,
            "pokemons": {pid: pokemon.serializar() for pid, pokemon in partida.pokemons_por_id.items()},
            "areas": dict(partida.ocupacao_areas),
            "lados": list(partida.lados.keys()),
            "avisos": list(avisos or []),
            "erros_acoes": list(erros_acoes or []),
            "acoes_falhas": list(acoes_falhas or []),
        }
        return {
            "id_log": f"{int(rodada_anterior):06d}",
            "rodada": int(rodada_anterior),
            "historico": [],
            "resultado": resultado,
        }

