import json

from SimuladorServerGeral.Main import processar_requisicao_json


def autenticar(usuario, senha):
    pacote = {
        "acao": "login",
        "dados": {
            "usuario": usuario,
            "senha": senha,
        },
    }

    resposta_json = processar_requisicao_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return {
            "status": "erro",
            "mensagem": "Falha ao interpretar resposta do servidor",
            "usuario": None,
        }
