from __future__ import annotations

import copy
from types import SimpleNamespace

import pygame

from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.ControladorAnimacoes import ControladorAnimacoes
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from Codigo.ModulosBatalha.FinalizadorBatalha import FinalizadorBatalha
from Codigo.ModulosBatalha.FluxoBatalha import FluxoBatalha
from Codigo.ModulosBatalha.LeitorLogs import LeitorLogs
from Codigo.ModulosBatalha.MontadorJogadas import MontadorJogadas
from Codigo.ModulosBatalha.PlayerBatalha import PlayerBatalha
from Codigo.ModulosBatalha.PokemonBatalha import PokemonBatalha
from Codigo.ModulosBatalha.RenderizadorBatalha import RenderizadorBatalha
from Codigo.ModulosMundo.Geradores.Player.Inventario import Inventario
from Codigo.ModulosMundo.Geradores.Player.Perfil import Perfil
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
        self.fluxo = FluxoBatalha(self)
        self.renderizador = RenderizadorBatalha(self)

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
        return self.renderizador.desenhar(surface)

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
        return self.fluxo.passar_rodada_local()

    def enviar_jogada_pronta(self):
        return self.fluxo.enviar_jogada_pronta()

    def tratar_resposta_jogada(self, resposta):
        return self.fluxo.tratar_resposta_jogada(resposta)

    def aplicar_resultado_batalha(self, resultado):
        return self.fluxo.aplicar_resultado_batalha(resultado)

    def aplicar_resultado_final(self, resultado):
        return self.fluxo.aplicar_resultado_final(resultado)

    def batalha_usa_ia(self):
        return self.fluxo.batalha_usa_ia()

    def fuga_disponivel(self):
        return self.fluxo.fuga_disponivel()

    def posicao_captura_lado_tela(self, lado_id=None):
        return self.renderizador.posicao_captura_lado_tela(lado_id)

    def posicao_captura_lado_mundo(self, lado_id=None):
        return self.renderizador.posicao_captura_lado_mundo(lado_id)

    def _preparar_atores_visuais_batalha(self):
        return self.renderizador.preparar_atores_visuais_batalha()

    def _skin_player_batalha(self):
        return self.renderizador.skin_player_batalha()

    def _skin_npc_batalha(self):
        return self.renderizador.skin_npc_batalha()

    def _desenhar_atores_visuais_batalha(self, surface):
        return self.renderizador.desenhar_atores_visuais_batalha(surface)

    def _desenhar_ator_captura(self, surface, ator, lado_id):
        return self.renderizador.desenhar_ator_captura(surface, ator, lado_id)

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
        return FluxoBatalha._resposta_aguardando(resposta)

    def receber_log(self, log):
        return self.fluxo.receber_log(log)

    def registrar_evento_visual(self, evento):
        return self.fluxo.registrar_evento_visual(evento)

    def voltar_para_montagem(self):
        return self.fluxo.voltar_para_montagem()

    def bloquear_input_durante_log(self):
        return self.fluxo.bloquear_input_durante_log()

    def _ocultar_montagem_visual(self):
        return self.fluxo._ocultar_montagem_visual()

    def desbloquear_input_apos_log(self):
        return self.fluxo.desbloquear_input_apos_log()

    def adicionar_log_local(self, texto):
        return self.fluxo.adicionar_log_local(texto)

    def limpar_jogada_confirmada(self):
        return self.fluxo.limpar_jogada_confirmada()

    def atualizar_previsoes_hud(self):
        return self.fluxo.atualizar_previsoes_hud()

    def iniciar_fuga(self):
        return self.fluxo.iniciar_fuga()

    def _atualizar_fuga(self, dt: float):
        return self.fluxo.atualizar_fuga(dt)

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
        return self.fluxo.estado_visualizador_logs()

    def obter_log_publico(self, rodada):
        return self.fluxo.obter_log_publico(rodada)
