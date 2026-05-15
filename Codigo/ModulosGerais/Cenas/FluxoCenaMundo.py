"""Mixin de bootstrap, montagem e ciclo principal da CenaMundo."""

from copy import deepcopy

import pygame

from Codigo.ModulosGerais.Camera import CameraDungeon
from Codigo.ModulosMundo.ControladorMundo import ControladorMundo
from Codigo.ModulosMundo.ServicoMapaMundo import ServicoMapaMundo
from Codigo.ModulosGerais.ModuladorRegras import ModuladorRegras
from Codigo.ModulosGerais.Sonoridades import tile_mundo_atual
from Codigo.ModulosGerais.Server.ServerMundo import (
    desconectar_mundo,
    enviar_diffs_mundo,
    notificar_dano_dungeon_mundo,
    notificar_pokemon_derrotado_batalha_mundo,
    receber_pacotes_tick_mundo,
    consultar_chunks_mundo,
    coletar_mapa_mundo,
    enviar_evento_interacao_dungeon_mundo,
)
from Codigo.ModulosGerais.Server.ServerTerminal import buscar_mensagens_terminal, enviar_mensagem_terminal
from Codigo.Telas.Subtelas.SubtelaInventario import SubtelaInventario
from Codigo.Prefabs.Terminal import Terminal
from Codigo.Telas.Subtelas.SubtelaDialogo import SubtelaDialogo
from Codigo.Telas.Subtelas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha
from Codigo.ModulosGerais.GerenciadorPokemons import materializar_pokemon, gerar_bando_confronto
from Codigo.ModulosMundo.Geradores.portal import Portal


