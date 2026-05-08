import json
import time

from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff, desconectar_client
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Gerais.EstadoServidor import adicionar_personagem, obter_personagem_para_entrada, snapshot_estado, obter_regras_cliente, registrar_checkpoint_mundo_seguro, aplicar_invulnerabilidade_player
from SimuladorServerJogo.Mundo.Dungeons.EstadoDungeon import normalizar_personagem_login_dungeon


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


def _ator_payload(usuario: str, personagem: dict) -> dict:
    dados = dict(personagem or {})
    inventario = dict(dados.get("inventario") or {})
    return {
        "nome": str(dados.get("nome") or usuario),
        "nome_skin": str(dados.get("skin") or "S1.png"),
        "perfil": {
            "nivel": int(dados.get("nivel", 0) or 0),
            "xp": int(dados.get("xp", 0) or 0),
            "xp_alvo": int(dados.get("xp_alvo", 0) or 0),
            "batalhas_totais": int(dados.get("batalhas_totais", 0) or 0),
            "batalhas_pvp_vencidas": int(dados.get("batalhas_pvp_vencidas", 0) or 0),
            "batalhas_bot_vencidas": int(dados.get("batalhas_bot_vencidas", 0) or 0),
            "tempo_jogo_segundos": float(dados.get("tempo_jogo_segundos", 0.0) or 0.0),
            "baus_abertos": int(dados.get("baus_abertos", 0) or 0),
            "maestria": int(dados.get("maestria", 0) or 0),
            "nivel_mochila": int(dados.get("nivel_mochila", 1) or 1),
            "limite_pokemons": int(dados.get("limite_pokemons", 64) or 64),
            "limite_conhecimento": int(dados.get("limite_conhecimento", 300) or 300),
            "conhecimento": dict(dados.get("conhecimento") or {}),
            "eternidade_derrotada": bool(dados.get("eternidade_derrotada", False)),
            "grande_campeao_derrotado": bool(dados.get("grande_campeao_derrotado", False)),
            "estadios_liderados": list(dados.get("estadios_liderados") or []),
            "moedas_maximas": int(dados.get("moedas_maximas", 0) or 0),
            "recursos_miticos_maximos": int(dados.get("recursos_miticos_maximos", 0) or 0),
            "dinheiro": int(dados.get("dinheiro", 0) or 0),
            "skins_liberadas": list(dados.get("skins_liberadas") or []),
            "habilidades_aprendidas": list(dados.get("habilidades_aprendidas") or []),
        },
        "inventario": {
            "pokemons": list(inventario.get("pokemons") or []),
            "itens": list(inventario.get("itens") or []),
            "times_pokemon": list(inventario.get("times_pokemon") or []),
            "doces": dict(inventario.get("doces") or {}),
        },
    }


def _estadio_id_por_dimensao(dimensao: str) -> int:
    dim = str(dimensao or "").strip()
    if not dim.startswith("Estadio"):
        return 0
    for obj in BANCO_DADOS.listar_objetos():
        if str(getattr(obj, "tipo_classe", "") or "") != "entidade_estadio":
            continue
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        if str(estado.get("dimensao_destino") or "EstadioNormal") == dim:
            return int(getattr(obj, "Id", 0) or 0)
    return 0


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
            personagem = normalizar_personagem_login_dungeon(usuario, personagem)
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
            personagem["posicao"] = [float(pos_dim_dim[0]), float(pos_dim_dim[1])]
            personagem["dimensao"] = dimensao_atual
            estadio_id = _estadio_id_por_dimensao(dimensao_atual)
            if estadio_id > 0:
                ator.estado_extra["estadio_atual_id"] = estadio_id
                personagem["estadio_atual_id"] = estadio_id
            registrar_checkpoint_mundo_seguro(usuario, ator)
            aplicar_invulnerabilidade_player(ator, 90, "entrada_mundo")
            personagem["id"] = ator.Id
            mensagem = "Entrada autorizada: personagem já encontrado no servidor."
        else:
            mensagem = "Entrada autorizada: nenhum personagem encontrado para sua conta."

        return json.dumps(
            _resposta("ok", mensagem, possui_personagem=possui_personagem, personagem=personagem, regras=obter_regras_cliente()),
            ensure_ascii=False,
        )

    # ROTA: sair_mundo
    if acao == "obter_estatisticas_player":
        usuario = str(dados.get("usuario", "")).strip()
        if not usuario:
            return json.dumps(_resposta("erro", "Usuário obrigatório"), ensure_ascii=False)
        estado = snapshot_estado()
        personagem = estado.get("personagens", {}).get(usuario)
        if not isinstance(personagem, dict):
            return json.dumps({"status": "negado", "mensagem": "Personagem não encontrado para esta conta."}, ensure_ascii=False)
        return json.dumps({"status": "ok", "mensagem": "Estatísticas carregadas", "ator": _ator_payload(usuario, personagem)}, ensure_ascii=False)

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
            registrar_checkpoint_mundo_seguro(usuario, ator)
            aplicar_invulnerabilidade_player(ator, 90, "entrada_mundo")
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
