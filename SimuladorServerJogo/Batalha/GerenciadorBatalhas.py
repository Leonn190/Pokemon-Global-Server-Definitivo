from __future__ import annotations

import uuid
from typing import Dict, List

from SimuladorServerJogo.Batalha.LeitorJogadas import LeitorJogadas
from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha


class GerenciadorBatalhas:
    def __init__(self) -> None:
        self._batalhas_por_id: Dict[str, SistemaBatalha] = {}
        self._batalha_ativa_por_cliente: Dict[str, str] = {}
        self._leitor = LeitorJogadas()

    def iniciar_batalha(self, client_id: str, contexto_batalha: Dict[str, object] | None = None) -> Dict[str, object]:
        batalha_id = f"bat-{uuid.uuid4().hex[:10]}"
        sistema = SistemaBatalha(batalha_id=batalha_id, client_id=client_id, contexto=contexto_batalha)
        self._batalhas_por_id[batalha_id] = sistema
        self._batalha_ativa_por_cliente[str(client_id)] = batalha_id
        return {"status": "ok", "mensagem": "Batalha iniciada", "batalha": sistema.snapshot()}

    def obter_batalha(self, batalha_id: str):
        chave = str(batalha_id or "").strip()
        if not chave:
            return None
        return self._batalhas_por_id.get(chave)

    def obter_batalha_ativa(self, client_id: str):
        chave = str(self._batalha_ativa_por_cliente.get(str(client_id), ""))
        return self._batalhas_por_id.get(chave)

    def snapshot_batalha_ativa(self, client_id: str) -> Dict[str, object] | None:
        sistema = self.obter_batalha_ativa(client_id)
        if sistema is None:
            return None
        return sistema.snapshot() if hasattr(sistema, "snapshot") else None

    def receber_jogadas(self, client_id: str, jogadas: List[Dict[str, object]] | None = None, batalha_id: str = "") -> Dict[str, object]:
        chave = str(batalha_id or self._batalha_ativa_por_cliente.get(str(client_id), ""))
        sistema = self._batalhas_por_id.get(chave)
        if sistema is None:
            return {"status": "erro", "mensagem": "Batalha nao encontrada"}
        if bool(getattr(sistema, "Encerrada", False)):
            return {"status": "finalizada", "mensagem": "Batalha ja encerrada", "batalha": sistema.snapshot()}
        return self._leitor.executar_turno(sistema, client_id, jogadas=jogadas)


GERENCIADOR_BATALHAS = GerenciadorBatalhas()
