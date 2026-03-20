"""Subcérebro de estruturas naturais."""

from __future__ import annotations

import csv
import math
import uuid
from pathlib import Path
from typing import Dict, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada
from SimuladorServerJogo.Controle.ObjetosMundoServer import AtorServer, EstruturaNaturalServer, ItemMundoServer

_RAIZ = Path(__file__).resolve().parents[3]


def _carregar_ferramentas() -> Dict[str, Dict[str, object]]:
    by_code: Dict[str, Dict[str, object]] = {}
    with (_RAIZ / "Dados" / "Global server - Itens.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = str(row.get("Code", "")).strip()
            if not code:
                continue
            nome = str(row.get("Nome", "")).strip().lower()
            estilo = str(row.get("Estilo", "")).strip().lower()
            try:
                fator = int(float(row.get("Fator", 1) or 1))
            except Exception:
                fator = 1
            by_code[code] = {"nome": nome, "estilo": estilo, "fator": fator}
    return by_code


_FERRAMENTAS = _carregar_ferramentas()


class CerebroEstruturasNaturais:
    def __init__(self, cerebro_core) -> None:
        self._core = cerebro_core

    def executar_tick(self) -> None:
        return None

    @staticmethod
    def _estilo_ferramenta(item: Dict[str, object]) -> Tuple[str, int]:
        if not isinstance(item, dict):
            return "", 1
        code = str(item.get("Code") or "").strip()
        meta = dict(_FERRAMENTAS.get(code, {})) if code else {}
        nome = str(item.get("Nome") or meta.get("nome") or "").strip()
        fator = int(item.get("Fator", meta.get("fator", 1)) or 1)
        primeira = nome.split(" ", 1)[0].strip().lower() if nome else ""
        if primeira == "machado":
            return "machado", fator
        if primeira in {"picarte", "picareta"}:
            return "picareta", fator
        return "", 1

    def registrar_coleta(self, client_id: str, payload: Dict[str, object]) -> bool:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        usuario = str(client_id or "").strip()
        if not usuario:
            return False
        player_id = int(BANCO_DADOS.objeto_id_por_usuario(usuario) or 0)
        player = BANCO_DADOS.obter_objeto(player_id)
        if not isinstance(player, AtorServer):
            return False

        estrutura_id = int(payload.get("estrutura_id", 0) or 0)
        estrutura = BANCO_DADOS.obter_objeto(estrutura_id)
        if not isinstance(estrutura, EstruturaNaturalServer):
            return False

        mao = payload.get("pos_mao") if isinstance(payload.get("pos_mao"), (list, tuple)) and len(payload.get("pos_mao")) == 2 else None
        mx, my = (float(mao[0]), float(mao[1])) if mao else (float(player.posicao[0]), float(player.posicao[1]))
        limite = float(player.raio_interacao) + float(estrutura.raio_colisao) + 0.35
        if math.hypot(float(estrutura.posicao[0]) - mx, float(estrutura.posicao[1]) - my) > limite:
            return False

        perfil = obter_personagem_para_entrada(usuario) or {}
        inventario = perfil.get("inventario") if isinstance(perfil.get("inventario"), dict) else {}
        itens = inventario.get("itens") if isinstance(inventario.get("itens"), list) else []
        slot = int(inventario.get("slot_selecionado", player.estado_extra.get("slot_selecionado", 0)) or 0)
        item_mao = itens[slot] if 0 <= slot < len(itens) and isinstance(itens[slot], dict) else {}

        estilo_ferramenta, fator = self._estilo_ferramenta(item_mao)
        coletado = estrutura.tentar_coleta(fator_ferramenta=fator, estilo_ferramenta=estilo_ferramenta)
        if coletado <= 0:
            return False

        restante = estrutura.quantidade_restante
        BANCO_DADOS.registrar_quantidade_estrutura(estrutura.Id, restante)
        if restante <= 0:
            removido = BANCO_DADOS.remover_objeto(estrutura.Id)
            if removido is not None:
                registrar_diff("despawn", payload={"id": removido.Id, "motivo": "estrutura_esgotada"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 90.0}, objeto_id=removido.Id, autor="server", categoria="estrutura")
        else:
            BANCO_DADOS.atualizar_objeto(estrutura.Id, {"estado": {"quantidade": restante}})
            registrar_diff("update", payload=estrutura.serializar(), escopo={"centro": [estrutura.posicao[0], estrutura.posicao[1]], "raio": 90.0}, objeto_id=estrutura.Id, autor="server", categoria="estrutura")

        material = str(estrutura.estado_extra.get("material", "") or "").strip()
        adicionado, sobra = self._core._servico_inventario.adicionar_item(inventario, {"Nome": material}, coletado, dados_personagem=perfil)
        if adicionado > 0:
            self._core._servico_inventario.persistir_jogador(usuario, int(player.Id), inventario, registrar_diff)
        if sobra > 0:
            self._spawn_item_mundo(material, sobra, player, estrutura, registrar_diff)
        return True

    def _spawn_item_mundo(self, nome_material: str, quantidade: int, player: AtorServer, estrutura: EstruturaNaturalServer, registrar_diff) -> None:
        qtd = max(1, int(quantidade or 1))
        item = self._core._servico_inventario.normalizar_item({"Nome": str(nome_material or "Item"), "quantidade": qtd}, quantidade_padrao=qtd)
        novo_id = BANCO_DADOS.gerar_id()
        p0 = (float(player.posicao[0]), float(player.posicao[1]))
        p1 = (float(estrutura.posicao[0]) + 0.22, float(estrutura.posicao[1]) + 0.08)
        obj = ItemMundoServer(
            id_objeto=novo_id,
            posicao=p0,
            dono_id=int(getattr(player, "Id", 0) or 0),
            item_nome=str(item.get("Nome") or "Item"),
            item_base_id=str(item.get("Code") or ""),
            quantidade=qtd,
            pos_inicial=p0,
            pos_final=p1,
            velocidade=4.2,
            tick_spawn=int(self._core._tick_contador),
            token_drop=str(uuid.uuid4()),
            item_dados=item,
        )
        BANCO_DADOS.inserir_objeto(obj)
        self._core.registrar_spawn_manual(obj)
        registrar_diff("spawn", payload=obj.serializar(), escopo={"centro": [p1[0], p1[1]], "raio": 80.0}, objeto_id=obj.Id, autor="server", categoria="item_mundo")
