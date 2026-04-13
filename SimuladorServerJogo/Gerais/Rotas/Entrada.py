import json
import time

from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff, desconectar_client
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Gerais.EstadoServidor import adicionar_personagem, obter_personagem_para_entrada, snapshot_estado, obter_regras_cliente


# --------------------- Funções auxiliares ---------------------
def _resposta(status, mensagem, possui_personagem=None, personagem=None, regras=None):
    pacote = {"status": status, "mensagem": mensagem}
    if possui_personagem is not None:
        pacote["possui_personagem"] = bool(possui_personagem)
    if personagem is not None:
        pacote["personagem"] = personagem
    if regras is not None:
        pacote["regras"] = regras
    return pacote


# ============================= ROTA =============================
# ROTA: processa requisições de entrada no servidor.
def processar_entrada_json(requisicao_json):
    time.sleep(0.25)

    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    dados = pacote.get("dados", {})

    # ROTA: entrar_server
    if acao == "entrar_server":
        usuario = str(dados.get("usuario", "")).strip()

        if not usuario:
            return json.dumps(_resposta("erro", "Usuário obrigatório"), ensure_ascii=False)

        estado = snapshot_estado()

        if estado.get("mundo_em_geracao"):
            return json.dumps(_resposta("negado", "O mundo está em criação. Aguarde o término."), ensure_ascii=False)

        if not estado["mundo_existente"]:
            return json.dumps(_resposta("negado", "Este servidor ainda não possui mundo"), ensure_ascii=False)

        if not estado["ligado"]:
            return json.dumps(_resposta("negado", "Este servidor está desligado"), ensure_ascii=False)

        if usuario in estado["banidos"]:
            return json.dumps(_resposta("negado", "Você está banido deste servidor"), ensure_ascii=False)

        possui_personagem = usuario in estado["jogadores_com_personagem"]
        personagem = None
        if possui_personagem:
            personagem = obter_personagem_para_entrada(usuario) or {}
            personagem.setdefault("nome", usuario)
            dimensao_atual = str(personagem.get("dimensao_atual") or "Mundo")
            pos_dim = personagem.get("posicoes_por_dimensao") if isinstance(personagem.get("posicoes_por_dimensao"), dict) else {}
            pos_dim_dim = pos_dim.get(dimensao_atual) if isinstance(pos_dim.get(dimensao_atual), (list, tuple)) and len(pos_dim.get(dimensao_atual)) == 2 else personagem.get("posicao", (0.0, 0.0))
            ator = BANCO_DADOS.garantir_player(
                usuario=usuario,
                skin=str(personagem.get("skin", "S1.png")),
                posicao=tuple(pos_dim_dim),
            )
            ator.estado_extra["dimensao"] = dimensao_atual
            ator.estado_extra["posicoes_por_dimensao"] = {str(k): [float(v[0]), float(v[1])] for k, v in pos_dim.items() if isinstance(v, (list, tuple)) and len(v) == 2}
            personagem["id"] = ator.Id
            mensagem = "Entrada autorizada: personagem já encontrado no servidor."
        else:
            mensagem = "Entrada autorizada: nenhum personagem encontrado para sua conta."

        return json.dumps(
            _resposta("ok", mensagem, possui_personagem=possui_personagem, personagem=personagem, regras=obter_regras_cliente()),
            ensure_ascii=False,
        )

    # ROTA: sair_mundo
    if acao == "sair_mundo":
        client_id = str(dados.get("client_id", "")).strip()
        if not client_id:
            return json.dumps(_resposta("erro", "client_id obrigatório"), ensure_ascii=False)
        desconectar_client(client_id)
        return json.dumps(_resposta("ok", "Desconectado do mundo com sucesso"), ensure_ascii=False)

    # ROTA: criar_personagem
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

    # ROTA: coletar_regras_mundo
    if acao == "coletar_regras_mundo":
        return json.dumps(_resposta("ok", "Regras do mundo coletadas", regras=obter_regras_cliente()), ensure_ascii=False)

    return json.dumps(_resposta("erro", "Ação de entrada não suportada"), ensure_ascii=False)
