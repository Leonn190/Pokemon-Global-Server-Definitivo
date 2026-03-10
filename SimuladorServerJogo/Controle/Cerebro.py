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
                    categoria="rapida",
                )
        self._pokemons_ids.clear()
        self._baus_ids.clear()
        self._projeteis_ids.clear()

    def registrar_intencao_arremesso(self, client_id: str, payload: Dict[str, object]) -> bool:
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        origem = payload.get("origem") if isinstance(payload.get("origem"), (list, tuple)) and len(payload.get("origem")) == 2 else None
        direcao = payload.get("direcao") if isinstance(payload.get("direcao"), (list, tuple)) and len(payload.get("direcao")) == 2 else None
        if origem is None or direcao is None:
            return False

        dono_obj = BANCO_DADOS.obter_objeto(int(payload.get("dono_id", 0) or 0))
        if dono_obj is None:
            return False

        estilo = str(item.get("Estilo") or item.get("estilo") or "item").lower()
        nome_item = str(item.get("Nome") or "item")
        token = str(payload.get("token_arremesso") or "")
        velocidade = float(payload.get("velocidade", 11.0) or 11.0)
        alcance = float(payload.get("alcance", 6.0) or 6.0)
        distancia_conferencia = max(0.8, min(4.0, float(payload.get("distancia_conferencia_inicial", 4.0) or 4.0)))

        pid = BANCO_DADOS.gerar_id()
        proj = ProjetilServer(
            id_objeto=pid,
            posicao=(float(origem[0]), float(origem[1])),
            dono_id=int(getattr(dono_obj, "Id", 0) or 0),
            tipo_projetil=estilo,
            subtipo=nome_item,
            item_base_id=str(item.get("Code") or ""),
            token_arremesso=token,
            direcao=(float(direcao[0]), float(direcao[1])),
            velocidade=velocidade,
            alcance=alcance,
            raio_colisao=0.18,
        )
        proj.estado_extra["distancia_conferencia_inicial"] = distancia_conferencia
        BANCO_DADOS.inserir_objeto(proj)
        self._projeteis_ids.add(proj.Id)

        from SimuladorServerJogo.Rotas.Ativador import registrar_diff
        registrar_diff("spawn", payload=proj.serializar(), escopo={"centro": [proj.posicao[0], proj.posicao[1]], "raio": 80}, objeto_id=proj.Id, categoria="rapida")
        return True


    def registrar_spawn_manual(self, objeto) -> None:
        """Inclui objetos spawnados por comando no ciclo do cérebro."""
        if isinstance(objeto, PokemonServer):
            self._pokemons_ids.add(int(objeto.Id))
            return
        if isinstance(objeto, BauServer):
            self._baus_ids.add(int(objeto.Id))
            return

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
            for e in eventos:
                registrar_diff(
                    "evento",
                    payload=e["payload"],
                    escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120},
                    objeto_id=poke.Id,
                    categoria="rapida",
                    evento=e.get("evento", "pokemon_captura"),
                )

            cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
            if str(cap.get("fase", "")) == "finalizada" and str(cap.get("resultado", "")) == "sucesso":
                removido = BANCO_DADOS.remover_objeto(poke.Id)
                self._pokemons_ids.discard(poke.Id)
                if removido is not None:
                    registrar_diff(
                        "despawn",
                        payload={"id": removido.Id, "motivo": "captura_sucesso"},
                        escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120},
                        objeto_id=removido.Id,
                        categoria="rapida",
                    )

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

        chance_mover = max(0.0, min(1.0, self._f("chance_mover_por_tick", 0.45)))
        for poke in pokemons:
            if random.random() < chance_mover:
                self._mover_pokemon(poke, chunks_carregados)

        self._executar_tick_baus(chunks_simulados, chunks_carregados)
        self._executar_tick_projeteis(chunks_carregados)
        self._executar_tick_capturas()
        self._limpar_baus_abertos_expirados()

    def validar_colisao_candidata_projetil(self, client_id: str, payload: Dict[str, object]) -> bool:
        token = str(payload.get("token_arremesso") or "")
        if not token:
            return False

        proj = None
        for oid in list(self._projeteis_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if isinstance(obj, ProjetilServer) and str(obj.estado_extra.get("token_arremesso", "")) == token:
                proj = obj
                break
        if proj is None or bool(proj.estado_extra.get("terminado", False)):
            return False

        alvo_id = int(payload.get("alvo_id", 0) or 0)
        alvo = BANCO_DADOS.obter_objeto(alvo_id) if alvo_id > 0 else None
        if alvo is None or alvo.Id == proj.Id:
            return False

        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        raio_proj = float(getattr(proj, "raio_colisao", 0.18) or 0.18)
        raio_alvo = float(getattr(alvo, "raio_colisao", 0.2) or 0.2)
        dx = float(alvo.posicao[0]) - float(proj.posicao[0])
        dy = float(alvo.posicao[1]) - float(proj.posicao[1])
        limite = raio_proj + raio_alvo
        colisao_confirmada = ((dx * dx) + (dy * dy)) <= (limite * limite)

        pos_ini = proj.estado_extra.get("posicao_inicial") if isinstance(proj.estado_extra.get("posicao_inicial"), (list, tuple)) else [proj.posicao[0], proj.posicao[1]]
        dpx = float(proj.posicao[0]) - float(pos_ini[0])
        dpy = float(proj.posicao[1]) - float(pos_ini[1])
        distancia_percorrida = (dpx * dpx + dpy * dpy) ** 0.5
        distancia_conferencia = float(proj.estado_extra.get("distancia_conferencia_inicial", 4.0) or 4.0)

        if colisao_confirmada and distancia_percorrida <= max(0.8, distancia_conferencia):
            categoria = self._classificar_colisao(alvo)
            if categoria == "pokemon" and isinstance(alvo, PokemonServer):
                cap_alvo = alvo.estado_extra.get("captura") if isinstance(alvo.estado_extra.get("captura"), dict) else {}
                if bool(cap_alvo.get("ativa", False)) or bool(cap_alvo.get("captura_pendente", False)):
                    registrar_diff("evento", payload={"token_arremesso": token, "projetil_id": int(proj.Id), "colidiu": False, "alvo_id": int(alvo.Id)}, escopo={"centro": [proj.posicao[0], proj.posicao[1]], "raio": 120}, objeto_id=proj.Id, categoria="rapida", evento="projetil_colisao_negada")
                    return True
            tipo_proj = str(proj.estado_extra.get("tipo_projetil", "item")).lower()
            nome_item = str(proj.estado_extra.get("nome_item", "item"))

            if categoria == "pokemon" and isinstance(alvo, PokemonServer):
                if tipo_proj == "fruta":
                    fr = resolver_fruta(alvo, nome_item, contexto={"dono_id": int(proj.estado_extra.get("dono_id", 0) or 0)})
                    registrar_diff("evento", payload=fr["payload"], escopo={"centro": [alvo.posicao[0], alvo.posicao[1]], "raio": 120}, objeto_id=alvo.Id, categoria="rapida", evento=fr.get("evento", "pokemon_frutificado"))
                else:
                    dono_id = int(proj.estado_extra.get("dono_id", 0) or 0)
                    dono_obj = BANCO_DADOS.obter_objeto(dono_id)
                    dono_pos = [float(dono_obj.posicao[0]), float(dono_obj.posicao[1])] if dono_obj is not None else [alvo.posicao[0], alvo.posicao[1]]
                    ret_captura = resolver_captura(alvo, nome_item, contexto={
                        "dono_id": dono_id,
                        "dono_posicao": dono_pos,
                        "distancia_arremesso_tiles": float(proj.estado_extra.get("distancia", 0.0) or 0.0),
                        "tentativas_falhas_anteriores": int(alvo.estado_extra.get("tentativas_falhas_captura", 0) or 0),
                        "bioma": str(alvo.estado_extra.get("bioma", "")),
                        "servidor_agora_ms": int(time.time() * 1000),
                        "maestria": self._maestria_player(dono_id),
                    })
                    if bool(ret_captura.get("iniciada", False)):
                        BANCO_DADOS.atualizar_objeto(alvo.Id, {"estado": alvo.estado_extra})
                        cap = dict(alvo.estado_extra.get("captura", {}))
                        cap["fase"] = "iniciada"
                        cap.setdefault("checks_total", 3)
                        cap.setdefault("resultado", "pendente")
                        cap.setdefault("captura_pendente", True)
                        registrar_diff("evento", payload={"pokemon_id": int(alvo.Id), "captura": cap}, escopo={"centro": [alvo.posicao[0], alvo.posicao[1]], "raio": 120}, objeto_id=alvo.Id, categoria="rapida", evento="pokemon_captura_iniciada")

            proj.terminar(f"colisao_{categoria}")
            BANCO_DADOS.atualizar_objeto(proj.Id, {"estado": proj.estado_extra})
            registrar_diff("update", payload=proj.serializar(), escopo={"centro": [proj.posicao[0], proj.posicao[1]], "raio": 80}, objeto_id=proj.Id, categoria="rapida")
            registrar_diff("evento", payload={"token_arremesso": token, "projetil_id": int(proj.Id), "colidiu": True, "alvo_id": int(alvo.Id), "categoria": categoria, "ponto_impacto": [float(proj.posicao[0]), float(proj.posicao[1])]}, escopo={"centro": [proj.posicao[0], proj.posicao[1]], "raio": 120}, objeto_id=proj.Id, categoria="rapida", evento="projetil_colisao_confirmada")
            return True

        registrar_diff("evento", payload={"token_arremesso": token, "projetil_id": int(proj.Id), "colidiu": False, "alvo_id": int(getattr(alvo, "Id", 0) or 0)}, escopo={"centro": [proj.posicao[0], proj.posicao[1]], "raio": 120}, objeto_id=proj.Id, categoria="rapida", evento="projetil_colisao_negada")
        return True

    def _executar_tick_projeteis(self, chunks_carregados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        dt = max(0.02, self._f("tick_segundos", 0.2))
        substeps = max(1, int(dt / 0.04))
        dt_sub = dt / substeps

        for oid in list(self._projeteis_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(obj, ProjetilServer):
                self._projeteis_ids.discard(oid)
                continue

            if bool(obj.estado_extra.get("terminado", False)):
                removido = BANCO_DADOS.remover_objeto(obj.Id)
                self._projeteis_ids.discard(obj.Id)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": str(removido.estado_extra.get("motivo_termino", "fim"))}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 80}, objeto_id=removido.Id, categoria="rapida")
                continue

            colidiu = None
            for _ in range(substeps):
                obj.atualizar(dt_sub)
                proximos = BANCO_DADOS.buscar_proximos(obj.posicao, 4.0)
                for outro in proximos:
                    if outro.Id == obj.Id or outro.Id == int(obj.estado_extra.get("dono_id", 0) or 0):
                        continue
                    rr = float(getattr(outro, "raio_colisao", 0.2)) + float(getattr(obj, "raio_colisao", 0.18))
                    if ((outro.posicao[0] - obj.posicao[0]) ** 2 + (outro.posicao[1] - obj.posicao[1]) ** 2) <= (rr * rr):
                        colidiu = outro
                        break
                if colidiu is not None or bool(obj.estado_extra.get("terminado", False)):
                    break

            BANCO_DADOS.atualizar_objeto(obj.Id, {"posicao": [obj.posicao[0], obj.posicao[1]], "estado": obj.estado_extra})
            registrar_diff("update", payload=obj.serializar(), escopo={"centro": [obj.posicao[0], obj.posicao[1]], "raio": 80}, objeto_id=obj.Id, categoria="rapida")

            if colidiu is None:
                continue

            categoria = self._classificar_colisao(colidiu)
            tipo_proj = str(obj.estado_extra.get("tipo_projetil", "item")).lower()
            nome_item = str(obj.estado_extra.get("nome_item", "item"))

            if categoria == "pokemon":
                # Captura/frutificação autoritativa de pokémon é conferida via evento candidato do client.
                continue

            if categoria in {"player", "estrutura_natural", "projetil", "bloqueante", "outro"}:
                obj.terminar(f"colisao_{categoria}")

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
            categoria="rapida",
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

        ttl = max(0.1, self._f("ttl_bau_aberto_segundos", 5.0))
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
                    categoria="rapida",
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
                categoria="rapida",
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
            categoria="rapida",
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


CEREBRO = CerebroServer()
