"""Rota Atualizador: recebe diffs de clients e aplica no estado do servidor."""

from __future__ import annotations

import json
import math
import time
from typing import Dict

from SimuladorServerJogo.Rotas.Ativador import registrar_diff, _obter_state_client, _coletar_diffs_visibilidade
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, criar_objeto_mundo_server
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_perfil_personagem, atualizar_posicao_personagem, atualizar_inventario_personagem
from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Controle.Cerebro import CEREBRO


def _normalizar_posicao_loop(posicao):
    if not isinstance(posicao, (list, tuple)) or len(posicao) != 2:
        return posicao
    largura, altura = BANCO_DADOS.limites_mundo()
    try:
        x = float(posicao[0]) % max(1.0, float(largura))
        y = float(posicao[1]) % max(1.0, float(altura))
    except (TypeError, ValueError):
        return posicao
    return [x, y]


def _ok(mensagem: str, **extras) -> str:
    payload = {"status": "ok", "mensagem": mensagem}
    payload.update(extras)
    return json.dumps(payload, ensure_ascii=False)


def _erro(mensagem: str) -> str:
    return json.dumps({"status": "erro", "mensagem": mensagem}, ensure_ascii=False)


def _escopo_objeto(obj) -> Dict[str, object]:
    return {"centro": [obj.posicao[0], obj.posicao[1]], "raio": 780.0}


def _normalizar_posicao(valor):
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return (0.0, 0.0)
    try:
        return (float(valor[0]), float(valor[1]))
    except (TypeError, ValueError):
        return (0.0, 0.0)


def _diff_relevante_para_camera(diff, posicao_camera, raio_visao):
    if not isinstance(diff, dict):
        return False
    escopo = diff.get("escopo", {}) if isinstance(diff.get("escopo"), dict) else {}
    centro = escopo.get("centro") if isinstance(escopo.get("centro"), (list, tuple)) else None
    if centro is None:
        return True
    try:
        cx, cy = float(centro[0]), float(centro[1])
    except (TypeError, ValueError, IndexError):
        return True
    raio_diff = float(escopo.get("raio", 0.0) or 0.0)
    return math.hypot(cx - posicao_camera[0], cy - posicao_camera[1]) <= (raio_visao + max(0.0, raio_diff))


def _filtrar_pacotes_por_camera(pacotes, posicao_camera, raio_visao):
    saida = []
    for pacote in pacotes if isinstance(pacotes, list) else []:
        if not isinstance(pacote, dict):
            continue
        diffs = pacote.get("diffs", []) if isinstance(pacote.get("diffs"), list) else []
        diffs_visiveis = [d for d in diffs if _diff_relevante_para_camera(d, posicao_camera, raio_visao)]
        if not diffs_visiveis:
            continue
        novo = dict(pacote)
        novo["diffs"] = diffs_visiveis
        saida.append(novo)
    return saida


def processar_atualizador_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return _erro("JSON inválido")

    dados = pacote.get("dados", {})
    client_id = str(dados.get("client_id", "")).strip()
    if not client_id:
        return _erro("client_id obrigatório")

    ultimo_tick_recebido = int(dados.get("ultimo_tick_recebido", 0) or 0)
    posicao_camera = _normalizar_posicao(dados.get("posicao_camera", [0.0, 0.0]))
    raio_chunks = max(1, int(dados.get("raio_chunks", 4) or 4))
    raio_visao = float((raio_chunks + 2) * BANCO_DADOS.chunk_tamanho_unidade())

    diffs = dados.get("diffs", []) if isinstance(dados.get("diffs"), list) else []
    updates = dados.get("updates", []) if isinstance(dados.get("updates"), list) else []
    if updates:
        diffs.extend([d for d in updates if isinstance(d, dict)])

    aplicados = 0
    ignorados = 0

    for diff in diffs:
        if not isinstance(diff, dict):
            ignorados += 1
            continue
        tipo = str(diff.get("tipo", "")).strip().lower()
        if tipo not in {"spawn", "update", "despawn"}:
            ignorados += 1
            continue

        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}
        objeto_id = diff.get("objeto_id")

        if tipo == "update" and objeto_id is not None:
            obj = BANCO_DADOS.obter_objeto(int(objeto_id))
            if obj is None:
                ignorados += 1
                continue
            payload_in = dict(payload)
            if "posicao" in payload_in:
                payload_in["posicao"] = _normalizar_posicao_loop(payload_in.get("posicao"))
            obj = BANCO_DADOS.atualizar_objeto(int(objeto_id), payload_in)
            usuario = BANCO_DADOS.usuario_por_objeto_id(int(objeto_id))
            if usuario and isinstance(obj, AtorServer):
                if "posicao" in payload_in:
                    atualizar_posicao_personagem(usuario, obj.posicao)
                if "perfil" in payload_in and isinstance(payload_in.get("perfil"), dict):
                    atualizar_perfil_personagem(usuario, payload_in.get("perfil"))
                if "inventario" in payload_in and isinstance(payload_in.get("inventario"), dict):
                    atualizar_inventario_personagem(usuario, payload_in.get("inventario"))
            aplicados += 1
            continue

        if tipo == "spawn":
            categoria = str(diff.get("categoria", "")).strip().lower()
            if categoria == "projetil_lancamento":
                if CEREBRO.registrar_lancamento_projetil(client_id, payload):
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            dados_obj = payload.get("objeto") if isinstance(payload.get("objeto"), dict) else payload
            try:
                novo_id = BANCO_DADOS.gerar_id()
                dados_obj = dict(dados_obj)
                dados_obj["id"] = novo_id
                obj = criar_objeto_mundo_server(dados_obj)
                if obj is None:
                    raise ValueError("tipo nao suportado")
                BANCO_DADOS.inserir_objeto(obj)
                registrar_diff("spawn", payload=obj.serializar(), escopo=_escopo_objeto(obj), objeto_id=obj.Id, autor=client_id, categoria=str(getattr(obj, "estado_extra", {}).get("subtipo", "outro")), base=False)
                aplicados += 1
            except Exception:
                ignorados += 1
            continue

        if tipo == "despawn" and objeto_id is not None:
            removido = BANCO_DADOS.remover_objeto(int(objeto_id))
            if removido is None:
                ignorados += 1
                continue
            registrar_diff("despawn", payload={"id": removido.Id}, escopo=_escopo_objeto(removido), objeto_id=removido.Id, autor="server", categoria=str(getattr(removido, "estado_extra", {}).get("subtipo", "outro")), base=False)
            aplicados += 1
            continue

        ignorados += 1

    pacotes = _filtrar_pacotes_por_camera(PACOTES_TICK.obter_pacotes_desde(ultimo_tick_recebido, limite=60), posicao_camera, raio_visao)
    state = _obter_state_client(client_id)
    vistos = state["objetos_vistos"]
    diffs_vis = _coletar_diffs_visibilidade(posicao_camera, raio_visao, vistos)
    if diffs_vis:
        if pacotes:
            pacote_vis = pacotes[-1]
            diffs_base = pacote_vis.get("diffs", []) if isinstance(pacote_vis.get("diffs"), list) else []
            pacote_vis["diffs"] = list(diffs_base) + list(diffs_vis)
        else:
            pacotes.append({"tick": 0, "diffs": diffs_vis, "sintetico": True})

    return _ok("Pacote cliente processado", client_id=client_id, aplicados=aplicados, ignorados=ignorados, pacotes=pacotes, tick_atual_servidor=PACOTES_TICK.tick_atual(), servidor_ts=time.time())
