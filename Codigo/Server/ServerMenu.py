import json

from SimuladorServerJogo.Entrada import processar_entrada_json
from SimuladorServerJogo.ServerOperar import processar_operacao_json


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
