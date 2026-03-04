import json

from SimuladorServerJogo.Ativador import processar_ativador_json
from SimuladorServerJogo.Entrada import processar_entrada_json
from SimuladorServerJogo.ServerOperar import processar_operacao_json
from SimuladorServerJogo.Atualizador import processar_atualizador_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def _enviar_operacao(ip, acao, dados=None):
    pacote = {
        "ip": ip,
        "acao": acao,
        "dados": dados or {},
    }

    resposta_json = processar_operacao_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de operação do servidor")


def entrar_server(ip, usuario):
    pacote = {
        "ip": ip,
        "acao": "entrar_server",
        "dados": {
            "usuario": usuario,
        },
    }

    resposta_json = processar_entrada_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de entrada do servidor")


def operar_server(ip, chave):
    return _enviar_operacao(ip, "operar_server", {"chave": chave})


def obter_status_operacao(ip):
    return _enviar_operacao(ip, "status_operacao")


def definir_server_ligado(ip, ligado):
    return _enviar_operacao(ip, "definir_ligado", {"ligado": bool(ligado)})


def definir_mundo_server(ip, mundo_existente):
    return _enviar_operacao(ip, "definir_mundo", {"mundo_existente": bool(mundo_existente)})


def criar_personagem(ip, usuario, skin, pokemon_inicial):
    pacote = {
        "ip": ip,
        "acao": "criar_personagem",
        "dados": {
            "usuario": usuario,
            "skin": skin,
            "pokemon_inicial": pokemon_inicial,
        },
    }

    resposta_json = processar_entrada_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de criação de personagem")


def consultar_estado_mundo(ip, client_id, posicao_main, raio=640.0):
    pacote = {
        "ip": ip,
        "acao": "ativador",
        "dados": {
            "client_id": client_id,
            "posicao_main": [float(posicao_main[0]), float(posicao_main[1])],
            "raio": float(raio),
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
