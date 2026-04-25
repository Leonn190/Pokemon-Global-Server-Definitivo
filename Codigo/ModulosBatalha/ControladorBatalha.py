from __future__ import annotations

import pygame

from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from Codigo.ModulosBatalha.PlayerBatalha import PlayerBatalha
from Codigo.ModulosBatalha.PokemonBatalha import PokemonBatalha
from Codigo.ModulosGerais.Camera import CameraBatalha


class ControladorBatalha:
    def __init__(self, camera=None):
        self.camera = camera
        self.arena = None
        self.pokemons = []
        self.pokemons_por_id = {}
        self.player_batalha = None
        self.hud = None

        self.rodada_atual = 1
        self.lado_jogador = 50
        self.modo_teste = False
        self.pokemon_selecionado = None
        self.area_selecionada = None
        self.ataque_selecionado = None
        self.logs_locais = []
        self.estado_batalha = "inicializando"

        self.timer_rodada = 1.0
        self.timer_rodada_max = 45.0
        self._area_hover = None
        self._ultimos_eventos = []
        self._ultimo_dt = 0.0
        self._intervalo_frame_ms = 85
        self._fuga_alpha = 0.0
        self._fuga_incremento_clique = 56.0
        self._fuga_clarear_por_segundo = 34.0
        self._fuga_limite_saida = 210.0
        self.solicitou_encerrar_batalha = False

    def iniciar(self, estado_inicial):
        estado = dict(estado_inicial or {})
        self.rodada_atual = int(estado.get("rodada_atual", 1) or 1)
        self.lado_jogador = int(estado.get("lado_jogador", 50) or 50)

        contexto_arena = dict(estado.get("arena") or {})
        self.arena = Arena(contexto_arena)

        if self.camera is None:
            self.camera = CameraBatalha((1920, 1080), posicao_inicial_tiles=(0, 0), tile_px=40)
        self.camera.definir_limites_mundo(self.arena.Largura, self.arena.Altura, toroidal=False)

        self.pokemons = [PokemonBatalha.from_serializado(item) for item in list(estado.get("pokemons") or [])]
        regras = estado.get("regras") if isinstance(estado.get("regras"), dict) else {}
        animacao = regras.get("animacao") if isinstance(regras.get("animacao"), dict) else {}
        intervalo_ms = animacao.get("intervalo_frame_ms", 85)
        try:
            self._intervalo_frame_ms = max(1, int(float(intervalo_ms)))
        except (TypeError, ValueError):
            self._intervalo_frame_ms = 85
        for pokemon in self.pokemons:
            pokemon.definir_intervalo_frame_ms(self._intervalo_frame_ms)
            pokemon.Nivel = max(1, int(getattr(pokemon, "Nivel", 1) or 1))
            pokemon.VidaAtual = max(0.0, min(float(pokemon.VidaMax), float(pokemon.VidaMax)))
        self.pokemons_por_id = {p.id_batalha: p for p in self.pokemons}
        self.arena.atualizar_ocupacao(self.pokemons)

        self.criar_componentes()
        self.timer_rodada = self.timer_rodada_max
        self.estado_batalha = "montando_jogada"

    def criar_componentes(self):
        self.player_batalha = PlayerBatalha(self)
        self.hud = ElementosHudBatalha(self)

    def atualizar(self, dt, eventos):
        if self.arena is None or self.camera is None:
            return
        self._ultimos_eventos = list(eventos or [])
        self._ultimo_dt = float(dt or 0.0)
        self.camera.processar_eventos(eventos)
        self.camera.atualizar(dt)

        self.timer_rodada = max(0.0, self.timer_rodada - float(dt))
        self.arena.atualizar_ocupacao(self.pokemons)
        self.arena.atualizar_layout_batalha(self.camera)
        self.arena.atualizar_slots_reserva(self.pokemons, self.camera)
        for pokemon in self.pokemons:
            pokemon.atualizar_animacao(dt)

        self._area_hover = self.arena.area_em_posicao_mouse(pygame.mouse.get_pos(), self.camera)
        self.player_batalha.processar_eventos(eventos)
        self.hud.atualizar(dt, eventos)
        self._atualizar_fuga(dt)

    def desenhar(self, surface):
        if self.arena is None:
            return
        self.arena.renderizar(surface, self.camera)
        self.arena.desenhar_areas(surface, self.camera, area_hover=self._area_hover, area_selecionada=self.area_selecionada)

        for pokemon in self.pokemons:
            if pokemon.esta_ativo() and not pokemon.esta_na_reserva():
                hover = pokemon.contem_ponto(pygame.mouse.get_pos())
                pokemon.desenhar(surface, self.camera, self.arena, selecionado=(self.area_selecionada == pokemon.AreaId), hover=hover)

        for lado in ("jogador", "inimigo"):
            for slot in self.arena.obter_slots_reserva(lado):
                poke = self.pokemons_por_id.get(slot.get("pokemon_id"))
                if poke is None:
                    continue
                rect = slot.get("rect_tela")
                hover = rect.collidepoint(pygame.mouse.get_pos()) if rect else False
                selecionado = self.area_selecionada == slot.get("id_slot")
                if rect:
                    borda = (255, 235, 90) if selecionado else (204, 212, 228, 170) if hover else (150, 158, 175, 130)
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(overlay, borda, overlay.get_rect(), 2)
                    surface.blit(overlay, rect.topleft)
                poke.desenhar_reserva(surface, rect, selecionado=selecionado, hover=hover)

        self.hud.desenhar(surface, self._ultimos_eventos, self._ultimo_dt)
        alpha = max(0, min(255, int(round(self._fuga_alpha))))
        if alpha > 0:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            surface.blit(overlay, (0, 0))

    def selecionar_pokemon(self, pokemon):
        self.pokemon_selecionado = pokemon
        if pokemon is None:
            self.area_selecionada = None
        elif bool(getattr(pokemon, "EmReserva", False)):
            self.area_selecionada = getattr(pokemon, "id_batalha", None)
        else:
            self.area_selecionada = getattr(pokemon, "AreaId", None)
        if self.hud:
            self.hud.ficha.definir_controle_inimigo(self.modo_teste)
            if pokemon is None or (pokemon.Lado == "inimigo" and not self.modo_teste):
                self.limpar_ataque()

    def desselecionar_pokemon(self):
        self.pokemon_selecionado = None
        self.area_selecionada = None
        self.limpar_ataque()

    def selecionar_area(self, area_id):
        self.area_selecionada = area_id
        if area_id is None:
            self.pokemon_selecionado = None
            self.limpar_ataque()
            return
        self.pokemon_selecionado = self.arena.pokemon_na_area(area_id)

    def selecionar_ataque(self, ataque):
        self.ataque_selecionado = ataque

    def limpar_ataque(self):
        self.ataque_selecionado = None
        if self.hud:
            self.hud.ficha.limpar_ataque_selecionado()

    def passar_rodada_local(self):
        self.estado_batalha = "passando_rodada"
        self.rodada_atual += 1
        self.limpar_ataque()
        self.timer_rodada = self.timer_rodada_max
        self.logs_locais.append({"rodada": self.rodada_atual, "texto": f"Rodada {self.rodada_atual} iniciada."})
        self.estado_batalha = "montando_jogada"

    def iniciar_fuga(self):
        self._fuga_alpha = min(255.0, self._fuga_alpha + self._fuga_incremento_clique)
        self.estado_batalha = "fugindo"
        if self._fuga_alpha >= self._fuga_limite_saida:
            self.solicitou_encerrar_batalha = True

    def _atualizar_fuga(self, dt: float):
        dt = max(0.0, float(dt or 0.0))
        if self._fuga_alpha > 0.0:
            self._fuga_alpha = max(0.0, self._fuga_alpha - self._fuga_clarear_por_segundo * dt)

    def definir_modo_teste(self, ativo: bool):
        self.modo_teste = bool(ativo)
        if self.hud:
            self.hud.ficha.definir_controle_inimigo(self.modo_teste)
        if self.pokemon_selecionado is not None and self.pokemon_selecionado.Lado == "inimigo" and not self.modo_teste:
            self.limpar_ataque()
            if self.pokemon_selecionado.esta_ativo():
                self.selecionar_area(getattr(self.pokemon_selecionado, "AreaId", None))
        return self.modo_teste

    def alternar_modo_teste(self):
        return self.definir_modo_teste(not self.modo_teste)

    def estado_visualizador_logs(self):
        return {
            "ultimo_turno_com_log": max(1, self.rodada_atual),
            "replay": {"ativo": False},
        }

    def obter_log_publico(self, rodada):
        alvo = int(rodada or 1)
        historico = []
        for idx, item in enumerate(self.logs_locais):
            if int(item.get("rodada", 0) or 0) != alvo:
                continue
            historico.append(
                {
                    "tick": idx,
                    "fase": "inicializacao",
                    "evento": {
                        "tipo": "acao",
                        "texto": str(item.get("texto") or ""),
                    },
                }
            )
        return {"historico": historico}
