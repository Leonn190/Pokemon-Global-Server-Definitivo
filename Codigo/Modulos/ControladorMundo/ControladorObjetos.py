"""Controlador de objetos NÃO-player do mundo."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math
import os
import threading
import time

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.Baus import Bau
from Codigo.Geradores.EstruturaNaturais import EstruturaNatural, tipo_estrutura_natural_por_codigo
from Codigo.Geradores.Player.Inventario import Inventario
from Codigo.Geradores.Player.Perfil import Perfil
from Codigo.Geradores.PokemonMundo import Pokemon
from Codigo.Geradores.Projetil import Projetil


class ControladorObjetos:
    def __init__(self):
        self.ObjetosPorId: Dict[int, Dict[str, object]] = {}
        self.PokemonsPorId: Dict[int, Pokemon] = {}
        self.BausPorId: Dict[int, Bau] = {}
        self.AtoresRemotosPorId: Dict[int, Ator] = {}
        self.ProjeteisPorId: Dict[int, Projetil] = {}
        self.EstruturasPorId: Dict[int, EstruturaNatural] = {}

        self._player_local_id: Optional[int] = None
        self._autor_local_id: str = ""
        self._lock_objetos = threading.RLock()
        self._lock_diffs = threading.Lock()
        self._fila_saida_envio: List[Dict[str, object]] = []

        self._chunk_tamanho_tiles = 10
        self._ids_por_chunk: Dict[Tuple[int, int], set[int]] = {}
        self._chunk_por_objeto: Dict[int, Tuple[int, int]] = {}

        self._cache_sprites_fallback: Dict[str, Optional[pygame.Surface]] = {}
        self._ultimo_render_pokemons_ms = pygame.time.get_ticks()
        self._pokemon_alvo_local_id: Optional[int] = None

    def definir_player_local_info(self, player) -> None:
        self._player_local_id = int(getattr(player, "Id", -1) or -1) if player is not None else None

    def definir_autor_local(self, autor_id: str) -> None:
        self._autor_local_id = str(autor_id or "").strip()

    def autor_local(self) -> str:
        return str(self._autor_local_id or "")

    def id_player_local(self) -> int:
        return int(self._player_local_id or -1)

    def _chunk_posicao(self, x: float, y: float) -> Tuple[int, int]:
        return (int(math.floor(float(x) / self._chunk_tamanho_tiles)), int(math.floor(float(y) / self._chunk_tamanho_tiles)))

    def _upsert_indice_chunk_objeto(self, oid: int, payload: Dict[str, object]) -> None:
        chunk_antigo = self._chunk_por_objeto.pop(oid, None)
        if chunk_antigo is not None:
            bucket = self._ids_por_chunk.get(chunk_antigo)
            if bucket is not None:
                bucket.discard(oid)
                if not bucket:
                    self._ids_por_chunk.pop(chunk_antigo, None)

        pos = payload.get("posicao")
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return
        chunk = self._chunk_posicao(float(pos[0]), float(pos[1]))
        self._chunk_por_objeto[oid] = chunk
        self._ids_por_chunk.setdefault(chunk, set()).add(oid)

    def _remover_indice_chunk_objeto(self, oid: int) -> None:
        chunk = self._chunk_por_objeto.pop(int(oid), None)
        if chunk is None:
            return
        bucket = self._ids_por_chunk.get(chunk)
        if bucket is not None:
            bucket.discard(int(oid))
            if not bucket:
                self._ids_por_chunk.pop(chunk, None)

    def _iter_objetos_visiveis_por_chunk(self, camera, margem_chunks: int = 1):
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        tile_px = max(1.0, float(getattr(camera, "TilePx", 50) or 50))
        centro_tiles = (float(camera.PosicaoTiles[0]) + (float(tela_w) * 0.5) / tile_px, float(camera.PosicaoTiles[1]) + (float(tela_h) * 0.5) / tile_px)
        cx, cy = self._chunk_posicao(*centro_tiles)
        alcance_x = max(1, int(math.ceil((float(tela_w) / tile_px) / (2.0 * self._chunk_tamanho_tiles)))) + int(margem_chunks)
        alcance_y = max(1, int(math.ceil((float(tela_h) / tile_px) / (2.0 * self._chunk_tamanho_tiles)))) + int(margem_chunks)
        ids: set[int] = set()
        with self._lock_objetos:
            for dx in range(-alcance_x, alcance_x + 1):
                for dy in range(-alcance_y, alcance_y + 1):
                    ids.update(self._ids_por_chunk.get((cx + dx, cy + dy), set()))
            return [self.ObjetosPorId.get(oid) for oid in ids if oid in self.ObjetosPorId]

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
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            sx, sy = float(pos[0]), float(pos[1])
            if ((sx - px) ** 2 + (sy - py) ** 2) > r2:
                continue
            raio = float(obj.get("raio_colisao", 0.0) or 0.0)
            if raio <= 0.0:
                continue
            yield (int(obj.get("id", 0)), sx, sy, raio, str(obj.get("tipo", "")), float(obj.get("campo", 0.0) or 0.0), float(obj.get("intensidade", 0.0) or 0.0))

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

    def _eh_payload_projetil(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"entidade_projetil", "projetil"}

    def _eh_payload_estrutura(self, payload: Dict[str, object]) -> bool:
        return str(payload.get("tipo", "")).strip().lower() in {"estrutura_natural", "estrutura"}

    def _hidratar_ator_remoto(self, oid: int, payload: Dict[str, object]) -> Ator:
        dados = dict(payload)
        dados["id"] = oid
        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)

        remoto = self.AtoresRemotosPorId.get(oid)
        if remoto is None:
            remoto = Ator(nome_skin=str(dados.get("skin", "S1")), posicao=(float(pos[0]), float(pos[1])), escala_skin_tiles=1.0, tile_px=50)
            remoto.Id = oid
            self.AtoresRemotosPorId[oid] = remoto

        remoto.definir_posicao(float(pos[0]), float(pos[1]))
        nome = dados.get("nome") or dados.get("usuario")
        if nome:
            remoto.Nome = str(nome)
        skin = dados.get("skin")
        if skin and str(skin) != str(getattr(remoto, "NomeSkin", "")):
            remoto.set_nome_skin(str(skin))

        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        if "angulo" in estado:
            remoto.definir_angulo_olhar(float(estado.get("angulo", 0.0)))
        if bool(estado.get("tapa")):
            remoto.iniciar_tapa()

        if remoto.Perfil is None:
            remoto.Perfil = Perfil()
        if remoto.Inventario is None:
            remoto.Inventario = Inventario()
        if isinstance(dados.get("perfil"), dict):
            remoto.Perfil.aplicar_serializado(dados.get("perfil"))
        if isinstance(dados.get("inventario"), dict):
            remoto.Inventario.aplicar_serializado(dados.get("inventario"))

        remoto.update(dados)
        return remoto

    def _reconciliar_projetil_predito_por_token(self, oid_oficial: int, payload: Dict[str, object]) -> None:
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
            self.ObjetosPorId.pop(oid, None)
            self._remover_indice_chunk_objeto(oid)

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
                bau.update(payload) if hasattr(bau, "update") else bau.aplicar_snapshot(payload)
        else:
            self.BausPorId.pop(oid, None)

        if str(payload.get("tipo", "")).strip().lower() == "entidade_player":
            if oid != self.id_player_local():
                self._hidratar_ator_remoto(oid, payload)
        else:
            self.AtoresRemotosPorId.pop(oid, None)

        if self._eh_payload_projetil(payload):
            self._reconciliar_projetil_predito_por_token(oid, payload)
            proj = self.ProjeteisPorId.get(oid)
            if proj is None:
                self.ProjeteisPorId[oid] = Projetil(payload)
            else:
                proj.aplicar_snapshot(payload)
        else:
            self.ProjeteisPorId.pop(oid, None)

        if self._eh_payload_estrutura(payload):
            est = self.EstruturasPorId.get(oid)
            if est is None:
                est = EstruturaNatural(tipo=str((payload.get("estado") or {}).get("subtipo", "natural")), posicao=tuple(payload.get("posicao", [0.0, 0.0])), id_objeto=oid, raio_colisao=float(payload.get("raio_colisao", 0.8)), raio_interacao=float(payload.get("raio_interacao", 0.8)), campo=float(payload.get("campo", 0.0)), intensidade=float(payload.get("intensidade", 0.0)), recursos=dict((payload.get("estado") or {}).get("recursos", {})))
                self.EstruturasPorId[oid] = est
            est.update(payload)
        else:
            self.EstruturasPorId.pop(oid, None)

    def aplicar_diff(self, diff):
        if not isinstance(diff, dict):
            return

        tipo = str(diff.get("tipo", "")).strip().lower()
        objeto_id = diff.get("objeto_id")
        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}

        if tipo == "spawn" and str(diff.get("categoria", "")).strip().lower() == "projetil_lancamento":
            dados = payload if isinstance(payload, dict) else {}
            pos_inicial = dados.get("pos_inicial") if isinstance(dados.get("pos_inicial"), (list, tuple)) else [0.0, 0.0]
            pos_final = dados.get("pos_final") if isinstance(dados.get("pos_final"), (list, tuple)) else list(pos_inicial)
            dx = float(pos_final[0]) - float(pos_inicial[0]); dy = float(pos_final[1]) - float(pos_inicial[1])
            dist = math.hypot(dx, dy) or 1.0
            direcao = [dx / dist, dy / dist]
            token = str(dados.get("token") or "")
            oid_vis = -abs(hash((token, time.time())))
            fake = {
                "id": int(oid_vis),
                "tipo": "entidade_projetil",
                "tipo_projetil": str(dados.get("subtipo_projetil", "pokebola")),
                "subtipo": str(dados.get("variante") or dados.get("item") or "pokebola"),
                "item_base_id": str(dados.get("item_base_id") or ""),
                "dono_id": int(dados.get("dono_id", 0) or 0),
                "posicao": [float(pos_inicial[0]), float(pos_inicial[1])],
                "estado": {
                    "direcao": direcao,
                    "velocidade": float(dados.get("velocidade_tiles_s", 7.0) or 7.0),
                    "alcance": float(dist),
                    "token_arremesso": token,
                    "predito_local": False,
                    "pos_final": [float(pos_final[0]), float(pos_final[1])],
                },
                "token_arremesso": token,
            }
            self.aplicar_diff({"tipo": "spawn", "objeto_id": int(oid_vis), "payload": fake})
            return

        if tipo == "spawn":
            oid = int(payload.get("id", objeto_id or 0))
            dados = dict(payload)
            dados["id"] = oid
            with self._lock_objetos:
                self.ObjetosPorId[oid] = dados
                self._upsert_indice_chunk_objeto(oid, dados)
                self._upsert_especializado(oid, dados)
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
            return

        if tipo == "despawn":
            with self._lock_objetos:
                self.ObjetosPorId.pop(oid, None)
                self.PokemonsPorId.pop(oid, None)
                self.BausPorId.pop(oid, None)
                self.AtoresRemotosPorId.pop(oid, None)
                self.ProjeteisPorId.pop(oid, None)
                self.EstruturasPorId.pop(oid, None)
                self._remover_indice_chunk_objeto(oid)

    def aplicar_pacote_tick(self, pacote_tick: Dict[str, object]) -> None:
        diffs = pacote_tick.get("diffs", []) if isinstance(pacote_tick, dict) else []
        if not isinstance(diffs, list):
            return
        for diff in diffs:
            if isinstance(diff, dict):
                self.aplicar_diff(diff)

    def _detectar_colisao_visual_local_projetil(self, proj: Projetil, objetos_snapshot: Dict[int, Dict[str, object]]):
        raio_busca = 4.0
        for oid, obj in objetos_snapshot.items():
            if not isinstance(obj, dict):
                continue
            if int(oid) == int(getattr(proj, "Id", 0) or 0):
                continue
            if int(oid) == int(getattr(proj, "DonoId", 0) or 0):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            dx = float(pos[0]) - float(proj.Posicao[0])
            dy = float(pos[1]) - float(proj.Posicao[1])
            d2 = (dx * dx) + (dy * dy)
            if d2 > (raio_busca * raio_busca):
                continue
            tipo = str(obj.get("tipo", "")).strip().lower()
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            subtipo = str(estado.get("subtipo", "")).strip().lower()
            if not (subtipo in {"pokemon", "player", "bau"} or tipo.startswith("estrutura")):
                continue
            raio_alvo = float(obj.get("raio_colisao", 0.2) or 0.2)
            limite = float(getattr(getattr(proj, "Colisor", None), "raio_colisao", 0.18)) + raio_alvo
            if d2 <= (limite * limite):
                return obj
        return None

    def atualizar_projeteis_visuais(self, dt: float) -> None:
        with self._lock_objetos:
            projeteis = list(self.ProjeteisPorId.values())
            objetos_snapshot = dict(self.ObjetosPorId)

        for p in projeteis:
            p.atualizar_visual(dt)
            if (not p.Terminado) and (not p.Colidiu):
                alvo = self._detectar_colisao_visual_local_projetil(p, objetos_snapshot)
                if alvo is not None:
                    subtipo = str((alvo.get("estado") or {}).get("subtipo", "")).strip().lower() if isinstance(alvo, dict) else ""
                    if subtipo == "pokemon":
                        poke = self.PokemonsPorId.get(int(alvo.get("id", 0) or 0)) if isinstance(alvo, dict) else None
                        p.encerrar_imediato()
                        if str(getattr(p, "TipoProjetil", "")).lower() != "fruta" and poke is not None and hasattr(poke, "iniciar_captura_fake"):
                            em_captura = bool(getattr(poke, "em_captura_pendente", lambda: False)()) if hasattr(poke, "em_captura_pendente") else bool(getattr(poke, "CapturaEstado", {}).get("captura_pendente", False))
                            fase_cap = str(getattr(poke, "CapturaEstado", {}).get("fase", "nenhuma") or "nenhuma").strip().lower()
                            if (not em_captura) and fase_cap not in {"iniciada", "absorcao", "bola_no_chao", "tremida1", "tremida2", "tremida3", "retorno_bola", "sucesso"}:
                                poke.iniciar_captura_fake(str(getattr(p, "TokenArremesso", "")))
                    else:
                        p.encerrar_com_fade(0.5)
            if p.deve_remover():
                self.aplicar_diff({"tipo": "despawn", "objeto_id": int(p.Id)})

    def _atualizar_alvo_local_captura(self, camera, player_pos: Optional[Tuple[float, float]] = None) -> None:
        if camera is None:
            self._pokemon_alvo_local_id = None
            return
        mouse_mundo = camera.tela_para_mundo_tiles(pygame.mouse.get_pos())
        mx, my = float(mouse_mundo[0]), float(mouse_mundo[1])
        px, py = (float(player_pos[0]), float(player_pos[1])) if player_pos is not None else (mx, my)

        melhor_id = None
        melhor_score = None
        with self._lock_objetos:
            itens = list(self.PokemonsPorId.items())
        for oid, poke in itens:
            fase = str(getattr(poke, "CapturaEstado", {}).get("fase", "nenhuma") or "nenhuma")
            pendente = bool(getattr(poke, "CapturaEstado", {}).get("captura_pendente", False))
            invalido = pendente or fase in {"iniciada", "absorcao", "bola_no_chao", "tremida1", "tremida2", "tremida3", "retorno_bola", "sucesso", "finalizada"}
            if invalido:
                continue
            dxm, dym = float(poke.Posicao[0]) - mx, float(poke.Posicao[1]) - my
            dmouse = math.hypot(dxm, dym)
            if dmouse > 1.35:
                continue
            dplayer = math.hypot(float(poke.Posicao[0]) - px, float(poke.Posicao[1]) - py)
            if dplayer > 8.5:
                continue
            score = dmouse + (dplayer * 0.12)
            if melhor_score is None or score < melhor_score:
                melhor_score = score
                melhor_id = int(oid)

        self._pokemon_alvo_local_id = melhor_id
        for oid, poke in itens:
            poke.definir_alvo_local_captura(int(oid) == int(melhor_id) if melhor_id is not None else False)

    def _obter_sprite_fallback(self, caminho):
        caminho = str(caminho or "").strip()
        if not caminho:
            return None
        if caminho in self._cache_sprites_fallback:
            return self._cache_sprites_fallback[caminho]
        if not os.path.exists(caminho):
            self._cache_sprites_fallback[caminho] = None
            return None
        try:
            sprite = pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            sprite = None
        self._cache_sprites_fallback[caminho] = sprite
        return sprite

    def _render_fallback_objeto(self, tela, camera, obj: Dict[str, object], cor_fallback=(222, 233, 245)):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            return
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))

        codigo_natural = obj.get("codigo_natural")
        if codigo_natural is None and isinstance(obj.get("estado"), dict):
            codigo_natural = obj["estado"].get("codigo_natural")
        cfg_natural = tipo_estrutura_natural_por_codigo(codigo_natural)

        sprite_path = str(obj.get("sprite", "")).strip()
        if not sprite_path and cfg_natural:
            sprite_path = str(cfg_natural.get("sprite", "")).strip()

        sprite = self._obter_sprite_fallback(sprite_path)
        if sprite is not None:
            sprite_rect = sprite.get_rect(center=(int(px), int(py)))
            tela.blit(sprite, sprite_rect)
            return

        raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
        raio_px = int(raio_raw if raio_raw > 4.0 else raio_raw * camera.TilePx)
        raio_px = max(3, min(80, raio_px))
        pygame.draw.circle(tela, cor_fallback, (int(px), int(py)), raio_px)

    def _objeto_posicao_tela_se_visivel(self, obj: Dict[str, object], camera, margem_px: int = 120):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return None
        px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        if px < -margem_px or py < -margem_px or px > (tela_w + margem_px) or py > (tela_h + margem_px):
            return None
        return px, py

    def renderizar_entidades(self, tela, camera, ignorar_id=None, player_pos=None):
        self._atualizar_alvo_local_captura(camera, player_pos=player_pos)
        agora = pygame.time.get_ticks()
        dt_pokemons = max(0.0, (agora - self._ultimo_render_pokemons_ms) / 1000.0)
        self._ultimo_render_pokemons_ms = agora

        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue
            if str(obj.get("tipo", "")).startswith("estrutura"):
                continue
            if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                continue

            poke = self.PokemonsPorId.get(oid)
            if poke is not None:
                poke.render(tela, camera, dt_pokemons)
                continue

            bau = self.BausPorId.get(oid)
            if bau is not None:
                bau.render(tela, camera)
                continue

            proj = self.ProjeteisPorId.get(oid)
            if proj is not None:
                proj.desenhar(tela, camera)
                continue

            ator_remoto = self.AtoresRemotosPorId.get(oid)
            if ator_remoto is not None:
                ator_remoto.atualizar(dt_pokemons)
                ator_remoto.set_tile_px(getattr(camera, "TilePx", 50))
                pos_tela = camera.mundo_para_tela_px(ator_remoto.Posicao)
                ator_remoto.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=0.0)
                if getattr(ator_remoto, "Nome", ""):
                    Ator.desenhar_nome(tela, pos_tela, ator_remoto.Nome)
                continue

            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(222, 233, 245))

    def renderizar_estruturas(self, tela, camera):
        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            if not str(obj.get("tipo", "")).startswith("estrutura"):
                continue
            if self._objeto_posicao_tela_se_visivel(obj, camera, margem_px=220) is None:
                continue
            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(125, 86, 54))

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        self.renderizar_entidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self.renderizar_estruturas(tela, camera)
