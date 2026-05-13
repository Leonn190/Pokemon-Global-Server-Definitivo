"""Rota Ativador: entrega chunks e pacotes de tick para sincronização."""

from __future__ import annotations

import json
import math
import threading
import time
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.Cerebros.CerebroCentral import CEREBRO
from SimuladorServerJogo.Mundo.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Mundo.TiqueServidor import TIQUE_SERVIDOR
from SimuladorServerJogo.Mundo.Cerebros.CerebroEstadios import CEREBRO_ESTADIOS
from SimuladorServerJogo.Mundo.DungeonGeometria import eh_dimensao_dungeon
from SimuladorServerJogo.Mundo.Dungeons.EstadoDungeon import criar_estado_entrada
from SimuladorServerJogo.Gerais.EstadoServidor import obter_exploracao_chunks, registrar_chunks_explorados

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]

_LOCK = threading.Lock()
_DIFF_SEQ = 0
_CLIENTS_CONHECIDOS: Set[str] = set()
_CLIENT_STATE: Dict[str, Dict[str, object]] = {}




def _cor_regiao_fallback(regiao_id: int) -> list[int]:
    base = int(regiao_id or 0) * 1103515245 + 12345
    r = 60 + ((base >> 16) & 0x7F)
    g = 60 + ((base >> 9) & 0x7F)
    b = 60 + ((base >> 2) & 0x7F)
    return [int(r), int(g), int(b)]


def _meta_mundo_para_mapa() -> dict:
    meta = BANCO_DADOS._estado_mundo.get("meta", {}) if isinstance(getattr(BANCO_DADOS, "_estado_mundo", {}), dict) else {}
    largura, altura = BANCO_DADOS.limites_mundo()
    chunk = int(BANCO_DADOS.chunk_tamanho_unidade())
    seed = int(meta.get("seed", 0) or 0)
    chunks_x = int(meta.get("chunks_x", BANCO_DADOS.total_chunks()[0]))
    chunks_y = int(meta.get("chunks_y", BANCO_DADOS.total_chunks()[1]))
    world_fingerprint = f"{seed}:{int(largura)}:{int(altura)}:{chunks_x}:{chunks_y}:{int(chunk)}"
    cores = {
        "0": [18, 74, 156], "1": [95, 176, 232], "2": [110, 186, 72], "3": [48, 126, 54],
        "4": [228, 214, 149], "5": [218, 188, 100], "6": [235, 242, 248], "7": [138, 72, 192],
        "8": [112, 74, 44], "9": [132, 132, 132],
    }
    return {
        "largura_blocos": int(largura),
        "altura_blocos": int(altura),
        "chunk_blocos": int(chunk),
        "chunks_x": chunks_x,
        "chunks_y": chunks_y,
        "seed": seed,
        "world_fingerprint": world_fingerprint,
        "atlas_chunks_lado": 100,
        "atlas_px": 1000,
        "cores_blocos": cores,
        "rotas": list(meta.get("rotas", []) if isinstance(meta.get("rotas"), list) else []),
    }


def _poi_mapa() -> tuple[list, list, list, list]:
    meta = BANCO_DADOS._estado_mundo.get("meta", {}) if isinstance(getattr(BANCO_DADOS, "_estado_mundo", {}), dict) else {}
    vilas = list(meta.get("vilas", []) if isinstance(meta.get("vilas"), list) else [])
    estadios = list(meta.get("estadios", []) if isinstance(meta.get("estadios"), list) else [])
    rotas = list(meta.get("rotas", []) if isinstance(meta.get("rotas"), list) else [])
    regioes_raw = list(meta.get("regioes", []) if isinstance(meta.get("regioes"), list) else [])
    regioes = []
    prox_id = 1
    for reg in regioes_raw:
        if not isinstance(reg, dict):
            continue
        item = dict(reg)
        rid = item.get("id")
        if rid in (None, ""):
            rid = prox_id
            prox_id += 1
        item["id"] = int(rid)
        item["nome"] = str(item.get("nome") or f"Região {int(item['id'])}")
        centro = item.get("centro")
        if not (isinstance(centro, (list, tuple)) and len(centro) == 2):
            centro = [0, 0]
        item["centro"] = [float(centro[0]), float(centro[1])]
        cor = item.get("cor") if isinstance(item.get("cor"), list) else item.get("cor_rgb")
        if not (isinstance(cor, list) and len(cor) == 3):
            item["cor"] = _cor_regiao_fallback(int(item.get("id", 0) or 0))
        regioes.append(item)
    return vilas, estadios, regioes, rotas


