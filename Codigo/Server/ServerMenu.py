import json

from SimuladorServerJogo.Entrada import processar_entrada_json
from SimuladorServerJogo.ServerOperar import processar_operacao_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


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
    pacote = {
        "ip": ip,
        "acao": "operar_server",
        "dados": {
            "chave": chave,
        },
    }

    resposta_json = processar_operacao_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de operação do servidor")
