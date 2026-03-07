"""Funil de comunicação JSON do mundo (cliente -> simulador de servidor)."""

from __future__ import annotations

import json

from SimuladorServerJogo.Ativador import processar_ativador_json
from SimuladorServerJogo.Atualizador import processar_atualizador_json
from SimuladorServerJogo.Entrada import processar_entrada_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def consultar_estado_mundo(ip, client_id, posicao_camera, raio_chunks=3):
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
