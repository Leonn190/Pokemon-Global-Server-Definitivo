"""Subcérebro de pokémons (lógica real preservada)."""

from __future__ import annotations

import random
from typing import Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import PokemonServer, BauServer
from SimuladorServerJogo.Geradores.GeradorPokemon import gerar_pokemon_server

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]
_DIRECOES_8: Tuple[Vector2, ...] = (
    (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
    (0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, 0.7071), (-0.7071, -0.7071),
)


class CerebroPokemons:
    def __init__(self, core) -> None:
        self._core = core

    def tentar_spawn(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        if random.random() > self._core._f("chance_spawn_pokemon_por_tick", 0.02):
            return
        if len(self._core._spawns_pokemon_ultimos_100) >= self._core._i("limite_spawn_pokemon_100_ticks", 4):
            return
        if self._core.contagem_pokemons_registrados() >= self._core._i("limite_total_pokemons", 100):
            return

        tentativas = max(1, self._core._i("tentativas_spawn_pokemon", 5))
        chunk_tamanho = BANCO_DADOS.chunk_tamanho_unidade()
        chunk_list = list(chunks_simulados)
        random.shuffle(chunk_list)
        for _ in range(tentativas):
            if not chunk_list:
                return
            chunk = random.choice(chunk_list)
            if self._core._contar_pokemons_chunk(chunk) >= self._core._i("limite_pokemons_chunk", 2):
                continue
            x0, y0 = chunk[0] * chunk_tamanho, chunk[1] * chunk_tamanho
            px = random.uniform(x0 + 0.2, x0 + chunk_tamanho - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_tamanho - 0.2)
            if not self._core._posicao_spawn_valida((px, py), raio=0.45):
                continue
            novo_id = BANCO_DADOS.gerar_id()
            poke = gerar_pokemon_server(novo_id=novo_id, posicao=(px, py), chunk_xy=chunk)
            BANCO_DADOS.inserir_objeto(poke)
            self._core._pokemons_ids.add(int(poke.Id))
            self._core._spawns_pokemon_ultimos_100.append(self._core._tick_contador)
            registrar_diff("spawn", payload=poke.serializar(), escopo={"centro": [px, py], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            return

    def atualizar_movimento(self, chunks_carregados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        chance_inicio = self._core._f("chance_movimento_pokemon_por_tick", 0.008)
        cooldown_min = self._core._i("intervalo_minimo_apos_movimento_ticks", 40)
        duracao_max = self._core._i("tempo_maximo_movimento_ticks", 150)
        velocidade = self._core._f("velocidade_base_pokemon_tiles_s", 3.0)
        passo = velocidade / 30.0

        for oid in list(self._core._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._core._pokemons_ids.discard(oid)
                continue
            cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
            if cap:
                liberar_tick = int(cap.get("liberar_movimento_tick", 0) or 0)
                resultado_cap = str(cap.get("resultado", "pendente") or "pendente").strip().lower()
                if bool(cap.get("captura_pendente", False)) and liberar_tick > 0 and int(self._core._tick_contador) >= liberar_tick and resultado_cap != "sucesso":
                    poke.estado_extra["captura"] = {
                        "captura_pendente": False,
                        "checks_total": 3,
                        "checagens": [],
                        "resultado": "pendente",
                        "capturador_id": 0,
                        "dono_id": 0,
                        "token_arremesso": "",
                        "bola_nome": "",
                        "bola_posicao": [float(poke.posicao[0]), float(poke.posicao[1])],
                        "retorno_inicio": None,
                        "retorno_destino": None,
                        "poder_total": 0.0,
                        "chance_escape": 0.0,
                        "captura_garantida": False,
                        "liberar_movimento_tick": 0,
                        "pokemon_colisao_ativa": True,
                        "pokemon_interacao_ativa": True,
                        "efeitos_bola": {},
                    }
                    poke.estado_extra["captura_fase"] = "nenhuma"
                    cap = poke.estado_extra["captura"]
                    BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": poke.estado_extra})
                    registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120}, objeto_id=poke.Id, autor="server", categoria="pokemon")

            cooldown_ate = int(poke.estado_extra.get("cooldown_movimento_ate_tick", 0) or 0)
            if int(self._core._tick_contador) < cooldown_ate:
                continue
            if bool(cap.get("captura_pendente", False)):
                continue

            estado = self._core._movimento_estado.get(oid)
            if not isinstance(estado, dict):
                estado = {"dir": (0.0, 0.0), "restante": 0, "cooldown_ate": 0}
                self._core._movimento_estado[oid] = estado

            if int(estado.get("restante", 0) or 0) > 0:
                dx, dy = estado.get("dir", (0.0, 0.0))
                destino = (float(poke.posicao[0]) + float(dx) * passo, float(poke.posicao[1]) + float(dy) * passo)
                if self._colisao_movimento_pokemon(oid, destino, poke.raio_colisao):
                    estado["restante"] = 0
                    estado["cooldown_ate"] = self._core._tick_contador + cooldown_min
                    continue
                poke.definir_posicao(destino[0], destino[1])
                BANCO_DADOS.atualizar_objeto(poke.Id, {"posicao": [poke.posicao[0], poke.posicao[1]]})
                estado["restante"] = int(estado.get("restante", 0) or 0) - 1
                if int(estado.get("restante", 0) or 0) <= 0:
                    estado["cooldown_ate"] = self._core._tick_contador + cooldown_min
                registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 40}, objeto_id=poke.Id, autor="server", categoria="pokemon")
                continue

            if self._core._tick_contador < int(estado.get("cooldown_ate", 0) or 0):
                continue
            if BANCO_DADOS.chunk_da_posicao(poke.posicao) not in chunks_carregados:
                continue
            if random.random() > chance_inicio:
                continue

            estado["dir"] = random.choice(_DIRECOES_8)
            estado["restante"] = random.randint(max(10, cooldown_min), max(10, duracao_max))

    @staticmethod
    def _colisao_movimento_pokemon(pokemon_id: int, destino: Vector2, raio: float) -> bool:
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

    def despawn_simulado(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        chance_poke = self._core._f("chance_despawn_pokemon_simulado_por_tick", 0.003)
        chance_bau = self._core._f("chance_despawn_bau_simulado_por_tick", 0.002)

        candidatos_poke = []
        for oid in list(self._core._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._core._pokemons_ids.discard(oid); continue
            if BANCO_DADOS.chunk_da_posicao(poke.posicao) in chunks_simulados:
                candidatos_poke.append((oid, poke))
        if candidatos_poke and random.random() <= chance_poke:
            oid, _ = random.choice(candidatos_poke)
            rem = BANCO_DADOS.remover_objeto(oid)
            self._core._pokemons_ids.discard(oid)
            self._core._movimento_estado.pop(oid, None)
            if rem is not None:
                registrar_diff("despawn", payload={"id": rem.Id, "motivo": "simulado"}, escopo={"centro": [rem.posicao[0], rem.posicao[1]], "raio": 80}, objeto_id=rem.Id, autor="server", categoria="pokemon")

        candidatos_bau = []
        for oid in list(self._core._baus_ids):
            bau = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(bau, BauServer):
                self._core._baus_ids.discard(oid); continue
            if bool(bau.estado_extra.get("aberto", False)):
                continue
            if BANCO_DADOS.chunk_da_posicao(bau.posicao) in chunks_simulados:
                candidatos_bau.append((oid, bau))
        if candidatos_bau and random.random() <= chance_bau:
            oid, _ = random.choice(candidatos_bau)
            rem = BANCO_DADOS.remover_objeto(oid)
            self._core._baus_ids.discard(oid)
            if rem is not None:
                registrar_diff("despawn", payload={"id": rem.Id, "motivo": "simulado"}, escopo={"centro": [rem.posicao[0], rem.posicao[1]], "raio": 80}, objeto_id=rem.Id, autor="server", categoria="bau")
