from __future__ import annotations

from Servidor.Batalha.GerenciadorPartidas import GERENCIADOR_PARTIDAS


def rota_inicializar_batalha(dados_inicializacao):
    if not isinstance(dados_inicializacao, dict):
        return {"status": "erro", "mensagem": "Inicializacao invalida", "id_partida": "", "estado_inicial": {}, "avisos": [], "erros": ["dados_inicializacao_devem_ser_dict"]}
    partida = GERENCIADOR_PARTIDAS.criar_partida(dados_inicializacao)
    return {
        "status": "ok",
        "mensagem": "Batalha inicializada",
        "id_partida": partida.id_partida,
        "estado_inicial": partida.serializar_estado_inicial(),
        "avisos": list(partida.avisos),
        "erros": [],
    }


def rota_enviar_jogada(dados_jogada):
    if not isinstance(dados_jogada, dict):
        return {"status": "erro", "mensagem": "Jogada invalida", "id_partida": "", "estado_batalha": "erro", "avisos": [], "erros": ["dados_jogada_devem_ser_dict"]}
    id_partida = str(dados_jogada.get("id_partida") or "")
    if not id_partida:
        return {"status": "erro", "mensagem": "id_partida obrigatorio", "id_partida": "", "estado_batalha": "erro", "avisos": [], "erros": ["id_partida_obrigatorio"]}
    if bool(dados_jogada.get("modo_teste")):
        return GERENCIADOR_PARTIDAS.receber_jogadas_modo_teste(id_partida, dados_jogada.get("jogadas") or [])
    try:
        lado_id = int(dados_jogada.get("lado_id", -1))
    except (TypeError, ValueError):
        return {"status": "erro", "mensagem": "lado_id invalido", "id_partida": id_partida, "estado_batalha": "erro", "avisos": [], "erros": ["lado_id_invalido"]}
    return GERENCIADOR_PARTIDAS.receber_jogada(id_partida, lado_id, dados_jogada)


def rota_finalizar_batalha(dados_finalizacao):
    if not isinstance(dados_finalizacao, dict):
        return {"status": "erro", "mensagem": "Finalizacao invalida", "id_partida": "", "estado_finalizacao": "erro", "avisos": [], "erros": ["dados_finalizacao_devem_ser_dict"]}
    return GERENCIADOR_PARTIDAS.finalizar_partida(
        dados_finalizacao.get("id_partida"),
        motivo=dados_finalizacao.get("motivo"),
        dados=dados_finalizacao.get("dados"),
        lado_id=dados_finalizacao.get("lado_id"),
    )
