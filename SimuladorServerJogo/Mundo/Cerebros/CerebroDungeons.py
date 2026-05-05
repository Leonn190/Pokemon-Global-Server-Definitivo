from __future__ import annotations

import math
import random

from SimuladorServerJogo.Gerais.Geradores.GeradorDungeons import gerar_dungeon_layout
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import gerar_pokemon_server, materializar_pokemon
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_dungeons
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.DungeonGeometria import (
    ALTURA_BLOCO_SALA_TILES,
    LARGURA_BLOCO_SALA_TILES,
    centro_sala_em_tiles,
    eh_dimensao_dungeon,
    nome_dimensao_dungeon,
    retangulo_sala_em_tiles,
    sala_atual_por_posicao,
)
from SimuladorServerJogo.Mundo.Dungeons.EstadoDungeon import (
    criar_estado_entrada,
    limpar_estado_temporario,
    registrar_sala_explorada,
    resolver_posicao_saida_dungeon,
)
from SimuladorServerJogo.Mundo.ObjetosMundoServer import AtorServer, ItemMundoServer, PokemonServer
from SimuladorServerJogo.Mundo.ServicoInventario import ServicoInventario


class CerebroDungeons:
    def __init__(self, cerebro_central):
        self._cerebro = cerebro_central
        self._regras = carregar_regras_dungeons()
        self._layouts = {}

    def obter_ou_gerar(self, dungeon_code, porta_idx=1, pedra_id=0):
        dim = nome_dimensao_dungeon(dungeon_code)
        if dim in self._layouts:
            return self._layouts[dim]
        self._layouts[dim] = gerar_dungeon_layout(str(dungeon_code), [{"porta_idx": int(porta_idx or 1), "pedra_id": int(pedra_id or 0)}])
        return self._layouts[dim]

    def _regenerar_run(self, dungeon_code, porta_idx=1, pedra_id=0):
        dim = nome_dimensao_dungeon(dungeon_code)
        self._remover_servos_dimensao(dim)
        self._layouts[dim] = gerar_dungeon_layout(str(dungeon_code), [{"porta_idx": int(porta_idx or 1), "pedra_id": int(pedra_id or 0)}])
        return self._layouts[dim]

    def chunks_proximos(self, dimensao, centro, raio):
        layout = self._layouts.get(str(dimensao), {}) if isinstance(self._layouts.get(str(dimensao), {}), dict) else {}
        bloco_w = max(1, int(layout.get("largura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)) or 32))
        bloco_h = max(1, int(layout.get("altura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)) or 32))
        chunk_sz = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
        max_x = max(1, int((int(layout.get("largura_blocos", 1) or 1) * bloco_w + chunk_sz - 1) // chunk_sz))
        max_y = max(1, int((int(layout.get("altura_blocos", 1) or 1) * bloco_h + chunk_sz - 1) // chunk_sz))
        cx, cy = int(centro[0]), int(centro[1])
        out = []
        for dx in range(-int(raio), int(raio) + 1):
            for dy in range(-int(raio), int(raio) + 1):
                nx, ny = cx + dx, cy + dy
                if nx < 0 or ny < 0 or nx >= max_x or ny >= max_y:
                    continue
                out.append((nx, ny))
        return out

    def chunk_em_grade(self, dimensao, chunk):
        t = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
        tile_vazio = int(self._regras.get("tile_vazio_dungeon", 9) or 9)
        layout = self._layouts.get(str(dimensao), {}) if isinstance(self._layouts.get(str(dimensao), {}), dict) else {}
        grid = layout.get("grid_tiles") if isinstance(layout.get("grid_tiles"), list) else []
        if not grid:
            return [[tile_vazio for _ in range(t)] for _ in range(t)]
        x0 = int(chunk[0]) * t
        y0 = int(chunk[1]) * t
        out = []
        for yy in range(y0, y0 + t):
            row = []
            for xx in range(x0, x0 + t):
                if 0 <= yy < len(grid) and isinstance(grid[yy], list) and 0 <= xx < len(grid[yy]):
                    try:
                        row.append(int(grid[yy][xx]))
                    except (TypeError, ValueError):
                        row.append(tile_vazio)
                else:
                    row.append(tile_vazio)
            out.append(row)
        return out

    def entrar_dungeon(self, client_id, pedra_id, porta_idx, dungeon_code):
        obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(client_id)) or 0)
        player = BANCO_DADOS.obter_objeto(obj_id)
        if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
            return False
        pedra = BANCO_DADOS.obter_objeto(int(pedra_id or 0))
        estado_pedra = getattr(pedra, "estado_extra", {}) if pedra is not None and isinstance(getattr(pedra, "estado_extra", {}), dict) else {}
        if str(estado_pedra.get("subtipo") or "").lower() != "dungeon":
            return False
        if not bool(estado_pedra.get("porta_ativa", False) or estado_pedra.get("estrutura_quebrada", False)):
            return False
        code_real = str(dungeon_code or estado_pedra.get("dungeon_code") or "").strip()
        if not code_real:
            return False
        porta_real = int(porta_idx or estado_pedra.get("porta_idx", 1) or 1)
        if str(estado_pedra.get("dungeon_code") or code_real).strip().lower() != code_real.lower():
            return False
        if int(estado_pedra.get("porta_idx", porta_real) or porta_real) != int(porta_real):
            return False
        dx = float(player.posicao[0]) - float(getattr(pedra, "posicao", [0.0, 0.0])[0])
        dy = float(player.posicao[1]) - float(getattr(pedra, "posicao", [0.0, 0.0])[1])
        if (dx * dx + dy * dy) > float(self._regras.get("raio_interacao_porta", 2.0)) ** 2:
            return False
        layout = self._regenerar_run(code_real, porta_real, pedra_id)
        entrada = next((e for e in layout.get("entradas", []) if int(e.get("porta_idx", 0)) == int(porta_real)), None) or (layout.get("entradas") or [{}])[0]
        player.estado_extra["ultima_pos_mundo"] = [float(player.posicao[0]), float(player.posicao[1])]
        player.estado_extra["dimensao"] = layout.get("dimensao")
        player.estado_extra["estado_dungeon"] = criar_estado_entrada(player, client_id, code_real, porta_real, pedra_id, layout, entrada, self._regras)
        registrar_sala_explorada(player, code_real, str(entrada.get("sala_id") or ""), client_id=str(client_id))
        sx, sy = float(entrada.get("spawn", [0, 0])[0]), float(entrada.get("spawn", [0, 0])[1])
        BANCO_DADOS.atualizar_objeto(player.Id, {"posicao": [sx, sy], "estado": player.estado_extra})
        return True

    def sair_dungeon(self, client_id):
        obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(client_id)) or 0)
        player = BANCO_DADOS.obter_objeto(obj_id)
        if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
            return False
        if not eh_dimensao_dungeon(player.estado_extra.get("dimensao")):
            return False
        estado_dungeon = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
        dimensao = str(player.estado_extra.get("dimensao") or "")
        layout = self._layouts.get(dimensao) if isinstance(self._layouts.get(dimensao), dict) else {}
        porta_idx = int(estado_dungeon.get("porta_idx", 1) or 1)
        entrada = next((e for e in (layout.get("entradas") or []) if int(e.get("porta_idx", 0) or 0) == porta_idx), None)
        saida = entrada.get("saida") if isinstance(entrada, dict) else None
        if isinstance(saida, (list, tuple)) and len(saida) == 2:
            dx = float(player.posicao[0]) - float(saida[0])
            dy = float(player.posicao[1]) - float(saida[1])
            if (dx * dx + dy * dy) > float(self._regras.get("raio_interacao_porta", 2.0)) ** 2:
                return False
        self._expulsar_player_dungeon(player)
        return True

    def registrar_derrota_dungeon(self, client_id, motivo="derrota_batalha", pokemon_id=0, registrar_diff=None):
        obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(client_id)) or 0)
        player = BANCO_DADOS.obter_objeto(obj_id)
        if not isinstance(player, AtorServer):
            return False
        if not eh_dimensao_dungeon(player.estado_extra.get("dimensao")):
            return False
        return self._perder_vida_player(player, str(motivo or "derrota_batalha"), registrar_diff=registrar_diff, forcar=True)

    def executar_tick(self, chunks_carregados, chunks_simulados, registrar_diff):
        _ = (chunks_carregados, chunks_simulados)
        players_por_dim = self._players_dungeon_por_dimensao()
        if not players_por_dim:
            return
        for dimensao, players in players_por_dim.items():
            layout = self._layout_para_dimensao(dimensao, players)
            if not layout:
                continue
            salas_por_id = {str(s.get("id")): s for s in layout.get("salas", []) if isinstance(s, dict)}
            salas_por_pos = {tuple(s.get("posicao_sala", [0, 0])): s for s in salas_por_id.values()}
            for player in players:
                sala = salas_por_pos.get(tuple(sala_atual_por_posicao(player.posicao)))
                if isinstance(sala, dict):
                    estado = player.estado_extra.setdefault("estado_dungeon", {})
                    if isinstance(estado, dict) and estado.get("sala_id") != sala.get("id"):
                        registrar_sala_explorada(player, str(layout.get("dungeon_code") or estado.get("dungeon_code") or ""), str(sala.get("id") or ""))
                        estado["sala_id"] = sala.get("id")
                        estado["sala_posicao"] = list(sala.get("posicao_sala", []))
                        BANCO_DADOS.atualizar_objeto(player.Id, {"estado": player.estado_extra})
                        registrar_diff("update", payload=player.serializar(), escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 80}, objeto_id=player.Id, autor="server", categoria="player")
            self._garantir_bosses(layout, salas_por_id, registrar_diff)
            self._garantir_servos(layout, salas_por_id, registrar_diff)
            self._atualizar_servos(layout, players, salas_por_id, registrar_diff)

    def _players_dungeon_por_dimensao(self):
        out = {}
        for obj in BANCO_DADOS.listar_objetos():
            if not isinstance(obj, AtorServer):
                continue
            dimensao = str(obj.estado_extra.get("dimensao") or "Mundo")
            if eh_dimensao_dungeon(dimensao):
                out.setdefault(dimensao, []).append(obj)
        return out

    def _layout_para_dimensao(self, dimensao, players):
        layout = self._layouts.get(str(dimensao))
        if isinstance(layout, dict):
            return layout
        for player in players:
            estado = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
            code = str(estado.get("dungeon_code") or "").strip()
            if code:
                return self.obter_ou_gerar(code, int(estado.get("porta_idx", 1) or 1), int(estado.get("pedra_id", 0) or 0))
        return {}

    def _pokemons_dungeon(self, dimensao):
        for oid in list(getattr(self._cerebro, "_pokemons_ids", set())):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                continue
            estado = poke.estado_extra if isinstance(poke.estado_extra, dict) else {}
            if str(estado.get("dimensao") or "Mundo") == str(dimensao) and str(estado.get("comportamento_mundo") or "") in {"servo", "boss"}:
                yield poke

    def _garantir_bosses(self, layout, salas_por_id, registrar_diff):
        dimensao = str(layout.get("dimensao") or "")
        existentes = {
            str(p.estado_extra.get("sala_id") or ""): p
            for p in self._pokemons_dungeon(dimensao)
            if bool(p.estado_extra.get("boss", False))
        }
        for boss in list(layout.get("bosses") or []):
            sala_id = str(boss.get("sala_id") or "")
            sala = salas_por_id.get(sala_id)
            if not isinstance(sala, dict) or sala_id in existentes:
                continue
            pos = boss.get("posicao") if isinstance(boss.get("posicao"), list) else centro_sala_em_tiles(sala.get("posicao_sala", [0, 0]))
            self._spawn_pokemon_dungeon(str(boss.get("pokemon") or sala.get("pokemon_boss") or "Pokemon"), pos, sala, layout, "boss", registrar_diff)

    def _garantir_servos(self, layout, salas_por_id, registrar_diff):
        dimensao = str(layout.get("dimensao") or "")
        derrotados = set(layout.setdefault("servos_derrotados", []))
        existentes = {
            str(p.estado_extra.get("servo_uid") or ""): p
            for p in self._pokemons_dungeon(dimensao)
            if str(p.estado_extra.get("comportamento_mundo")) == "servo"
        }
        for item in list(layout.get("servos") or []):
            if not isinstance(item, dict):
                continue
            uid = str(item.get("uid") or "")
            if not uid or uid in existentes or uid in derrotados:
                continue
            sala = salas_por_id.get(str(item.get("sala_id") or ""))
            if not isinstance(sala, dict):
                continue
            pos = self._posicao_spawn_sala(sala)
            self._spawn_pokemon_dungeon(str(item.get("pokemon") or "Pokemon"), pos, sala, layout, "servo", registrar_diff, servo_info=item)

    def _atualizar_servos(self, layout, players, salas_por_id, registrar_diff):
        dimensao = str(layout.get("dimensao") or "")
        for poke in list(self._pokemons_dungeon(dimensao)):
            if str(poke.estado_extra.get("comportamento_mundo")) != "servo":
                continue
            sala_id = str(poke.estado_extra.get("sala_id") or "")
            sala = salas_por_id.get(sala_id)
            if not isinstance(sala, dict):
                continue
            players_sala = [p for p in players if str((p.estado_extra.get("estado_dungeon") or {}).get("sala_id") or "") == sala_id]
            if not players_sala:
                continue
            if bool(poke.estado_extra.get("em_batalha", False)):
                if not self._liberar_lock_batalha_expirado(poke, registrar_diff):
                    continue
            alvo = min(players_sala, key=lambda p: (float(p.posicao[0]) - poke.posicao[0]) ** 2 + (float(p.posicao[1]) - poke.posicao[1]) ** 2)
            dx = float(alvo.posicao[0]) - float(poke.posicao[0])
            dy = float(alvo.posicao[1]) - float(poke.posicao[1])
            dist = math.hypot(dx, dy)
            if dist <= float(poke.raio_colisao + alvo.raio_colisao + 0.10):
                self._processar_colisao_dungeon(alvo, poke, registrar_diff)
                continue
            if dist <= 0.001:
                continue
            passo = self._velocidade_servo(poke) / 30.0
            nx = float(poke.posicao[0]) + (dx / dist) * min(passo, dist)
            ny = float(poke.posicao[1]) + (dy / dist) * min(passo, dist)
            nx, ny = self._clamp_sala(sala, nx, ny, margem=max(0.5, float(poke.raio_colisao)))
            BANCO_DADOS.atualizar_objeto(poke.Id, {"posicao": [nx, ny], "estado": poke.estado_extra})
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [nx, ny], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")

    def _processar_colisao_dungeon(self, player, poke, registrar_diff):
        tick = int(getattr(self._cerebro, "_tick_contador", 0))
        if tick < int(poke.estado_extra.get("cooldown_colisao_ate_tick", 0) or 0):
            return
        estado = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
        inv_ate = int(estado.get("invulneravel_dungeon_ate_tick", 0) or 0)
        if tick < inv_ate:
            return
        if self._player_tem_pokemon_apto(player):
            poke.estado_extra["cooldown_colisao_ate_tick"] = tick + int(self._regras.get("servo_cooldown_colisao_ticks", 30) or 30)
            poke.estado_extra["ultimo_player_colidido"] = str(player.estado_extra.get("usuario") or "")
            BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": poke.estado_extra})
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            return
        self._perder_vida_player(player, "colisao_sem_pokemon", registrar_diff=registrar_diff)

    def _liberar_lock_batalha_expirado(self, poke, registrar_diff) -> bool:
        if bool(poke.estado_extra.get("batalha_confirmada", False)):
            return False
        tick = int(getattr(self._cerebro, "_tick_contador", 0))
        inicio = int(poke.estado_extra.get("batalha_tick", tick) or tick)
        timeout = int(self._regras.get("servo_batalha_lock_timeout_ticks", 180) or 180)
        if timeout <= 0 or tick - inicio <= timeout:
            return False
        poke.estado_extra.pop("em_batalha", None)
        poke.estado_extra.pop("batalha_client_id", None)
        poke.estado_extra.pop("batalha_tick", None)
        poke.estado_extra.pop("batalha_confirmada", None)
        BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": poke.estado_extra})
        if callable(registrar_diff):
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")
        return True

    def _velocidade_servo(self, poke) -> float:
        fallback = float(self._regras.get("servo_velocidade_tiles_s", 2.8) or 2.8)
        stats = poke.estado_extra.get("stats") if isinstance(poke.estado_extra.get("stats"), dict) else {}
        try:
            vel = float(stats.get("Vel", stats.get("vel")))
        except (TypeError, ValueError):
            return fallback
        base = float(self._regras.get("servo_vel_base_tiles_s", 1.0) or 1.0)
        divisor = max(1.0, float(self._regras.get("servo_vel_divisor", 90.0) or 90.0))
        mult = float(self._regras.get("servo_vel_mult_dungeon", 0.85) or 0.85)
        minimo = float(self._regras.get("servo_vel_min_tiles_s", 1.4) or 1.4)
        maximo = float(self._regras.get("servo_vel_max_tiles_s", 4.6) or 4.6)
        return max(minimo, min(maximo, (base + (vel / divisor)) * mult))

    def _spawn_pokemon_dungeon(self, especie, pos, sala, layout, tipo, registrar_diff, servo_info=None):
        x, y = self._clamp_sala(sala, float(pos[0]), float(pos[1]), margem=0.8)
        novo_id = BANCO_DADOS.gerar_id()
        poke = gerar_pokemon_server(novo_id=novo_id, posicao=(x, y), chunk_xy=BANCO_DADOS.chunk_da_posicao((x, y)), especie=especie)
        if tipo == "boss":
            bruto = dict(poke.estado_extra)
            bruto["nivel"] = 100
            bruto["iv"] = 100
            mat = materializar_pokemon(bruto)
            estado_mat = mat.get("estado") if isinstance(mat.get("estado"), dict) else mat
            if isinstance(estado_mat, dict):
                poke.estado_extra.update(estado_mat)
        poke.estado_extra.update(
            {
                "subtipo": "pokemon",
                "comportamento": tipo,
                "comportamento_mundo": tipo,
                "capturavel": False,
                "dungeon_code": str(layout.get("dungeon_code") or ""),
                "dimensao": str(layout.get("dimensao") or ""),
                "sala_id": str(sala.get("id") or ""),
                "sala_posicao": list(sala.get("posicao_sala") or []),
                "tipo_batalha": tipo,
                "esta_irritado": False,
            }
        )
        if tipo == "servo" and isinstance(servo_info, dict):
            poke.estado_extra.update(
                {
                    "servo_uid": str(servo_info.get("uid") or ""),
                    "possui_chave_dungeon": bool(servo_info.get("possui_chave", False)),
                    "chave_id": str(servo_info.get("chave_id") or ""),
                    "drop_item": "ChaveDungeon" if bool(servo_info.get("possui_chave", False)) else "",
                }
            )
        if tipo == "boss":
            stats = poke.estado_extra.get("stats") if isinstance(poke.estado_extra.get("stats"), dict) else {}
            vida_max = float(stats.get("Vida", 1.0) or 1.0)
            barreira = round(50.0 + (vida_max * 0.20), 2)
            poke.estado_extra.update(
                {
                    "boss": True,
                    "pokemon_boss": str(especie),
                    "nivel": 100,
                    "iv": 100,
                    "BarreiraAtual": barreira,
                    "barreira_inicial": barreira,
                }
            )
        BANCO_DADOS.inserir_objeto(poke)
        self._cerebro._pokemons_ids.add(int(poke.Id))
        registrar_diff("spawn", payload=poke.serializar(), escopo={"centro": [x, y], "raio": 100}, objeto_id=poke.Id, autor="server", categoria="pokemon")
        return poke

    def _despawn_pokemon_dungeon(self, poke, registrar_diff):
        snapshot = poke.serializar()
        BANCO_DADOS.remover_objeto(poke.Id)
        self._cerebro._pokemons_ids.discard(int(poke.Id))
        registrar_diff("despawn", payload=snapshot, escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 100}, objeto_id=poke.Id, autor="server", categoria="pokemon")

    def _remover_servos_dimensao(self, dimensao: str):
        for poke in list(self._pokemons_dungeon(str(dimensao))):
            if str(poke.estado_extra.get("comportamento_mundo") or "") != "servo":
                continue
            BANCO_DADOS.remover_objeto(poke.Id)
            self._cerebro._pokemons_ids.discard(int(poke.Id))

    def registrar_pokemon_derrotado(self, pokemon_id: int, client_id: str, registrar_diff=None):
        poke = BANCO_DADOS.obter_objeto(int(pokemon_id or 0))
        if not isinstance(poke, PokemonServer):
            return False
        estado = poke.estado_extra if isinstance(poke.estado_extra, dict) else {}
        if str(estado.get("comportamento_mundo") or "") == "boss" or bool(estado.get("boss", False)):
            estado.pop("em_batalha", None)
            estado.pop("batalha_client_id", None)
            estado.pop("batalha_confirmada", None)
            BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": estado})
            if callable(registrar_diff):
                registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120}, objeto_id=int(poke.Id), autor="server", categoria="pokemon")
            return True
        if str(estado.get("comportamento_mundo") or "") != "servo":
            return False
        dimensao = str(estado.get("dimensao") or "")
        layout = self._layouts.get(dimensao) if isinstance(self._layouts.get(dimensao), dict) else {}
        uid = str(estado.get("servo_uid") or "")
        if uid:
            derrotados = layout.setdefault("servos_derrotados", []) if isinstance(layout, dict) else []
            if isinstance(derrotados, list) and uid not in derrotados:
                derrotados.append(uid)
        if bool(estado.get("possui_chave_dungeon", False)):
            self._dropar_chave_dungeon(poke, registrar_diff)
        self._despawn_pokemon_dungeon(poke, registrar_diff)
        return True

    def _dropar_chave_dungeon(self, poke, registrar_diff):
        item = self._cerebro._servico_inventario.normalizar_item({"Code": "ChaveDungeon", "Nome": "ChaveDungeon", "quantidade": 1})
        novo_id = BANCO_DADOS.gerar_id()
        pos = [float(poke.posicao[0]), float(poke.posicao[1])]
        obj = ItemMundoServer(
            id_objeto=novo_id,
            posicao=(pos[0], pos[1]),
            dono_id=0,
            item_nome=str(item.get("Nome") or "ChaveDungeon"),
            item_base_id=str(item.get("Code") or "ChaveDungeon"),
            quantidade=1,
            pos_inicial=(pos[0], pos[1]),
            pos_final=(pos[0], pos[1]),
            velocidade=0.0,
            tick_spawn=int(getattr(self._cerebro, "_tick_contador", 0)),
            item_dados=item,
        )
        obj.estado_extra["dimensao"] = str(poke.estado_extra.get("dimensao") or "")
        BANCO_DADOS.inserir_objeto(obj)
        self._cerebro._itens_mundo_ids.add(int(obj.Id))
        if callable(registrar_diff):
            registrar_diff("spawn", payload=obj.serializar(), escopo={"centro": pos, "raio": 120}, objeto_id=int(obj.Id), autor="server", categoria="item_mundo")
        return True

    def _posicao_spawn_sala(self, sala):
        x, y, w, h = retangulo_sala_em_tiles(sala.get("posicao_sala", [0, 0]))
        return [random.uniform(x + 3.0, x + max(3.0, w - 3.0)), random.uniform(y + 3.0, y + max(3.0, h - 3.0))]

    @staticmethod
    def _clamp_sala(sala, x, y, margem=0.5):
        sx, sy, w, h = retangulo_sala_em_tiles(sala.get("posicao_sala", [0, 0]))
        return (max(sx + margem, min(sx + w - margem, float(x))), max(sy + margem, min(sy + h - margem, float(y))))

    def destrancar_porta(self, client_id: str, porta_id: str, registrar_diff=None) -> bool:
        obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(client_id)) or 0)
        player = BANCO_DADOS.obter_objeto(obj_id)
        if not isinstance(player, AtorServer) or not eh_dimensao_dungeon(player.estado_extra.get("dimensao")):
            return False
        estado_dungeon = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
        layout = self._layouts.get(str(player.estado_extra.get("dimensao") or "")) if isinstance(self._layouts.get(str(player.estado_extra.get("dimensao") or "")), dict) else {}
        if not layout:
            return False
        porta = self._buscar_porta(layout, str(porta_id or ""))
        if not isinstance(porta, dict) or not bool(porta.get("trancada", False)):
            return False
        if not self._player_perto_porta(player, porta, layout):
            return False
        if not self._chave_na_mao(player):
            return False
        inv = player.estado_extra.get("inventario") if isinstance(player.estado_extra.get("inventario"), dict) else {}
        serv = ServicoInventario()
        if not serv.consumir_um(inv, "ChaveDungeon", "ChaveDungeon"):
            return False
        estado_dungeon.setdefault("portas_destrancadas", [])
        if isinstance(estado_dungeon["portas_destrancadas"], list) and porta["id"] not in estado_dungeon["portas_destrancadas"]:
            estado_dungeon["portas_destrancadas"].append(porta["id"])
        player.estado_extra["inventario"] = inv
        self._abrir_porta_layout(layout, porta)
        BANCO_DADOS.atualizar_objeto(player.Id, {"estado": player.estado_extra})
        if callable(registrar_diff):
            registrar_diff("update", payload=player.serializar(), escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 120}, objeto_id=int(player.Id), autor="server", categoria="player")
        serv.persistir_jogador(str(player.estado_extra.get("usuario") or client_id), int(player.Id), inv, registrar_diff if callable(registrar_diff) else (lambda *a, **k: None))
        return True

    @staticmethod
    def _buscar_porta(layout: dict, porta_id: str):
        for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
            for info in list(sala.get("portas_info") or []):
                if str(info.get("id") or "") == str(porta_id or ""):
                    return {"sala": sala, **dict(info)}
        return None

    @staticmethod
    def _porta_centro_tiles(sala: dict, direcao: str):
        x, y, w, h = retangulo_sala_em_tiles(sala.get("posicao_sala", [0, 0]))
        if direcao == "N":
            return [x + w / 2.0, y]
        if direcao == "S":
            return [x + w / 2.0, y + h - 1]
        if direcao == "L":
            return [x + w - 1, y + h / 2.0]
        return [x, y + h / 2.0]

    def normalizar_posicao_player(self, player, destino):
        if not isinstance(player, AtorServer) or not eh_dimensao_dungeon(player.estado_extra.get("dimensao")):
            return destino
        if not (isinstance(destino, (list, tuple)) and len(destino) == 2):
            return [float(player.posicao[0]), float(player.posicao[1])]
        dimensao = str(player.estado_extra.get("dimensao") or "")
        layout = self._layouts.get(dimensao) if isinstance(self._layouts.get(dimensao), dict) else {}
        if not layout:
            estado = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
            layout = self.obter_ou_gerar(str(estado.get("dungeon_code") or dimensao.removeprefix("Dungeon_")), int(estado.get("porta_idx", 1) or 1), int(estado.get("pedra_id", 0) or 0))
        salas_por_pos = {tuple(s.get("posicao_sala", [0, 0])): s for s in layout.get("salas", []) if isinstance(s, dict)}
        origem_pos = tuple(sala_atual_por_posicao(player.posicao))
        destino_pos = tuple(sala_atual_por_posicao(destino))
        sala_origem = salas_por_pos.get(origem_pos)
        sala_destino = salas_por_pos.get(destino_pos)
        if not isinstance(sala_destino, dict):
            return list(self._clamp_sala(sala_origem or {"posicao_sala": origem_pos}, player.posicao[0], player.posicao[1], margem=max(0.5, float(player.raio_colisao))))
        if origem_pos == destino_pos or not isinstance(sala_origem, dict):
            return [float(destino[0]), float(destino[1])]
        dx, dy = destino_pos[0] - origem_pos[0], destino_pos[1] - origem_pos[1]
        if abs(dx) + abs(dy) != 1:
            return list(self._clamp_sala(sala_origem, player.posicao[0], player.posicao[1], margem=max(0.5, float(player.raio_colisao))))
        direcao = "L" if dx > 0 else "O" if dx < 0 else "S" if dy > 0 else "N"
        if not self._passagem_aberta(sala_origem, direcao, player):
            return list(self._clamp_sala(sala_origem, player.posicao[0], player.posicao[1], margem=max(0.5, float(player.raio_colisao))))
        if not self._dentro_da_abertura(sala_origem, direcao, destino):
            return list(self._clamp_sala(sala_origem, player.posicao[0], player.posicao[1], margem=max(0.5, float(player.raio_colisao))))
        return [float(destino[0]), float(destino[1])]

    def _passagem_aberta(self, sala: dict, direcao: str, player) -> bool:
        estado = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
        destrancadas = {str(p) for p in list(estado.get("portas_destrancadas") or [])}
        for info in list(sala.get("portas_info") or []):
            if str(info.get("direcao") or "") != str(direcao):
                continue
            return (not bool(info.get("trancada", False))) or str(info.get("id") or "") in destrancadas
        return False

    def _dentro_da_abertura(self, sala: dict, direcao: str, pos) -> bool:
        x, y, w, h = retangulo_sala_em_tiles(sala.get("posicao_sala", [0, 0]))
        porta_w = max(1, int(self._regras.get("porta_largura_tiles", 4) or 4))
        metade = max(0.5, porta_w / 2.0)
        if direcao in {"N", "S"}:
            return abs(float(pos[0]) - (x + w / 2.0)) <= metade
        return abs(float(pos[1]) - (y + h / 2.0)) <= metade

    def _player_perto_porta(self, player, porta: dict, layout: dict) -> bool:
        centro = self._porta_centro_tiles(porta.get("sala", {}), str(porta.get("direcao") or ""))
        dx = float(player.posicao[0]) - float(centro[0])
        dy = float(player.posicao[1]) - float(centro[1])
        return (dx * dx + dy * dy) <= float(self._regras.get("raio_interacao_porta", 2.0) or 2.0) ** 2

    @staticmethod
    def _chave_na_mao(player) -> bool:
        inv = player.estado_extra.get("inventario") if isinstance(player.estado_extra.get("inventario"), dict) else {}
        itens = list(inv.get("itens") or [])
        idx = int(inv.get("slot_selecionado", player.estado_extra.get("slot_selecionado", 0)) or 0)
        item = itens[idx] if 0 <= idx < len(itens) else None
        if not isinstance(item, dict):
            return False
        return str(item.get("Code") or "").strip().lower() == "chavedungeon" or str(item.get("Nome") or "").strip().lower() == "chavedungeon"

    def _abrir_porta_layout(self, layout: dict, porta: dict) -> None:
        pid = str(porta.get("id") or "")
        tile_chao = int(self._regras.get("tile_chao_dungeon", 8) or 8)
        for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
            novas = []
            for info in list(sala.get("portas_info") or []):
                item = dict(info)
                if str(item.get("id") or "") == pid:
                    item["trancada"] = False
                    d = str(item.get("direcao") or "")
                    if d in list(sala.get("portas_bloqueadas") or []):
                        sala["portas_bloqueadas"] = [p for p in list(sala.get("portas_bloqueadas") or []) if str(p) != d]
                novas.append(item)
            sala["portas_info"] = novas
        for item in list(layout.get("portas_trancadas") or []):
            if str(item.get("id") or "") == pid:
                item["trancada"] = False
        grid = layout.get("grid_tiles") if isinstance(layout.get("grid_tiles"), list) else []
        sala = porta.get("sala") if isinstance(porta.get("sala"), dict) else {}
        pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
        self._marcar_porta_grid_runtime(grid, pos, str(porta.get("direcao") or ""), tile_chao)

    def _marcar_porta_grid_runtime(self, grid, pos, direcao, tile):
        porta_w = max(1, int(self._regras.get("porta_largura_tiles", 4) or 4))
        x0 = int(pos[0]) * LARGURA_BLOCO_SALA_TILES
        y0 = int(pos[1]) * ALTURA_BLOCO_SALA_TILES
        cx = x0 + (LARGURA_BLOCO_SALA_TILES // 2)
        cy = y0 + (ALTURA_BLOCO_SALA_TILES // 2)
        meio = porta_w // 2
        if direcao in {"N", "S"}:
            y = y0 if direcao == "N" else y0 + ALTURA_BLOCO_SALA_TILES - 1
            pontos = [(x, y) for x in range(cx - meio, cx - meio + porta_w)]
        else:
            x = x0 + LARGURA_BLOCO_SALA_TILES - 1 if direcao == "L" else x0
            pontos = [(x, y) for y in range(cy - meio, cy - meio + porta_w)]
        for x, y in pontos:
            if 0 <= y < len(grid) and isinstance(grid[y], list) and 0 <= x < len(grid[y]):
                grid[y][x] = int(tile)

    def _perder_vida_player(self, player, motivo, registrar_diff=None, forcar=False):
        estado = player.estado_extra.get("estado_dungeon")
        if not isinstance(estado, dict):
            return False
        tick = int(getattr(self._cerebro, "_tick_contador", 0))
        if not bool(forcar) and tick < int(estado.get("invulneravel_dungeon_ate_tick", 0) or 0):
            return False
        coracoes = max(0, int(estado.get("coracoes", self._regras.get("coracoes_iniciais", 3)) or 0) - 1)
        estado["coracoes"] = coracoes
        estado["ultimo_dano_motivo"] = str(motivo or "")
        estado["invulneravel_dungeon_ate_tick"] = tick + int(self._regras.get("invulnerabilidade_dungeon_ticks", 90) or 90)
        if coracoes <= 0:
            self._expulsar_player_dungeon(player)
        else:
            BANCO_DADOS.atualizar_objeto(player.Id, {"estado": player.estado_extra})
        if callable(registrar_diff):
            registrar_diff("update", payload=player.serializar(), escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 120}, objeto_id=player.Id, autor="server", categoria="player")
        return True

    def _expulsar_player_dungeon(self, player):
        estado_dungeon = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
        pos = resolver_posicao_saida_dungeon(player, estado_dungeon)
        limpar_estado_temporario(player)
        BANCO_DADOS.atualizar_objeto(player.Id, {"posicao": [float(pos[0]), float(pos[1])], "estado": player.estado_extra})
        try:
            from SimuladorServerJogo.Gerais.EstadoServidor import atualizar_posicao_personagem

            atualizar_posicao_personagem(str(player.estado_extra.get("usuario") or ""), [float(pos[0]), float(pos[1])], dimensao="Mundo")
        except Exception:
            pass

    @staticmethod
    def _player_tem_pokemon_apto(player):
        inv = player.estado_extra.get("inventario") if isinstance(player.estado_extra.get("inventario"), dict) else {}

        def _iter_pokemons():
            for p in list(inv.get("pokemons") or []):
                if isinstance(p, dict):
                    yield p
            for time in list(inv.get("times_pokemon") or []):
                if not isinstance(time, dict):
                    continue
                for p in list(time.get("Slots") or time.get("slots") or []):
                    if isinstance(p, dict):
                        yield p

        for pokemon in _iter_pokemons():
            estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
            vida = estado.get("VidaAtual", estado.get("vida_atual", pokemon.get("VidaAtual", pokemon.get("vida_atual", 1.0))))
            try:
                vida_f = float(vida)
            except (TypeError, ValueError):
                vida_f = 1.0
            if vida_f > 0.0 and not bool(estado.get("morto", False)):
                return True
        return False
