"""Serviço autoritativo de inventário no servidor."""

from __future__ import annotations

import random
from typing import Dict, Optional

from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Gerais.EstadoServidor import atualizar_inventario_personagem, obter_personagem_para_entrada
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from Codigo.ModulosGerais.ServicoSkills import stack_efetivo


def _carregar_itens() -> tuple[Dict[str, Dict[str, object]], Dict[str, Dict[str, object]]]:
    by_code: Dict[str, Dict[str, object]] = {}
    by_nome: Dict[str, Dict[str, object]] = {}
    for row in carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8"):
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
                "Bau": str(row.get("Bau", "")).strip().lower(),
                "Stacks": int(float(row.get("Stacks", 1) or 1)) if str(row.get("Stacks", "")).strip() else 1,
            }
            by_code[code] = item
            by_nome[nome.strip().lower()] = item
    return by_code, by_nome


_ITENS_POR_CODE, _ITENS_POR_NOME = _carregar_itens()


class ServicoInventario:
    @staticmethod
    def _limite_stack(item: Dict[str, object], nivel_acumulador: int = 0) -> int:
        if not isinstance(item, dict):
            return 1
        base = 999999
        try:
            valor = int(item.get("Stacks", 0) or 0)
            if valor > 0:
                base = valor
        except (TypeError, ValueError):
            pass
        return stack_efetivo(base, nivel_acumulador)

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
        grupo = str((pokemon or {}).get("grupo") or "").strip()
        if grupo:
            doces = dict(inv.get("doces", {})) if isinstance(inv.get("doces"), dict) else {}
            doces[grupo] = int(doces.get(grupo, 0) or 0) + random.randint(2, 4)
            inv["doces"] = doces
        inv["pokemons"] = pokemons
        inv["limite_pokemons"] = int(limite_pokes)


        inventario.clear(); inventario.update(inv)
        return True

    def adicionar_primeiro_slot_livre(self, inventario: Dict[str, object], item: Dict[str, object], dados_personagem: Optional[Dict[str, object]] = None) -> bool:
        dados_item = dict(item or {})
        quantidade = int(dados_item.get("quantidade", 1) or 1)
        adicionado, sobra = self.adicionar_item(inventario, dados_item, quantidade, dados_personagem=dados_personagem)
        return adicionado > 0 and sobra <= 0

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
        dados = dados_personagem if isinstance(dados_personagem, dict) else {}
        nivel_acumulador = int(dados.get("nivel_acumulador", dados.get("NivelAcumulador", 0)) or 0)
        mochila_sem_limite = bool(dados.get("mochila_sem_limite", dados.get("MochilaSemLimite", False)))
        limite_itens = int(inv.get("limite_itens", 100) or 0)
        itens = list(inv.get("itens", []))
        if len(itens) < lim:
            itens.extend([None] * (lim - len(itens)))
        else:
            itens = itens[:lim]

        total_itens = 0
        for atual in itens:
            if isinstance(atual, dict):
                total_itens += int(max(1, atual.get("quantidade", 1) or 1))
        if mochila_sem_limite or limite_itens <= 0:
            adicionavel = qtd
            sobra = 0
        else:
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
                limite_stack = self._limite_stack(atual, nivel_acumulador)
                qtd_atual = int(atual.get("quantidade", 1) or 1)
                pode_entrar = max(0, min(adicionavel, limite_stack - qtd_atual))
                if pode_entrar > 0:
                    atual["quantidade"] = qtd_atual + pode_entrar
                    adicionavel -= pode_entrar
                    itens[i] = atual
                if adicionavel <= 0:
                    inv["itens"] = itens
                    inventario.clear(); inventario.update(inv)
                    return (qtd - sobra, sobra)

        while adicionavel > 0:
            i = next((idx for idx, atual in enumerate(itens) if atual is None), None)
            if i is None:
                break
            quantidade_slot = min(adicionavel, self._limite_stack(item_base, nivel_acumulador))
            itens[i] = self.normalizar_item(item_base, quantidade_padrao=quantidade_slot)
            adicionavel -= quantidade_slot

        adicionado_total = (qtd - sobra) - adicionavel
        sobra_final = sobra + adicionavel
        if adicionado_total > 0:
            inv["itens"] = itens
            inventario.clear(); inventario.update(inv)
        return (adicionado_total, sobra_final)

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
        dados = obter_personagem_para_entrada(str(usuario)) or {}
        perfil = {k: v for k, v in dados.items() if k != "inventario"}
        if int(player_obj_id) > 0:
            BANCO_DADOS.atualizar_objeto(int(player_obj_id), {"estado": {"inventario": inventario, "perfil": perfil}})
            player_obj = BANCO_DADOS.obter_objeto(int(player_obj_id))
            if player_obj is not None:
                registrar_diff_cb("update", payload={"inventario": inventario, "perfil": perfil}, escopo={"centro": [float(player_obj.posicao[0]), float(player_obj.posicao[1])], "raio": 780.0}, objeto_id=int(player_obj_id), autor="server", categoria="player")
