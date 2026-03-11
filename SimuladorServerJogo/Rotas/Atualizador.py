"""Rota Atualizador: recebe diffs de clients e aplica no estado do servidor."""

from __future__ import annotations

import json
import math
import time
from typing import Dict

from SimuladorServerJogo.Rotas.Ativador import registrar_diff, _obter_state_client, _coletar_diffs_visibilidade
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import BauServer, criar_objeto_mundo_server
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_perfil_personagem, atualizar_posicao_personagem, atualizar_inventario_personagem, obter_personagem_para_entrada
from SimuladorServerJogo.Controle.Cerebro import CEREBRO
from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK


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

# ============================= ROTA =============================
# ROTA: recebe diffs de clients e aplica no estado do servidor.
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
    categoria = "rapida"
    if isinstance(dados.get("categoria"), str):
        categoria = str(dados.get("categoria") or "rapida").strip().lower()

    envelope_eventos = dados.get("eventos", []) if isinstance(dados.get("eventos"), list) else []
    envelope_updates = dados.get("updates", []) if isinstance(dados.get("updates"), list) else []
    diffs = dados.get("diffs", []) if isinstance(dados.get("diffs"), list) else []

    if envelope_eventos or envelope_updates:
        diffs = []
        for ev in envelope_eventos:
            if isinstance(ev, dict):
                d = dict(ev)
                d.setdefault("tipo", "evento")
                diffs.append(d)
        for up in envelope_updates:
            if isinstance(up, dict):
                d = dict(up)
                d.setdefault("tipo", "update")
                diffs.append(d)

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
            dono_obj = BANCO_DADOS.obter_objeto(int(payload.get("dono_id", 0) or 0))
            info = obj.abrir(player=dono_obj, dono_id=int(payload.get("dono_id", 0) or 0))
            if info is None:
                ignorados += 1
                continue
            usuario = BANCO_DADOS.usuario_por_objeto_id(int(payload.get("dono_id", 0) or 0))
            if usuario:
                dados = obter_personagem_para_entrada(usuario) or {}
                inventario = dados.get("inventario") if isinstance(dados.get("inventario"), dict) else {"itens": []}
                itens = list(inventario.get("itens", []))
                for item in info.get("itens", []):
                    if isinstance(item, dict):
                        itens.append(dict(item))
                inventario["itens"] = itens
                atualizar_inventario_personagem(usuario, inventario)
                if dono_obj is not None:
                    registrar_diff("update", payload={"inventario": inventario}, escopo=_escopo_objeto(dono_obj), objeto_id=int(getattr(dono_obj, "Id", 0)), categoria="rapida", origem="server", autor=client_id)
            payload_update = {"estado": {"aberto": True, "itens": []}}
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
            if evento_nome == "projetil_colisao_candidata":
                ok = CEREBRO.validar_colisao_candidata_projetil(client_id, payload)
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
                obj = criar_objeto_mundo_server(dados_obj)
                if obj is None:
                    raise ValueError("tipo nao suportado")
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

    return _ok(
        "Pacote cliente processado",
        client_id=client_id,
        aplicados=aplicados,
        ignorados=ignorados,
        pacotes=pacotes,
        tick_atual_servidor=PACOTES_TICK.tick_atual(),
        servidor_ts=time.time(),
    )