def _resolver_posicao_mundo_referencia(obj_player, posicao_camera: Vector2) -> Vector2:
    estado = getattr(obj_player, "estado_extra", {}) if obj_player is not None and isinstance(getattr(obj_player, "estado_extra", {}), dict) else {}
    dimensao = str(estado.get("dimensao") or "Mundo")
    if dimensao == "Mundo" and obj_player is not None:
        pos = getattr(obj_player, "posicao", None)
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return (float(pos[0]), float(pos[1]))
        return (float(posicao_camera[0]), float(posicao_camera[1]))
    estadio_id = int(estado.get("estadio_atual_id", 0) or 0)
    if estadio_id > 0:
        estadio = BANCO_DADOS.obter_objeto(estadio_id)
        if estadio is not None:
            return (float(getattr(estadio, "posicao", [0.0, 0.0])[0]), float(getattr(estadio, "posicao", [0.0, 0.0])[1]))
    ultima = estado.get("ultima_pos_mundo")
    if isinstance(ultima, (list, tuple)) and len(ultima) == 2:
        return (float(ultima[0]), float(ultima[1]))
    pos_dim = estado.get("posicoes_por_dimensao") if isinstance(estado.get("posicoes_por_dimensao"), dict) else {}
    pos_mundo = pos_dim.get("Mundo")
    if isinstance(pos_mundo, (list, tuple)) and len(pos_mundo) == 2:
        return (float(pos_mundo[0]), float(pos_mundo[1]))
    return (float(posicao_camera[0]), float(posicao_camera[1]))


def _objetos_no_chunk_mapa(chunk: Chunk) -> list[dict]:
    saida: list[dict] = []
    for obj in BANCO_DADOS.listar_objetos():
        try:
            if BANCO_DADOS.chunk_da_posicao(getattr(obj, "posicao", (0.0, 0.0))) != chunk:
                continue
        except Exception:
            continue
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        tipo_classe = str(getattr(obj, "tipo_classe", "") or "")
        subtipo = str(estado.get("subtipo") or "")
        if tipo_classe in {"ator", "entidade_estadio"}:
            continue
        if str(estado.get("dimensao") or "Mundo") != "Mundo":
            continue
        pos = getattr(obj, "posicao", (0.0, 0.0))
        saida.append({
            "pos": [float(pos[0]), float(pos[1])],
            "tipo": tipo_classe,
            "subtipo": subtipo,
            "categoria": str(estado.get("categoria") or subtipo or tipo_classe),
        })
    return saida


def _atlas_do_conjunto(chunks: set[Chunk]) -> list[dict]:
    grupos: Dict[Tuple[int, int], list[dict]] = {}
    for chunk in sorted(chunks):
        ax = int(chunk[0]) // 100
        ay = int(chunk[1]) // 100
        grupos.setdefault((ax, ay), []).append({
            "pos": [int(chunk[0]), int(chunk[1])],
            "grid": BANCO_DADOS.chunk_em_grade(chunk),
            "objetos": _objetos_no_chunk_mapa(chunk),
        })
    out = []
    for (ax, ay), lista in grupos.items():
        if not lista:
            continue
        out.append({"atlas_x": ax, "atlas_y": ay, "chunks": lista})
    return out


def _chunks_explorados_para_set(explorados: dict) -> set[Chunk]:
    mundo = explorados.get("Mundo") if isinstance(explorados.get("Mundo"), dict) else {}
    out: set[Chunk] = set()
    for sx, ys in mundo.items():
        try:
            x = int(sx)
        except Exception:
            continue
        if isinstance(ys, list):
            for y in ys:
                try:
                    out.add((x, int(y)))
                except Exception:
                    continue
    return out


