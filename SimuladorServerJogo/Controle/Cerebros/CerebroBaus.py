"""Subcérebro de baús (lógica real)."""

from __future__ import annotations

import time
from typing import Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import BauServer
from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada

Chunk = Tuple[int, int]


class CerebroBaus:
    def __init__(self, core) -> None:
        self._core = core

    def executar_tick(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        players = [o for o in BANCO_DADOS.listar_objetos() if str(getattr(o, "estado_extra", {}).get("subtipo", "")) == "player"]
        for oid in list(self._core._baus_ids):
            bau = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(bau, BauServer):
                self._core._baus_ids.discard(oid)
                continue
            if bool(bau.estado_extra.get("aberto", False)):
                continue
            for player in players:
                dx = float(bau.posicao[0]) - float(player.posicao[0]); dy = float(bau.posicao[1]) - float(player.posicao[1])
                limite = float(bau.raio_interacao) + float(player.raio_colisao)
                if (dx * dx + dy * dy) > (limite * limite):
                    continue
                usuario = BANCO_DADOS.usuario_por_objeto_id(int(player.Id))
                if not usuario:
                    continue
                dados = obter_personagem_para_entrada(usuario) or {}
                inv = dict(dados.get("inventario", {})) if isinstance(dados.get("inventario"), dict) else {"itens": []}

                # Nova regra: tenta inserir; excedente é descartado. Baú abre de qualquer forma.
                for item in list(bau.estado_extra.get("itens", [])):
                    if isinstance(item, dict):
                        self._core._servico_inventario.adicionar_primeiro_slot_livre(inv, dict(item), dados_personagem=dados)
                bau.estado_extra["itens"] = []
                bau.estado_extra["aberto"] = True
                bau.estado_extra["aberto_em"] = time.monotonic()
                BANCO_DADOS.atualizar_objeto(bau.Id, {"estado": bau.estado_extra})
                self._core._servico_inventario.persistir_jogador(usuario, int(player.Id), inv, registrar_diff)
                registrar_diff("update", payload={"estado": {"aberto": True, "itens": []}}, escopo={"centro": [bau.posicao[0], bau.posicao[1]], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau")
                break

        ttl = 100
        for oid in list(self._core._baus_ids):
            bau = BANCO_DADOS.obter_objeto(oid)
            if not isinstance(bau, BauServer):
                self._core._baus_ids.discard(oid)
                continue
            if not bool(bau.estado_extra.get("aberto", False)):
                continue
            aberto_em = float(bau.estado_extra.get("aberto_em", 0.0) or 0.0)
            if aberto_em <= 0.0:
                continue
            if int((time.monotonic() - aberto_em) * 30.0) < ttl:
                continue
            removido = BANCO_DADOS.remover_objeto(oid)
            self._core._baus_ids.discard(oid)
            if removido is not None:
                registrar_diff("despawn", payload={"id": removido.Id, "motivo": "bau_aberto_expirado"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 80}, objeto_id=removido.Id, autor="server", categoria="bau")
