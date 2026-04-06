"""Cérebro central do servidor: maestro de tick e coordenação de domínios."""

from __future__ import annotations

import random
import threading
import time
import math
from collections import deque
from typing import Deque, Dict, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import BauServer, ItemMundoServer, PokemonServer, XpMundoServer
from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada
from SimuladorServerJogo.Controle.LoaderRegras import carregar_regras_runtime_servidor
from SimuladorServerJogo.Geradores.GeradorBaus import gerar_bau_server
from SimuladorServerJogo.Geradores.GeradorPokemon import materializar_pokemon

from SimuladorServerJogo.Controle.Cerebros.CerebroBaus import CerebroBaus
from SimuladorServerJogo.Controle.Cerebros.CerebroPokemons import CerebroPokemons
from SimuladorServerJogo.Controle.Cerebros.CerebroProjeteis import CerebroProjeteis
from SimuladorServerJogo.Controle.Cerebros.CerebroItensMundo import CerebroItensMundo
from SimuladorServerJogo.Controle.Cerebros.CerebroEstruturasNaturais import CerebroEstruturasNaturais
from SimuladorServerJogo.Controle.Cerebros.CerebroXpMundo import CerebroXpMundo
from SimuladorServerJogo.Controle.Cerebros.CerebroNPCs import CerebroNPCs
from SimuladorServerJogo.Controle.Cerebros.CerebroTempo import CerebroTempo
from SimuladorServerJogo.Controle.ServicoInventario import ServicoInventario

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]


