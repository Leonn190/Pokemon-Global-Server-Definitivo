from __future__ import annotations

import math

import pygame

from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from Codigo.ModulosBatalha.MontadorJogadas import MontadorJogadas
from Codigo.ModulosBatalha.PlayerBatalha import PlayerBatalha
from Codigo.ModulosBatalha.PokemonBatalha import PokemonBatalha
from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.Server import ServerBatalha


class ControladorBatalha:
    def __init__(self, camera=None):
        self.camera = camera
        self.arena = None
        self.pokemons = []
        self.pokemons_por_id = {}
        self.player_batalha = None
        self.hud = None
        self.montador_jogadas = None

        self.rodada_atual = 1
        self.lado_jogador = 50
        self.tipo_batalha = "simulador"
        self.modo_teste = False
        self.pokemon_selecionado = None
        self.area_selecionada = None
        self.ataque_selecionado = None
        self.logs_locais = []
        self.estado_batalha = "inicializando"
        self.id_partida = "simulador_local_fase2"
        self.server_batalha = ServerBatalha

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
        estado_cliente = dict(estado)
        estado.setdefault("id_partida", self.id_partida)
        estado.setdefault("lado_jogador", self.lado_jogador)
        resposta_inicial = self.server_batalha.inicializar_batalha(estado)
        if isinstance(resposta_inicial, dict) and resposta_inicial.get("status") == "ok" and isinstance(resposta_inicial.get("estado_inicial"), dict):
            estado = dict(resposta_inicial.get("estado_inicial") or estado)
            for chave in ("regras", "regras_mundo"):
                if chave not in estado and isinstance(estado_cliente.get(chave), dict):
                    estado[chave] = estado_cliente[chave]
        self.rodada_atual = int(estado.get("rodada_atual", 1) or 1)
        self.lado_jogador = int(estado.get("lado_jogador", 50) or 50)
        self.tipo_batalha = str(estado.get("tipo_batalha") or self.tipo_batalha)
        self.modo_teste = bool(estado.get("modo_teste", self.modo_teste))

        contexto_arena = dict(estado.get("arena") or {})
        self.arena = Arena(contexto_arena)

        if self.camera is None:
            self.camera = CameraBatalha((1920, 1080), posicao_inicial_tiles=(0, 0), tile_px=40)
        self.camera.definir_limites_mundo(self.arena.Largura, self.arena.Altura, toroidal=False)

        self.pokemons = [PokemonBatalha.from_serializado(item) for item in list(estado.get("pokemons") or [])]
        regras = estado.get("regras") if isinstance(estado.get("regras"), dict) else {}
        if not regras and isinstance(estado.get("regras_mundo"), dict):
            regras = estado.get("regras_mundo")
        if not regras:
            regras = estado
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
        self.id_partida = str(estado.get("id_partida") or self.id_partida)
        self.timer_rodada = self.timer_rodada_max
        self.estado_batalha = str(estado.get("estado_batalha") or "montando_jogada")

    def criar_componentes(self):
        self.player_batalha = PlayerBatalha(self)
        self.hud = ElementosHudBatalha(self)
        self.montador_jogadas = MontadorJogadas(self)

    def atualizar(self, dt, eventos):
        if self.arena is None or self.camera is None:
            return
        self._ultimos_eventos = list(eventos or [])
        self._ultimo_dt = float(dt or 0.0)
        self.camera.processar_eventos(eventos)
        self.camera.atualizar(dt)

        self.timer_rodada = max(0.0, self.timer_rodada - float(dt))
        if self.timer_rodada <= 0.0 and self.estado_batalha == "montando_jogada":
            self.enviar_jogada_pronta()
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
        areas_destacadas = []
        reservas_destacadas = []
        if self.montador_jogadas is not None:
            areas_destacadas = self.montador_jogadas.areas_destacadas()
            reservas_destacadas = self.montador_jogadas.reservas_destacadas()
        self.arena.desenhar_areas(
            surface,
            self.camera,
            area_hover=self._area_hover,
            area_selecionada=self.area_selecionada,
            areas_destacadas=areas_destacadas,
        )
        if self.montador_jogadas is not None:
            self.montador_jogadas.desenhar_pulso_previa(surface)
        for indicador in list(getattr(self.montador_jogadas, "indicadores_preparados", []) or []):
            indicador.atualizar(dt=self._ultimo_dt)
            indicador.desenhar(surface, self.camera)
        if getattr(self.montador_jogadas, "indicador_previa", None) is not None:
            self.montador_jogadas.indicador_previa.atualizar(dt=self._ultimo_dt)
            self.montador_jogadas.indicador_previa.desenhar(surface, self.camera)

        for pokemon in self.pokemons:
            if pokemon.esta_ativo() and not pokemon.esta_na_reserva():
                hover = pokemon.contem_ponto(pygame.mouse.get_pos())
                pokemon.desenhar(surface, self.camera, self.arena, selecionado=(self.area_selecionada == pokemon.AreaId), hover=hover)

        reservas_destacadas_set = set(reservas_destacadas)
        for lado in ("jogador", "inimigo"):
            for slot in self.arena.obter_slots_reserva(lado):
                poke = self.pokemons_por_id.get(slot.get("pokemon_id"))
                if poke is None:
                    continue
                rect = slot.get("rect_tela")
                hover = rect.collidepoint(pygame.mouse.get_pos()) if rect else False
                selecionado = self.area_selecionada in {slot.get("id_slot"), slot.get("pokemon_id")}
                if rect:
                    destacado = str(slot.get("id_slot")) in reservas_destacadas_set
                    if selecionado:
                        borda = (255, 235, 90, 245)
                    elif destacado:
                        pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
                        borda = (255, 225, 70, int(80 + 150 * pulso))
                    elif hover:
                        borda = (204, 212, 228, 170)
                    else:
                        borda = (0, 0, 0, 225)
                    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(overlay, (0, 0, 0, 235), overlay.get_rect(), 4)
                    pygame.draw.rect(overlay, borda, overlay.get_rect().inflate(-4, -4), 3)
                    surface.blit(overlay, rect.topleft)
                poke.desenhar_reserva(surface, rect, selecionado=selecionado, hover=hover, camera=self.camera)

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
        if area_id is not None and self.area_selecionada == area_id:
            self.desselecionar_pokemon()
            return
        self.area_selecionada = area_id
        if area_id is None:
            self.pokemon_selecionado = None
            self.limpar_ataque()
            return
        self.pokemon_selecionado = self.arena.pokemon_na_area(area_id)

    def selecionar_ataque(self, ataque):
        self.ataque_selecionado = ataque
        if ataque is None and self.montador_jogadas is not None and self.montador_jogadas.estado_montagem == "preparando_ataque":
            self.montador_jogadas.cancelar_previa()

    def limpar_ataque(self):
        self.ataque_selecionado = None
        if self.montador_jogadas is not None and self.montador_jogadas.estado_montagem == "preparando_ataque":
            self.montador_jogadas.cancelar_previa()
        if self.hud:
            self.hud.ficha.limpar_ataque_selecionado()

    def passar_rodada_local(self):
        self.estado_batalha = "passando_rodada"
        self.rodada_atual += 1
        self.limpar_ataque()
        self.timer_rodada = self.timer_rodada_max
        self.logs_locais.append({"rodada": self.rodada_atual, "texto": f"Rodada {self.rodada_atual} iniciada."})
        self.estado_batalha = "montando_jogada"

    def enviar_jogada_pronta(self):
        if self.montador_jogadas is None:
            return
        if self.modo_teste:
            pacote = self.montador_jogadas.gerar_pacote_jogadas_modo_teste()
        else:
            pacote = self.montador_jogadas.gerar_pacote_jogada()
            pacote["resolver_lados_ausentes"] = True
        self.estado_batalha = "aguardando_servidor"
        resposta = self.server_batalha.enviar_jogada(self.id_partida, self.lado_jogador, pacote)
        self.tratar_resposta_jogada(resposta)

    def tratar_resposta_jogada(self, resposta):
        status = str((resposta or {}).get("status") or "erro")
        if status == "ok":
            self.estado_batalha = str((resposta or {}).get("estado_batalha") or "recebido_stub")
            self.adicionar_log_local(str((resposta or {}).get("mensagem") or "Jogada aceita"))
            resultado = (resposta or {}).get("resultado")
            if not isinstance(resultado, dict):
                log = (resposta or {}).get("log") if isinstance((resposta or {}).get("log"), dict) else {}
                resultado = log.get("resultado") if isinstance(log.get("resultado"), dict) else None
            if isinstance(resultado, dict):
                self.aplicar_resultado_batalha(resultado)
                self.limpar_jogada_confirmada()
                return
            if self.estado_batalha != "aguardando":
                self.limpar_jogada_confirmada()
                self.estado_batalha = "montando_jogada"
            return
        self.estado_batalha = "montando_jogada"
        self.adicionar_log_local(str((resposta or {}).get("mensagem") or "Falha ao enviar jogada"))

    def aplicar_resultado_batalha(self, resultado):
        pokemons = resultado.get("pokemons") if isinstance(resultado.get("pokemons"), dict) else {}
        for pid, diff in pokemons.items():
            pokemon = self.pokemons_por_id.get(str(pid))
            if pokemon is not None:
                pokemon.atualizar_por_diff(diff)
        if self.arena is not None:
            self.arena.atualizar_ocupacao(self.pokemons)
        self.rodada_atual = int(resultado.get("rodada_atual", self.rodada_atual) or self.rodada_atual)
        self.estado_batalha = str(resultado.get("estado_batalha") or ("finalizada" if resultado.get("finalizada") else "montando_jogada"))
        if bool(resultado.get("finalizada")):
            self.estado_batalha = "finalizada"
        self.timer_rodada = self.timer_rodada_max

    def adicionar_log_local(self, texto):
        self.logs_locais.append({"rodada": self.rodada_atual, "texto": str(texto or "")})

    def limpar_jogada_confirmada(self):
        if self.montador_jogadas is not None:
            self.montador_jogadas.limpar_jogada()
        self.atualizar_previsoes_hud()

    def atualizar_previsoes_hud(self):
        if self.montador_jogadas is not None:
            self.montador_jogadas.recalcular_previsao_energia()

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
