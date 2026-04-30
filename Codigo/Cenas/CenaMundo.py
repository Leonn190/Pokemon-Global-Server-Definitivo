from copy import deepcopy

import pygame

from Codigo.ModulosGerais.Camera import Camera
from Codigo.ModulosMundo.ControladorMundo import ControladorMundo
from Codigo.ModulosMundo.ElementosHudMundo import ElementosHudMundo
from Codigo.ModulosMundo.ServicoMapaMundo import ServicoMapaMundo
from Codigo.Telas.Telas.TelaMapa import TelaMapa
from Codigo.ModulosGerais.EfeitosTela import FecharIris, AbrirIris
from Codigo.ModulosGerais.FiltroCamera import FiltroCamera
from Codigo.ModulosGerais.ModuladorRegras import ModuladorRegras
from Codigo.ModulosGerais.Sonoridades import tile_mundo_atual
from Codigo.ModulosGerais.Auxiliares import bioma_visual_por_tile
from Codigo.Telas.Subtelas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Telas.Telas.TelaConfig import TelaConfig, ResetTelaConfig
from Codigo.ModulosGerais.Server.ServerMundo import (
    desconectar_mundo,
    enviar_diffs_mundo,
    finalizar_interacao_npc_mundo,
    iniciar_interacao_npc_mundo,
    notificar_pokemon_derrotado_batalha_mundo,
    receber_pacotes_tick_mundo,
    consultar_chunks_mundo,
    coletar_mapa_mundo,
)
from Codigo.ModulosGerais.Server.ServerTerminal import buscar_mensagens_terminal, enviar_mensagem_terminal
from Codigo.Telas.Subtelas.SubtelaInventario import SubtelaInventario
from Codigo.Prefabs.Terminal import Terminal
from Codigo.Telas.Subtelas.SubtelaDialogo import SubtelaDialogo
from Codigo.Telas.Subtelas.SubtelaPreBatalha import SubtelaPreBatalha
from Codigo.Geradores.Estadio import EstadioInterno
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha
from Codigo.Prefabs.Texto import Texto
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_cliente_mundo


