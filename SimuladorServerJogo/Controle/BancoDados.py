"""Banco de dados em memória do simulador de mundo online."""

from __future__ import annotations

import math
import threading
from collections import defaultdict
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from SimuladorServerJogo.Geradores.GeradorMundo import (
    BLOCO_TAMANHO_PX,
    CHUNK_BLOCOS,
    PASTA_WORLD_CHUNKS,
    carregar_estado_mundo,
)
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, EstruturaNaturalServer, EstadioServer
from SimuladorServerJogo.Regras.Loader import carregar_regras_estruturas_naturais
from Codigo.Modulos.Colisor import Colisor


Vector2 = Tuple[float, float]


class BancoDadosMundo:
    def __init__(self, tamanho_celula: int = 256, chunk_tamanho_px: int = CHUNK_BLOCOS * BLOCO_TAMANHO_PX) -> None:
        self._lock = threading.RLock()
        self._objetos: Dict[int, object] = {}
        self._usuarios_para_objeto: Dict[str, int] = {}
        self._indice_espacial: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
        self._next_id = 1000
        self._tamanho_celula = max(64, int(tamanho_celula))
        self._chunk_tamanho_px = max(128, int(chunk_tamanho_px))

        self._estado_mundo = carregar_estado_mundo()
        self._grid: List[List[int]] = []
        self._chunks_cache: Dict[Tuple[int, int], Dict[str, List[List[int]]]] = {}
        self._chunk_sets_cache: Dict[Tuple[int, int], Dict[Tuple[int, int], Dict[str, List[List[int]]]]] = {}
        self._chunks_estruturas_carregados: Set[Tuple[int, int]] = set()
        self._chunks_dir = self._resolver_chunks_dir()
        meta = self._estado_mundo.get("meta", {}) if isinstance(self._estado_mundo.get("meta", {}), dict) else {}
        self._chunk_blocos = int(CHUNK_BLOCOS)
        self._chunk_blocos_disco = max(1, int(meta.get("chunk_blocos_disco", meta.get("chunk_blocos", CHUNK_BLOCOS))))
        self._chunks_por_arquivo = max(1, int(meta.get("chunks_por_arquivo", 10)))
        self._largura_blocos = int(meta.get("largura_blocos", 0))
        self._altura_blocos = int(meta.get("altura_blocos", 0))
        self._regras_estruturas = self._carregar_regras_estruturas_naturais()
        self._estado_estruturas_naturais: Dict[int, int] = self._carregar_estruturas_tocadas(self._estado_mundo)
        self._gerar_estruturas_naturais_no_mapa()
        self._gerar_estadios_do_meta()

    def _carregar_regras_estruturas_naturais(self) -> Dict[int, Dict[str, object]]:
        bruto = carregar_regras_estruturas_naturais()
        tipos = bruto.get("tipos") if isinstance(bruto.get("tipos"), dict) else {}
        saida: Dict[int, Dict[str, object]] = {}
        for chave, cfg in tipos.items():
            try:
                codigo = int(chave)
            except (TypeError, ValueError):
                continue
            if not isinstance(cfg, dict):
                continue
            saida[codigo] = dict(cfg)
        return saida

    @staticmethod
    def _carregar_estruturas_tocadas(estado_mundo: Dict[str, object]) -> Dict[int, int]:
        bruto = estado_mundo.get("estruturas_naturais_tocadas", {}) if isinstance(estado_mundo, dict) else {}
        if not isinstance(bruto, dict):
            return {}
        saida: Dict[int, int] = {}
        for chave, valor in bruto.items():
            try:
                oid = int(chave)
                qtd = max(0, int(valor))
            except (TypeError, ValueError):
                continue
            saida[oid] = qtd
        return saida

    @staticmethod
    def _id_estrutura_natural(codigo: int, gx: int, gy: int) -> int:
        c = int(codigo) & 0xFF
        x = int(gx) & 0x0FFFFF
        y = int(gy) & 0xFFFFFF
        return int((1 << 62) | (c << 44) | (x << 24) | y)

    def _resolver_chunks_dir(self) -> Path:
        candidatos = [
            PASTA_WORLD_CHUNKS,
            Path(__file__).resolve().parent / "world_chunks",
            Path(__file__).resolve().parents[2] / "world_chunks",
        ]
        for pasta in candidatos:
            if pasta.exists() and pasta.is_dir():
                return pasta
        return PASTA_WORLD_CHUNKS

    def recarregar_mundo(self, estado_mundo: Dict[str, object], limpar_objetos: bool = False) -> None:
        with self._lock:
            self._estado_mundo = estado_mundo if isinstance(estado_mundo, dict) else {}
            self._grid = []
            self._chunks_cache.clear()
            self._chunk_sets_cache.clear()
            self._chunks_estruturas_carregados.clear()
            meta = self._estado_mundo.get("meta", {}) if isinstance(self._estado_mundo.get("meta", {}), dict) else {}
            self._chunk_blocos = max(1, int(CHUNK_BLOCOS))
            self._chunk_blocos_disco = max(1, int(meta.get("chunk_blocos_disco", meta.get("chunk_blocos", CHUNK_BLOCOS))))
            self._chunks_por_arquivo = max(1, int(meta.get("chunks_por_arquivo", 10)))
            self._largura_blocos = int(meta.get("largura_blocos", 0))
            self._altura_blocos = int(meta.get("altura_blocos", 0))
            self._regras_estruturas = self._carregar_regras_estruturas_naturais()
            self._estado_estruturas_naturais = self._carregar_estruturas_tocadas(self._estado_mundo)

            if limpar_objetos:
                self._objetos.clear()
                self._usuarios_para_objeto.clear()
                self._indice_espacial.clear()
            self._gerar_estruturas_naturais_no_mapa()
            self._gerar_estadios_do_meta()

    def _gerar_estruturas_naturais_no_mapa(self) -> None:
        with self._lock:
            ids_remover = [oid for oid, obj in self._objetos.items() if obj.tipo_classe == "estrutura_natural"]
            for oid in ids_remover:
                obj_antigo = self._objetos.pop(oid, None)
                if obj_antigo is not None:
                    self._indice_espacial[self._celula(obj_antigo.posicao)].discard(oid)
            self._chunks_estruturas_carregados.clear()

    def _tile_estrutura_em(self, gx: int, gy: int) -> int:
        dc = max(1, int(self._chunk_blocos_disco))
        cx = gx // dc
        cy = gy // dc
        lx = gx % dc
        ly = gy % dc
        chunk = self._carregar_chunk(cx, cy)
        grid = chunk.get("grid_estruturas", [])
        if 0 <= ly < len(grid) and isinstance(grid[ly], list) and 0 <= lx < len(grid[ly]):
            try:
                return int(grid[ly][lx])
            except (TypeError, ValueError):
                return 0
        return 0

    def _assegurar_estruturas_chunk(self, cx: int, cy: int) -> None:
        with self._lock:
            chave = self.normalizar_chunk((cx, cy))
            if chave in self._chunks_estruturas_carregados:
                return

            x0 = chave[0] * self._chunk_blocos
            y0 = chave[1] * self._chunk_blocos
            x1 = min(self._largura_blocos - 1, x0 + self._chunk_blocos - 1)
            y1 = min(self._altura_blocos - 1, y0 + self._chunk_blocos - 1)
            if x1 < x0 or y1 < y0:
                self._chunks_estruturas_carregados.add(chave)
                return

            for gy in range(y0, y1 + 1):
                for gx in range(x0, x1 + 1):
                    tile_nat = self._tile_estrutura_em(gx, gy)
                    cfg = self._regras_estruturas.get(int(tile_nat))
                    if not cfg:
                        continue
                    oid = self._id_estrutura_natural(tile_nat, gx, gy)
                    qtd_base = max(0, int(cfg.get("quantidade", 0) or 0))
                    qtd_restante = int(self._estado_estruturas_naturais.get(oid, qtd_base))
                    if qtd_restante <= 0:
                        continue

                    obj = EstruturaNaturalServer(
                        id_objeto=oid,
                        tipo=str(cfg.get("subtipo", "natural")),
                        nome=str(cfg.get("nome", "Estrutura")),
                        sprite=str(cfg.get("sprite", "")),
                        posicao=(float(gx), float(gy)),
                        raio_colisao=float(cfg.get("raio_colisao", 0.8) or 0.8),
                        raio_interacao=float(cfg.get("raio_interacao", cfg.get("raio_colisao", 0.8)) or 0.8),
                        campo=float(cfg.get("campo", 0.0) or 0.0),
                        intensidade=float(cfg.get("intensidade", 0.0) or 0.0),
                        codigo_natural=tile_nat,
                        quantidade=qtd_restante,
                        material=str(cfg.get("material", "") or ""),
                        estilo=str(cfg.get("estilo", "") or ""),
                        dureza=int(cfg.get("dureza", 1) or 1),
                    )
                    obj.tipo_classe = "estrutura_natural"
                    self._objetos[obj.Id] = obj
                    self._indice_espacial[self._celula(obj.posicao)].add(obj.Id)

            self._chunks_estruturas_carregados.add(chave)



    def _gerar_estadios_do_meta(self) -> None:
        with self._lock:
            ids_remover = [oid for oid, obj in self._objetos.items() if getattr(obj, "tipo_classe", "") == "entidade_estadio"]
            for oid in ids_remover:
                obj = self._objetos.pop(oid, None)
                if obj is not None:
                    self._indice_espacial[self._celula(obj.posicao)].discard(oid)

            meta = self._estado_mundo.get("meta", {}) if isinstance(self._estado_mundo.get("meta"), dict) else {}
            estadios = meta.get("estadios", []) if isinstance(meta.get("estadios"), list) else []
            for idx, item in enumerate(estadios):
                if not isinstance(item, dict):
                    continue
                estadio_id = int(item.get("estadio_id", item.get("id", 0)) or 0)
                pos = item.get("posicao") if isinstance(item.get("posicao"), (list, tuple)) and len(item.get("posicao")) == 2 else [0.0, 0.0]
                if estadio_id <= 0:
                    estadio_id = 1_900_000_000 + int(idx)
                existente = self._objetos.get(estadio_id)
                if existente is not None and getattr(existente, "tipo_classe", "") != "entidade_estadio":
                    estadio_id = 1_900_000_000 + int(idx)
                while estadio_id in self._objetos and getattr(self._objetos.get(estadio_id), "tipo_classe", "") != "entidade_estadio":
                    estadio_id += 1
                obj = EstadioServer(
                    id_objeto=estadio_id,
                    tipo_estadio=str(item.get("tipo") or "normal"),
                    dimensao=str(item.get("dimensao") or "EstadioNormal"),
                    posicao=(float(pos[0]), float(pos[1])),
                    raio_elipse_x=float(item.get("raio_elipse_x", 24.0) or 24.0),
                    raio_elipse_y=float(item.get("raio_elipse_y", 24.0) or 24.0),
                )
                self._objetos[obj.Id] = obj
                self._indice_espacial[self._celula(obj.posicao)].add(obj.Id)

    def _nova_grade_vazia(self) -> List[List[int]]:
        return [[0 for _ in range(self._chunk_blocos_disco)] for _ in range(self._chunk_blocos_disco)]

    def _carregar_chunk_set(self, chave: Tuple[int, int], chunks_dir_atual: Path) -> Optional[Dict[str, List[List[int]]]]:
        grupo_x = chave[0] // self._chunks_por_arquivo
        grupo_y = chave[1] // self._chunks_por_arquivo
        cache_grupo = self._chunk_sets_cache.get((grupo_x, grupo_y))
        if cache_grupo is None:
            arquivo_grupo = self._chunks_dir / f"chunk_set_{grupo_x}_{grupo_y}.json"
            if not arquivo_grupo.exists() and chunks_dir_atual != self._chunks_dir:
                arquivo_grupo = chunks_dir_atual / f"chunk_set_{grupo_x}_{grupo_y}.json"
            if arquivo_grupo.exists():
                with arquivo_grupo.open("r", encoding="utf-8") as f:
                    payload_grupo = json.load(f)
                chunks_indexados: Dict[Tuple[int, int], Dict[str, List[List[int]]]] = {}
                if isinstance(payload_grupo, dict):
                    chunks = payload_grupo.get("chunks", [])
                    if isinstance(chunks, list):
                        for item in chunks:
                            if not isinstance(item, dict):
                                continue
                            try:
                                icx = int(item.get("chunk_x", -1))
                                icy = int(item.get("chunk_y", -1))
                            except (TypeError, ValueError):
                                continue
                            chunks_indexados[(icx, icy)] = {
                                "grid_blocos": item.get("grid_blocos", []) if isinstance(item.get("grid_blocos", []), list) else [],
                                "grid_biomas": item.get("grid_biomas", []) if isinstance(item.get("grid_biomas", []), list) else [],
                                "grid_estruturas": item.get("grid_estruturas", []) if isinstance(item.get("grid_estruturas", []), list) else [],
                            }
                self._chunk_sets_cache[(grupo_x, grupo_y)] = chunks_indexados
                for chave_chunk, dados_chunk in chunks_indexados.items():
                    self._chunks_cache[chave_chunk] = dados_chunk
                cache_grupo = chunks_indexados
            else:
                cache_grupo = {}
        cache_chunk = cache_grupo.get(chave)
        if cache_chunk is not None:
            self._chunks_cache[chave] = cache_chunk
            return cache_chunk
        return None

    def _carregar_chunk(self, cx: int, cy: int) -> Dict[str, List[List[int]]]:
        with self._lock:
            chave = (int(cx), int(cy))
            cache = self._chunks_cache.get(chave)
            if cache is not None:
                return cache

            chunks_dir_atual = self._chunks_dir
            self._chunks_dir = self._resolver_chunks_dir()

            if self._chunks_por_arquivo > 1:
                cache_chunk = self._carregar_chunk_set(chave, chunks_dir_atual)
                if cache_chunk is not None:
                    return cache_chunk

            arquivo = self._chunks_dir / f"chunk_{chave[0]}_{chave[1]}.json"
            if not arquivo.exists() and chunks_dir_atual != self._chunks_dir:
                arquivo = chunks_dir_atual / f"chunk_{chave[0]}_{chave[1]}.json"

            if not arquivo.exists() and self._chunks_por_arquivo <= 1:
                cache_chunk = self._carregar_chunk_set(chave, chunks_dir_atual)
                if cache_chunk is not None:
                    return cache_chunk

            if arquivo.exists():
                with arquivo.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
            else:
                cache = {
                    "grid_blocos": self._nova_grade_vazia(),
                    "grid_biomas": self._nova_grade_vazia(),
                    "grid_estruturas": self._nova_grade_vazia(),
                }
                self._chunks_cache[chave] = cache
                return cache
            if not isinstance(payload, dict):
                raise ValueError(f"Chunk inválido: {arquivo}")

            grid = payload.get("grid_blocos", [])
            grid_biomas = payload.get("grid_biomas", [])
            grid_estruturas = payload.get("grid_estruturas", [])
            cache = {
                "grid_blocos": grid if isinstance(grid, list) else [],
                "grid_biomas": grid_biomas if isinstance(grid_biomas, list) else [],
                "grid_estruturas": grid_estruturas if isinstance(grid_estruturas, list) else [],
            }
            self._chunks_cache[chave] = cache
            return cache

    def tile_em(self, gx: int, gy: int) -> int:
        with self._lock:
            if gx < 0 or gy < 0 or gx >= self._largura_blocos or gy >= self._altura_blocos:
                return 0
            dc = max(1, int(self._chunk_blocos_disco))
            cx = gx // dc
            cy = gy // dc
            lx = gx % dc
            ly = gy % dc
            chunk = self._carregar_chunk(cx, cy)
            grid = chunk.get("grid_blocos", [])
            if 0 <= ly < len(grid) and isinstance(grid[ly], list) and 0 <= lx < len(grid[ly]):
                try:
                    return int(grid[ly][lx])
                except (TypeError, ValueError):
                    return 0
            return 0

    def limites_mundo(self) -> Tuple[int, int]:
        with self._lock:
            return (max(1, int(self._largura_blocos)), max(1, int(self._altura_blocos)))

    def gerar_id(self) -> int:
        with self._lock:
            novo = self._next_id
            self._next_id += 1
            while novo in self._objetos:
                novo = self._next_id
                self._next_id += 1
            return novo

    def _celula(self, posicao: Vector2) -> Tuple[int, int]:
        return (int(math.floor(posicao[0] / self._tamanho_celula)), int(math.floor(posicao[1] / self._tamanho_celula)))

    def inserir_objeto(self, obj) -> None:
        with self._lock:
            if obj.Id in self._objetos:
                raise ValueError(f"ID já existe: {obj.Id}")
            self._objetos[obj.Id] = obj
            self._indice_espacial[self._celula(obj.posicao)].add(obj.Id)

    def remover_objeto(self, objeto_id: int) -> Optional[object]:
        with self._lock:
            obj = self._objetos.pop(int(objeto_id), None)
            if obj is None:
                return None
            self._indice_espacial[self._celula(obj.posicao)].discard(obj.Id)
            return obj

    def atualizar_objeto(self, objeto_id: int, campos: Dict[str, object]) -> Optional[object]:
        with self._lock:
            obj = self._objetos.get(int(objeto_id))
            if obj is None:
                return None

            celula_antiga = self._celula(obj.posicao)
            posicao_anterior = obj.posicao
            if "posicao" in campos:
                pos = campos["posicao"]
                obj.definir_posicao(float(pos[0]), float(pos[1]))

            for campo in ("raio_colisao", "raio_interacao", "campo", "intensidade"):
                if campo in campos:
                    setattr(obj, campo, float(campos[campo]))
            if "raio_colisao" in campos and getattr(obj, "Colisor", None) is not None:
                obj.Colisor.raio_colisao = float(getattr(obj, "raio_colisao", obj.Colisor.raio_colisao))
            if "raio_interacao" in campos and getattr(obj, "Colisor", None) is not None:
                obj.Colisor.raio_interacao = float(getattr(obj, "raio_interacao", obj.Colisor.raio_interacao))

            estado = campos.get("estado")
            if isinstance(estado, dict):
                obj.estado_extra.update(estado)

            if str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower() == "player":
                if "nome" in campos:
                    obj.estado_extra["nome"] = str(campos.get("nome") or obj.estado_extra.get("usuario", ""))
                if "skin" in campos:
                    obj.estado_extra["skin"] = str(campos.get("skin") or obj.estado_extra.get("skin", "S1"))
                if "perfil" in campos and isinstance(campos.get("perfil"), dict):
                    obj.estado_extra["perfil"] = dict(campos.get("perfil") or {})
                if "inventario" in campos and isinstance(campos.get("inventario"), dict):
                    obj.estado_extra["inventario"] = dict(campos.get("inventario") or {})
                if "slot_selecionado" in campos:
                    try:
                        obj.estado_extra["slot_selecionado"] = int(campos.get("slot_selecionado", 0) or 0)
                    except Exception:
                        pass

            if "posicao" in campos and str(obj.tipo_classe).startswith("entidade"):
                self._aplicar_campos_forca_em_entidade(obj, posicao_anterior)

            celula_nova = self._celula(obj.posicao)
            if celula_nova != celula_antiga:
                self._indice_espacial[celula_antiga].discard(obj.Id)
                self._indice_espacial[celula_nova].add(obj.Id)

            return obj

    def _aplicar_campos_forca_em_entidade(self, entidade, posicao_anterior: Vector2) -> None:
        x0, y0 = float(posicao_anterior[0]), float(posicao_anterior[1])
        x1, y1 = float(entidade.posicao[0]), float(entidade.posicao[1])
        mvx, mvy = (x1 - x0), (y1 - y0)
        px, py = x1, y1
        raio_entidade = max(0.0, float(getattr(entidade, "raio_colisao", 0.0)))

        # Nova regra: colisão/repulsão local por raio fixo de 10 tiles para pokémons.
        # Para demais entidades, mantém comportamento amplo atual.
        is_pokemon = str(getattr(entidade, "tipo_classe", "")).lower() in ("pokemon", "entidade_pokemon")
        if is_pokemon:
            estruturas = self._estruturas_proximas_por_raio((px, py), raio_tiles=10.0)
        else:
            estruturas = [o for o in self._objetos.values() if str(getattr(o, "tipo_classe", "")).startswith("estrutura")]
        for estrutura in estruturas:
            if estrutura.Id == entidade.Id:
                continue
            campo = max(0.0, float(getattr(estrutura, "campo", 0.0)))
            intensidade = max(0.0, float(getattr(estrutura, "intensidade", 0.0)))
            if campo <= 0.0 and intensidade <= 0.0:
                continue

            mvx, mvy = Colisor.aplicar_repulsao_circular(
                posicao_entidade=(px, py),
                movimento_entidade=(mvx, mvy),
                centro_estrutura=estrutura.posicao,
                raio_estrutura=float(getattr(estrutura, "raio_colisao", 0.0)),
                campo=campo,
                intensidade=intensidade,
                delta_time=(1.0 / 60.0),
                raio_entidade=raio_entidade,
            )
            px = x0 + mvx
            py = y0 + mvy

        entidade.definir_posicao(px, py)

    def _estruturas_proximas_por_raio(self, posicao: Vector2, raio_tiles: float = 10.0) -> List[object]:
        """Busca estruturas candidatas por raio fixo sem depender de chunks para colisão local."""
        raio = max(0.1, float(raio_tiles))
        cx, cy = self._celula(posicao)
        alcance = int(math.ceil(raio / self._tamanho_celula)) + 1
        ids: Set[int] = set()
        with self._lock:
            for ix in range(cx - alcance, cx + alcance + 1):
                for iy in range(cy - alcance, cy + alcance + 1):
                    ids.update(self._indice_espacial.get((ix, iy), set()))

            candidatos = [self._objetos[i] for i in ids if i in self._objetos]

        px, py = float(posicao[0]), float(posicao[1])
        raio2 = raio * raio
        saida = []
        for obj in candidatos:
            if not str(getattr(obj, "tipo_classe", "")).startswith("estrutura"):
                continue
            ox, oy = obj.posicao
            if ((ox - px) ** 2 + (oy - py) ** 2) <= raio2:
                saida.append(obj)
        return saida

    def contar_subtipo_entidade(self, subtipo: str) -> int:
        alvo = str(subtipo or "").strip().lower()
        with self._lock:
            return sum(1 for o in self._objetos.values() if str(getattr(o, "estado_extra", {}).get("subtipo", "")).strip().lower() == alvo)

    def obter_objeto(self, objeto_id: int) -> Optional[object]:
        with self._lock:
            return self._objetos.get(int(objeto_id))

    def registrar_quantidade_estrutura(self, estrutura_id: int, quantidade_restante: int) -> None:
        with self._lock:
            oid = int(estrutura_id)
            qtd = max(0, int(quantidade_restante or 0))
            self._estado_estruturas_naturais[oid] = qtd

    def exportar_estruturas_tocadas(self) -> Dict[str, int]:
        with self._lock:
            return {str(oid): int(qtd) for oid, qtd in self._estado_estruturas_naturais.items()}


    def objeto_id_por_usuario(self, usuario: str) -> int:
        with self._lock:
            return int(self._usuarios_para_objeto.get(str(usuario), 0) or 0)

    def listar_objetos(self) -> List[object]:
        with self._lock:
            return list(self._objetos.values())
    def usuario_por_objeto_id(self, objeto_id: int) -> Optional[str]:
        with self._lock:
            for usuario, oid in self._usuarios_para_objeto.items():
                if oid == int(objeto_id):
                    return usuario
        return None

    def buscar_proximos(self, posicao: Vector2, raio: float) -> List[object]:
        raio = max(0.0, float(raio))
        chunk_tamanho = self.chunk_tamanho_unidade()
        if chunk_tamanho > 0:
            alcance_chunk = max(0, int(math.ceil(raio / chunk_tamanho)))
            for c in self.chunks_proximos(posicao, raio_chunks=alcance_chunk):
                self._assegurar_estruturas_chunk(c[0], c[1])
        cx, cy = self._celula(posicao)
        alcance = int(math.ceil(raio / self._tamanho_celula)) + 1
        ids: Set[int] = set()
        with self._lock:
            for ix in range(cx - alcance, cx + alcance + 1):
                for iy in range(cy - alcance, cy + alcance + 1):
                    ids.update(self._indice_espacial.get((ix, iy), set()))
            objetos = [self._objetos[i] for i in ids if i in self._objetos]

        px, py = posicao
        return [o for o in objetos if math.hypot(o.posicao[0] - px, o.posicao[1] - py) <= raio]

    def garantir_player(self, usuario: str, skin: str, posicao: Vector2 = (0.0, 0.0)) -> AtorServer:
        with self._lock:
            objeto_id = self._usuarios_para_objeto.get(usuario)
            if objeto_id and objeto_id in self._objetos:
                obj = self._objetos[objeto_id]
                if isinstance(obj, AtorServer):
                    obj.estado_extra["skin"] = skin
                    obj.estado_extra.setdefault("dimensao", "Mundo")
                    obj.definir_posicao(float(posicao[0]), float(posicao[1]))
                    return obj

            novo_id = self._next_id
            self._next_id += 1
            ator = AtorServer(id_objeto=novo_id, usuario=usuario, skin=skin, posicao=posicao, dimensao="Mundo")
            self._usuarios_para_objeto[usuario] = ator.Id
            self._objetos[ator.Id] = ator
            self._indice_espacial[self._celula(ator.posicao)].add(ator.Id)
            return ator

    def chunk_em_grade(self, chunk_xy: Tuple[int, int]) -> List[List[int]]:
        cx, cy = self.normalizar_chunk(chunk_xy)
        self._assegurar_estruturas_chunk(cx, cy)
        x0 = cx * self._chunk_blocos
        y0 = cy * self._chunk_blocos

        grid: List[List[int]] = []
        for by in range(self._chunk_blocos):
            gy = y0 + by
            linha: List[int] = []
            for bx in range(self._chunk_blocos):
                gx = x0 + bx
                if 0 <= gy < self._altura_blocos and 0 <= gx < self._largura_blocos:
                    linha.append(self.tile_em(gx, gy))
                else:
                    linha.append(0)
            grid.append(linha)
        return grid

    def chunk_tamanho_unidade(self) -> int:
        return max(1, int(self._chunk_blocos))

    def total_chunks(self) -> Tuple[int, int]:
        chunk_tamanho = self.chunk_tamanho_unidade()
        largura, altura = self.limites_mundo()
        return (max(1, int(math.ceil(largura / chunk_tamanho))), max(1, int(math.ceil(altura / chunk_tamanho))))

    def normalizar_chunk(self, chunk_xy: Tuple[int, int]) -> Tuple[int, int]:
        tx, ty = self.total_chunks()
        return (int(chunk_xy[0]) % tx, int(chunk_xy[1]) % ty)

    def chunk_da_posicao(self, posicao: Vector2) -> Tuple[int, int]:
        chunk_tamanho = self.chunk_tamanho_unidade()
        return self.normalizar_chunk((int(math.floor(float(posicao[0]) / chunk_tamanho)), int(math.floor(float(posicao[1]) / chunk_tamanho))))

    def chunks_proximos(self, posicao: Vector2, raio_chunks: int = 1) -> List[Tuple[int, int]]:
        chunk_tamanho = self.chunk_tamanho_unidade()
        largura, altura = self.limites_mundo()
        total_chunks_x = max(1, int(math.ceil(largura / chunk_tamanho)))
        total_chunks_y = max(1, int(math.ceil(altura / chunk_tamanho)))

        cpx = int(math.floor(posicao[0] / chunk_tamanho)) % total_chunks_x
        cpy = int(math.floor(posicao[1] / chunk_tamanho)) % total_chunks_y
        coords = []
        vistos: Set[Tuple[int, int]] = set()
        for dx in range(-raio_chunks, raio_chunks + 1):
            for dy in range(-raio_chunks, raio_chunks + 1):
                chunk = ((cpx + dx) % total_chunks_x, (cpy + dy) % total_chunks_y)
                if chunk in vistos:
                    continue
                vistos.add(chunk)
                coords.append(chunk)
        return coords


BANCO_DADOS = BancoDadosMundo()
