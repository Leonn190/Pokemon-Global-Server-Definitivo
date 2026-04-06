"""Subcérebro de partículas de XP no mundo."""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Deque, Dict, Iterable, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_perfil_personagem
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, XpMundoServer

Vector2 = Tuple[float, float]


class CerebroXpMundo:
    def __init__(self, core) -> None:
        self._core = core
        self._spawns_pendentes: Deque[Dict[str, object]] = deque()

    @staticmethod
    def _normalizar_tamanho(tamanho: str) -> str:
        t = str(tamanho or "").strip().lower()
        if t in {"pequeno", "medio", "grande"}:
            return t
        return "pequeno"

    def agendar_burst(self, origem: Vector2, total_particulas: int, tamanhos_possiveis: Iterable[str], atraso_ticks: int = 0) -> None:
        qtd = max(0, int(total_particulas or 0))
        if qtd <= 0:
            return
        pool = [self._normalizar_tamanho(x) for x in list(tamanhos_possiveis or [])]
        if not pool:
            pool = ["pequeno"]
        self._spawns_pendentes.append(
            {
                "tick": int(self._core._tick_contador + max(0, int(atraso_ticks or 0))),
                "origem": [float(origem[0]), float(origem[1])],
                "qtd": qtd,
                "pool": pool,
            }
        )

    def executar_tick(self) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        self._processar_spawns_pendentes(registrar_diff)
        ttl_ticks = int(self._core._i("xp_mundo_ttl_ticks", 600))
        ttl_fade_ticks = 10
        players = [o for o in BANCO_DADOS.listar_objetos() if isinstance(o, AtorServer)]

        for oid in list(self._core._xp_mundo_ids):
            xp_obj = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(xp_obj, XpMundoServer):
                self._core._xp_mundo_ids.discard(oid)
                continue
            estado = xp_obj.estado_extra if isinstance(xp_obj.estado_extra, dict) else {}
            if bool(estado.get("voando", False)):
                if int(self._core._tick_contador) >= int(estado.get("voando_ate_tick", self._core._tick_contador) or self._core._tick_contador):
                    destino = estado.get("pos_final") if isinstance(estado.get("pos_final"), (list, tuple)) else [xp_obj.posicao[0], xp_obj.posicao[1]]
                    xp_obj.definir_posicao(float(destino[0]), float(destino[1]))
                    estado["voando"] = False
                    BANCO_DADOS.atualizar_objeto(xp_obj.Id, {"posicao": [xp_obj.posicao[0], xp_obj.posicao[1]], "estado": estado})
                continue

            idade = int(self._core._tick_contador) - int(estado.get("tick_spawn", self._core._tick_contador) or self._core._tick_contador)
            if idade >= ttl_ticks:
                if not bool(estado.get("sumindo_ttl", False)):
                    estado["sumindo_ttl"] = True
                    estado["ttl_fade_ticks"] = int(ttl_fade_ticks)
                    estado["tick_despawn"] = int(self._core._tick_contador + ttl_fade_ticks)
                    BANCO_DADOS.atualizar_objeto(xp_obj.Id, {"estado": estado})
                    registrar_diff("update", payload={"estado": {"sumindo_ttl": True, "ttl_fade_ticks": int(ttl_fade_ticks)}}, escopo={"centro": [xp_obj.posicao[0], xp_obj.posicao[1]], "raio": 120}, objeto_id=xp_obj.Id, autor="server", categoria="xp_mundo")
                    continue
                if int(self._core._tick_contador) < int(estado.get("tick_despawn", self._core._tick_contador) or self._core._tick_contador):
                    continue
                removido = BANCO_DADOS.remover_objeto(xp_obj.Id)
                self._core._xp_mundo_ids.discard(int(xp_obj.Id))
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "sumico"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120}, objeto_id=removido.Id, autor="server", categoria="xp_mundo")
                continue

            for player in players:
                dx = float(xp_obj.posicao[0]) - float(player.posicao[0])
                dy = float(xp_obj.posicao[1]) - float(player.posicao[1])
                limite = float(xp_obj.raio_colisao) + float(player.raio_colisao)
                if (dx * dx + dy * dy) > (limite * limite):
                    continue
                ganho = player.GanharXP(int(estado.get("xp_valor", 0) or 0))
                usuario = BANCO_DADOS.usuario_por_objeto_id(int(player.Id))
                if usuario:
                    atualizar_perfil_personagem(str(usuario), dict(player.estado_extra.get("perfil", {})))
                BANCO_DADOS.atualizar_objeto(player.Id, {"estado": {"perfil": dict(player.estado_extra.get("perfil", {}))}})
                registrar_diff("update", payload={"estado": {"perfil": dict(player.estado_extra.get("perfil", {}))}, "perfil": dict(player.estado_extra.get("perfil", {})), "xp_ganho": dict(ganho)}, escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 780.0}, objeto_id=player.Id, autor="server", categoria="player")
                removido = BANCO_DADOS.remover_objeto(xp_obj.Id)
                self._core._xp_mundo_ids.discard(int(xp_obj.Id))
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "coleta"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120}, objeto_id=removido.Id, autor="server", categoria="xp_mundo")
                break

    def _processar_spawns_pendentes(self, registrar_diff) -> None:
        while self._spawns_pendentes and int(self._spawns_pendentes[0].get("tick", 0) or 0) <= int(self._core._tick_contador):
            burst = self._spawns_pendentes.popleft()
            origem = burst.get("origem") if isinstance(burst.get("origem"), (list, tuple)) else [0.0, 0.0]
            px, py = float(origem[0]), float(origem[1])
            qtd = max(1, int(burst.get("qtd", 1) or 1))
            pool = [self._normalizar_tamanho(x) for x in list(burst.get("pool") or [])] or ["pequeno"]
            angulo_base = random.uniform(0.0, math.tau)
            passo_angular = (math.tau / float(qtd)) if qtd > 0 else 0.0
            for i in range(qtd):
                tamanho = random.choice(pool)
                ang = angulo_base + (passo_angular * i)
                dist = random.uniform(0.18, 0.55)
                vel = random.uniform(2.6, 4.0)
                p1 = (px + math.cos(ang) * dist, py + math.sin(ang) * dist)
                novo_id = BANCO_DADOS.gerar_id()
                obj = XpMundoServer(
                    id_objeto=novo_id,
                    posicao=(px, py),
                    tamanho=tamanho,
                    pos_inicial=(px, py),
                    pos_final=(p1[0], p1[1]),
                    velocidade=vel,
                    tick_spawn=int(self._core._tick_contador),
                )
                BANCO_DADOS.inserir_objeto(obj)
                self._core.registrar_spawn_manual(obj)
                registrar_diff("spawn", payload=obj.serializar(), escopo={"centro": [px, py], "raio": 120}, objeto_id=obj.Id, autor="server", categoria="xp_mundo")
