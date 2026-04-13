"""Subcérebro de baús (lógica real)."""

from __future__ import annotations

import time
import math
from typing import Dict, Set, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, BauServer
from SimuladorServerJogo.Gerais.EstadoServidor import obter_personagem_para_entrada

Chunk = Tuple[int, int]


class CerebroBaus:
    def __init__(self, core) -> None:
        self._core = core

    def executar_tick(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff
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

    @staticmethod
    def _tem_chave_na_mao(perfil: Dict[str, object], player: AtorServer) -> bool:
        inventario = perfil.get("inventario") if isinstance(perfil.get("inventario"), dict) else {}
        itens = inventario.get("itens") if isinstance(inventario.get("itens"), list) else []
        slot = int(inventario.get("slot_selecionado", player.estado_extra.get("slot_selecionado", 0)) or 0)
        item_mao = itens[slot] if 0 <= slot < len(itens) and isinstance(itens[slot], dict) else {}
        nome = str(item_mao.get("Nome") or "").strip().lower()
        return bool(nome == "chave" or " key" in f" {nome}" or nome.startswith("chave "))

    @staticmethod
    def _consumir_chave_selecionada(inventario: Dict[str, object], player: AtorServer) -> bool:
        inv = inventario if isinstance(inventario, dict) else {}
        itens = inv.get("itens") if isinstance(inv.get("itens"), list) else []
        slot = int(inv.get("slot_selecionado", player.estado_extra.get("slot_selecionado", 0)) or 0)
        if not (0 <= slot < len(itens)):
            return False
        item_mao = itens[slot] if isinstance(itens[slot], dict) else None
        if not isinstance(item_mao, dict):
            return False
        nome = str(item_mao.get("Nome") or "").strip().lower()
        if not (nome == "chave" or " key" in f" {nome}" or nome.startswith("chave ")):
            return False
        qtd = max(1, int(item_mao.get("quantidade", 1) or 1))
        if qtd <= 1:
            itens[slot] = None
        else:
            item_mao["quantidade"] = qtd - 1
            itens[slot] = item_mao
        inv["itens"] = itens
        return True

    def registrar_interacao(self, client_id: str, payload: Dict[str, object]) -> bool:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        usuario = str(client_id or "").strip()
        if not usuario:
            return False
        player_id = int(BANCO_DADOS.objeto_id_por_usuario(usuario) or 0)
        player = BANCO_DADOS.obter_objeto(player_id)
        if not isinstance(player, AtorServer):
            return False

        bau_id = int(payload.get("bau_id", 0) or 0)
        bau = BANCO_DADOS.obter_objeto(bau_id)
        if not isinstance(bau, BauServer):
            return False
        if bool(bau.estado_extra.get("aberto", False)):
            return False

        mao = payload.get("pos_mao") if isinstance(payload.get("pos_mao"), (list, tuple)) and len(payload.get("pos_mao")) == 2 else None
        mx, my = (float(mao[0]), float(mao[1])) if mao else (float(player.posicao[0]), float(player.posicao[1]))
        limite = float(player.raio_interacao) + float(bau.raio_colisao) + 0.20
        if math.hypot(float(bau.posicao[0]) - mx, float(bau.posicao[1]) - my) > limite:
            return False

        dados = obter_personagem_para_entrada(usuario) or {}
        if not self._tem_chave_na_mao(dados, player):
            return False
        inv = dict(dados.get("inventario", {})) if isinstance(dados.get("inventario"), dict) else {"itens": []}
        if not self._consumir_chave_selecionada(inv, player):
            return False
        for item in list(bau.estado_extra.get("itens", [])):
            if isinstance(item, dict):
                self._core._servico_inventario.adicionar_primeiro_slot_livre(inv, dict(item), dados_personagem=dados)
        bau.estado_extra["itens"] = []
        bau.estado_extra["aberto"] = True
        bau.estado_extra["aberto_em"] = time.monotonic()
        BANCO_DADOS.atualizar_objeto(bau.Id, {"estado": bau.estado_extra})
        self._core._servico_inventario.persistir_jogador(usuario, int(player.Id), inv, registrar_diff)
        registrar_diff("update", payload={"estado": {"aberto": True, "itens": []}}, escopo={"centro": [bau.posicao[0], bau.posicao[1]], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau")
        return True
