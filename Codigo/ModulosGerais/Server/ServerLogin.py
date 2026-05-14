import json

from ServidorGeral.Main import processar_requisicao_json


def _enviar_pacote(pacote):
    resposta_json = processar_requisicao_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return {
            "status": "erro",
            "mensagem": "Falha ao interpretar resposta do servidor",
            "usuario": None,
        }


def autenticar(usuario, senha):
    return _enviar_pacote({
        "acao": "login",
        "dados": {
            "usuario": usuario,
            "senha": senha,
        },
    })


def registrar_server_conta(usuario, server_id, server_nome=None):
    return _enviar_pacote({
        "acao": "registrar_server",
        "dados": {
            "usuario": usuario,
            "server_id": server_id,
            "server_nome": server_nome,
        },
    })
