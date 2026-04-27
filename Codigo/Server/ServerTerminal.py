"""Funil de comunicação JSON do terminal (cliente -> simulador local)."""

from __future__ import annotations

import json
from pathlib import Path

from Codigo.Server.GerenciadorServerList import obter_servidor_por_id
from SimuladorServerJogo.Gerais.ContextoServidor import definir_servidor_ativo, obter_pasta_servidor_ativo
from SimuladorServerJogo.Gerais.Rotas.Terminal import processar_terminal_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def _preparar_servidor_local(server_id):
    server = obter_servidor_por_id(server_id)
    if not server:
        return _erro_padrao("Servidor não encontrado.")
    if server.get("tipo") != "local":
        return {"status": "negado", "mensagem": "Servidor online ainda não implementado."}
    pasta = Path(server.get("pasta")).resolve()
    if obter_pasta_servidor_ativo() != pasta:
        definir_servidor_ativo(pasta)
        from SimuladorServerJogo.Gerais.EstadoServidor import snapshot_estado
        snapshot_estado()
    return None


def enviar_mensagem_terminal(ip, autor, texto, *, contexto="mundo", meta=None):
    erro = _preparar_servidor_local(ip)
    if erro:
        return erro
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
    erro = _preparar_servidor_local(ip)
    if erro:
        return erro
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
