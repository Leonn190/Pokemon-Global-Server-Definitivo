from __future__ import annotations

from typing import Dict, List

from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha


class LeitorJogadas:
    """Leitura básica das jogadas recebidas pelo servidor (sem lógica de dano por enquanto)."""

    def executar_turno(self, sistema: SistemaBatalha, client_id: str, jogadas: List[Dict[str, object]] | None = None) -> Dict[str, object]:
        sistema.adicionar_jogadas(client_id, list(jogadas or []))
        sistema.avancar_turno()
        return {"status": "ok", "mensagem": "Jogadas recebidas", "batalha": sistema.snapshot()}
