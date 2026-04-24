from Codigo.ModulosGerais.EfeitosTela import FecharIris, AbrirIris
from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.Telas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Server.ServerMundo import finalizar_interacao_npc_mundo, solicitar_contexto_batalha_mundo
from Codigo.Server.ServerTerminal import buscar_mensagens_terminal, enviar_mensagem_terminal
from Codigo.Telas.TelaConfig import TelaConfig, ResetTelaConfig
from Codigo.Prefabs.Terminal import Terminal
import pygame


class CenaCombate:
    def PrepararTransicaoAssincrona(self, JOGO) -> None:
        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        if str(contexto.get("tipo") or "confronto").strip().lower() not in {"confronto", "treinador", "trainer"}:
            return
        tiles = contexto.get("tiles")
        if isinstance(tiles, list) and tiles:
            return
        pokemon_colisao = contexto.get("pokemon_colisao") if isinstance(contexto.get("pokemon_colisao"), dict) else {}
        server_ip = str(contexto.get("server_ip") or "")
        client_id = str(contexto.get("client_id") or JOGO.INFO.get("UsuarioLogado", "anon"))
        pokemon_id = int(pokemon_colisao.get("id", pokemon_colisao.get("Id", pokemon_colisao.get("ID", 0))) or 0)
        centro = contexto.get("posicao_referencia_mundo")
        if not isinstance(centro, (list, tuple)) or len(centro) != 2:
            centro = pokemon_colisao.get("posicao")
        if not isinstance(centro, (list, tuple)) or len(centro) != 2:
            centro = contexto.get("centro")
        if not isinstance(centro, (list, tuple)) or len(centro) != 2:
            centro = [40.0, 20.0]
        if not server_ip:
            return
        ret = solicitar_contexto_batalha_mundo(server_ip, client_id, pokemon_id, centro)
        contexto_servidor = ret.get("contexto_batalha") if isinstance(ret, dict) and isinstance(ret.get("contexto_batalha"), dict) else {}
        if not contexto_servidor:
            return
        JOGO.INFO["CombateContexto"] = {
            **dict(contexto),
            **dict(contexto_servidor),
            "pokemon_colisao": dict(pokemon_colisao),
            "time_jogador": dict(contexto.get("time_jogador") or {}),
            "times_jogador": list(contexto.get("times_jogador") or []),
            "pokemons_jogador": list(contexto.get("pokemons_jogador") or []),
        }

    def Inicializar(self, JOGO):
        self._jogo_ref = JOGO
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Combate"
        self.TelaAtual = "Combate"

        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        regras_mundo = JOGO.INFO.get("RegrasMundo") if isinstance(JOGO.INFO.get("RegrasMundo"), dict) else {}
        gerais = regras_mundo.get("gerais") if isinstance(regras_mundo.get("gerais"), dict) else {}
        tile_px = int(gerais.get("combate_camera_px_por_tile", 40))
        largura = float(contexto.get("largura", 80) or 80)
        altura = float(contexto.get("altura", 40) or 40)
        centro = contexto.get("centro") if isinstance(contexto.get("centro"), (list, tuple)) and len(contexto.get("centro")) == 2 else [largura * 0.5, altura * 0.5]
        arena_w = float(contexto.get("arena_largura", 40) or 40)
        arena_h = float(contexto.get("arena_altura", 20) or 20)
        half_w = (float(JOGO.TELA.get_size()[0]) / float(tile_px)) * 0.5
        half_h = (float(JOGO.TELA.get_size()[1]) / float(tile_px)) * 0.5
        pos_inicial = (float(centro[0]) - half_w, float(centro[1]) - half_h)

        self.Camera = CameraBatalha(JOGO.TELA.get_size(), posicao_inicial_tiles=pos_inicial, tile_px=tile_px)
        self.Camera.definir_limites_mundo(largura, altura)
        self.Camera.definir_referencia_arena(
            (float(centro[0]) - (arena_w * 0.5), float(centro[1]) - (arena_h * 0.5)),
            (arena_w, arena_h),
        )
        self.Camera.atualizar(0.0)
        self.Arena = Arena(contexto)

        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        usuario = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        self.Terminal = Terminal(
            pygame.Rect(14, 14, 520, 220),
            callback_enviar=lambda texto: self._enviar_terminal_batalha(link, usuario, texto),
            callback_buscar=lambda ultimo_id: buscar_mensagens_terminal(link, ultimo_id=ultimo_id, contexto="batalha", meta=self._meta_terminal_batalha(JOGO)) if link else {"status": "ok", "mensagens": []},
            autor_local=usuario,
            tecla_abrir=pygame.K_t,
        )
        self.Terminal.iniciar()
        self._eventos_ui_atual = []

    def _meta_terminal_batalha(self, jogo) -> dict:
        contexto = jogo.INFO.get("CombateContexto") if isinstance(jogo.INFO.get("CombateContexto"), dict) else {}
        meta = {
            "batalha_id": str(contexto.get("batalha_id_servidor") or ""),
            "client_id": str(contexto.get("client_id") or jogo.INFO.get("UsuarioLogado", "anon")),
        }
        return meta

    def _enviar_terminal_batalha(self, link: str, usuario: str, texto: str) -> dict:
        if not link:
            return {"status": "erro", "mensagem": "Servidor indisponível"}
        return enviar_mensagem_terminal(link, usuario, texto, contexto="batalha", meta=self._meta_terminal_batalha(self._jogo_ref))

    def _fugir_combate(self, jogo) -> None:
        jogo.INFO["ImuneCombateAteMs"] = int(pygame.time.get_ticks()) + 3000
        jogo.CenaAlvo = "Mundo"

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = str(tela)

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Config":
            return
        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()
        eventos_ui = list(EVENTOS or [])
        if self.Terminal is not None:
            eventos_ui = self.Terminal.processar_eventos(eventos_ui)
        opcoes_modal = JOGO.GerenciadorSubtelas.obter_por_tipo(SubtelaOpcoes)
        if opcoes_modal is None and self.TelaAtual != "Config":
            for ev in eventos_ui:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    opcoes_modal = SubtelaOpcoes()
                    opcoes_modal.toggle(JOGO)
                    JOGO.GerenciadorSubtelas.abrir(opcoes_modal)
                    break
        terminal_digitando = bool(self.Terminal is not None and self.Terminal.esta_digitando)
        bloqueado = opcoes_modal is not None or terminal_digitando
        if not bloqueado:
            self.Camera.processar_eventos(eventos_ui)
        self._eventos_ui_atual = list(eventos_ui)
        self.Camera.atualizar(dt)

    def tela_atual_eh_complexa(self) -> bool:
        return self.TelaAtual != "Config"

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=surface)

    def render_base(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        surface.fill((20, 20, 28))
        self.Arena.renderizar(surface, self.Camera)

    def render_post(self, surface, JOGO, EVENTOS, dt):
        _ = (surface, JOGO, EVENTOS, dt)

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        eventos_ui = list(getattr(self, "_eventos_ui_atual", EVENTOS) or [])
        if self.Terminal is not None:
            self.Terminal.desenhar(surface, eventos_ui, dt)

    def Tela(self, JOGO, EVENTOS, dt):
        self.atualizar_cena(JOGO, EVENTOS, dt)
        if self.tela_atual_eh_complexa():
            self.render_base(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_post(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_hud(JOGO.TELA, JOGO, EVENTOS, dt)
        else:
            self.render_tela(JOGO.TELA, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        if self.Terminal is not None:
            self.Terminal.parar()
        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        npc_ctx = contexto.get("npc_contexto") if isinstance(contexto.get("npc_contexto"), dict) else {}
        npc_id = int(npc_ctx.get("npc_id", 0) or 0)
        if npc_id <= 0:
            return
        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        if link:
            finalizar_interacao_npc_mundo(link, client_id, npc_id)
