"""Rota Ativador: entrega chunks e pacotes de tick para sincronização."""

from __future__ import annotations

import json
import math
import threading
import time
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.Cerebros.CerebroCentral import CEREBRO
from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Controle.TiqueServidor import TIQUE_SERVIDOR
from SimuladorServerJogo.Controle.Cerebros.CerebroEstadios import CEREBRO_ESTADIOS

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]

_LOCK = threading.Lock()
_DIFF_SEQ = 0
_CLIENTS_CONHECIDOS: Set[str] = set()
_CLIENT_STATE: Dict[str, Dict[str, object]] = {}


def _next_seq() -> int:
    global _DIFF_SEQ
    _DIFF_SEQ += 1
    return _DIFF_SEQ


def diff_seq_atual() -> int:
    return int(_DIFF_SEQ)


def registrar_diff(tipo: str, payload: Dict[str, object], escopo: Dict[str, object], objeto_id=None, autor: str = "server", categoria: str | None = None, extras: Dict[str, object] | None = None) -> Dict[str, object]:
    diff = {
        "seq": _next_seq(),
        "timestamp": time.time(),
        "tipo": str(tipo or ""),
        "objeto_id": objeto_id,
        "autor": str(autor or "server"),
        "payload": dict(payload or {}),
        "escopo": dict(escopo or {}),
    }
    if categoria is not None:
        diff["categoria"] = str(categoria)
    if isinstance(extras, dict):
        diff.update(extras)
    PACOTES_TICK.registrar_diff_pendente(diff)
    return diff


def _normalizar_posicao(valor) -> Vector2:
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return (0.0, 0.0)
    return (float(valor[0]), float(valor[1]))


def _obter_state_client(client_id: str) -> Dict[str, object]:
    if client_id not in _CLIENT_STATE:
        _CLIENT_STATE[client_id] = {"objetos_vistos": set(), "dimensao": "Mundo", "estadios_pre_enviados": False}
    return _CLIENT_STATE[client_id]


def _eh_dimensao_estadio(dimensao: str) -> bool:
    return str(dimensao or "").strip().startswith("Estadio")


