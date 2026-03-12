"""Cérebro do servidor: chunks carregados/simulados, spawn/movimento/despawn e decisões oficiais do servidor."""

from __future__ import annotations

import math
import random
import threading
import time
from collections import deque
from typing import Deque, Dict, List, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import BauServer, PokemonServer
from SimuladorServerJogo.Geradores.GeradorBaus import gerar_bau_server
from SimuladorServerJogo.Geradores.GeradorPokemon import gerar_pokemon_server
from SimuladorServerJogo.Logica.AutoridadeCaptura import coletar_eventos_captura_agendada, resolver_captura, resolver_fruta
from SimuladorServerJogo.Controle.EstadoServidor import (
    obter_personagem_para_entrada,
    atualizar_inventario_personagem,
)
from SimuladorServerJogo.Regras.Loader import carregar_regras_cerebro

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]

_DIRECOES_8: Tuple[Vector2, ...] = (
    (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
    (0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, 0.7071), (-0.7071, -0.7071),
)


class CerebroServer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ultimo_tick = 0.0
        self._tick_contador = 0
        self._ativador_id = ""
        self._players_ativos: Dict[str, Vector2] = {}
        self._pokemons_ids: Set[int] = set()
        self._baus_ids: Set[int] = set()
        self._regras = self._carregar_regras()

        self._spawns_pokemon_ultimos_100: Deque[int] = deque()
        self._spawns_bau_ultimos_100: Deque[int] = deque()
        self._movimento_estado: Dict[int, Dict[str, object]] = {}

    def _carregar_regras(self) -> Dict[str, object]:
        return carregar_regras_cerebro()

    def _i(self, k: str, d: int) -> int:
        try:
            return int(self._regras.get(k, d))
        except Exception:
            return int(d)

    def _f(self, k: str, d: float) -> float:
        try:
            return float(self._regras.get(k, d))
        except Exception:
            return float(d)

    def remover_player(self, client_id: str) -> None:
        with self._lock:
            self._players_ativos.pop(str(client_id), None)
            if self._ativador_id == str(client_id):
                self._ativador_id = next(iter(self._players_ativos.keys()), "")

    def desligar_servidor(self) -> None:
        with self._lock:
            self._players_ativos.clear()
            self._ativador_id = ""
            self._movimento_estado.clear()

    def registrar_spawn_manual(self, objeto) -> None:
        if isinstance(objeto, PokemonServer):
            self._pokemons_ids.add(int(objeto.Id))
            return
        if isinstance(objeto, BauServer):
            self._baus_ids.add(int(objeto.Id))
            return

    def executar_tick_servidor(self) -> None:
        with self._lock:
            self._tick_contador += 1
            self._executar_tick()
            self._ultimo_tick = time.monotonic()

    def processar_ativacao(self, client_id: str, posicao_camera: Vector2) -> Dict[str, object]:
        with self._lock:
            cid = str(client_id)
            if not self._ativador_id:
                self._ativador_id = cid
            self._players_ativos[cid] = (float(posicao_camera[0]), float(posicao_camera[1]))
            chunks_carregados, chunks_simulados = self._calcular_chunks_carregados()
            return {
                "ativador": self._ativador_id,
                "is_ativador": self._ativador_id == cid,
                "tick_executado": False,
                "tick_intervalo_s": (1.0 / 30.0),
                "chunks_visiveis": len(chunks_carregados),
                "chunks_simulados": len(chunks_simulados),
                "players_ativos": len(self._players_ativos),
                "raio_chunks_carregados": self._i("raio_chunks_carregados", 4),
                "raio_chunks_simulados": self._i("raio_chunks_simulados", 3),
            }

    def _sincronizar_registries_com_banco(self) -> None:
        for obj in BANCO_DADOS.listar_objetos():
            subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
            if subt == "pokemon":
                self._pokemons_ids.add(int(obj.Id))
            elif subt == "bau":
                self._baus_ids.add(int(obj.Id))

        self._pokemons_ids = {oid for oid in self._pokemons_ids if isinstance(BANCO_DADOS.obter_objeto(oid), PokemonServer)}
        self._baus_ids = {oid for oid in self._baus_ids if isinstance(BANCO_DADOS.obter_objeto(oid), BauServer)}

    def _limpar_janela_spawns(self) -> None:
        limite = max(1, self._tick_contador - 100)
        while self._spawns_pokemon_ultimos_100 and self._spawns_pokemon_ultimos_100[0] <= limite:
            self._spawns_pokemon_ultimos_100.popleft()
        while self._spawns_bau_ultimos_100 and self._spawns_bau_ultimos_100[0] <= limite:
            self._spawns_bau_ultimos_100.popleft()

    def _executar_tick(self) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        self._sincronizar_registries_com_banco()
        self._limpar_janela_spawns()

        chunks_carregados, chunks_simulados = self._calcular_chunks_carregados()

        if chunks_simulados:
            self._tentar_spawn_pokemon(chunks_simulados)
            self._tentar_spawn_bau(chunks_simulados)

        self._atualizar_movimento_pokemons(chunks_carregados)
        self._executar_tick_baus(chunks_simulados)
        self._executar_tick_capturas()
        self._despawn_simulado(chunks_simulados)

        # limpeza de movimentos órfãos
        for oid in list(self._movimento_estado.keys()):
            if oid not in self._pokemons_ids:
                self._movimento_estado.pop(oid, None)

    def _tentar_spawn_pokemon(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        if random.random() > self._f("chance_spawn_pokemon_por_tick", 0.02):
            return
        if len(self._spawns_pokemon_ultimos_100) >= self._i("limite_spawn_pokemon_100_ticks", 4):
            return
        if self.contagem_pokemons_registrados() >= self._i("limite_total_pokemons", 100):
            return

        tentativas = max(1, self._i("tentativas_spawn_pokemon", 5))
        chunk_tamanho = BANCO_DADOS.chunk_tamanho_unidade()
        chunk_list = list(chunks_simulados)
        random.shuffle(chunk_list)

        for _ in range(tentativas):
            chunk = random.choice(chunk_list)
            if self._contar_pokemons_chunk(chunk) >= self._i("limite_pokemons_chunk", 2):
                continue
            x0, y0 = chunk[0] * chunk_tamanho, chunk[1] * chunk_tamanho
            px = random.uniform(x0 + 0.2, x0 + chunk_tamanho - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_tamanho - 0.2)
            if not self._posicao_spawn_valida((px, py), raio=0.45):
                continue
            novo_id = BANCO_DADOS.gerar_id()
            poke = gerar_pokemon_server(novo_id=novo_id, posicao=(px, py), chunk_xy=chunk)
            BANCO_DADOS.inserir_objeto(poke)
            self._pokemons_ids.add(int(poke.Id))
            self._spawns_pokemon_ultimos_100.append(self._tick_contador)
            registrar_diff("spawn", payload=poke.serializar(), escopo={"centro": [px, py], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            return

    def _tentar_spawn_bau(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        if random.random() > self._f("chance_spawn_bau_por_tick", 0.015):
            return
        if len(self._spawns_bau_ultimos_100) >= self._i("limite_spawn_bau_100_ticks", 2):
            return
        if self.contagem_baus_registrados() >= self._i("limite_total_baus", 60):
            return

        tentativas = max(1, self._i("tentativas_spawn_bau", 5))
        chunk_tamanho = BANCO_DADOS.chunk_tamanho_unidade()
        chunk_list = list(chunks_simulados)
        random.shuffle(chunk_list)

        for _ in range(tentativas):
            chunk = random.choice(chunk_list)
            if self._contar_baus_chunk(chunk) >= self._i("limite_baus_chunk", 1):
                continue
            x0, y0 = chunk[0] * chunk_tamanho, chunk[1] * chunk_tamanho
            px = random.uniform(x0 + 0.2, x0 + chunk_tamanho - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_tamanho - 0.2)
            dados = gerar_bau_server(random)
            raio_bau = float(dados.get("raio_colisao", 0.42) or 0.42)
            if not self._posicao_spawn_valida((px, py), raio=raio_bau):
                continue
            novo_id = BANCO_DADOS.gerar_id()
            bau = BauServer(id_objeto=novo_id, tipo_bau=str(dados.get("tipo_bau", "Comum")), itens=list(dados.get("itens", [])), posicao=(px, py), raio_colisao=raio_bau, raio_interacao=float(dados.get("raio_interacao", 0.85) or 0.85), aberto=False, quantidade_itens=int(dados.get("quantidade_itens", max(1, len(list(dados.get("itens", [])))))), tamanho_tiles=float(dados.get("tamanho_tiles", 1.10) or 1.10))
            BANCO_DADOS.inserir_objeto(bau)
            self._baus_ids.add(int(bau.Id))
            self._spawns_bau_ultimos_100.append(self._tick_contador)
            registrar_diff("spawn", payload=bau.serializar(), escopo={"centro": [px, py], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau")
            return

    def _posicao_spawn_valida(self, pos: Vector2, raio: float) -> bool:
        px, py = float(pos[0]), float(pos[1])
        for obj in BANCO_DADOS.buscar_proximos((px, py), max(0.8, raio + 0.8)):
            subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
            tipo = str(getattr(obj, "tipo_classe", "")).strip().lower()
            if subt in {"pokemon", "bau", "player"} or tipo.startswith("estrutura"):
                rr = float(getattr(obj, "raio_colisao", 0.5) or 0.5) + float(raio)
                if ((px - float(obj.posicao[0])) ** 2 + (py - float(obj.posicao[1])) ** 2) <= (rr * rr):
                    return False
        return True

    def _atualizar_movimento_pokemons(self, chunks_carregados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        chance_inicio = self._f("chance_movimento_pokemon_por_tick", 0.008)
        cooldown_min = self._i("intervalo_minimo_apos_movimento_ticks", 40)
        duracao_max = self._i("tempo_maximo_movimento_ticks", 150)
        velocidade = self._f("velocidade_base_pokemon_tiles_s", 3.0)
        tps = 30.0
        passo = velocidade / tps

        for oid in list(self._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._pokemons_ids.discard(oid)
                continue

            estado = self._movimento_estado.get(oid)
            if not isinstance(estado, dict):
                estado = {"dir": (0.0, 0.0), "restante": 0, "cooldown_ate": 0}
                self._movimento_estado[oid] = estado

            if int(estado.get("restante", 0) or 0) > 0:
                dx, dy = estado.get("dir", (0.0, 0.0))
                destino = (float(poke.posicao[0]) + float(dx) * passo, float(poke.posicao[1]) + float(dy) * passo)
                if self._colisao_movimento_pokemon(oid, destino, poke.raio_colisao):
                    estado["restante"] = 0
                    estado["cooldown_ate"] = self._tick_contador + cooldown_min
                    continue
                poke.definir_posicao(destino[0], destino[1])
                BANCO_DADOS.atualizar_objeto(poke.Id, {"posicao": [poke.posicao[0], poke.posicao[1]]})
                estado["restante"] = int(estado.get("restante", 0) or 0) - 1
                if int(estado.get("restante", 0) or 0) <= 0:
                    estado["cooldown_ate"] = self._tick_contador + cooldown_min
                registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 40}, objeto_id=poke.Id, autor="server", categoria="pokemon")
                continue

            if self._tick_contador < int(estado.get("cooldown_ate", 0) or 0):
                continue

            if BANCO_DADOS.chunk_da_posicao(poke.posicao) not in chunks_carregados:
                continue
            if random.random() > chance_inicio:
                continue

            estado["dir"] = random.choice(_DIRECOES_8)
            estado["restante"] = random.randint(max(10, cooldown_min), max(10, duracao_max))

    def _colisao_movimento_pokemon(self, pokemon_id: int, destino: Vector2, raio: float) -> bool:
        px, py = float(destino[0]), float(destino[1])
        for obj in BANCO_DADOS.buscar_proximos((px, py), max(0.8, float(raio) + 0.8)):
            oid = int(getattr(obj, "Id", 0) or 0)
            if oid == int(pokemon_id):
                continue
            subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
            tipo = str(getattr(obj, "tipo_classe", "")).strip().lower()
            if subt in {"player"} or tipo.startswith("estrutura"):
                rr = float(getattr(obj, "raio_colisao", 0.5) or 0.5) + float(raio)
                if ((px - float(obj.posicao[0])) ** 2 + (py - float(obj.posicao[1])) ** 2) <= (rr * rr):
                    return True
        return False

    def _executar_tick_baus(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Controle.EstadoServidor import atualizar_inventario_personagem, obter_personagem_para_entrada
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        players = [o for o in BANCO_DADOS.listar_objetos() if str(getattr(o, "estado_extra", {}).get("subtipo", "")) == "player"]
        for oid in list(self._baus_ids):
            bau = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(bau, BauServer):
                self._baus_ids.discard(oid)
                continue
            if bool(bau.estado_extra.get("aberto", False)):
                continue
            for player in players:
                dx = float(bau.posicao[0]) - float(player.posicao[0])
                dy = float(bau.posicao[1]) - float(player.posicao[1])
                limite = float(bau.raio_interacao) + float(player.raio_colisao)
                if (dx * dx + dy * dy) > (limite * limite):
                    continue
                info = bau.abrir(player=player, dono_id=int(player.Id))
                if info is None:
                    break
                BANCO_DADOS.atualizar_objeto(bau.Id, {"estado": bau.estado_extra})
                usuario = BANCO_DADOS.usuario_por_objeto_id(int(player.Id))
                if usuario:
                    dados = obter_personagem_para_entrada(usuario) or {}
                    inv = dict(dados.get("inventario", {})) if isinstance(dados.get("inventario"), dict) else {"itens": []}
                    itens = list(inv.get("itens", []))
                    for item in list(info.get("itens", [])):
                        if isinstance(item, dict):
                            itens.append(dict(item))
                    inv["itens"] = itens
                    atualizar_inventario_personagem(usuario, inv)
                    registrar_diff("update", payload={"inventario": inv}, escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 780.0}, objeto_id=player.Id, autor="server", categoria="player")
                registrar_diff("update", payload={"estado": {"aberto": True, "itens": []}}, escopo={"centro": [bau.posicao[0], bau.posicao[1]], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau")
                break

        ttl = int(100)
        for oid in list(self._baus_ids):
            bau = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(bau, BauServer):
                self._baus_ids.discard(oid)
                continue
            if not bool(bau.estado_extra.get("aberto", False)):
                continue
            aberto_em = float(bau.estado_extra.get("aberto_em", 0.0) or 0.0)
            if aberto_em <= 0.0:
                continue
            passou_ticks = int((time.monotonic() - aberto_em) * 30.0)
            if passou_ticks < ttl:
                continue
            removido = BANCO_DADOS.remover_objeto(oid)
            self._baus_ids.discard(oid)
            if removido is not None:
                registrar_diff("despawn", payload={"id": removido.Id, "motivo": "bau_aberto_expirado"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 80}, objeto_id=removido.Id, autor="server", categoria="bau")

    def _executar_tick_capturas(self) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        agora_ms = int(time.time() * 1000)
        for oid in list(self._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._pokemons_ids.discard(oid)
                continue
            eventos = coletar_eventos_captura_agendada(poke, agora_ms)
            if not eventos:
                continue
            BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": poke.estado_extra})
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
            if str(cap.get("fase", "")) == "finalizada" and str(cap.get("resultado", "")) == "sucesso":
                self._adicionar_pokemon_capturado_inventario(int(cap.get("dono_id", 0) or 0), poke)
                removido = BANCO_DADOS.remover_objeto(poke.Id)
                self._pokemons_ids.discard(poke.Id)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "captura_sucesso"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120}, objeto_id=removido.Id, autor="server", categoria="pokemon")

    def _snapshot_pokemon_capturado(self, poke: PokemonServer) -> Dict[str, object]:
        estado = poke.estado_extra if isinstance(getattr(poke, "estado_extra", None), dict) else {}
        return {
            "id": int(getattr(poke, "Id", 0) or 0),
            "especie": str(estado.get("especie") or estado.get("nome") or "Pokemon"),
            "nome": str(estado.get("nome") or estado.get("especie") or "Pokemon"),
            "nivel": int(estado.get("nivel", 1) or 1),
            "iv": int(estado.get("iv", 0) or 0),
            "subivs": dict(estado.get("subivs", {})) if isinstance(estado.get("subivs"), dict) else {},
            "stats_base": dict(estado.get("stats_base", {})) if isinstance(estado.get("stats_base"), dict) else {},
            "stats": dict(estado.get("stats", {})) if isinstance(estado.get("stats"), dict) else {},
            "altura": float(estado.get("altura", 1.0) or 1.0),
            "peso": float(estado.get("peso", 1.0) or 1.0),
            "tipos": list(estado.get("tipos", [])) if isinstance(estado.get("tipos"), list) else [],
            "grupo": str(estado.get("grupo", "") or ""),
            "raridade": int(estado.get("raridade", 1) or 1),
            "estagio": int(estado.get("estagio", 1) or 1),
            "code": str(estado.get("code", "") or ""),
            "linhagem": str(estado.get("linhagem", "") or ""),
            "chunk_origem": list(estado.get("chunk_origem", [])) if isinstance(estado.get("chunk_origem"), list) else [],
            "capturado_em_ms": int(time.time() * 1000),
        }

    def _adicionar_pokemon_capturado_inventario(self, dono_id: int, poke: PokemonServer) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        usuario = BANCO_DADOS.usuario_por_objeto_id(int(dono_id))
        if not usuario:
            return
        perfil = obter_personagem_para_entrada(str(usuario))
        if not isinstance(perfil, dict):
            return
        inventario = perfil.get("inventario") if isinstance(perfil.get("inventario"), dict) else {}
        pokemons = list(inventario.get("pokemons", []))
        pokemons.append(self._snapshot_pokemon_capturado(poke))
        inventario["pokemons"] = pokemons
        atualizar_inventario_personagem(str(usuario), inventario)

        player_id = int(BANCO_DADOS.objeto_id_por_usuario(str(usuario)) or 0)
        player_obj = BANCO_DADOS.obter_objeto(player_id) if player_id > 0 else None
        if player_obj is not None:
            BANCO_DADOS.atualizar_objeto(player_id, {"estado": {"inventario": inventario}})
            registrar_diff("update", payload={"inventario": inventario}, escopo={"centro": [float(player_obj.posicao[0]), float(player_obj.posicao[1])], "raio": 780.0}, objeto_id=player_id, autor="server", categoria="player")

    def _despawn_simulado(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        chance_poke = self._f("chance_despawn_pokemon_simulado_por_tick", 0.003)
        chance_bau = self._f("chance_despawn_bau_simulado_por_tick", 0.002)

        candidatos_poke = []
        for oid in list(self._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._pokemons_ids.discard(oid)
                continue
            if BANCO_DADOS.chunk_da_posicao(poke.posicao) in chunks_simulados:
                candidatos_poke.append((oid, poke))

        if candidatos_poke:
            oid, poke = random.choice(candidatos_poke)
            if random.random() <= chance_poke:
                removido = BANCO_DADOS.remover_objeto(oid)
                self._pokemons_ids.discard(oid)
                self._movimento_estado.pop(oid, None)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "simulado"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 80}, objeto_id=removido.Id, autor="server", categoria="pokemon")

        candidatos_bau = []
        for oid in list(self._baus_ids):
            bau = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(bau, BauServer):
                self._baus_ids.discard(oid)
                continue
            if bool(bau.estado_extra.get("aberto", False)):
                continue
            if BANCO_DADOS.chunk_da_posicao(bau.posicao) in chunks_simulados:
                candidatos_bau.append((oid, bau))

        if candidatos_bau:
            oid, bau = random.choice(candidatos_bau)
            if random.random() <= chance_bau:
                removido = BANCO_DADOS.remover_objeto(oid)
                self._baus_ids.discard(oid)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "simulado"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 80}, objeto_id=removido.Id, autor="server", categoria="bau")

    def registrar_lancamento_projetil(self, client_id: str, payload: Dict[str, object]) -> bool:
        token = str(payload.get("token") or "").strip()
        if not token:
            return False
        dono_id = int(payload.get("dono_id", 0) or 0)
        dono_obj = BANCO_DADOS.obter_objeto(dono_id)
        if dono_obj is None:
            return False

        subtipo = str(payload.get("subtipo_projetil") or "pokebola").strip().lower()
        variante = str(payload.get("variante") or "pokebola").strip().lower()
        if subtipo == "fruta":
            velocidade, alcance = 6.0, 6.0
        elif variante == "sniperball":
            velocidade, alcance = 8.0, 9.0
        elif variante == "fastball":
            velocidade, alcance = 10.0, 7.0
        else:
            velocidade, alcance = 7.0, 7.0

        p0 = payload.get("pos_inicial") if isinstance(payload.get("pos_inicial"), (list, tuple)) and len(payload.get("pos_inicial")) == 2 else [dono_obj.posicao[0], dono_obj.posicao[1]]
        p1 = payload.get("pos_final") if isinstance(payload.get("pos_final"), (list, tuple)) and len(payload.get("pos_final")) == 2 else list(p0)
        dx = float(p1[0]) - float(p0[0])
        dy = float(p1[1]) - float(p0[1])
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        dist_final = min(float(alcance), dist)
        destino = [float(p0[0]) + ux * dist_final, float(p0[1]) + uy * dist_final]

        cliente_ms = int(payload.get("instante_cliente_ms", 0) or 0)
        agora_ms = int(time.time() * 1000)
        tempo_total = max(0.05, dist_final / max(0.1, velocidade))
        atraso_rede_ms = max(0, agora_ms - cliente_ms) if cliente_ms > 0 else 0

        from SimuladorServerJogo.Rotas.Ativador import registrar_diff
        registrar_diff("spawn", payload={"token": token, "subtipo_projetil": subtipo, "variante": variante, "item": str(payload.get("item") or ""), "item_nome": str(payload.get("item_nome") or payload.get("item") or variante), "item_base_id": str(payload.get("item_base_id") or ""), "pos_inicial": [float(p0[0]), float(p0[1])], "pos_final": [float(destino[0]), float(destino[1])], "velocidade_tiles_s": float(velocidade), "dono_id": int(dono_id), "dono_nome": str(payload.get("dono_nome") or client_id)}, escopo={"centro": [float(p0[0]), float(p0[1])], "raio": 120}, objeto_id=int(dono_id), autor=client_id, categoria="projetil_lancamento")

        impacto = self._simular_lancamento_servidor(tuple(p0), tuple(destino), dono_id=dono_id)
        if impacto is None:
            return True

        tempo_impacto_ms = int(max(0.0, (math.hypot(float(impacto.posicao[0]) - float(p0[0]), float(impacto.posicao[1]) - float(p0[1])) / max(0.1, velocidade)) * 1000.0))
        agora_resolucao_ms = int(time.time() * 1000)

        if subtipo == "fruta":
            resolver_fruta(impacto, str(payload.get("item") or variante), contexto={"dono_id": dono_id})
            BANCO_DADOS.atualizar_objeto(impacto.Id, {"estado": impacto.estado_extra})
            registrar_diff("update", payload=impacto.serializar(), escopo={"centro": [impacto.posicao[0], impacto.posicao[1]], "raio": 120}, objeto_id=impacto.Id, autor="server", categoria="pokemon")
            return True

        atraso_animacao_ms = max(0, tempo_impacto_ms - atraso_rede_ms)
        if atraso_animacao_ms <= 0:
            atraso_animacao_ms = 2000

        ret = resolver_captura(impacto, str(payload.get("item") or variante), contexto={
            "dono_id": dono_id,
            "dono_posicao": [dono_obj.posicao[0], dono_obj.posicao[1]],
            "distancia_arremesso_tiles": dist_final,
            "tentativas_falhas_anteriores": int(impacto.estado_extra.get("tentativas_falhas_captura", 0) or 0),
            "bioma": str(impacto.estado_extra.get("bioma", "")),
            "servidor_agora_ms": agora_resolucao_ms,
            "maestria": self._maestria_jogador(client_id),
            "token_arremesso": token,
            "tempo_impacto_ms": tempo_impacto_ms,
            "atraso_animacao_ms": atraso_animacao_ms,
        })
        if bool(ret.get("iniciada", False)):
            estado_captura = impacto.estado_extra.get("captura") if isinstance(impacto.estado_extra.get("captura"), dict) else {}
            estado_captura["token_arremesso"] = token
            BANCO_DADOS.atualizar_objeto(impacto.Id, {"estado": impacto.estado_extra})
            registrar_diff("update", payload=impacto.serializar(), escopo={"centro": [impacto.posicao[0], impacto.posicao[1]], "raio": 120}, objeto_id=impacto.Id, autor="server", categoria="pokemon")
        return True

    def _maestria_jogador(self, client_id: str) -> float:
        dados = obter_personagem_para_entrada(str(client_id))
        if not isinstance(dados, dict):
            return 0.0
        try:
            return float(dados.get("maestria", 0.0) or 0.0)
        except Exception:
            return 0.0

    def _simular_lancamento_servidor(self, origem: Vector2, destino: Vector2, dono_id: int):
        raio_proj = 0.18
        dist_total = max(0.001, math.hypot(destino[0] - origem[0], destino[1] - origem[1]))
        passo_tiles = max(0.08, raio_proj * 0.5)
        passos = max(8, int(math.ceil(dist_total / passo_tiles)))

        for i in range(1, passos + 1):
            t = float(i) / float(passos)
            px = float(origem[0]) + (float(destino[0]) - float(origem[0])) * t
            py = float(origem[1]) + (float(destino[1]) - float(origem[1])) * t

            for obj in BANCO_DADOS.buscar_proximos((px, py), 2.2):
                if int(getattr(obj, "Id", 0) or 0) == int(dono_id):
                    continue

                subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
                tipo = str(getattr(obj, "tipo_classe", "")).strip().lower()
                if subt not in {"pokemon", "bau", "player"} and not tipo.startswith("estrutura"):
                    continue

                raio_alvo = float(getattr(obj, "raio_colisao", 0.35) or 0.35)
                limite = raio_proj + max(0.05, raio_alvo)
                dx = float(getattr(obj, "posicao", (0.0, 0.0))[0]) - px
                dy = float(getattr(obj, "posicao", (0.0, 0.0))[1]) - py
                if (dx * dx + dy * dy) > (limite * limite):
                    continue

                if subt == "pokemon":
                    return obj
                return None
        return None

    def _contar_pokemons_chunk(self, chunk: Chunk) -> int:
        return sum(1 for oid in self._pokemons_ids if isinstance(BANCO_DADOS.obter_objeto(oid), PokemonServer) and BANCO_DADOS.chunk_da_posicao(BANCO_DADOS.obter_objeto(oid).posicao) == chunk)

    def _contar_baus_chunk(self, chunk: Chunk) -> int:
        return sum(1 for oid in self._baus_ids if isinstance(BANCO_DADOS.obter_objeto(oid), BauServer) and BANCO_DADOS.chunk_da_posicao(BANCO_DADOS.obter_objeto(oid).posicao) == chunk)

    def _calcular_chunks_carregados(self):
        chunks_carregados: Set[Chunk] = set()
        chunks_simulados: Set[Chunk] = set()

        raio_carregado = max(0, self._i("raio_chunks_carregados", 4))
        extra_sim = max(0, self._i("raio_chunks_simulados", 3))
        raio_total = raio_carregado + extra_sim

        for pos in self._players_ativos.values():
            centro = BANCO_DADOS.chunk_da_posicao(pos)
            for dx in range(-raio_total, raio_total + 1):
                for dy in range(-raio_total, raio_total + 1):
                    ch = BANCO_DADOS.normalizar_chunk((centro[0] + dx, centro[1] + dy))
                    if abs(dx) <= raio_carregado and abs(dy) <= raio_carregado:
                        chunks_carregados.add(ch)
                    else:
                        chunks_simulados.add(ch)

        chunks_simulados = {ch for ch in chunks_simulados if ch not in chunks_carregados}
        return chunks_carregados, chunks_simulados

    def contagem_pokemons_registrados(self) -> int:
        return len([oid for oid in self._pokemons_ids if BANCO_DADOS.obter_objeto(oid) is not None])

    def contagem_baus_registrados(self) -> int:
        return len([oid for oid in self._baus_ids if BANCO_DADOS.obter_objeto(oid) is not None])


CEREBRO = CerebroServer()
