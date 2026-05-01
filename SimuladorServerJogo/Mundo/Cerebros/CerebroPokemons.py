"""Subcérebro de pokémons (lógica real preservada)."""

from __future__ import annotations

import random
import math
from typing import List, Optional, Set, Tuple

from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.ObjetosMundoServer import PokemonServer, BauServer
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import gerar_pokemon_server

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]
_DIRECOES_8: Tuple[Vector2, ...] = (
    (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
    (0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, 0.7071), (-0.7071, -0.7071),
)


class CerebroPokemons:
    def __init__(self, core) -> None:
        self._core = core

    def registrar_falha_captura(self, poke: PokemonServer) -> bool:
        if not isinstance(poke, PokemonServer):
            return False
        extra = poke.estado_extra if isinstance(poke.estado_extra, dict) else {}
        falhas = int(extra.get("tentativas_falhas_captura", 0) or 0) + 1
        extra["tentativas_falhas_captura"] = int(falhas)
        dificuldade_antes = float(extra.get("dificuldade_captura", extra.get("dificuldade_captura_base", 50.0)) or 50.0)
        personalidade = str(extra.get("personalidade_mundo") or "").strip().lower()

        if personalidade == "bravo" and falhas >= 1:
            return self.tornar_irritado(poke, "personalidade_bravo", registrar=False)

        if bool(extra.get("esta_irritado", False)):
            extra["dificuldade_captura"] = float(self._core._f("captura_falhas_dificuldade_irritado_fixa", 130.0))
            return True

        incremento = float(self._core._f("captura_falhas_incremento_dificuldade_por_falha", 3.0))
        dificuldade_nova = dificuldade_antes + incremento
        extra["dificuldade_captura"] = round(float(dificuldade_nova), 2)

        limiar = float(self._core._f("captura_falhas_limiar_dificuldade_irritado", 85.0))
        limite_falhas = int(self._core._i("captura_falhas_falhas_para_irritar", 5))
        if dificuldade_antes >= limiar or dificuldade_nova >= limiar:
            return self.tornar_irritado(poke, "dificuldade_alta", registrar=False)
        if falhas >= limite_falhas:
            return self.tornar_irritado(poke, "falhas_captura", registrar=False)
        return True

    def tornar_irritado(self, poke: PokemonServer, motivo: str, registrar: bool = True) -> bool:
        if not isinstance(poke, PokemonServer):
            return False
        extra = poke.estado_extra if isinstance(poke.estado_extra, dict) else {}
        extra["esta_irritado"] = True
        extra["motivo_irritado"] = str(motivo or "")
        extra["dificuldade_captura"] = float(self._core._f("captura_falhas_dificuldade_irritado_fixa", 130.0))
        if registrar:
            from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

            BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": extra})
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120}, objeto_id=poke.Id, autor="server", categoria="pokemon")
        return True

    def _players_ativos(self) -> List[Tuple[str, Vector2]]:
        players: List[Tuple[str, Vector2]] = []
        for client_id, fallback in list(getattr(self._core, "_players_ativos", {}).items()):
            pos = self._core._posicao_central_cliente(client_id, fallback)
            if pos is not None:
                players.append((str(client_id), (float(pos[0]), float(pos[1]))))
        return players

    @staticmethod
    def _player_mais_proximo(posicao: Vector2, players: List[Tuple[str, Vector2]], raio: float) -> Optional[Tuple[str, Vector2, float]]:
        melhor = None
        px, py = float(posicao[0]), float(posicao[1])
        raio2 = float(raio) * float(raio)
        for player_id, pos in players:
            dx = float(pos[0]) - px
            dy = float(pos[1]) - py
            d2 = (dx * dx) + (dy * dy)
            if d2 > raio2:
                continue
            dist = math.sqrt(d2)
            if melhor is None or dist < melhor[2]:
                melhor = (player_id, pos, dist)
        return melhor

    @staticmethod
    def _direcao_para(origem: Vector2, destino: Vector2, inverter: bool = False) -> Vector2:
        dx = float(destino[0]) - float(origem[0])
        dy = float(destino[1]) - float(origem[1])
        if inverter:
            dx, dy = -dx, -dy
        n = math.hypot(dx, dy)
        if n <= 1e-6:
            return random.choice(_DIRECOES_8)
        return (dx / n, dy / n)

    def tentar_spawn(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        if random.random() >= self._core._f("chance_spawn_pokemon_por_tick", 0.02):
            return
        if len(self._core._spawns_pokemon_ultimos_200) >= self._core._i("limite_spawn_pokemon_200_ticks", 4):
            return
        if self._core.contagem_pokemons_registrados() >= self._core._i("limite_total_pokemons", 100):
            return
        limite_por_chunk = self._core._f("limite_total_pokemons_por_chunk_existente", -1.0)
        if limite_por_chunk >= 0.0:
            chunks_existentes = len(set(chunks_simulados) | set(getattr(self._core, "_chunks_carregados_tick_atual", set())))
            if self._core.contagem_pokemons_registrados() >= int(math.floor(max(0.0, limite_por_chunk) * max(0, chunks_existentes))):
                return

        tentativas = int(self._core._i("tentativas_spawn_pokemon", 5))
        if tentativas <= 0:
            return
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
            self._core._spawns_pokemon_ultimos_200.append(self._core._tick_contador)
            registrar_diff("spawn", payload=poke.serializar(), escopo={"centro": [px, py], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            return

    def atualizar_movimento(self, chunks_carregados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        chance_inicio = self._core._f("chance_movimento_pokemon_por_tick", 0.008)
        cooldown_min = self._core._i("intervalo_minimo_apos_movimento_ticks", 40)
        duracao_max = self._core._i("tempo_maximo_movimento_ticks", 150)
        velocidade = self._core._f("velocidade_base_pokemon_tiles_s", 3.0)
        passo = velocidade / 30.0
        players_ativos = self._players_ativos()

        for oid in list(self._core._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._core._pokemons_ids.discard(oid)
                continue
            cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
            if cap:
                liberar_tick = int(cap.get("liberar_movimento_tick", 0) or 0)
                if bool(cap.get("captura_pendente", False)) and liberar_tick > 0 and int(self._core._tick_contador) >= liberar_tick:
                    cap["captura_pendente"] = False
                    cap["pokemon_colisao_ativa"] = True
                    cap["pokemon_interacao_ativa"] = True
                    poke.estado_extra["captura_fase"] = "nenhuma"
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
                passo_atual = passo * max(0.1, float(estado.get("vel_mult", 1.0) or 1.0))
                destino = (float(poke.posicao[0]) + float(dx) * passo_atual, float(poke.posicao[1]) + float(dy) * passo_atual)
                if self._colisao_movimento_pokemon(oid, destino, poke.raio_colisao):
                    estado["restante"] = 0
                    estado["cooldown_ate"] = self._core._tick_contador + int(estado.get("cooldown_ticks", cooldown_min) or cooldown_min)
                    continue
                poke.definir_posicao(destino[0], destino[1])
                BANCO_DADOS.atualizar_objeto(poke.Id, {"posicao": [poke.posicao[0], poke.posicao[1]]})
                estado["restante"] = int(estado.get("restante", 0) or 0) - 1
                if int(estado.get("restante", 0) or 0) <= 0:
                    estado["cooldown_ate"] = self._core._tick_contador + int(estado.get("cooldown_ticks", cooldown_min) or cooldown_min)
                registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 40}, objeto_id=poke.Id, autor="server", categoria="pokemon")
                continue

            if self._core._tick_contador < int(estado.get("cooldown_ate", 0) or 0):
                continue
            if BANCO_DADOS.chunk_da_posicao(poke.posicao) not in chunks_carregados:
                continue

            personalidade = str(poke.estado_extra.get("personalidade_mundo") or "").strip().lower()
            irritado = bool(poke.estado_extra.get("esta_irritado", False))
            if personalidade == "super_bravo" and not irritado:
                raio_ativacao = float(self._core._f("personalidade_mundo_super_bravo_raio_ativacao_tiles", 7.0))
                if self._player_mais_proximo(poke.posicao, players_ativos, raio_ativacao) is not None:
                    self.tornar_irritado(poke, "personalidade_super_bravo")
                    irritado = True

            chance_atual = float(chance_inicio)
            cooldown_atual = int(cooldown_min)
            direcao_forcada = None
            restante_forcado = None
            vel_mult = 1.0

            if irritado:
                busca = float(self._core._f("personalidade_mundo_irritado_raio_busca_tiles", 6.0))
                vel_mult = float(self._core._f("personalidade_mundo_irritado_multiplicador_velocidade", 1.20))
                if personalidade == "super_bravo":
                    busca = float(self._core._f("personalidade_mundo_super_bravo_raio_busca_irritado_tiles", 9.0))
                    vel_mult = float(self._core._f("personalidade_mundo_super_bravo_multiplicador_velocidade_irritado", 1.35))
                alvo = self._player_mais_proximo(poke.posicao, players_ativos, busca)
                if alvo is not None:
                    poke.estado_extra["alvo_player_id"] = str(alvo[0])
                    poke.estado_extra["comportamento_mundo"] = "perseguindo"
                    direcao_forcada = self._direcao_para(poke.posicao, alvo[1])
                chance_atual *= float(self._core._f("personalidade_mundo_irritado_chance_movimento_mult", 2.0))
                cooldown_atual = max(1, int(round(cooldown_min * float(self._core._f("personalidade_mundo_irritado_cooldown_movimento_mult", 0.70)))))
            elif personalidade == "curioso":
                raio = float(self._core._f("personalidade_mundo_curioso_raio_percepcao_tiles", 5.0))
                seguro = float(self._core._f("personalidade_mundo_curioso_distancia_segura_tiles", 2.4))
                alvo = self._player_mais_proximo(poke.posicao, players_ativos, raio)
                if alvo is not None and float(alvo[2]) > seguro:
                    direcao_forcada = self._direcao_para(poke.posicao, alvo[1])
                    vel_mult = float(self._core._f("personalidade_mundo_curioso_multiplicador_velocidade", 0.95))
                    restante_forcado = max(1, int((float(alvo[2]) - seguro) / max(0.001, passo * vel_mult)))
                    poke.estado_extra["comportamento_mundo"] = "curioso"
            elif personalidade == "medroso":
                raio = float(self._core._f("personalidade_mundo_medroso_raio_percepcao_tiles", 5.5))
                alvo = self._player_mais_proximo(poke.posicao, players_ativos, raio)
                if alvo is not None:
                    direcao_forcada = self._direcao_para(poke.posicao, alvo[1], inverter=True)
                    vel_mult = float(self._core._f("personalidade_mundo_medroso_multiplicador_velocidade", 1.05))
                    poke.estado_extra["comportamento_mundo"] = "fugindo"

            if direcao_forcada is None and random.random() >= chance_atual:
                continue

            estado["dir"] = direcao_forcada or random.choice(_DIRECOES_8)
            estado["vel_mult"] = float(vel_mult)
            estado["cooldown_ticks"] = int(cooldown_atual)
            restante_min = int(cooldown_atual)
            restante_max = int(duracao_max)
            if restante_max < restante_min:
                restante_min, restante_max = restante_max, restante_min
            if restante_forcado is not None:
                estado["restante"] = max(1, min(int(restante_forcado), int(restante_max)))
            else:
                estado["restante"] = random.randint(restante_min, restante_max)

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
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        chance_poke = self._core._f("chance_despawn_pokemon_simulado_por_tick", 0.003)
        chance_bau = self._core._f("chance_despawn_bau_simulado_por_tick", 0.002)

        candidatos_poke = []
        for oid in list(self._core._pokemons_ids):
            poke = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(poke, PokemonServer):
                self._core._pokemons_ids.discard(oid); continue
            if BANCO_DADOS.chunk_da_posicao(poke.posicao) in chunks_simulados:
                candidatos_poke.append((oid, poke))
        if candidatos_poke and random.random() < chance_poke:
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
        if candidatos_bau and random.random() < chance_bau:
            oid, _ = random.choice(candidatos_bau)
            rem = BANCO_DADOS.remover_objeto(oid)
            self._core._baus_ids.discard(oid)
            if rem is not None:
                registrar_diff("despawn", payload={"id": rem.Id, "motivo": "simulado"}, escopo={"centro": [rem.posicao[0], rem.posicao[1]], "raio": 80}, objeto_id=rem.Id, autor="server", categoria="bau")
