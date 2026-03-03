import json

_CHAVE_SEGURANCA = "1900"


def _resposta(status, mensagem):
    return {"status": status, "mensagem": mensagem}


def processar_operacao_json(requisicao_json):
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    if acao != "operar_server":
        return json.dumps(_resposta("erro", "Ação de operação não suportada"), ensure_ascii=False)

    dados = pacote.get("dados", {})
    chave = str(dados.get("chave", "")).strip()

    if len(chave) != 4 or not chave.isdigit():
        return json.dumps(_resposta("negado", "A chave de segurança deve ter 4 dígitos"), ensure_ascii=False)

    if chave != _CHAVE_SEGURANCA:
        return json.dumps(_resposta("negado", "Chave de segurança incorreta"), ensure_ascii=False)

    return json.dumps(_resposta("ok", "Operação autorizada no servidor"), ensure_ascii=False)
