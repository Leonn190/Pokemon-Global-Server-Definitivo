from __future__ import annotations

import copy
import math
from types import SimpleNamespace

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.ControladorAnimacoes import ControladorAnimacoes
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from Codigo.ModulosBatalha.FinalizadorBatalha import FinalizadorBatalha
from Codigo.ModulosBatalha.LeitorLogs import LeitorLogs
from Codigo.ModulosBatalha.MontadorJogadas import MontadorJogadas
from Codigo.ModulosBatalha.PlayerBatalha import PlayerBatalha
from Codigo.ModulosBatalha.PokemonBatalha import PokemonBatalha
from Codigo.Geradores.Player.Inventario import Inventario
from Codigo.Geradores.Player.Perfil import Perfil
from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.ModulosGerais.Server import ServerBatalha


class ControladorBatalha:
    ESCALA_ATOR_BATALHA = 1.5
    MARGEM_ATOR_CAPTURA_TILES = 1.8

    def __init__(self, camera=None, jogo=None, ao_sair_batalha=None):
        self.camera = camera
        self.jogo = jogo
        self.ao_sair_batalha = ao_sair_batalha
        self.arena = None
        self.pokemons = []
        self.pokemons_por_id = {}
        self.player_batalha = None
        self.hud = None
        self.montador_jogadas = None
        self.controlador_animacoes = None
        self.leitor_logs = None
        self.finalizador = FinalizadorBatalha(self)

        self.rodada_atual = 1
        self.lado_jogador = 50
        self.tipo_batalha = "simulador"
        self.modo_teste = False
        self.pokemon_selecionado = None
        self.area_selecionada = None
        self.ataque_selecionado = None
        self.logs_locais = []
        self.logs_por_rodada = {}
        self.logs_visiveis_por_rodada = {}
        self.replay_log_atual = None
        self.estado_batalha = "inicializando"
        self.id_partida = "simulador_local_fase2"
        self.server_batalha = ServerBatalha
        self.clima_atual = None
        self.ator = None
        self.contexto_batalha = {}
        self._ator_visual_player = None
        self._ator_visual_npc = None
        self._respiracao_atores_batalha = 0.0

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
        self._conhecimento_pokemons_vistos = set()
        self._ator_perfil_cache = None

    def ator_local(self):
        if self.ator is not None:
            return self.ator
        if self._ator_perfil_cache is not None:
            return self._ator_perfil_cache
        jogo = getattr(self, "jogo", None)
        dados = getattr(jogo, "INFO", {}).get("PlayerDadosServer") if jogo is not None and isinstance(getattr(jogo, "INFO", None), dict) else {}
        if not isinstance(dados, dict):
            return None
        perfil = Perfil()
        perfil.aplicar_serializado(dados.get("perfil") if isinstance(dados.get("perfil"), dict) else dados)
        inventario = Inventario()
        inventario.Perfil = perfil
        if isinstance(dados.get("inventario"), dict):
            inventario.aplicar_serializado(dados.get("inventario"))
        self._ator_perfil_cache = SimpleNamespace(Perfil=perfil, Inventario=inventario)
        return self._ator_perfil_cache

    def perfil_local(self):
        return getattr(self.ator_local(), "Perfil", None)

    def sincronizar_perfil_local(self):
        if self._ator_perfil_cache is None:
            return
        jogo = getattr(self, "jogo", None)
        if jogo is None or not isinstance(getattr(jogo, "INFO", None), dict):
            return
        dados = jogo.INFO.setdefault("PlayerDadosServer", {})
        perfil = getattr(self._ator_perfil_cache, "Perfil", None)
        inventario = getattr(self._ator_perfil_cache, "Inventario", None)
        if perfil is not None and hasattr(perfil, "serializar"):
            dados["perfil"] = perfil.serializar()
        if inventario is not None and hasattr(inventario, "serializar"):
            dados.setdefault("inventario", inventario.serializar())

    def inventario_local_serializado(self):
        ator = self.ator_local()
        inventario = getattr(ator, "Inventario", None)
        if inventario is not None and hasattr(inventario, "serializar"):
            return inventario.serializar()
        jogo = getattr(self, "jogo", None)
        dados = getattr(jogo, "INFO", {}).get("PlayerDadosServer") if jogo is not None and isinstance(getattr(jogo, "INFO", None), dict) else {}
        inv = dados.get("inventario") if isinstance(dados, dict) and isinstance(dados.get("inventario"), dict) else {}
        return copy.deepcopy(inv)

    def aplicar_inventario_batalha(self, inventario):
        if not isinstance(inventario, dict) or not inventario:
            return
        ator = self.ator_local()
        inv_obj = getattr(ator, "Inventario", None)
        if inv_obj is not None and hasattr(inv_obj, "aplicar_serializado"):
            inv_obj.aplicar_serializado(inventario)
        jogo = getattr(self, "jogo", None)
        if jogo is not None and isinstance(getattr(jogo, "INFO", None), dict):
            dados = jogo.INFO.setdefault("PlayerDadosServer", {})
            dados["inventario"] = copy.deepcopy(inventario)

    def iniciar(self, estado_inicial):
        estado = dict(estado_inicial or {})
        self.contexto_batalha = dict(estado)
        estado_cliente = dict(estado)
        tipo_estado = str(estado.get("tipo_batalha") or estado.get("tipo") or self.tipo_batalha).strip().lower()
        if tipo_estado in {"confronto", "treinador", "trainer"} and not bool(estado.get("modo_teste", self.modo_teste)):
            estado.setdefault("inventario_jogador", self.inventario_local_serializado())
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
        self.clima_atual = estado.get("clima_atual")

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
            pokemon.VidaAtual = max(0.0, min(float(pokemon.VidaMax), float(getattr(pokemon, "VidaAtual", pokemon.VidaMax))))
        self.pokemons_por_id = {p.id_batalha: p for p in self.pokemons}
        self._registrar_conhecimento_pokemons_batalha()
        self.arena.atualizar_ocupacao(self.pokemons)

        self.criar_componentes()
        self.id_partida = str(estado.get("id_partida") or self.id_partida)
        self.timer_rodada = self.timer_rodada_max
        self.estado_batalha = str(estado.get("estado_batalha") or "montando_jogada")
        self._preparar_atores_visuais_batalha()

    def criar_componentes(self):
        self.player_batalha = PlayerBatalha(self)
        self.hud = ElementosHudBatalha(self)
        self.montador_jogadas = MontadorJogadas(self)
        self.controlador_animacoes = ControladorAnimacoes(self)
        self.leitor_logs = LeitorLogs(self, self.controlador_animacoes)

    def atualizar(self, dt, eventos):
        if self.arena is None or self.camera is None:
            return
        self._ultimos_eventos = list(eventos or [])
        self._ultimo_dt = float(dt or 0.0)
        self.camera.processar_eventos(eventos)
        self.camera.atualizar(dt)
        self._respiracao_atores_batalha += max(0.0, float(dt or 0.0))

        if self.estado_batalha == "montando_jogada":
            self.timer_rodada = max(0.0, self.timer_rodada - float(dt))
        if self.timer_rodada <= 0.0 and self.estado_batalha == "montando_jogada":
            self.enviar_jogada_pronta()
        self.arena.atualizar_ocupacao(self.pokemons)
        self.arena.atualizar_layout_batalha(self.camera)
        self.arena.atualizar_slots_reserva(self.pokemons, self.camera)
        for pokemon in self.pokemons:
            pokemon.atualizar_animacao(dt)
            if hasattr(pokemon, "atualizar_efeitos_visuais"):
                pokemon.atualizar_efeitos_visuais(dt)

        self._area_hover = self.arena.area_em_posicao_mouse(pygame.mouse.get_pos(), self.camera)
        if self.controlador_animacoes is not None:
            self.controlador_animacoes.atualizar(dt)
        if self.leitor_logs is not None and (self.estado_batalha in {"lendo_log", "animando_rodada"} or getattr(self.leitor_logs, "estado", "") == "aguardando_resultado"):
            self.leitor_logs.atualizar(dt)
        if self.estado_batalha not in {"lendo_log", "animando_rodada", "aguardando_servidor", "finalizada"}:
            self.player_batalha.processar_eventos(eventos)
        self.hud.atualizar(dt, eventos)
        self._atualizar_fuga(dt)

    def _registrar_conhecimento_pokemons_batalha(self):
        perfil = self.perfil_local()
        if perfil is None or not hasattr(perfil, "registrar_conhecimento_pokemon"):
            return
        for pokemon in list(self.pokemons or []):
            pid = perfil._extrair_id_pokemon(pokemon) if hasattr(perfil, "_extrair_id_pokemon") else getattr(pokemon, "Nome", "")
            chave = str(pid or "").strip()
            if not chave or chave in self._conhecimento_pokemons_vistos:
                continue
            perfil.registrar_conhecimento_pokemon(pokemon)
            if hasattr(perfil, "registrar_conhecimento_ataques_pokemon"):
                perfil.registrar_conhecimento_ataques_pokemon(pokemon)
            for efeito in list(getattr(pokemon, "EfeitosFormais", []) or []):
                perfil.registrar_conhecimento_efeito((efeito or {}).get("code") or (efeito or {}).get("nome"))
            self._conhecimento_pokemons_vistos.add(chave)
        self.sincronizar_perfil_local()

    def desenhar(self, surface):
        if self.arena is None:
            return
        if self.hud is not None:
            self.hud.preparar_layout(surface)
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
            self.montador_jogadas.desenhar_fantasmas_movimento(surface)
        for indicador in list(getattr(self.montador_jogadas, "indicadores_alvos_parciais", []) or []):
            indicador.atualizar(dt=self._ultimo_dt)
            indicador.desenhar(surface, self.camera)
        for indicador in list(getattr(self.montador_jogadas, "indicadores_preparados", []) or []):
            indicador.atualizar(dt=self._ultimo_dt)
            indicador.desenhar(surface, self.camera)
        if getattr(self.montador_jogadas, "indicador_previa", None) is not None:
            self.montador_jogadas.indicador_previa.atualizar(dt=self._ultimo_dt)
            self.montador_jogadas.indicador_previa.desenhar(surface, self.camera)

        self._desenhar_atores_visuais_batalha(surface)

        for pokemon in self.pokemons:
            if pokemon.esta_ativo() and not pokemon.esta_na_reserva():
                if not self.pokemon_visivel(pokemon):
                    pokemon.RectAtual = pygame.Rect(0, 0, 0, 0)
                    continue
                hover = pokemon.contem_ponto(pygame.mouse.get_pos())
                pokemon.desenhar(surface, self.camera, self.arena, selecionado=(self.area_selecionada == pokemon.AreaId), hover=hover)

        reservas_destacadas_set = set(reservas_destacadas)
        for lado in ("jogador", "inimigo"):
            for slot in self.arena.obter_slots_reserva(lado):
                poke = self.pokemons_por_id.get(slot.get("pokemon_id"))
                if poke is None:
                    continue
                if not self.pokemon_visivel(poke):
                    poke.RectAtual = pygame.Rect(0, 0, 0, 0)
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

        if self.controlador_animacoes is not None:
            self.controlador_animacoes.desenhar(surface)
        self.hud.desenhar(surface, self._ultimos_eventos, self._ultimo_dt)
        alpha = max(0, min(255, int(round(self._fuga_alpha))))
        if alpha > 0:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            surface.blit(overlay, (0, 0))

    def selecionar_pokemon(self, pokemon):
        if pokemon is not None and not self.pokemon_visivel(pokemon):
            pokemon = None
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
        if not self.pokemon_visivel(self.pokemon_selecionado):
            self.pokemon_selecionado = None

    def pokemon_visivel(self, pokemon):
        if pokemon is None:
            return False
        if bool(self.modo_teste):
            return True
        if int(getattr(pokemon, "lado_id", -1)) == int(self.lado_jogador):
            return True
        return not (hasattr(pokemon, "esta_furtivo") and pokemon.esta_furtivo())

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
        if self.estado_batalha != "montando_jogada":
            return
        if self.montador_jogadas is None:
            return
        if self.modo_teste:
            pacote = self.montador_jogadas.gerar_pacote_jogadas_modo_teste()
        else:
            pacote = self.montador_jogadas.gerar_pacote_jogada()
            if not self.batalha_usa_ia():
                pacote["resolver_lados_ausentes"] = True
        self._ocultar_montagem_visual()
        self.estado_batalha = "aguardando_servidor"
        resposta = self.server_batalha.enviar_jogada(self.id_partida, self.lado_jogador, pacote)
        self.tratar_resposta_jogada(resposta)

    def tratar_resposta_jogada(self, resposta):
        status = str((resposta or {}).get("status") or "erro")
        if status == "ok":
            self.estado_batalha = str((resposta or {}).get("estado_batalha") or "recebido_stub")
            self.adicionar_log_local(str((resposta or {}).get("mensagem") or "Jogada aceita"))
            log = (resposta or {}).get("log") if isinstance((resposta or {}).get("log"), dict) else {}
            if isinstance(log, dict) and list(log.get("historico") or []):
                self.receber_log(log)
                return
            resultado = (resposta or {}).get("resultado")
            if not isinstance(resultado, dict):
                resultado = log.get("resultado") if isinstance(log.get("resultado"), dict) else None
            if isinstance(resultado, dict):
                self.aplicar_resultado_final(resultado)
                self.limpar_jogada_confirmada()
                if bool(resultado.get("finalizada")) and self.finalizador is not None:
                    self.finalizador.finalizar_por_resultado(resultado)
                return
            if self.estado_batalha != "aguardando":
                self.limpar_jogada_confirmada()
                self.estado_batalha = "montando_jogada"
            return
        self.estado_batalha = "montando_jogada"
        self.adicionar_log_local(str((resposta or {}).get("mensagem") or "Falha ao enviar jogada"))

    def aplicar_resultado_batalha(self, resultado):
        return self.aplicar_resultado_final(resultado)

    def aplicar_resultado_final(self, resultado):
        pokemons = resultado.get("pokemons") if isinstance(resultado.get("pokemons"), dict) else {}
        for pid, diff in pokemons.items():
            pokemon = self.pokemons_por_id.get(str(pid))
            if pokemon is not None:
                pokemon.atualizar_por_diff(diff)
        if self.arena is not None:
            self.arena.atualizar_ocupacao(self.pokemons)
        if self.pokemon_selecionado is not None and ((not self.pokemon_selecionado.esta_vivo()) or (not self.pokemon_visivel(self.pokemon_selecionado))):
            self.desselecionar_pokemon()
        self.rodada_atual = int(resultado.get("rodada_atual", self.rodada_atual) or self.rodada_atual)
        if "clima_atual" in resultado:
            self.clima_atual = resultado.get("clima_atual")
        if isinstance(resultado.get("inventario_jogador"), dict):
            self.aplicar_inventario_batalha(resultado.get("inventario_jogador"))
        self.estado_batalha = str(resultado.get("estado_batalha") or ("finalizada" if resultado.get("finalizada") else "montando_jogada"))
        if bool(resultado.get("finalizada")):
            self.estado_batalha = "finalizada"
        self.timer_rodada = self.timer_rodada_max

    def batalha_usa_ia(self):
        tipo = str(self.tipo_batalha or "").strip().lower()
        return tipo in {"confronto", "treinador", "trainer", "servo", "boss"} and not bool(self.modo_teste)

    def fuga_disponivel(self):
        tipo = str(self.tipo_batalha or "").strip().lower()
        if tipo == "boss":
            return False
        if tipo == "servo":
            return int(self.rodada_atual or 1) > 5
        return True

    def posicao_captura_lado_tela(self, lado_id=None):
        pos = self.posicao_captura_lado_mundo(lado_id)
        if pos is None or self.camera is None:
            return None
        try:
            return self.camera.mundo_para_tela_px(pos)
        except Exception:
            return None

    def posicao_captura_lado_mundo(self, lado_id=None):
        if self.arena is None:
            return None
        lado = int(lado_id if lado_id is not None else self.lado_jogador)
        aliado = int(lado) == int(self.lado_jogador)
        area_id = "A7" if aliado else "I3"
        area = self.arena.obter_area_por_id(area_id)
        if not area or not isinstance(area.get("rect"), pygame.Rect):
            return self.arena.centro_area(area_id)
        rect = area["rect"]
        margem = float(self.MARGEM_ATOR_CAPTURA_TILES)
        if aliado:
            return (float(rect.left) - margem, float(rect.centery))
        return (float(rect.right) + margem, float(rect.centery))

    def _preparar_atores_visuais_batalha(self):
        tile = max(1, int(getattr(self.camera, "TilePx", 40) or 40)) if self.camera is not None else 40
        self._ator_visual_player = Ator(nome_skin=self._skin_player_batalha(), posicao=(0.0, 0.0), escala_skin_tiles=self.ESCALA_ATOR_BATALHA, tile_px=tile)
        npc_skin = self._skin_npc_batalha()
        self._ator_visual_npc = Ator(nome_skin=npc_skin, posicao=(0.0, 0.0), escala_skin_tiles=self.ESCALA_ATOR_BATALHA, tile_px=tile) if npc_skin else None

    def _skin_player_batalha(self):
        if self.ator is not None and getattr(self.ator, "NomeSkin", None):
            return str(getattr(self.ator, "NomeSkin"))
        jogo = getattr(self, "jogo", None)
        dados = getattr(jogo, "INFO", {}).get("PlayerDadosServer") if jogo is not None and isinstance(getattr(jogo, "INFO", None), dict) else {}
        for chave in ("skin", "nome_skin", "NomeSkin"):
            if isinstance(dados, dict) and dados.get(chave):
                return str(dados.get(chave))
        perfil = self.perfil_local()
        skins = list(getattr(perfil, "SkinsLiberadas", []) or [])
        return str(skins[0] if skins else "S1.png")

    def _skin_npc_batalha(self):
        tipo = str(self.tipo_batalha or "").strip().lower()
        if tipo not in {"treinador", "trainer"}:
            return ""
        ctx = dict(getattr(self, "contexto_batalha", {}) or {})
        npc = ctx.get("npc_contexto") if isinstance(ctx.get("npc_contexto"), dict) else {}
        estado = npc.get("estado") if isinstance(npc.get("estado"), dict) else {}
        return str(npc.get("skin") or estado.get("skin") or "1.png")

    def _desenhar_atores_visuais_batalha(self, surface):
        tipo = str(self.tipo_batalha or "").strip().lower()
        if tipo not in {"confronto", "treinador", "trainer"} or bool(self.modo_teste):
            return
        if self._ator_visual_player is None:
            self._preparar_atores_visuais_batalha()
        self._desenhar_ator_captura(surface, self._ator_visual_player, self.lado_jogador)
        if tipo in {"treinador", "trainer"}:
            self._desenhar_ator_captura(surface, self._ator_visual_npc, self.obter_lado_ia())

    def _desenhar_ator_captura(self, surface, ator, lado_id):
        if ator is None or not hasattr(ator, "Desenhador"):
            return
        pos_mundo = self.posicao_captura_lado_mundo(lado_id)
        pos_tela = self.posicao_captura_lado_tela(lado_id)
        if pos_mundo is None or pos_tela is None:
            return
        if self.camera is not None and hasattr(ator, "set_tile_px"):
            ator.set_tile_px(max(1, int(getattr(self.camera, "TilePx", 40) or 40)))
        ator.definir_posicao(float(pos_mundo[0]), float(pos_mundo[1]))
        mouse = pygame.mouse.get_pos()
        dx = float(mouse[0]) - float(pos_tela[0])
        dy = float(mouse[1]) - float(pos_tela[1])
        if abs(dx) + abs(dy) > 0.001:
            ator.definir_angulo_olhar((math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0)
        ator.Desenhador.desenhar(surface, pos_tela, mouse_pos=mouse, angulo_graus=getattr(ator, "AnguloOlhar", 0.0), respiracao_tempo=self._respiracao_atores_batalha)

    def nome_jogador_batalha(self):
        ator = self.ator_local()
        perfil = getattr(ator, "Perfil", None)
        for valor in (
            getattr(ator, "Nome", None),
            getattr(perfil, "Nome", None),
            getattr(perfil, "nome", None),
        ):
            if str(valor or "").strip():
                return str(valor).strip()
        jogo = getattr(self, "jogo", None)
        info = getattr(jogo, "INFO", {}) if jogo is not None else {}
        dados = info.get("PlayerDadosServer") if isinstance(info, dict) else {}
        for chave in ("nome", "Nome", "usuario", "Usuario", "player_nome"):
            if isinstance(dados, dict) and str(dados.get(chave) or "").strip():
                return str(dados.get(chave)).strip()
        return "Jogador"

    def obter_lado_ia(self):
        for pokemon in self.pokemons:
            if not pokemon.esta_vivo():
                continue
            lado = int(getattr(pokemon, "lado_id", -1) or -1)
            if lado != int(self.lado_jogador):
                return lado
        return 51

    @staticmethod
    def _resposta_aguardando(resposta):
        return str((resposta or {}).get("status") or "").lower() == "ok" and str((resposta or {}).get("estado_batalha") or "").lower() == "aguardando"

    def receber_log(self, log):
        rodada = int((log or {}).get("rodada") or self.rodada_atual or 1)
        self.logs_por_rodada[rodada] = dict(log or {})
        self.logs_visiveis_por_rodada[rodada] = []
        self.replay_log_atual = {"ativo": True, "turno_atual": rodada, "tick_atual": 0, "tick_final": len(list((log or {}).get("historico") or []))}
        self._ocultar_montagem_visual()
        self.bloquear_input_durante_log()
        self.estado_batalha = "animando_rodada"
        if self.leitor_logs is not None:
            self.leitor_logs.carregar_log(log)
            self.leitor_logs.iniciar_leitura()

    def registrar_evento_visual(self, evento):
        rodada = int((evento or {}).get("rodada") or (self.replay_log_atual or {}).get("turno_atual") or self.rodada_atual or 1)
        self.logs_visiveis_por_rodada.setdefault(rodada, []).append(dict(evento or {}))
        if isinstance(self.replay_log_atual, dict) and int(self.replay_log_atual.get("turno_atual", 0) or 0) == rodada:
            self.replay_log_atual["tick_atual"] = len(self.logs_visiveis_por_rodada.get(rodada, []))

    def voltar_para_montagem(self):
        self.desbloquear_input_apos_log()
        self.estado_batalha = "montando_jogada"
        self.timer_rodada = self.timer_rodada_max
        if isinstance(self.replay_log_atual, dict):
            self.replay_log_atual["ativo"] = False

    def bloquear_input_durante_log(self):
        self.limpar_ataque()
        self.area_selecionada = None
        self.pokemon_selecionado = None

    def _ocultar_montagem_visual(self):
        if self.montador_jogadas is not None:
            self.montador_jogadas.limpar_jogada()
            self.montador_jogadas.cancelar_previa()
        hud = getattr(self, "hud", None)
        painel = getattr(hud, "painel_acoes", None)
        if painel is not None and hasattr(painel, "sincronizar"):
            painel.sincronizar([], None)

    def desbloquear_input_apos_log(self):
        if isinstance(self.replay_log_atual, dict):
            self.replay_log_atual["ativo"] = False

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
        if not self.fuga_disponivel():
            self.adicionar_log_local("Fuga liberada apos 5 turnos." if str(self.tipo_batalha or "").strip().lower() == "servo" else "Fuga bloqueada nesta batalha.")
            return
        self._fuga_alpha = min(255.0, self._fuga_alpha + self._fuga_incremento_clique)
        self.estado_batalha = "fugindo"
        if self._fuga_alpha >= self._fuga_limite_saida:
            if self.finalizador is not None:
                self.finalizador.finalizar_por_fuga()
            else:
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
        ultimo = max([1, self.rodada_atual, *list(self.logs_por_rodada.keys() or [1]), *list(self.logs_visiveis_por_rodada.keys() or [1])])
        return {
            "ultimo_turno_com_log": ultimo,
            "rodada_atual": self.rodada_atual,
            "replay": dict(self.replay_log_atual or {"ativo": False}),
        }

    def obter_log_publico(self, rodada):
        alvo = int(rodada or 1)
        if alvo in self.logs_visiveis_por_rodada:
            return {"historico": [dict(e) for e in self.logs_visiveis_por_rodada.get(alvo, [])]}
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