def _atlas_conhecidos(conhecidos: dict | None) -> dict[tuple[int, int], set[Chunk]]:
    out: dict[tuple[int, int], set[Chunk]] = {}
    atual = str(_meta_mundo_para_mapa().get("world_fingerprint") or "")
    recebido = str(conhecidos.get("world_fingerprint") or "") if isinstance(conhecidos, dict) else ""
    if atual and recebido != atual:
        return out
    atlas_lista = conhecidos.get("atlas") if isinstance(conhecidos, dict) and isinstance(conhecidos.get("atlas"), list) else []
    for item in atlas_lista:
        if not isinstance(item, dict):
            continue
        pos = item.get("atlas")
        if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
            continue
        try:
            chave = (int(pos[0]), int(pos[1]))
        except Exception:
            continue
        chunks_out = out.setdefault(chave, set())
        chunks = item.get("chunks") if isinstance(item.get("chunks"), list) else []
        for ch in chunks:
            if not (isinstance(ch, (list, tuple)) and len(ch) == 2):
                continue
            try:
                chunks_out.add((int(ch[0]), int(ch[1])))
            except Exception:
                continue
    return out

def _serializar_resposta(payload: Dict[str, object], serializar: bool):
    if not serializar:
        return payload
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), check_circular=False)


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
        _CLIENT_STATE[client_id] = {"objetos_vistos": set(), "dimensao": "Mundo", "estadios_pre_enviados": False, "mapa_chunks_enviados": set()}
    return _CLIENT_STATE[client_id]


def _eh_dimensao_estadio(dimensao: str) -> bool:
    return str(dimensao or "").strip().startswith("Estadio")

def _eh_dimensao_dungeon(dimensao: str) -> bool:
    return eh_dimensao_dungeon(dimensao)


