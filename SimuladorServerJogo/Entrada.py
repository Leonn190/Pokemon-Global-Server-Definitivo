import json
import time

from SimuladorServerJogo.EstadoServidor import snapshot_estado


def _resposta(status, mensagem, possui_personagem=None):
    pacote = {"status": status, "mensagem": mensagem}
    if possui_personagem is not None:
        pacote["possui_personagem"] = bool(possui_personagem)
    return pacote


def processar_entrada_json(requisicao_json):
    time.sleep(0.25)

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

    estado = snapshot_estado()

    if not estado["mundo_existente"]:
        return json.dumps(_resposta("negado", "Este servidor ainda não possui mundo"), ensure_ascii=False)

    if not estado["ligado"]:
        return json.dumps(_resposta("negado", "Este servidor está desligado"), ensure_ascii=False)

    if usuario in estado["banidos"]:
        return json.dumps(_resposta("negado", "Você está banido deste servidor"), ensure_ascii=False)

    possui_personagem = usuario in estado["jogadores_com_personagem"]
    if possui_personagem:
        mensagem = "Entrada autorizada: personagem já encontrado no servidor."
    else:
        mensagem = "Entrada autorizada: nenhum personagem encontrado para sua conta."

    return json.dumps(_resposta("ok", mensagem, possui_personagem=possui_personagem), ensure_ascii=False)
