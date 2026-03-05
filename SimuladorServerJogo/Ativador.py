"""Rota Ativador: entrega chunks e diffs ainda não coletados por client."""

from __future__ import annotations

import json
import math
import threading
import time
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.BancoDados import BANCO_DADOS

Vector2 = Tuple[float, float]

_DIFF_LOCK = threading.Lock()
_DIFF_SEQ = 0
_DIFF_LOG: List[Dict[str, object]] = []
_CLIENTS_CONHECIDOS: Set[str] = set()
_CLIENT_STATE: Dict[str, Dict[str, object]] = {}


def _next_seq() -> int:
    global _DIFF_SEQ
    _DIFF_SEQ += 1
    return _DIFF_SEQ


def registrar_diff(tipo: str, payload: Dict[str, object], escopo: Dict[str, object], objeto_id=None) -> Dict[str, object]:
    with _DIFF_LOCK:
        diff = {
            "seq": _next_seq(),
            "timestamp": time.time(),
            "tipo": tipo,
            "objeto_id": objeto_id,
            "payload": payload,
            "escopo": escopo,
            "coletado_por": set(),
        }
        _DIFF_LOG.append(diff)
        return diff


def _normalizar_posicao(valor) -> Vector2:
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return (0.0, 0.0)
    return (float(valor[0]), float(valor[1]))


def _diff_relevante(diff: Dict[str, object], posicao_camera: Vector2, raio: float) -> bool:
    escopo = diff.get("escopo") or {}
    centro = escopo.get("centro")
    if not centro:
        return True
    cx, cy = _normalizar_posicao(centro)
    return math.hypot(cx - posicao_camera[0], cy - posicao_camera[1]) <= raio


def _prune_diff_log() -> None:
    if len(_DIFF_LOG) < 200:
        return
    ativos = set(_CLIENTS_CONHECIDOS)
    if not ativos:
        del _DIFF_LOG[:-120]
        return
    _DIFF_LOG[:] = [d for d in _DIFF_LOG if not ativos.issubset(d["coletado_por"]) or (time.time() - d["timestamp"] < 10.0)]


def _obter_state_client(client_id: str) -> Dict[str, object]:
    if client_id not in _CLIENT_STATE:
        _CLIENT_STATE[client_id] = {"objetos_vistos": set(), "chunks_vistos": set()}
    return _CLIENT_STATE[client_id]


def processar_ativador_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps({"status": "erro", "mensagem": "JSON inválido"}, ensure_ascii=False)

    dados = pacote.get("dados", {})
    client_id = str(dados.get("client_id", "")).strip()
    posicao_camera = _normalizar_posicao(dados.get("posicao_camera", [0.0, 0.0]))
    raio_chunks = max(1, int(dados.get("raio_chunks", 5)))
    raio = float(raio_chunks * BANCO_DADOS.chunk_tamanho_unidade())

    if not client_id:
        return json.dumps({"status": "erro", "mensagem": "client_id obrigatório"}, ensure_ascii=False)


    with _DIFF_LOCK:
        _CLIENTS_CONHECIDOS.add(client_id)
        state = _obter_state_client(client_id)
        vistos: Set[int] = state["objetos_vistos"]
        chunks_vistos: Set[Tuple[int, int]] = state["chunks_vistos"]

        objetos_proximos = BANCO_DADOS.buscar_proximos(posicao_camera, raio)
        diffs: List[Dict[str, object]] = []

        for obj in objetos_proximos:
            if obj.Id not in vistos:
                spawn = {
                    "seq": _next_seq(),
                    "timestamp": time.time(),
                    "tipo": "spawn",
                    "objeto_id": obj.Id,
                    "payload": obj.serializar(),
                    "escopo": {"centro": list(obj.posicao), "raio": raio},
                }
                diffs.append(spawn)
                vistos.add(obj.Id)

        for diff in _DIFF_LOG:
            if client_id in diff["coletado_por"]:
                continue
            if not _diff_relevante(diff, posicao_camera, raio):
                continue
            diffs.append(
                {
                    "seq": diff["seq"],
                    "timestamp": diff["timestamp"],
                    "tipo": diff["tipo"],
                    "objeto_id": diff.get("objeto_id"),
                    "payload": diff.get("payload", {}),
                    "escopo": diff.get("escopo", {}),
                }
            )
            diff["coletado_por"].add(client_id)

        chunks = []
        for chunk in BANCO_DADOS.chunks_proximos(posicao_camera, raio_chunks=raio_chunks):
            if chunk in chunks_vistos:
                continue
            dados_chunk = {"pos": [chunk[0], chunk[1]], "grid": BANCO_DADOS.chunk_em_grade(chunk), "chunk_blocos": 32}
            chunks.append(dados_chunk)
            diffs.append(
                {
                    "seq": _next_seq(),
                    "timestamp": time.time(),
                    "tipo": "chunk",
                    "objeto_id": None,
                    "payload": dados_chunk,
                    "escopo": {"centro": [posicao_camera[0], posicao_camera[1]], "raio": raio},
                }
            )
            chunks_vistos.add(chunk)

        _prune_diff_log()

    resposta = {
        "status": "ok",
        "mensagem": "Ativador processado",
        "client_id": client_id,
        "chunks": chunks,
        "diffs": sorted(diffs, key=lambda d: d["seq"]),
        "meta": {"total_diffs": len(diffs), "total_chunks": len(chunks)},
    }
    return json.dumps(resposta, ensure_ascii=False)


def desconectar_client(client_id: str) -> None:
    with _DIFF_LOCK:
        _CLIENTS_CONHECIDOS.discard(client_id)
        _CLIENT_STATE.pop(client_id, None)
