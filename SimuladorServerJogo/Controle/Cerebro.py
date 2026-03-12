"""Cérebro do servidor: controla tick, chunks simulados/visíveis e ciclo de pokémons."""

from __future__ import annotations

import random
import threading
import time
from typing import Dict, List, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Geradores.GeradorPokemon import gerar_pokemon_server
from SimuladorServerJogo.Geradores.GeradorBaus import gerar_bau_server
from SimuladorServerJogo.Controle.ObjetosMundoServer import PokemonServer, BauServer, ProjetilServer
from SimuladorServerJogo.Logica.AutoridadeCaptura import resolver_fruta, resolver_captura, coletar_eventos_captura_agendada
from SimuladorServerJogo.Regras.Loader import carregar_regras_cerebro

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]


class CerebroServer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ultimo_tick = 0.0
        self._ativador_id = ""
        self._players_ativos: Dict[str, Vector2] = {}
        self._pokemons_ids: Set[int] = set()
        self._baus_ids: Set[int] = set()
        self._projeteis_ids: Set[int] = set()
        self._regras = self._carregar_regras()

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
            if self._players_ativos:
                return
            self._limpar_pokemons_dinamicos()

    def desligar_servidor(self) -> None:
        with self._lock:
            self._players_ativos.clear()
            self._ativador_id = ""
            self._limpar_pokemons_dinamicos()

    def _limpar_pokemons_dinamicos(self) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

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
                    categoria="projetil",
                )
        self._pokemons_ids.clear()
        self._baus_ids.clear()
        self._projeteis_ids.clear()

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
        velocidade = float(payload.get("velocidade_tiles_s", 7.0) or 7.0)
        if subtipo == "fruta":
            velocidade = 6.0
            alcance = 6.0
        elif variante == "sniperball":
            velocidade = 8.0
            alcance = 9.0
        elif variante == "fastball":
            velocidade = 10.0
            alcance = 7.0
        else:
            velocidade = 7.0
            alcance = 7.0

        p0 = payload.get("pos_inicial") if isinstance(payload.get("pos_inicial"), (list, tuple)) and len(payload.get("pos_inicial")) == 2 else [dono_obj.posicao[0], dono_obj.posicao[1]]
        p1 = payload.get("pos_final") if isinstance(payload.get("pos_final"), (list, tuple)) and len(payload.get("pos_final")) == 2 else list(p0)
        dx = float(p1[0]) - float(p0[0])
        dy = float(p1[1]) - float(p0[1])
        dist = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / dist, dy / dist
        dist_final = min(float(alcance), dist)
        destino = [float(p0[0]) + ux * dist_final, float(p0[1]) + uy * dist_final]

        cliente_ms = int(payload.get("instante_cliente_ms", 0) or 0)
        agora_ms = int(time.time() * 1000)
        tempo_total = max(0.05, dist_final / max(0.1, velocidade))
        atraso = max(0.0, (agora_ms - cliente_ms) / 1000.0) if cliente_ms > 0 else 0.0
        rewind = min(tempo_total * 0.15, atraso)

        fator_rewind = min(0.05, (rewind / tempo_total) * 0.05 if tempo_total > 1e-6 else 0.0)
        velocidade_remota = velocidade * (1.0 + fator_rewind)

        from SimuladorServerJogo.Rotas.Ativador import registrar_diff
        registrar_diff(
            "spawn",
            payload={
                "token": token,
                "subtipo_projetil": subtipo,
                "variante": variante,
                "item": str(payload.get("item") or ""),
                "item_base_id": str(payload.get("item_base_id") or ""),
                "pos_inicial": [float(p0[0]), float(p0[1])],
                "pos_final": [float(destino[0]), float(destino[1])],
                "velocidade_tiles_s": velocidade_remota,
                "dono_id": int(dono_id),
                "dono_nome": str(payload.get("dono_nome") or client_id),
            },
            escopo={"centro": [float(p0[0]), float(p0[1])], "raio": 120},
            objeto_id=int(dono_id),
            autor="server",
            categoria="projetil_lancamento",
            base=False,
        )

        inicio_sim = [float(p0[0]) + ux * velocidade * rewind, float(p0[1]) + uy * velocidade * rewind]
        impacto = self._simular_lancamento_servidor(tuple(inicio_sim), tuple(destino), subtipo=subtipo, dono_id=dono_id)
        if impacto is None:
            return True

        alvo = impacto
        if subtipo == "fruta":
            ret = resolver_fruta(alvo, str(payload.get("item") or variante), contexto={"dono_id": dono_id})
            BANCO_DADOS.atualizar_objeto(alvo.Id, {"estado": alvo.estado_extra})
            registrar_diff("update", payload=alvo.serializar(), escopo={"centro": [alvo.posicao[0], alvo.posicao[1]], "raio": 120}, objeto_id=alvo.Id, autor="server", categoria="pokemon", base=False)
            return True

        ret_captura = resolver_captura(alvo, str(payload.get("item") or variante), contexto={"dono_id": dono_id, "dono_posicao": [dono_obj.posicao[0], dono_obj.posicao[1]], "distancia_arremesso_tiles": dist_final, "tentativas_falhas_anteriores": int(alvo.estado_extra.get("tentativas_falhas_captura", 0) or 0), "bioma": str(alvo.estado_extra.get("bioma", "")), "servidor_agora_ms": agora_ms, "maestria": self._maestria_player(dono_id)})
        if bool(ret_captura.get("iniciada", False)):
            BANCO_DADOS.atualizar_objeto(alvo.Id, {"estado": alvo.estado_extra})
            registrar_diff("update", payload=alvo.serializar(), escopo={"centro": [alvo.posicao[0], alvo.posicao[1]], "raio": 120}, objeto_id=alvo.Id, autor="server", categoria="pokemon", base=False)
        return True

    def _simular_lancamento_servidor(self, origem: Vector2, destino: Vector2, subtipo: str, dono_id: int):
        passos = max(4, int(math.hypot(destino[0] - origem[0], destino[1] - origem[1]) * 12.0))
        for i in range(1, passos + 1):
            t = float(i) / float(passos)
            px = float(origem[0]) + (float(destino[0]) - float(origem[0])) * t
            py = float(origem[1]) + (float(destino[1]) - float(origem[1])) * t
            for obj in BANCO_DADOS.buscar_proximos((px, py), 0.45):
                if int(getattr(obj, "Id", 0) or 0) == int(dono_id):
                    continue
                subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
                if subt == "pokemon":
                    return obj
                if subt in {"bau", "player"} or str(getattr(obj, "tipo_classe", "")).startswith("estrutura"):
                    return None
        return None


    def registrar_spawn_manual(self, objeto) -> None:
        """Inclui objetos spawnados por comando no ciclo do cérebro."""
        if isinstance(objeto, PokemonServer):
            objeto.estado_extra["forcar_movimento_ate"] = time.monotonic() + 8.0
            self._pokemons_ids.add(int(objeto.Id))
            return
        if isinstance(objeto, BauServer):
            self._baus_ids.add(int(objeto.Id))
            return


    def executar_tick_servidor(self) -> None:
        with self._lock:
            self._executar_tick()
            self._ultimo_tick = time.monotonic()

    def processar_ativacao(self, client_id: str, posicao_camera: Vector2) -> Dict[str, object]:
        with self._lock:
            client_id = str(client_id)
            if not self._ativador_id:
                self._ativador_id = client_id
            self._players_ativos[client_id] = (float(posicao_camera[0]), float(posicao_camera[1]))
            is_ativador = self._ativador_id == client_id

            tick_s = (1.0 / 30.0)
            tick_executado = False
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
            tile = BANCO_DADOS.tile_em(gx, gy)
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

    def _maestria_player(self, objeto_player_id: int) -> float:
        from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada
        usuario = BANCO_DADOS.usuario_por_objeto_id(int(objeto_player_id or 0))
        if not usuario:
            return 0.0
        perfil = obter_personagem_para_entrada(usuario)
        if not isinstance(perfil, dict):
            return 0.0
        return float(perfil.get("maestria", 0.0) or 0.0)

    def _classificar_colisao(self, obj) -> str:
        tipo = str(getattr(obj, "tipo_classe", "")).strip().lower()
        subtipo = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
        if subtipo == "pokemon":
            return "pokemon"
        if subtipo == "player":
            return "player"
        if subtipo == "projetil":
            return "projetil"
        if tipo == "estrutura_natural":
            return "estrutura_natural"
        if tipo.startswith("estrutura"):
            return "bloqueante"
        return "outro"

    def _payload_pokemon_capturado(self, poke: PokemonServer) -> Dict[str, object]:
        estado = poke.estado_extra if isinstance(poke.estado_extra, dict) else {}
        payload = {
            "Nome": str(estado.get("nome") or estado.get("especie") or "Pokemon"),
            "Code": str(estado.get("code") or ""),
            "Nivel": int(estado.get("nivel", 1) or 1),
            "IV": int(estado.get("iv", 0) or 0),
            "Raridade": int(estado.get("raridade", 1) or 1),
            "Estagio": int(estado.get("estagio", 1) or 1),
        }
        for chave, valor in estado.items():
            if chave in {"captura"}:
                continue
            payload[chave] = valor
        return payload

    def _registrar_captura_inventario_player(self, dono_id: int, poke: PokemonServer) -> None:
        from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada, atualizar_inventario_personagem
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        usuario = BANCO_DADOS.usuario_por_objeto_id(int(dono_id or 0))
        if not usuario:
            return

        dados_player = obter_personagem_para_entrada(usuario)
        if not isinstance(dados_player, dict):
            return

        inventario = dict(dados_player.get("inventario", {})) if isinstance(dados_player.get("inventario"), dict) else {}
        pokemons = list(inventario.get("pokemons", []))
        pokemons.append(self._payload_pokemon_capturado(poke))
        inventario["pokemons"] = pokemons

        atualizar_inventario_personagem(usuario, inventario)
        dados_player["inventario"] = inventario

        obj = BANCO_DADOS.garantir_player(usuario, str(dados_player.get("skin", "S1")), tuple(dados_player.get("posicao", [0.0, 0.0])))
        payload = {
            "tipo": "entidade_player",
            "nome": str(dados_player.get("nome", usuario)),
            "skin": str(dados_player.get("skin", "S1")),
            "posicao": [float(obj.posicao[0]), float(obj.posicao[1])],
            "perfil": {k: v for k, v in dados_player.items() if k != "inventario"},
            "inventario": inventario,
        }
        registrar_diff(
            "update",
            payload=payload,
            escopo={"centro": [float(obj.posicao[0]), float(obj.posicao[1])], "raio": 780.0},
            objeto_id=obj.Id,
            categoria="outro"
        )

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
            registrar_diff(
                "update",
                payload=poke.serializar(),
                escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120},
                objeto_id=poke.Id,
                autor="server",
                categoria="pokemon",
                base=False,
            )

            cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
            if str(cap.get("fase", "")) == "finalizada" and str(cap.get("resultado", "")) == "sucesso":
                self._registrar_captura_inventario_player(int(cap.get("dono_id", 0) or 0), poke)
                removido = BANCO_DADOS.remover_objeto(poke.Id)
                self._pokemons_ids.discard(poke.Id)
                if removido is not None:
                    registrar_diff(
                        "despawn",
                        payload={"id": removido.Id, "motivo": "captura_sucesso"},
                        escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120},
                        objeto_id=removido.Id,
                        categoria="pokemon",
                    base=False,
                    )


    def _sincronizar_registries_com_banco(self) -> None:
        for obj in BANCO_DADOS.listar_objetos():
            subtipo = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
            if subtipo == "pokemon":
                self._pokemons_ids.add(int(obj.Id))
            elif subtipo == "bau":
                self._baus_ids.add(int(obj.Id))

    def _executar_tick(self) -> None:
        self._sincronizar_registries_com_banco()
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

        chance_mover = max(0.0, min(1.0, self._f("chance_mover_por_tick", 0.45)))
        agora = time.monotonic()
        for poke in pokemons:
            forcar = agora < float(poke.estado_extra.get("forcar_movimento_ate", 0.0) or 0.0)
            if forcar or random.random() < chance_mover:
                self._mover_pokemon(poke, chunks_carregados)

        self._executar_tick_baus(chunks_simulados, chunks_carregados)
        self._executar_tick_capturas()
        self._limpar_baus_abertos_expirados()

    def _executar_tick_baus(self, chunks_simulados: Set[Chunk], chunks_carregados: Set[Chunk]) -> None:
        baus = []
        for oid in list(self._baus_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if isinstance(obj, BauServer):
                baus.append(obj)
            else:
                self._baus_ids.discard(oid)

        max_total = self._max_baus_permitidos(len(chunks_carregados))
        chance_spawn = max(0.0, min(1.0, self._f("chance_spawn_bau_por_tick", 0.03)))
        if chunks_simulados and len(baus) < max_total and random.random() < chance_spawn:
            chunk = random.choice(list(chunks_simulados))
            max_por_chunk = max(1, self._i("max_bau_por_chunk_simulado", 1))
            if self._contar_baus_chunk(chunk) < max_por_chunk:
                self._spawn_bau(chunk)

        self._abrir_baus_por_colisao(baus)


    def _abrir_baus_por_colisao(self, baus: List[BauServer]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff
        from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada, atualizar_inventario_personagem

        players = [o for o in BANCO_DADOS.listar_objetos() if str(getattr(o, "estado_extra", {}).get("subtipo", "")) == "player"]
        for bau in baus:
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
                    registrar_diff("update", payload={"inventario": inv}, escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 780.0}, objeto_id=player.Id, autor="server", categoria="player", base=False)
                registrar_diff("update", payload={"estado": {"aberto": True, "itens": []}}, escopo={"centro": [bau.posicao[0], bau.posicao[1]], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau", base=False)
                break
    def _max_baus_permitidos(self, total_chunks_carregados: int) -> int:
        fator = max(0.005, self._f("max_bau_por_chunk_carregado", 0.03))
        return max(1, int(total_chunks_carregados * fator))

    def _spawn_bau(self, chunk: Chunk) -> None:
        chunk_sz = BANCO_DADOS.chunk_tamanho_unidade()
        x0, y0 = chunk[0] * chunk_sz, chunk[1] * chunk_sz
        tentativas = max(1, self._i("tentativas_spawn_bau_chunk", 8))
        escolhido = None
        colisor = self._obter_colisor_global()
        while tentativas > 0:
            tentativas -= 1
            px = random.uniform(x0 + 0.2, x0 + chunk_sz - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_sz - 0.2)
            if colisor((px, py), 0.42):
                escolhido = (px, py)
                break
        if escolhido is None:
            return

        dados = gerar_bau_server(random)
        novo_id = BANCO_DADOS.gerar_id()
        bau = BauServer(
            id_objeto=novo_id,
            tipo_bau=str(dados.get("tipo_bau", "Comum")),
            itens=list(dados.get("itens", [])),
            posicao=escolhido,
            raio_colisao=0.42,
            raio_interacao=0.85,
            aberto=False,
        )
        BANCO_DADOS.inserir_objeto(bau)
        self._baus_ids.add(bau.Id)

        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        registrar_diff(
            "spawn",
            payload=bau.serializar(),
            escopo={"centro": [escolhido[0], escolhido[1]], "raio": 80},
            objeto_id=bau.Id,
            categoria="outro",
        )

    def _contar_baus_chunk(self, chunk: Chunk) -> int:
        c = 0
        for oid in self._baus_ids:
            obj = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(obj, BauServer):
                continue
            if BANCO_DADOS.chunk_da_posicao(obj.posicao) == chunk:
                c += 1
        return c

    def _limpar_baus_abertos_expirados(self) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        ttl = max(0.1, self._f("tick_segundos", 0.2) * 100.0)
        agora = time.monotonic()
        for oid in list(self._baus_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(obj, BauServer):
                self._baus_ids.discard(oid)
                continue
            if not bool(obj.estado_extra.get("aberto", False)):
                continue
            aberto_em = float(obj.estado_extra.get("aberto_em", 0.0))
            if aberto_em <= 0.0 or (agora - aberto_em) < ttl:
                continue
            removido = BANCO_DADOS.remover_objeto(oid)
            self._baus_ids.discard(oid)
            if removido is not None:
                registrar_diff(
                    "despawn",
                    payload={"id": removido.Id, "motivo": "bau_aberto_expirado"},
                    escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 80},
                    objeto_id=removido.Id,
                    categoria="bau",
                )

    def _max_pokemons_permitidos(self, total_chunks_carregados: int) -> int:
        fator = max(0.01, self._f("max_pokemon_por_chunk_carregado", 0.12))
        return max(1, int(total_chunks_carregados * fator))

    def _mover_pokemon(self, poke: PokemonServer, chunks_carregados: Set[Chunk]) -> None:
        max_step = max(0.08, self._f("maior_vetor_movimento_pokemon", 3.0) * 0.35)
        dx = random.uniform(-max_step, max_step)
        dy = random.uniform(-max_step, max_step)
        if abs(dx) < 1e-8 and abs(dy) < 1e-8:
            return

        destino = (float(poke.posicao[0]) + dx, float(poke.posicao[1]) + dy)
        chunk_destino = BANCO_DADOS.chunk_da_posicao(destino)
        if chunk_destino not in chunks_carregados:
            return

        colisor = self._obter_colisor_global()
        velocidade_base = max(0.05, self._f("velocidade_pokemon_tiles_s", 5.5) * 0.45)
        if poke.mover((dx, dy), colisor_cb=colisor, velocidade_tiles_s=velocidade_base):
            BANCO_DADOS.atualizar_objeto(poke.Id, {"posicao": [poke.posicao[0], poke.posicao[1]]})
            from SimuladorServerJogo.Rotas.Ativador import registrar_diff

            registrar_diff(
                "update",
                payload=poke.serializar(),
                escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 40},
                objeto_id=poke.Id,
                categoria="pokemon",
            )

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
        poke = gerar_pokemon_server(novo_id=novo_id, posicao=escolhido, chunk_xy=chunk)
        poke.raio_colisao = raio
        BANCO_DADOS.inserir_objeto(poke)
        self._pokemons_ids.add(poke.Id)
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        registrar_diff(
            "spawn",
            payload=poke.serializar(),
            escopo={"centro": [escolhido[0], escolhido[1]], "raio": 80},
            objeto_id=poke.Id,
            categoria="outro",
        )

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


    def contagem_pokemons_registrados(self) -> int:
        return len([oid for oid in self._pokemons_ids if BANCO_DADOS.obter_objeto(oid) is not None])

    def contagem_baus_registrados(self) -> int:
        return len([oid for oid in self._baus_ids if BANCO_DADOS.obter_objeto(oid) is not None])


CEREBRO = CerebroServer()