class CenaMundo:
    @staticmethod
    def _tem_exploracao_chunks(dados_player: dict) -> bool:
        exploracao = dados_player.get("exploracao_chunks") if isinstance(dados_player, dict) else {}
        mundo = exploracao.get("Mundo") if isinstance(exploracao, dict) and isinstance(exploracao.get("Mundo"), dict) else {}
        return any(isinstance(valores, (list, tuple, set)) and len(valores) > 0 for valores in mundo.values())

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
        player_id = int(player_dados.get("id", 0) or 0)
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        if player_id > 0 and isinstance(inventario, dict):
            enviar_diffs_mundo(
                link,
                client_id,
                [
                    {
                        "tipo": "update",
                        "objeto_id": int(player_id),
                        "payload": {
                            "inventario": deepcopy(inventario),
                        },
                    }
                ],
            )
        pokemon_mundo_id = int(pendente.get("pokemon_mundo_id", 0) or 0)
        if pokemon_mundo_id > 0:
            notificar_pokemon_derrotado_batalha_mundo(link, client_id, pokemon_mundo_id)
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
        inventario = getattr(player, "Inventario", None)
        perfil = getattr(player, "Perfil", None)
        slot_selecionado = int(getattr(inventario, "SlotSelecionado", base.get("slot_selecionado", 0)) or 0) if inventario is not None else int(base.get("slot_selecionado", 0) or 0)
        return {
            **base,
            "id": int(getattr(player, "Id", base.get("id", 0)) or 0),
            "nome": str(getattr(player, "Nome", base.get("nome", base.get("usuario", ""))) or ""),
            "usuario": str(getattr(player, "Nome", base.get("usuario", base.get("nome", ""))) or ""),
            "skin": str(getattr(player, "NomeSkin", base.get("skin", "1.png")) or "1.png"),
            "posicao": [float(player.Posicao[0]), float(player.Posicao[1])],
            "estado": estado,
            "perfil": perfil.serializar() if perfil is not None and hasattr(perfil, "serializar") else deepcopy(base.get("perfil", {})),
            "inventario": inventario.serializar() if inventario is not None and hasattr(inventario, "serializar") else deepcopy(base.get("inventario", {})),
            "slot_selecionado": slot_selecionado,
        }

    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Mundo"

        self.Camera = None
        self.ControladorMundo = None
        self.EntidadeMain = None
        self.ElementosHud = ElementosHudMundo()
        self._desconectado = False
        self.TelaAtual = None
        self.ServicoMapa = None
        self.TelaMapa = TelaMapa()
        self.Terminal = None
        self._npc_interacao_id = 0
        self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
        self._texto_estadio = Texto("", style={"size": 22, "align": "center", "outline": True, "color": (230, 236, 245)})
        agora_ms = int(pygame.time.get_ticks())
        self._imune_combate_ate_ms = max(int(JOGO.INFO.get("ImuneCombateAteMs", 0) or 0), agora_ms + 3000)
        JOGO.INFO["ImuneCombateAteMs"] = int(self._imune_combate_ate_ms)
        self._filtro_camera = FiltroCamera()
        self.ModuladorRegras = ModuladorRegras()

        self._montar_mundo(JOGO)

        tela_sobreposta = JOGO.INFO.pop("MundoTelaSobreposta", None)
        if tela_sobreposta == "Config":
            ResetTelaConfig()
            self.TelaAtual = "Config"

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = tela

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
        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=None, tile_px=tile_px)
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

        dentro_estadio = str(self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo") != "Mundo"
        if self.ServicoMapa is not None:
            self.ServicoMapa.tick()

        bloqueio_mapa = bloqueio_gameplay or (opcoes_modal is not None) or dialogo_ativo or inventario_modal is not None or self.TelaAtual == "Config" or ger.ativa
        if self.TelaAtual is None and not bloqueio_mapa and not dentro_estadio:
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
                    estado_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}).get("estado", {}) if player is not None else {}
                    pos_player_mundo = self.ServicoMapa.gerenciador.posicao_player_mundo(estado_player, tuple(getattr(player, "Posicao", (0.0, 0.0)))) if (self.ServicoMapa is not None and player is not None) else tuple(getattr(player, "Posicao", (0.0, 0.0)))
                    if self.ServicoMapa is not None:
                        self.TelaMapa.abrir(JOGO, self.ServicoMapa, pos_player_mundo)
                        self.TelaAtual = "Mapa"
                    break

        player_bloqueado = (self.TelaAtual == "Mapa") or bloqueio_gameplay or (opcoes_modal is not None) or self.TelaAtual == "Config" or dialogo_ativo
        self.ControladorMundo.atualizar_frame(EVENTOS, dt, bloqueio_gameplay=player_bloqueado)

        if self._abrir_dialogo_pos_batalha_pendente(JOGO):
            return EVENTOS

        if JOGO.CenaAlvo is None and (not player_bloqueado) and int(pygame.time.get_ticks()) >= int(self._imune_combate_ate_ms or 0):
            colisao_pokemon = self.ControladorMundo.Player.consumir_colisao_pokemon()
            if isinstance(colisao_pokemon, dict):
                inventario = getattr(player, "Inventario", None)
                times = deepcopy(list(getattr(inventario, "TimesPokemon", []) or [])) if inventario is not None else []
                pokemons_jogador = deepcopy(list(getattr(inventario, "Pokemons", []) or [])) if inventario is not None else []
                indice_time, time_escolhido = InicializadorBatalha.escolher_time_confronto_com_indice(times, pokemons_jogador, slots_por_time=6)
                if not InicializadorBatalha.time_tem_pokemon_vivo(time_escolhido):
                    return EVENTOS
                server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
                link = server.get("ip")
                client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
                posicao_referencia_mundo = colisao_pokemon.get("posicao") if isinstance(colisao_pokemon.get("posicao"), (list, tuple)) and len(colisao_pokemon.get("posicao")) == 2 else list(getattr(player, "Posicao", [0.0, 0.0]))
                contexto = {
                    "batalha": dict(carregar_regras_cliente_mundo().get("batalha") or {}),
                    "pokemon_colisao": dict(colisao_pokemon),
                    "times_jogador": times,
                    "pokemons_jogador": pokemons_jogador,
                    "time_jogador": deepcopy(time_escolhido),
                    "time_jogador_indice": int(indice_time),
                    "tipo": "confronto",
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
                    break
        self._processar_estado_dialogo_npc(JOGO)
        self.ElementosHud.atualizar(dt)
        self.Camera.atualizar(dt)
        return EVENTOS

    def render_base(self, surface, JOGO, EVENTOS, dt):
        surface.fill((20, 20, 28))
        self.ControladorMundo.renderizar(surface)

    def render_base_limpa_surface(self):
        return True

    def render_post(self, surface, JOGO, EVENTOS, dt):
        _ = EVENTOS
        tempo = self.ControladorMundo.tempo_mundo_atual() if self.ControladorMundo is not None else {}
        dentro_estadio = False
        if self.ControladorMundo is not None and getattr(self.ControladorMundo, "Objetos", None) is not None:
            dentro_estadio = str(self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo") != "Mundo"
        bloco_bioma = tile_mundo_atual(self)
        biome_atual = bioma_visual_por_tile(bloco_bioma)
        self._filtro_camera.coletar_uniformes(
            tamanho_tela=surface.get_size(),
            camera=self.Camera,
            entidade_main=self.EntidadeMain,
            tempo_mundo=tempo,
            dt=dt,
            dentro_estadio=dentro_estadio,
            biome_atual=biome_atual,
        )
        if not dentro_estadio:
            self._filtro_camera.desenhar_bioma_base(surface)
            self._filtro_camera.desenhar_chuva_base(surface)

    def coletar_efeito_shader(self, JOGO, dt, tamanho_tela):
        _ = (JOGO, dt, tamanho_tela)
        if self.TelaAtual == "Config":
            return None
        return self._filtro_camera.uniformes_atuais()

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        player = self.ControladorMundo.player_local
        if player is not None:
            estado_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}).get("estado", {})
            pos_player_mundo = self.ServicoMapa.gerenciador.posicao_player_mundo(estado_player, tuple(getattr(player, "Posicao", (0.0, 0.0)))) if (self.ServicoMapa is not None and isinstance(estado_player, dict)) else tuple(getattr(player, "Posicao", (0.0, 0.0)))
            dentro_estadio = str((estado_player or {}).get("dimensao") or self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo") != "Mundo"
            if dentro_estadio:
                estadio_id = int((estado_player or {}).get("estadio_atual_id", 0) or 0)
                estadio = self.ControladorMundo.Objetos.EstadiosPorId.get(estadio_id, {})
                pos_estadio = estadio.get("posicao") if isinstance(estadio, dict) and isinstance(estadio.get("posicao"), (list, tuple)) and len(estadio.get("posicao")) == 2 else None
                if pos_estadio is not None:
                    pos_player_mundo = (float(pos_estadio[0]), float(pos_estadio[1]))
            self.ElementosHud.desenhar(surface, player.Inventario, terminal=self.Terminal, eventos=EVENTOS, dt=dt, servico_mapa=self.ServicoMapa, pos_player_mundo=pos_player_mundo, angulo_olhar=float(getattr(player, "AnguloOlhar", 0.0) or 0.0), mostrar_minimapa=bool(JOGO.CONFIG.get("MostrarMinimapa", False)))
            player_payload = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {})
            estado_player = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
            dica_estadio = self.ControladorMundo.Objetos.mensagem_interacao_estadio(
                pos_player=tuple(player.Posicao),
                dimensao_player=str(estado_player.get("dimensao") or self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo"),
                estadio_atual_id=int(estado_player.get("estadio_atual_id", 0) or 0),
            )
            if dica_estadio:
                self._texto_estadio.set_text(dica_estadio)
                self._texto_estadio.set_pos((surface.get_width() // 2, max(45, surface.get_height() - 118)))
                self._texto_estadio.draw(surface)

    def tela_atual_eh_complexa(self) -> bool:
        return self.TelaAtual not in ("Config", "Mapa")

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=surface)
            return
        if self.TelaAtual == "Mapa" and self.ServicoMapa is not None:
            player = self.ControladorMundo.player_local
            estado_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}).get("estado", {}) if player is not None else {}
            pos_player_mundo = self.ServicoMapa.gerenciador.posicao_player_mundo(estado_player, tuple(getattr(player, "Posicao", (0.0, 0.0)))) if player is not None else (0.0, 0.0)
            self.TelaMapa.desenhar(
                surface,
                JOGO,
                EVENTOS,
                dt,
                self.ServicoMapa,
                estado_player if isinstance(estado_player, dict) else {},
                pos_player_mundo,
                angulo_olhar=float(getattr(player, "AnguloOlhar", 0.0) or 0.0) if player is not None else 0.0,
            )
            if not self.TelaMapa.ativo:
                self.TelaAtual = None

    def Tela(self, JOGO, EVENTOS, dt):
        self.atualizar_cena(JOGO, EVENTOS, dt)
        if self.tela_atual_eh_complexa():
            self.render_base(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_post(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_hud(JOGO.TELA, JOGO, EVENTOS, dt)
        else:
            self.render_tela(JOGO.TELA, JOGO, EVENTOS, dt)

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
        times_validos = InicializadorBatalha.times_completos(times, slots_por_time=6)
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

        npc_ctx = dict(contexto_dialogo or {})

        def _comecar_com_time(time_escolhido: dict):
            indice_time = next((i for i, time_existente in enumerate(times_validos) if time_existente == time_escolhido), 0)
            times_npc = [t for t in list(npc_ctx.get("times_pokemon") or []) if isinstance(t, dict)]
            batalha_numero = max(1, int(npc_ctx.get("batalha_numero", 1) or 1))
            time_npc = deepcopy(times_npc[min(len(times_npc) - 1, batalha_numero - 1)]) if times_npc else {}
            pokemons_npc = list(time_npc.get("Slots") or time_npc.get("slots") or [])
            pokemons_jogador = deepcopy(list(getattr(inventario, "Pokemons", []) or [])) if inventario is not None else []
            jogo.INFO["CombateContexto"] = {
                **contexto_base,
                "batalha": dict(carregar_regras_cliente_mundo().get("batalha") or {}),
                "tipo": "treinador",
                "npc_contexto": npc_ctx,
                "times_jogador": deepcopy(list(times_validos)),
                "pokemons_jogador": pokemons_jogador,
                "time_jogador": deepcopy(dict(time_escolhido or {})),
                "time_jogador_indice": int(indice_time),
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

    def _finalizar_dialogo_npc(self, jogo) -> None:
        npc_id = int(self._npc_interacao_id or 0)
        self._npc_interacao_id = 0
        self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
        server = jogo.INFO.get("ServerSelecionado") if isinstance(jogo.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        if link and npc_id > 0:
            finalizar_interacao_npc_mundo(link, client_id, npc_id)

    def Finalizar(self, JOGO):
        JOGO.INFO.pop("MundoTelaSobreposta", None)
        preservando_imagens_mapa = str(getattr(JOGO, "CenaAlvo", "") or "") == "Combate"
        snapshot_player = self._snapshot_player_atual(JOGO)
        if isinstance(snapshot_player, dict):
            JOGO.INFO["PlayerDadosServer"] = snapshot_player
        if int(self._npc_interacao_id or 0) > 0:
            self._finalizar_dialogo_npc(JOGO)
        if self.Terminal is not None:
            self.Terminal.parar()
        if self.ControladorMundo is not None:
            server = JOGO.INFO.get("ServerSelecionado") or {}
            link = server.get("ip")
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
            self.ControladorMundo.parar(link, client_id)
        if self.ServicoMapa is not None:
            self.ServicoMapa.encerrar(limpar_imagens=not preservando_imagens_mapa)
            if not preservando_imagens_mapa:
                self.ServicoMapa = None
        self._desconectado = True
