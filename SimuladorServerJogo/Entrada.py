import json
import time

from SimuladorServerJogo.Ativador import registrar_diff, desconectar_client
from SimuladorServerJogo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.EstadoServidor import adicionar_personagem, snapshot_estado


def _resposta(status, mensagem, possui_personagem=None, personagem=None):
    pacote = {"status": status, "mensagem": mensagem}
    if possui_personagem is not None:
        pacote["possui_personagem"] = bool(possui_personagem)
    if personagem is not None:
        pacote["personagem"] = personagem
    return pacote


def processar_entrada_json(requisicao_json):
    time.sleep(0.25)

    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    dados = pacote.get("dados", {})

    if acao == "entrar_server":
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
        personagem = None
        if possui_personagem:
            personagem = dict(estado.get("personagens", {}).get(usuario, {}))
            personagem.setdefault("nome", usuario)
            personagem.setdefault("posicao", (0.0, 0.0))
            ator = BANCO_DADOS.garantir_player(
                usuario=usuario,
                skin=str(personagem.get("skin", "S1.png")),
                posicao=tuple(personagem.get("posicao", (0.0, 0.0))),
            )
            personagem["id"] = ator.Id
            mensagem = "Entrada autorizada: personagem já encontrado no servidor."
        else:
            mensagem = "Entrada autorizada: nenhum personagem encontrado para sua conta."

        return json.dumps(
            _resposta("ok", mensagem, possui_personagem=possui_personagem, personagem=personagem),
            ensure_ascii=False,
        )

    if acao == "sair_mundo":
        client_id = str(dados.get("client_id", "")).strip()
        if not client_id:
            return json.dumps(_resposta("erro", "client_id obrigatório"), ensure_ascii=False)
        desconectar_client(client_id)
        return json.dumps(_resposta("ok", "Desconectado do mundo com sucesso"), ensure_ascii=False)

    if acao == "criar_personagem":
        usuario = str(dados.get("usuario", "")).strip()
        skin = str(dados.get("skin", "")).strip()
        pokemon = str(dados.get("pokemon_inicial", "")).strip()

        if not usuario:
            return json.dumps(_resposta("erro", "Usuário obrigatório"), ensure_ascii=False)
        if not skin:
            return json.dumps(_resposta("erro", "Skin inválida"), ensure_ascii=False)
        if not pokemon:
            return json.dumps(_resposta("erro", "Pokémon inicial inválido"), ensure_ascii=False)

        criado, mensagem = adicionar_personagem(usuario, skin, pokemon)
        if criado:
            estado = snapshot_estado()
            personagem = estado.get("personagens", {}).get(usuario, {})
            pos = personagem.get("posicao", (0.0, 0.0))
            ator = BANCO_DADOS.garantir_player(usuario=usuario, skin=skin, posicao=(float(pos[0]), float(pos[1])))
            registrar_diff(
                "spawn",
                payload=ator.serializar(),
                escopo={"centro": [ator.posicao[0], ator.posicao[1]], "raio": 1000.0},
                objeto_id=ator.Id,
            )
        status = "ok" if criado else "negado"
        return json.dumps(_resposta(status, mensagem), ensure_ascii=False)

    return json.dumps(_resposta("erro", "Ação de entrada não suportada"), ensure_ascii=False)
