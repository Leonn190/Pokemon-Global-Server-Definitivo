"""Funil de comunicação JSON do mundo (cliente -> simulador de servidor)."""

from __future__ import annotations

import json
import time

from SimuladorServerJogo.Rotas.Ativador import processar_ativador_json
from SimuladorServerJogo.Rotas.Atualizador import processar_atualizador_json
from SimuladorServerJogo.Rotas.Entrada import processar_entrada_json
from SimuladorServerJogo.Rotas.Terminal import processar_terminal_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def consultar_estado_mundo(ip, client_id, posicao_camera, raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "ativador",
        "dados": {
            "client_id": client_id,
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
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
            # Compatibilidade: servidor define os raios/chunks por regra.
        },
    }
    resposta_json = processar_ativador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de chunks")


def receber_diffs_mundo(ip, client_id, posicao_camera, categoria="rapida", raio_chunks=4):
    resposta = receber_pacotes_tick_mundo(ip, client_id, 0, posicao_camera=posicao_camera, raio_chunks=raio_chunks)
    if not isinstance(resposta, dict):
        return resposta
    diffs = []
    for pacote in resposta.get("pacotes", []) if isinstance(resposta.get("pacotes"), list) else []:
        diffs.extend(list(pacote.get("diffs", [])) if isinstance(pacote, dict) else [])
    resposta["diffs"] = diffs
    return resposta


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
    return enviar_pacote_cliente_mundo(ip, client_id, ultimo_tick_recebido=0, diffs=diffs, tick_cliente=0)


def enviar_mensagem_terminal(ip, autor, texto):
    pacote = {
        "ip": ip,
        "acao": "terminal_enviar",
        "dados": {"autor": str(autor or "anon"), "texto": str(texto or "")},
    }
    resposta_json = processar_terminal_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de envio do terminal")


def buscar_mensagens_terminal(ip, ultimo_id=0, limite=16):
    pacote = {
        "ip": ip,
        "acao": "terminal_buscar",
        "dados": {"ultimo_id": int(ultimo_id), "limite": int(limite)},
    }
    resposta_json = processar_terminal_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de busca do terminal")


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



def enviar_evento_arremesso_mundo(ip, client_id, payload):
    """Mantido por compatibilidade: normaliza para spawn/categoria=projetil_lancamento."""
    dados = dict(payload or {})
    pos_inicial = dados.get("pos_inicial") if isinstance(dados.get("pos_inicial"), (list, tuple)) else dados.get("origem")
    pos_final = dados.get("pos_final") if isinstance(dados.get("pos_final"), (list, tuple)) else dados.get("destino")
    if not isinstance(pos_inicial, (list, tuple)) or len(pos_inicial) != 2:
        pos_inicial = [0.0, 0.0]
    if not isinstance(pos_final, (list, tuple)) or len(pos_final) != 2:
        pos_final = [float(pos_inicial[0]), float(pos_inicial[1])]
    diff = {
        "tipo": "spawn",
        "categoria": "projetil_lancamento",
        "payload": {
            "token": str(dados.get("token") or ""),
            "subtipo_projetil": str(dados.get("subtipo_projetil") or "pokebola"),
            "variante": str(dados.get("variante") or dados.get("item") or "pokebola"),
            "item": str(dados.get("item") or ""),
            "item_base_id": str(dados.get("item_base_id") or ""),
            "pos_inicial": [float(pos_inicial[0]), float(pos_inicial[1])],
            "pos_final": [float(pos_final[0]), float(pos_final[1])],
            "velocidade_tiles_s": float(dados.get("velocidade_tiles_s", 7.0) or 7.0),
            "dono_id": int(dados.get("dono_id", 0) or 0),
            "dono_nome": str(dados.get("dono_nome") or client_id or ""),
            "instante_cliente_ms": int(dados.get("instante_cliente_ms", int(time.time() * 1000)) or int(time.time() * 1000)),
        },
    }
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def enviar_evento_coleta_estrutura_mundo(ip, client_id, payload):
    dados = dict(payload or {})
    pos_mao = dados.get("pos_mao") if isinstance(dados.get("pos_mao"), (list, tuple)) and len(dados.get("pos_mao")) == 2 else [0.0, 0.0]
    diff = {
        "tipo": "spawn",
        "categoria": "estrutura_natural_coleta",
        "payload": {
            "estrutura_id": int(dados.get("estrutura_id", 0) or 0),
            "pos_mao": [float(pos_mao[0]), float(pos_mao[1])],
            "instante_cliente_ms": int(dados.get("instante_cliente_ms", int(time.time() * 1000)) or int(time.time() * 1000)),
        },
    }
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def enviar_pacote_cliente_mundo(ip, client_id, ultimo_tick_recebido, diffs=None, tick_cliente=0, posicao_camera=(0.0, 0.0), raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": client_id,
            "tick_cliente": int(tick_cliente or 0),
            "ultimo_tick_recebido": int(ultimo_tick_recebido or 0),
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
            "diffs": list(diffs or []),
        },
    }
    resposta_json = processar_atualizador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de pacote cliente")


def receber_pacotes_tick_mundo(ip, client_id, ultimo_tick_recebido, posicao_camera=(0.0,0.0), raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "ativador_pacotes",
        "dados": {
            "client_id": client_id,
            "modo": "pacotes",
            "ultimo_tick_recebido": int(ultimo_tick_recebido or 0),
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
        },
    }
    resposta_json = processar_ativador_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de pacotes por tick")
