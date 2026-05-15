"""Mixin de eventos e acoes de gameplay da CenaMundo."""

from copy import deepcopy

import pygame

from Codigo.ModulosGerais.Server.ServerMundo import (
    enviar_diffs_mundo,
    finalizar_interacao_npc_mundo,
    iniciar_interacao_npc_mundo,
)
from Codigo.Telas.Subtelas.SubtelaDialogo import SubtelaDialogo
from Codigo.Telas.Subtelas.SubtelaPreBatalha import SubtelaPreBatalha
from Codigo.ModulosMundo.Geradores.Estadio import EstadioInterno
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha
from Codigo.ModulosGerais.Sonoridades import tile_mundo_atual


class EventosCenaMundoMixin:
    def _iniciar_transicao_portal(self, acao):
        if self._portal_transicao is not None or not callable(acao):
            return
        jogo = getattr(self, "_jogo_ref", None)
        if jogo is not None:
            jogo.Escuro = 0
        self._portal_transicao = {"fase": "fechando", "acao": acao, "executou": False}

    def _solicitar_interacao_npc(self, jogo, npc_obj: dict) -> None:
        if jogo.GerenciadorSubtelas.contem(SubtelaDialogo):
            return
        player = self.ControladorMundo.player_local
        if player is None:
            return
        server = jogo.INFO.get("ServerSelecionado") if isinstance(jogo.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        npc_id = int(npc_obj.get("id", 0) or 0)
        if link and npc_id > 0:
            resposta = iniciar_interacao_npc_mundo(link, client_id, npc_id)
            pacotes = resposta.get("pacotes", []) if isinstance(resposta, dict) and isinstance(resposta.get("pacotes"), list) else []
            for pacote in pacotes:
                if isinstance(pacote, dict):
                    self.ControladorMundo.Pacotes._distribuir_pacote_tick(pacote)
        self._npc_interacao_pendente = {"npc_id": npc_id, "desde_ms": int(pygame.time.get_ticks())}

    def _abrir_dialogo_npc_autoritativo(self, jogo, npc_obj: dict) -> None:
        player = self.ControladorMundo.player_local
        if player is None:
            return
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        npc_id = int(npc_obj.get("id", 0) or 0)
        self._npc_interacao_id = npc_id
        self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
        jogo.GerenciadorSubtelas.abrir(SubtelaDialogo(
            player_nome=str(getattr(player, "Nome", "") or client_id),
            player_skin=str(getattr(player, "NomeSkin", "S1.png")),
            npc_payload=npc_obj,
            ao_encerrar=lambda: self._finalizar_dialogo_npc(jogo),
            ao_iniciar_batalha=lambda contexto: self._iniciar_batalha_por_dialogo(jogo, contexto),
            ao_registrar_ganho=self.ElementosHud.registrar_ganho,
            ator_local=player,
        ))

    def _iniciar_batalha_por_dialogo(self, jogo, contexto_dialogo: dict) -> None:
        player = self.ControladorMundo.player_local
        inventario = getattr(player, "Inventario", None)
        times = list(getattr(inventario, "TimesPokemon", []) or []) if inventario is not None else []
        npc_ctx = dict(contexto_dialogo or {})
        times_validos = InicializadorBatalha.times_completos_por_tipo(times, npc_ctx.get("npc_estadio"), slots_por_time=6)
        if not times_validos:
            return

        player_payload = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}) if player is not None else {}
        estado_p = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        dimensao = str(estado_p.get("dimensao") or "Mundo")
        estadio_atual_id = int(estado_p.get("estadio_atual_id", 0) or 0)

        regras_mundo = jogo.INFO.get("RegrasMundo") if isinstance(jogo.INFO.get("RegrasMundo"), dict) else {}
        pokemons_regras = regras_mundo.get("pokemons") if isinstance(regras_mundo.get("pokemons"), dict) else {}
        contexto_base = {
            "origem": [0.0, 0.0],
            "centro": [40.0, 20.0],
            "largura": 80,
            "altura": 40,
            "arena_largura": 40,
            "arena_altura": 20,
            "tiles": [],
            "estruturas": [],
            "combate_pokemon_tamanho_diametro_base_tiles": float(pokemons_regras.get("combate_tamanho_diametro_base_tiles", 1.0)),
            "combate_pokemon_tamanho_incremento_por_escala": float(pokemons_regras.get("combate_tamanho_incremento_por_escala", 0.15)),
        }

        if dimensao != "Mundo":
            estadio_payload = self.ControladorMundo.Objetos.EstadiosPorId.get(estadio_atual_id, {})
            estado_estadio = estadio_payload.get("estado") if isinstance(estadio_payload.get("estado"), dict) else {}
            contexto_base = EstadioInterno.contexto_batalha(estado_estadio)

        def _comecar_com_time(time_escolhido: dict):
            indice_time = next((i for i, time_existente in enumerate(times_validos) if time_existente == time_escolhido), 0)
            times_npc = [t for t in list(npc_ctx.get("times_pokemon") or []) if isinstance(t, dict)]
            batalha_numero = max(1, int(npc_ctx.get("batalha_numero", 1) or 1))
            time_npc = deepcopy(times_npc[min(len(times_npc) - 1, batalha_numero - 1)]) if times_npc else {}
            pokemons_npc = list(time_npc.get("Slots") or time_npc.get("slots") or [])
            pokemons_jogador = deepcopy(list(getattr(inventario, "Pokemons", []) or [])) if inventario is not None else []
            regras_mundo = jogo.INFO.get("RegrasMundo") if isinstance(jogo.INFO.get("RegrasMundo"), dict) else {}
            batalha = regras_mundo.get("batalha") if isinstance(regras_mundo.get("batalha"), dict) else {}
            jogo.INFO["CombateContexto"] = {
                **contexto_base,
                "batalha": dict(batalha),
                "tipo": "treinador",
                "npc_contexto": npc_ctx,
                "times_jogador": deepcopy(list(times_validos)),
                "pokemons_jogador": pokemons_jogador,
                "time_jogador": deepcopy(dict(time_escolhido or {})),
                "time_jogador_indice": int(indice_time),
                "perfil_jogador": player.Perfil.serializar() if player is not None and getattr(player, "Perfil", None) is not None else {},
                "time_inimigo": time_npc,
                "pokemons_inimigo": deepcopy(pokemons_npc),
                "tile_bioma": tile_mundo_atual(self),
                "posicao_referencia_mundo": [float(player.Posicao[0]), float(player.Posicao[1])] if player is not None else [0.0, 0.0],
                "server_ip": str((jogo.INFO.get("ServerSelecionado") or {}).get("ip") or ""),
                "client_id": str(jogo.INFO.get("UsuarioLogado", "anon")),
            }
            jogo.CenaAlvo = "Combate"

        if jogo.GerenciadorSubtelas.obter_por_tipo(SubtelaPreBatalha) is None:
            jogo.GerenciadorSubtelas.abrir(SubtelaPreBatalha(times=times_validos, ao_confirmar=_comecar_com_time))

    def _finalizar_creditos(self, JOGO) -> None:
        JOGO.INFO.pop("CreditosAtivos", None)
        JOGO.INFO["MenuTelaInicial"] = "MenuPrincipal"
        JOGO.Escuro = 100
        JOGO.CenaAlvo = "Menu"

    def _processar_estado_dialogo_npc(self, jogo) -> None:
        if jogo.GerenciadorSubtelas.contem(SubtelaDialogo):
            return
        pend = dict(self._npc_interacao_pendente or {})
        npc_id = int(pend.get("npc_id", 0) or 0)
        if npc_id <= 0:
            return
        obj = self.ControladorMundo.Objetos.ObjetosPorId.get(npc_id)
        if not isinstance(obj, dict):
            return
        estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
        inter = estado.get("interacao") if isinstance(estado.get("interacao"), dict) else {}
        dono = str(inter.get("cliente", "") or "")
        ativo = bool(inter.get("ativa", False))
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        if ativo and dono == client_id:
            confirmado_ms = int(pend.get("confirmado_ms", 0) or 0)
            if confirmado_ms <= 0:
                self._npc_interacao_pendente = {"npc_id": npc_id, "desde_ms": int(pend.get("desde_ms", 0) or 0), "confirmado_ms": int(pygame.time.get_ticks())}
                return
            if int(pygame.time.get_ticks()) - confirmado_ms < 220:
                return
            self._abrir_dialogo_npc_autoritativo(jogo, obj)
            return
        if ativo and dono != client_id:
            self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
            return
        if int(pygame.time.get_ticks()) - int(pend.get("desde_ms", 0) or 0) > 1800:
            self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}

    def _abrir_dialogo_pos_batalha_pendente(self, jogo) -> bool:
        if jogo.GerenciadorSubtelas.contem(SubtelaDialogo) or jogo.GerenciadorSubtelas.contem(SubtelaPreBatalha):
            return False
        pend = jogo.INFO.get("DialogoPosBatalha") if isinstance(jogo.INFO.get("DialogoPosBatalha"), dict) else None
        if not isinstance(pend, dict):
            return False
        npc_id = int(pend.get("npc_id", 0) or 0)
        if npc_id <= 0:
            jogo.INFO.pop("DialogoPosBatalha", None)
            return False
        npc_obj = self.ControladorMundo.Objetos.ObjetosPorId.get(npc_id)
        if not isinstance(npc_obj, dict):
            return False
        npc_payload = deepcopy(npc_obj)
        npc_payload["inicio_dialogo"] = str(pend.get("inicio_dialogo") or "")
        npc_payload["resultado_batalha"] = str(pend.get("resultado_batalha") or "")
        jogo.INFO.pop("DialogoPosBatalha", None)
        self._centralizar_camera_no_player()
        self._abrir_dialogo_npc_autoritativo(jogo, npc_payload)
        return True

    def _atualizar_checkpoint_seguro(self):
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        controle = getattr(player, "Controle", None) if player is not None else None
        if player is None or controle is None:
            return
        dim = "Mundo"
        if self.ControladorMundo is not None and getattr(self.ControladorMundo, "Objetos", None) is not None:
            dim = str(self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo")
        if dim != "Mundo":
            return
        leitor = getattr(self.ControladorMundo, "Leitor", None)
        if leitor is None:
            return
        tamanho = max(1, int(getattr(leitor, "TamanhoChunkBlocos", 10)))
        px, py = float(player.Posicao[0]), float(player.Posicao[1])
        cx, cy = int(px // tamanho), int(py // tamanho)
        normalizar = getattr(leitor, "_normalizar_chunk_referencia", None)
        if callable(normalizar):
            cx, cy = normalizar((cx, cy))
        chunk = (getattr(leitor, "Chunks", {}) or {}).get((cx, cy))
        if not isinstance(chunk, list) or not chunk:
            return
        lx = int(px) % tamanho
        ly = int(py) % tamanho
        try:
            if int(chunk[ly][lx]) == 0:
                return
        except (IndexError, TypeError, ValueError):
            return
        checkpoint = {"chave": (cx, cy), "posicao": [float(px), float(py)], "grid": [list(linha) for linha in chunk], "dimensao": dim}
        self._ultimo_chunk_seguro = checkpoint
        self._ultimo_chunk_seguro_mundo = checkpoint

    def _aplicar_morte_se_necessario(self, jogo):
        if self._tela_morrer.ativa:
            return
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is None:
            return
        payload_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}) if self.ControladorMundo is not None else {}
        estado_player = payload_player.get("estado") if isinstance(payload_player.get("estado"), dict) else {}
        game_over_server = bool(estado_player.get("morto", False) or estado_player.get("game_over", False) or getattr(player, "GameOverServidor", False))
        if game_over_server:
            self._definir_player_morto(True)
            self._tela_morrer.abrir(jogo.TELA.get_size(), ao_ressurgir=lambda: self._ressurgir_player(jogo), ao_menu=lambda: self._voltar_menu(jogo))
            return
        controle = getattr(player, "Controle", None) if player is not None else None
        perfil = getattr(player, "Perfil", None) if player is not None else None
        if controle is None or perfil is None:
            return
        tile_atual = getattr(controle, "tile_atual_cache", lambda: None)()
        if tile_atual is None and callable(getattr(controle, "_tile_atual", None)):
            tile_atual = controle._tile_atual()
        try:
            em_agua_funda = int(tile_atual) == 0
        except (TypeError, ValueError):
            em_agua_funda = False
        dimensao = str(self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo") if self.ControladorMundo is not None and getattr(self.ControladorMundo, "Objetos", None) is not None else "Mundo"
        if dimensao == "Mundo" and em_agua_funda and float(getattr(perfil, "Stamina", 0.0)) <= 0.001:
            self._definir_player_morto(True)
            self._enviar_diff_morte(jogo)
            self._tela_morrer.abrir(jogo.TELA.get_size(), ao_ressurgir=lambda: self._ressurgir_player(jogo), ao_menu=lambda: self._voltar_menu(jogo))

    def _definir_player_morto(self, morto: bool):
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is None:
            return
        setattr(player, "Morto", bool(morto))
        if not bool(morto):
            setattr(player, "GameOverServidor", False)
            setattr(player, "MotivoMorteServidor", "")
            setattr(player, "AnimacaoQuedaAteMs", 0)
            setattr(player, "SobreBuraco", False)
        oid = int(getattr(player, "Id", 0) or 0)
        atual = self.ControladorMundo.Objetos.ObjetosPorId.get(oid, {})
        estado = atual.get("estado") if isinstance(atual.get("estado"), dict) else {}
        estado["morto"] = bool(morto)
        estado["game_over"] = bool(morto)
        estado["queda_buraco"] = False if not bool(morto) else bool(estado.get("queda_buraco", False))
        if not bool(morto):
            estado.pop("estado_dungeon", None)
        self.ControladorMundo.Objetos.aplicar_diff({"tipo": "update", "objeto_id": oid, "payload": {"estado": estado}})

    def _enviar_diff_morte(self, jogo):
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is None:
            return
        server = jogo.INFO.get("ServerSelecionado") if isinstance(jogo.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        if not link:
            return
        payload = {"motivo": "agua_funda_stamina_zero"}
        checkpoint = self._ultimo_chunk_seguro_mundo if isinstance(self._ultimo_chunk_seguro_mundo, dict) else {}
        if isinstance(checkpoint.get("chave"), (list, tuple)) and len(checkpoint.get("chave")) == 2:
            payload["checkpoint_mundo"] = {"chunk": [int(checkpoint["chave"][0]), int(checkpoint["chave"][1])], "posicao": list(checkpoint.get("posicao") or [])}
        enviar_diffs_mundo(link, str(jogo.INFO.get("UsuarioLogado", "anon")), [{"tipo": "evento", "categoria": "player_morreu", "objeto_id": int(getattr(player, "Id", 0) or 0), "payload": payload}])

    def _aplicar_resposta_mundo(self, resposta):
        pacotes = resposta.get("pacotes", []) if isinstance(resposta, dict) and isinstance(resposta.get("pacotes"), list) else []
        distribuir = getattr(getattr(self.ControladorMundo, "Pacotes", None), "_distribuir_pacote_tick", None) if self.ControladorMundo is not None else None
        if not callable(distribuir):
            return
        for pacote in pacotes:
            if isinstance(pacote, dict):
                distribuir(pacote)

    def _ressurgir_player(self, jogo):
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is None:
            return
        server = jogo.INFO.get("ServerSelecionado") if isinstance(jogo.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        if link:
            resposta = enviar_diffs_mundo(link, str(jogo.INFO.get("UsuarioLogado", "anon")), [{"tipo": "evento", "categoria": "player_ressurgir", "objeto_id": int(getattr(player, "Id", 0) or 0), "payload": {"motivo": "pedido_cliente"}}])
            self._aplicar_resposta_mundo(resposta)
        self._tela_morrer.fechar()

    def _voltar_menu(self, jogo):
        jogo.CenaAlvo = "Menu"

    def _finalizar_dialogo_npc(self, jogo) -> None:
        npc_id = int(self._npc_interacao_id or 0)
        self._npc_interacao_id = 0
        self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
        server = jogo.INFO.get("ServerSelecionado") if isinstance(jogo.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        if link and npc_id > 0:
            finalizar_interacao_npc_mundo(link, client_id, npc_id)
