"""Rota Ativador: entrega chunks e pacotes de tick para sincronização."""

from __future__ import annotations

import json
import math
import threading
import time
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.Cerebro import CEREBRO
from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Controle.TiqueServidor import TIQUE_SERVIDOR

Vector2 = Tuple[float, float]

_LOCK = threading.Lock()
_DIFF_SEQ = 0
_CLIENTS_CONHECIDOS: Set[str] = set()
_CLIENT_STATE: Dict[str, Dict[str, object]] = {}


def _next_seq() -> int:
    global _DIFF_SEQ
    _DIFF_SEQ += 1
    return _DIFF_SEQ


def registrar_diff(tipo: str, payload: Dict[str, object], escopo: Dict[str, object], objeto_id=None, autor: str = "server", categoria: str | None = None, base: bool = False) -> Dict[str, object]:
    diff = {
        "seq": _next_seq(),
        "timestamp": time.time(),
        "tipo": str(tipo or ""),
        "objeto_id": objeto_id,
        "autor": str(autor or "server"),
        "payload": dict(payload or {}),
        "escopo": dict(escopo or {}),
        "base": bool(base),
    }
    if categoria is not None:
        diff["categoria"] = str(categoria)
    PACOTES_TICK.registrar_diff_pendente(diff)
    return diff


def _normalizar_posicao(valor) -> Vector2:
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return (0.0, 0.0)
    return (float(valor[0]), float(valor[1]))


def _obter_state_client(client_id: str) -> Dict[str, object]:
    if client_id not in _CLIENT_STATE:
        _CLIENT_STATE[client_id] = {"objetos_vistos": set()}
    return _CLIENT_STATE[client_id]


def _chunks_no_raio(posicao_camera: Vector2, raio_chunks: int):
    centro = BANCO_DADOS.chunk_da_posicao(posicao_camera)
    chunks = []
    raio = max(0, int(raio_chunks))
    for dx in range(-raio, raio + 1):
        for dy in range(-raio, raio + 1):
            chunks.append(BANCO_DADOS.normalizar_chunk((centro[0] + dx, centro[1] + dy)))
    return chunks




def _diff_relevante_para_camera(diff, posicao_camera: Vector2, raio_visao: float) -> bool:
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


def _filtrar_pacotes_por_camera(pacotes, posicao_camera: Vector2, raio_visao: float):
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

def _coletar_diffs_visibilidade(posicao_camera: Vector2, raio: float, vistos: Set[int]) -> List[Dict[str, object]]:
    objetos_proximos = BANCO_DADOS.buscar_proximos(posicao_camera, raio)
    ids_proximos = {int(obj.Id) for obj in objetos_proximos}
    diffs: List[Dict[str, object]] = []
    agora = time.time()
    for obj in objetos_proximos:
        if obj.Id in vistos:
            continue
        vistos.add(int(obj.Id))
        categoria = str(getattr(obj, "estado_extra", {}).get("subtipo", "outro") or "outro")
        diffs.append({"seq": _next_seq(), "timestamp": agora, "tipo": "spawn", "objeto_id": obj.Id, "autor": "server", "payload": obj.serializar(), "escopo": {"centro": list(obj.posicao), "raio": raio}, "categoria": categoria, "base": False})
    for oid in [oid for oid in list(vistos) if oid not in ids_proximos]:
        vistos.discard(int(oid))
        diffs.append({"seq": _next_seq(), "timestamp": agora, "tipo": "despawn", "objeto_id": int(oid), "autor": "server", "payload": {}, "escopo": {"centro": list(posicao_camera), "raio": raio}, "categoria": "outro", "base": False})
    return diffs




