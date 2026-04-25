from __future__ import annotations

from SimuladorServerJogo.Batalha.GerenciadorPartidas import GERENCIADOR_PARTIDAS


def rota_inicializar_batalha(dados_inicializacao):
    if not isinstance(dados_inicializacao, dict):
        return {"status": "erro", "mensagem": "dados_inicializacao inválido", "id_partida": "", "estado_inicial": {}, "avisos": [], "erros": ["dados_invalidos"]}
    partida = GERENCIADOR_PARTIDAS.criar_partida(dados_inicializacao)
    return {
        "status": "ok",
        "mensagem": "Batalha inicializada",
        "id_partida": partida.id_partida,
        "estado_inicial": partida.serializar_estado_inicial(),
        "avisos": list(partida.avisos_inicializacao),
        "erros": [],
    }


def rota_enviar_jogada(dados_jogada):
    dados_jogada = dados_jogada if isinstance(dados_jogada, dict) else {}
    id_partida = str(dados_jogada.get("id_partida") or "")
    if not id_partida:
        return {"status": "erro", "mensagem": "id_partida obrigatório", "id_partida": "", "estado_batalha": "erro", "avisos": [], "erros": ["id_partida_obrigatorio"]}
    if bool(dados_jogada.get("modo_teste")):
        return GERENCIADOR_PARTIDAS.receber_jogadas_modo_teste(id_partida, dados_jogada.get("jogadas") or [])
    lado_id = int(dados_jogada.get("lado_id", -1))
    return GERENCIADOR_PARTIDAS.receber_jogada(id_partida, lado_id, dados_jogada)


def rota_finalizar_batalha(dados_finalizacao):
    dados_finalizacao = dados_finalizacao if isinstance(dados_finalizacao, dict) else {}
    return GERENCIADOR_PARTIDAS.finalizar_partida(
        dados_finalizacao.get("id_partida"),
        motivo=dados_finalizacao.get("motivo"),
        dados=dados_finalizacao.get("dados"),
    )
