"""Banco de dados em memória do simulador de mundo online."""

from __future__ import annotations

import math
import threading
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from SimuladorServerJogo.GeradorMundo import (
    BLOCO_TAMANHO_PX,
    CHUNK_BLOCOS,
    carregar_ou_criar_estado_mundo,
)
from SimuladorServerJogo.ObjetosMundoServer import AtorServer, EstruturaNaturalServer, GameObjetoServer
from Codigo.Modulos.ConfigEstruturasNaturais import tipo_estrutura_natural_por_codigo
from Codigo.Modulos.colisor import Colisor

Vector2 = Tuple[float, float]


class BancoDadosMundo:
    def __init__(self, tamanho_celula: int = 256, chunk_tamanho_px: int = CHUNK_BLOCOS * BLOCO_TAMANHO_PX) -> None:
        self._lock = threading.Lock()
        self._objetos: Dict[int, GameObjetoServer] = {}
        self._usuarios_para_objeto: Dict[str, int] = {}
        self._indice_espacial: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
        self._next_id = 1000
        self._tamanho_celula = max(64, int(tamanho_celula))
        self._chunk_tamanho_px = max(128, int(chunk_tamanho_px))

        self._estado_mundo = carregar_ou_criar_estado_mundo()
        self._grid = self._estado_mundo.get("grid", [])
        meta = self._estado_mundo.get("meta", {}) if isinstance(self._estado_mundo.get("meta", {}), dict) else {}
        self._chunk_blocos = int(meta.get("chunk_blocos", CHUNK_BLOCOS))
        self._largura_blocos = int(meta.get("largura_blocos", len(self._grid[0]) if self._grid else 0))
        self._altura_blocos = int(meta.get("altura_blocos", len(self._grid)))
        self._gerar_estruturas_naturais_no_mapa()

    def recarregar_mundo(self, estado_mundo: Dict[str, object], limpar_objetos: bool = False) -> None:
        with self._lock:
            self._estado_mundo = estado_mundo if isinstance(estado_mundo, dict) else {}
            self._grid = self._estado_mundo.get("grid", [])
            meta = self._estado_mundo.get("meta", {}) if isinstance(self._estado_mundo.get("meta", {}), dict) else {}
            self._chunk_blocos = max(1, int(meta.get("chunk_blocos", CHUNK_BLOCOS)))
            self._largura_blocos = int(meta.get("largura_blocos", len(self._grid[0]) if self._grid else 0))
            self._altura_blocos = int(meta.get("altura_blocos", len(self._grid)))

            if limpar_objetos:
                self._objetos.clear()
                self._usuarios_para_objeto.clear()
                self._indice_espacial.clear()
            self._gerar_estruturas_naturais_no_mapa()

    def _gerar_estruturas_naturais_no_mapa(self) -> None:
        grid_nat = self._estado_mundo.get("grid_estruturas_naturais", [])
        if not isinstance(grid_nat, list) or not grid_nat:
            return

        ids_remover = [oid for oid, obj in self._objetos.items() if obj.tipo_classe == "estrutura_natural"]
        for oid in ids_remover:
            obj_antigo = self._objetos.pop(oid, None)
            if obj_antigo is not None:
                self._indice_espacial[self._celula(obj_antigo.posicao)].discard(oid)

        for y, linha in enumerate(grid_nat):
            if not isinstance(linha, list):
                continue
            for x, valor in enumerate(linha):
                try:
                    tile_nat = int(valor)
                except (TypeError, ValueError):
                    continue
                cfg = tipo_estrutura_natural_por_codigo(tile_nat)
                if not cfg:
                    continue
                oid = self._next_id
                self._next_id += 1
                while oid in self._objetos:
                    oid = self._next_id
                    self._next_id += 1

                obj = EstruturaNaturalServer(
                    id_objeto=oid,
                    tipo=cfg["subtipo"],
                    nome=cfg["nome"],
                    sprite=cfg["sprite"],
                    posicao=(float(x), float(y)),
                    raio_colisao=cfg["raio_colisao"],
                    raio_interacao=cfg["raio_interacao"],
                    campo=float(cfg.get("campo", 0.0) or 0.0),
                    intensidade=float(cfg.get("intensidade", 0.0) or 0.0),
                    codigo_natural=tile_nat,
                )
                obj.tipo_classe = "estrutura_natural"
                self._objetos[obj.Id] = obj
                self._indice_espacial[self._celula(obj.posicao)].add(obj.Id)

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

    def inserir_objeto(self, obj: GameObjetoServer) -> None:
        with self._lock:
            if obj.Id in self._objetos:
                raise ValueError(f"ID já existe: {obj.Id}")
            self._objetos[obj.Id] = obj
            self._indice_espacial[self._celula(obj.posicao)].add(obj.Id)

    def remover_objeto(self, objeto_id: int) -> Optional[GameObjetoServer]:
        with self._lock:
            obj = self._objetos.pop(int(objeto_id), None)
            if obj is None:
                return None
            self._indice_espacial[self._celula(obj.posicao)].discard(obj.Id)
            return obj

    def atualizar_objeto(self, objeto_id: int, campos: Dict[str, object]) -> Optional[GameObjetoServer]:
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

            estado = campos.get("estado")
            if isinstance(estado, dict):
                obj.estado_extra.update(estado)

            if "posicao" in campos and str(obj.tipo_classe).startswith("entidade"):
                self._aplicar_campos_forca_em_entidade(obj, posicao_anterior)

            celula_nova = self._celula(obj.posicao)
            if celula_nova != celula_antiga:
                self._indice_espacial[celula_antiga].discard(obj.Id)
                self._indice_espacial[celula_nova].add(obj.Id)

            return obj

    def _aplicar_campos_forca_em_entidade(self, entidade: GameObjetoServer, posicao_anterior: Vector2) -> None:
        x0, y0 = float(posicao_anterior[0]), float(posicao_anterior[1])
        x1, y1 = float(entidade.posicao[0]), float(entidade.posicao[1])
        mvx, mvy = (x1 - x0), (y1 - y0)
        px, py = x1, y1
        raio_entidade = max(0.0, float(getattr(entidade, "raio_colisao", 0.0)))

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

    def obter_objeto(self, objeto_id: int) -> Optional[GameObjetoServer]:
        with self._lock:
            return self._objetos.get(int(objeto_id))

    def usuario_por_objeto_id(self, objeto_id: int) -> Optional[str]:
        with self._lock:
            for usuario, oid in self._usuarios_para_objeto.items():
                if oid == int(objeto_id):
                    return usuario
        return None

    def buscar_proximos(self, posicao: Vector2, raio: float) -> List[GameObjetoServer]:
        raio = max(0.0, float(raio))
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
                    obj.definir_posicao(float(posicao[0]), float(posicao[1]))
                    return obj

            novo_id = self._next_id
            self._next_id += 1
            ator = AtorServer(id_objeto=novo_id, usuario=usuario, skin=skin, posicao=posicao)
            self._usuarios_para_objeto[usuario] = ator.Id
            self._objetos[ator.Id] = ator
            self._indice_espacial[self._celula(ator.posicao)].add(ator.Id)
            return ator

    def chunk_em_grade(self, chunk_xy: Tuple[int, int]) -> List[List[int]]:
        cx, cy = chunk_xy
        x0 = cx * self._chunk_blocos
        y0 = cy * self._chunk_blocos

        grid: List[List[int]] = []
        for by in range(self._chunk_blocos):
            gy = y0 + by
            linha: List[int] = []
            for bx in range(self._chunk_blocos):
                gx = x0 + bx
                if 0 <= gy < self._altura_blocos and 0 <= gx < self._largura_blocos:
                    linha.append(int(self._grid[gy][gx]))
                else:
                    linha.append(0)
            grid.append(linha)
        return grid

    def chunk_tamanho_unidade(self) -> int:
        return max(1, int(self._chunk_blocos))

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