def _coletar_diffs_base_players(client_id: str, posicao_camera: Vector2, raio: float) -> List[Dict[str, object]]:
    diffs: List[Dict[str, object]] = []
    alvo_id = BANCO_DADOS.objeto_id_por_usuario(client_id)
    agora = time.time()
    for obj in BANCO_DADOS.buscar_proximos(posicao_camera, raio):
        subtipo = str(getattr(obj, "estado_extra", {}).get("subtipo", ""))
        if subtipo != "player":
            continue
        usuario_obj = BANCO_DADOS.usuario_por_objeto_id(int(obj.Id)) or ""
        if int(obj.Id) == int(alvo_id) or str(usuario_obj) == str(client_id):
            continue
        diffs.append({
            "seq": _next_seq(),
            "timestamp": agora,
            "tipo": "update",
            "objeto_id": int(obj.Id),
            "autor": str(usuario_obj or "server"),
            "payload": obj.serializar(),
            "escopo": {"centro": [obj.posicao[0], obj.posicao[1]], "raio": 780.0},
            "categoria": "player",
            "base": True,
        })
    return diffs
def processar_ativador_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps({"status": "erro", "mensagem": "JSON inválido"}, ensure_ascii=False)

    dados = pacote.get("dados", {})
    client_id = str(dados.get("client_id", "")).strip()
    if not client_id:
        return json.dumps({"status": "erro", "mensagem": "client_id obrigatório"}, ensure_ascii=False)

    posicao_camera = _normalizar_posicao(dados.get("posicao_camera", [0.0, 0.0]))
    raio_chunks = max(1, int(dados.get("raio_chunks", 4)))
    raio = float((raio_chunks + 2) * BANCO_DADOS.chunk_tamanho_unidade())
    modo = str(dados.get("modo", "pacotes")).strip().lower()
    ultimo_tick_recebido = int(dados.get("ultimo_tick_recebido", 0) or 0)

    TIQUE_SERVIDOR.ativar_por_usuario(client_id)
    meta_cerebro = CEREBRO.processar_ativacao(client_id, posicao_camera)

    with _LOCK:
        _CLIENTS_CONHECIDOS.add(client_id)
        state = _obter_state_client(client_id)
        vistos: Set[int] = state["objetos_vistos"]

        if modo == "chunks":
            chunks = [{"pos": [chunk[0], chunk[1]], "grid": BANCO_DADOS.chunk_em_grade(chunk), "chunk_blocos": BANCO_DADOS.chunk_tamanho_unidade()} for chunk in _chunks_no_raio(posicao_camera, raio_chunks)]
            return json.dumps({"status": "ok", "client_id": client_id, "chunks": chunks, "meta": {"total_chunks": len(chunks), "chunk_blocos": int(BANCO_DADOS.chunk_tamanho_unidade())}}, ensure_ascii=False)

        pacotes = _filtrar_pacotes_por_camera(PACOTES_TICK.obter_pacotes_desde(ultimo_tick_recebido, limite=90), posicao_camera, raio)
        diffs_base_players = _coletar_diffs_base_players(client_id, posicao_camera, raio)
        diffs_vis = _coletar_diffs_visibilidade(posicao_camera, raio, vistos)
        diffs_extra = list(diffs_base_players) + list(diffs_vis)
        if diffs_extra:
            if pacotes:
                pacote_vis = pacotes[-1]
                diffs_base = pacote_vis.get("diffs", []) if isinstance(pacote_vis.get("diffs"), list) else []
                pacote_vis["diffs"] = list(diffs_base) + list(diffs_extra)
            else:
                # Sem pacote real no intervalo: envia pacote sintético de bootstrap/visibilidade.
                pacotes.append({"tick": 0, "diffs": diffs_extra, "sintetico": True})

        return json.dumps({"status": "ok", "mensagem": "Pacotes coletados", "client_id": client_id, "pacotes": pacotes, "tick_atual_servidor": PACOTES_TICK.tick_atual(), "meta": {"players_ativos": int(meta_cerebro.get("players_ativos", 0)), "chunks_visiveis": int(meta_cerebro.get("chunks_visiveis", 0))}}, ensure_ascii=False)


def desconectar_client(client_id: str) -> None:
    with _LOCK:
        _CLIENTS_CONHECIDOS.discard(client_id)
        _CLIENT_STATE.pop(client_id, None)
    CEREBRO.remover_player(client_id)


def resetar_estado_clientes() -> None:
    with _LOCK:
        _CLIENTS_CONHECIDOS.clear()
        _CLIENT_STATE.clear()
