from __future__ import annotations

from typing import Dict, List

import pygame

from Codigo.Geradores.PokemonBatalha import PokemonBatalha
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha, pontos_lados_arena
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
        self.Jogador = PlayerBatalha("jogador", max_ativos=self._MAX_ATIVOS)
        self.Inimigo = PlayerBatalha("inimigo", max_ativos=self._MAX_ATIVOS)
        self.PokemonSelecionado: PokemonBatalha | None = None
        self._provedor_reservas = None
        self._rodada_atual = 1
        self._ultima_resposta_inicio_servidor = None
        self._ultima_resposta_turno_servidor = None
        self._inicializar_times()

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

    def _inicializar_times(self) -> None:
        init = InicializadorBatalha(self.Contexto)
        batalha = init.inicializar()
        self.Contexto["batalha_inicializada"] = batalha
        if hasattr(self.SistemaBatalha, "iniciar_batalha_server_async"):
            self.SistemaBatalha.iniciar_batalha_server_async(batalha)

        centro = self.Contexto.get("centro") if isinstance(self.Contexto.get("centro"), (list, tuple)) and len(self.Contexto.get("centro")) == 2 else [40.0, 20.0]
        arena_w = float(self.Contexto.get("arena_largura", 40) or 40)
        arena_h = float(self.Contexto.get("arena_altura", 20) or 20)
        self.Jogador.TimeCompleto = [poke for poke in batalha.get("jogador", []) if isinstance(poke, dict)]
        self.Inimigo.TimeCompleto = [poke for poke in batalha.get("inimigo", []) if isinstance(poke, dict)]
        aliados_ativos = self.Jogador.preparar_slots()
        inimigos_ativos = self.Inimigo.preparar_slots()
        self.PokemonsReservaAliados = list(self.Jogador.PokemonsReserva)
        self.PokemonsReservaInimigos = list(self.Inimigo.PokemonsReserva)
        pos_aliados, pos_inimigos = pontos_lados_arena(
            centro=(float(centro[0]), float(centro[1])),
            largura=arena_w,
            altura=arena_h,
            total_aliados=len(aliados_ativos),
            total_inimigos=len(inimigos_ativos),
        )

        self.PokemonsAliados = [PokemonBatalha(poke, posicao=pos_aliados[i], lado="jogador", regras=self.Contexto) for i, poke in enumerate(aliados_ativos) if i < len(pos_aliados)]
        self.PokemonsInimigos = [PokemonBatalha(poke, posicao=pos_inimigos[i], lado="inimigo", regras=self.Contexto) for i, poke in enumerate(inimigos_ativos) if i < len(pos_inimigos)]
        self.PokemonsReservaAliadosObj = self._criar_reservas_visuais(
            self.PokemonsReservaAliados,
            centro=(float(centro[0]), float(centro[1])),
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
            reserva = PokemonBatalha(poke, posicao=pos, lado="jogador", regras=self.Contexto)
            reserva.EmReserva = True
            saida.append(reserva)
        return saida

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

    def definir_provedor_reservas(self, provedor) -> None:
        self._provedor_reservas = provedor

    def selecionar_slot_aliado(self, indice: int) -> PokemonBatalha | None:
        idx = int(indice)
        if idx < 0 or idx >= len(self.PokemonsAliados):
            return self.PokemonSelecionado
        self.PokemonSelecionado = self.PokemonsAliados[idx]
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

    def atualizar_estado_servidor(self, retorno: Dict[str, object] | None = None) -> None:
        if not isinstance(retorno, dict):
            return
        log = retorno.get("log") if isinstance(retorno.get("log"), dict) else {}
        resultado = self.SistemaBatalha.resolver_estado_recebido(retorno, log)
        if not resultado:
            return

        self.SistemaBatalha.atualizar(dados_servidor=resultado, log_servidor=log if isinstance(log, dict) else None)
        self._rodada_atual = max(1, int(self.SistemaBatalha.TurnoAtual or self._rodada_atual))

        selecionado_uid = self._uid_pokemon(self.PokemonSelecionado)
        existentes = self._mapa_existentes()
        centro = self.Contexto.get("centro") if isinstance(self.Contexto.get("centro"), (list, tuple)) and len(self.Contexto.get("centro")) == 2 else [40.0, 20.0]
        arena_w = float(self.Contexto.get("arena_largura", 40) or 40)
        arena_h = float(self.Contexto.get("arena_altura", 20) or 20)

        dados_jogador = resultado.get("jogador") if isinstance(resultado.get("jogador"), dict) else {}
        dados_inimigo = resultado.get("inimigo") if isinstance(resultado.get("inimigo"), dict) else {}
        ativos_jogador = [dict(item) for item in list(dados_jogador.get("ativos") or []) if isinstance(item, dict)]
        ativos_inimigo = [dict(item) for item in list(dados_inimigo.get("ativos") or []) if isinstance(item, dict)]
        reservas_jogador = [dict(item) for item in list(dados_jogador.get("reservas") or []) if isinstance(item, dict)]
        reservas_inimigo = [dict(item) for item in list(dados_inimigo.get("reservas") or []) if isinstance(item, dict)]

        pos_aliados, pos_inimigos = pontos_lados_arena(
            centro=(float(centro[0]), float(centro[1])),
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
