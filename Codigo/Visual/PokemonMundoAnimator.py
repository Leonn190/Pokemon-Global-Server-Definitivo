from __future__ import annotations

import math

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario


class PokemonMundoAnimator:
    def __init__(self, pokemon) -> None:
        self.pokemon = pokemon

    def _desenhar_pokemon_normal(self, tela, centro, raio_corpo, escala_extra: float = 1.0, alpha: int = 255):
        p = self.pokemon
        raio = max(2, int(raio_corpo * max(0.05, float(escala_extra))))
        frames = p._obter_frames_escalados(p.Especie, max(12, int(raio * 1.8)))
        if frames and raio > 2:
            frame = frames[int((pygame.time.get_ticks() / p._INTERVALO_FRAME_ANIM_MS) % len(frames))].copy()
            if alpha < 255:
                frame.set_alpha(alpha)
            tela.blit(frame, frame.get_rect(center=centro))
        else:
            surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(surf, (70, 155, 245, alpha), (surf.get_width() // 2, surf.get_height() // 2), raio)
            pygame.draw.circle(surf, (24, 84, 190, alpha), (surf.get_width() // 2, surf.get_height() // 2), raio, 2)
            tela.blit(surf, surf.get_rect(center=centro))

    def _desenhar_circulo_base(self, tela, centro, raio_base):
        estado_visual = getattr(self.pokemon, "EstadoVisual", None)
        if estado_visual is not None:
            return estado_visual.desenhar_circulo_base(tela, centro, raio_base)
        return max(3, int(raio_base))

    def _surface_bola_captura(self, tile_px: int):
        p = self.pokemon
        nome_bola = str(p.CapturaEstado.get("bola_nome") or "pokeball")
        item = {"Nome": nome_bola, "Code": ""}
        return ItemInventario.surface_item(item, lado_px=max(12, int(tile_px * 0.45)))

    def _desenhar_bola(self, tela, centro, tile_px: int, rotacao: float = 0.0, escala: float = 1.0, alpha: int = 255):
        p = self.pokemon
        base = self._surface_bola_captura(tile_px)
        if base is None:
            pygame.draw.circle(tela, (255, 180, 90), (int(centro[0]), int(centro[1])), max(3, int(tile_px * 0.16)))
            return
        sprite = base
        if abs(escala - 1.0) > 1e-3:
            w, h = base.get_size()
            sprite = pygame.transform.smoothscale(base, (max(1, int(w * escala)), max(1, int(h * escala))))
        ang_i = int(rotacao) % 360
        chave = (id(sprite), ang_i)
        rot = p._cache_rotacao_bola.get(chave)
        if rot is None:
            rot = pygame.transform.rotate(sprite, rotacao)
            p._cache_rotacao_bola[chave] = rot
            if len(p._cache_rotacao_bola) > 720:
                p._cache_rotacao_bola.clear()
        if alpha < 255:
            rot = rot.copy()
            rot.set_alpha(alpha)
        tela.blit(rot, rot.get_rect(center=(int(centro[0]), int(centro[1]))))

    def _desenhar_animacao_captura(self, tela, camera, centro, tile_px):
        p = self.pokemon
        t = min(1.0, max(0.0, p._tempo_fase_ms() / max(1.0, float(p.TempoAnimCapturaMs))))
        base = max(6, int(tile_px * p._raio_colisao_padrao))
        aura_r = max(base + 4, int(base * (1.1 + 0.55 * t)))
        aura = pygame.Surface((aura_r * 3, aura_r * 3), pygame.SRCALPHA)
        c = (150, 220, 255, int(120 * (1.0 - t * 0.35)))
        pygame.draw.circle(aura, c, (aura.get_width() // 2, aura.get_height() // 2), aura_r, max(2, int(base * 0.09)))
        tela.blit(aura, aura.get_rect(center=centro))
        for i in range(3):
            ang = (t * math.pi * 2.2) + (i * math.pi * 2.0 / 3.0)
            ox = int(math.cos(ang) * base * (0.5 + 0.2 * (1.0 - t)))
            oy = int(math.sin(ang) * base * (0.35 + 0.2 * (1.0 - t)))
            pygame.draw.circle(tela, (180, 235, 255), (centro[0] + ox, centro[1] + oy), max(2, int(base * 0.10)))
        poke_scale = max(0.0, 1.0 - (t ** 1.35))
        poke_y = int(centro[1] - tile_px * 0.12 * t)
        if poke_scale > 0.02:
            self._desenhar_pokemon_normal(tela, (centro[0], poke_y), max(2, int(base * 2.1)), escala_extra=poke_scale, alpha=max(20, int(255 * (1.0 - t * 0.55))))
        bola_y = int(centro[1] - tile_px * 0.24 * (1.0 - t) * (1.0 - t))
        bola_rot = -280.0 * (1.0 - t)
        bola_squash = 1.0 + 0.12 * math.sin(t * math.pi)
        self._desenhar_bola(tela, (centro[0], bola_y), tile_px, rotacao=bola_rot, escala=bola_squash)

    def _desenhar_animacao_checagem(self, tela, camera, centro, tile_px):
        p = self.pokemon
        base = max(6, int(tile_px * p._raio_colisao_padrao))
        indice = max(0, int(p.CapturaEstado.get("indice_checagem", 0) or 0))
        t = min(1.0, max(0.0, p._tempo_fase_ms() / max(1.0, float(p.TempoAnimChecagemMs))))
        amplitudes = [13.0, 9.0, 6.0]
        rotacoes = [18.0, 12.0, 7.0]
        amp = amplitudes[min(indice, len(amplitudes) - 1)]
        rot = rotacoes[min(indice, len(rotacoes) - 1)]
        onda = math.sin(t * math.pi)
        dx = int(math.sin(t * math.pi * 2.0) * amp * onda)
        ang = math.sin(t * math.pi * 2.0) * rot * onda
        sombra = pygame.Rect(0, 0, int(base * 1.8), max(4, int(base * 0.45)))
        sombra.center = (centro[0], centro[1] + int(base * 0.72))
        pygame.draw.ellipse(tela, (0, 0, 0, 90), sombra)
        self._desenhar_bola(tela, (centro[0] + dx, centro[1]), tile_px, rotacao=ang)

    def _desenhar_animacao_fuga(self, tela, centro, base):
        p = self.pokemon
        t = min(1.0, max(0.0, p._tempo_fase_ms() / max(1.0, float(p.TempoAnimFugaMs))))
        base_visual = max(6, int(base * 2))
        corpo_visual = max(3, int(base_visual * 1.05))
        self._desenhar_circulo_base(tela, centro, base_visual)
        for i in range(5):
            ang = (i / 5.0) * math.pi * 2.0 + (t * 2.4)
            ox = int(math.cos(ang) * base_visual * (0.45 + t * 0.85))
            oy = int(math.sin(ang) * base_visual * (0.25 + t * 0.65))
            pygame.draw.circle(tela, (255, 225, 170), (centro[0] + ox, centro[1] + oy), max(2, int(base_visual * 0.08)))
        escala = min(1.0, 0.18 + (t ** 0.65) * 0.92)
        alpha = max(50, int(255 * min(1.0, 0.4 + t * 0.9)))
        self._desenhar_pokemon_normal(tela, centro, corpo_visual, escala_extra=escala, alpha=alpha)

    def _desenhar_animacao_volta(self, tela, camera, tile_px):
        p = self.pokemon
        ini = p.CapturaEstado.get("retorno_inicio") if isinstance(p.CapturaEstado.get("retorno_inicio"), (list, tuple)) else list(p._posicao_bola_mundo())
        fim = p.CapturaEstado.get("retorno_destino") if isinstance(p.CapturaEstado.get("retorno_destino"), (list, tuple)) else ini
        t = min(1.0, max(0.0, p._tempo_fase_ms() / max(1.0, float(p.TempoAnimVoltaMs))))
        ini_t = camera.mundo_para_tela_px((float(ini[0]), float(ini[1])))
        fim_t = camera.mundo_para_tela_px((float(fim[0]), float(fim[1])))
        bx = ini_t[0] + (fim_t[0] - ini_t[0]) * t
        by = ini_t[1] + (fim_t[1] - ini_t[1]) * t - math.sin(t * math.pi) * max(18.0, tile_px * 0.55)
        rot = -540.0 * t
        self._desenhar_bola(tela, (int(bx), int(by)), tile_px, rotacao=rot)

    def atualizar_visual(self, dt: float) -> None:
        self.pokemon.atualizar(dt)

    def render(self, tela, camera, dt: float = 0.0) -> None:
        p = self.pokemon
        if p._pronto_para_remover:
            return
        cx, cy = camera.mundo_para_tela_px(p.Posicao)
        centro = (int(cx), int(cy))
        tile_px = int(getattr(camera, "TilePx", 50))
        base = max(6, int(tile_px * max(float(getattr(p.Colisor, "raio_colisao", 0.0) or 0.0), p._raio_colisao_padrao)))
        fase = p._fase()
        em_pendente = p.em_captura_pendente()

        if fase == "captura":
            self._desenhar_animacao_captura(tela, camera, centro, tile_px)
        elif fase == "checagem":
            self._desenhar_animacao_checagem(tela, camera, centro, tile_px)
        elif fase == "fuga":
            self._desenhar_animacao_fuga(tela, centro, base)
        elif fase == "volta":
            self._desenhar_animacao_volta(tela, camera, tile_px)
        else:
            self._desenhar_circulo_base(tela, centro, int(base * 2))
            self._desenhar_pokemon_normal(tela, centro, max(2, int(base * 2.0)))
            if p.AlvoLocalCaptura and not em_pendente:
                p.EstadoVisual.desenhar_barra_critica(tela, centro, int(base * 2.35))
