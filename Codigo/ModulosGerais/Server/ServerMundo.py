"""Funil de comunicação JSON do mundo (cliente -> simulador de servidor)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from Codigo.ModulosGerais.Server.GerenciadorServerList import obter_servidor_por_id
from SimuladorServerJogo.Gerais.ContextoServidor import definir_servidor_ativo, obter_pasta_servidor_ativo
from SimuladorServerJogo.Mundo.TiqueServidor import TIQUE_SERVIDOR
from SimuladorServerJogo.Gerais.Rotas.Ativador import processar_ativador_json
from SimuladorServerJogo.Gerais.Rotas.Atualizador import processar_atualizador_json
from SimuladorServerJogo.Gerais.Rotas.Entrada import processar_entrada_json


def _erro_padrao(mensagem):
    return {"status": "erro", "mensagem": mensagem}


def _preparar_servidor_local(server_id):
    server = obter_servidor_por_id(server_id)
    if not server:
        return _erro_padrao("Servidor não encontrado.")
    if server.get("tipo") != "local":
        return {"status": "negado", "mensagem": "Servidor online ainda não implementado."}
    pasta = Path(server.get("pasta")).resolve()
    if obter_pasta_servidor_ativo() != pasta:
        definir_servidor_ativo(pasta)
        from SimuladorServerJogo.Gerais.EstadoServidor import snapshot_estado
        snapshot_estado()
    return None


def _processar_rota_local(processador, pacote, mensagem_erro):
    erro = _preparar_servidor_local(pacote.get("ip"))
    if erro:
        return erro
    resposta = processador(pacote)
    if isinstance(resposta, dict):
        return resposta
    return _erro_padrao(mensagem_erro)


def definir_bombeamento_local_manual(ativo: bool) -> None:
    TIQUE_SERVIDOR.usar_bombeamento_manual(bool(ativo))


def consultar_estado_mundo(ip, client_id, posicao_camera, raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "ativador",
        "dados": {
            "client_id": client_id,
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
        },
    }
    return _processar_rota_local(processar_ativador_json, pacote, "Falha ao interpretar resposta do Ativador")


def consultar_chunks_mundo(ip, client_id, posicao_camera, raio_chunks=4):
    """Consulta exclusiva de chunks do mundo (sem diffs de objetos)."""
    pacote = {
        "ip": ip,
        "acao": "ativador_chunks",
        "dados": {
            "client_id": client_id,
            "modo": "chunks",
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
        },
    }
    return _processar_rota_local(processar_ativador_json, pacote, "Falha ao interpretar resposta de chunks")


def receber_diffs_mundo(ip, client_id, posicao_camera, categoria="rapida", raio_chunks=4):
    resposta = receber_pacotes_tick_mundo(ip, client_id, 0, posicao_camera=posicao_camera, raio_chunks=raio_chunks)
    if not isinstance(resposta, dict):
        return resposta
    diffs = []
    for pacote in resposta.get("pacotes", []) if isinstance(resposta.get("pacotes"), list) else []:
        diffs.extend(list(pacote.get("diffs", [])) if isinstance(pacote, dict) else [])
    resposta["diffs"] = diffs
    return resposta


def enviar_diffs_mundo(ip, client_id, diffs):
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": client_id,
            "diffs": diffs,
        },
    }
    return _processar_rota_local(processar_atualizador_json, pacote, "Falha ao interpretar resposta do Atualizador")


def enviar_diffs_mundo_categoria(ip, client_id, categoria, diffs):
    return enviar_pacote_cliente_mundo(ip, client_id, ultimo_tick_recebido=0, diffs=diffs, tick_cliente=0)



def desconectar_mundo(ip, client_id):
    erro = _preparar_servidor_local(ip)
    if erro:
        return erro
    pacote = {
        "ip": ip,
        "acao": "sair_mundo",
        "dados": {
            "client_id": client_id,
        },
    }

    resposta_json = processar_entrada_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de desconexão do mundo")


def coletar_regras_mundo(ip):
    erro = _preparar_servidor_local(ip)
    if erro:
        return erro
    pacote = {
        "ip": ip,
        "acao": "coletar_regras_mundo",
        "dados": {},
    }
    resposta_json = processar_entrada_json(json.dumps(pacote, ensure_ascii=False))
    try:
        return json.loads(resposta_json)
    except json.JSONDecodeError:
        return _erro_padrao("Falha ao interpretar resposta de regras do mundo")



def enviar_evento_coleta_estrutura_mundo(ip, client_id, payload):
    dados = dict(payload or {})
    pos_mao = dados.get("pos_mao") if isinstance(dados.get("pos_mao"), (list, tuple)) and len(dados.get("pos_mao")) == 2 else [0.0, 0.0]
    diff = {
        "tipo": "evento",
        "categoria": "coleta_estrutura_natural",
        "payload": {
            "estrutura_id": int(dados.get("estrutura_id", 0) or 0),
            "pos_mao": [float(pos_mao[0]), float(pos_mao[1])],
            "instante_cliente_ms": int(dados.get("instante_cliente_ms", int(time.time() * 1000)) or int(time.time() * 1000)),
        },
    }
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def solicitar_contexto_batalha_mundo(ip, client_id, pokemon_id, centro):
    pos = centro if isinstance(centro, (list, tuple)) and len(centro) == 2 else [0.0, 0.0]
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": client_id,
            "posicao_camera": [float(pos[0]), float(pos[1])],
            "diffs": [
                {
                    "tipo": "evento",
                    "categoria": "batalha_contexto_request",
                    "payload": {
                        "pokemon_id": int(pokemon_id or 0),
                        "centro": [float(pos[0]), float(pos[1])],
                    },
                }
            ],
        },
    }
    return _processar_rota_local(processar_atualizador_json, pacote, "Falha ao interpretar contexto de batalha")


def iniciar_interacao_npc_mundo(ip, client_id, npc_id):
    diff = {"tipo": "evento", "categoria": "npc_interacao_inicio", "payload": {"npc_id": int(npc_id or 0)}}
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def finalizar_interacao_npc_mundo(ip, client_id, npc_id):
    diff = {"tipo": "evento", "categoria": "npc_interacao_fim", "payload": {"npc_id": int(npc_id or 0)}}
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def notificar_pokemon_derrotado_batalha_mundo(ip, client_id, pokemon_id):
    diff = {"tipo": "evento", "categoria": "pokemon_derrotado_batalha", "payload": {"pokemon_id": int(pokemon_id or 0)}}
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def notificar_pokemon_fuga_batalha_mundo(ip, client_id, pokemon_id):
    diff = {"tipo": "evento", "categoria": "pokemon_fuga_batalha", "payload": {"pokemon_id": int(pokemon_id or 0)}}
    return enviar_diffs_mundo_categoria(ip, client_id, "rapida", [diff])


def enviar_pacote_cliente_mundo(ip, client_id, ultimo_tick_recebido, diffs=None, tick_cliente=0, posicao_camera=(0.0, 0.0), raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "atualizador",
        "dados": {
            "client_id": client_id,
            "tick_cliente": int(tick_cliente or 0),
            "ultimo_tick_recebido": int(ultimo_tick_recebido or 0),
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
            "diffs": diffs if isinstance(diffs, list) else list(diffs or []),
        },
    }
    return _processar_rota_local(processar_atualizador_json, pacote, "Falha ao interpretar resposta de pacote cliente")


def receber_pacotes_tick_mundo(ip, client_id, ultimo_tick_recebido, posicao_camera=(0.0,0.0), raio_chunks=4):
    pacote = {
        "ip": ip,
        "acao": "ativador_pacotes",
        "dados": {
            "client_id": client_id,
            "modo": "pacotes",
            "ultimo_tick_recebido": int(ultimo_tick_recebido or 0),
            "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
            # Compatibilidade: servidor define os raios/chunks por regra.
        },
    }
    return _processar_rota_local(processar_ativador_json, pacote, "Falha ao interpretar resposta de pacotes por tick")


def coletar_mapa_mundo(ip, client_id, posicao_camera, conhecidos=None):
    dados = {
        "client_id": client_id,
        "modo": "mapa_bootstrap",
        "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
    }
    if isinstance(conhecidos, dict):
        dados["conhecidos"] = conhecidos
    pacote = {
        "ip": ip,
        "acao": "ativador_mapa_bootstrap",
        "dados": dados,
    }
    return _processar_rota_local(processar_ativador_json, pacote, "Falha ao interpretar resposta de mapa bootstrap")


def atualizar_mapa_mundo(ip, client_id, posicao_camera, conhecidos=None):
    dados = {
        "client_id": client_id,
        "modo": "mapa_delta",
        "posicao_camera": [float(posicao_camera[0]), float(posicao_camera[1])],
    }
    if isinstance(conhecidos, dict):
        dados["conhecidos"] = conhecidos
    pacote = {
        "ip": ip,
        "acao": "ativador_mapa_delta",
        "dados": dados,
    }
    return _processar_rota_local(processar_ativador_json, pacote, "Falha ao interpretar resposta de mapa delta")
