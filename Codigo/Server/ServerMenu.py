import json

from SimuladorServerJogo.Entrada import processar_entrada_json
from SimuladorServerJogo.EstadoServidor import snapshot_estado
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


def consultar_estado_mundo(ip, posicao_main):
    """Mock de pacote de atualização do mundo para o leitor local."""
    estado = snapshot_estado()
    px, py = posicao_main

    estruturas = [
        {
            "id": 501,
            "tipo": "arvore",
            "posicao": (px + 180.0, py - 120.0),
            "raio_colisao": 22.0,
            "raio_interacao": 28.0,
            "recursos": {"madeira": 2},
        }
    ]

    return {
        "server": ip,
        "chunks": [
            {
                "pos": (0, 0),
                "grid": [[0 for _ in range(8)] for _ in range(8)],
            }
        ],
        "entidades": [],
        "estruturas": estruturas,
        "meta": {
            "nome": estado.get("nome", "Servidor"),
        },
    }
