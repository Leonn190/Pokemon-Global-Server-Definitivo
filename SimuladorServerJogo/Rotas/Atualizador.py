"""Rota Atualizador: recebe diffs de clients e aplica no estado do servidor."""

from __future__ import annotations

import json
import time
from typing import Dict

from SimuladorServerJogo.Rotas.Ativador import registrar_diff
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import GameObjetoServer, BauServer
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_perfil_personagem, atualizar_posicao_personagem, atualizar_inventario_personagem
from SimuladorServerJogo.Controle.Cerebro import CEREBRO


# --------------------- Funções auxiliares ---------------------
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


def _escopo_objeto(obj: GameObjetoServer) -> Dict[str, object]:
    return {"centro": [obj.posicao[0], obj.posicao[1]], "raio": 780.0}


# ============================= ROTA =============================
# ROTA: recebe diffs de clients e aplica no estado do servidor.
def processar_atualizador_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return _erro("JSON inválido")

    dados = pacote.get("dados", {})
    diffs = dados.get("diffs", [])
    categoria = str(dados.get("categoria", "rapida")).strip().lower()
    if categoria not in ("rapida", "lenta"):
        categoria = "rapida"
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
        meta_in = diff.get("meta", {}) if isinstance(diff.get("meta"), dict) else {}

        if tipo == "abrir_bau" and objeto_id is not None:
            obj = BANCO_DADOS.obter_objeto(int(objeto_id))
            if not isinstance(obj, BauServer):
                ignorados += 1
                continue
            if not obj.abrir():
                ignorados += 1
                continue
            payload_update = {"estado": {"aberto": True}}
            registrar_diff("update", payload=payload_update, escopo=_escopo_objeto(obj), objeto_id=obj.Id, categoria="rapida", origem="server", autor=client_id)
            aplicados += 1
            continue


        if tipo == "evento":
            evento_nome = str(diff.get("evento", "")).strip().lower()
            if evento_nome == "projetil_arremesso_intencao":
                ok = CEREBRO.registrar_intencao_arremesso(client_id, payload)
                if ok:
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            ignorados += 1
            continue

        if tipo == "update" and objeto_id is not None:
            houve_correcao_servidor = False
            if "posicao" in payload:
                payload = dict(payload)
                pos_original = payload.get("posicao")
                payload["posicao"] = _normalizar_posicao_loop(payload.get("posicao"))
                houve_correcao_servidor = payload.get("posicao") != pos_original
            obj = BANCO_DADOS.atualizar_objeto(int(objeto_id), payload)
            if obj is None:
                ignorados += 1
                continue
            usuario = BANCO_DADOS.usuario_por_objeto_id(int(objeto_id))
            if "posicao" in payload and usuario:
                atualizar_posicao_personagem(usuario, obj.posicao)
            if "perfil" in payload and usuario and isinstance(payload.get("perfil"), dict):
                atualizar_perfil_personagem(usuario, payload.get("perfil"))
            if "inventario" in payload and usuario and isinstance(payload.get("inventario"), dict):
                atualizar_inventario_personagem(usuario, payload.get("inventario"))
            origem_diff = str(meta_in.get("origem") or "client")
            if houve_correcao_servidor:
                origem_diff = "server"
            registrar_diff("update", payload=payload, escopo=_escopo_objeto(obj), objeto_id=obj.Id, categoria=categoria, origem=origem_diff, autor=str(meta_in.get("autor") or client_id))
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
                registrar_diff("spawn", payload=obj.serializar(), escopo=_escopo_objeto(obj), objeto_id=obj.Id, categoria=categoria, origem=str(meta_in.get("origem") or "client"), autor=str(meta_in.get("autor") or client_id))
                aplicados += 1
            except Exception:
                ignorados += 1
            continue

        if tipo == "despawn" and objeto_id is not None:
            removido = BANCO_DADOS.remover_objeto(int(objeto_id))
            if removido is None:
                ignorados += 1
                continue
            registrar_diff("despawn", payload={"id": removido.Id}, escopo=_escopo_objeto(removido), objeto_id=removido.Id, categoria=categoria, origem=str(meta_in.get("origem") or "client"), autor=str(meta_in.get("autor") or client_id))
            aplicados += 1
            continue

        ignorados += 1

    return _ok(
        "Diffs processados",
        client_id=client_id,
        categoria=categoria,
        aplicados=aplicados,
        ignorados=ignorados,
        servidor_ts=time.time(),
    )
