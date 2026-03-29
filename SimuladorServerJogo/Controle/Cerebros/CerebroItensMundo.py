"""Subcérebro de itens mundo (lógica real)."""

from __future__ import annotations

import math
import time
from typing import Dict, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import ItemMundoServer
from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada

Chunk = Tuple[int, int]


class CerebroItensMundo:
    def __init__(self, core) -> None:
        self._core = core

    def registrar_drop(self, client_id: str, payload: Dict[str, object]) -> bool:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        usuario = str(client_id or "").strip()
        player_id = int(BANCO_DADOS.objeto_id_por_usuario(usuario) or 0)
        dono_obj = BANCO_DADOS.obter_objeto(player_id) if player_id > 0 else None
        if dono_obj is None:
            return True

        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        item_base_id = str(item.get("Code") or payload.get("item_base_id") or "")
        quantidade = max(1, int(item.get("quantidade") or payload.get("quantidade") or 1))
        item_dados = self._core._servico_inventario.normalizar_item({"Code": item_base_id, "Nome": item.get("Nome") or payload.get("item_nome") or "Item", "quantidade": quantidade})
        item_nome = str(item_dados.get("Nome") or "Item")
        item_base_id = str(item_dados.get("Code") or item_base_id)
        token = str(payload.get("token") or "").strip()

        p0 = payload.get("pos_inicial") if isinstance(payload.get("pos_inicial"), (list, tuple)) and len(payload.get("pos_inicial")) == 2 else [dono_obj.posicao[0], dono_obj.posicao[1]]
        p1 = payload.get("pos_final") if isinstance(payload.get("pos_final"), (list, tuple)) and len(payload.get("pos_final")) == 2 else list(p0)
        dx = float(p1[0]) - float(p0[0]); dy = float(p1[1]) - float(p0[1])
        dist = math.hypot(dx, dy) or 1.0
        destino = [float(p0[0]) + (dx / dist) * min(1.0, dist), float(p0[1]) + (dy / dist) * min(1.0, dist)]
        velocidade = 3.0
        cliente_ms = int(payload.get("instante_cliente_ms", 0) or 0)
        atraso_ms = max(0, int(time.time() * 1000) - cliente_ms) if cliente_ms > 0 else 0
        velocidade_visual = min(9.0, velocidade + (atraso_ms / 1000.0) * 1.5)

        registrar_diff("spawn", payload={"token": token, "item_nome": item_nome, "item_base_id": item_base_id, "item_dados": dict(item_dados), "quantidade": quantidade, "pos_inicial": [float(p0[0]), float(p0[1])], "pos_final": [float(destino[0]), float(destino[1])], "velocidade_tiles_s": float(velocidade_visual), "dono_id": int(player_id)}, escopo={"centro": [float(p0[0]), float(p0[1])], "raio": 120}, objeto_id=int(player_id), autor=usuario, categoria="item_mundo_lancamento")

        novo_id = BANCO_DADOS.gerar_id()
        obj = ItemMundoServer(id_objeto=novo_id, posicao=(float(p0[0]), float(p0[1])), dono_id=player_id, item_nome=item_nome, item_base_id=item_base_id, quantidade=quantidade, pos_inicial=(float(p0[0]), float(p0[1])), pos_final=(float(destino[0]), float(destino[1])), velocidade=velocidade, tick_spawn=int(self._core._tick_contador), token_drop=token, item_dados=item_dados)
        BANCO_DADOS.inserir_objeto(obj)
        self._core._itens_mundo_ids.add(int(obj.Id))
        registrar_diff("spawn", payload=obj.serializar(), escopo={"centro": [float(obj.posicao[0]), float(obj.posicao[1])], "raio": 120}, objeto_id=obj.Id, autor="server", categoria="item_mundo")
        return True

    def executar_tick(self, chunks_carregados: Set[Chunk], chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        chunks_validos = set(chunks_carregados) | set(chunks_simulados)
        players = [o for o in BANCO_DADOS.listar_objetos() if str(getattr(o, "estado_extra", {}).get("subtipo", "")).strip().lower() == "player"]
        ttl_ticks = 5000

        usados_no_tick: set[int] = set()
        for oid in sorted(list(self._core._itens_mundo_ids)):
            if oid in usados_no_tick:
                continue
            item = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(item, ItemMundoServer):
                self._core._itens_mundo_ids.discard(oid); continue
            est = item.estado_extra if isinstance(item.estado_extra, dict) else {}
            if bool(est.get("voando", False)) or bool(est.get("despawn_pendente", False)):
                continue
            base_id = str(est.get("item_base_id") or "").strip().lower(); nome = str(est.get("item_nome") or "").strip().lower()
            candidatos = []
            for prox in BANCO_DADOS.buscar_proximos(item.posicao, 1.0):
                if not isinstance(prox, ItemMundoServer) or int(prox.Id) == int(item.Id):
                    continue
                est2 = prox.estado_extra if isinstance(prox.estado_extra, dict) else {}
                if bool(est2.get("voando", False)) or bool(est2.get("despawn_pendente", False)):
                    continue
                base2 = str(est2.get("item_base_id") or "").strip().lower(); nome2 = str(est2.get("item_nome") or "").strip().lower()
                if base_id and base2 and base_id != base2:
                    continue
                if (not base_id or not base2) and nome != nome2:
                    continue
                candidatos.append(prox)
            if not candidatos:
                continue
            survivor = min([item] + candidatos, key=lambda o: int(o.Id))
            absorvidos = [o for o in candidatos if int(o.Id) != int(survivor.Id)]
            if int(item.Id) != int(survivor.Id):
                absorvidos.append(item)
            soma = int((survivor.estado_extra if isinstance(survivor.estado_extra, dict) else {}).get("quantidade", 1) or 1)
            for ab in absorvidos:
                soma += int((ab.estado_extra if isinstance(ab.estado_extra, dict) else {}).get("quantidade", 1) or 1)
            ests = survivor.estado_extra if isinstance(survivor.estado_extra, dict) else {}
            ests["quantidade"] = soma
            BANCO_DADOS.atualizar_objeto(survivor.Id, {"estado": ests})
            registrar_diff("update", payload={"quantidade": soma, "estado": {"quantidade": soma}}, escopo={"centro": [survivor.posicao[0], survivor.posicao[1]], "raio": 120}, objeto_id=survivor.Id, autor="server", categoria="item_mundo")
            usados_no_tick.add(int(survivor.Id))
            for ab in absorvidos:
                esta = ab.estado_extra if isinstance(ab.estado_extra, dict) else {}
                esta["despawn_pendente"] = True
                esta["tick_despawn"] = int(self._core._tick_contador + 10)
                esta["evento"] = {"tipo": "fusao", "alvo_id": int(survivor.Id), "velocidade": 8.0}
                BANCO_DADOS.atualizar_objeto(ab.Id, {"estado": esta})
                registrar_diff("update", payload={"estado": {"evento": dict(esta.get("evento", {}))}}, escopo={"centro": [ab.posicao[0], ab.posicao[1]], "raio": 120}, objeto_id=ab.Id, autor="server", categoria="item_mundo")
                usados_no_tick.add(int(ab.Id))

        for oid in list(self._core._itens_mundo_ids):
            item = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(item, ItemMundoServer):
                self._core._itens_mundo_ids.discard(oid); continue
            estado = item.estado_extra if isinstance(item.estado_extra, dict) else {}
            if bool(estado.get("voando", False)):
                if int(self._core._tick_contador) >= int(estado.get("voando_ate_tick", self._core._tick_contador) or self._core._tick_contador):
                    destino = estado.get("pos_final") if isinstance(estado.get("pos_final"), (list, tuple)) else [item.posicao[0], item.posicao[1]]
                    item.definir_posicao(float(destino[0]), float(destino[1])); estado["voando"] = False
                    BANCO_DADOS.atualizar_objeto(item.Id, {"posicao": [item.posicao[0], item.posicao[1]], "estado": estado})
                continue
            if BANCO_DADOS.chunk_da_posicao(item.posicao) not in chunks_validos:
                rem = BANCO_DADOS.remover_objeto(item.Id); self._core._itens_mundo_ids.discard(item.Id)
                if rem is not None:
                    registrar_diff("despawn", payload={"id": rem.Id, "motivo": "chunk_nao_mantido"}, escopo={"centro": [rem.posicao[0], rem.posicao[1]], "raio": 120}, objeto_id=rem.Id, autor="server", categoria="item_mundo")
                continue
            if (self._core._tick_contador - int(estado.get("tick_spawn", self._core._tick_contador) or self._core._tick_contador)) >= ttl_ticks:
                rem = BANCO_DADOS.remover_objeto(item.Id); self._core._itens_mundo_ids.discard(item.Id)
                if rem is not None:
                    registrar_diff("despawn", payload={"id": rem.Id, "motivo": "ttl"}, escopo={"centro": [rem.posicao[0], rem.posicao[1]], "raio": 120}, objeto_id=rem.Id, autor="server", categoria="item_mundo")
                continue
            if bool(estado.get("despawn_pendente", False)):
                if int(self._core._tick_contador) >= int(estado.get("tick_despawn", self._core._tick_contador) or self._core._tick_contador):
                    rem = BANCO_DADOS.remover_objeto(item.Id); self._core._itens_mundo_ids.discard(item.Id)
                    if rem is not None:
                        registrar_diff("despawn", payload={"id": rem.Id, "motivo": "evento"}, escopo={"centro": [rem.posicao[0], rem.posicao[1]], "raio": 120}, objeto_id=rem.Id, autor="server", categoria="item_mundo")
                continue
            for player in players:
                dx = float(item.posicao[0]) - float(player.posicao[0]); dy = float(item.posicao[1]) - float(player.posicao[1])
                limite = float(item.raio_colisao) + float(player.raio_colisao)
                if (dx * dx + dy * dy) > (limite * limite):
                    continue
                usuario = BANCO_DADOS.usuario_por_objeto_id(int(player.Id))
                if not usuario:
                    continue
                dados = obter_personagem_para_entrada(usuario) or {}
                inv = dict(dados.get("inventario", {})) if isinstance(dados.get("inventario"), dict) else {"itens": []}
                item_inv = dict(estado.get("item_dados", {})) if isinstance(estado.get("item_dados"), dict) else self._core._servico_inventario.normalizar_item({"Code": str(estado.get("item_base_id") or ""), "Nome": str(estado.get("item_nome") or "Item"), "quantidade": 1})
                item_inv["quantidade"] = int(estado.get("quantidade", item_inv.get("quantidade", 1)) or 1)
                if not self._core._servico_inventario.adicionar_primeiro_slot_livre(inv, item_inv, dados_personagem=dados):
                    continue
                self._core._servico_inventario.persistir_jogador(usuario, int(player.Id), inv, registrar_diff)
                estado["despawn_pendente"] = True; estado["tick_despawn"] = int(self._core._tick_contador + 10)
                estado["evento"] = {"tipo": "coleta", "alvo_id": int(player.Id), "velocidade": 9.0, "coletor_id": int(player.Id)}
                BANCO_DADOS.atualizar_objeto(item.Id, {"estado": estado})
                registrar_diff("update", payload={"estado": {"evento": dict(estado.get("evento", {}))}}, escopo={"centro": [item.posicao[0], item.posicao[1]], "raio": 120}, objeto_id=item.Id, autor="server", categoria="item_mundo")
                break
