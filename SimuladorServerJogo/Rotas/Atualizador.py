"""Rota Atualizador: recebe diffs de clients e aplica no estado do servidor."""

from __future__ import annotations

import json
import time
from typing import Dict

from SimuladorServerJogo.Rotas.Ativador import registrar_diff, diff_seq_atual, _obter_state_client, _coletar_diffs_visibilidade, _filtrar_pacotes_por_camera, _normalizar_posicao, _chunks_carregados_cliente, _raio_visao_por_regras
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, criar_objeto_mundo_server
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_perfil_personagem, atualizar_posicao_personagem, atualizar_inventario_personagem
from SimuladorServerJogo.Controle.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Controle.Cerebros.CerebroCentral import CEREBRO
from SimuladorServerJogo.Controle.TiqueServidor import TIQUE_SERVIDOR
from SimuladorServerJogo.Geradores.GeradorPokemon import subir_nivel_pokemon
from Codigo.Geradores.EstruturaNaturais import prioridade_estrutura_natural


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
    estruturas.sort(key=lambda e: (prioridade_estrutura_natural(codigo=e.get("codigo_natural")), float(e.get("y", 0.0)), float(e.get("x", 0.0))))

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


def _pokemon_casa_chave(pokemon: dict, chave_pokemon: str) -> bool:
    if not isinstance(pokemon, dict):
        return False
    alvo = str(chave_pokemon or "").strip().lower()
    if not alvo:
        return False
    for campo in ("UID", "uid", "Id", "id", "ID"):
        valor = pokemon.get(campo)
        if valor is not None and f"id:{valor}".lower() == alvo:
            return True
    nome = str(pokemon.get("Nome") or pokemon.get("nome") or "").strip().lower()
    especie = str(pokemon.get("Especie") or pokemon.get("especie") or "").strip().lower()
    if alvo.startswith("nome:"):
        sufixo = alvo[5:]
        return sufixo in {nome, especie, f"{nome}|{pokemon.get('nivel', '')}".strip("|"), f"{nome}|{pokemon.get('Nivel', '')}".strip("|")}
    return False


def _processar_evento_subir_nivel_pokemon(client_id: str, payload: Dict[str, object]) -> bool:
    chave_pokemon = str(payload.get("chave_pokemon") or "").strip()
    if not chave_pokemon:
        return False
    objeto_id = int(BANCO_DADOS.objeto_id_por_usuario(client_id) or 0)
    if objeto_id <= 0:
        return False
    obj = BANCO_DADOS.obter_objeto(objeto_id)
    if obj is None:
        return False
    inventario = {}
    if isinstance(getattr(obj, "estado_extra", {}), dict):
        inventario = dict(getattr(obj, "estado_extra", {}).get("inventario", {}))
    pokemons = list(inventario.get("pokemons", [])) if isinstance(inventario.get("pokemons"), list) else []
    alterado = False
    for pokemon in pokemons:
        if not _pokemon_casa_chave(pokemon, chave_pokemon):
            continue
        alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
        xp = int(float(alvo.get("XP", alvo.get("xp", 0)) or 0))
        xp_alvo = int(float(alvo.get("XPAlvo", alvo.get("xp_alvo", 0)) or 0))
        if xp_alvo <= 0 or xp < xp_alvo:
            return False
        alvo["XP"] = max(0, xp - xp_alvo)
        alvo["xp"] = alvo["XP"]
        subir_nivel_pokemon(alvo, vezes=1)
        alterado = True
        break
    if not alterado:
        return False
    inventario["pokemons"] = pokemons
    if isinstance(getattr(obj, "estado_extra", {}), dict):
        obj.estado_extra["inventario"] = inventario
    atualizar_inventario_personagem(client_id, inventario)
    registrar_diff(
        "update",
        payload=obj.serializar() if hasattr(obj, "serializar") else {"inventario": inventario},
        escopo=_escopo_objeto(obj),
        objeto_id=int(objeto_id),
        autor="server",
        categoria=str(getattr(obj, "estado_extra", {}).get("subtipo", "player")),
    )
    return True




