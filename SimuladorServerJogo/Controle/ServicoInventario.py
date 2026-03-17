"""Serviço autoritativo de inventário no servidor."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_inventario_personagem

_RAIZ = Path(__file__).resolve().parents[2]


def _carregar_itens_por_code() -> Dict[str, Dict[str, object]]:
    by_code: Dict[str, Dict[str, object]] = {}
    with (_RAIZ / "Dados" / "Global server - Itens.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = str(row.get("Code", "")).strip()
            if not code:
                continue
            raridade_raw = str(row.get("Raridade", "")).strip()
            by_code[code] = {
                "Code": code,
                "Nome": str(row.get("Nome", "")).strip(),
                "Descrição": str(row.get("Descrição", "")).strip(),
                "Estilo": str(row.get("Estilo", "")).strip(),
                "Raridade": int(raridade_raw) if raridade_raw.isdigit() else raridade_raw,
            }
    return by_code


_ITENS_POR_CODE = _carregar_itens_por_code()


class ServicoInventario:
    @staticmethod
    def normalizar_item(item: Dict[str, object], quantidade_padrao: int = 1) -> Dict[str, object]:
        base = dict(item or {})
        code = str(base.get("Code") or "").strip()
        qtd = max(1, int(base.get("quantidade", quantidade_padrao) or quantidade_padrao))
        item_csv = dict(_ITENS_POR_CODE.get(code, {})) if code else {}
        if item_csv:
            item_csv["quantidade"] = qtd
            return item_csv
        return {"Code": code, "Nome": str(base.get("Nome") or "Item"), "quantidade": qtd}

    @staticmethod
    def limite_slots(inventario: Dict[str, object], dados_personagem: Optional[Dict[str, object]] = None) -> int:
        inv = inventario if isinstance(inventario, dict) else {}
        dados = dados_personagem if isinstance(dados_personagem, dict) else {}
        limite_inv = int(inv.get("limite_slots", 0) or 0)
        if limite_inv > 0:
            return limite_inv
        limite_perfil = int(dados.get("limite_slots_inventario", 0) or 0)
        if limite_perfil > 0:
            return limite_perfil
        return 32

    @staticmethod
    def limite_pokemons(inventario: Dict[str, object], dados_personagem: Optional[Dict[str, object]] = None) -> int:
        inv = inventario if isinstance(inventario, dict) else {}
        dados = dados_personagem if isinstance(dados_personagem, dict) else {}
        limite_inv = int(inv.get("limite_pokemons", 0) or 0)
        if limite_inv > 0:
            return limite_inv
        limite_perfil = int(dados.get("limite_pokemons", 0) or 0)
        if limite_perfil > 0:
            return limite_perfil
        return 64


    def adicionar_pokemon_capturado(self, inventario: Dict[str, object], pokemon: Dict[str, object], dados_personagem: Optional[Dict[str, object]] = None) -> bool:
        inv = dict(inventario or {})
        limite_pokes = self.limite_pokemons(inv, dados_personagem)
        pokemons = list(inv.get("pokemons", []))
        if len(pokemons) >= limite_pokes:
            return False
        pokemons.append(dict(pokemon or {}))
        inv["pokemons"] = pokemons
        inv["limite_pokemons"] = int(limite_pokes)


        inventario.clear(); inventario.update(inv)
        return True

    def adicionar_primeiro_slot_livre(self, inventario: Dict[str, object], item: Dict[str, object], dados_personagem: Optional[Dict[str, object]] = None) -> bool:
        inv = dict(inventario or {})
        lim = self.limite_slots(inv, dados_personagem)
        inv["limite_slots"] = int(lim)
        itens = list(inv.get("itens", []))
        if len(itens) < lim:
            itens.extend([None] * (lim - len(itens)))
        for i in range(lim):
            if i >= len(itens):
                itens.append(None)
            if itens[i] is None:
                itens[i] = self.normalizar_item(item)
                inv["itens"] = itens
                inventario.clear(); inventario.update(inv)
                return True
        return False

    def consumir_um(self, inventario: Dict[str, object], item_base_id: str, item_nome: str) -> bool:
        inv = dict(inventario or {})
        itens = list(inv.get("itens", []))
        alvo_code = str(item_base_id or "").strip().lower()
        alvo_nome = str(item_nome or "").strip().lower()
        for i, atual in enumerate(itens):
            if not isinstance(atual, dict):
                continue
            code = str(atual.get("Code") or "").strip().lower()
            nome = str(atual.get("Nome") or "").strip().lower()
            if alvo_code and code != alvo_code:
                continue
            if (not alvo_code) and alvo_nome and nome != alvo_nome:
                continue
            qtd = max(1, int(atual.get("quantidade", 1) or 1))
            if qtd <= 1:
                itens[i] = None
            else:
                atual["quantidade"] = qtd - 1
                itens[i] = atual
            inv["itens"] = itens
            inventario.clear(); inventario.update(inv)
            return True
        return False

    @staticmethod
    def persistir_jogador(usuario: str, player_obj_id: int, inventario: Dict[str, object], registrar_diff_cb) -> None:
        atualizar_inventario_personagem(str(usuario), inventario)
        if int(player_obj_id) > 0:
            BANCO_DADOS.atualizar_objeto(int(player_obj_id), {"estado": {"inventario": inventario}})
            player_obj = BANCO_DADOS.obter_objeto(int(player_obj_id))
            if player_obj is not None:
                registrar_diff_cb("update", payload={"inventario": inventario}, escopo={"centro": [float(player_obj.posicao[0]), float(player_obj.posicao[1])], "raio": 780.0}, objeto_id=int(player_obj_id), autor="server", categoria="player")
