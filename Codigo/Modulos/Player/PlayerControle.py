"""Controlador de player local para cena de mundo (movimento em tiles)."""

from __future__ import annotations

import math

import pygame

from Codigo.Prefabs.Barra import Barra


class PlayerController:
    def __init__(self, ator, perfil, inventario, velocidade_tiles=4.8):
        self.Ator = ator
        self.Perfil = perfil
        self.Inventario = inventario
        self.VelocidadeTiles = float(velocidade_tiles)
        self.LimitesMundoTiles = None
        self._grid_chunks = {}
        self._chunk_blocos = 32
        self._tempo_desde_ultima_corrida = 0.0
        self._bloqueio_por_exaustao = False
        self._tempo_shift_pressionado = 0.0
        self._bonus_corrida_atual = 0.0
        self._batendo = False
        self._soltar_apos_tapa_atual = False
        self._consumindo_stamina = False
        self._stamina_alpha = 0.0
        self.InventarioAberto = False
        self._tempo_respiracao = 0.0
        self._tempo_diff_angulo = 0
        self._ultimo_angulo_emitido = None

        self.BarraStamina = Barra(pygame.Rect(0, 0, 80, 10), valor=100, minimo=0, maximo=100, mostrar_rotulo=False, suavizacao=20.0)
        self.BarraStamina.cor_fundo = (16, 22, 30)
        self.BarraStamina.cor_borda = (180, 210, 255)
        self.BarraStamina.cor_preenchimento = (86, 220, 125)

    def atualizar(self, eventos, dt, mouse_pos_mundo_tiles):
        dt = max(0.0, float(dt))
        self._processar_toggle_inventario(eventos)
        if self.InventarioAberto:
            return
        self._processar_scroll_inventario(eventos)
        self._processar_input_tapa(eventos)
        self._processar_rotacao(mouse_pos_mundo_tiles)
        deslocando, correndo, tile_atual = self._processar_movimento(dt)
        self._atualizar_stamina(dt, deslocando, correndo, tile_atual)
        self._atualizar_tapa_automatico()
        self._tempo_respiracao += dt
        self.Ator.atualizar(dt)
        self.Ator.atualizar_colisor_mao_mundo()

    def renderizar_stamina(self, tela, camera, dt):
        dt = max(0.0, float(dt))
        self.BarraStamina.maximo = max(1.0, float(self.Perfil.StaminaMax))
        self.BarraStamina.set_valor(float(self.Perfil.Stamina))
        self.BarraStamina.atualizar(dt)

        cheio = self.Perfil.Stamina >= (self.Perfil.StaminaMax - 0.001)
        tentando_correr = pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]
        alvo_alpha = 255.0 if (self._consumindo_stamina or not cheio or tentando_correr) else 0.0
        velocidade = 10.0 if alvo_alpha > self._stamina_alpha else 6.0
        self._stamina_alpha += (alvo_alpha - self._stamina_alpha) * min(1.0, dt * velocidade)

        if self._stamina_alpha <= 1.0:
            return

        px, py = camera.mundo_para_tela_px(self.Ator.Posicao)
        self.BarraStamina.rect.midbottom = (int(px), int(py - 42))
        bar_surf = pygame.Surface(self.BarraStamina.rect.size, pygame.SRCALPHA)
        rect_original = self.BarraStamina.rect.copy()
        self.BarraStamina.rect.topleft = (0, 0)
        self.BarraStamina._desenhar_barra(bar_surf)
        self.BarraStamina.rect = rect_original
        bar_surf.set_alpha(int(self._stamina_alpha))
        tela.blit(bar_surf, self.BarraStamina.rect.topleft)

    def definir_grid_chunks(self, chunks, chunk_blocos=32):
        self._grid_chunks = dict(chunks) if isinstance(chunks, dict) else {}
        self._chunk_blocos = max(1, int(chunk_blocos))

    def definir_limites_mundo(self, largura_tiles, altura_tiles):
        try:
            largura = max(1.0, float(largura_tiles))
            altura = max(1.0, float(altura_tiles))
        except (TypeError, ValueError):
            self.LimitesMundoTiles = None
            return
        self.LimitesMundoTiles = (largura, altura)

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
        self.Ator.definir_posicao(px % largura, py % altura)

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
        minimo = float(getattr(self.Perfil, "BonusVelocidadeCorridaMin", 0.30))
        maximo = float(getattr(self.Perfil, "BonusVelocidadeCorridaMax", 0.60))
        tempo_max = max(0.01, float(getattr(self.Perfil, "TempoAceleracaoCorrida", 3.0)))
        passo = min(1.0, self._tempo_shift_pressionado / tempo_max)
        return minimo + (maximo - minimo) * passo

    def _processar_movimento(self, dt):
        teclas = pygame.key.get_pressed()
        eixo_x = 0.0
        eixo_y = 0.0

        if teclas[pygame.K_a]:
            eixo_x -= 1.0
        if teclas[pygame.K_d]:
            eixo_x += 1.0
        if teclas[pygame.K_w]:
            eixo_y -= 1.0
        if teclas[pygame.K_s]:
            eixo_y += 1.0

        mag = math.hypot(eixo_x, eixo_y)
        if mag > 0:
            eixo_x /= mag
            eixo_y /= mag

        deslocando = mag > 0
        tile_atual = self._tile_atual()
        shift = teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]

        if self._bloqueio_por_exaustao and self.Perfil.Stamina >= (self.Perfil.StaminaMax - 0.001):
            self._bloqueio_por_exaustao = False

        pode_correr = not self._bloqueio_por_exaustao and self.Perfil.Stamina > 0.0
        correndo = deslocando and shift and pode_correr

        if correndo:
            self._tempo_shift_pressionado += dt
            self._bonus_corrida_atual = self._bonus_velocidade_alvo()
        else:
            self._tempo_shift_pressionado = 0.0
            tempo_desacel = max(0.01, float(getattr(self.Perfil, "TempoDesaceleracaoCorrida", 3.0)))
            self._bonus_corrida_atual = max(0.0, self._bonus_corrida_atual - (dt / tempo_desacel) * float(getattr(self.Perfil, "BonusVelocidadeCorridaMax", 0.60)))

        mult = 1.0 + max(0.0, self._bonus_corrida_atual)
        velocidade_base = float(getattr(self.Perfil, "VelocidadeBaseTiles", self.VelocidadeTiles))

        antes = self.Ator.Posicao
        self.Ator.mover(eixo_x * velocidade_base * mult * dt, eixo_y * velocidade_base * mult * dt)
        self._aplicar_loop_mundo()
        return self.Ator.Posicao != antes, correndo, tile_atual

    def _atualizar_stamina(self, dt, deslocando, correndo, tile_atual):
        custo = 0.0
        max_bonus = float(getattr(self.Perfil, "BonusVelocidadeCorridaMax", 0.60))
        correndo_no_max = correndo and self._bonus_corrida_atual >= (max_bonus - 0.01)

        if correndo:
            if correndo_no_max:
                custo += float(getattr(self.Perfil, "CustoStaminaCorridaMax", 15.0))
            else:
                custo += float(getattr(self.Perfil, "CustoStaminaCorrida", 10.0))

        if deslocando:
            if tile_atual == 0:
                custo += float(getattr(self.Perfil, "CustoStaminaAguaFunda", 16.0))
            elif tile_atual == 2:
                custo += float(getattr(self.Perfil, "CustoStaminaAguaRasa", 4.0))

        if tile_atual == 2 and not correndo:
            custo = 0.0

        if custo > 0.0:
            self.Perfil.consumir_stamina(custo * dt)
            self._tempo_desde_ultima_corrida = 0.0
            self._consumindo_stamina = True
            if self.Perfil.Stamina <= 0.001:
                self._bloqueio_por_exaustao = True
        else:
            self._consumindo_stamina = False
            self._tempo_desde_ultima_corrida += dt
            if self._tempo_desde_ultima_corrida >= float(getattr(self.Perfil, "AtrasoRegeneracaoStamina", 2.0)):
                if deslocando:
                    regen = float(getattr(self.Perfil, "RegeneracaoStaminaAndando", 6.0))
                else:
                    regen = float(getattr(self.Perfil, "RegeneracaoStaminaParado", 12.0))
                self.Perfil.regenerar_stamina(regen * dt)

    def _processar_rotacao(self, mouse_pos_mundo_tiles):
        self._tempo_diff_angulo += 1
        px, py = self.Ator.Posicao
        mx, my = mouse_pos_mundo_tiles

        if self.LimitesMundoTiles:
            largura, altura = self.LimitesMundoTiles
            dx = self._delta_toroidal(px, mx, largura)
            dy = self._delta_toroidal(py, my, altura)
        else:
            dx = mx - px
            dy = my - py

        if dx == 0 and dy == 0:
            return
        angulo = math.degrees(math.atan2(-dy, dx))
        self.Ator.definir_angulo_olhar(angulo)
        if self._tempo_diff_angulo < 3:
            return
        self._tempo_diff_angulo = 0
        if self._ultimo_angulo_emitido is not None and abs(angulo - self._ultimo_angulo_emitido) < 0.5:
            return
        self._ultimo_angulo_emitido = angulo

    def _atualizar_tapa_automatico(self):
        if self._batendo and not self.Ator.esta_tapando():
            if self._soltar_apos_tapa_atual:
                self._batendo = False
                self._soltar_apos_tapa_atual = False
                return
            self.Ator.iniciar_tapa()

    def _processar_scroll_inventario(self, eventos):
        for evento in eventos:
            if evento.type == pygame.MOUSEWHEEL:
                self.Inventario.mudar_slot_por_scroll(-evento.y)

    def _processar_input_tapa(self, eventos):
        sem_item_na_mao = self.Inventario.item_na_mao() is None
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and sem_item_na_mao:
                self._batendo = True
                self._soltar_apos_tapa_atual = False
                if not self.Ator.esta_tapando():
                    self.Ator.iniciar_tapa()

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self.Ator.esta_tapando():
                    self._soltar_apos_tapa_atual = True
                else:
                    self._batendo = False
                    self._soltar_apos_tapa_atual = False

    def _processar_toggle_inventario(self, eventos):
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_e:
                self.InventarioAberto = not self.InventarioAberto
                break
