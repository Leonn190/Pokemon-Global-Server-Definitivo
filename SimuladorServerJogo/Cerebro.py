"""Cérebro do servidor: controla tick, chunks simulados/visíveis e ciclo de pokémons."""

from __future__ import annotations

import json
import random
import threading
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.GeradorPokemon import GERADOR_POKEMON_SERVER
from SimuladorServerJogo.ObjetosMundoServer import PokemonServer

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]
ARQUIVO_REGRAS = Path(__file__).resolve().parent / "RegrasCerebro.json"


class CerebroServer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ultimo_tick = 0.0
        self._ativador_id = ""
        self._players_ativos: Dict[str, Vector2] = {}
        self._pokemons_ids: Set[int] = set()
        self._regras = self._carregar_regras()

    def _carregar_regras(self) -> Dict[str, object]:
        padrao = {
            "tick_segundos": 0.2,
            "anel_render_chunks": 7,
            "anel_simulado_chunks": 13,
            "chance_spawn_por_tick": 0.35,
            "chance_mover_por_tick": 0.65,
            "max_pokemon_por_chunk_simulado": 3,
            "max_pokemon_por_chunk_carregado": 0.12,
            "maior_vetor_movimento_pokemon": 3.0,
            "velocidade_pokemon_tiles_s": 9.0,
            "raio_colisao_pokemon": 0.45,
            "tentativas_spawn_chunk": 12,
            "tiles_bloqueados": [0, 1, 2],
        }
        if not ARQUIVO_REGRAS.exists():
            return padrao
        try:
            raw = json.loads(ARQUIVO_REGRAS.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                padrao.update(raw)
        except Exception:
            pass
        return padrao

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
            if self._players_ativos:
                return
            self._limpar_pokemons_dinamicos()

    def desligar_servidor(self) -> None:
        with self._lock:
            self._players_ativos.clear()
            self._ativador_id = ""
            self._limpar_pokemons_dinamicos()

    def _limpar_pokemons_dinamicos(self) -> None:
        from SimuladorServerJogo.Ativador import registrar_diff

        for oid in list(self._pokemons_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if isinstance(obj, PokemonServer):
                obj.sumir()
            removido = BANCO_DADOS.remover_objeto(oid)
            if removido is not None:
                registrar_diff(
                    "despawn",
                    payload={"id": removido.Id},
                    escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 100},
                    objeto_id=removido.Id,
                )
        self._pokemons_ids.clear()

    def processar_ativacao(self, client_id: str, posicao_camera: Vector2) -> Dict[str, object]:
        with self._lock:
            client_id = str(client_id)
            if not self._ativador_id:
                self._ativador_id = client_id
            self._players_ativos[client_id] = (float(posicao_camera[0]), float(posicao_camera[1]))
            is_ativador = self._ativador_id == client_id

            agora = time.monotonic()
            tick_s = max(0.05, self._f("tick_segundos", 0.2))
            tick_executado = False
            if is_ativador and (agora - self._ultimo_tick) >= tick_s:
                self._executar_tick()
                self._ultimo_tick = agora
                tick_executado = True

            chunks_visiveis, chunks_simulados = self._calcular_chunks_carregados()
            return {
                "ativador": self._ativador_id,
                "is_ativador": is_ativador,
                "tick_executado": tick_executado,
                "tick_intervalo_s": tick_s,
                "chunks_visiveis": len(chunks_visiveis),
                "chunks_simulados": len(chunks_simulados),
                "players_ativos": len(self._players_ativos),
                "anel_render_chunks": self._i("anel_render_chunks", 7),
                "anel_simulado_chunks": self._i("anel_simulado_chunks", 13),
                "max_pokemons": self._max_pokemons_permitidos(len(chunks_visiveis | chunks_simulados)),
                "maior_vetor_movimento_pokemon": self._f("maior_vetor_movimento_pokemon", 3.0),
            }

    def _obter_colisor_global(self):
        bloqueados = {int(v) for v in (self._regras.get("tiles_bloqueados") or [0, 1, 2])}

        def _colide(destino: Vector2, raio: float) -> bool:
            px, py = float(destino[0]), float(destino[1])
            largura, altura = BANCO_DADOS.limites_mundo()
            if px < 0.0 or py < 0.0 or px >= float(largura) or py >= float(altura):
                return False
            gx = int(px)
            gy = int(py)
            grid = BANCO_DADOS._grid
            if 0 <= gy < len(grid) and 0 <= gx < len(grid[gy]):
                tile = int(grid[gy][gx])
                if tile in bloqueados:
                    return False
            proximos = BANCO_DADOS.buscar_proximos((px, py), max(0.25, float(raio) + 0.55))
            for obj in proximos:
                if str(getattr(obj, "tipo_classe", "")).startswith("estrutura"):
                    ox, oy = obj.posicao
                    rr = float(getattr(obj, "raio_colisao", 0.5)) + float(raio)
                    if ((px - ox) ** 2 + (py - oy) ** 2) <= (rr * rr):
                        return False
            return True

        return _colide

    def _executar_tick(self) -> None:
        chunks_visiveis, chunks_simulados = self._calcular_chunks_carregados()
        chunks_carregados = chunks_visiveis | chunks_simulados

        pokemons: List[PokemonServer] = []
        for oid in list(self._pokemons_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if isinstance(obj, PokemonServer):
                pokemons.append(obj)
            else:
                self._pokemons_ids.discard(oid)

        max_total = self._max_pokemons_permitidos(len(chunks_carregados))
        chance_spawn = max(0.0, min(1.0, self._f("chance_spawn_por_tick", 0.35)))
        if chunks_simulados and len(pokemons) < max_total and random.random() < chance_spawn:
            chunk = random.choice(list(chunks_simulados))
            max_por_chunk = max(1, self._i("max_pokemon_por_chunk_simulado", 3))
            if self._contar_pokemons_chunk(chunk) < max_por_chunk:
                self._spawn_pokemon(chunk)

        chance_mover = max(0.0, min(1.0, self._f("chance_mover_por_tick", 0.65)))
        for poke in pokemons:
            if random.random() < chance_mover:
                self._mover_pokemon(poke, chunks_carregados)

    def _max_pokemons_permitidos(self, total_chunks_carregados: int) -> int:
        fator = max(0.01, self._f("max_pokemon_por_chunk_carregado", 0.12))
        return max(1, int(total_chunks_carregados * fator))

    def _mover_pokemon(self, poke: PokemonServer, chunks_carregados: Set[Chunk]) -> None:
        max_step = max(0.2, self._f("maior_vetor_movimento_pokemon", 3.0) * 0.7)
        dx = random.uniform(-max_step, max_step)
        dy = random.uniform(-max_step, max_step)
        if abs(dx) < 1e-8 and abs(dy) < 1e-8:
            return

        destino = (float(poke.posicao[0]) + dx, float(poke.posicao[1]) + dy)
        chunk_destino = BANCO_DADOS.chunk_da_posicao(destino)
        if chunk_destino not in chunks_carregados:
            return

        colisor = self._obter_colisor_global()
        velocidade_base = max(0.1, self._f("velocidade_pokemon_tiles_s", 9.0) * 0.7)
        if poke.mover((dx, dy), colisor_cb=colisor, velocidade_tiles_s=velocidade_base):
            BANCO_DADOS.atualizar_objeto(poke.Id, {"posicao": [poke.posicao[0], poke.posicao[1]]})
            from SimuladorServerJogo.Ativador import registrar_diff

            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 40}, objeto_id=poke.Id)

    def _spawn_pokemon(self, chunk: Chunk) -> None:
        chunk_sz = BANCO_DADOS.chunk_tamanho_unidade()
        x0, y0 = chunk[0] * chunk_sz, chunk[1] * chunk_sz
        tentativas = max(1, self._i("tentativas_spawn_chunk", 12))
        raio = max(0.1, self._f("raio_colisao_pokemon", 0.45))
        escolhido = None
        colisor = self._obter_colisor_global()
        while tentativas > 0:
            tentativas -= 1
            px = random.uniform(x0 + 0.2, x0 + chunk_sz - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_sz - 0.2)
            if colisor((px, py), raio):
                escolhido = (px, py)
                break
        if escolhido is None:
            return

        novo_id = BANCO_DADOS.gerar_id()
        poke = GERADOR_POKEMON_SERVER.gerar(novo_id=novo_id, posicao=escolhido, chunk_xy=chunk)
        poke.raio_colisao = raio
        BANCO_DADOS.inserir_objeto(poke)
        self._pokemons_ids.add(poke.Id)
        from SimuladorServerJogo.Ativador import registrar_diff

        registrar_diff("spawn", payload=poke.serializar(), escopo={"centro": [escolhido[0], escolhido[1]], "raio": 80}, objeto_id=poke.Id)

    def _contar_pokemons_chunk(self, chunk: Chunk) -> int:
        c = 0
        for oid in self._pokemons_ids:
            obj = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(obj, PokemonServer):
                continue
            if BANCO_DADOS.chunk_da_posicao(obj.posicao) == chunk:
                c += 1
        return c

    def _calcular_chunks_carregados(self):
        chunks_visiveis: Set[Chunk] = set()
        chunks_simulados: Set[Chunk] = set()

        render_half = max(0, self._i("anel_render_chunks", 7) // 2)
        sim_half = max(render_half, self._i("anel_simulado_chunks", 13) // 2)

        for pos in self._players_ativos.values():
            centro = BANCO_DADOS.chunk_da_posicao(pos)
            for dx in range(-render_half, render_half + 1):
                for dy in range(-render_half, render_half + 1):
                    chunks_visiveis.add(BANCO_DADOS.normalizar_chunk((centro[0] + dx, centro[1] + dy)))

            for dx in range(-sim_half, sim_half + 1):
                for dy in range(-sim_half, sim_half + 1):
                    ch = BANCO_DADOS.normalizar_chunk((centro[0] + dx, centro[1] + dy))
                    if ch not in chunks_visiveis:
                        chunks_simulados.add(ch)

        return chunks_visiveis, chunks_simulados


CEREBRO = CerebroServer()
