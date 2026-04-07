from __future__ import annotations

import copy
from typing import Callable, Dict, Iterable, Optional, Tuple


class ServicoCraft:
    @staticmethod
    def resolver_resultado_grade(craft_slots, receitas: Iterable[Dict[str, object]], chave_item: Callable, quantidade_item: Callable) -> Tuple[Optional[Dict[str, object]], Optional[Dict[str, object]]]:
        for receita in receitas:
            ok = True
            for i, esperado in enumerate(receita.get("grade", [])):
                atual = craft_slots[i]
                if esperado is None and atual is None:
                    continue
                if esperado is None or atual is None:
                    ok = False
                    break
                if chave_item(esperado) != chave_item(atual):
                    ok = False
                    break
                if quantidade_item(atual) < quantidade_item(esperado):
                    ok = False
                    break
            if ok:
                return copy.deepcopy(receita.get("saida")), receita
        return None, None

    @staticmethod
    def consumir_receita(craft_slots, origens, receita: Optional[Dict[str, object]], quantidade_item: Callable) -> None:
        if receita is None:
            return
        for i, esperado in enumerate(receita.get("grade", [])):
            if esperado is None or craft_slots[i] is None:
                continue
            qtd = quantidade_item(craft_slots[i])
            consumo = max(1, quantidade_item(esperado))
            if qtd <= consumo:
                craft_slots[i] = None
                origens[i] = None
            else:
                craft_slots[i]["quantidade"] = qtd - consumo

    @staticmethod
    def preencher_grade_receita(craft_slots, origens, receita: Optional[Dict[str, object]], estado: str, container, chave_item: Callable, quantidade_item: Callable) -> bool:
        if receita is None or estado == "vermelho" or container is None:
            return False
        colocou_algo = False
        reservas = {}
        for idx, item in enumerate(getattr(container, "Itens", [])):
            chave = chave_item(item)
            if item is None or not chave:
                continue
            reservas.setdefault(chave, []).append({"indice": idx, "quantidade": quantidade_item(item)})

        def _consumir_reserva(chave):
            pilha = reservas.get(chave) or []
            while pilha:
                topo = pilha[0]
                if topo["quantidade"] <= 0:
                    pilha.pop(0)
                    continue
                retirado = container.recolher_do_slot(topo["indice"], quantidade=1)
                if retirado is None:
                    pilha.pop(0)
                    continue
                topo["quantidade"] -= 1
                if topo["quantidade"] <= 0:
                    pilha.pop(0)
                return retirado, topo["indice"]
            return None, None

        for i, esperado in enumerate(receita.get("grade", [])):
            if esperado is None:
                continue
            atual = craft_slots[i]
            chave_esperada = chave_item(esperado)
            qtd_esperada = max(1, quantidade_item(esperado))
            if atual is not None and chave_item(atual) != chave_esperada:
                continue
            qtd_atual = quantidade_item(atual)
            faltante = max(0, qtd_esperada - qtd_atual)
            if faltante <= 0:
                continue
            origem_slot = None
            for _ in range(faltante):
                retirado, origem = _consumir_reserva(chave_esperada)
                if retirado is None:
                    break
                if atual is None:
                    craft_slots[i] = retirado
                    origens[i] = origem
                    atual = craft_slots[i]
                    origem_slot = origem
                else:
                    atual["quantidade"] = quantidade_item(atual) + quantidade_item(retirado)
                if origem_slot is None:
                    origem_slot = origem
                colocou_algo = True
            if atual is not None and origens[i] is None and origem_slot is not None:
                origens[i] = origem_slot
        return colocou_algo
