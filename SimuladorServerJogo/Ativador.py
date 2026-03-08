"""Rota Ativador: entrega chunks e diffs por canal separado + ativa cérebro do servidor."""

from __future__ import annotations

import json
import math
import threading
import time
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Cerebro import CEREBRO

Vector2 = Tuple[float, float]

_DIFF_LOCK = threading.Lock()
_DIFF_SEQ = 0
_DIFF_LOG: List[Dict[str, object]] = []
_CLIENTS_CONHECIDOS: Set[str] = set()
_CLIENT_STATE: Dict[str, Dict[str, object]] = {}
_CATEGORIAS_VALIDAS = {"rapida", "lenta"}


def _next_seq() -> int:
    global _DIFF_SEQ
    _DIFF_SEQ += 1
    return _DIFF_SEQ


def registrar_diff(tipo: str, payload: Dict[str, object], escopo: Dict[str, object], objeto_id=None, categoria: str = "rapida") -> Dict[str, object]:
    """Registra diff no log central com categoria de sincronização.

    Categoria rápida = visual/dinâmico; categoria lenta = dados persistentes.
    """
    cat = str(categoria or "rapida").strip().lower()
    if cat not in _CATEGORIAS_VALIDAS:
        cat = "rapida"
    with _DIFF_LOCK:
        diff = {
            "seq": _next_seq(),
            "timestamp": time.time(),
            "tipo": tipo,
            "objeto_id": objeto_id,
            "payload": payload,
            "escopo": escopo,
            "categoria": cat,
            "coletado_por": {"rapida": set(), "lenta": set()},
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

    def _coletado_para_categoria_da_diff(diff) -> bool:
        categoria = str(diff.get("categoria", "rapida")).strip().lower()
        if categoria not in _CATEGORIAS_VALIDAS:
            categoria = "rapida"
        coletado = diff.get("coletado_por") or {}
        coletado_categoria = set(coletado.get(categoria, set()))
        return ativos.issubset(coletado_categoria)

    _DIFF_LOG[:] = [d for d in _DIFF_LOG if not _coletado_para_categoria_da_diff(d) or (time.time() - d["timestamp"] < 10.0)]


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


def _serializar_diff_registrada(diff: Dict[str, object]) -> Dict[str, object]:
    return {
        "seq": diff["seq"],
        "timestamp": diff["timestamp"],
        "tipo": diff["tipo"],
        "objeto_id": diff.get("objeto_id"),
        "payload": diff.get("payload", {}),
        "escopo": diff.get("escopo", {}),
        "categoria": diff.get("categoria", "rapida"),
    }


def _resposta_base(client_id: str, meta_cerebro: Dict[str, object], raio_chunks: int, diffs: List[Dict[str, object]] | None = None, chunks: List[Dict[str, object]] | None = None):
    largura_blocos, altura_blocos = BANCO_DADOS.limites_mundo()
    return {
        "status": "ok",
        "mensagem": "Ativador processado",
        "client_id": client_id,
        "chunks": chunks or [],
        "diffs": sorted((diffs or []), key=lambda d: d["seq"]) if diffs else [],
        "meta": {
            "total_diffs": len(diffs or []),
            "total_chunks": len(chunks or []),
            "largura_blocos": int(largura_blocos),
            "altura_blocos": int(altura_blocos),
            "chunk_blocos": int(BANCO_DADOS.chunk_tamanho_unidade()),
            "raio_chunks_ativo": int(raio_chunks),
            "anel_render_chunks": int(meta_cerebro.get("anel_render_chunks", 7)),
            "anel_simulado_chunks": int(meta_cerebro.get("anel_simulado_chunks", 13)),
            "cerebro": meta_cerebro,
        },
    }


def processar_ativador_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps({"status": "erro", "mensagem": "JSON inválido"}, ensure_ascii=False)

    dados = pacote.get("dados", {})
    client_id = str(dados.get("client_id", "")).strip()
    posicao_camera = _normalizar_posicao(dados.get("posicao_camera", [0.0, 0.0]))
    raio_chunks = max(1, int(dados.get("raio_chunks", 4)))
    raio = float((raio_chunks + 2) * BANCO_DADOS.chunk_tamanho_unidade())
    modo = str(dados.get("modo", "estado")).strip().lower()
    categoria = str(dados.get("categoria", "rapida")).strip().lower()
    if categoria not in _CATEGORIAS_VALIDAS:
        categoria = "rapida"

    if not client_id:
        return json.dumps({"status": "erro", "mensagem": "client_id obrigatório"}, ensure_ascii=False)

    meta_cerebro = CEREBRO.processar_ativacao(client_id, posicao_camera)

    with _DIFF_LOCK:
        _CLIENTS_CONHECIDOS.add(client_id)
        state = _obter_state_client(client_id)
        vistos: Set[int] = state["objetos_vistos"]

        # Modo exclusivo de chunks: sempre retorna o anel completo atual.
        if modo == "chunks":
            chunks = []
            for chunk in _chunks_no_raio(posicao_camera, raio_chunks):
                chunks.append({
                    "pos": [chunk[0], chunk[1]],
                    "grid": BANCO_DADOS.chunk_em_grade(chunk),
                    "chunk_blocos": BANCO_DADOS.chunk_tamanho_unidade(),
                })
            resposta = _resposta_base(client_id, meta_cerebro, raio_chunks, diffs=[], chunks=chunks)
            return json.dumps(resposta, ensure_ascii=False)

        # Modo exclusivo de diffs: separa por categoria rápida/lenta.
        diffs: List[Dict[str, object]] = []
        if modo in ("diffs", "estado"):
            if modo == "estado":
                objetos_proximos = BANCO_DADOS.buscar_proximos(posicao_camera, raio)
                for obj in objetos_proximos:
                    if obj.Id not in vistos:
                        spawn = {
                            "seq": _next_seq(),
                            "timestamp": time.time(),
                            "tipo": "spawn",
                            "objeto_id": obj.Id,
                            "payload": obj.serializar(),
                            "escopo": {"centro": list(obj.posicao), "raio": raio},
                            "categoria": "rapida",
                        }
                        diffs.append(spawn)
                        vistos.add(obj.Id)

            for diff in _DIFF_LOG:
                cat_diff = str(diff.get("categoria", "rapida")).strip().lower()
                if cat_diff != categoria:
                    continue
                coletado = diff.get("coletado_por") or {}
                coletado_categoria = coletado.get(categoria, set())
                if client_id in coletado_categoria:
                    continue
                if not _diff_relevante(diff, posicao_camera, raio):
                    continue
                diffs.append(_serializar_diff_registrada(diff))
                coletado_categoria.add(client_id)
                coletado[categoria] = coletado_categoria
                diff["coletado_por"] = coletado

            _prune_diff_log()

            resposta = _resposta_base(client_id, meta_cerebro, raio_chunks, diffs=diffs, chunks=[])
            return json.dumps(resposta, ensure_ascii=False)

    return json.dumps({"status": "erro", "mensagem": "modo inválido"}, ensure_ascii=False)


def desconectar_client(client_id: str) -> None:
    with _DIFF_LOCK:
        _CLIENTS_CONHECIDOS.discard(client_id)
        _CLIENT_STATE.pop(client_id, None)
    CEREBRO.remover_player(client_id)


def resetar_estado_clientes() -> None:
    with _DIFF_LOCK:
        _CLIENTS_CONHECIDOS.clear()
        _CLIENT_STATE.clear()
        _DIFF_LOG.clear()
