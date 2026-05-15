"""Mixin de renderizacao, HUD e efeitos da CenaMundo."""

from Codigo.ModulosGerais.EfeitosTela import FecharIris, AbrirIris
from Codigo.ModulosGerais.Sonoridades import tile_mundo_atual
from Codigo.ModulosGerais.Auxiliares import bioma_visual_por_tile
from Codigo.Telas.Telas.TelaConfig import TelaConfig


class RenderCenaMundoMixin:
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
        _ = (JOGO, dt)
        if getattr(self, "_tela_creditos", None) is not None and self._tela_creditos.ativa:
            return self._tela_creditos.coletar_efeito_shader() or {}
        if self.TelaAtual == "Config":
            return None
        efeito = self._filtro_camera.uniformes_atuais()
        if self.ControladorMundo is not None and getattr(self.ControladorMundo, "Objetos", None) is not None:
            dungeon_fx = self._coletar_efeito_dungeon()
            if dungeon_fx:
                efeito = {**efeito, **dungeon_fx}
            captura = self.ControladorMundo.Objetos.coletar_efeito_captura_shader(self.Camera, tamanho_tela)
            if isinstance(captura, dict) and captura:
                efeito = {**efeito, **captura}
            dungeon_texto = self.ControladorMundo.Dungeons.efeito_shader()
            if isinstance(dungeon_texto, dict) and dungeon_texto:
                efeito = {**efeito, **dungeon_texto}
        if getattr(self, "_tela_morrer", None) is not None and self._tela_morrer.ativa:
            texto = self._tela_morrer.coletar_efeito_shader()
            if isinstance(texto, dict) and texto:
                efeito = {**efeito, **texto}
        return efeito

    def _coletar_efeito_dungeon(self) -> dict:
        player = self.ControladorMundo.player_local if self.ControladorMundo is not None else None
        objetos = getattr(self.ControladorMundo, "Objetos", None) if self.ControladorMundo is not None else None
        if player is None or objetos is None:
            return {}
        payload = objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {})
        estado_player = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        dimensao = str(estado_player.get("dimensao") or objetos.dimensao_atual_client() or "Mundo")
        if not dimensao.startswith("Dungeon_"):
            return {}
        layout = self.ControladorMundo.Leitor.MetaMundo.get("layout_dungeon") if isinstance(self.ControladorMundo.Leitor.MetaMundo, dict) else {}
        estado_dungeon = estado_player.get("estado_dungeon") if isinstance(estado_player.get("estado_dungeon"), dict) else {}
        sala_id = str(estado_dungeon.get("sala_id") or "")
        sala = next((s for s in layout.get("salas", []) if isinstance(s, dict) and str(s.get("id") or "") == sala_id), None) if isinstance(layout, dict) else None
        escura = isinstance(sala, dict) and str(sala.get("tipo") or "").strip().lower() == "escura"
        return {"dungeon_power": 1.0, "dungeon_darkness": 0.84 if escura else 0.58}

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        player = self.ControladorMundo.player_local
        if player is not None:
            estado_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}).get("estado", {})
            pos_player_mundo = self.ServicoMapa.gerenciador.posicao_player_mundo(estado_player, tuple(getattr(player, "Posicao", (0.0, 0.0)))) if (self.ServicoMapa is not None and isinstance(estado_player, dict)) else tuple(getattr(player, "Posicao", (0.0, 0.0)))
            dim_player = str((estado_player or {}).get("dimensao") or self.ControladorMundo.Objetos.dimensao_atual_client() or "Mundo")
            dentro_estadio = dim_player.startswith("Estadio")
            dentro_dungeon = dim_player.startswith("Dungeon_")
            if dentro_estadio:
                estadio_id = int((estado_player or {}).get("estadio_atual_id", 0) or 0)
                estadio = self.ControladorMundo.Objetos.EstadiosPorId.get(estadio_id, {})
                pos_estadio = estadio.get("posicao") if isinstance(estadio, dict) and isinstance(estadio.get("posicao"), (list, tuple)) and len(estadio.get("posicao")) == 2 else None
                if pos_estadio is not None:
                    pos_player_mundo = (float(pos_estadio[0]), float(pos_estadio[1]))
            layout_dungeon = self.ControladorMundo.Leitor.MetaMundo.get("layout_dungeon") if dentro_dungeon and isinstance(self.ControladorMundo.Leitor.MetaMundo, dict) else None
            estado_hud_dungeon = (estado_player or {}).get("estado_dungeon") if dentro_dungeon and isinstance((estado_player or {}).get("estado_dungeon"), dict) else None
            if isinstance(estado_hud_dungeon, dict) and isinstance((estado_player or {}).get("vida_player"), dict):
                estado_hud_dungeon = {**estado_hud_dungeon, "vida_player": (estado_player or {}).get("vida_player")}
            captura_hud = self.ControladorMundo.Objetos.captura_hud_atual()
            self.ElementosHud.desenhar(surface, player.Inventario, terminal=self.Terminal, eventos=EVENTOS, dt=dt, servico_mapa=self.ServicoMapa, pos_player_mundo=pos_player_mundo, angulo_olhar=float(getattr(player, "AnguloOlhar", 0.0) or 0.0), mostrar_minimapa=bool(JOGO.CONFIG.get("MostrarMinimapa", False)), estado_dungeon=estado_hud_dungeon, layout_dungeon=layout_dungeon, captura_hud=captura_hud, objetos_mundo=self.ControladorMundo.Objetos, perfil=getattr(player, "Perfil", None))
            if dentro_dungeon:
                self.ControladorMundo.Dungeons.renderizar_texto(surface)
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
        self._tela_morrer.desenhar(surface, EVENTOS, dt, JOGO)
        self._renderizar_transicao_portal(JOGO, dt)
        self._tela_creditos.desenhar(surface, EVENTOS, dt, JOGO)

    def _renderizar_transicao_portal(self, jogo, dt):
        trans = self._portal_transicao if isinstance(self._portal_transicao, dict) else None
        if not trans:
            return
        fase = str(trans.get("fase") or "fechando")
        if fase == "fechando":
            FecharIris(jogo, dt, dur=0.22)
            if float(getattr(jogo, "Escuro", 0.0) or 0.0) >= 100.0 and not bool(trans.get("executou", False)):
                trans["executou"] = True
                acao = trans.get("acao")
                if callable(acao):
                    acao()
                trans["fase"] = "abrindo"
            return
        AbrirIris(jogo, dt, dur=0.24)
        if float(getattr(jogo, "Escuro", 0.0) or 0.0) <= 0.0:
            self._portal_transicao = None

    def tela_atual_eh_complexa(self) -> bool:
        return self.TelaAtual not in ("Config", "Mapa")

    def bloquear_claridade_global(self) -> bool:
        return bool(self._tela_morrer.ativa or self._tela_creditos.ativa)

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=surface)
            self._tela_morrer.desenhar(surface, EVENTOS, dt, JOGO)
            self._tela_creditos.desenhar(surface, EVENTOS, dt, JOGO)
            return
        if self.TelaAtual == "Mapa" and (self.ServicoMapa is not None or isinstance(getattr(self.TelaMapa, "_layout_dungeon", None), dict)):
            player = self.ControladorMundo.player_local
            estado_player = self.ControladorMundo.Objetos.ObjetosPorId.get(int(getattr(player, "Id", 0) or 0), {}).get("estado", {}) if player is not None else {}
            pos_player_mundo = self.ServicoMapa.gerenciador.posicao_player_mundo(estado_player, tuple(getattr(player, "Posicao", (0.0, 0.0)))) if (self.ServicoMapa is not None and player is not None) else tuple(getattr(player, "Posicao", (0.0, 0.0))) if player is not None else (0.0, 0.0)
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
        self._tela_morrer.desenhar(surface, EVENTOS, dt, JOGO)
        self._tela_creditos.desenhar(surface, EVENTOS, dt, JOGO)
