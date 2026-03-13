"""Subcontrolador para criáveis do player (projéteis e itens mundo)."""

from __future__ import annotations

from typing import Callable, Dict, List
import math
import time

from Codigo.Geradores.Projetil import Projetil
from Codigo.Geradores.ItemMundo import ItemMundo


class ControladorCriaveis:
    def __init__(self, objetos_por_id: Dict[int, Dict[str, object]], remover_indice_cb: Callable[[int], None]) -> None:
        self._objetos_por_id = objetos_por_id
        self._remover_indice = remover_indice_cb
        self.ProjeteisPorId: Dict[int, Projetil] = {}
        self.ItensMundoPorId: Dict[int, ItemMundo] = {}

    @staticmethod
    def eh_payload_projetil(payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"entidade_projetil", "projetil"}

    @staticmethod
    def eh_payload_item_mundo(payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"entidade_item_mundo", "item_mundo"}

    def reconciliar_projetil_predito_por_token(self, oid_oficial: int, payload: Dict[str, object]) -> None:
        token = str(payload.get("token_arremesso") or (payload.get("estado") or {}).get("token_arremesso") or "")
        if not token:
            return
        remover_ids: List[int] = []
        for oid, proj in list(self.ProjeteisPorId.items()):
            if int(oid) == int(oid_oficial):
                continue
            if str(getattr(proj, "TokenArremesso", "") or "") != token:
                continue
            if int(getattr(proj, "Id", 0) or 0) >= 0 and not bool(getattr(proj, "PreditoLocal", False)):
                continue
            remover_ids.append(int(oid))
        for oid in remover_ids:
            self.ProjeteisPorId.pop(oid, None)
            self._objetos_por_id.pop(oid, None)
            self._remover_indice(oid)

    def reconciliar_item_mundo_predito_por_token(self, oid_oficial: int, payload: Dict[str, object]) -> None:
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        token = str(payload.get("token_drop") or estado.get("token_drop") or "")
        if not token:
            return
        remover_ids: List[int] = []
        for oid, item in list(self.ItensMundoPorId.items()):
            if int(oid) == int(oid_oficial):
                continue
            if str(getattr(item, "TokenDrop", "") or "") != token:
                continue
            item.reconciliar_autoritativo(payload)
            remover_ids.append(int(oid))
        for rid in remover_ids:
            self.ItensMundoPorId.pop(rid, None)
            self._objetos_por_id.pop(rid, None)
            self._remover_indice(rid)

    def upsert_criavel(self, oid: int, payload: Dict[str, object]) -> None:
        if self.eh_payload_projetil(payload):
            self.reconciliar_projetil_predito_por_token(oid, payload)
            proj = self.ProjeteisPorId.get(oid)
            if proj is None:
                self.ProjeteisPorId[oid] = Projetil(payload)
            else:
                proj.aplicar_snapshot(payload)
        else:
            self.ProjeteisPorId.pop(oid, None)

        if self.eh_payload_item_mundo(payload):
            self.reconciliar_item_mundo_predito_por_token(oid, payload)
            item_mundo = self.ItensMundoPorId.get(oid)
            if item_mundo is None:
                self.ItensMundoPorId[oid] = ItemMundo(payload)
            else:
                item_mundo.aplicar_snapshot(payload)
        else:
            self.ItensMundoPorId.pop(oid, None)

    def remover_criavel(self, oid: int) -> None:
        self.ProjeteisPorId.pop(int(oid), None)
        self.ItensMundoPorId.pop(int(oid), None)

    def aplicar_spawn_especial(self, categoria: str, payload: Dict[str, object], aplicar_diff_cb: Callable[[Dict[str, object]], None]) -> bool:
        categoria = str(categoria or "").strip().lower()
        dados = payload if isinstance(payload, dict) else {}
        if categoria == "projetil_lancamento":
            pos_inicial = dados.get("pos_inicial") if isinstance(dados.get("pos_inicial"), (list, tuple)) else [0.0, 0.0]
            pos_final = dados.get("pos_final") if isinstance(dados.get("pos_final"), (list, tuple)) else list(pos_inicial)
            dx = float(pos_final[0]) - float(pos_inicial[0]); dy = float(pos_final[1]) - float(pos_inicial[1])
            dist = math.hypot(dx, dy) or 1.0
            direcao = [dx / dist, dy / dist]
            token = str(dados.get("token") or "")
            oid_vis = -abs(hash((token, time.time())))
            fake = {
                "id": int(oid_vis), "tipo": "entidade_projetil", "tipo_projetil": str(dados.get("subtipo_projetil", "pokebola")),
                "subtipo": str(dados.get("variante") or dados.get("item") or "pokebola"), "item_base_id": str(dados.get("item_base_id") or ""),
                "item_nome": str(dados.get("item_nome") or dados.get("item") or dados.get("variante") or ""), "dono_id": int(dados.get("dono_id", 0) or 0),
                "posicao": [float(pos_inicial[0]), float(pos_inicial[1])],
                "estado": {"direcao": direcao, "velocidade": float(dados.get("velocidade_tiles_s", 7.0) or 7.0), "alcance": float(dist), "token_arremesso": token, "predito_local": False, "pos_final": [float(pos_final[0]), float(pos_final[1])]},
                "token_arremesso": token,
            }
            aplicar_diff_cb({"tipo": "spawn", "objeto_id": int(oid_vis), "payload": fake})
            return True

        if categoria == "item_mundo_lancamento":
            pos_inicial = dados.get("pos_inicial") if isinstance(dados.get("pos_inicial"), (list, tuple)) else [0.0, 0.0]
            pos_final = dados.get("pos_final") if isinstance(dados.get("pos_final"), (list, tuple)) else list(pos_inicial)
            token = str(dados.get("token") or "")
            oid_vis = -abs(hash(("item_drop", token, time.time())))
            fake = {
                "id": int(oid_vis), "tipo": "entidade_item_mundo", "item_nome": str(dados.get("item_nome") or dados.get("item") or "Item"),
                "item_base_id": str(dados.get("item_base_id") or ""), "quantidade": max(1, int(dados.get("quantidade", 1) or 1)),
                "dono_id": int(dados.get("dono_id", 0) or 0), "token_drop": token,
                "posicao": [float(pos_inicial[0]), float(pos_inicial[1])],
                "estado": {"subtipo": "item_mundo", "pos_inicial": [float(pos_inicial[0]), float(pos_inicial[1])], "pos_final": [float(pos_final[0]), float(pos_final[1])], "velocidade": float(dados.get("velocidade_tiles_s", 3.0) or 3.0), "voando": True, "token_drop": token, "predito_local": False},
            }
            aplicar_diff_cb({"tipo": "spawn", "objeto_id": int(oid_vis), "payload": fake})
            return True

        return False

    def atualizar_visuais(self, dt: float, objetos_snapshot: Dict[int, Dict[str, object]], detectar_colisao_projetil_cb: Callable, registrar_colisao_pokemon_cb: Callable, aplicar_despawn_cb: Callable[[int], None]) -> None:
        for p in list(self.ProjeteisPorId.values()):
            p.atualizar_visual(dt)
            if (not p.Terminado) and (not p.Colidiu):
                alvo = detectar_colisao_projetil_cb(p, objetos_snapshot)
                if alvo is not None:
                    subtipo = str((alvo.get("estado") or {}).get("subtipo", "")).strip().lower() if isinstance(alvo, dict) else ""
                    if subtipo == "pokemon":
                        poke = alvo
                        p.encerrar_imediato()
                        if str(getattr(p, "TipoProjetil", "")).lower() != "fruta":
                            registrar_colisao_pokemon_cb(p, poke)
                    else:
                        p.encerrar_com_fade(0.5)
            if p.deve_remover():
                aplicar_despawn_cb(int(p.Id))

        for item in list(self.ItensMundoPorId.values()):
            item.atualizar_visual(dt)
            if item.deve_remover_local():
                aplicar_despawn_cb(int(item.Id))

    def renderizar_criavel(self, oid: int, tela, camera) -> bool:
        proj = self.ProjeteisPorId.get(int(oid))
        if proj is not None:
            proj.desenhar(tela, camera)
            return True
        item_mundo = self.ItensMundoPorId.get(int(oid))
        if item_mundo is not None:
            item_mundo.desenhar(tela, camera)
            return True
        return False