class FluxoCenaMundoMixin:
    def PrepararTransicaoAssincrona(self, JOGO) -> None:
        preparado = {
            "regras_mundo": {},
            "bootstrap": None,
            "chunks_bootstrap": None,
            "mapa_bootstrap": None,
            "erros": [],
        }
        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        regras_mundo = {}
        if link:
            try:
                regras_mundo = ModuladorRegras().coletar_regras(link) or {}
            except Exception as exc:
                preparado["erros"].append(f"falha_regras:{exc}")
            try:
                self._aplicar_sincronizacao_pos_batalha_pendente(JOGO, link)
            except Exception as exc:
                preparado["erros"].append(f"falha_sincronizacao:{exc}")
        dados = JOGO.INFO.get("PlayerDadosServer") if isinstance(JOGO.INFO.get("PlayerDadosServer"), dict) else {}
        posicao = dados.get("posicao") if isinstance(dados.get("posicao"), (list, tuple)) and len(dados.get("posicao")) == 2 else [0.0, 0.0]
        client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        bootstrap = None
        if link:
            try:
                bootstrap = receber_pacotes_tick_mundo(link, client_id, 0, posicao_camera=posicao, raio_chunks=4)
            except Exception as exc:
                preparado["erros"].append(f"falha_bootstrap_mundo:{exc}")

        chunks_bootstrap = None
        if link:
            try:
                chunks_bootstrap = consultar_chunks_mundo(link, client_id, posicao, raio_chunks=4)
            except Exception as exc:
                preparado["erros"].append(f"falha_bootstrap_chunks:{exc}")

        mapa_bootstrap = None
        if link and self._tem_exploracao_chunks(dados):
            try:
                import threading
                resultado = {"payload": None}

                def _worker_bootstrap_mapa():
                    try:
                        resultado["payload"] = coletar_mapa_mundo(link, client_id, posicao)
                    except Exception as exc:
                        resultado["payload"] = {"status": "erro", "mensagem": str(exc)}

                t = threading.Thread(target=_worker_bootstrap_mapa, daemon=True)
                t.start()
                t.join(timeout=6.0)
                if t.is_alive():
                    mapa_bootstrap = {"status": "erro", "mensagem": "timeout_bootstrap_mapa"}
                    preparado["erros"].append("timeout_bootstrap_mapa")
                else:
                    mapa_bootstrap = resultado.get("payload")
            except Exception as exc:
                mapa_bootstrap = {"status": "erro", "mensagem": str(exc)}
                preparado["erros"].append(f"falha_bootstrap_mapa:{exc}")
        elif link:
            preparado["erros"].append("mapa_bootstrap_pulado_primeira_entrada")

        preparado["regras_mundo"] = dict(regras_mundo or {})
        preparado["bootstrap"] = bootstrap if isinstance(bootstrap, dict) else None
        preparado["chunks_bootstrap"] = chunks_bootstrap if isinstance(chunks_bootstrap, dict) else None
        preparado["mapa_bootstrap"] = mapa_bootstrap if isinstance(mapa_bootstrap, dict) else None
        JOGO.INFO["MundoPreparadoTransicao"] = preparado

    def _aplicar_sincronizacao_pos_batalha_pendente(self, jogo, link: str | None) -> None:
        pendente = jogo.INFO.get("SincronizacaoPosBatalhaMundo") if isinstance(jogo.INFO.get("SincronizacaoPosBatalhaMundo"), dict) else None
        if not isinstance(pendente, dict) or not link:
            return
        player_dados = jogo.INFO.get("PlayerDadosServer") if isinstance(jogo.INFO.get("PlayerDadosServer"), dict) else {}
        inventario = pendente.get("inventario") if isinstance(pendente.get("inventario"), dict) else player_dados.get("inventario")
        perfil = pendente.get("perfil") if isinstance(pendente.get("perfil"), dict) else player_dados.get("perfil")
        player_id = int(player_dados.get("id", 0) or 0)
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        payload = {}
        if isinstance(inventario, dict):
            payload["inventario"] = deepcopy(inventario)
        if isinstance(perfil, dict):
            payload["perfil"] = deepcopy(perfil)
        if player_id > 0 and payload:
            enviar_diffs_mundo(
                link,
                client_id,
                [
                    {
                        "tipo": "update",
                        "objeto_id": int(player_id),
                        "payload": payload,
                    }
                ],
            )
        pokemon_ids = []
        for pid in list(pendente.get("pokemon_mundo_ids") or []):
            try:
                pid_int = int(pid or 0)
            except (TypeError, ValueError):
                continue
            if pid_int > 0 and pid_int not in pokemon_ids:
                pokemon_ids.append(pid_int)
        pokemon_mundo_id = int(pendente.get("pokemon_mundo_id", 0) or 0)
        if pokemon_mundo_id > 0 and pokemon_mundo_id not in pokemon_ids:
            pokemon_ids.append(pokemon_mundo_id)
        for pokemon_id in pokemon_ids:
            notificar_pokemon_derrotado_batalha_mundo(link, client_id, pokemon_id)
        # Essas chamadas passam pela rota de atualização, que sintetiza visibilidade.
        # Como ainda não existe um cliente de mundo ativo para aplicar o retorno, limpamos
        # o estado transitório antes do bootstrap real da cena.
        desconectar_mundo(link, client_id)
        jogo.INFO.pop("SincronizacaoPosBatalhaMundo", None)

    def _snapshot_player_atual(self, jogo) -> dict | None:
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is None:
            return None
        base = deepcopy(jogo.INFO.get("PlayerDadosServer")) if isinstance(jogo.INFO.get("PlayerDadosServer"), dict) else {}
        estado_base = base.get("estado") if isinstance(base.get("estado"), dict) else {}
        player_payload = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}) if self.ControladorMundo is not None else {}
        estado_payload = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        estado = {
            **estado_base,
            **estado_payload,
            "angulo": float(getattr(player, "AnguloOlhar", estado_payload.get("angulo", estado_base.get("angulo", 0.0))) or 0.0),
        }
        posicao = [float(player.Posicao[0]), float(player.Posicao[1])]
        inventario = getattr(player, "Inventario", None)
        perfil = getattr(player, "Perfil", None)
        slot_selecionado = int(getattr(inventario, "SlotSelecionado", base.get("slot_selecionado", 0)) or 0) if inventario is not None else int(base.get("slot_selecionado", 0) or 0)
        return {
            **base,
            "id": int(getattr(player, "Id", base.get("id", 0)) or 0),
            "nome": str(getattr(player, "Nome", base.get("nome", base.get("usuario", ""))) or ""),
            "usuario": str(getattr(player, "Nome", base.get("usuario", base.get("nome", ""))) or ""),
            "skin": str(getattr(player, "NomeSkin", base.get("skin", "1.png")) or "1.png"),
            "posicao": posicao,
            "dimensao_atual": str(estado.get("dimensao") or base.get("dimensao_atual", "Mundo") or "Mundo"),
            "estado": estado,
            "perfil": perfil.serializar() if perfil is not None and hasattr(perfil, "serializar") else deepcopy(base.get("perfil", {})),
            "inventario": inventario.serializar() if inventario is not None and hasattr(inventario, "serializar") else deepcopy(base.get("inventario", {})),
            "slot_selecionado": slot_selecionado,
        }

    def _iniciar_imunidade_combate_agora(self, JOGO) -> None:
        agora_ms = int(pygame.time.get_ticks())
        self._imune_combate_ate_ms = max(int(getattr(self, "_imune_combate_ate_ms", 0) or 0), agora_ms + 3000)
        JOGO.INFO["ImuneCombateAteMs"] = int(self._imune_combate_ate_ms)
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is not None:
            setattr(player, "ImuneCombateAteMs", max(int(getattr(player, "ImuneCombateAteMs", 0) or 0), int(self._imune_combate_ate_ms)))
            setattr(player, "ImuneCombateAtiva", True)

    def _ativar_imunidade_combate_pendente(self, JOGO) -> None:
        eventos = JOGO.INFO.get("EventosMundoPosTransicao")
        tem_eventos = isinstance(eventos, list) and bool(eventos)
        if not bool(getattr(self, "_imunidade_combate_pendente", False) or tem_eventos):
            return
        if JOGO.CenaAlvo is not None or self._portal_transicao is not None or float(getattr(JOGO, "Escuro", 0.0) or 0.0) > 0.0:
            return
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        if player is None:
            return
        self._imunidade_combate_pendente = False
        eventos = JOGO.INFO.pop("EventosMundoPosTransicao", []) if tem_eventos else []
        diffs = []
        for ev in eventos:
            if not isinstance(ev, dict):
                continue
            categoria = str(ev.get("categoria") or "").strip()
            payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
            if categoria:
                diffs.append({"tipo": "evento", "categoria": categoria, "payload": payload})
        diffs.append({"tipo": "evento", "categoria": "player_invulnerabilidade_pos_batalha", "objeto_id": int(getattr(player, "Id", 0) or 0), "payload": {"motivo": "pos_batalha"}})
        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        if link:
            resposta = enviar_diffs_mundo(link, str(JOGO.INFO.get("UsuarioLogado", "anon")), diffs)
            self._aplicar_resposta_mundo(resposta)
        self._iniciar_imunidade_combate_agora(JOGO)

    def _atualizar_imunidade_combate_visual(self, JOGO) -> bool:
        agora = int(pygame.time.get_ticks())
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        ate = max(
            int(getattr(self, "_imune_combate_ate_ms", 0) or 0),
            int(JOGO.INFO.get("ImuneCombateAteMs", 0) or 0),
            int(getattr(player, "ImuneCombateAteMs", 0) or 0) if player is not None else 0,
        )
        self._imune_combate_ate_ms = int(ate)
        JOGO.INFO["ImuneCombateAteMs"] = int(ate)
        if player is not None:
            setattr(player, "ImuneCombateAteMs", max(int(getattr(player, "ImuneCombateAteMs", 0) or 0), int(ate)))
            setattr(player, "ImuneCombateAtiva", bool(agora < ate))
        return bool(agora < ate)

    def _montar_mundo(self, JOGO):
        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        preparado = JOGO.INFO.pop("MundoPreparadoTransicao", None)
        regras_mundo = preparado.get("regras_mundo") if isinstance(preparado, dict) and isinstance(preparado.get("regras_mundo"), dict) else {}
        if not regras_mundo:
            regras_mundo = self.ModuladorRegras.coletar_regras(link) if link else {}
        if link:
            self._aplicar_sincronizacao_pos_batalha_pendente(JOGO, link)
        self.ModuladorRegras.definir_regras(regras_mundo or {})
        JOGO.INFO["RegrasMundo"] = dict(regras_mundo or {})

        gerais = regras_mundo.get("gerais") if isinstance(regras_mundo.get("gerais"), dict) else {}
        tile_px = int(gerais.get("camera_px_por_tile", 50))

        dados = JOGO.INFO.get("PlayerDadosServer") or {}
        self.Camera = CameraDungeon(JOGO.TELA.get_size(), entidade_main=None, tile_px=tile_px)
        self.ControladorMundo = ControladorMundo(jogo=JOGO, camera=self.Camera)
        player_local = self.ControladorMundo.montar_player_local(dados)
        self.EntidadeMain = player_local
        self.Camera.definir_main(self.EntidadeMain)
        self._centralizar_camera_no_player()
        self.ModuladorRegras.aplicar_em_cena_mundo(self, JOGO)

        usuario = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        self.Terminal = Terminal(
            pygame.Rect(14, 14, 520, 220),
            callback_enviar=lambda texto: enviar_mensagem_terminal(link, usuario, texto, contexto="mundo") if link else None,
            callback_buscar=lambda ultimo_id: buscar_mensagens_terminal(link, ultimo_id=ultimo_id, contexto="mundo") if link else {"status": "ok", "mensagens": []},
            autor_local=usuario,
        )
        self.Terminal.iniciar()

        if link:
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
            bootstrap = preparado.get("bootstrap") if isinstance(preparado, dict) and isinstance(preparado.get("bootstrap"), dict) else None
            chunks_bootstrap = preparado.get("chunks_bootstrap") if isinstance(preparado, dict) and isinstance(preparado.get("chunks_bootstrap"), dict) else None
            self.ControladorMundo.conectar(link, client_id, bootstrap_inicial=bootstrap, chunks_bootstrap=chunks_bootstrap)
            self.ServicoMapa = ServicoMapaMundo(JOGO, link, client_id)
            mapa_bootstrap = preparado.get("mapa_bootstrap") if isinstance(preparado, dict) and isinstance(preparado.get("mapa_bootstrap"), dict) else None
            try:
                self.ServicoMapa.preparar_bootstrap(mapa_bootstrap if str((mapa_bootstrap or {}).get("status", "ok")).lower() == "ok" else None)
            except Exception as exc:
                print(f"[CenaMundo] falha ao preparar serviço de mapa: {exc}")

    def _centralizar_camera_no_player(self) -> None:
        if self.Camera is None or self.EntidadeMain is None or not hasattr(self.EntidadeMain, "Posicao"):
            return
        half_w = (float(self.Camera.TamanhoTelaPx[0]) * 0.5) / max(1.0, float(self.Camera.TilePx))
        half_h = (float(self.Camera.TamanhoTelaPx[1]) * 0.5) / max(1.0, float(self.Camera.TilePx))
        self.Camera.PosicaoTiles = (float(self.EntidadeMain.Posicao[0]) - half_w, float(self.EntidadeMain.Posicao[1]) - half_h)
        normalizar = getattr(self.Camera, "_normalizar_posicao_limites", None)
        if callable(normalizar):
            normalizar()

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        if self._tela_creditos.ativa:
            self._tela_creditos.atualizar(EVENTOS, dt, JOGO)
            self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()
            self.ElementosHud.atualizar(dt)
            self.Camera.atualizar(dt)
            return EVENTOS
        if self._tela_morrer.ativa:
            self._tela_morrer.atualizar(EVENTOS, dt, JOGO)
            self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()
            self.ElementosHud.atualizar(dt)
            self.Camera.atualizar(dt)
            return EVENTOS
        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()

        bloqueio_gameplay = False
        player = self.ControladorMundo.player_local
        inventario_aberto = bool(
            player is not None
            and getattr(player, "Controle", None) is not None
            and bool(getattr(player.Controle, "InventarioAberto", False))
        )
        if self.Terminal is not None:
            EVENTOS = self.Terminal.processar_eventos(EVENTOS, bloquear_atalho_enter=inventario_aberto)
            bloqueio_gameplay = bool(self.Terminal.esta_digitando)

        ger = JOGO.GerenciadorSubtelas
        inventario_modal = ger.obter_por_tipo(SubtelaInventario)
        opcoes_modal = ger.obter_por_tipo(SubtelaOpcoes)
        dialogo_ativo = ger.contem(SubtelaDialogo)

        # Atalho temporario de teste dos creditos; remover quando houver gatilho definitivo.
        sem_modal_bloqueando = opcoes_modal is None and inventario_modal is None and not dialogo_ativo and not ger.ativa
        if self.TelaAtual is None and (not bloqueio_gameplay) and sem_modal_bloqueando:
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_c:
                    JOGO.INFO["CreditosAtivos"] = True
                    self._tela_creditos.abrir(JOGO.TELA.get_size(), ao_finalizar=lambda: self._finalizar_creditos(JOGO))
                    return EVENTOS

        if player is not None and getattr(player, "Controle", None) is not None:
            player.Controle.BloquearToggleInventario = inventario_modal.bloquear_toggle_inventario() if inventario_modal is not None else False
            if opcoes_modal is not None:
                player.Controle.InventarioAberto = False

        if opcoes_modal is None and self.TelaAtual not in ("Config", "Mapa"):
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    opcoes = SubtelaOpcoes()
                    opcoes.toggle(JOGO)
                    ger.abrir(opcoes)
                    opcoes_modal = opcoes
                    break

        if player is not None and getattr(player, "Controle", None) is not None:
            if player.Controle.InventarioAberto and inventario_modal is None:
                inventario_modal = ger.abrir(SubtelaInventario(player))
                inventario_modal.Ativo = True
            elif not player.Controle.InventarioAberto and inventario_modal is not None:
                ger.fechar(inventario_modal)

        dim_cliente_atual = str(self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo")
        dentro_estadio = dim_cliente_atual.startswith("Estadio")
        if self.ServicoMapa is not None:
            self.ServicoMapa.tick()

        bloqueio_mapa = bloqueio_gameplay or (opcoes_modal is not None) or dialogo_ativo or inventario_modal is not None or self.TelaAtual == "Config" or ger.ativa
        if self.TelaAtual is None and not bloqueio_mapa and not dentro_estadio:
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
                    estado_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}).get("estado", {}) if player is not None else {}
                    dim_player = str((estado_player or {}).get("dimensao") or dim_cliente_atual)
                    if dim_player.startswith("Dungeon_"):
                        layout = self.ControladorMundo.Leitor.MetaMundo.get("layout_dungeon") if isinstance(self.ControladorMundo.Leitor.MetaMundo, dict) else {}
                        self.TelaMapa.abrir_dungeon(JOGO, layout, (estado_player or {}).get("estado_dungeon", {}))
                        self.TelaAtual = "Mapa"
                    elif self.ServicoMapa is not None:
                        pos_player_mundo = self.ServicoMapa.gerenciador.posicao_player_mundo(estado_player, tuple(getattr(player, "Posicao", (0.0, 0.0)))) if player is not None else tuple(getattr(player, "Posicao", (0.0, 0.0)))
                        self.TelaMapa.abrir(JOGO, self.ServicoMapa, pos_player_mundo)
                        self.TelaAtual = "Mapa"
                    break

        transicao_global = float(getattr(JOGO, "Escuro", 0.0) or 0.0) > 0.0
        player_bloqueado = (self.TelaAtual == "Mapa") or bloqueio_gameplay or (opcoes_modal is not None) or self.TelaAtual == "Config" or dialogo_ativo or self._portal_transicao is not None or transicao_global
        self._ativar_imunidade_combate_pendente(JOGO)
        imune_combate = self._atualizar_imunidade_combate_visual(JOGO)
        self.ControladorMundo.atualizar_frame(EVENTOS, dt, bloqueio_gameplay=player_bloqueado)
        self._atualizar_checkpoint_seguro()
        self._aplicar_morte_se_necessario(JOGO)
        if self._tela_morrer.ativa:
            return EVENTOS

        if self._abrir_dialogo_pos_batalha_pendente(JOGO):
            return EVENTOS

        if JOGO.CenaAlvo is None and (not player_bloqueado) and imune_combate:
            self.ControladorMundo.Player.consumir_colisao_pokemon()
        elif JOGO.CenaAlvo is None and (not player_bloqueado):
            colisao_pokemon = self.ControladorMundo.Player.consumir_colisao_pokemon()
            if isinstance(colisao_pokemon, dict):
                estado_colisao = colisao_pokemon.get("estado") if isinstance(colisao_pokemon.get("estado"), dict) else {}
                tipo_batalha = str(estado_colisao.get("tipo_batalha") or estado_colisao.get("comportamento_mundo") or estado_colisao.get("comportamento") or "confronto").strip().lower()
                if tipo_batalha not in {"servo", "boss"}:
                    tipo_batalha = "confronto"
                server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
                link = server.get("ip")
                client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
                pokemon_mundo_id = int(colisao_pokemon.get("id", colisao_pokemon.get("Id", colisao_pokemon.get("ID", 0))) or 0)
                inventario = getattr(player, "Inventario", None)
                times = deepcopy(list(getattr(inventario, "TimesPokemon", []) or [])) if inventario is not None else []
                pokemons_jogador = deepcopy(list(getattr(inventario, "Pokemons", []) or [])) if inventario is not None else []
                indice_time, time_escolhido = InicializadorBatalha.escolher_time_confronto_com_indice(times, pokemons_jogador, slots_por_time=6)
                if not InicializadorBatalha.time_tem_pokemon_vivo(time_escolhido):
                    if tipo_batalha in {"servo", "boss"} and link:
                        notificar_dano_dungeon_mundo(link, client_id, "colisao_sem_pokemon", pokemon_mundo_id)
                    return EVENTOS
                posicao_referencia_mundo = colisao_pokemon.get("posicao") if isinstance(colisao_pokemon.get("posicao"), (list, tuple)) and len(colisao_pokemon.get("posicao")) == 2 else list(getattr(player, "Posicao", [0.0, 0.0]))
                regras_mundo = JOGO.INFO.get("RegrasMundo") if isinstance(JOGO.INFO.get("RegrasMundo"), dict) else {}
                batalha = regras_mundo.get("batalha") if isinstance(regras_mundo.get("batalha"), dict) else {}
                pokemon_materializado = materializar_pokemon(dict(colisao_pokemon))
                if isinstance(pokemon_materializado, dict):
                    est_mat = pokemon_materializado.get("estado") if isinstance(pokemon_materializado.get("estado"), dict) else pokemon_materializado
                    if isinstance(est_mat, dict):
                        est_mat["capturavel"] = False if tipo_batalha in {"servo", "boss"} else est_mat.get("capturavel", True)
                        est_mat["tipo_batalha"] = tipo_batalha
                pokemons_inimigo = [pokemon_materializado] if tipo_batalha in {"servo", "boss"} else gerar_bando_confronto(pokemon_materializado, max_extras=5)
                contexto = {
                    "batalha": dict(batalha),
                    "pokemon_colisao": dict(colisao_pokemon),
                    "pokemon_mundo_id": pokemon_mundo_id,
                    "pokemons_inimigo": deepcopy(pokemons_inimigo),
                    "times_jogador": times,
                    "pokemons_jogador": pokemons_jogador,
                    "time_jogador": deepcopy(time_escolhido),
                    "time_jogador_indice": int(indice_time),
                    "perfil_jogador": player.Perfil.serializar() if getattr(player, "Perfil", None) is not None else {},
                    "tipo": tipo_batalha,
                    "tipo_batalha": tipo_batalha,
                    "origem": [0.0, 0.0],
                    "centro": [40.0, 20.0],
                    "largura": 80,
                    "altura": 40,
                    "arena_largura": 40,
                    "arena_altura": 20,
                    "tile_bioma": tile_mundo_atual(self),
                    "posicao_referencia_mundo": [float(posicao_referencia_mundo[0]), float(posicao_referencia_mundo[1])],
                    "server_ip": str(link or ""),
                    "client_id": client_id,
                }
                JOGO.INFO["CombateContexto"] = contexto
                JOGO.CenaAlvo = "Combate"
                return EVENTOS

        if (not player_bloqueado) and player is not None and getattr(player, "Controle", None) is not None:
            player_payload = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {})
            estado_player = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_f:
                    alvo = self.ControladorMundo.Objetos.alvo_interagivel_atual(
                        pos_player=tuple(player.Posicao),
                        dimensao_player=str(estado_player.get("dimensao") or self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo"),
                        estadio_atual_id=int(estado_player.get("estadio_atual_id", 0) or 0),
                    )
                    if isinstance(alvo, dict) and str(alvo.get("tipo") or "") == "npc":
                        npc_obj = dict(alvo.get("npc", {}))
                        estado = npc_obj.get("estado") if isinstance(npc_obj.get("estado"), dict) else {}
                        inter = estado.get("interacao") if isinstance(estado.get("interacao"), dict) else {}
                        if not bool(inter.get("ativa", False)):
                            self._solicitar_interacao_npc(JOGO, npc_obj)
                    elif isinstance(alvo, dict) and str(alvo.get("tipo") or "") == "dungeon_entrada":
                        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
                        link = server.get("ip")
                        payload_estrutura = alvo.get("estrutura") if isinstance(alvo.get("estrutura"), dict) else {}
                        payload = Portal.payload_dungeon_entrada(payload_estrutura, player.Posicao)
                        self._iniciar_transicao_portal(lambda: self._aplicar_resposta_mundo(enviar_evento_interacao_dungeon_mundo(link, str(JOGO.INFO.get("UsuarioLogado", "anon")), payload)))
                    elif isinstance(alvo, dict) and str(alvo.get("tipo") or "") == "dungeon_saida":
                        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
                        link = server.get("ip")
                        payload = Portal.payload_dungeon_saida(player.Posicao)
                        self._iniciar_transicao_portal(lambda: self._aplicar_resposta_mundo(enviar_evento_interacao_dungeon_mundo(link, str(JOGO.INFO.get("UsuarioLogado", "anon")), payload)))
                    break
        self._processar_estado_dialogo_npc(JOGO)
        self.ElementosHud.atualizar(dt)
        self.Camera.atualizar(dt)
        return EVENTOS