class CerebroCentral:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ultimo_tick = 0.0
        self._tick_contador = 0
        self._ativador_id = ""
        self._players_ativos: Dict[str, Vector2] = {}
        self._pokemons_ids: Set[int] = set()
        self._baus_ids: Set[int] = set()
        self._itens_mundo_ids: Set[int] = set()
        self._xp_mundo_ids: Set[int] = set()
        self._regras = carregar_regras_runtime_servidor()

        self._spawns_pokemon_ultimos_200: Deque[int] = deque()
        self._spawns_bau_ultimos_200: Deque[int] = deque()
        self._movimento_estado: Dict[int, Dict[str, object]] = {}
        self._capturas_inventario_pendentes: Deque[Dict[str, object]] = deque()

        self._servico_inventario = ServicoInventario()
        self._cerebro_baus = CerebroBaus(self)
        self._cerebro_pokemons = CerebroPokemons(self)
        self._cerebro_projeteis = CerebroProjeteis(self)
        self._cerebro_itens_mundo = CerebroItensMundo(self)
        self._cerebro_estruturas = CerebroEstruturasNaturais(self)
        self._cerebro_xp_mundo = CerebroXpMundo(self)
        self._cerebro_npcs = CerebroNPCs(self)
        self._cerebro_tempo = CerebroTempo(self._regras)
        self._snapshot_tempo = self._cerebro_tempo.snapshot()

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

    def tem_players_ativos(self) -> bool:
        with self._lock:
            return bool(self._players_ativos)

    def obter_snapshot_tempo(self) -> Dict[str, object]:
        with self._lock:
            return dict(self._snapshot_tempo)

    def alternar_chuva_global(self) -> bool:
        with self._lock:
            self._snapshot_tempo = self._cerebro_tempo.snapshot()
            novo = self._cerebro_tempo.alternar_chuva_habilitada()
            self._snapshot_tempo = self._cerebro_tempo.snapshot()
            return bool(novo)

    def definir_chuva_alvo_global(self, alvo: int) -> bool:
        with self._lock:
            ok = self._cerebro_tempo.definir_chuva_alvo_manual(int(alvo))
            self._snapshot_tempo = self._cerebro_tempo.snapshot()
            return bool(ok)

    def chuva_habilitada(self) -> bool:
        with self._lock:
            return self._cerebro_tempo.chuva_habilitada()

    def registrar_spawn_manual(self, objeto) -> None:
        if isinstance(objeto, PokemonServer):
            self._pokemons_ids.add(int(objeto.Id)); return
        if isinstance(objeto, BauServer):
            self._baus_ids.add(int(objeto.Id)); return
        if isinstance(objeto, ItemMundoServer):
            self._itens_mundo_ids.add(int(objeto.Id)); return
        if isinstance(objeto, XpMundoServer):
            self._xp_mundo_ids.add(int(objeto.Id)); return

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
                "tick_intervalo_s": float(self._f("tick_segundos", 1.0 / 30.0)),
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
            elif subt == "item_mundo":
                self._itens_mundo_ids.add(int(obj.Id))
            elif subt == "xp_mundo":
                self._xp_mundo_ids.add(int(obj.Id))

        self._pokemons_ids = {oid for oid in self._pokemons_ids if isinstance(BANCO_DADOS.obter_objeto(oid), PokemonServer)}
        self._baus_ids = {oid for oid in self._baus_ids if isinstance(BANCO_DADOS.obter_objeto(oid), BauServer)}
        self._itens_mundo_ids = {oid for oid in self._itens_mundo_ids if isinstance(BANCO_DADOS.obter_objeto(oid), ItemMundoServer)}
        self._xp_mundo_ids = {oid for oid in self._xp_mundo_ids if isinstance(BANCO_DADOS.obter_objeto(oid), XpMundoServer)}

    def _limpar_janela_spawns(self) -> None:
        limite = max(1, self._tick_contador - 200)
        while self._spawns_pokemon_ultimos_200 and self._spawns_pokemon_ultimos_200[0] <= limite:
            self._spawns_pokemon_ultimos_200.popleft()
        while self._spawns_bau_ultimos_200 and self._spawns_bau_ultimos_200[0] <= limite:
            self._spawns_bau_ultimos_200.popleft()

    def _executar_tick(self) -> None:
        self._snapshot_tempo = self._cerebro_tempo.executar_tick(random)
        self._sincronizar_registries_com_banco()
        self._limpar_janela_spawns()
        chunks_carregados, chunks_simulados = self._calcular_chunks_carregados()
        self._chunks_carregados_tick_atual = set(chunks_carregados)

        if chunks_simulados:
            self._cerebro_pokemons.tentar_spawn(chunks_simulados)
            self._tentar_spawn_bau(chunks_simulados)

        self._cerebro_pokemons.atualizar_movimento(chunks_carregados)
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff
        self._cerebro_npcs.executar_tick(chunks_carregados, chunks_simulados, registrar_diff)
        self._cerebro_baus.executar_tick(chunks_simulados)
        self._cerebro_itens_mundo.executar_tick(chunks_carregados, chunks_simulados)
        self._cerebro_xp_mundo.executar_tick()
        self._executar_tick_capturas()
        self._cerebro_pokemons.despawn_simulado(chunks_simulados)
        self._cerebro_estruturas.executar_tick()

        for oid in list(self._movimento_estado.keys()):
            if oid not in self._pokemons_ids:
                self._movimento_estado.pop(oid, None)

    def _tentar_spawn_bau(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        if random.random() > self._f("chance_spawn_bau_por_tick", 0.015):
            return
        if len(self._spawns_bau_ultimos_200) >= self._i("limite_spawn_bau_200_ticks", 2):
            return
        if self.contagem_baus_registrados() >= self._i("limite_total_baus", 60):
            return
        limite_por_chunk = self._f("limite_total_baus_por_chunk_existente", -1.0)
        if limite_por_chunk >= 0.0:
            chunks_existentes = len(set(chunks_simulados) | set(getattr(self, "_chunks_carregados_tick_atual", set())))
            if self.contagem_baus_registrados() >= int(math.floor(max(0.0, limite_por_chunk) * max(0, chunks_existentes))):
                return

        tentativas = max(1, self._i("tentativas_spawn_bau", 5))
        chunk_tamanho = BANCO_DADOS.chunk_tamanho_unidade()
        chunk_list = list(chunks_simulados)
        random.shuffle(chunk_list)
        for _ in range(tentativas):
            if not chunk_list:
                return
            chunk = random.choice(chunk_list)
            if self._contar_baus_chunk(chunk) >= self._i("limite_baus_chunk", 1):
                continue
            x0, y0 = chunk[0] * chunk_tamanho, chunk[1] * chunk_tamanho
            px = random.uniform(x0 + 0.2, x0 + chunk_tamanho - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_tamanho - 0.2)
            dados = gerar_bau_server(random, dia_fixo=int(self._snapshot_tempo.get("dia", 0) or 0))
            raio_bau = float(dados.get("raio_colisao", 0.42) or 0.42)
            if not self._posicao_spawn_valida((px, py), raio=raio_bau):
                continue
            novo_id = BANCO_DADOS.gerar_id()
            bau = BauServer(id_objeto=novo_id, tipo_bau=str(dados.get("tipo_bau", "Comum")), itens=list(dados.get("itens", [])), posicao=(px, py), raio_colisao=raio_bau, raio_interacao=float(dados.get("raio_interacao", 0.85) or 0.85), aberto=False, quantidade_itens=int(dados.get("quantidade_itens", max(1, len(list(dados.get("itens", [])))))), tamanho_tiles=float(dados.get("tamanho_tiles", 1.10) or 1.10))
            BANCO_DADOS.inserir_objeto(bau)
            self._baus_ids.add(int(bau.Id))
            self._spawns_bau_ultimos_200.append(self._tick_contador)
            registrar_diff("spawn", payload=bau.serializar(), escopo={"centro": [px, py], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau")
            return

    @staticmethod
    def _posicao_spawn_valida(pos: Vector2, raio: float) -> bool:
        px, py = float(pos[0]), float(pos[1])
        for obj in BANCO_DADOS.buscar_proximos((px, py), max(0.8, raio + 0.8)):
            subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
            tipo = str(getattr(obj, "tipo_classe", "")).strip().lower()
            if subt in {"pokemon", "bau", "player"} or tipo.startswith("estrutura"):
                rr = float(getattr(obj, "raio_colisao", 0.5) or 0.5) + float(raio)
                if ((px - float(obj.posicao[0])) ** 2 + (py - float(obj.posicao[1])) ** 2) <= (rr * rr):
                    return False
        return True

    def _executar_tick_capturas(self) -> None:
        while self._capturas_inventario_pendentes and int(self._capturas_inventario_pendentes[0].get("tick", 0) or 0) <= int(self._tick_contador):
            item = self._capturas_inventario_pendentes.popleft()
            self._adicionar_pokemon_capturado_inventario(
                int(item.get("dono_id", 0) or 0),
                item.get("pokemon_snapshot", {}) if isinstance(item.get("pokemon_snapshot"), dict) else {},
            )

    @staticmethod
    def _snapshot_pokemon_capturado(poke: PokemonServer) -> Dict[str, object]:
        estado = poke.estado_extra if isinstance(poke.estado_extra, dict) else {}
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        estado_fruta = estado.get("estado_frutificacao") if isinstance(estado.get("estado_frutificacao"), dict) else {}
        efeitos_bola = captura.get("efeitos_bola") if isinstance(captura.get("efeitos_bola"), dict) else {}

        iv_base = int(estado.get("iv", 0) or 0)
        bonus_iv = int(efeitos_bola.get("bonus_iv", 0) or 0)
        bonus_iv += int(round(iv_base * (float(efeitos_bola.get("bonus_iv_percentual", 0.0) or 0.0) / 100.0)))
        bonus_iv += int(round(iv_base * (float(estado_fruta.get("bonus_iv_percentual_captura", 0.0) or 0.0) / 100.0)))

        bonus_nivel = int(efeitos_bola.get("bonus_nivel", 0) or 0) + int(efeitos_bola.get("nivel_aumentado", 0) or 0)
        bonus_amizade = int(efeitos_bola.get("bonus_amizade", 0) or 0) + int(estado_fruta.get("bonus_amizade_captura", 0) or 0)

        bruto = {
            "id": int(getattr(poke, "Id", 0) or 0),
            "especie": str(estado.get("especie") or "Pokemon"),
            "nome": str(estado.get("nome") or estado.get("especie") or "Pokemon"),
            "nivel": int(estado.get("nivel", 1) or 1),
            "iv": int(estado.get("iv", 0) or 0),
            "subivs": dict(estado.get("subivs", {})) if isinstance(estado.get("subivs"), dict) else {},
            "stats_base": dict(estado.get("stats_base", {})) if isinstance(estado.get("stats_base"), dict) else {},
            "stats": dict(estado.get("stats", {})) if isinstance(estado.get("stats"), dict) else {},
            "altura": float(estado.get("altura", 0.0) or 0.0),
            "peso": float(estado.get("peso", 0.0) or 0.0),
            "tipos": list(estado.get("tipos", [])) if isinstance(estado.get("tipos"), list) else [],
            "grupo": str(estado.get("grupo") or ""),
            "raridade": int(estado.get("raridade", 0) or 0),
            "estagio": int(estado.get("estagio", 0) or 0),
            "code": str(estado.get("code") or ""),
            "linhagem": str(estado.get("linhagem") or ""),
            "chunk_origem": list(estado.get("chunk_origem", [])) if isinstance(estado.get("chunk_origem"), list) else [],
            "capturado_em_ms": int(time.time() * 1000),
        }
        return materializar_pokemon(bruto, efeitos_captura={"bonus_iv": bonus_iv, "bonus_nivel": bonus_nivel, "bonus_amizade": bonus_amizade})

    def _adicionar_pokemon_capturado_inventario(self, dono_id: int, pokemon_snapshot: Dict[str, object]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        usuario = BANCO_DADOS.usuario_por_objeto_id(int(dono_id))
        if not usuario:
            return
        perfil = obter_personagem_para_entrada(str(usuario)) or {}
        inventario = perfil.get("inventario") if isinstance(perfil.get("inventario"), dict) else {}
        if not self._servico_inventario.adicionar_pokemon_capturado(inventario, pokemon_snapshot, perfil):
            return

        self._servico_inventario.persistir_jogador(str(usuario), int(BANCO_DADOS.objeto_id_por_usuario(str(usuario)) or 0), inventario, registrar_diff)

    def agendar_pokemon_capturado_inventario(self, dono_id: int, poke: PokemonServer, atraso_ticks: int = 24) -> None:
        if not isinstance(poke, PokemonServer):
            return
        snapshot = self._snapshot_pokemon_capturado(poke)
        self._capturas_inventario_pendentes.append(
            {
                "tick": int(self._tick_contador + max(1, int(atraso_ticks or 1))),
                "dono_id": int(dono_id or 0),
                "pokemon_snapshot": snapshot,
            }
        )

    def registrar_lancamento_projetil(self, client_id: str, payload: Dict[str, object]) -> bool:
        return self._cerebro_projeteis.registrar_lancamento(client_id, payload)

    def registrar_drop_item_mundo(self, client_id: str, payload: Dict[str, object]) -> bool:
        return self._cerebro_itens_mundo.registrar_drop(client_id, payload)

    def registrar_coleta_estrutura(self, client_id: str, payload: Dict[str, object]) -> bool:
        return self._cerebro_estruturas.registrar_coleta(client_id, payload)

    def registrar_interacao_bau(self, client_id: str, payload: Dict[str, object]) -> bool:
        return self._cerebro_baus.registrar_interacao(client_id, payload)

    def registrar_inicio_interacao_npc(self, client_id: str, npc_id: int) -> tuple[bool, str]:
        return self._cerebro_npcs.registrar_inicio_interacao(client_id, int(npc_id))

    def registrar_fim_interacao_npc(self, client_id: str, npc_id: int) -> tuple[bool, str]:
        return self._cerebro_npcs.registrar_fim_interacao(client_id, int(npc_id))

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


CEREBRO = CerebroCentral()
