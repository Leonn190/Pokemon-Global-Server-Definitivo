"""Mixin de colisoes e alvos interagiveis do ControladorObjetos."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math

from Codigo.ModulosMundo.ControladorAtores import ControladorAtores
from Codigo.ModulosMundo.Geradores.Estadio import GeradorEstadio
from Codigo.ModulosMundo.Geradores.portal import Portal


class InteracoesObjetosMixin:
    def _payload_tem_colisao_solida(self, payload: Dict[str, object]) -> bool:
        if not isinstance(payload, dict):
            return False
        tipo = str(payload.get("tipo", "")).strip().lower()
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        subtipo = str(estado.get("subtipo", "")).strip().lower()

        if tipo == "entidade_player":
            return True
        if self._eh_payload_pokemon(payload):
            return True
        if self._eh_payload_ator(payload):
            return True
        if self._eh_payload_bau(payload):
            return True
        if self._eh_payload_estrutura(payload):
            if self._eh_dungeon_aberta(payload):
                return False
            return True
        if self._eh_payload_estadio(payload):
            return True

        if tipo in {"entidade_item_mundo", "item_mundo", "entidade_projetil", "projetil", "entidade_xp_mundo", "xp_mundo"}:
            return False
        if subtipo in {"item_mundo", "projetil", "xp_mundo"}:
            return False
        return False

    def _posicao_raio_colisao_client(self, oid: int, obj: Dict[str, object]):
        if self._eh_dungeon_aberta(obj):
            return None, 0.0
        if self._eh_payload_pokemon(obj):
            poke = self.PokemonsPorId.get(int(oid))
            colisor = getattr(poke, "Colisor", None) if poke is not None else None
            if colisor is not None:
                return (float(colisor.x), float(colisor.y)), float(getattr(colisor, "raio_colisao", 0.0) or 0.0)
        pos = obj.get("posicao")
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return None, 0.0
        return (float(pos[0]), float(pos[1])), float(obj.get("raio_colisao", 0.0) or 0.0)

    def iter_colisores_proximos_por_raio(self, posicao: Tuple[float, float], raio_tiles: float = 10.0):
        px, py = float(posicao[0]), float(posicao[1])
        chunk_cx, chunk_cy = self._chunk_posicao(px, py)
        alcance = max(1, int(math.ceil(float(raio_tiles) / float(self._chunk_tamanho_tiles))))

        with self._lock_objetos:
            ids = set()
            for dx in range(-alcance, alcance + 1):
                for dy in range(-alcance, alcance + 1):
                    ids.update(self._ids_por_chunk.get((chunk_cx + dx, chunk_cy + dy), set()))
            objs = [self.ObjetosPorId.get(oid) for oid in ids]

        r2 = raio_tiles * raio_tiles
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            if not self._payload_na_dimensao_local(obj):
                continue
            if not self._payload_tem_colisao_solida(obj):
                continue
            pos_colisao, raio = self._posicao_raio_colisao_client(int(obj.get("id", 0) or 0), obj)
            if pos_colisao is None:
                continue
            sx, sy = pos_colisao
            if ((sx - px) ** 2 + (sy - py) ** 2) > r2:
                continue
            if raio <= 0.0:
                continue
            tipo_obj = str(obj.get("tipo", ""))
            if self._eh_payload_bau(obj):
                tipo_obj = "estrutura_bau"
            if self._eh_payload_estadio(obj):
                estado_obj = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
                rx_visual = float(estado_obj.get("raio_elipse_x", raio) or raio)
                ry_visual = float(estado_obj.get("raio_elipse_y", raio) or raio)
                rx_casco, ry_casco = GeradorEstadio.raios_casco_colisao(rx_visual, ry_visual)
                off_casco_x, off_casco_y = GeradorEstadio.deslocamento_casco_colisao(ry_visual)
                yield (
                    int(obj.get("id", 0)), sx + off_casco_x, sy + off_casco_y, raio, "estrutura_estadio",
                    float(obj.get("campo", 0.0) or 0.0), float(obj.get("intensidade", 0.0) or 0.0),
                    "elipse", rx_casco, ry_casco,
                )
                continue
            yield (int(obj.get("id", 0)), sx, sy, raio, tipo_obj, float(obj.get("campo", 0.0) or 0.0), float(obj.get("intensidade", 0.0) or 0.0))
        yield from self._iter_colisores_armadilhas_dungeon(posicao, raio_tiles)

    def _iter_colisores_armadilhas_dungeon(self, posicao: Tuple[float, float], raio_tiles: float):
        dim = self._dimensao_player_local()
        if not str(dim or "").startswith("Dungeon_"):
            return
        layout = self.LayoutDungeonAtual if isinstance(self.LayoutDungeonAtual, dict) else {}
        if not layout:
            return
        px, py = float(posicao[0]), float(posicao[1])
        r2 = float(raio_tiles) * float(raio_tiles)
        estado_armadilhas = layout.get("estado_armadilhas") if isinstance(layout.get("estado_armadilhas"), dict) else {}
        traps_estado = estado_armadilhas.get("traps") if isinstance(estado_armadilhas.get("traps"), dict) else {}
        oid_base = -900000
        idx = 0
        for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
            if not isinstance(sala, dict):
                continue
            cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
            for trap in list(cfg_sala.get("armadilhas") or []):
                if not isinstance(trap, dict):
                    continue
                tipo = str(trap.get("tipo") or "")
                cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
                solido = bool(cfg.get("solido", False) or cfg.get("solido_centro", False))
                if not solido or tipo == "espeto_movel":
                    continue
                tid = str(trap.get("id") or "")
                estado = traps_estado.get(tid) if isinstance(traps_estado.get(tid), dict) else {}
                pos = estado.get("posicao") if isinstance(estado.get("posicao"), (list, tuple)) else trap.get("posicao")
                if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                    continue
                sx, sy = float(pos[0]), float(pos[1])
                if ((sx - px) ** 2 + (sy - py) ** 2) > r2:
                    continue
                if tipo == "espeto":
                    raio = max(0.62, float(cfg.get("raio_colisao", cfg.get("raio_dano", 0.8)) or 0.8))
                else:
                    raio = max(0.56, float(cfg.get("raio_colisao", 0.58) or 0.58))
                idx += 1
                yield (oid_base - idx, sx, sy, raio, "armadilha_dungeon", 0.0, 0.0)

    def estrutura_colidindo(self, posicao: Tuple[float, float], raio: float) -> Optional[Dict[str, object]]:
        colisoes = self.estruturas_colidindo(posicao, raio)
        return colisoes[0] if colisoes else None

    def estruturas_colidindo(self, posicao: Tuple[float, float], raio: float) -> List[Dict[str, object]]:
        px, py = float(posicao[0]), float(posicao[1])
        encontrados: List[Tuple[float, Dict[str, object]]] = []
        with self._lock_objetos:
            estruturas = [self.ObjetosPorId.get(oid) for oid in self.EstruturasPorId.keys()]
        for obj in estruturas:
            if not isinstance(obj, dict):
                continue
            if self._eh_dungeon_aberta(obj):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            rr = float(obj.get("raio_colisao", 0.0) or 0.0) + max(0.0, float(raio))
            d2 = (sx - px) ** 2 + (sy - py) ** 2
            if d2 > (rr * rr):
                continue
            encontrados.append((d2, obj))
        encontrados.sort(key=lambda par: par[0])
        return [obj for _, obj in encontrados]

    def baus_colidindo(self, posicao: Tuple[float, float], raio: float) -> List[Dict[str, object]]:
        px, py = float(posicao[0]), float(posicao[1])
        encontrados: List[Tuple[float, Dict[str, object]]] = []
        with self._lock_objetos:
            baus = [self.ObjetosPorId.get(oid) for oid in self.BausPorId.keys()]
        for obj in baus:
            if not isinstance(obj, dict):
                continue
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            if bool(estado.get("aberto", False)):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            rr = float(obj.get("raio_colisao", 0.0) or 0.0) + max(0.0, float(raio))
            d2 = (sx - px) ** 2 + (sy - py) ** 2
            if d2 > (rr * rr):
                continue
            encontrados.append((d2, obj))
        encontrados.sort(key=lambda par: par[0])
        return [obj for _, obj in encontrados]

    def _eh_payload_pokemon(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", "")).strip().lower()
        if tipo in ("entidade_pokemon", "pokemon"):
            return True
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return str(estado.get("subtipo", "")).strip().lower() == "pokemon"

    def _eh_payload_bau(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", ""))
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return tipo.startswith("entidade") and str(estado.get("subtipo", "")).strip().lower() == "bau"

    def _eh_payload_ator(self, payload: Dict[str, object]) -> bool:
        tipo = str(payload.get("tipo", "")).strip().lower()
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        if tipo in {"entidade_player", "player"}:
            return True
        subtipo = str(estado.get("subtipo", "")).strip().lower()
        return subtipo == "player" or ControladorAtores._eh_npc_estado(estado)

    def _eh_payload_projetil(self, payload: Dict[str, object]) -> bool:
        return self._criaveis.eh_payload_projetil(payload)

    def _eh_payload_estrutura(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"estrutura_natural", "estrutura"}

    @staticmethod
    def _eh_dungeon_aberta(payload: Dict[str, object]) -> bool:
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return str(estado.get("subtipo") or "").strip().lower() == "dungeon" and bool(estado.get("porta_ativa", False) or estado.get("estrutura_quebrada", False))

    def _eh_payload_estadio(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"entidade_estadio", "estadio"}

    @staticmethod
    def _saida_interna_estadio(estado: dict) -> List[float]:
        if isinstance(estado.get("saida_interna_pos"), (list, tuple)) and len(estado.get("saida_interna_pos")) == 2:
            return [float(estado.get("saida_interna_pos")[0]), float(estado.get("saida_interna_pos")[1])]
        largura = float(estado.get("largura_interna", 60.0) or 60.0)
        altura = float(estado.get("altura_interna", 40.0) or 40.0)
        return [largura * 0.5, max(1.0, altura - 3.0)]

    @staticmethod
    def _entrada_externa_estadio(payload_estadio: dict) -> List[float]:
        estado = payload_estadio.get("estado") if isinstance(payload_estadio.get("estado"), dict) else {}
        pos = payload_estadio.get("posicao") if isinstance(payload_estadio.get("posicao"), (list, tuple)) and len(payload_estadio.get("posicao")) == 2 else None
        if pos is not None:
            raio_y = float(estado.get("raio_elipse_y", payload_estadio.get("raio_colisao", 24.0)) or 24.0)
            off_x, off_y = GeradorEstadio.offset_porta_externa(raio_y)
            return [float(pos[0]) + off_x, float(pos[1]) + off_y]
        if isinstance(estado.get("entrada_pos"), (list, tuple)) and len(estado.get("entrada_pos")) == 2:
            return [float(estado.get("entrada_pos")[0]), float(estado.get("entrada_pos")[1])]
        if isinstance(estado.get("entrada_offset"), (list, tuple)) and len(estado.get("entrada_offset")) == 2:
            return [float(estado.get("entrada_offset")[0]), float(estado.get("entrada_offset")[1])]
        return [0.0, 0.0]

    def alvo_interagivel_atual(self, pos_player: Tuple[float, float], dimensao_player: str, estadio_atual_id: int = 0) -> Optional[Dict[str, object]]:
        px, py = float(pos_player[0]), float(pos_player[1])
        dim = str(dimensao_player or self._dimensao_player_local() or "Mundo")
        player_payload = self.ObjetosPorId.get(int(self.id_player_local() or -1), {})
        estado_p = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        estadio_real_id = int(estado_p.get("estadio_atual_id", player_payload.get("estadio_atual_id", estadio_atual_id)) or 0)

        candidatos: List[Tuple[float, Dict[str, object]]] = []

        if dim.startswith("Dungeon_"):
            estado_dungeon = estado_p.get("estado_dungeon") if isinstance(estado_p.get("estado_dungeon"), dict) else {}
            destrancadas = {str(p) for p in list(estado_dungeon.get("portas_destrancadas") or [])}
            porta_idx = int(estado_dungeon.get("porta_idx", 1) or 1)
            layout = self.LayoutDungeonAtual if isinstance(self.LayoutDungeonAtual, dict) else {}
            bloco_w = int(layout.get("largura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)) or 32)
            bloco_h = int(layout.get("altura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 24)) or 24)
            for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
                if not isinstance(sala, dict):
                    continue
                pos_s = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
                if not pos_s:
                    continue
                for porta in list(sala.get("portas_info") or []):
                    if not bool(porta.get("trancada", False)) or str(porta.get("id") or "") in destrancadas:
                        continue
                    direcao = str(porta.get("direcao") or "")
                    cx = float(pos_s[0]) * bloco_w + bloco_w * 0.5
                    cy = float(pos_s[1]) * bloco_h + bloco_h * 0.5
                    if direcao == "N":
                        cy = float(pos_s[1]) * bloco_h
                    elif direcao == "S":
                        cy = (float(pos_s[1]) + 1.0) * bloco_h - 1.0
                    elif direcao == "L":
                        cx = (float(pos_s[0]) + 1.0) * bloco_w - 1.0
                    elif direcao == "O":
                        cx = float(pos_s[0]) * bloco_w
                    d2 = (cx - px) ** 2 + (cy - py) ** 2
                    if d2 <= (2.0 * 2.0):
                        candidatos.append((d2, {"tipo": "dungeon_porta_trancada", "porta_id": str(porta.get("id") or ""), "posicao": [cx, cy]}))
            entradas = layout.get("entradas") if isinstance(layout.get("entradas"), list) else []
            entrada = next((e for e in entradas if int(e.get("porta_idx", 0) or 0) == porta_idx), None)
            saida = entrada.get("saida") if isinstance(entrada, dict) else None
            if isinstance(saida, (list, tuple)) and len(saida) == 2:
                d2 = (float(saida[0]) - px) ** 2 + (float(saida[1]) - py) ** 2
                if d2 <= (Portal.RAIO_INTERACAO_TILES * Portal.RAIO_INTERACAO_TILES):
                    candidatos.append((d2, {"tipo": "dungeon_saida", "posicao": [float(saida[0]), float(saida[1])] }))
        elif dim != "Mundo":
            estadio = self.EstadiosPorId.get(estadio_real_id, {})
            if not isinstance(estadio, dict) or not estadio:
                for candidato in self.EstadiosPorId.values():
                    if not isinstance(candidato, dict):
                        continue
                    estado_c = candidato.get("estado") if isinstance(candidato.get("estado"), dict) else {}
                    if str(estado_c.get("dimensao_destino") or "EstadioNormal") == dim:
                        estadio = candidato
                        break
            estado = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}
            porta = self._saida_interna_estadio(estado)
            d2 = (float(porta[0]) - px) ** 2 + (float(porta[1]) - py) ** 2
            if d2 <= (2.0 * 2.0):
                candidatos.append((d2, {"tipo": "estadio_saida", "estadio": estadio, "posicao": porta}))
        else:
            for estadio in list(self.EstadiosPorId.values()):
                if not isinstance(estadio, dict):
                    continue
                entrada = self._entrada_externa_estadio(estadio)
                d2 = (float(entrada[0]) - px) ** 2 + (float(entrada[1]) - py) ** 2
                if d2 <= (2.0 * 2.0):
                    candidatos.append((d2, {"tipo": "estadio_entrada", "estadio": estadio, "posicao": [float(entrada[0]), float(entrada[1])] }))
            objs = self._estruturas_interagiveis_por_dimensao(dim)
            for obj in objs:
                estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
                if str(estado.get("subtipo") or "").lower() != "dungeon":
                    continue
                if not bool(estado.get("porta_ativa", False) or estado.get("estrutura_quebrada", False)):
                    continue
                pos_d = obj.get("posicao") if isinstance(obj.get("posicao"), (list, tuple)) and len(obj.get("posicao")) == 2 else None
                if pos_d is None:
                    continue
                d2 = (float(pos_d[0]) - px) ** 2 + (float(pos_d[1]) - py) ** 2
                if d2 <= (Portal.RAIO_INTERACAO_TILES * Portal.RAIO_INTERACAO_TILES):
                    candidatos.append((d2, {"tipo": "dungeon_entrada", "estrutura": obj, "posicao": [float(pos_d[0]), float(pos_d[1])] }))

        npc_alvo = self.npc_interagivel_proximo((px, py), raio=2.3)
        if isinstance(npc_alvo, dict):
            npc_obj = npc_alvo.get("obj") if isinstance(npc_alvo.get("obj"), dict) else {}
            npc_pos = npc_obj.get("posicao") if isinstance(npc_obj.get("posicao"), (list, tuple)) and len(npc_obj.get("posicao")) == 2 else None
            if npc_pos is not None:
                d2_npc = (float(npc_pos[0]) - px) ** 2 + (float(npc_pos[1]) - py) ** 2
                candidatos.append((d2_npc, {"tipo": "npc", "npc": dict(npc_obj), "posicao": [float(npc_pos[0]), float(npc_pos[1])]}))

        if not candidatos:
            return None
        candidatos.sort(key=lambda item: float(item[0]))
        return candidatos[0][1]

    def mensagem_interacao_estadio(self, pos_player: Tuple[float, float], dimensao_player: str, estadio_atual_id: int = 0) -> str:
        alvo = self.alvo_interagivel_atual(pos_player=pos_player, dimensao_player=dimensao_player, estadio_atual_id=estadio_atual_id)
        if not isinstance(alvo, dict):
            return ""
        tipo = str(alvo.get("tipo") or "").strip().lower()
        if tipo == "estadio_entrada":
            return "Pressione F para entrar no estádio"
        if tipo == "estadio_saida":
            return "Pressione F para sair do estádio"
        if tipo == "npc":
            return "Pressione F para interagir"
        if tipo == "dungeon_entrada":
            return "Pressione F para entrar na dungeon"
        if tipo == "dungeon_saida":
            return "Pressione F para sair da dungeon"
        if tipo == "dungeon_porta_trancada":
            return ""
        return "Pressione F para interagir"

    def _estruturas_interagiveis_por_dimensao(self, dim: str):
        with self._lock_objetos:
            vals = list(self.ObjetosPorId.values())
        out = []
        for obj in vals:
            if not isinstance(obj, dict) or not self._eh_payload_estrutura(obj):
                continue
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            if str(estado.get("dimensao") or obj.get("dimensao") or "Mundo") != dim:
                continue
            out.append(obj)
        return out

    def npc_interagivel_proximo(self, posicao: Tuple[float, float], raio: float = 2.2) -> Optional[Dict[str, object]]:
        with self._lock_objetos:
            snapshot = dict(self.ObjetosPorId)
        return self._atores.npc_proximo(snapshot, posicao=posicao, raio=raio, dimensao_local=self._dimensao_player_local())