def _chunks_carregados_cliente(posicao_camera: Vector2, dimensao: str = "Mundo") -> Set[Chunk]:
    raio = max(0, int(CEREBRO._i("raio_chunks_carregados", 4)))
    dimensao_norm = str(dimensao or "Mundo")
    if _eh_dimensao_estadio(dimensao_norm):
        centro = (int(posicao_camera[0] // BANCO_DADOS.chunk_tamanho_unidade()), int(posicao_camera[1] // BANCO_DADOS.chunk_tamanho_unidade()))
        return set(CEREBRO_ESTADIOS.chunks_proximos(dimensao_norm, centro, raio))
    centro = BANCO_DADOS.chunk_da_posicao(posicao_camera)
    chunks: Set[Chunk] = set()
    for dx in range(-raio, raio + 1):
        for dy in range(-raio, raio + 1):
            chunks.add(BANCO_DADOS.normalizar_chunk((centro[0] + dx, centro[1] + dy)))
    return chunks


def _raio_visao_por_regras() -> float:
    chunk_u = float(BANCO_DADOS.chunk_tamanho_unidade())
    raio_carregado = max(0, int(CEREBRO._i("raio_chunks_carregados", 4)))
    return float((raio_carregado + 1) * chunk_u)


def _grid_neutra_estadio() -> list[list[int]]:
    """Grade neutra para estádios: mantém referência espacial sem tiles de terreno."""
    lado = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
    return [[-1 for _ in range(lado)] for _ in range(lado)]


def _objeto_em_chunks(obj, chunks: Set[Chunk], dimensao: str = "Mundo") -> bool:
    if not chunks:
        return False
    if _dimensao_objeto(obj) != str(dimensao or "Mundo"):
        return False
    return BANCO_DADOS.chunk_da_posicao(getattr(obj, "posicao", (0.0, 0.0))) in chunks



def _dimensao_objeto(obj) -> str:
    estado = getattr(obj, "estado_extra", {}) if obj is not None and isinstance(getattr(obj, "estado_extra", {}), dict) else {}
    tipo = str(getattr(obj, "tipo_classe", "") or "")
    if tipo == "entidade_estadio":
        return "Mundo"
    return str(estado.get("dimensao") or "Mundo")


def _diff_na_dimensao(diff: Dict[str, object], dimensao: str) -> bool:
    if not isinstance(diff, dict):
        return False
    payload = diff.get("payload") if isinstance(diff.get("payload"), dict) else {}
    estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
    tipo = str(payload.get("tipo") or "")
    if tipo == "entidade_estadio":
        dim_payload = "Mundo"
    else:
        dim_payload = str(payload.get("dimensao") or estado.get("dimensao") or "")
    if dim_payload:
        return dim_payload == str(dimensao or "Mundo")
    oid = diff.get("objeto_id")
    if oid is not None:
        obj = BANCO_DADOS.obter_objeto(int(oid))
        if obj is not None:
            return _dimensao_objeto(obj) == str(dimensao or "Mundo")
    return True

def _diff_relevante_para_camera(diff, posicao_camera: Vector2, raio_visao: float, chunks_carregados: Set[Chunk] | None = None) -> bool:
    if not isinstance(diff, dict):
        return False
    escopo = diff.get("escopo", {}) if isinstance(diff.get("escopo"), dict) else {}
    payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}
    if str(payload.get("tipo") or "").strip().lower() == "entidade_estadio":
        return True
    centro = escopo.get("centro") if isinstance(escopo.get("centro"), (list, tuple)) else None
    if centro is None:
        return True
    try:
        cx, cy = float(centro[0]), float(centro[1])
    except (TypeError, ValueError, IndexError):
        return True
    if chunks_carregados:
        if BANCO_DADOS.chunk_da_posicao((cx, cy)) not in chunks_carregados:
            return False
    raio_diff = float(escopo.get("raio", 0.0) or 0.0)
    return math.hypot(cx - posicao_camera[0], cy - posicao_camera[1]) <= (raio_visao + max(0.0, raio_diff))


def _filtrar_pacotes_por_camera(pacotes, posicao_camera: Vector2, raio_visao: float, chunks_carregados: Set[Chunk], client_id: str = "", dimensao: str = "Mundo"):
    saida = []
    client_id_norm = str(client_id or "").strip().lower()
    for pacote in pacotes if isinstance(pacotes, list) else []:
        if not isinstance(pacote, dict):
            continue
        diffs = pacote.get("diffs", []) if isinstance(pacote.get("diffs"), list) else []
        diffs_visiveis = []
        for d in diffs:
            alvo = str(d.get("cliente_alvo", "") or "").strip().lower()
            if client_id_norm and alvo and alvo == client_id_norm:
                diffs_visiveis.append(d)
                continue
            if not _diff_na_dimensao(d, dimensao):
                continue
            if not _diff_relevante_para_camera(d, posicao_camera, raio_visao, chunks_carregados):
                continue
            diffs_visiveis.append(d)
        if not diffs_visiveis:
            continue
        novo = dict(pacote)
        novo["diffs"] = diffs_visiveis
        saida.append(novo)
    return saida


def _coletar_diffs_visibilidade(posicao_camera: Vector2, chunks_carregados: Set[Chunk], vistos: Set[int], client_id: str = "", dimensao: str = "Mundo") -> List[Dict[str, object]]:
    raio = _raio_visao_por_regras()
    client_id_norm = str(client_id or "").strip().lower()
    objetos_proximos = [obj for obj in BANCO_DADOS.buscar_proximos(posicao_camera, raio) if _objeto_em_chunks(obj, chunks_carregados, dimensao=dimensao)]
    ids_proximos = {int(obj.Id) for obj in objetos_proximos}
    diffs: List[Dict[str, object]] = []
    agora = time.time()
    for obj in objetos_proximos:
        dono = str(BANCO_DADOS.usuario_por_objeto_id(int(obj.Id)) or "").strip().lower()
        if client_id_norm and dono and dono == client_id_norm:
            continue
        if int(obj.Id) in vistos:
            continue
        vistos.add(int(obj.Id))
        categoria = str(getattr(obj, "estado_extra", {}).get("subtipo", "outro") or "outro")
        diffs.append({"seq": _next_seq(), "timestamp": agora, "tipo": "spawn", "objeto_id": obj.Id, "autor": "server", "payload": obj.serializar(), "escopo": {"centro": list(obj.posicao), "raio": raio}, "categoria": categoria})
    for oid in [oid for oid in list(vistos) if oid not in ids_proximos]:
        obj = BANCO_DADOS.obter_objeto(int(oid))
        if obj is not None and str(getattr(obj, "tipo_classe", "") or "") == "entidade_estadio":
            continue
        vistos.discard(int(oid))
        diffs.append({"seq": _next_seq(), "timestamp": agora, "tipo": "despawn", "objeto_id": int(oid), "autor": "server", "payload": {}, "escopo": {"centro": list(posicao_camera), "raio": raio}, "categoria": "outro"})
    return diffs


def _coletar_preload_estadios(vistos: Set[int]) -> List[Dict[str, object]]:
    agora = time.time()
    saida: List[Dict[str, object]] = []
    for obj in BANCO_DADOS.listar_objetos():
        if str(getattr(obj, "tipo_classe", "") or "") != "entidade_estadio":
            continue
        if int(obj.Id) in vistos:
            continue
        vistos.add(int(obj.Id))
        saida.append({"seq": _next_seq(), "timestamp": agora, "tipo": "spawn", "objeto_id": obj.Id, "autor": "server", "payload": obj.serializar(), "escopo": {"centro": list(obj.posicao), "raio": 999999.0}, "categoria": "estadio"})
    return saida



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
    modo = str(dados.get("modo", "pacotes")).strip().lower()
    ultimo_tick_recebido = int(dados.get("ultimo_tick_recebido", 0) or 0)

    meta_cerebro = CEREBRO.processar_ativacao(client_id, posicao_camera)
    TIQUE_SERVIDOR.ativar_por_usuario(client_id)
    TIQUE_SERVIDOR.bombear_ate_agora()
    state_cli = _obter_state_client(client_id)
    obj_id = int(BANCO_DADOS.objeto_id_por_usuario(client_id) or 0)
    obj_player = BANCO_DADOS.obter_objeto(obj_id) if obj_id > 0 else None
    dimensao = str(getattr(obj_player, "estado_extra", {}).get("dimensao", state_cli.get("dimensao", "Mundo")) if obj_player is not None else state_cli.get("dimensao", "Mundo"))
    chunks_carregados = _chunks_carregados_cliente(posicao_camera, dimensao=dimensao)
    chunks_servidor_carregados, chunks_servidor_simulados = CEREBRO._calcular_chunks_carregados()
    raio = _raio_visao_por_regras()

    with _LOCK:
        _CLIENTS_CONHECIDOS.add(client_id)
        state = _obter_state_client(client_id)
        state["dimensao"] = dimensao
        vistos: Set[int] = state["objetos_vistos"]

        if modo == "chunks":
            chunks = []
            for chunk in sorted(chunks_carregados):
                grid = _grid_neutra_estadio() if _eh_dimensao_estadio(dimensao) else BANCO_DADOS.chunk_em_grade(chunk)
                chunks.append({"pos": [chunk[0], chunk[1]], "grid": grid, "chunk_blocos": BANCO_DADOS.chunk_tamanho_unidade()})
            dim_largura = int(CEREBRO_ESTADIOS.chunks_largura * BANCO_DADOS.chunk_tamanho_unidade()) if _eh_dimensao_estadio(dimensao) else int(BANCO_DADOS.limites_mundo()[0])
            dim_altura = int(CEREBRO_ESTADIOS.chunks_altura * BANCO_DADOS.chunk_tamanho_unidade()) if _eh_dimensao_estadio(dimensao) else int(BANCO_DADOS.limites_mundo()[1])
            return json.dumps({"status": "ok", "client_id": client_id, "chunks": chunks, "meta": {"total_chunks": len(chunks), "chunk_blocos": int(BANCO_DADOS.chunk_tamanho_unidade()), "dimensao": dimensao, "largura_blocos": int(dim_largura), "altura_blocos": int(dim_altura)}}, ensure_ascii=False)

        pacotes = _filtrar_pacotes_por_camera(PACOTES_TICK.obter_pacotes_desde(ultimo_tick_recebido, limite=90), posicao_camera, raio, chunks_carregados, client_id=client_id, dimensao=dimensao)
        diffs_extra = _coletar_diffs_visibilidade(posicao_camera, chunks_carregados, vistos, client_id=client_id, dimensao=dimensao)
        if not bool(state.get("estadios_pre_enviados", False)):
            diffs_extra.extend(_coletar_preload_estadios(vistos))
            state["estadios_pre_enviados"] = True
        if diffs_extra:
            if pacotes:
                pacote_vis = pacotes[-1]
                diffs_atuais = pacote_vis.get("diffs", []) if isinstance(pacote_vis.get("diffs"), list) else []
                pacote_vis["diffs"] = list(diffs_atuais) + list(diffs_extra)
            else:
                pacotes.append({"tick": 0, "diffs": diffs_extra, "sintetico": True})

        return json.dumps({
            "status": "ok",
            "mensagem": "Pacotes coletados",
            "client_id": client_id,
            "pacotes": pacotes,
            "tick_atual_servidor": PACOTES_TICK.tick_atual(),
            "meta": {
                "players_ativos": int(meta_cerebro.get("players_ativos", 0)),
                "chunks_carregados": len(chunks_servidor_carregados),
                "chunks_simulados": len(chunks_servidor_simulados),
                "tempo_mundo": CEREBRO.obter_snapshot_tempo(),
            },
        }, ensure_ascii=False)


def desconectar_client(client_id: str) -> None:
    with _LOCK:
        _CLIENTS_CONHECIDOS.discard(client_id)
        _CLIENT_STATE.pop(client_id, None)
    CEREBRO.remover_player(client_id)


def resetar_estado_clientes() -> None:
    with _LOCK:
        _CLIENTS_CONHECIDOS.clear()
        _CLIENT_STATE.clear()
