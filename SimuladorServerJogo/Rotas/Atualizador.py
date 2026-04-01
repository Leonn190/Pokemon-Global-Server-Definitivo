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
from SimuladorServerJogo.Controle.Cerebros.CerebroCentral import CEREBRO
from SimuladorServerJogo.Geradores.GeradorPokemon import subir_nivel_pokemon


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


def _processar_pendencias_pokemon_nivel(inventario: dict) -> dict:
    inv = dict(inventario) if isinstance(inventario, dict) else {}
    pokemons = list(inv.get("pokemons", [])) if isinstance(inv.get("pokemons"), list) else []
    alterado = False
    for pokemon in pokemons:
        if not isinstance(pokemon, dict):
            continue
        alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
        pendente = int(float(alvo.get("__subir_nivel_pendente", 0) or 0))
        if pendente <= 0:
            continue
        subir_nivel_pokemon(alvo, vezes=pendente)
        alvo.pop("__subir_nivel_pendente", None)
        alterado = True
    if alterado:
        inv["pokemons"] = pokemons
    return inv


def _bloco_mundo_em(wx: int, wy: int) -> int:
    largura, altura = BANCO_DADOS.limites_mundo()
    if largura <= 0 or altura <= 0:
        return 0
    gx = int(wx) % int(largura)
    gy = int(wy) % int(altura)
    chunk_tamanho = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
    cx = int(gx // chunk_tamanho)
    cy = int(gy // chunk_tamanho)
    grid = BANCO_DADOS.chunk_em_grade((cx, cy))
    if not grid:
        return 0
    lx = int(gx - (cx * chunk_tamanho))
    ly = int(gy - (cy * chunk_tamanho))
    if ly < 0 or ly >= len(grid):
        return 0
    row = grid[ly]
    if lx < 0 or lx >= len(row):
        return 0
    try:
        return int(row[lx])
    except (TypeError, ValueError):
        return 0


def _coletar_contexto_batalha_servidor(centro: tuple[float, float], rx: int = 50, ry: int = 30) -> Dict[str, object]:
    cx, cy = float(centro[0]), float(centro[1])
    x0, y0 = int(cx) - int(rx), int(cy) - int(ry)
    largura_rect = int(rx) * 2
    altura_rect = int(ry) * 2

    tiles = []
    for ly in range(altura_rect):
        wy = y0 + ly
        for lx in range(largura_rect):
            wx = x0 + lx
            tiles.append({"x": int(lx), "y": int(ly), "bloco": _bloco_mundo_em(wx, wy)})

    largura_mundo, altura_mundo = BANCO_DADOS.limites_mundo()
    estruturas = []
    for obj in BANCO_DADOS.listar_objetos():
        tipo = str(getattr(obj, "tipo_classe", "") or "")
        if not tipo.startswith("estrutura"):
            continue
        ox, oy = float(obj.posicao[0]), float(obj.posicao[1])
        dx = ox - cx
        dy = oy - cy
        if largura_mundo > 0:
            dx = dx - round(dx / float(largura_mundo)) * float(largura_mundo)
        if altura_mundo > 0:
            dy = dy - round(dy / float(altura_mundo)) * float(altura_mundo)
        if abs(dx) > float(rx) or abs(dy) > float(ry):
            continue
        local_x = float(rx) + dx
        local_y = float(ry) + dy
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        estruturas.append({
            "x": local_x,
            "y": local_y,
            "codigo_natural": int(getattr(obj, "codigo_natural", estado.get("codigo_natural", 0)) or 0),
            "sprite": str(getattr(obj, "sprite", "") or ""),
        })

    return {
        "origem": [x0, y0],
        "centro": [int(rx), int(ry)],
        "largura": int(largura_rect),
        "altura": int(altura_rect),
        "arena_largura": 50,
        "arena_altura": 30,
        "tiles": tiles,
        "estruturas": estruturas,
    }



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
        if tipo not in {"spawn", "update", "despawn", "evento"}:
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
                    inventario_sync = _processar_pendencias_pokemon_nivel(payload_in.get("inventario"))
                    payload_in["inventario"] = inventario_sync
                    atualizar_inventario_personagem(usuario, inventario_sync)
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

        if tipo in {"spawn", "evento"}:
            categoria = str(diff.get("categoria", "")).strip().lower()
            if categoria in {"batalha_contexto_request", "combate_contexto_request"}:
                centro = payload.get("centro") if isinstance(payload.get("centro"), (list, tuple)) and len(payload.get("centro")) == 2 else payload.get("player_pos")
                if not isinstance(centro, (list, tuple)) or len(centro) != 2:
                    centro = [0.0, 0.0]
                contexto = _coletar_contexto_batalha_servidor((float(centro[0]), float(centro[1])), rx=50, ry=30)
                return _ok("Contexto de batalha pronto", client_id=client_id, aplicados=aplicados, ignorados=ignorados, contexto_batalha=contexto)
            if categoria in {"coleta_estrutura_natural", "estrutura_natural_coleta"}:
                if CEREBRO.registrar_coleta_estrutura(client_id, payload):
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            if tipo == "evento":
                ignorados += 1
                continue
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
