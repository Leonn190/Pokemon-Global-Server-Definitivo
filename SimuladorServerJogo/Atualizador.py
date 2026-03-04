"""Rota Atualizador: recebe diffs de clients e aplica no estado do servidor."""

from __future__ import annotations

import json
import time
from typing import Dict

from SimuladorServerJogo.Ativador import registrar_diff
from SimuladorServerJogo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.ObjetosMundoServer import GameObjetoServer


def _ok(mensagem: str, **extras) -> str:
    payload = {"status": "ok", "mensagem": mensagem}
    payload.update(extras)
    return json.dumps(payload, ensure_ascii=False)


def _erro(mensagem: str) -> str:
    return json.dumps({"status": "erro", "mensagem": mensagem}, ensure_ascii=False)


def _escopo_objeto(obj: GameObjetoServer) -> Dict[str, object]:
    return {"centro": [obj.posicao[0], obj.posicao[1]], "raio": 780.0}


def processar_atualizador_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return _erro("JSON inválido")

    dados = pacote.get("dados", {})
    diffs = dados.get("diffs", [])
    client_id = str(dados.get("client_id", "")).strip()

    if not client_id:
        return _erro("client_id obrigatório")
    if not isinstance(diffs, list):
        return _erro("diffs deve ser uma lista")

    aplicados = 0
    ignorados = 0

    for diff in diffs:
        if not isinstance(diff, dict):
            ignorados += 1
            continue

        tipo = str(diff.get("tipo", "")).strip()
        payload = diff.get("payload", {}) if isinstance(diff.get("payload", {}), dict) else {}
        objeto_id = diff.get("objeto_id")

        if tipo == "update" and objeto_id is not None:
            obj = BANCO_DADOS.atualizar_objeto(int(objeto_id), payload)
            if obj is None:
                ignorados += 1
                continue
            registrar_diff("update", payload=payload, escopo=_escopo_objeto(obj), objeto_id=obj.Id)
            aplicados += 1
            continue

        if tipo == "spawn":
            dados_obj = payload.get("objeto") if isinstance(payload.get("objeto"), dict) else payload
            try:
                novo_id = BANCO_DADOS.gerar_id()
                dados_obj = dict(dados_obj)
                dados_obj["id"] = novo_id
                obj = GameObjetoServer.de_dict(dados_obj)
                BANCO_DADOS.inserir_objeto(obj)
                registrar_diff("spawn", payload=obj.serializar(), escopo=_escopo_objeto(obj), objeto_id=obj.Id)
                aplicados += 1
            except Exception:
                ignorados += 1
            continue

        if tipo == "despawn" and objeto_id is not None:
            removido = BANCO_DADOS.remover_objeto(int(objeto_id))
            if removido is None:
                ignorados += 1
                continue
            registrar_diff("despawn", payload={"id": removido.Id}, escopo=_escopo_objeto(removido), objeto_id=removido.Id)
            aplicados += 1
            continue

        ignorados += 1

    return _ok("Diffs processados", client_id=client_id, aplicados=aplicados, ignorados=ignorados, servidor_ts=time.time())
