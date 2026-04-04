"""Cérebro de estádios/dimensões."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import EstadioServer
from SimuladorServerJogo.Geradores.GeradorMundo import _manifesto_estadios_meta

Vector2 = Tuple[float, float]

@dataclass
class DefEstadio:
    id_estadio: int
    tipo: str
    dimensao: str
    posicao: Vector2
    chunk_largura: int = 5
    chunk_altura: int = 5


class CerebroEstadios:
    def __init__(self, core) -> None:
        self._core = core
        self._por_id: Dict[int, DefEstadio] = {}
        self._por_dimensao: Dict[str, DefEstadio] = {}
        self._obj_por_id: Dict[int, int] = {}
        self._dimensao_por_player: Dict[int, str] = {}
        self._estadio_por_player: Dict[int, int] = {}
        self._chunks_dimensao: Dict[str, Dict[Tuple[int, int], List[List[int]]]] = {}
        self._interior_spawn = (12.0, 16.0)
        self._registrar_estadios()

    def _registrar_estadios(self) -> None:
        largura, altura = BANCO_DADOS.limites_mundo()
        chunk = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
        for item in _manifesto_estadios_meta(largura=largura, altura=altura, chunk_tamanho=chunk):
            d = DefEstadio(
                id_estadio=int(item["estadio_id"]),
                tipo=str(item["tipo"]),
                dimensao=str(item["dimensao"]),
                posicao=(float(item["posicao"][0]), float(item["posicao"][1])),
            )
            self._por_id[d.id_estadio] = d
            self._por_dimensao[d.dimensao] = d
            self._chunks_dimensao[d.dimensao] = self._gerar_chunks_internos_padrao()

    @staticmethod
    def _gerar_chunks_internos_padrao() -> Dict[Tuple[int, int], List[List[int]]]:
        saida: Dict[Tuple[int, int], List[List[int]]] = {}
        for cy in range(5):
            for cx in range(5):
                saida[(cx, cy)] = [[2 for _ in range(10)] for _ in range(10)]
        return saida

    def garantir_objetos_mundo(self, registrar_diff_cb) -> None:
        for est in self._por_id.values():
            if int(est.id_estadio) in self._obj_por_id:
                if BANCO_DADOS.obter_objeto(self._obj_por_id[int(est.id_estadio)]) is not None:
                    continue
            oid = BANCO_DADOS.gerar_id()
            obj = EstadioServer(
                id_objeto=oid,
                estadio_id=int(est.id_estadio),
                tipo=est.tipo,
                dimensao_destino=est.dimensao,
                posicao=est.posicao,
                chunk_tamanho=max(1, int(BANCO_DADOS.chunk_tamanho_unidade())),
                chunk_largura=int(est.chunk_largura),
                chunk_altura=int(est.chunk_altura),
            )
            BANCO_DADOS.inserir_objeto(obj)
            self._obj_por_id[int(est.id_estadio)] = int(oid)
            registrar_diff_cb("spawn", payload=obj.serializar(), escopo={"centro": [obj.posicao[0], obj.posicao[1]], "raio": 900}, objeto_id=obj.Id, autor="server", categoria="estadio")

    def dimensao_de_objeto(self, obj) -> str:
        return str(getattr(obj, "Dimensao", "Mundo") or "Mundo")

    def dimensao_player(self, player_obj_id: int) -> str:
        oid = int(player_obj_id or 0)
        if oid <= 0:
            return "Mundo"
        if oid in self._dimensao_por_player:
            return str(self._dimensao_por_player[oid] or "Mundo")
        obj = BANCO_DADOS.obter_objeto(oid)
        if obj is None:
            return "Mundo"
        return str(getattr(obj, "Dimensao", "Mundo") or "Mundo")

    def lookup_por_id(self, estadio_id: int) -> Optional[DefEstadio]:
        return self._por_id.get(int(estadio_id or 0))

    def lookup_por_dimensao(self, dimensao: str) -> Optional[DefEstadio]:
        return self._por_dimensao.get(str(dimensao or ""))

    def chunks_dimensao(self, dimensao: str) -> Dict[Tuple[int, int], List[List[int]]]:
        if str(dimensao or "Mundo") == "Mundo":
            return {}
        base = self._chunks_dimensao.get(str(dimensao or ""))
        if not isinstance(base, dict):
            return {}
        return {k: [list(l) for l in v] for k, v in base.items()}

    def processar_interacao(self, client_id: str, payload: Dict[str, object], registrar_diff_cb) -> bool:
        usuario = str(client_id or "")
        player_id = int(BANCO_DADOS.objeto_id_por_usuario(usuario) or 0)
        if player_id <= 0:
            return False
        player = BANCO_DADOS.obter_objeto(player_id)
        if player is None:
            return False

        acao = str(payload.get("acao") or "entrar").strip().lower()
        if acao == "sair":
            return self._sair_estadio(player_id, player, registrar_diff_cb)

        estadio_id = int(payload.get("estadio_id", 0) or 0)
        est = self.lookup_por_id(estadio_id)
        if est is None:
            return False
        return self._entrar_estadio(player_id, player, est, registrar_diff_cb)

    def _entrar_estadio(self, player_id: int, player, est: DefEstadio, registrar_diff_cb) -> bool:
        if str(getattr(player, "Dimensao", "Mundo") or "Mundo") != "Mundo":
            return False
        self._dimensao_por_player[int(player_id)] = str(est.dimensao)
        self._estadio_por_player[int(player_id)] = int(est.id_estadio)
        player.Dimensao = str(est.dimensao)
        player.estado_extra["dimensao"] = str(est.dimensao)
        player.definir_posicao(*self._interior_spawn)

        registrar_diff_cb(
            "update",
            payload={"posicao": [player.posicao[0], player.posicao[1]], "estado": {"dimensao": str(est.dimensao)}},
            escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 2000},
            objeto_id=int(player.Id),
            autor="server",
            categoria="player",
        )
        registrar_diff_cb(
            "evento",
            payload={
                "tipo_transicao": "entrada_estadio",
                "estadio_id": int(est.id_estadio),
                "tipo": str(est.tipo),
                "dimensao": str(est.dimensao),
                "posicao": [player.posicao[0], player.posicao[1]],
            },
            escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 9999},
            objeto_id=int(player.Id),
            autor="server",
            categoria="dimensao_transicao",
            extras={"cliente_alvo": str(BANCO_DADOS.usuario_por_objeto_id(int(player.Id)) or "")},
        )
        return True

    def _sair_estadio(self, player_id: int, player, registrar_diff_cb) -> bool:
        est_id = int(self._estadio_por_player.get(int(player_id), 0) or 0)
        est = self.lookup_por_id(est_id)
        if est is None:
            return False
        player.Dimensao = "Mundo"
        player.estado_extra["dimensao"] = "Mundo"
        player.definir_posicao(float(est.posicao[0]), float(est.posicao[1] + 2.0))
        self._dimensao_por_player[int(player_id)] = "Mundo"

        registrar_diff_cb(
            "update",
            payload={"posicao": [player.posicao[0], player.posicao[1]], "estado": {"dimensao": "Mundo"}, "teleporte": True},
            escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 2000},
            objeto_id=int(player.Id),
            autor="server",
            categoria="player",
        )
        registrar_diff_cb(
            "evento",
            payload={"tipo_transicao": "saida_estadio", "dimensao": "Mundo", "posicao": [player.posicao[0], player.posicao[1]]},
            escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 9999},
            objeto_id=int(player.Id),
            autor="server",
            categoria="dimensao_transicao",
            extras={"cliente_alvo": str(BANCO_DADOS.usuario_por_objeto_id(int(player.Id)) or "")},
        )
        return True