def _processar_evento_interacao_estadio(client_id: str, payload: Dict[str, object]) -> bool:
    obj_id = int(BANCO_DADOS.objeto_id_por_usuario(client_id) or 0)
    if obj_id <= 0:
        return False
    player = BANCO_DADOS.obter_objeto(obj_id)
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False

    acao = str(payload.get("acao") or "entrar").strip().lower()
    estadio_id = int(payload.get("estadio_id", 0) or int(player.estado_extra.get("estadio_atual_id", 0) or 0))
    estadio = BANCO_DADOS.obter_objeto(estadio_id) if estadio_id > 0 else None

    def _dist_ok(a, b, lim):
        try:
            dx = float(a[0]) - float(b[0]); dy = float(a[1]) - float(b[1])
        except Exception:
            return False
        return (dx * dx + dy * dy) <= (float(lim) * float(lim))

    def _saida_interna(estado_est):
        if isinstance(estado_est.get("saida_interna_pos"), (list, tuple)) and len(estado_est.get("saida_interna_pos")) == 2:
            return [float(estado_est.get("saida_interna_pos")[0]), float(estado_est.get("saida_interna_pos")[1])]
        largura = float(estado_est.get("largura_interna", 60.0) or 60.0)
        altura = float(estado_est.get("altura_interna", 40.0) or 40.0)
        return [largura * 0.5, max(1.0, altura - 3.0)]

    def _spawn_interno(estado_est):
        if isinstance(estado_est.get("spawn_interno_pos"), (list, tuple)) and len(estado_est.get("spawn_interno_pos")) == 2:
            return [float(estado_est.get("spawn_interno_pos")[0]), float(estado_est.get("spawn_interno_pos")[1])]
        largura = float(estado_est.get("largura_interna", 60.0) or 60.0)
        altura = float(estado_est.get("altura_interna", 40.0) or 40.0)
        return [largura * 0.5, max(1.0, altura - 3.0)]

    def _entrada_externa(estado_est):
        if isinstance(estado_est.get("entrada_pos"), (list, tuple)) and len(estado_est.get("entrada_pos")) == 2:
            return [float(estado_est.get("entrada_pos")[0]), float(estado_est.get("entrada_pos")[1])]
        if isinstance(estado_est.get("entrada_offset"), (list, tuple)) and len(estado_est.get("entrada_offset")) == 2:
            return [
                float(estadio.posicao[0]) + float(estado_est.get("entrada_offset")[0]),
                float(estadio.posicao[1]) + float(estado_est.get("entrada_offset")[1]),
            ]
        offset_y = max(2.0, float(estado_est.get("raio_elipse_y", 24.0) or 24.0) - 3.0)
        return [float(estadio.posicao[0]), float(estadio.posicao[1] + offset_y)]

    if acao == "sair":
        if estadio is None:
            return False
        estado_est = getattr(estadio, "estado_extra", {}) if isinstance(getattr(estadio, "estado_extra", {}), dict) else {}
        dim_atual = str(player.estado_extra.get("dimensao") or "Mundo")
        if dim_atual == "Mundo":
            return False
        pos_dim = player.estado_extra.get("posicoes_por_dimensao") if isinstance(player.estado_extra.get("posicoes_por_dimensao"), dict) else {}
        pos_dim[dim_atual] = [float(player.posicao[0]), float(player.posicao[1])]
        saida_interna = _saida_interna(estado_est)
        if not _dist_ok(player.posicao, saida_interna, 2.0):
            return False
        entrada = _entrada_externa(estado_est)
        player.estado_extra["dimensao"] = "Mundo"
        player.estado_extra["estadio_atual_id"] = 0
        player.estado_extra["posicoes_por_dimensao"] = pos_dim
        mundo_salvo = player.estado_extra.get("ultima_pos_mundo")
        if isinstance(mundo_salvo, (list, tuple)) and len(mundo_salvo) == 2:
            mundo_pos = [float(mundo_salvo[0]), float(mundo_salvo[1])]
        else:
            mundo_pos = pos_dim.get("Mundo") if isinstance(pos_dim.get("Mundo"), (list, tuple)) and len(pos_dim.get("Mundo")) == 2 else entrada
        player.definir_posicao(float(mundo_pos[0]), float(mundo_pos[1]))
        registrar_diff("update", payload=player.serializar(), escopo=_escopo_objeto(player), objeto_id=player.Id, autor="server", categoria="player")
        return True

    if estadio is None:
        return False
    estado_est = getattr(estadio, "estado_extra", {}) if isinstance(getattr(estadio, "estado_extra", {}), dict) else {}
    entrada = payload.get("entrada_pos") if isinstance(payload.get("entrada_pos"), (list, tuple)) and len(payload.get("entrada_pos")) == 2 else _entrada_externa(estado_est)
    if not _dist_ok(player.posicao, entrada, 2.0):
        return False

    dim = str(estado_est.get("dimensao_destino") or "EstadioNormal")
    spawn = _spawn_interno(estado_est)
    pos_dim = player.estado_extra.get("posicoes_por_dimensao") if isinstance(player.estado_extra.get("posicoes_por_dimensao"), dict) else {}
    dim_atual = str(player.estado_extra.get("dimensao") or "Mundo")
    if dim_atual != "Mundo":
        return False
    pos_dim[dim_atual] = [float(player.posicao[0]), float(player.posicao[1])]
    player.estado_extra["ultima_pos_mundo"] = [float(player.posicao[0]), float(player.posicao[1])]
    destino = spawn
    player.estado_extra["dimensao"] = dim
    player.estado_extra["estadio_atual_id"] = int(estadio.Id)
    player.estado_extra["posicoes_por_dimensao"] = pos_dim
    player.definir_posicao(float(destino[0]), float(destino[1]))
    registrar_diff("update", payload=player.serializar(), escopo=_escopo_objeto(player), objeto_id=player.Id, autor="server", categoria="player")
    return True


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
    obj_id_dim = int(BANCO_DADOS.objeto_id_por_usuario(client_id) or 0)
    obj_dim = BANCO_DADOS.obter_objeto(obj_id_dim) if obj_id_dim > 0 else None
    if isinstance(obj_dim, AtorServer):
        CEREBRO.atualizar_player_ativo(client_id, obj_dim.posicao)
    else:
        CEREBRO.atualizar_player_ativo(client_id, posicao_camera)
    TIQUE_SERVIDOR.ativar_por_usuario(client_id)
    TIQUE_SERVIDOR.bombear_ate_agora()
    dim_atual = str(getattr(obj_dim, "estado_extra", {}).get("dimensao", "Mundo") if obj_dim is not None else "Mundo")
    posicao_filtro = posicao_camera
    chunks_carregados = _chunks_carregados_cliente(posicao_filtro, dimensao=dim_atual)
    raio_visao = _raio_visao_por_regras()
    seq_inicio_requisicao = diff_seq_atual()

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
                    atualizar_posicao_personagem(usuario, obj.posicao, dimensao=str(getattr(obj, "estado_extra", {}).get("dimensao", "Mundo")))
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
            if categoria == "interacao_bau":
                if CEREBRO.registrar_interacao_bau(client_id, payload):
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            if categoria == "interacao_estadio":
                if _processar_evento_interacao_estadio(client_id, payload):
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            if categoria == "npc_interacao_inicio":
                npc_id = int(payload.get("npc_id", 0) or 0)
                ok, _ = CEREBRO.registrar_inicio_interacao_npc(client_id, npc_id)
                if ok:
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            if categoria == "npc_interacao_fim":
                npc_id = int(payload.get("npc_id", 0) or 0)
                ok, _ = CEREBRO.registrar_fim_interacao_npc(client_id, npc_id)
                if ok:
                    aplicados += 1
                else:
                    ignorados += 1
                continue
            if categoria == "pokemon_subir_nivel":
                if _processar_evento_subir_nivel_pokemon(client_id, payload):
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

    obj_pos_final = BANCO_DADOS.obter_objeto(obj_id_dim) if obj_id_dim > 0 else None
    if isinstance(obj_pos_final, AtorServer):
        CEREBRO.atualizar_player_ativo(client_id, obj_pos_final.posicao)
        posicao_filtro = (float(obj_pos_final.posicao[0]), float(obj_pos_final.posicao[1]))
        dim_atual = str(getattr(obj_pos_final, "estado_extra", {}).get("dimensao", "Mundo") or "Mundo")
        chunks_carregados = _chunks_carregados_cliente(posicao_filtro, dimensao=dim_atual)

    pacotes = _filtrar_pacotes_por_camera(PACOTES_TICK.obter_pacotes_desde(ultimo_tick_recebido, limite=60), posicao_filtro, raio_visao, chunks_carregados, client_id=client_id, dimensao=dim_atual)
    diffs_imediatos = PACOTES_TICK.snapshot_pendentes_desde_seq(seq_inicio_requisicao)
    if diffs_imediatos:
        pacotes.extend(
            _filtrar_pacotes_por_camera(
                [{"tick": int(PACOTES_TICK.tick_atual()), "diffs": diffs_imediatos, "sintetico": True}],
                posicao_filtro,
                raio_visao,
                chunks_carregados,
                client_id=client_id,
                dimensao=dim_atual,
            )
        )
    state = _obter_state_client(client_id)
    vistos = state["objetos_vistos"]
    diffs_extra = _coletar_diffs_visibilidade(posicao_filtro, chunks_carregados, vistos, client_id=client_id, dimensao=dim_atual)
    if diffs_extra:
        if pacotes:
            pacote_vis = pacotes[-1]
            diffs_atuais = pacote_vis.get("diffs", []) if isinstance(pacote_vis.get("diffs"), list) else []
            pacote_vis["diffs"] = list(diffs_atuais) + list(diffs_extra)
        else:
            pacotes.append({"tick": 0, "diffs": diffs_extra, "sintetico": True})

    return _ok(
        "Pacote cliente processado",
        client_id=client_id,
        aplicados=aplicados,
        ignorados=ignorados,
        pacotes=pacotes,
        tick_atual_servidor=PACOTES_TICK.tick_atual(),
        servidor_ts=time.time(),
        meta={"tempo_mundo": CEREBRO.obter_snapshot_tempo()},
    )
