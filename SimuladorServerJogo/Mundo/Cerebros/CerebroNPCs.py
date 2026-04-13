from __future__ import annotations

import csv
import math
import random
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Tuple

from Codigo.ModulosGerais.Colisor import Colisor
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer
from SimuladorServerJogo.Gerais.EstadoServidor import carregar_npcs_vendedores_estado, salvar_npcs_vendedores_estado
from SimuladorServerJogo.Gerais.Geradores.GeradorMundo import carregar_estado_mundo
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]


class CerebroNPCs:
    def __init__(self, core) -> None:
        self._core = core
        self._npcs: Dict[str, Dict[str, object]] = {}
        self._ids_materializados: Set[int] = set()
        self._carregar_ou_criar_estado()

    def _carregar_ou_criar_estado(self) -> None:
        largura, altura = BANCO_DADOS.limites_mundo()
        estado_mundo = carregar_estado_mundo()
        spawn = estado_mundo.get("spawn", [0.0, 0.0]) if isinstance(estado_mundo, dict) else [0.0, 0.0]
        try:
            spawn_x = float(spawn[0])
            spawn_y = float(spawn[1])
        except Exception:
            spawn_x = max(4.0, float(largura) * 0.5)
            spawn_y = max(4.0, float(altura) * 0.5)

        estado = carregar_npcs_vendedores_estado()
        if estado:
            self._npcs = {str(k): dict(v) for k, v in estado.items() if isinstance(v, dict)}
            self._forcar_josefa_chunk_inicial(spawn_x, spawn_y)
            return

        base: Dict[str, Dict[str, object]] = {}
        arquivo_vendedores = Path("Dados") / "Pokemon Global Server - NPC Vendedor.csv"
        if arquivo_vendedores.exists():
            with arquivo_vendedores.open("r", encoding="utf-8") as f:
                for idx, row in enumerate(csv.DictReader(f), start=1):
                    nome = str(row.get("Nome") or f"Vendedor {idx}").strip() or f"Vendedor {idx}"
                    code = str(row.get("Code") or idx).strip() or str(idx)
                    skin_raw = str(row.get("Skin") or "1").strip()
                    if skin_raw.lower().endswith(".png"):
                        skin = skin_raw
                    elif skin_raw.lower().startswith("s") and skin_raw[1:].isdigit():
                        skin = f"{skin_raw[1:]}.png"
                    else:
                        skin = f"{skin_raw}.png"
                    px, py = self._encontrar_spawn_terrestre((spawn_x, spawn_y), idx)
                    estatico = False
                    rota = [] if estatico else self._gerar_rota_grande((px, py), idx)
                    npc_id = int(900000 + int(code) if code.isdigit() else 900000 + idx)
                    base[f"vendedor:{code}"] = {
                        "id": npc_id,
                        "code": str(code),
                        "nome": nome,
                        "skin": skin,
                        "velocidade": float(self._core._f("npc_velocidade_base", 4.5)),
                        "estilo": "vendedor",
                        "estatico": bool(estatico),
                        "dimensao": "Mundo",
                        "posicao": [float(px), float(py)],
                        "rota": [[float(p[0]), float(p[1])] for p in rota],
                        "rota_idx": 0,
                        "espera_ate_tick": 0,
                        "interacao": {"ativa": False, "cliente": ""},
                    }
        mapa_estadios = self._mapa_dimensao_estadios()
        arquivo_combatentes = Path("Dados") / "Pokemon Global Server - NPC Combatente.csv"
        if arquivo_combatentes.exists():
            with arquivo_combatentes.open("r", encoding="utf-8") as f:
                for idx, row in enumerate(csv.DictReader(f), start=1):
                    nivel = str(row.get("Nivel") or "").strip().lower()
                    if nivel != "lider":
                        continue
                    nome = str(row.get("Nome") or f"Lider {idx}").strip() or f"Lider {idx}"
                    code = str(row.get("Code") or idx).strip() or str(idx)
                    estadio_tipo = self._normalizar_tipo_estadio(str(row.get("Estadio") or "normal"))
                    dimensao = mapa_estadios.get(estadio_tipo, f"Estadio{estadio_tipo.title()}")
                    skin_raw = str(row.get("Skin") or "1").strip()
                    if skin_raw.lower().endswith(".png"):
                        skin = skin_raw
                    elif skin_raw.lower().startswith("s") and skin_raw[1:].isdigit():
                        skin = f"{skin_raw[1:]}.png"
                    else:
                        skin = f"{skin_raw}.png"
                    npc_id = int(910000 + int(code) if code.isdigit() else 910000 + idx)
                    pokemons_npc, times_npc = self._pokemon_npc_materializados(row)
                    base[f"combatente:{code}"] = {
                        "id": npc_id,
                        "code": str(code),
                        "nome": nome,
                        "skin": skin,
                        "velocidade": 0.0,
                        "estilo": "combatente",
                        "estatico": True,
                        "dimensao": dimensao,
                        "estadio_tipo": estadio_tipo,
                        "posicao": [30.0, 20.0],
                        "rota": [],
                        "rota_idx": 0,
                        "espera_ate_tick": 0,
                        "interacao": {"ativa": False, "cliente": ""},
                        "pokemons": list(pokemons_npc),
                        "times_pokemon": list(times_npc),
                    }
        self._npcs = base
        self._forcar_josefa_chunk_inicial(spawn_x, spawn_y)
        salvar_npcs_vendedores_estado(self._npcs, force=True)

    def _forcar_josefa_chunk_inicial(self, spawn_x: float, spawn_y: float) -> None:
        mudou = False
        for npc in self._npcs.values():
            nome = str(npc.get("nome") or "").strip().lower()
            estilo = str(npc.get("estilo") or "vendedor").strip().lower()
            if estilo == "combatente":
                npc["estatico"] = True
                npc["rota"] = []
                npc["rota_idx"] = 0
                mudou = True
                continue
            pos = npc.get("posicao", [spawn_x, spawn_y])
            pos_ruim = (
                (not isinstance(pos, (list, tuple)))
                or len(pos) != 2
                or self._tile_bloqueado_npc((float(pos[0]), float(pos[1])))
                or (abs(float(pos[0])) < 0.05 and abs(float(pos[1])) < 0.05)
            )
            if bool(npc.get("estatico", False)) or pos_ruim:
                npc["estatico"] = False
                if pos_ruim:
                    sx, sy = self._encontrar_spawn_terrestre((spawn_x, spawn_y), int(npc.get("id", 0) or 1))
                    npc["posicao"] = [float(sx), float(sy)]
                if not isinstance(npc.get("rota"), list) or not npc.get("rota"):
                    pos = npc.get("posicao", [spawn_x, spawn_y])
                    origem = (float(pos[0]), float(pos[1])) if isinstance(pos, (list, tuple)) and len(pos) == 2 else (float(spawn_x), float(spawn_y))
                    npc["rota"] = [[float(p[0]), float(p[1])] for p in self._gerar_rota_grande(origem, int(npc.get("id", 0) or 1))]
                mudou = True
        if mudou:
            salvar_npcs_vendedores_estado(self._npcs, force=True)

    def _segmento_terrestre(self, p0: Vector2, p1: Vector2, passo: float = 0.75) -> tuple[bool, float]:
        dx, dy = self._dist_toroidal(p0, p1)
        dist = math.hypot(dx, dy)
        if dist <= 1e-6:
            return (False, 0.0)
        amostras = max(2, int(math.ceil(dist / max(0.2, float(passo)))))
        for i in range(1, amostras + 1):
            t = i / amostras
            x = p0[0] + (dx * t)
            y = p0[1] + (dy * t)
            if self._tile_bloqueado_npc((x, y)):
                return (False, dist)
        return (True, dist)

    def _gerar_rota_grande(self, inicio: Vector2, semente: int) -> List[Vector2]:
        largura, altura = BANCO_DADOS.limites_mundo()
        rnd = random.Random(int(semente) * 7919)
        alvo_total = rnd.uniform(
            float(self._core._f("npc_rota_tamanho_min", 200.0)),
            float(self._core._f("npc_rota_tamanho_max", 1000.0)),
        )
        pontos = [inicio]
        atual = inicio
        soma = 0.0
        tentativas = 0
        while soma < alvo_total and tentativas < 1200:
            tentativas += 1
            dist = rnd.uniform(24.0, 96.0)
            ang = rnd.uniform(0.0, math.tau)
            nx = (atual[0] + math.cos(ang) * dist) % max(1.0, float(largura))
            ny = (atual[1] + math.sin(ang) * dist) % max(1.0, float(altura))
            candidato = (nx, ny)
            if self._tile_bloqueado_npc(candidato):
                continue
            ok, seg = self._segmento_terrestre(atual, candidato)
            if not ok:
                continue
            pontos.append(candidato)
            atual = candidato
            soma += float(seg)
        if len(pontos) <= 1:
            return [inicio]
        return pontos

    def _dist_toroidal(self, p0: Vector2, p1: Vector2) -> Vector2:
        largura, altura = BANCO_DADOS.limites_mundo()
        dx = float(p1[0]) - float(p0[0])
        dy = float(p1[1]) - float(p0[1])
        if largura > 0:
            dx -= round(dx / float(largura)) * float(largura)
        if altura > 0:
            dy -= round(dy / float(altura)) * float(altura)
        return (dx, dy)

    def _tile_bloqueado_npc(self, pos: Vector2) -> bool:
        gx = int(math.floor(float(pos[0])))
        gy = int(math.floor(float(pos[1])))
        tile = int(BANCO_DADOS.tile_em(gx, gy) or 0)
        return tile in {0, 1}

    def _encontrar_spawn_terrestre(self, origem: Vector2, semente: int) -> Vector2:
        largura, altura = BANCO_DADOS.limites_mundo()
        rnd = random.Random((int(semente) + 17) * 10657)
        base_x, base_y = float(origem[0]), float(origem[1])
        for _ in range(720):
            dist = rnd.uniform(16.0, 220.0)
            ang = rnd.uniform(0.0, math.tau)
            x = (base_x + math.cos(ang) * dist) % max(1.0, float(largura))
            y = (base_y + math.sin(ang) * dist) % max(1.0, float(altura))
            pos = (x, y)
            if self._tile_bloqueado_npc(pos):
                continue
            if self._colisao_objetos(0, pos, raio=0.95):
                continue
            return pos
        return (base_x % max(1.0, float(largura)), base_y % max(1.0, float(altura)))

    def _colisao_objetos(self, npc_id: int, pos: Vector2, raio: float = 0.55) -> bool:
        for obj in BANCO_DADOS.buscar_proximos(pos, max(1.5, raio + 1.0)):
            if int(getattr(obj, "Id", 0) or 0) == int(npc_id):
                continue
            subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "") or "").strip().lower()
            tipo = str(getattr(obj, "tipo_classe", "") or "").strip().lower()
            if subt not in {"player", "pokemon", "bau", "npc_vendedor", "npc_combatente"} and not tipo.startswith("estrutura"):
                continue
            rr = float(getattr(obj, "raio_colisao", 0.5) or 0.5) + float(raio)
            dx, dy = self._dist_toroidal(pos, getattr(obj, "posicao", pos))
            if (dx * dx + dy * dy) <= (rr * rr):
                return True
        return False

    def _chunk_in_qualquer(self, pos: Vector2, carregados: Set[Chunk], simulados: Set[Chunk]) -> bool:
        c = BANCO_DADOS.chunk_da_posicao(pos)
        return c in carregados or c in simulados

    def _materializar_npc(self, npc: Dict[str, object]) -> AtorServer:
        oid = int(npc.get("id", 0) or 0)
        obj = BANCO_DADOS.obter_objeto(oid)
        if isinstance(obj, AtorServer):
            return obj
        ator = AtorServer(
            id_objeto=oid,
            usuario=f"npc:{npc.get('code', oid)}",
            skin=str(npc.get("skin", "1.png")),
            posicao=tuple(npc.get("posicao", [0.0, 0.0])),
            dimensao=str(npc.get("dimensao") or "Mundo"),
        )
        ator.raio_interacao = max(ator.raio_colisao, float(self._core._f("npc_raio_interacao", 1.1)))
        ator.Colisor.raio_interacao = ator.raio_interacao
        estilo = str(npc.get("estilo") or "vendedor").strip().lower()
        ator.estado_extra["subtipo"] = "npc_combatente" if estilo == "combatente" else "npc_vendedor"
        ator.estado_extra["nome"] = str(npc.get("nome") or "Vendedor")
        ator.estado_extra["npc_code"] = str(npc.get("code") or "")
        ator.estado_extra["estilo"] = str(npc.get("estilo") or "vendedor")
        ator.estado_extra["estatico"] = bool(npc.get("estatico", False))
        ator.estado_extra["velocidade"] = float(npc.get("velocidade", self._core._f("npc_velocidade_base", 4.5)) or self._core._f("npc_velocidade_base", 4.5))
        ator.estado_extra["angulo"] = float(npc.get("angulo", 0.0) or 0.0)
        ator.estado_extra["interacao"] = dict(npc.get("interacao", {})) if isinstance(npc.get("interacao"), dict) else {"ativa": False, "cliente": ""}
        ator.estado_extra["dimensao"] = str(npc.get("dimensao") or "Mundo")
        ator.estado_extra["pokemons"] = list(npc.get("pokemons", [])) if isinstance(npc.get("pokemons"), list) else []
        ator.estado_extra["times_pokemon"] = list(npc.get("times_pokemon", [])) if isinstance(npc.get("times_pokemon"), list) else []
        BANCO_DADOS.inserir_objeto(ator)
        self._ids_materializados.add(int(ator.Id))
        return ator

    @staticmethod
    def _colunas_pokemon_npc(row: Dict[str, object]) -> List[tuple[int, str]]:
        cols: List[tuple[int, str]] = []
        for chave in list(row.keys()):
            texto = str(chave or "").strip()
            if not texto.lower().startswith("pokemon"):
                continue
            sufixo = texto[7:]
            try:
                indice = int(sufixo)
            except Exception:
                continue
            cols.append((indice, texto))
        cols.sort(key=lambda x: x[0])
        return cols

    def _pokemon_npc_materializados(self, row: Dict[str, object]) -> tuple[List[dict], List[dict]]:
        pokemons: List[dict] = []
        times: List[dict] = []
        slots_atual: List[dict] = []
        indice_time = 1
        for _, coluna in self._colunas_pokemon_npc(row):
            nome = str(row.get(coluna) or "").strip()
            if nome:
                try:
                    poke = criar_pokemon_inicial_materializado(nome)
                    if isinstance(poke, dict):
                        pokemons.append(poke)
                        slots_atual.append(poke)
                except Exception:
                    pass
            if len(slots_atual) >= 6:
                times.append({"Nome": f"Time {indice_time}", "Slots": list(slots_atual)})
                indice_time += 1
                slots_atual = []
        if slots_atual:
            times.append({"Nome": f"Time {indice_time}", "Slots": list(slots_atual)})
        return pokemons, times

    @staticmethod
    def _normalizar_tipo_estadio(valor: str) -> str:
        base = unicodedata.normalize("NFD", str(valor or "").strip().lower())
        base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
        alias = {"eletrico": "eletrico", "psiquico": "psiquico", "terrestre": "terra", "agua": "agua", "dragao": "dragao"}
        return alias.get(base, base or "normal")

    def _mapa_dimensao_estadios(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for obj in BANCO_DADOS.listar_objetos():
            if str(getattr(obj, "tipo_classe", "") or "") != "entidade_estadio":
                continue
            estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
            tipo = self._normalizar_tipo_estadio(str(estado.get("tipo_estadio") or "normal"))
            out[tipo] = str(estado.get("dimensao_destino") or "EstadioNormal")
        return out

    def _desmaterializar_npc(self, npc_id: int):
        rem = BANCO_DADOS.remover_objeto(int(npc_id))
        if rem is not None:
            self._ids_materializados.discard(int(npc_id))

    def listar_locais_nomeados(self) -> List[Dict[str, object]]:
        locais: List[Dict[str, object]] = []
        for npc in self._npcs.values():
            if not isinstance(npc, dict):
                continue
            nome = str(npc.get("nome") or "").strip()
            pos = npc.get("posicao")
            if not nome or not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            try:
                px, py = float(pos[0]), float(pos[1])
            except Exception:
                continue
            locais.append({"id": int(npc.get("id", 0) or 0), "categoria": "npc", "nome": nome, "posicao": [px, py]})
        return locais

    def _resolver_movimento_npc_materializado(self, npc_id: int, origem: Vector2, destino: Vector2, raio: float = 0.55) -> Vector2:
        colisores: List[tuple[int, float, float, float, str, float, float]] = []
        for obj in BANCO_DADOS.buscar_proximos(origem, 2.2):
            oid = int(getattr(obj, "Id", 0) or 0)
            if oid == int(npc_id):
                continue
            subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "") or "").strip().lower()
            tipo = str(getattr(obj, "tipo_classe", "") or "").strip().lower()
            if subt not in {"player", "pokemon", "bau", "npc_vendedor", "npc_combatente"} and not tipo.startswith("estrutura"):
                continue
            colisores.append(
                (
                    oid,
                    float(getattr(obj, "posicao", origem)[0]),
                    float(getattr(obj, "posicao", origem)[1]),
                    float(getattr(obj, "raio_colisao", 0.5) or 0.5),
                    tipo,
                    float(getattr(obj, "campo", 0.0) or 0.0),
                    float(getattr(obj, "intensidade", 0.0) or 0.0),
                )
            )
        if not colisores:
            return destino
        rx, ry = Colisor.resolver_movimento_com_colisores(
            posicao_antes=origem,
            posicao_depois=destino,
            raio_entidade=float(raio),
            colisores=colisores,
            dt=(1.0 / 30.0),
        )
        return (float(rx), float(ry))

    def registrar_inicio_interacao(self, client_id: str, npc_id: int) -> tuple[bool, str]:
        alvo = None
        for npc in self._npcs.values():
            if int(npc.get("id", 0) or 0) == int(npc_id):
                alvo = npc
                break
        if alvo is None:
            return (False, "NPC não encontrado")
        inter = alvo.get("interacao") if isinstance(alvo.get("interacao"), dict) else {}
        if bool(inter.get("ativa", False)) and str(inter.get("cliente", "")) != str(client_id):
            return (False, "NPC já está em interação")
        alvo["interacao"] = {"ativa": True, "cliente": str(client_id)}
        obj = BANCO_DADOS.obter_objeto(int(alvo.get("id", 0) or 0))
        if isinstance(obj, AtorServer):
            obj.estado_extra["interacao"] = dict(alvo["interacao"])
        salvar_npcs_vendedores_estado(self._npcs)
        return (True, "Interação iniciada")

    def registrar_fim_interacao(self, client_id: str, npc_id: int) -> tuple[bool, str]:
        for npc in self._npcs.values():
            if int(npc.get("id", 0) or 0) != int(npc_id):
                continue
            inter = npc.get("interacao") if isinstance(npc.get("interacao"), dict) else {}
            if str(inter.get("cliente", "")) not in {"", str(client_id)}:
                return (False, "NPC ocupado")
            npc["interacao"] = {"ativa": False, "cliente": ""}
            npc["espera_ate_tick"] = int(self._core._tick_contador + random.randint(90, 360))
            obj = BANCO_DADOS.obter_objeto(int(npc.get("id", 0) or 0))
            if isinstance(obj, AtorServer):
                obj.estado_extra["interacao"] = dict(npc["interacao"])
            salvar_npcs_vendedores_estado(self._npcs)
            return (True, "Interação finalizada")
        return (False, "NPC não encontrado")

    def executar_tick(self, chunks_carregados: Set[Chunk], chunks_simulados: Set[Chunk], registrar_diff_cb) -> None:
        tick = int(self._core._tick_contador)
        for npc in self._npcs.values():
            pos = npc.get("posicao", [0.0, 0.0])
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                pos = [0.0, 0.0]
            atual = (float(pos[0]), float(pos[1]))
            estilo = str(npc.get("estilo") or "vendedor").strip().lower()
            if estilo != "combatente":
                ruim = self._tile_bloqueado_npc(atual) or (abs(atual[0]) < 0.05 and abs(atual[1]) < 0.05)
                if ruim:
                    sx, sy = self._encontrar_spawn_terrestre(atual, int(npc.get("id", 0) or 1))
                    atual = (float(sx), float(sy))
                    npc["posicao"] = [float(atual[0]), float(atual[1])]
                    npc["estatico"] = False
                    npc["rota"] = [[float(p[0]), float(p[1])] for p in self._gerar_rota_grande(atual, int(npc.get("id", 0) or 1))]
                    npc["rota_idx"] = 0
            inter = npc.get("interacao") if isinstance(npc.get("interacao"), dict) else {"ativa": False, "cliente": ""}
            esperando = int(npc.get("espera_ate_tick", 0) or 0) > tick
            estatico = bool(npc.get("estatico", False))
            materializado = isinstance(BANCO_DADOS.obter_objeto(int(npc.get("id", 0) or 0)), AtorServer)

            if (not estatico) and (not inter.get("ativa", False)) and (not esperando):
                rota = npc.get("rota", []) if isinstance(npc.get("rota"), list) else []
                if rota:
                    idx = int(npc.get("rota_idx", 0) or 0) % max(1, len(rota))
                    alvo_raw = rota[idx]
                    if isinstance(alvo_raw, (list, tuple)) and len(alvo_raw) == 2:
                        alvo = (float(alvo_raw[0]), float(alvo_raw[1]))
                        dx, dy = self._dist_toroidal(atual, alvo)
                        dist = math.hypot(dx, dy)
                        if dist < 0.75:
                            npc["rota_idx"] = (idx + 1) % len(rota)
                            npc["espera_ate_tick"] = tick + random.randint(30, 180)
                        else:
                            vel = float(npc.get("velocidade", self._core._f("npc_velocidade_base", 4.5)) or self._core._f("npc_velocidade_base", 4.5))
                            passo = min(dist, max(0.01, vel / 30.0))
                            nx, ny = (atual[0] + (dx / max(1e-6, dist)) * passo, atual[1] + (dy / max(1e-6, dist)) * passo)
                            nx += math.sin((tick + int(npc.get("id", 0))) * 0.03) * 0.04
                            ny += math.cos((tick + int(npc.get("id", 0))) * 0.025) * 0.04
                            largura, altura = BANCO_DADOS.limites_mundo()
                            candidato = (nx % max(1.0, float(largura)), ny % max(1.0, float(altura)))
                            if self._tile_bloqueado_npc(candidato):
                                candidato = atual
                            elif materializado:
                                candidato = self._resolver_movimento_npc_materializado(
                                    int(npc.get("id", 0) or 0),
                                    atual,
                                    candidato,
                                    raio=0.55,
                                )
                            atual = candidato
                            npc["posicao"] = [float(atual[0]), float(atual[1])]
                            if passo > 1e-6:
                                angulo = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
                                npc["angulo"] = float(angulo)

            deve_materializar = self._chunk_in_qualquer(atual, chunks_carregados, chunks_simulados)
            oid = int(npc.get("id", 0) or 0)
            categoria_npc = "npc_combatente" if str(npc.get("estilo") or "").strip().lower() == "combatente" else "npc_vendedor"
            obj = BANCO_DADOS.obter_objeto(oid)
            if deve_materializar:
                if not isinstance(obj, AtorServer):
                    obj = self._materializar_npc(npc)
                    registrar_diff_cb("spawn", payload=obj.serializar(), escopo={"centro": [obj.posicao[0], obj.posicao[1]], "raio": 240.0}, objeto_id=obj.Id, autor="server", categoria=categoria_npc)
                else:
                    BANCO_DADOS.atualizar_objeto(int(obj.Id), {"posicao": [float(atual[0]), float(atual[1])]})
                    obj.estado_extra["nome"] = str(npc.get("nome") or obj.estado_extra.get("nome", "NPC"))
                    obj.estado_extra["estatico"] = bool(npc.get("estatico", False))
                    obj.estado_extra["interacao"] = dict(npc.get("interacao", {}))
                    obj.estado_extra["angulo"] = float(npc.get("angulo", obj.estado_extra.get("angulo", 0.0)) or 0.0)
                    obj.estado_extra["dimensao"] = str(npc.get("dimensao") or obj.estado_extra.get("dimensao", "Mundo"))
                    registrar_diff_cb("update", payload=obj.serializar(), escopo={"centro": [obj.posicao[0], obj.posicao[1]], "raio": 240.0}, objeto_id=obj.Id, autor="server", categoria=categoria_npc)
            else:
                if isinstance(obj, AtorServer):
                    rem = BANCO_DADOS.remover_objeto(oid)
                    if rem is not None:
                        registrar_diff_cb("despawn", payload={"id": oid}, escopo={"centro": [atual[0], atual[1]], "raio": 240.0}, objeto_id=oid, autor="server", categoria=categoria_npc)

        if tick % 60 == 0:
            salvar_npcs_vendedores_estado(self._npcs)
