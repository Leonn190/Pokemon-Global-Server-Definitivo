"""Controlador de player local para cena de mundo (movimento em tiles)."""

from __future__ import annotations

import math

import pygame
from Codigo.ModulosGerais.Sonoridades import tocar
from Codigo.ModulosMundo.MecanicasTiles import MecanicasTiles


class Controle:
    def __init__(self, ator, velocidade_tiles=None):
        self.Ator = ator
        base = getattr(self.Ator.Perfil, "VelocidadeBaseTiles", 5.0) if velocidade_tiles is None else velocidade_tiles
        self.VelocidadeTiles = float(base)
        self.LimitesMundoTiles = None
        self.LimitesToroidais = True
        self._grid_chunks = {}
        self._chunk_blocos = 10
        self._tempo_desde_ultima_corrida = 0.0
        self._bloqueio_por_exaustao = False
        self._tempo_shift_pressionado = 0.0
        self._bonus_corrida_atual = 0.0
        self._batendo = False
        self._soltar_apos_tapa_atual = False
        self._consumindo_stamina = False
        self._tentando_correr = False
        self.InventarioAberto = False
        self._tempo_respiracao = 0.0
        self._tempo_diff_angulo = 0
        self._ultimo_angulo_emitido = None
        self._mirando = False
        self._tempo_mira = 0.0
        self._item_arremesso_atual = None
        self._acao_arremesso_pendente = None
        self._acao_drop_item_mundo_pendente = None
        self._acao_evoluir_pokemon_pendente = None
        self._acao_interacao_pendente = None
        self.BloquearToggleInventario = False
        self._tile_atual_cache = None

    def atualizar(self, eventos, dt, mouse_pos_mundo_tiles, mouse_pos_tela_px=None, ator_pos_tela_px=None):
        dt = max(0.0, float(dt))
        self._processar_toggle_inventario(eventos)
        if self.InventarioAberto:
            self._tentando_correr = False
            tile_atual = self._tile_atual()
            MecanicasTiles.aplicar_no_ator(self.Ator, tile_atual)
            self._tile_atual_cache = tile_atual
            self._atualizar_stamina(dt, False, False, tile_atual)
            self._tempo_respiracao += dt
            self.Ator.atualizar(dt)
            self.Ator.atualizar_colisor_mao_mundo()
            return
        self._processar_scroll_inventario(eventos)
        self._processar_input_ataque(eventos, mouse_pos_mundo_tiles)
        self._processar_rotacao(mouse_pos_mundo_tiles, mouse_pos_tela_px=mouse_pos_tela_px, ator_pos_tela_px=ator_pos_tela_px)
        deslocando, correndo, tile_atual = self._processar_movimento(dt)
        self._tile_atual_cache = tile_atual
        self._atualizar_stamina(dt, deslocando, correndo, tile_atual)
        self._atualizar_tapa_automatico()
        self._tempo_respiracao += dt
        self._tempo_mira = self._tempo_mira + dt if self._mirando else 0.0
        self.Ator.atualizar(dt)
        self.Ator.atualizar_colisor_mao_mundo()

    def atualizar_bloqueado(self, dt):
        dt = max(0.0, float(dt))
        self._tentando_correr = False
        tile_atual = self._tile_atual()
        MecanicasTiles.aplicar_no_ator(self.Ator, tile_atual)
        self._tile_atual_cache = tile_atual
        self._atualizar_stamina(dt, False, False, tile_atual)
        self._tempo_respiracao += dt
        self._mirando = False
        self.Ator.atualizar(dt)
        self.Ator.atualizar_colisor_mao_mundo()

    def consumir_acao_arremesso(self):
        acao = self._acao_arremesso_pendente
        self._acao_arremesso_pendente = None
        return acao

    def consumir_acao_drop_item_mundo(self):
        acao = self._acao_drop_item_mundo_pendente
        self._acao_drop_item_mundo_pendente = None
        return acao

    def solicitar_evoluir_pokemon(self, chave_pokemon: str):
        chave = str(chave_pokemon or "").strip()
        if not chave:
            return
        self._acao_evoluir_pokemon_pendente = {"chave_pokemon": chave}

    def solicitar_subir_nivel_pokemon(self, chave_pokemon: str):
        self.solicitar_evoluir_pokemon(chave_pokemon)


    def registrar_acao_interacao(self, payload):
        self._acao_interacao_pendente = dict(payload or {})

    def consumir_acao_interacao(self):
        acao = self._acao_interacao_pendente
        self._acao_interacao_pendente = None
        return acao

    def consumir_acao_evoluir_pokemon(self):
        acao = self._acao_evoluir_pokemon_pendente
        self._acao_evoluir_pokemon_pendente = None
        return acao

    def consumir_acao_subir_nivel_pokemon(self):
        return self.consumir_acao_evoluir_pokemon()

    def _item_qualquer_na_mao(self):
        inv = getattr(self.Ator, "Inventario", None)
        item = inv.item_na_mao() if inv is not None else None
        if not isinstance(item, dict):
            return None
        return dict(item)

    def estado_mira(self, mouse_pos_mundo_tiles):
        if not self._mirando or self._item_arremesso_atual is None:
            return None
        max_alc = self._alcance_item(self._item_arremesso_atual)
        px, py = self._ponto_mao_mundo()
        mx, my = mouse_pos_mundo_tiles
        dx, dy = mx - px, my - py
        n = math.hypot(dx, dy)
        if n <= 1e-6:
            dx, dy, n = 1.0, 0.0, 1.0
        ux, uy = dx / n, dy / n
        fim = (px + ux * max_alc, py + uy * max_alc)
        return {"inicio": (px, py), "fim": fim, "item": dict(self._item_arremesso_atual)}

    def _lancamento_direto_mouse(self, mouse_pos_mundo_tiles):
        if self._item_arremesso_atual is None:
            return None
        px, py = self._ponto_mao_mundo()
        mx, my = mouse_pos_mundo_tiles
        dx, dy = mx - px, my - py
        n = math.hypot(dx, dy)
        if n <= 1e-6:
            dx, dy, n = 1.0, 0.0, 1.0
        ux, uy = dx / n, dy / n
        alc = self._alcance_item(self._item_arremesso_atual)
        return {"inicio": (px, py), "fim": (px + ux * alc, py + uy * alc), "item": dict(self._item_arremesso_atual)}

    def _ponto_mao_mundo(self):
        ang = math.radians(float(getattr(self.Ator, "AnguloOlhar", 0.0)))
        frente_x = math.cos(ang)
        frente_y = -math.sin(ang)
        lateral_x = -frente_y
        lateral_y = frente_x
        px, py = self.Ator.Posicao
        return (px + lateral_x * 0.28 + frente_x * 0.22, py + lateral_y * 0.28 + frente_y * 0.22)

    def _item_arremessavel_mao(self):
        inv = getattr(self.Ator, "Inventario", None)
        item = inv.item_na_mao() if inv is not None else None
        if not isinstance(item, dict):
            return None
        estilo = str(item.get("Estilo") or item.get("estilo") or "").strip().lower()
        if estilo in {"bola", "fruta"}:
            return dict(item)
        return None

    def _alcance_item(self, item_info):
        nome = str(item_info.get("Nome") or "").strip().lower()
        estilo = str(item_info.get("Estilo") or "").strip().lower()
        if estilo == "fruta":
            return 5.0
        if "sniperball" in nome:
            return 8.0
        return 6.0

    def _consumir_item_na_mao(self):
        inv = getattr(self.Ator, "Inventario", None)
        if inv is None:
            return False
        idx = inv.SlotSelecionado
        if idx < 0 or idx >= len(inv.Itens):
            return False
        item = inv.Itens[idx]
        if not isinstance(item, dict):
            inv.Itens[idx] = None
            return True
        qtd = int(item.get("quantidade", 1))
        if qtd <= 1:
            inv.Itens[idx] = None
        else:
            item["quantidade"] = qtd - 1
        return True

    def _processar_input_ataque(self, eventos, mouse_pos_mundo_tiles):
        self._item_arremesso_atual = self._item_arremessavel_mao()
        pode_arremessar = self._item_arremesso_atual is not None
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_q:
                item_mao = self._item_qualquer_na_mao()
                if item_mao is not None and self._consumir_item_na_mao():
                    item_drop = dict(item_mao)
                    item_drop["quantidade"] = 1
                    self._acao_drop_item_mundo_pendente = {
                        "item": item_drop,
                        "origem": self._ponto_mao_mundo(),
                    }
                    tocar("Dropar")

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 3:
                self._mirando = pode_arremessar
            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 3:
                self._mirando = False

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if pode_arremessar:
                    if self._consumir_item_na_mao():
                        estado = self.estado_mira(mouse_pos_mundo_tiles) if self._mirando else self._lancamento_direto_mouse(mouse_pos_mundo_tiles)
                        self._acao_arremesso_pendente = {
                            "item": dict(self._item_arremesso_atual),
                            "origem": estado["inicio"] if estado else self._ponto_mao_mundo(),
                            "destino": estado["fim"] if estado else mouse_pos_mundo_tiles,
                            "mirando": bool(self._mirando),
                        }
                    self._batendo = False
                    self._soltar_apos_tapa_atual = False
                else:
                    self._batendo = True
                    self._soltar_apos_tapa_atual = False
                    self._iniciar_tapa_com_som()

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self.Ator.esta_tapando():
                    self._soltar_apos_tapa_atual = True
                else:
                    self._batendo = False
                    self._soltar_apos_tapa_atual = False

        self.Ator.EstadoMiraAtiva = bool(self._mirando and pode_arremessar)

    def definir_grid_chunks(self, chunks, chunk_blocos=10):
        self._grid_chunks = dict(chunks) if isinstance(chunks, dict) else {}
        self._chunk_blocos = max(1, int(chunk_blocos))

    def definir_limites_mundo(self, largura_tiles, altura_tiles, toroidal=True):
        try:
            largura = max(1.0, float(largura_tiles))
            altura = max(1.0, float(altura_tiles))
        except (TypeError, ValueError):
            self.LimitesMundoTiles = None
            return
        self.LimitesMundoTiles = (largura, altura)
        self.LimitesToroidais = bool(toroidal)

    @staticmethod
    def _delta_toroidal(origem, destino, tamanho):
        delta = float(destino) - float(origem)
        if not tamanho or tamanho <= 0:
            return delta
        return delta - round(delta / tamanho) * tamanho

    def _aplicar_loop_mundo(self):
        if not self.LimitesMundoTiles:
            return
        largura, altura = self.LimitesMundoTiles
        px, py = self.Ator.Posicao
        if self.LimitesToroidais:
            self.Ator.definir_posicao(px % largura, py % altura)
            return
        margem = 1e-4
        self.Ator.definir_posicao(
            max(0.0, min(max(0.0, largura - margem), float(px))),
            max(0.0, min(max(0.0, altura - margem), float(py))),
        )

    def normalizar_posicao_mundo(self):
        self._aplicar_loop_mundo()

    def _tile_atual(self):
        x, y = self.Ator.Posicao
        bx = int(math.floor(x))
        by = int(math.floor(y))
        cx = bx // self._chunk_blocos
        cy = by // self._chunk_blocos
        chunk = self._grid_chunks.get((cx, cy))
        if chunk is None:
            return None
        lx = bx % self._chunk_blocos
        ly = by % self._chunk_blocos
        try:
            return int(chunk[ly][lx])
        except (IndexError, TypeError, ValueError):
            return None

    def _bonus_velocidade_alvo(self):
        minimo = float(getattr(self.Ator.Perfil, "BonusVelocidadeCorridaMin", 0.30))
        maximo = float(getattr(self.Ator.Perfil, "BonusVelocidadeCorridaMax", 0.60))
        tempo_max = float(getattr(self.Ator.Perfil, "TempoAceleracaoCorrida", 3.0))
        if tempo_max <= 0.0:
            return maximo
        passo = min(1.0, self._tempo_shift_pressionado / tempo_max)
        return minimo + (maximo - minimo) * passo

    def _processar_movimento(self, dt):
        teclas = pygame.key.get_pressed()
        eixo_x = (1.0 if teclas[pygame.K_d] else 0.0) - (1.0 if teclas[pygame.K_a] else 0.0)
        eixo_y = (1.0 if teclas[pygame.K_s] else 0.0) - (1.0 if teclas[pygame.K_w] else 0.0)
        mag = math.hypot(eixo_x, eixo_y)
        if mag > 0:
            eixo_x /= mag
            eixo_y /= mag

        deslocando = mag > 0
        tile_atual = self._tile_atual()
        MecanicasTiles.aplicar_no_ator(self.Ator, tile_atual)
        shift = teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]
        self._tentando_correr = bool(shift)
        if self._bloqueio_por_exaustao and self.Ator.Perfil.Stamina >= (self.Ator.Perfil.StaminaMax - 0.001):
            self._bloqueio_por_exaustao = False
        correndo = deslocando and shift and (not self._bloqueio_por_exaustao) and self.Ator.Perfil.Stamina > 0.0

        if correndo:
            self._tempo_shift_pressionado += dt
            self._bonus_corrida_atual = self._bonus_velocidade_alvo()
        else:
            self._tempo_shift_pressionado = 0.0
            tempo_desacel = float(getattr(self.Ator.Perfil, "TempoDesaceleracaoCorrida", 3.0))
            if tempo_desacel <= 0.0:
                self._bonus_corrida_atual = 0.0
            else:
                self._bonus_corrida_atual = max(
                    0.0,
                    self._bonus_corrida_atual - (dt / tempo_desacel) * float(getattr(self.Ator.Perfil, "BonusVelocidadeCorridaMax", 0.60)),
                )

        mult = (1.0 + max(0.0, self._bonus_corrida_atual)) * MecanicasTiles.multiplicador_velocidade(tile_atual)
        vbase = float(getattr(self.Ator.Perfil, "VelocidadeBaseTiles", self.VelocidadeTiles))
        antes = self.Ator.Posicao
        self.Ator.mover(eixo_x * vbase * mult * dt, eixo_y * vbase * mult * dt)
        self._aplicar_loop_mundo()
        return self.Ator.Posicao != antes, correndo, tile_atual

    def _atualizar_stamina(self, dt, deslocando, correndo, tile_atual):
        custo = 0.0
        max_bonus = float(getattr(self.Ator.Perfil, "BonusVelocidadeCorridaMax", 0.60))
        if correndo:
            custo += float(getattr(self.Ator.Perfil, "CustoStaminaCorridaMax" if self._bonus_corrida_atual >= (max_bonus - 0.01) else "CustoStaminaCorrida", 10.0))
        if tile_atual == 0:
            custo += float(getattr(self.Ator.Perfil, "CustoStaminaAguaFunda", 16.0))
        elif tile_atual == 1:
            custo += float(getattr(self.Ator.Perfil, "CustoStaminaAguaRasa", 4.0))

        if custo > 0.0:
            self.Ator.Perfil.consumir_stamina(custo * dt)
            self._tempo_desde_ultima_corrida = 0.0
            self._consumindo_stamina = True
            if self.Ator.Perfil.Stamina <= 0.001:
                self._bloqueio_por_exaustao = True
        else:
            self._consumindo_stamina = False
            self._tempo_desde_ultima_corrida += dt
            if self._tempo_desde_ultima_corrida >= float(getattr(self.Ator.Perfil, "AtrasoRegeneracaoStamina", 2.0)):
                regen = float(getattr(self.Ator.Perfil, "RegeneracaoStaminaAndando" if deslocando else "RegeneracaoStaminaParado", 12.0))
                self.Ator.Perfil.regenerar_stamina(regen * dt)

    def _processar_rotacao(self, mouse_pos_mundo_tiles, mouse_pos_tela_px=None, ator_pos_tela_px=None):
        self._tempo_diff_angulo += 1
        if mouse_pos_tela_px is not None and ator_pos_tela_px is not None:
            mx, my = float(mouse_pos_tela_px[0]), float(mouse_pos_tela_px[1])
            px, py = float(ator_pos_tela_px[0]), float(ator_pos_tela_px[1])
            dx, dy = (mx - px), (my - py)
        else:
            px, py = self.Ator.Posicao
            mx, my = mouse_pos_mundo_tiles
            if self.LimitesMundoTiles and self.LimitesToroidais:
                dx, dy = (self._delta_toroidal(px, mx, self.LimitesMundoTiles[0]), self._delta_toroidal(py, my, self.LimitesMundoTiles[1]))
            else:
                dx, dy = (mx - px, my - py)
        if dx == 0 and dy == 0:
            return
        angulo = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
        self.Ator.definir_angulo_olhar(angulo)
        if self._tempo_diff_angulo < 3:
            return
        self._tempo_diff_angulo = 0
        if self._ultimo_angulo_emitido is not None:
            delta = abs(((angulo - self._ultimo_angulo_emitido + 180.0) % 360.0) - 180.0)
            if delta < 0.5:
                return
        self._ultimo_angulo_emitido = angulo

    def _atualizar_tapa_automatico(self):
        if self._batendo and not self.Ator.esta_tapando():
            if self._soltar_apos_tapa_atual:
                self._batendo = False
                self._soltar_apos_tapa_atual = False
                return
            self._iniciar_tapa_com_som()

    def _iniciar_tapa_com_som(self):
        if self.Ator.esta_tapando():
            return
        self.Ator.iniciar_tapa()
        if not self.Ator.esta_tapando():
            return
        item_mao = self._item_qualquer_na_mao()
        estilo_item = str((item_mao or {}).get("Estilo") or (item_mao or {}).get("estilo") or "").strip().lower()
        if estilo_item == "ferramenta":
            tocar("BaterFerramenta")

    def _processar_scroll_inventario(self, eventos):
        for evento in eventos:
            if evento.type == pygame.MOUSEWHEEL:
                self.Ator.Inventario.mudar_slot_por_scroll(-evento.y)

    def _processar_toggle_inventario(self, eventos):
        if self.BloquearToggleInventario:
            return
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_e:
                self.InventarioAberto = not self.InventarioAberto
                break
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_f:
                self.registrar_acao_interacao({"tecla": "F"})

    def tile_atual_cache(self):
        return self._tile_atual_cache

    def esta_em_agua_funda(self) -> bool:
        return int(self._tile_atual_cache) == 0 if self._tile_atual_cache is not None else False

    def esta_em_agua_rasa(self) -> bool:
        return int(self._tile_atual_cache) == 1 if self._tile_atual_cache is not None else False

PlayerController = Controle
