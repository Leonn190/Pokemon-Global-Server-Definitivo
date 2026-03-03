import json
import time

_CONTAS = {
    "Leon19": "Batata19",
}


def _resposta(status, mensagem, usuario=None):
    return {
        "status": status,
        "mensagem": mensagem,
        "usuario": usuario,
    }


def processar_requisicao_json(requisicao_json):
    time.sleep(0.25)
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    if acao != "login":
        return json.dumps(_resposta("erro", "Ação não suportada"), ensure_ascii=False)

    dados = pacote.get("dados", {})
    usuario = str(dados.get("usuario", "")).strip()
    senha = str(dados.get("senha", "")).strip()

    if not usuario or not senha:
        return json.dumps(_resposta("erro", "Usuário e senha são obrigatórios"), ensure_ascii=False)

    if usuario not in _CONTAS:
        return json.dumps(_resposta("negado", "Usuário não encontrado"), ensure_ascii=False)

    if _CONTAS[usuario] != senha:
        return json.dumps(_resposta("negado", "Senha inválida"), ensure_ascii=False)

    return json.dumps(_resposta("ok", "Login autorizado", usuario=usuario), ensure_ascii=False)
