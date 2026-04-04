import pygame

from Codigo.Modulos.Camera import Camera
from Codigo.Modulos.ControladorMundo.ControladorMundo import ControladorMundo
from Codigo.Modulos.ElementosHud import ElementosHud
from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Telas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Telas.Config import TelaConfig, ResetTelaConfig
from Codigo.Server.ServerMundo import (
    buscar_mensagens_terminal,
    enviar_mensagem_terminal,
    finalizar_interacao_npc_mundo,
    iniciar_interacao_npc_mundo,
    solicitar_contexto_batalha_mundo,
)
from Codigo.Telas.Inventario.Unificador import UnificadorInventario
from Codigo.Prefabs.Terminal import Terminal
from Codigo.Telas.TelaDialogo import TelaDialogo
from Codigo.Prefabs.Texto import Texto


class CenaMundo:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Mundo"

        self.Camera = None
        self.ControladorMundo = None
        self.EntidadeMain = None
        self.ElementosHud = ElementosHud()
        self.SubtelaOpcoes = SubtelaOpcoes()
        self._desconectado = False
        self.TelaAtual = None
        self.SubtelaInventario = None
        self.SubtelaDialogo = None
        self.Terminal = None
        self._npc_interacao_id = 0
        self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
        self._texto_estadio = Texto("", style={"size": 22, "align": "center", "outline": True, "color": (230, 236, 245)})

        self._montar_mundo(JOGO)

        tela_sobreposta = JOGO.INFO.pop("MundoTelaSobreposta", None)
        if tela_sobreposta == "Config":
            ResetTelaConfig()
            self.TelaAtual = "Config"

    def _montar_mundo(self, JOGO):
        dados = JOGO.INFO.get("PlayerDadosServer") or {}
        self.Camera = Camera(JOGO.TELA.get_size(), entidade_main=None, tile_px=50)
        self.ControladorMundo = ControladorMundo(jogo=JOGO, camera=self.Camera)
        player_local = self.ControladorMundo.montar_player_local(dados)
        self.EntidadeMain = player_local
        self.Camera.definir_main(self.EntidadeMain)
        self.SubtelaInventario = UnificadorInventario(player_local)

        regras = JOGO.INFO.get("RegrasServer") if isinstance(JOGO.INFO.get("RegrasServer"), dict) else {}
        mundo = regras.get("mundo") if isinstance(regras.get("mundo"), dict) else {}
        chunk_tiles = mundo.get("chunk_tiles")
        if chunk_tiles is not None:
            try:
                self.ControladorMundo.Objetos._chunk_tamanho_tiles = max(1, int(chunk_tiles))
            except (TypeError, ValueError):
                pass

        server = JOGO.INFO.get("ServerSelecionado") or {}
        link = server.get("ip")
        usuario = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        self.Terminal = Terminal(
            pygame.Rect(14, 14, 520, 220),
            callback_enviar=lambda texto: enviar_mensagem_terminal(link, usuario, texto) if link else None,
            callback_buscar=lambda ultimo_id: buscar_mensagens_terminal(link, ultimo_id=ultimo_id) if link else {"status": "ok", "mensagens": []},
            autor_local=usuario,
        )
        self.Terminal.iniciar()

        if link:
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
            self.ControladorMundo.conectar(link, client_id)

    def Tela(self, JOGO, EVENTOS, dt):
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

        self.SubtelaOpcoes.processar_eventos(JOGO, EVENTOS)

        if player is not None and getattr(player, "Controle", None) is not None and self.SubtelaInventario is not None:
            player.Controle.BloquearToggleInventario = self.SubtelaInventario.bloquear_toggle_inventario()
        if player is not None and self.SubtelaOpcoes.Ativa:
            player.Controle.InventarioAberto = False

        dialogo_ativo = bool(self.SubtelaDialogo is not None and getattr(self.SubtelaDialogo, "Ativa", False))
        player_bloqueado = bloqueio_gameplay or self.SubtelaOpcoes.Ativa or self.TelaAtual == "Config" or dialogo_ativo
        self.ControladorMundo.atualizar_frame(EVENTOS, dt, bloqueio_gameplay=player_bloqueado)

        if not player_bloqueado:
            colisao_pokemon = self.ControladorMundo.Player.consumir_colisao_pokemon()
            if isinstance(colisao_pokemon, dict):
                server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
                link = server.get("ip")
                client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
                centro = tuple(player.Posicao) if player is not None else tuple(colisao_pokemon.get("posicao", [0.0, 0.0]))
                ret = solicitar_contexto_batalha_mundo(link, client_id, int(colisao_pokemon.get("id", 0) or 0), centro) if link else {"status": "erro"}
                contexto = ret.get("contexto_batalha") if isinstance(ret, dict) and isinstance(ret.get("contexto_batalha"), dict) else None
                if isinstance(contexto, dict):
                    contexto["pokemon_colisao"] = dict(colisao_pokemon)
                    JOGO.INFO["CombateContexto"] = contexto
                    JOGO.CenaAlvo = "Combate"
                    return

        if player is not None and self.SubtelaInventario is not None:
            self.SubtelaInventario.Ativo = player.Controle.InventarioAberto
            self.SubtelaInventario.atualizar(EVENTOS, dt, JOGO.TELA.get_size())
        if self.SubtelaDialogo is not None and getattr(self.SubtelaDialogo, "Ativa", False):
            self.SubtelaDialogo.processar_eventos(EVENTOS)
            self.SubtelaDialogo.atualizar(dt)
        elif self.SubtelaDialogo is not None and not getattr(self.SubtelaDialogo, "Ativa", False):
            self.SubtelaDialogo = None

        if (not player_bloqueado) and player is not None and getattr(player, "Controle", None) is not None:
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                    alvo = self.ControladorMundo.Objetos.npc_interagivel_proximo(tuple(player.Posicao), raio=2.3)
                    if alvo is not None:
                        npc_obj = dict(alvo.get("obj", {}))
                        estado = npc_obj.get("estado") if isinstance(npc_obj.get("estado"), dict) else {}
                        inter = estado.get("interacao") if isinstance(estado.get("interacao"), dict) else {}
                        if not bool(inter.get("ativa", False)):
                            self._solicitar_interacao_npc(JOGO, npc_obj)
                    break
        self._processar_estado_dialogo_npc(JOGO)
        self.Camera.atualizar(dt)

        JOGO.TELA.fill((20, 20, 28))
        self.ControladorMundo.renderizar(JOGO.TELA)

        if player is not None:
            player.renderizar_stamina(JOGO.TELA, self.Camera, dt)
            self.ElementosHud.desenhar(JOGO.TELA, player.Inventario, terminal=self.Terminal, eventos=EVENTOS, dt=dt)
            player_payload = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {})
            estado_player = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
            dica_estadio = self.ControladorMundo.Objetos.mensagem_interacao_estadio(
                pos_player=tuple(player.Posicao),
                dimensao_player=str(estado_player.get("dimensao") or "Mundo"),
                estadio_atual_id=int(estado_player.get("estadio_atual_id", 0) or 0),
            )
            if dica_estadio:
                self._texto_estadio.set_text(dica_estadio)
                self._texto_estadio.set_pos((JOGO.TELA.get_width() // 2, max(45, JOGO.TELA.get_height() - 118)))
                self._texto_estadio.draw(JOGO.TELA)

        self.SubtelaOpcoes.desenhar(JOGO)
        if self.SubtelaDialogo is not None and getattr(self.SubtelaDialogo, "Ativa", False):
            self.SubtelaDialogo.desenhar(JOGO.TELA, EVENTOS, dt)
        if self.SubtelaInventario is not None and self.SubtelaInventario.Ativo:
            self.SubtelaInventario.desenhar(JOGO.TELA, EVENTOS, dt)
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt)

    def _coletar_contexto_batalha(self, colisao_pokemon: dict) -> dict:
        player = self.ControladorMundo.player_local
        centro = tuple(player.Posicao) if player is not None else tuple(colisao_pokemon.get("posicao", [0.0, 0.0]))

        rx, ry = 50, 30
        x0, x1 = int(centro[0]) - rx, int(centro[0]) + rx
        y0, y1 = int(centro[1]) - ry, int(centro[1]) + ry

        leitor = self.ControladorMundo.Leitor
        chunks = dict(getattr(leitor, "Chunks", {}))
        chunk_tamanho = max(1, int(getattr(leitor, "TamanhoChunkBlocos", 10) or 10))

        tiles = []
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                cx = int(tx // chunk_tamanho)
                cy = int(ty // chunk_tamanho)
                grid = chunks.get((cx, cy))
                if not grid:
                    continue
                lx = tx - (cx * chunk_tamanho)
                ly = ty - (cy * chunk_tamanho)
                if ly < 0 or ly >= len(grid):
                    continue
                row = grid[ly]
                if lx < 0 or lx >= len(row):
                    continue
                tiles.append({"x": tx - x0, "y": ty - y0, "bloco": int(row[lx])})

        estruturas = []
        for payload in self.ControladorMundo.Objetos.ObjetosPorId.values():
            if not isinstance(payload, dict):
                continue
            if not str(payload.get("tipo", "")).startswith("estrutura"):
                continue
            pos = payload.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            x, y = float(pos[0]), float(pos[1])
            if x < x0 or x > x1 or y < y0 or y > y1:
                continue
            estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
            estruturas.append(
                {
                    "x": x - x0,
                    "y": y - y0,
                    "codigo_natural": int(payload.get("codigo_natural", estado.get("codigo_natural", 0)) or 0),
                    "sprite": str(payload.get("sprite", "") or ""),
                }
            )

        return {
            "origem": [x0, y0],
            "centro": [50, 30],
            "largura": 100,
            "altura": 60,
            "arena_largura": 50,
            "arena_altura": 30,
            "tiles": tiles,
            "estruturas": estruturas,
            "pokemon_colisao": dict(colisao_pokemon),
        }

    def _solicitar_interacao_npc(self, jogo, npc_obj: dict) -> None:
        if self.SubtelaDialogo is not None and getattr(self.SubtelaDialogo, "Ativa", False):
            return
        player = self.ControladorMundo.player_local
        if player is None:
            return
        server = jogo.INFO.get("ServerSelecionado") if isinstance(jogo.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        npc_id = int(npc_obj.get("id", 0) or 0)
        if link and npc_id > 0:
            iniciar_interacao_npc_mundo(link, client_id, npc_id)
        self._npc_interacao_pendente = {"npc_id": npc_id, "desde_ms": int(pygame.time.get_ticks())}

    def _abrir_dialogo_npc_autoritativo(self, jogo, npc_obj: dict) -> None:
        player = self.ControladorMundo.player_local
        if player is None:
            return
        client_id = str(jogo.INFO.get("UsuarioLogado", "anon"))
        npc_id = int(npc_obj.get("id", 0) or 0)
        self._npc_interacao_id = npc_id
        self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
        self.SubtelaDialogo = TelaDialogo(
            player_nome=str(getattr(player, "Nome", "") or client_id),
            player_skin=str(getattr(player, "NomeSkin", "S1.png")),
            npc_payload=npc_obj,
            ao_encerrar=lambda: self._finalizar_dialogo_npc(jogo),
            ator_local=player,
        )

    def _processar_estado_dialogo_npc(self, jogo) -> None:
        if self.SubtelaDialogo is not None and getattr(self.SubtelaDialogo, "Ativa", False):
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
            self._abrir_dialogo_npc_autoritativo(jogo, obj)
            return
        if ativo and dono != client_id:
            self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}
            return
        if int(pygame.time.get_ticks()) - int(pend.get("desde_ms", 0) or 0) > 1800:
            self._npc_interacao_pendente = {"npc_id": 0, "desde_ms": 0}

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
        if int(self._npc_interacao_id or 0) > 0:
            self._finalizar_dialogo_npc(JOGO)
        if self.Terminal is not None:
            self.Terminal.parar()
        if self.ControladorMundo is not None:
            server = JOGO.INFO.get("ServerSelecionado") or {}
            link = server.get("ip")
            client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
            self.ControladorMundo.parar(link, client_id)
        self._desconectado = True
