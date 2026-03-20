"""Serviço autoritativo de inventário no servidor."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.EstadoServidor import atualizar_inventario_personagem

_RAIZ = Path(__file__).resolve().parents[2]


def _carregar_itens() -> tuple[Dict[str, Dict[str, object]], Dict[str, Dict[str, object]]]:
    by_code: Dict[str, Dict[str, object]] = {}
    by_nome: Dict[str, Dict[str, object]] = {}
    with (_RAIZ / "Dados" / "Global server - Itens.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = str(row.get("Code", "")).strip()
            nome = str(row.get("Nome", "")).strip()
            if not code:
                continue
            raridade_raw = str(row.get("Raridade", "")).strip()
            try:
                fator = int(float(row.get("Fator", 1) or 1))
            except Exception:
                fator = 1
            item = {
                "Code": code,
                "Nome": nome,
                "Descrição": str(row.get("Descrição", "")).strip(),
                "Estilo": str(row.get("Estilo", "")).strip(),
                "Fator": fator,
                "Raridade": int(raridade_raw) if raridade_raw.isdigit() else raridade_raw,
            }
            by_code[code] = item
            by_nome[nome.strip().lower()] = item
    return by_code, by_nome


_ITENS_POR_CODE, _ITENS_POR_NOME = _carregar_itens()


class ServicoInventario:
    @staticmethod
    def _lista_pokemons_ocupados(valor: object) -> list[Dict[str, object]]:
        lista = valor if isinstance(valor, list) else []
        return [dict(p) for p in lista if isinstance(p, dict)]

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
        pokemons = self._lista_pokemons_ocupados(inv.get("pokemons", []))
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

    def adicionar_item(self, inventario: Dict[str, object], item: Dict[str, object], quantidade: int, dados_personagem: Optional[Dict[str, object]] = None) -> tuple[int, int]:
        qtd = max(0, int(quantidade or 0))
        if qtd <= 0:
            return (0, 0)
        base = dict(item or {})
        nome = str(base.get("Nome") or "").strip()
        code = str(base.get("Code") or "").strip()
        item_base = dict(_ITENS_POR_CODE.get(code, {})) if code else dict(_ITENS_POR_NOME.get(nome.lower(), {})) if nome else {}
        if not item_base:
            item_base = {"Code": code, "Nome": (nome or "Item")}
        item_base["quantidade"] = qtd
        inv = dict(inventario or {})
        lim = self.limite_slots(inv, dados_personagem)
        inv["limite_slots"] = int(lim)
        limite_itens = int(max(1, inv.get("limite_itens", 100) or 100))
        itens = list(inv.get("itens", []))
        if len(itens) < lim:
            itens.extend([None] * (lim - len(itens)))
        else:
            itens = itens[:lim]

        total_itens = 0
        for atual in itens:
            if isinstance(atual, dict):
                total_itens += int(max(1, atual.get("quantidade", 1) or 1))
        espaco = max(0, limite_itens - total_itens)
        if espaco <= 0:
            return (0, qtd)
        adicionavel = min(qtd, espaco)
        sobra = qtd - adicionavel

        chave_code = str(item_base.get("Code") or "").strip().lower()
        chave_nome = str(item_base.get("Nome") or "").strip().lower()
        for i, atual in enumerate(itens):
            if not isinstance(atual, dict):
                continue
            code_atual = str(atual.get("Code") or "").strip().lower()
            nome_atual = str(atual.get("Nome") or "").strip().lower()
            if (chave_code and code_atual == chave_code) or (not chave_code and nome_atual == chave_nome):
                atual["quantidade"] = int(atual.get("quantidade", 1) or 1) + adicionavel
                itens[i] = atual
                inv["itens"] = itens
                inventario.clear(); inventario.update(inv)
                return (adicionavel, sobra)

        for i, atual in enumerate(itens):
            if atual is None:
                itens[i] = self.normalizar_item(item_base, quantidade_padrao=adicionavel)
                inv["itens"] = itens
                inventario.clear(); inventario.update(inv)
                return (adicionavel, sobra)
        return (0, qtd)

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
