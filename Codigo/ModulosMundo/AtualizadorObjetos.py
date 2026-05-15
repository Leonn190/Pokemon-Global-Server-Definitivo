"""Mixin de sincronizacao e diffs do ControladorObjetos."""

from __future__ import annotations

import copy
from typing import Dict, List, Optional

import pygame

from Codigo.ModulosMundo.Geradores.Baus import Bau
from Codigo.ModulosMundo.Geradores.EstruturaNaturais import EstruturaNatural
from Codigo.ModulosMundo.Geradores.PokemonMundo import Pokemon


class AtualizadorObjetosMixin:
    def _marcar_diff_local(self, diff: Dict[str, object]) -> Dict[str, object]:
        if "autor" not in diff:
            diff["autor"] = self.autor_local() or "anon"
        return diff

    def EnfileirarDiffRapida(self, diff: Dict[str, object]) -> None:
        with self._lock_diffs:
            self._fila_saida_envio.append(self._marcar_diff_local(dict(diff)))

    def EnfileirarDiffLenta(self, diff: Dict[str, object]) -> None:
        self.EnfileirarDiffRapida(diff)

    def ColetarDiffsRapidas(self) -> List[Dict[str, object]]:
        with self._lock_diffs:
            lote = self._fila_saida_envio
            self._fila_saida_envio = []
        return lote

    def snapshot_objeto_por_id(self, objeto_id: int) -> Optional[Dict[str, object]]:
        oid = int(objeto_id or 0)
        if oid <= 0:
            return None
        with self._lock_objetos:
            payload = self.ObjetosPorId.get(oid)
            return copy.deepcopy(payload) if isinstance(payload, dict) else None

    def _reconciliar_projetil_predito_por_token(self, oid_oficial: int, payload: Dict[str, object]) -> None:
        self._criaveis.reconciliar_projetil_predito_por_token(oid_oficial, payload)

    def _upsert_especializado(self, oid: int, payload: Dict[str, object]) -> None:
        if self._eh_payload_pokemon(payload):
            poke = self.PokemonsPorId.get(oid)
            if poke is None:
                self.PokemonsPorId[oid] = Pokemon(payload)
            else:
                poke.update(payload) if hasattr(poke, "update") else poke.aplicar_snapshot(payload)
        else:
            self.PokemonsPorId.pop(oid, None)

        if self._eh_payload_bau(payload):
            bau = self.BausPorId.get(oid)
            if bau is None:
                self.BausPorId[oid] = Bau.from_snapshot(payload)
            else:
                aberto_antes = bool(getattr(bau, "Aberto", False))
                bau.update(payload) if hasattr(bau, "update") else bau.aplicar_snapshot(payload)
                if (not aberto_antes) and bool(getattr(bau, "Aberto", False)):
                    perfil = getattr(self._player_local_ref, "Perfil", None) if self._player_local_ref is not None else None
                    if perfil is not None:
                        perfil.registrar_bau_aberto(1)
        else:
            self.BausPorId.pop(oid, None)

        self._atores.upsert(oid, payload, id_player_local=self.id_player_local())

        self._criaveis.upsert_criavel(oid, payload)

        if self._eh_payload_estrutura(payload):
            est = self.EstruturasPorId.get(oid)
            if est is None:
                estado_payload = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                est = EstruturaNatural(tipo=str(estado_payload.get("subtipo", "natural")), posicao=tuple(payload.get("posicao", [0.0, 0.0])), id_objeto=oid, raio_colisao=float(payload.get("raio_colisao", 0.8)), raio_interacao=float(payload.get("raio_interacao", 0.8)), campo=float(payload.get("campo", 0.0)), intensidade=float(payload.get("intensidade", 0.0)), quantidade=int(estado_payload.get("quantidade", 0) or 0), material=str(estado_payload.get("material", "") or ""), estilo=str(estado_payload.get("estilo", "") or ""), dureza=int(estado_payload.get("dureza", 1) or 1))
                self.EstruturasPorId[oid] = est
            est.update(payload)
        else:
            self.EstruturasPorId.pop(oid, None)

        if self._eh_payload_estadio(payload):
            self.EstadiosPorId[oid] = payload
        else:
            self.EstadiosPorId.pop(oid, None)

    def aplicar_diff(self, diff):
        if not isinstance(diff, dict):
            return

        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}

        categoria = str(diff.get("categoria", "")).strip().lower()

        if tipo == "spawn" and self._criaveis.aplicar_spawn_especial(categoria, payload, self.aplicar_diff):
            return

        if categoria == "dungeon_armadilhas":
            estado = payload.get("estado_armadilhas") if isinstance(payload.get("estado_armadilhas"), dict) else {}
            with self._lock_objetos:
                if isinstance(self.LayoutDungeonAtual, dict):
                    self.LayoutDungeonAtual["estado_armadilhas"] = estado
                    if bool(payload.get("tiles_alterados", False)):
                        self.LayoutDungeonAtual["_tiles_runtime_dirty"] = True
            return

        if tipo == "spawn":
            oid = int(payload.get("id", objeto_id or 0))
            dados = dict(payload)
            dados["id"] = oid
            with self._lock_objetos:
                self.ObjetosPorId[oid] = dados
                self._upsert_indice_chunk_objeto(oid, dados)
                self._upsert_especializado(oid, dados)
                self._registrar_snapshot_hud_captura(dados)
                self._invalidar_cache_objetos_visiveis_locked()
                if self._eh_payload_estrutura(dados) or self._eh_payload_estadio(dados):
                    self._invalidar_cache_estruturas_visiveis_locked()
            return

        if objeto_id is None:
            return
        oid = int(objeto_id)

        if tipo == "update":
            with self._lock_objetos:
                atual = self.ObjetosPorId.get(oid, {"id": oid})
                estado_novo = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
                if estado_novo:
                    estado = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
                    estado.update(estado_novo)
                    atual["estado"] = estado
                for chave, valor in payload.items():
                    if chave != "estado":
                        atual[chave] = valor
                self.ObjetosPorId[oid] = atual
                self._upsert_indice_chunk_objeto(oid, atual)
                self._upsert_especializado(oid, atual)
                self._registrar_snapshot_hud_captura(atual)
                self._invalidar_cache_objetos_visiveis_locked()
                if self._eh_payload_estrutura(atual) or self._eh_payload_estadio(atual):
                    self._invalidar_cache_estruturas_visiveis_locked()
                estado_atual = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
                captura_atual = estado_atual.get("captura") if isinstance(estado_atual.get("captura"), dict) else {}
                if str(estado_atual.get("subtipo", "")).strip().lower() == "pokemon" and captura_atual:
                    self._registrar_confirmacao_servidor_captura(atual)
            return

        if tipo == "despawn":
            with self._lock_objetos:
                payload_atual = self.ObjetosPorId.get(oid, {})
                remover_cache_estruturas = (
                    oid in self.EstruturasPorId
                    or oid in self.EstadiosPorId
                    or (isinstance(payload_atual, dict) and (self._eh_payload_estrutura(payload_atual) or self._eh_payload_estadio(payload_atual)))
                )
                poke = self.PokemonsPorId.get(oid)
                if poke is not None and hasattr(poke, "deve_adiar_despawn") and poke.deve_adiar_despawn():
                    if hasattr(poke, "solicitar_despawn_apos_animacao"):
                        poke.solicitar_despawn_apos_animacao()
                    return
                self.ObjetosPorId.pop(oid, None)
                self.PokemonsPorId.pop(oid, None)
                self.BausPorId.pop(oid, None)
                self._atores.remover(oid)
                self._criaveis.remover_criavel(oid)
                self.EstruturasPorId.pop(oid, None)
                self.EstadiosPorId.pop(oid, None)
                self._remover_indice_chunk_objeto(oid)
                self._invalidar_cache_objetos_visiveis_locked()
                if remover_cache_estruturas:
                    self._invalidar_cache_estruturas_visiveis_locked()

    def aplicar_pacote_tick(self, pacote_tick: Dict[str, object]) -> None:
        diffs = pacote_tick.get("diffs", []) if isinstance(pacote_tick, dict) else []
        if not isinstance(diffs, list):
            return
        for diff in diffs:
            if isinstance(diff, dict):
                self.aplicar_diff(diff)

    def _token_info(self, token: str) -> Dict[str, object]:
        token = str(token or "").strip()
        if not token:
            return {}
        return self._capturas_por_token.setdefault(token, {
            "resultado_servidor_recebido": False,
            "resultado_servidor_recebido_ms": 0,
            "impacto_local_enviado": False,
            "impacto_local_enviado_ms": 0,
        })

    @staticmethod
    def _captura_tem_dados_hud(captura: Dict[str, object]) -> bool:
        if not isinstance(captura, dict):
            return False
        if not str(captura.get("token_arremesso") or "").strip():
            return False
        if str(captura.get("resultado") or "").strip().lower() not in {"sucesso", "falha"}:
            return False
        return any(chave in captura for chave in ("poder_total", "dificuldade_captura", "chance_geral", "chance_real_3_checks"))

    def _registrar_snapshot_hud_captura(self, payload: Dict[str, object]) -> None:
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        if str(estado.get("subtipo", "")).strip().lower() != "pokemon":
            return
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        if not self._captura_tem_dados_hud(captura):
            return
        token = str(captura.get("token_arremesso") or "").strip()
        snapshot = dict(captura)
        snapshot.setdefault("dificuldade_captura", estado.get("dificuldade_captura"))
        snapshot["recebido_ms"] = int(pygame.time.get_ticks())
        snapshot["expira_ms"] = int(snapshot["recebido_ms"] + 5000)
        info = self._token_info(token)
        info["hud_snapshot"] = snapshot
        info["hud_recebido_ms"] = int(snapshot["recebido_ms"])

    def captura_hud_atual(self) -> Dict[str, object]:
        agora = int(pygame.time.get_ticks())
        melhor: Dict[str, object] = {}
        melhor_ms = -1
        for token, info in list(self._capturas_por_token.items()):
            if not isinstance(info, dict):
                continue
            snap = info.get("hud_snapshot") if isinstance(info.get("hud_snapshot"), dict) else None
            if not isinstance(snap, dict):
                continue
            if agora > int(snap.get("expira_ms", 0) or 0):
                info.pop("hud_snapshot", None)
                continue
            recebido = int(snap.get("recebido_ms", 0) or 0)
            if recebido > melhor_ms:
                melhor = dict(snap)
                melhor["token_arremesso"] = str(melhor.get("token_arremesso") or token)
                melhor_ms = recebido
        return melhor

    def _registrar_confirmacao_servidor_captura(self, payload: Dict[str, object]) -> None:
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        if not bool(captura.get("captura_pendente", False)):
            return
        token = str(captura.get("token_arremesso") or "").strip()
        if not token:
            return
        info = self._token_info(token)
        info["resultado_servidor_recebido"] = True
        info["resultado_servidor_recebido_ms"] = pygame.time.get_ticks()
        self._registrar_snapshot_hud_captura(payload)
        poke = self.PokemonsPorId.get(int(payload.get("id", 0) or 0))
        if poke is None:
            return
        payload_captura = dict(captura)
        impacto_local_enviado = bool(info.get("impacto_local_enviado", False))
        if hasattr(poke, "aplicar_resultado_servidor_captura"):
            poke.aplicar_resultado_servidor_captura(payload_captura, esperar_colisao=not impacto_local_enviado)
        elif hasattr(poke, "resultado_servidor_recebido_por_token"):
            poke.resultado_servidor_recebido_por_token(token, esperar_colisao=not impacto_local_enviado, atraso_ms=0)
