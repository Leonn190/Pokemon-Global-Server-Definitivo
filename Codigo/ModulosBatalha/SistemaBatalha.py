from __future__ import annotations

import threading
from typing import Dict, List

from Codigo.Server.ServerBatalha import iniciar_batalha_server


class SistemaBatalha:
    """Controla o estado físico/espacial básico do campo de batalha."""

    def __init__(self, contexto: Dict[str, object] | None = None) -> None:
        self.Contexto = dict(contexto or {})
        self.PokemonsAliados: List[object] = []
        self.PokemonsInimigos: List[object] = []
        self._thread_inicio_server: threading.Thread | None = None

    def definir_lados(self, aliados: List[object], inimigos: List[object]) -> None:
        self.PokemonsAliados = list(aliados or [])
        self.PokemonsInimigos = list(inimigos or [])

    def iniciar_batalha_server_async(self, contexto_batalha: Dict[str, object]) -> None:
        if self._thread_inicio_server is not None and self._thread_inicio_server.is_alive():
            return
        ip = str(self.Contexto.get("server_ip") or "")
        client_id = str(self.Contexto.get("client_id") or "")
        if not ip or not client_id:
            return
        contexto_rede = dict(contexto_batalha or {})

        def _worker() -> None:
            resposta = iniciar_batalha_server(ip=ip, client_id=client_id, contexto_batalha=contexto_rede)
            if not isinstance(resposta, dict):
                return
            self.Contexto["batalha_servidor_inicio"] = resposta
            batalha = resposta.get("batalha") if isinstance(resposta.get("batalha"), dict) else {}
            batalha_id = str(batalha.get("batalha_id") or "")
            if batalha_id:
                self.Contexto["batalha_id_servidor"] = batalha_id

        self._thread_inicio_server = threading.Thread(target=_worker, name="BatalhaInicioServidor", daemon=True)
        self._thread_inicio_server.start()

    def atualizar(self, _eventos, _dt: float) -> None:
        return
