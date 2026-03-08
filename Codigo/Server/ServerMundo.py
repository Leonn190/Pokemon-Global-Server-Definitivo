"""Funil de comunicação JSON do mundo (cliente -> simulador de servidor)."""

from __future__ import annotations

import json

from SimuladorServerJogo.Ativador import processar_ativador_json
from SimuladorServerJogo.Atualizador import processar_atualizador_json
from SimuladorServerJogo.Entrada import processar_entrada_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def consultar_estado_mundo(ip, client_id, posicao_camera, raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "ativador",
        "dados": {
            "client_id": client_id,
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            "raio_chunks": int(raio_chunks),
        },
    }
    resposta_json = processar_ativador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta do Ativador")


def consultar_chunks_mundo(ip, client_id, posicao_camera, raio_chunks=4):
    """Consulta exclusiva de chunks do mundo (sem diffs de objetos)."""
    pacote = {
        "ip": ip,
        "acao": "ativador_chunks",
        "dados": {
            "client_id": client_id,
            "modo": "chunks",
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            "raio_chunks": int(raio_chunks),
        },
    }
    resposta_json = processar_ativador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de chunks")


def receber_diffs_mundo(ip, client_id, posicao_camera, categoria="rapida", raio_chunks=4):
    """Consulta exclusiva de diffs remotas por categoria (rápida/lenta)."""
    pacote = {
        "ip": ip,
        "acao": "ativador_diffs",
        "dados": {
            "client_id": client_id,
            "modo": "diffs",
            "categoria": str(categoria),
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            "raio_chunks": int(raio_chunks),
        },
    }
    resposta_json = processar_ativador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de diffs")


def enviar_diffs_mundo(ip, client_id, diffs):
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": client_id,
            "diffs": diffs,
        },
    }
    resposta_json = processar_atualizador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta do Atualizador")


def enviar_diffs_mundo_categoria(ip, client_id, categoria, diffs):
    """Envia uma lista de diffs locais separada por categoria de sincronização."""
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": client_id,
            "categoria": str(categoria),
            "diffs": diffs,
        },
    }
    resposta_json = processar_atualizador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta do Atualizador por categoria")


def desconectar_mundo(ip, client_id):
    pacote = {
        "ip": ip,
        "acao": "sair_mundo",
        "dados": {
            "client_id": client_id,
        },
    }

    resposta_json = processar_entrada_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de desconexão do mundo")
