import json

_SERVER_DISPONIVEL = {
    "nome": "Servidor Indigo",
    "ip": "203.0.113.77:8123",
    "ligado": True,
    "mundo_existente": True,
    "banidos": {"JogadorBanido"},
    "jogadores_com_personagem": {"Leon19"},
}


def _resposta(status, mensagem, possui_personagem=None):
    pacote = {"status": status, "mensagem": mensagem}
    if possui_personagem is not None:
        pacote["possui_personagem"] = bool(possui_personagem)
    return pacote


def processar_entrada_json(requisicao_json):
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    if acao != "entrar_server":
        return json.dumps(_resposta("erro", "Ação de entrada não suportada"), ensure_ascii=False)

    dados = pacote.get("dados", {})
    usuario = str(dados.get("usuario", "")).strip()

    if not usuario:
        return json.dumps(_resposta("erro", "Usuário obrigatório"), ensure_ascii=False)

    if not _SERVER_DISPONIVEL["mundo_existente"]:
        return json.dumps(_resposta("negado", "Este servidor ainda não possui mundo"), ensure_ascii=False)

    if not _SERVER_DISPONIVEL["ligado"]:
        return json.dumps(_resposta("negado", "Este servidor está desligado"), ensure_ascii=False)

    if usuario in _SERVER_DISPONIVEL["banidos"]:
        return json.dumps(_resposta("negado", "Você está banido deste servidor"), ensure_ascii=False)

    possui_personagem = usuario in _SERVER_DISPONIVEL["jogadores_com_personagem"]
    if possui_personagem:
        mensagem = "Entrada autorizada: personagem já encontrado no servidor."
    else:
        mensagem = "Entrada autorizada: nenhum personagem encontrado para sua conta."

    return json.dumps(_resposta("ok", mensagem, possui_personagem=possui_personagem), ensure_ascii=False)
