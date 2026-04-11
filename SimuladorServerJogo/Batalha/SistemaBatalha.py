from __future__ import annotations

from typing import Dict, List

from SimuladorServerJogo.Batalha.PokemonBatalha import PokemonBatalha


class SistemaBatalha:
    def __init__(self, batalha_id: str, client_id: str, contexto: Dict[str, object] | None = None) -> None:
        self.BatalhaId = str(batalha_id)
        self.ClienteDono = str(client_id)
        self.Contexto = dict(contexto or {})
        self.TurnoAtual = 1
        self.Jogadores: Dict[str, List[PokemonBatalha]] = {
            "jogador": [PokemonBatalha(p, lado="jogador") for p in list(self.Contexto.get("jogador") or []) if isinstance(p, dict)],
            "inimigo": [PokemonBatalha(p, lado="inimigo") for p in list(self.Contexto.get("inimigo") or []) if isinstance(p, dict)],
        }
        self.HistoricoJogadas: List[Dict[str, object]] = []

    def adicionar_jogadas(self, client_id: str, jogadas: List[Dict[str, object]]) -> None:
        self.HistoricoJogadas.append(
            {
                "client_id": str(client_id or ""),
                "turno": int(self.TurnoAtual),
                "jogadas": [dict(item) for item in list(jogadas or []) if isinstance(item, dict)],
            }
        )

    def avancar_turno(self) -> None:
        self.TurnoAtual += 1

    def snapshot(self) -> Dict[str, object]:
        return {
            "batalha_id": self.BatalhaId,
            "turno_atual": int(self.TurnoAtual),
            "historico_tamanho": len(self.HistoricoJogadas),
        }
