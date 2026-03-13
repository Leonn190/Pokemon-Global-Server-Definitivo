"""Rota Atualizador: recebe diffs de clients e aplica no estado do servidor."""

from __future__ import annotations

import json
import time
from typing import Dict

from SimuladorServerJogo.Rotas.Ativador import registrar_diff, _obter_state_client, _coletar_diffs_visibilidade, _filtrar_pacotes_por_camera, _normalizar_posicao, _chunks_carregados_cliente, _raio_visao_por_regras
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, criar_objeto_mundo_server
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_perfil_personagem, atualizar_posicao_personagem, atualizar_inventario_personagem
from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Controle.CerebroCentral import CEREBRO


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
    chunks_carregados = _chunks_carregados_cliente(posicao_camera)
    raio_visao = _raio_visao_por_regras()

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
            registrar_diff(
                "update",
                payload=obj.serializar() if hasattr(obj, "serializar") else dict(payload_in),
                escopo=_escopo_objeto(obj),
                objeto_id=int(objeto_id),
                autor=client_id,
                categoria=str(getattr(obj, "estado_extra", {}).get("subtipo", "outro")),
            )
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
            if categoria == "item_mundo_drop":
                CEREBRO.registrar_drop_item_mundo(client_id, payload)
                aplicados += 1
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
                registrar_diff("spawn", payload=obj.serializar(), escopo=_escopo_objeto(obj), objeto_id=obj.Id, autor=client_id, categoria=str(getattr(obj, "estado_extra", {}).get("subtipo", "outro")))
                aplicados += 1
            except Exception:
                ignorados += 1
            continue

        if tipo == "despawn" and objeto_id is not None:
            removido = BANCO_DADOS.remover_objeto(int(objeto_id))
            if removido is None:
                ignorados += 1
                continue
            registrar_diff("despawn", payload={"id": removido.Id}, escopo=_escopo_objeto(removido), objeto_id=removido.Id, autor=client_id, categoria=str(getattr(removido, "estado_extra", {}).get("subtipo", "outro")))
            aplicados += 1
            continue

        ignorados += 1

    pacotes = _filtrar_pacotes_por_camera(PACOTES_TICK.obter_pacotes_desde(ultimo_tick_recebido, limite=60), posicao_camera, raio_visao, chunks_carregados, client_id=client_id)
    state = _obter_state_client(client_id)
    vistos = state["objetos_vistos"]
    diffs_extra = _coletar_diffs_visibilidade(posicao_camera, chunks_carregados, vistos, client_id=client_id)
    if diffs_extra:
        if pacotes:
            pacote_vis = pacotes[-1]
            diffs_atuais = pacote_vis.get("diffs", []) if isinstance(pacote_vis.get("diffs"), list) else []
            pacote_vis["diffs"] = list(diffs_atuais) + list(diffs_extra)
        else:
            pacotes.append({"tick": 0, "diffs": diffs_extra, "sintetico": True})

    return _ok("Pacote cliente processado", client_id=client_id, aplicados=aplicados, ignorados=ignorados, pacotes=pacotes, tick_atual_servidor=PACOTES_TICK.tick_atual(), servidor_ts=time.time())
