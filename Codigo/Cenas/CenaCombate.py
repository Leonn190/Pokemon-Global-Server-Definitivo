from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Modulos.Camera import CameraBatalha
from Codigo.Modulos.ControladorBatalha import ControladorBatalha
from Codigo.Modulos.ElementosHudCombate import ElementosHudCombate
from Codigo.Telas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.Server.ServerMundo import finalizar_interacao_npc_mundo
from Codigo.Telas.TelaConfig import TelaConfig, ResetTelaConfig
import pygame


class CenaCombate:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Combate"
        self.TelaAtual = "Combate"

        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        regras_mundo = JOGO.INFO.get("RegrasMundo") if isinstance(JOGO.INFO.get("RegrasMundo"), dict) else {}
        gerais = regras_mundo.get("gerais") if isinstance(regras_mundo.get("gerais"), dict) else {}
        tile_px = max(8, int(gerais.get("combate_camera_px_por_tile", 40) or 40))
        largura = float(contexto.get("largura", 100) or 100)
        altura = float(contexto.get("altura", 60) or 60)
        centro = contexto.get("centro") if isinstance(contexto.get("centro"), (list, tuple)) and len(contexto.get("centro")) == 2 else [largura * 0.5, altura * 0.5]
        half_w = (float(JOGO.TELA.get_size()[0]) / float(tile_px)) * 0.5
        half_h = (float(JOGO.TELA.get_size()[1]) / float(tile_px)) * 0.5
        pos_inicial = (float(centro[0]) - half_w, float(centro[1]) - half_h)

        self.Camera = CameraBatalha(JOGO.TELA.get_size(), posicao_inicial_tiles=pos_inicial, tile_px=tile_px)
        self.Camera.definir_limites_mundo(largura, altura)
        self.Camera.atualizar(0.0)
        self.ControladorBatalha = ControladorBatalha(contexto)
        self.ElementosHudCombate = ElementosHudCombate(ao_fugir=lambda: self._fugir_combate(JOGO))

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
        opcoes_modal = JOGO.GerenciadorSubtelas.obter_por_tipo(SubtelaOpcoes)
        if opcoes_modal is None and self.TelaAtual != "Config":
            for ev in EVENTOS:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    opcoes_modal = SubtelaOpcoes()
                    opcoes_modal.toggle(JOGO)
                    JOGO.GerenciadorSubtelas.abrir(opcoes_modal)
                    break
        bloqueado = opcoes_modal is not None
        if not bloqueado:
            self.Camera.processar_eventos(EVENTOS)
        self.Camera.atualizar(dt)
        self.ControladorBatalha.atualizar(EVENTOS, dt)

    def tela_atual_eh_complexa(self) -> bool:
        return self.TelaAtual != "Config"

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=surface)

    def render_base(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        surface.fill((20, 20, 28))
        self.ControladorBatalha.renderizar(surface, self.Camera)

    def render_post(self, surface, JOGO, EVENTOS, dt):
        _ = (surface, JOGO, EVENTOS, dt)

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        self.ElementosHudCombate.desenhar(surface, EVENTOS, dt)

    def Tela(self, JOGO, EVENTOS, dt):
        self.atualizar_cena(JOGO, EVENTOS, dt)
        if self.tela_atual_eh_complexa():
            self.render_base(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_post(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_hud(JOGO.TELA, JOGO, EVENTOS, dt)
        else:
            self.render_tela(JOGO.TELA, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
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
