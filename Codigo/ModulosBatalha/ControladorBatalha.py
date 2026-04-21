from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

import pygame

from Codigo.Geradores.PokemonBatalha import PokemonBatalha
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha, pontos_lados_arena
from Codigo.ModulosBatalha.LeitorLogs import LeitorLogs
from Codigo.ModulosBatalha.SistemaBatalha import SistemaBatalha
from Codigo.ModulosBatalha.PlayerBatalha import PlayerBatalha
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_cliente_mundo


class ControladorBatalha:
    _MAX_ATIVOS = 3

    def __init__(self, contexto: Dict[str, object]):
        self.Contexto = dict(contexto or {})
        self.Arena = Arena(self.Contexto)
        self.SistemaBatalha = SistemaBatalha(self.Contexto)
        self.PokemonsAliados: List[PokemonBatalha] = []
        self.PokemonsInimigos: List[PokemonBatalha] = []
        self.PokemonsReservaAliados: List[Dict[str, object]] = []
        self.PokemonsReservaInimigos: List[Dict[str, object]] = []
        self.PokemonsReservaAliadosObj: List[PokemonBatalha] = []
        max_ativos = self._max_ativos_contexto()
        self.Jogador = PlayerBatalha("jogador", max_ativos=max_ativos)
        self.Inimigo = PlayerBatalha("inimigo", max_ativos=max_ativos)
        self.TimeCompletoJogadorInicial: List[Dict[str, object]] = []
        self.PokemonSelecionado: PokemonBatalha | None = None
        self._provedor_reservas = None
        self._rodada_atual = 1
        self._leitor_logs = LeitorLogs(self)
        self._logs_publicos_por_turno: Dict[int, Dict[str, object]] = {}
        self._ultima_resposta_inicio_servidor = None
        self._ultima_resposta_turno_servidor = None
        self._inicializar_times()

    def _max_ativos_contexto(self) -> int:
        regras = self.Contexto.get("batalha") if isinstance(self.Contexto.get("batalha"), dict) else {}
        candidatos = [
            self.Contexto.get("max_ativos"),
            self.Contexto.get("ativos_iniciais"),
            self.Contexto.get("slots_ativos"),
            regras.get("max_ativos"),
            regras.get("ativos_iniciais"),
            regras.get("slots_ativos"),
        ]
        for valor in candidatos:
            try:
                qtd = int(float(valor))
            except (TypeError, ValueError):
                continue
            if qtd > 0:
                return qtd
        return self._MAX_ATIVOS

    def obter_regras_batalha(self) -> Dict[str, object]:
        regras = self.Contexto.get("batalha") if isinstance(self.Contexto.get("batalha"), dict) else {}
        if not regras and hasattr(self.SistemaBatalha, "Contexto"):
            regras = self.SistemaBatalha.Contexto.get("batalha") if isinstance(self.SistemaBatalha.Contexto.get("batalha"), dict) else {}
        if not regras:
            resposta_inicio = self.Contexto.get("batalha_servidor_inicio") if isinstance(self.Contexto, dict) else {}
            batalha_inicio = resposta_inicio.get("batalha") if isinstance(resposta_inicio, dict) and isinstance(resposta_inicio.get("batalha"), dict) else {}
            regras = batalha_inicio.get("regras_batalha") if isinstance(batalha_inicio.get("regras_batalha"), dict) else {}
        if not regras:
            regras = dict(carregar_regras_cliente_mundo().get("batalha") or {})
        return dict(regras)

    def _centro_arena_local(self) -> tuple[float, float]:
        arena_w = float(self.Contexto.get("arena_largura", 40) or 40)
        arena_h = float(self.Contexto.get("arena_altura", 20) or 20)
        return arena_w * 0.5, arena_h * 0.5

    def _inicializar_times(self) -> None:
        init = InicializadorBatalha(self.Contexto)
        batalha = init.inicializar()
        self.Contexto["batalha_inicializada"] = batalha
        self.TimeCompletoJogadorInicial = [deepcopy(poke) for poke in batalha.get("jogador", []) if isinstance(poke, dict)]
        if hasattr(self.SistemaBatalha, "iniciar_batalha_server_async"):
            self.SistemaBatalha.iniciar_batalha_server_async(batalha)

        arena_w = float(self.Contexto.get("arena_largura", 40) or 40)
        arena_h = float(self.Contexto.get("arena_altura", 20) or 20)
        centro = self._centro_arena_local()
        self.Jogador.TimeCompleto = [poke for poke in batalha.get("jogador", []) if isinstance(poke, dict)]
        self.Inimigo.TimeCompleto = [poke for poke in batalha.get("inimigo", []) if isinstance(poke, dict)]
        aliados_ativos = self.Jogador.preparar_slots()
        inimigos_ativos = self.Inimigo.preparar_slots()
        self.PokemonsReservaAliados = list(self.Jogador.PokemonsReserva)
        self.PokemonsReservaInimigos = list(self.Inimigo.PokemonsReserva)
        pos_aliados, pos_inimigos = pontos_lados_arena(
            centro=centro,
            largura=arena_w,
            altura=arena_h,
            total_aliados=len(aliados_ativos),
            total_inimigos=len(inimigos_ativos),
        )

        self.PokemonsAliados = [self._criar_pokemon_visual_inicial(poke, pos_aliados[i], "jogador") for i, poke in enumerate(aliados_ativos) if i < len(pos_aliados)]
        self.PokemonsInimigos = [self._criar_pokemon_visual_inicial(poke, pos_inimigos[i], "inimigo") for i, poke in enumerate(inimigos_ativos) if i < len(pos_inimigos)]
        self.PokemonsReservaAliadosObj = self._criar_reservas_visuais(
            self.PokemonsReservaAliados,
            centro=centro,
            arena_w=arena_w,
            arena_h=arena_h,
        )
        self.Jogador.definir_ativos(self.PokemonsAliados)
        self.Inimigo.definir_ativos(self.PokemonsInimigos)
        self.SistemaBatalha.definir_lados(self.PokemonsAliados, self.PokemonsInimigos)

    def _criar_reservas_visuais(self, pokemons_reserva: List[Dict[str, object]], *, centro, arena_w: float, arena_h: float) -> List[PokemonBatalha]:
        base_x = float(centro[0]) - (arena_w * 0.5) + 1.8
        base_y = float(centro[1]) + (arena_h * 0.5) + 1.4
        saida: List[PokemonBatalha] = []
        for indice, poke in enumerate(list(pokemons_reserva or [])[:3]):
            pos = (base_x + indice * 1.85, base_y)
            reserva = self._criar_pokemon_visual_inicial(poke, pos, "jogador")
            reserva.EmReserva = True
            saida.append(reserva)
        return saida

    def _criar_pokemon_visual_inicial(self, dados: Dict[str, object], posicao, lado: str) -> PokemonBatalha:
        pokemon = PokemonBatalha(dados, posicao=posicao, lado=lado, regras=self.Contexto)
        pokemon.Posicao = (float(posicao[0]), float(posicao[1]))
        pokemon.PosicaoAnterior = pokemon.Posicao
        return pokemon

    def pokemon_no_ponto(self, mouse_tela_px, camera) -> PokemonBatalha | None:
        if not isinstance(mouse_tela_px, (tuple, list)) or len(mouse_tela_px) != 2:
            return None
        mx, my = int(mouse_tela_px[0]), int(mouse_tela_px[1])
        for poke in (self.PokemonsAliados + self.PokemonsInimigos + self.PokemonsReservaAliadosObj):
            cx, cy = poke.centro_tela(camera)
            r = poke.raio_px(camera)
            if (mx - cx) * (mx - cx) + (my - cy) * (my - cy) <= r * r:
                return poke
        return None

    def pokemon_eh_aliado(self, pokemon) -> bool:
        return pokemon in self.PokemonsAliados or pokemon in self.PokemonsReservaAliadosObj

    def pokemon_eh_reserva_aliada(self, pokemon) -> bool:
        return pokemon in self.PokemonsReservaAliadosObj

    def modo_teste_ativo(self) -> bool:
        resultado = self.resultado_batalha_atual()
        if isinstance(resultado, dict) and "modo_teste" in resultado:
            return bool(resultado.get("modo_teste"))
        return bool(self.Contexto.get("modo_teste", False))

    def pokemon_eh_controlavel(self, pokemon) -> bool:
        if pokemon is None or bool(getattr(pokemon, "EmReserva", False)):
            return False
        if self.pokemon_eh_aliado(pokemon):
            return True
        return bool(self.modo_teste_ativo() and pokemon in self.PokemonsInimigos)

    def definir_provedor_reservas(self, provedor) -> None:
        self._provedor_reservas = provedor

    def selecionar_slot_aliado(self, indice: int) -> PokemonBatalha | None:
        idx = int(indice)
        if idx < 0 or idx >= len(self.PokemonsAliados):
            return self.PokemonSelecionado
        alvo = self.PokemonsAliados[idx]
        self.PokemonSelecionado = None if self.PokemonSelecionado is alvo else alvo
        return self.PokemonSelecionado

    def limpar_selecao(self) -> None:
        self.PokemonSelecionado = None

    def selecionar_pokemon(self, pokemon) -> PokemonBatalha | None:
        if pokemon is self.PokemonSelecionado:
            self.PokemonSelecionado = None
        elif pokemon is not None:
            self.PokemonSelecionado = pokemon
        return self.PokemonSelecionado

    def selecionar_por_mouse(self, mouse_tela_px, camera) -> PokemonBatalha | None:
        return self.selecionar_pokemon(self.pokemon_no_ponto(mouse_tela_px, camera))

    @staticmethod
    def _uid_pokemon(pokemon) -> str:
        if pokemon is None:
            return ""
        uid = str(getattr(pokemon, "Uid", "") or "")
        if uid:
            return uid
        dados = getattr(pokemon, "Dados", {}) if hasattr(pokemon, "Dados") else {}
        if isinstance(dados, dict):
            return str(dados.get("uid") or dados.get("id") or dados.get("ID") or "")
        return ""

    def _mapa_existentes(self) -> Dict[str, PokemonBatalha]:
        mapa: Dict[str, PokemonBatalha] = {}
        for pokemon in self.PokemonsAliados + self.PokemonsInimigos + self.PokemonsReservaAliadosObj:
            uid = self._uid_pokemon(pokemon)
            if uid and uid not in mapa:
                mapa[uid] = pokemon
        return mapa

    @staticmethod
    def _posicao_dict(dados: Dict[str, object], fallback) -> tuple[float, float]:
        pos = dados.get("posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return float(pos[0]), float(pos[1])
        return float(fallback[0]), float(fallback[1])

    def _instanciar_ou_atualizar(self, dados: Dict[str, object], lado: str, posicao, existentes: Dict[str, PokemonBatalha], *, em_reserva: bool) -> PokemonBatalha:
        uid = str(dados.get("uid") or dados.get("id") or dados.get("ID") or "")
        pokemon = existentes.pop(uid, None) if uid else None
        if pokemon is None:
            pokemon = PokemonBatalha(dados, posicao=posicao, lado=lado, regras=self.Contexto)
        pokemon.EmReserva = bool(em_reserva)
        pokemon.atualizar(dados)
        if em_reserva:
            pokemon.Posicao = (float(posicao[0]), float(posicao[1]))
        return pokemon

    def mapa_pokemons(self) -> Dict[str, PokemonBatalha]:
        return self._mapa_existentes()

    def esta_reproduzindo_logs(self) -> bool:
        return bool(self._leitor_logs.esta_ativo())

    @staticmethod
    def _turno_log(log: Dict[str, object] | None, default: int = 0) -> int:
        if not isinstance(log, dict):
            return int(default)
        try:
            return max(0, int(log.get("turno_atual", default) or default))
        except (TypeError, ValueError):
            return int(default)

    def _registrar_log_publico(self, log: Dict[str, object] | None) -> None:
        turno = self._turno_log(log, default=0)
        if turno <= 0 or not isinstance(log, dict):
            return
        self._logs_publicos_por_turno[turno] = dict(log)

    def listar_logs_publicos(self) -> List[Dict[str, object]]:
        return [dict(self._logs_publicos_por_turno[turno]) for turno in sorted(self._logs_publicos_por_turno.keys())]

    def obter_log_publico(self, turno: int) -> Dict[str, object] | None:
        try:
            turno_i = int(turno)
        except (TypeError, ValueError):
            return None
        log = self._logs_publicos_por_turno.get(turno_i)
        return dict(log) if isinstance(log, dict) else None

    def estado_visualizador_logs(self) -> Dict[str, object]:
        replay = dict(self._leitor_logs.estado_visualizacao() or {})
        turnos = sorted(self._logs_publicos_por_turno.keys())
        ultimo_turno = max(turnos, default=0)
        return {
            "rodada_atual_batalha": int(self._rodada_atual or 1),
            "turnos_disponiveis": list(turnos),
            "ultimo_turno_com_log": int(ultimo_turno),
            "replay": replay,
        }

    def _aplicar_estado_servidor(self, resultado: Dict[str, object], log: Dict[str, object] | None = None) -> None:
        self.SistemaBatalha.atualizar(dados_servidor=resultado, log_servidor=log if isinstance(log, dict) else None)
        self._rodada_atual = max(1, int(self.SistemaBatalha.TurnoAtual or self._rodada_atual))
        self.Contexto["modo_teste"] = bool(resultado.get("modo_teste", self.Contexto.get("modo_teste", False)))

        selecionado_uid = self._uid_pokemon(self.PokemonSelecionado)
        existentes = self._mapa_existentes()
        arena_w = float(self.Contexto.get("arena_largura", 40) or 40)
        arena_h = float(self.Contexto.get("arena_altura", 20) or 20)
        centro = self._centro_arena_local()

        dados_jogador = resultado.get("jogador") if isinstance(resultado.get("jogador"), dict) else {}
        dados_inimigo = resultado.get("inimigo") if isinstance(resultado.get("inimigo"), dict) else {}
        ativos_jogador = [dict(item) for item in list(dados_jogador.get("ativos") or []) if isinstance(item, dict)]
        ativos_inimigo = [dict(item) for item in list(dados_inimigo.get("ativos") or []) if isinstance(item, dict)]
        reservas_jogador = [dict(item) for item in list(dados_jogador.get("reservas") or []) if isinstance(item, dict)]
        reservas_inimigo = [dict(item) for item in list(dados_inimigo.get("reservas") or []) if isinstance(item, dict)]

        pos_aliados, pos_inimigos = pontos_lados_arena(
            centro=centro,
            largura=arena_w,
            altura=arena_h,
            total_aliados=len(ativos_jogador),
            total_inimigos=len(ativos_inimigo),
        )

        self.PokemonsAliados = [
            self._instanciar_ou_atualizar(
                dados,
                "jogador",
                self._posicao_dict(dados, pos_aliados[indice] if indice < len(pos_aliados) else (0.0, 0.0)),
                existentes,
                em_reserva=False,
            )
            for indice, dados in enumerate(ativos_jogador)
        ]
        self.PokemonsInimigos = [
            self._instanciar_ou_atualizar(
                dados,
                "inimigo",
                self._posicao_dict(dados, pos_inimigos[indice] if indice < len(pos_inimigos) else (0.0, 0.0)),
                existentes,
                em_reserva=False,
            )
            for indice, dados in enumerate(ativos_inimigo)
        ]

        base_x = float(centro[0]) - (arena_w * 0.5) + 1.8
        base_y = float(centro[1]) + (arena_h * 0.5) + 1.4
        self.PokemonsReservaAliadosObj = []
        for indice, dados in enumerate(reservas_jogador[:3]):
            pos = (base_x + indice * 1.85, base_y)
            self.PokemonsReservaAliadosObj.append(self._instanciar_ou_atualizar(dados, "jogador", pos, existentes, em_reserva=True))

        self.PokemonsReservaAliados = list(reservas_jogador)
        self.PokemonsReservaInimigos = list(reservas_inimigo)
        self.Jogador.TimeCompleto = list(ativos_jogador) + list(reservas_jogador)
        self.Inimigo.TimeCompleto = list(ativos_inimigo) + list(reservas_inimigo)
        self.Jogador.PokemonsReserva = list(reservas_jogador)
        self.Inimigo.PokemonsReserva = list(reservas_inimigo)
        self.Jogador.definir_ativos(self.PokemonsAliados)
        self.Inimigo.definir_ativos(self.PokemonsInimigos)
        self.SistemaBatalha.definir_lados(self.PokemonsAliados, self.PokemonsInimigos)

        mapa_atual = self._mapa_existentes()
        self.PokemonSelecionado = mapa_atual.get(selecionado_uid) if selecionado_uid else None

    def atualizar_estado_servidor(self, retorno: Dict[str, object] | None = None) -> None:
        if not isinstance(retorno, dict):
            return
        status = str(retorno.get("status") or "")
        log = retorno.get("log") if isinstance(retorno.get("log"), dict) else {}
        if log:
            self._registrar_log_publico(log)
        resultado = self.SistemaBatalha.resolver_estado_recebido(retorno, log)
        if not resultado:
            if log:
                self.SistemaBatalha.atualizar(log_servidor=log)
            return
        if self._leitor_logs.reproduzir(
            log,
            resultado=resultado,
            ao_finalizar=lambda final: self._aplicar_estado_servidor(final, log),
        ):
            return
        self._aplicar_estado_servidor(resultado, log)

    def aplicar_snapshot_replay(self, snapshot: Dict[str, object] | None = None) -> None:
        if not isinstance(snapshot, dict) or not snapshot:
            return
        self._aplicar_estado_servidor(snapshot, None)

    def batalha_encerrada(self) -> bool:
        resultado = self.resultado_batalha_atual()
        return bool(resultado.get("encerrada", False))

    def resultado_batalha_atual(self) -> Dict[str, object]:
        resultado = self.SistemaBatalha.ResultadoRecebido if isinstance(getattr(self.SistemaBatalha, "ResultadoRecebido", None), dict) else {}
        return dict(resultado or {})

    def _sincronizar_respostas_servidor(self) -> None:
        resposta_inicio = self.Contexto.get("batalha_servidor_inicio")
        if isinstance(resposta_inicio, dict) and resposta_inicio is not self._ultima_resposta_inicio_servidor:
            self._ultima_resposta_inicio_servidor = resposta_inicio
            self.atualizar_estado_servidor(resposta_inicio)

        resposta_turno = self.Contexto.get("batalha_servidor_ultimo_envio")
        if isinstance(resposta_turno, dict) and resposta_turno is not self._ultima_resposta_turno_servidor:
            self._ultima_resposta_turno_servidor = resposta_turno
            self.atualizar_estado_servidor(resposta_turno)

    def atualizar(self, eventos, dt: float) -> None:
        self._sincronizar_respostas_servidor()
        self._leitor_logs.atualizar(dt)
        self.SistemaBatalha.atualizar(eventos, dt)

    def avancar_turno_basico(self) -> None:
        self._rodada_atual = int(self._rodada_atual) + 1

    def renderizar(self, tela, camera) -> None:
        self.Arena.renderizar(tela, camera)
        pokemon_hover = self.pokemon_no_ponto(pygame.mouse.get_pos(), camera)
        for poke in self.PokemonsReservaAliadosObj:
            reservado = float(self._provedor_reservas(poke)) if callable(self._provedor_reservas) else 0.0
            poke.renderizar(tela, camera, selecionado=(poke is self.PokemonSelecionado), hover=(poke is pokemon_hover), energia_reservada=reservado)
        for poke in self.PokemonsAliados:
            reservado = float(self._provedor_reservas(poke)) if callable(self._provedor_reservas) else 0.0
            poke.renderizar(tela, camera, selecionado=(poke is self.PokemonSelecionado), hover=(poke is pokemon_hover), energia_reservada=reservado)
        for poke in self.PokemonsInimigos:
            reservado = float(self._provedor_reservas(poke)) if callable(self._provedor_reservas) else 0.0
            poke.renderizar(tela, camera, selecionado=(poke is self.PokemonSelecionado), hover=(poke is pokemon_hover), energia_reservada=reservado)
