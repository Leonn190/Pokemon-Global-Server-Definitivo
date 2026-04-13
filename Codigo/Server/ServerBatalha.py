"""Funil de comunicação de batalha (cliente -> simulador de servidor)."""

from __future__ import annotations

import json
from typing import Dict, List

from SimuladorServerJogo.Gerais.Rotas.Atualizador import processar_atualizador_json


def _erro_padrao(mensagem: str) -> Dict[str, object]:
    return {"status": "erro", "mensagem": str(mensagem)}


def _enviar_evento_batalha(ip: str, client_id: str, categoria: str, payload: Dict[str, object]) -> Dict[str, object]:
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": str(client_id or "anon"),
            "diffs": [
                {
                    "tipo": "evento",
                    "categoria": str(categoria or ""),
                    "payload": dict(payload or {}),
                }
            ],
        },
    }
    resposta_json = processar_atualizador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de batalha")


def iniciar_batalha_server(ip: str, client_id: str, contexto_batalha: Dict[str, object] | None = None) -> Dict[str, object]:
    payload = {"contexto_batalha": dict(contexto_batalha or {})}
    return _enviar_evento_batalha(ip, client_id, "batalha_iniciar", payload)


def enviar_jogada_batalha_server(ip: str, client_id: str, jogadas: List[Dict[str, object]] | None = None, batalha_id: str = "") -> Dict[str, object]:
    payload = {
        "batalha_id": str(batalha_id or ""),
        "jogadas": [dict(item) for item in list(jogadas or []) if isinstance(item, dict)],
    }
    return _enviar_evento_batalha(ip, client_id, "batalha_jogada", payload)
