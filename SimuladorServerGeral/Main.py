import copy
import json
import time

_CONTAS = {
    "Leon19": {
        "senha": "Batata19",
        "data_criacao": "2025-01-03",
        "servidores_registrados": [
            {"id": "local-alpha", "nome": "Servidor Alpha"},
        ],
        "estatisticas_servidores": {
            "local-alpha": {
                "perfil_nome": "Leon19",
                "nivel": 18,
                "batalhas": 52,
                "vitorias": 31,
                "maestria": 120,
                "poder_maximo": 940,
            }
        },
    },
}


def _resposta(status, mensagem, usuario=None, conta=None):
    return {
        "status": status,
        "mensagem": mensagem,
        "usuario": usuario,
        "conta": conta,
    }


def _conta_publica(usuario):
    conta = _CONTAS.get(usuario) or {}
    return {
        "usuario": usuario,
        "data_criacao": conta.get("data_criacao"),
        "servidores_registrados": copy.deepcopy(list(conta.get("servidores_registrados") or [])),
        "estatisticas_servidores": copy.deepcopy(dict(conta.get("estatisticas_servidores") or {})),
    }


def _registrar_server(dados):
    usuario = str(dados.get("usuario", "")).strip()
    server_id = str(dados.get("server_id", "")).strip()
    server_nome = str(dados.get("server_nome") or server_id).strip() or server_id

    conta = _CONTAS.get(usuario)
    if conta is None:
        return _resposta("negado", "Usuário não encontrado")

    servidores = list(conta.get("servidores_registrados") or [])
    if not any(str((srv or {}).get("id") or "") == server_id for srv in servidores):
        servidores.append({"id": server_id, "nome": server_nome})
        conta["servidores_registrados"] = servidores

    estatisticas = dict(conta.get("estatisticas_servidores") or {})
    estatisticas.setdefault(server_id, {
        "perfil_nome": usuario,
        "nivel": 1,
        "batalhas": 0,
        "vitorias": 0,
        "maestria": 0,
        "poder_maximo": 0,
    })
    conta["estatisticas_servidores"] = estatisticas

    return _resposta("ok", "Servidor registrado na conta", usuario=usuario, conta=_conta_publica(usuario))


def processar_requisicao_json(requisicao_json):
    time.sleep(0.25)
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    dados = pacote.get("dados", {})

    if acao == "registrar_server":
        return json.dumps(_registrar_server(dados), ensure_ascii=False)

    if acao != "login":
        return json.dumps(_resposta("erro", "Ação não suportada"), ensure_ascii=False)

    usuario = str(dados.get("usuario", "")).strip()
    senha = str(dados.get("senha", "")).strip()

    if not usuario or not senha:
        return json.dumps(_resposta("erro", "Usuário e senha são obrigatórios"), ensure_ascii=False)

    conta = _CONTAS.get(usuario)
    if conta is None:
        return json.dumps(_resposta("negado", "Usuário não encontrado"), ensure_ascii=False)

    if str(conta.get("senha") or "") != senha:
        return json.dumps(_resposta("negado", "Senha inválida"), ensure_ascii=False)

    return json.dumps(_resposta("ok", "Login autorizado", usuario=usuario, conta=_conta_publica(usuario)), ensure_ascii=False)
