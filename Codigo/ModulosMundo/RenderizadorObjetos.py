"""Mixin de renderizacao e efeitos visuais do ControladorObjetos."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math
import os

import pygame

from Codigo.ModulosMundo.Geradores.Dungeon import renderizar_entrada_mundo as renderizar_entrada_dungeon_mundo
from Codigo.ModulosMundo.Geradores.Estadio import GeradorEstadio, EstadioInterno
from Codigo.ModulosMundo.Geradores.EstruturaNaturais import (
    limitar_escala_estrutura_natural,
    prioridade_estrutura_natural,
    tipo_estrutura_natural_por_codigo,
)
from Codigo.ModulosMundo.Geradores.PokemonMundo import Pokemon
from Codigo.ModulosMundo.Geradores.Projetil import Projetil


class RenderizadorObjetosMixin:
    def _detectar_colisao_visual_local_projetil(self, proj: Projetil, objetos_snapshot: Dict[int, Dict[str, object]]):
        raio_busca = 4.0
        for oid, obj in objetos_snapshot.items():
            if not isinstance(obj, dict):
                continue
            if int(oid) == int(getattr(proj, "Id", 0) or 0):
                continue
            if int(oid) == int(getattr(proj, "DonoId", 0) or 0):
                continue
            pos_colisao, raio_alvo = self._posicao_raio_colisao_client(int(oid), obj)
            if pos_colisao is None:
                continue
            dx = float(pos_colisao[0]) - float(proj.Posicao[0])
            dy = float(pos_colisao[1]) - float(proj.Posicao[1])
            d2 = (dx * dx) + (dy * dy)
            if d2 > (raio_busca * raio_busca):
                continue
            tipo = str(obj.get("tipo", "")).strip().lower()
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            subtipo = str(estado.get("subtipo", "")).strip().lower()
            if not (subtipo in {"pokemon", "player", "bau"} or tipo.startswith("estrutura")):
                continue
            if raio_alvo <= 0.0:
                if self._eh_payload_pokemon(obj):
                    continue
                raio_alvo = 0.2
            limite = float(getattr(getattr(proj, "Colisor", None), "raio_colisao", 0.18)) + raio_alvo
            if d2 <= (limite * limite):
                return obj
        return None

    def _registrar_colisao_local_projetil_pokemon(self, proj: Projetil, poke: Pokemon) -> None:
        token = str(getattr(proj, "TokenArremesso", "") or "").strip()
        if not token:
            return
        info = self._token_info(token)
        agora_ms = pygame.time.get_ticks()
        info["impacto_local_enviado"] = True
        info["impacto_local_enviado_ms"] = agora_ms
        eh_fruta = str(getattr(proj, "TipoProjetil", "")).lower() == "fruta"
        if (not eh_fruta) and hasattr(poke, "registrar_colisao_projetil_local"):
            poke.registrar_colisao_projetil_local(token, nome_bola=str(getattr(proj, "ItemNome", "") or getattr(proj, "Subtipo", "pokeball")), tempo_espera_confirmacao_ms=1500)
        dono_ref = getattr(self, "_player_local_ref", None)
        if dono_ref is not None and hasattr(dono_ref, "Posicao"):
            dono_pos = tuple(getattr(dono_ref, "Posicao", (0.0, 0.0)))
        else:
            dono_payload = self.ObjetosPorId.get(int(getattr(proj, "DonoId", 0) or 0), {})
            dono_pos = tuple(dono_payload.get("posicao") or proj.Posicao)
        dist = math.hypot(float(proj.Posicao[0]) - float(dono_pos[0]), float(proj.Posicao[1]) - float(dono_pos[1]))
        captura_critica_cliente = bool(getattr(poke, "calcular_captura_critica_local", lambda _p: False)(tuple(proj.Posicao)))
        self.EnfileirarDiffRapida({
            "tipo": "evento",
            "categoria": "fruta_impacto_cliente" if eh_fruta else "captura_impacto_cliente",
            "payload": {
                "token": token,
                "pokemon_id": int(getattr(poke, "Id", 0) or 0),
                "dono_id": int(getattr(proj, "DonoId", 0) or 0),
                "tipo_projetil": str(getattr(proj, "TipoProjetil", "") or ""),
                "variante": str(getattr(proj, "Subtipo", "") or ""),
                "item_nome": str(getattr(proj, "ItemNome", "") or ""),
                "item_base_id": str(getattr(proj, "ItemBaseId", "") or ""),
                "pos_projetil": [float(proj.Posicao[0]), float(proj.Posicao[1])],
                "pos_pokemon": [float(poke.Posicao[0]), float(poke.Posicao[1])],
                "distancia_arremesso_tiles": float(dist),
                "captura_critica_cliente": bool(captura_critica_cliente),
            },
        })
        if bool(info.get("resultado_servidor_recebido", False)) and hasattr(poke, "resultado_servidor_recebido_por_token"):
            poke.resultado_servidor_recebido_por_token(token, esperar_colisao=False, atraso_ms=0)

    def atualizar_projeteis_visuais(self, dt: float) -> None:
        with self._lock_objetos:
            objetos_snapshot = dict(self.ObjetosPorId)

        def _registrar_colisao(p, alvo_obj):
            if not isinstance(alvo_obj, dict):
                return
            poke = self.PokemonsPorId.get(int(alvo_obj.get("id", 0) or 0))
            if poke is not None:
                self._registrar_colisao_local_projetil_pokemon(p, poke)

        self._criaveis.atualizar_visuais(
            dt=dt,
            objetos_snapshot=objetos_snapshot,
            detectar_colisao_projetil_cb=self._detectar_colisao_visual_local_projetil,
            registrar_colisao_pokemon_cb=_registrar_colisao,
            aplicar_despawn_cb=lambda oid: self.aplicar_diff({"tipo": "despawn", "objeto_id": int(oid)}),
        )

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
            invalido = pendente or fase in {"captura", "checagem", "fuga", "volta"}
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

    def _obter_sprite_fallback_escalado(self, caminho: str, sprite: pygame.Surface, escala: float) -> pygame.Surface:
        largura = max(1, int(sprite.get_width() * escala))
        altura = max(1, int(sprite.get_height() * escala))
        chave = (str(caminho or ""), largura, altura)
        sprite_escalado = self._cache_sprites_fallback_escalados.get(chave)
        if sprite_escalado is not None:
            return sprite_escalado
        sprite_escalado = pygame.transform.smoothscale(sprite, (largura, altura))
        self._cache_sprites_fallback_escalados[chave] = sprite_escalado
        return sprite_escalado

    def _cfg_natural_cacheada(self, codigo_natural) -> Optional[Dict[str, object]]:
        chave = codigo_natural if codigo_natural is not None else ""
        if chave in self._cache_cfg_natural:
            return self._cache_cfg_natural[chave]
        cfg = tipo_estrutura_natural_por_codigo(codigo_natural)
        self._cache_cfg_natural[chave] = cfg
        return cfg

    @staticmethod
    def _rotacao_sprite_payload(obj: Dict[str, object]) -> float:
        estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
        try:
            return float(estado.get("rotacao_graus", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _render_fallback_objeto(self, tela, camera, obj: Dict[str, object], cor_fallback=(222, 233, 245), escala: float = 1.0, pos_tela: Optional[Tuple[float, float]] = None, fila_blits: Optional[List[tuple]] = None, tela_size: Optional[Tuple[int, int]] = None):
        if pos_tela is None:
            pos = obj.get("posicao", [0.0, 0.0])
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                return
            px, py = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
        else:
            px, py = pos_tela
        px_int = int(px)
        py_int = int(py)

        codigo_natural = obj.get("codigo_natural")
        if codigo_natural is None and isinstance(obj.get("estado"), dict):
            codigo_natural = obj["estado"].get("codigo_natural")
        cfg_natural = self._cfg_natural_cacheada(codigo_natural)

        sprite_path = str(obj.get("sprite", "")).strip()
        if not sprite_path and cfg_natural:
            sprite_path = str(cfg_natural.get("sprite", "")).strip()

        sprite = self._obter_sprite_fallback(sprite_path)
        if sprite is not None:
            escala = limitar_escala_estrutura_natural(float(escala or 1.0)) * max(0.05, float(getattr(camera, "TilePx", 50) or 50) / 50.0)
            if abs(escala - 1.0) > 0.001:
                sprite = self._obter_sprite_fallback_escalado(sprite_path, sprite, escala)
            rotacao = self._rotacao_sprite_payload(obj) % 360.0
            if abs(rotacao) > 0.001:
                ang = int(round(rotacao)) % 360
                chave_rot = (str(sprite_path or ""), sprite.get_width(), sprite.get_height(), ang)
                sprite_rot = self._cache_sprites_fallback_escalados.get(chave_rot)
                if sprite_rot is None:
                    sprite_rot = pygame.transform.rotate(sprite, rotacao)
                    self._cache_sprites_fallback_escalados[chave_rot] = sprite_rot
                sprite = sprite_rot
            largura_sprite = sprite.get_width()
            altura_sprite = sprite.get_height()
            destino_x = px_int - (largura_sprite // 2)
            destino_y = py_int - (altura_sprite // 2)
            tela_w, tela_h = tela_size if tela_size is not None else tela.get_size()
            clip_x = max(0, -destino_x)
            clip_y = max(0, -destino_y)
            largura_visivel = min(largura_sprite - clip_x, int(tela_w) - max(0, destino_x))
            altura_visivel = min(altura_sprite - clip_y, int(tela_h) - max(0, destino_y))
            if largura_visivel <= 0 or altura_visivel <= 0:
                return
            destino = (destino_x, destino_y)
            area = None
            if clip_x > 0 or clip_y > 0 or largura_visivel != largura_sprite or altura_visivel != altura_sprite:
                destino = (destino_x + clip_x, destino_y + clip_y)
                area = (clip_x, clip_y, largura_visivel, altura_visivel)
            if fila_blits is not None:
                if area is not None:
                    fila_blits.append((sprite, destino, area))
                else:
                    fila_blits.append((sprite, destino))
                return
            if area is not None:
                tela.blit(sprite, destino, area)
            else:
                tela.blit(sprite, destino)
            return

        raio_raw = max(0.0, float(obj.get("raio_colisao", 0.4)))
        raio_px = int(raio_raw if raio_raw > 4.0 else raio_raw * camera.TilePx)
        raio_px = int(max(1.0, raio_px * limitar_escala_estrutura_natural(float(escala or 1.0))))
        raio_px = max(3, min(80, raio_px))
        pygame.draw.circle(tela, cor_fallback, (px_int, py_int), raio_px)

    @staticmethod
    def _aplicar_blits_batch(tela, fila_blits: List[tuple]) -> None:
        if not fila_blits:
            return
        blits = getattr(tela, "blits", None)
        if callable(blits):
            try:
                blits(fila_blits, doreturn=False)
            except TypeError:
                blits(fila_blits)
            return
        for item in fila_blits:
            if len(item) >= 3:
                tela.blit(item[0], item[1], item[2])
            else:
                tela.blit(item[0], item[1])

    def _objeto_posicao_tela_se_visivel(self, obj: Dict[str, object], camera, margem_px: int = 120):
        pos = obj.get("posicao", [0.0, 0.0])
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            return None
        cam_pos = getattr(camera, "PosicaoTiles", (0.0, 0.0))
        tile_px = float(getattr(camera, "TilePx", 50) or 50)
        px = (float(pos[0]) - float(cam_pos[0])) * tile_px
        py = (float(pos[1]) - float(cam_pos[1])) * tile_px
        tela_w, tela_h = getattr(camera, "TamanhoTelaPx", (1280.0, 720.0))
        if px < -margem_px or py < -margem_px or px > (tela_w + margem_px) or py > (tela_h + margem_px):
            return None
        return px, py

    def atualizar_visuais(self, dt: float, camera, ignorar_id=None, player_pos=None):
        dt = max(0.0, float(dt))
        self.ArmadilhasDungeon.atualizar(self.LayoutDungeonAtual, dt)
        self._atualizar_alvo_local_captura(camera, player_pos=player_pos)
        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue
            if self._objeto_posicao_tela_se_visivel(obj, camera) is None:
                continue
            poke = self.PokemonsPorId.get(oid)
            if poke is not None and hasattr(poke, "atualizar_visual"):
                poke.atualizar_visual(dt)
                continue
            bau = self.BausPorId.get(oid)
            if bau is not None and hasattr(bau, "atualizar_visual"):
                bau.atualizar_visual(dt)
                continue
            self._atores.atualizar_visual(oid, dt)

        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=3):
            if not isinstance(obj, dict):
                continue
            if not str(obj.get("tipo", "")).startswith("estrutura"):
                continue
            est = self.EstruturasPorId.get(int(obj.get("id", 0) or 0))
            if est is not None and hasattr(est, "atualizar_visual"):
                est.atualizar_visual(dt)

    def coletar_efeito_captura_shader(self, camera, tamanho_tela) -> Dict[str, object]:
        """Escolhe a captura visível mais relevante para o pós-processo.

        O compositor atual aplica um efeito radial por vez. Se houver mais de
        uma captura simultânea na tela, priorizamos a com maior power e, em
        empate, a captura crítica. O resultado não entra na prioridade para o
        shader não antecipar sucesso ou fuga.
        """
        melhor: Dict[str, object] = {}
        melhor_score = -1.0
        for poke in list(self.PokemonsPorId.values()):
            if poke is None or not hasattr(poke, "dados_shader_captura"):
                continue
            dados = poke.dados_shader_captura(camera, tamanho_tela)
            if not isinstance(dados, dict) or not dados:
                continue
            power = float(dados.get("capture_power", 0.0) or 0.0)
            critica = float(dados.get("capture_critical", 0.0) or 0.0)
            score = power + critica * 0.08
            if score > melhor_score:
                melhor = dict(dados)
                melhor_score = float(score)
        return melhor

    def renderizar_entidades(self, tela, camera, ignorar_id=None, player_pos=None):
        _ = player_pos

        remover_pokemons: List[int] = []
        fila_blits: List[Tuple[pygame.Surface, Tuple[int, int]]] = []
        for obj in self._iter_objetos_visiveis_por_chunk(camera, margem_chunks=1):
            if not isinstance(obj, dict):
                continue
            oid = int(obj.get("id", -1))
            if ignorar_id is not None and oid == int(ignorar_id):
                continue
            if self._eh_payload_estrutura(obj) or self._eh_payload_estadio(obj):
                continue
            pos_tela = self._objeto_posicao_tela_se_visivel(obj, camera)
            if pos_tela is None:
                continue

            poke = self.PokemonsPorId.get(oid)
            if poke is not None:
                if fila_blits:
                    self._aplicar_blits_batch(tela, fila_blits)
                    fila_blits.clear()
                poke.render(tela, camera)
                if hasattr(poke, "pronto_para_remover_local") and poke.pronto_para_remover_local():
                    remover_pokemons.append(oid)
                continue

            bau = self.BausPorId.get(oid)
            if bau is not None:
                if fila_blits:
                    self._aplicar_blits_batch(tela, fila_blits)
                    fila_blits.clear()
                bau.render(tela, camera)
                continue

            if fila_blits:
                self._aplicar_blits_batch(tela, fila_blits)
                fila_blits.clear()
            if self._criaveis.renderizar_criavel(oid, tela, camera):
                continue

            if self._atores.renderizar(oid, tela, camera):
                continue

            self._render_fallback_objeto(tela, camera, obj, cor_fallback=(222, 233, 245), pos_tela=pos_tela, fila_blits=fila_blits)

        self._aplicar_blits_batch(tela, fila_blits)
        for oid in remover_pokemons:
            with self._lock_objetos:
                self.ObjetosPorId.pop(int(oid), None)
                self.PokemonsPorId.pop(int(oid), None)
                self._remover_indice_chunk_objeto(int(oid))
                self._invalidar_cache_objetos_visiveis_locked()

    def renderizar_estruturas(self, tela, camera):
        objs = self._estruturas_visiveis_ordenadas(camera, margem_chunks=1)
        tela_size = tela.get_size()
        preparados: List[tuple] = []
        for obj in objs:
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            eh_estadio = self._eh_payload_estadio(obj)
            if eh_estadio:
                rx = float(estado.get("raio_elipse_x", 24.0) or 24.0)
                ry = float(estado.get("raio_elipse_y", 24.0) or 24.0)
                margem_px = int(max(220.0, max(rx, ry) * float(getattr(camera, "TilePx", 50) or 50) * 1.35))
            else:
                margem_px = 220
            pos_tela = self._objeto_posicao_tela_se_visivel(obj, camera, margem_px=margem_px)
            if pos_tela is None:
                continue
            pos = obj.get("posicao") if isinstance(obj.get("posicao"), (list, tuple)) and len(obj.get("posicao")) == 2 else (0.0, 0.0)
            chave_ordem = (
                prioridade_estrutura_natural(codigo=obj.get("codigo_natural"), subtipo=estado.get("subtipo")),
                float(pos[1]),
                int(obj.get("id", 0) or 0),
            )
            preparados.append((chave_ordem, obj, pos_tela, eh_estadio))
        preparados.sort(key=lambda item: item[0])
        fila_blits: List[tuple] = []
        for _, obj, pos_tela, eh_estadio in preparados:
            if eh_estadio:
                if fila_blits:
                    self._aplicar_blits_batch(tela, fila_blits)
                    fila_blits.clear()
                GeradorEstadio.renderizar(tela, camera, obj)
                continue
            est = self.EstruturasPorId.get(int(obj.get("id", 0) or 0))
            escala = est.escala_render() if est is not None else 1.0
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            dungeon_aberta = self._eh_dungeon_aberta(obj)
            if not dungeon_aberta:
                self._render_fallback_objeto(tela, camera, obj, cor_fallback=(125, 86, 54), escala=escala, pos_tela=pos_tela, fila_blits=fila_blits, tela_size=tela_size)
            if dungeon_aberta:
                continue
        self._aplicar_blits_batch(tela, fila_blits)

    def renderizar_portais_dungeon(self, tela, camera):
        for obj in self._estruturas_visiveis_ordenadas(camera, margem_chunks=1):
            if not isinstance(obj, dict) or not self._eh_dungeon_aberta(obj):
                continue
            renderizar_entrada_dungeon_mundo(tela, camera, obj)

    def renderizar_estadio_interior(self, tela, camera):
        dim_local = self._dimensao_player_local()
        if dim_local == "Mundo":
            return
        player_payload = self.ObjetosPorId.get(int(self.id_player_local() or -1), {})
        estado_p = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        est_id = int(estado_p.get("estadio_atual_id", player_payload.get("estadio_atual_id", 0)) or 0)
        estadio_payload = self.EstadiosPorId.get(est_id, {})
        if not isinstance(estadio_payload, dict) or not estadio_payload:
            for candidato in self.EstadiosPorId.values():
                if not isinstance(candidato, dict):
                    continue
                estado_c = candidato.get("estado") if isinstance(candidato.get("estado"), dict) else {}
                if str(estado_c.get("dimensao_destino") or "EstadioNormal") == dim_local:
                    estadio_payload = candidato
                    break
        estado_est = estadio_payload.get("estado") if isinstance(estadio_payload.get("estado"), dict) else {}
        EstadioInterno.renderizar(tela, camera, estado_estadio=estado_est)

    def renderizar(self, tela, camera, ignorar_entidade_id=None):
        self.renderizar_entidades(tela, camera, ignorar_id=ignorar_entidade_id)
        self.renderizar_estruturas(tela, camera)
