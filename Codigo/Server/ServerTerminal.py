"""Funil de comunicação JSON do terminal (cliente -> simulador local)."""

from __future__ import annotations

import json

from SimuladorServerJogo.Gerais.Rotas.Terminal import processar_terminal_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def enviar_mensagem_terminal(ip, autor, texto, *, contexto="mundo", meta=None):
    pacote = {
        "ip": ip,
        "acao": "terminal_enviar",
        "dados": {"autor": str(autor or "anon"), "texto": str(texto or ""), "contexto": str(contexto or "mundo"), "meta": dict(meta or {})},
    }
    resposta_json = processar_terminal_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de envio do terminal")


def buscar_mensagens_terminal(ip, ultimo_id=0, limite=16, *, contexto="mundo", meta=None):
    pacote = {
        "ip": ip,
        "acao": "terminal_buscar",
        "dados": {"ultimo_id": int(ultimo_id), "limite": int(limite), "contexto": str(contexto or "mundo"), "meta": dict(meta or {})},
    }
    resposta_json = processar_terminal_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de busca do terminal")