def _chunks_carregados_cliente(posicao_camera: Vector2, dimensao: str = "Mundo") -> Set[Chunk]:
    raio = max(0, int(CEREBRO._i("raio_chunks_carregados", 4)))
    dimensao_norm = str(dimensao or "Mundo")
    if _eh_dimensao_estadio(dimensao_norm):
        centro = (int(posicao_camera[0] // BANCO_DADOS.chunk_tamanho_unidade()), int(posicao_camera[1] // BANCO_DADOS.chunk_tamanho_unidade()))
        return set(CEREBRO_ESTADIOS.chunks_proximos(dimensao_norm, centro, raio))
    if _eh_dimensao_dungeon(dimensao_norm):
        centro = (int(posicao_camera[0] // BANCO_DADOS.chunk_tamanho_unidade()), int(posicao_camera[1] // BANCO_DADOS.chunk_tamanho_unidade()))
        return set(CEREBRO._cerebro_dungeons.chunks_proximos(dimensao_norm, centro, raio))
    centro = BANCO_DADOS.chunk_da_posicao(posicao_camera)
    chunks: Set[Chunk] = set()
    for dx in range(-raio, raio + 1):
        for dy in range(-raio, raio + 1):
            chunks.add(BANCO_DADOS.normalizar_chunk((centro[0] + dx, centro[1] + dy)))
    return chunks


def _bonus_raio_exploracao(obj_player) -> int:
    estado = getattr(obj_player, "estado_extra", {}) if obj_player is not None and isinstance(getattr(obj_player, "estado_extra", {}), dict) else {}
    perfil = estado.get("perfil") if isinstance(estado.get("perfil"), dict) else {}
    return max(0, int(perfil.get("bonus_raio_exploracao_chunks", perfil.get("BonusRaioExploracaoChunks", 0)) or 0))


def _expandir_chunks_exploracao(chunks: Set[Chunk], bonus_raio: int) -> Set[Chunk]:
    bonus = max(0, int(bonus_raio or 0))
    if bonus <= 0:
        return set(chunks)
    out = set(chunks)
    for cx, cy in set(chunks):
        for dx in range(-bonus, bonus + 1):
            for dy in range(-bonus, bonus + 1):
                out.add(BANCO_DADOS.normalizar_chunk((int(cx) + dx, int(cy) + dy)))
    return out


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


def _objeto_renderizavel(obj) -> bool:
    estado = getattr(obj, "estado_extra", {}) if obj is not None and isinstance(getattr(obj, "estado_extra", {}), dict) else {}
    if str(getattr(obj, "tipo_classe", "") or "") == "entidade_player" and bool(estado.get("morto", False)):
        return False
    return True


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
    objetos_proximos = [obj for obj in BANCO_DADOS.buscar_proximos(posicao_camera, raio, garantir_estruturas=True) if _objeto_renderizavel(obj) and _objeto_em_chunks(obj, chunks_carregados, dimensao=dimensao)]
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



def processar_ativador_json(requisicao_json: str | Dict[str, object]):
    serializar_resposta = not isinstance(requisicao_json, dict)
    if serializar_resposta:
        try:
            pacote = json.loads(requisicao_json)
        except json.JSONDecodeError:
            return _serializar_resposta({"status": "erro", "mensagem": "JSON inválido"}, serializar_resposta)
    else:
        pacote = requisicao_json

    dados = pacote.get("dados", {})
    client_id = str(dados.get("client_id", "")).strip()
    if not client_id:
        return _serializar_resposta({"status": "erro", "mensagem": "client_id obrigatório"}, serializar_resposta)

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
        mapa_chunks_enviados: Set[Chunk] = state.get("mapa_chunks_enviados", set()) if isinstance(state.get("mapa_chunks_enviados", set()), set) else set()

        if modo == "chunks":
            chunks = []
            layout_dungeon = None
            if _eh_dimensao_dungeon(dimensao):
                layout_dungeon = CEREBRO._cerebro_dungeons._layouts.get(dimensao)
                if layout_dungeon is None and obj_player is not None:
                    estado_dungeon = getattr(obj_player, "estado_extra", {}).get("estado_dungeon", {}) if isinstance(getattr(obj_player, "estado_extra", {}), dict) else {}
                    code = str(estado_dungeon.get("dungeon_code") or str(dimensao).removeprefix("Dungeon_")).strip()
                    if code:
                        layout_dungeon = CEREBRO._cerebro_dungeons.obter_ou_gerar(code, int(estado_dungeon.get("porta_idx", 1) or 1), int(estado_dungeon.get("pedra_id", 0) or 0))
                        if isinstance(layout_dungeon, dict) and ((not isinstance(estado_dungeon, dict)) or not estado_dungeon):
                            estado_player = getattr(obj_player, "estado_extra", {}) if isinstance(getattr(obj_player, "estado_extra", {}), dict) else {}
                            entrada = (layout_dungeon.get("entradas") or [{}])[0]
                            estado_player["estado_dungeon"] = criar_estado_entrada(obj_player, client_id, str(code), int(entrada.get("porta_idx", 1) or 1), int(entrada.get("pedra_id", 0) or 0), layout_dungeon, entrada, CEREBRO._cerebro_dungeons._regras)
                            BANCO_DADOS.atualizar_objeto(obj_player.Id, {"estado": estado_player})
            for chunk in sorted(chunks_carregados):
                if _eh_dimensao_estadio(dimensao):
                    grid = _grid_neutra_estadio()
                elif _eh_dimensao_dungeon(dimensao):
                    grid = CEREBRO._cerebro_dungeons.chunk_em_grade(dimensao, chunk)
                else:
                    grid = BANCO_DADOS.chunk_em_grade(chunk)
                chunks.append({"pos": [chunk[0], chunk[1]], "grid": grid, "chunk_blocos": BANCO_DADOS.chunk_tamanho_unidade()})
            if obj_player is not None:
                if _eh_dimensao_estadio(dimensao):
                    chunks_mundo = {BANCO_DADOS.normalizar_chunk(ch) for ch in _chunks_carregados_cliente(_resolver_posicao_mundo_referencia(obj_player, posicao_camera), dimensao="Mundo")}
                    chunks_mundo = _expandir_chunks_exploracao(chunks_mundo, _bonus_raio_exploracao(obj_player))
                    registrar_chunks_explorados(client_id, list(chunks_mundo), dimensao="Mundo")
            dim_largura = int(CEREBRO_ESTADIOS.chunks_largura * BANCO_DADOS.chunk_tamanho_unidade()) if _eh_dimensao_estadio(dimensao) else int(BANCO_DADOS.limites_mundo()[0])
            dim_altura = int(CEREBRO_ESTADIOS.chunks_altura * BANCO_DADOS.chunk_tamanho_unidade()) if _eh_dimensao_estadio(dimensao) else int(BANCO_DADOS.limites_mundo()[1])
            if _eh_dimensao_dungeon(dimensao) and isinstance(layout_dungeon, dict):
                bloco = int(layout_dungeon.get("tamanho_bloco_sala_tiles", 30) or 30)
                bloco_w = int(layout_dungeon.get("largura_bloco_sala_tiles", bloco) or bloco)
                bloco_h = int(layout_dungeon.get("altura_bloco_sala_tiles", bloco) or bloco)
                dim_largura_dungeon = int(layout_dungeon.get("largura_blocos", 0) or 0)
                dim_altura_dungeon = int(layout_dungeon.get("altura_blocos", 0) or 0)
                dim_largura = int(dim_largura_dungeon * bloco_w)
                dim_altura = int(dim_altura_dungeon * bloco_h)
            else:
                dim_largura_dungeon = 0
                dim_altura_dungeon = 0
                bloco = 30
                bloco_w = bloco
                bloco_h = bloco
            return _serializar_resposta({"status": "ok", "client_id": client_id, "chunks": chunks, "meta": {"total_chunks": len(chunks), "chunk_blocos": int(BANCO_DADOS.chunk_tamanho_unidade()), "dimensao": dimensao, "tipo_dimensao": "dungeon" if _eh_dimensao_dungeon(dimensao) else ("estadio" if _eh_dimensao_estadio(dimensao) else "mundo"), "layout_dungeon": layout_dungeon, "tamanho_bloco_sala_tiles": int(bloco), "largura_bloco_sala_tiles": int(bloco_w), "altura_bloco_sala_tiles": int(bloco_h), "largura_blocos_dungeon": int(dim_largura_dungeon), "altura_blocos_dungeon": int(dim_altura_dungeon), "largura_blocos": int(dim_largura), "altura_blocos": int(dim_altura)}}, serializar_resposta)

        if modo == "mapa_bootstrap":
            chunks_base = _chunks_carregados_cliente(_resolver_posicao_mundo_referencia(obj_player, posicao_camera), dimensao="Mundo")
            chunks_base = _expandir_chunks_exploracao(chunks_base, _bonus_raio_exploracao(obj_player))
            registrar_chunks_explorados(client_id, list(chunks_base), dimensao="Mundo")
            explorados = obter_exploracao_chunks(client_id)
            chunks_explorados = _chunks_explorados_para_set(explorados)
            atlas_conhecidos = _atlas_conhecidos(dados.get("conhecidos") if isinstance(dados, dict) else None)
            chunks_confirmados = set()
            for chunk in chunks_explorados:
                chave_atlas = (int(chunk[0]) // 100, int(chunk[1]) // 100)
                if chunk in atlas_conhecidos.get(chave_atlas, set()):
                    chunks_confirmados.add(chunk)
            chunks_para_enviar = {ch for ch in chunks_explorados if ch not in chunks_confirmados}
            mapa_chunks_enviados.update(chunks_confirmados)
            mapa_chunks_enviados.update(chunks_para_enviar)
            state["mapa_chunks_enviados"] = mapa_chunks_enviados
            atlas = _atlas_do_conjunto(chunks_para_enviar)
            vilas, estadios, regioes, rotas = _poi_mapa()
            return _serializar_resposta({"status": "ok", "meta": _meta_mundo_para_mapa(), "explorados": explorados, "atlas": atlas, "vilas": vilas, "estadios": estadios, "regioes": regioes, "rotas": rotas}, serializar_resposta)

        if modo == "mapa_delta":
            chunks_base = _chunks_carregados_cliente(_resolver_posicao_mundo_referencia(obj_player, posicao_camera), dimensao="Mundo")
            chunks_base = _expandir_chunks_exploracao(chunks_base, _bonus_raio_exploracao(obj_player))
            novos = {BANCO_DADOS.normalizar_chunk(ch) for ch in chunks_base}
            registrar_chunks_explorados(client_id, list(novos), dimensao="Mundo")
            explorados_depois = obter_exploracao_chunks(client_id)
            todos_explorados = _chunks_explorados_para_set(explorados_depois)
            chunks_nunca_enviados = {ch for ch in todos_explorados if ch not in mapa_chunks_enviados}
            mapa_chunks_enviados.update(chunks_nunca_enviados)
            state["mapa_chunks_enviados"] = mapa_chunks_enviados
            atlas = _atlas_do_conjunto(chunks_nunca_enviados)
            return _serializar_resposta({"status": "ok", "meta": _meta_mundo_para_mapa(), "atlas": atlas, "explorados": explorados_depois}, serializar_resposta)

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

        return _serializar_resposta({
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
        }, serializar_resposta)


def desconectar_client(client_id: str) -> None:
    with _LOCK:
        _CLIENTS_CONHECIDOS.discard(client_id)
        _CLIENT_STATE.pop(client_id, None)
    CEREBRO.remover_player(client_id)


def resetar_estado_clientes() -> None:
    with _LOCK:
        _CLIENTS_CONHECIDOS.clear()
        _CLIENT_STATE.clear()
