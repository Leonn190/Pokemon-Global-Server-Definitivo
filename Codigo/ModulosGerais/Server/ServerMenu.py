import json

from Codigo.ModulosGerais.Server.GerenciadorServerList import obter_servidor_por_id
from SimuladorServerJogo.Gerais.ContextoServidor import definir_servidor_ativo
from SimuladorServerJogo.Gerais.Rotas.Entrada import processar_entrada_json
from SimuladorServerJogo.Gerais.Rotas.ServerOperar import processar_operacao_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def _preparar_servidor_local(server_id):
    server = obter_servidor_por_id(server_id)
    if not server:
        return None, _erro_padrao("Servidor não encontrado.")
    if server.get("tipo") != "local":
        return None, {"status": "negado", "mensagem": "Servidor online ainda não implementado."}
    definir_servidor_ativo(server.get("pasta"))
    return server, None


def _status_online():
    return {
        "status": "ok",
        "mensagem": "Servidor online ainda não implementado.",
        "ligado": False,
        "mundo_existente": False,
        "mundo_em_geracao": False,
        "progresso_mundo": 0,
        "mensagem_geracao": "",
        "erro_geracao": "",
        "operacao_geracao": "nenhuma",
    }


def _enviar_operacao(server_id, acao, dados=None):
    server, erro = _preparar_servidor_local(server_id)
    if erro:
        if acao == "status_operacao" and erro.get("mensagem") == "Servidor online ainda não implementado.":
            return _status_online()
        return erro

    pacote = {
        "server_id": server.get("id"),
        "acao": acao,
        "dados": dados or {},
    }

    resposta_json = processar_operacao_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de operação do servidor")


def entrar_server(server_id, usuario):
    server, erro = _preparar_servidor_local(server_id)
    if erro:
        return erro

    pacote = {
        "server_id": server.get("id"),
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


def operar_server(server_id, chave):
    return _enviar_operacao(server_id, "operar_server", {"chave": chave})


def obter_status_operacao(server_id):
    return _enviar_operacao(server_id, "status_operacao")


def definir_server_ligado(server_id, ligado):
    return _enviar_operacao(server_id, "definir_ligado", {"ligado": bool(ligado)})


def definir_mundo_server(server_id, mundo_existente):
    return _enviar_operacao(server_id, "definir_mundo", {"mundo_existente": bool(mundo_existente)})


def criar_personagem(server_id, usuario, skin, pokemon_inicial):
    server, erro = _preparar_servidor_local(server_id)
    if erro:
        return erro

    pacote = {
        "server_id": server.get("id"),
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


def obter_estatisticas_player(server_id, usuario):
    server, erro = _preparar_servidor_local(server_id)
    if erro:
        return erro

    pacote = {
        "server_id": server.get("id"),
        "acao": "obter_estatisticas_player",
        "dados": {
            "usuario": usuario,
        },
    }

    resposta_json = processar_entrada_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de estatísticas do jogador")
