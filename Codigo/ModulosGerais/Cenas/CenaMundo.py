from Codigo.ModulosGerais.Cenas.FluxoCenaMundo import FluxoCenaMundoMixin
from Codigo.ModulosGerais.Cenas.RenderCenaMundo import RenderCenaMundoMixin
from Codigo.ModulosGerais.Cenas.EventosCenaMundo import EventosCenaMundoMixin
from Codigo.ModulosMundo.ElementosHudMundo import ElementosHudMundo
from Codigo.Telas.Telas.TelaMapa import TelaMapa
from Codigo.ModulosGerais.EfeitosTela import FecharIris, AbrirIris
from Codigo.ModulosGerais.FiltroCamera import FiltroCamera
from Codigo.ModulosGerais.ModuladorRegras import ModuladorRegras
from Codigo.Telas.Telas.TelaConfig import ResetTelaConfig
from Codigo.Prefabs.Texto import Texto
from Codigo.Telas.Telas.TelaCreditos import TelaCreditos
from Codigo.Telas.Telas.TelaMorrer import TelaMorrer


class CenaMundo(
    FluxoCenaMundoMixin,
    RenderCenaMundoMixin,
    EventosCenaMundoMixin,
):
    @staticmethod
    def _tem_exploracao_chunks(dados_player: dict) -> bool:
        exploracao = dados_player.get("exploracao_chunks") if isinstance(dados_player, dict) else {}
        mundo = exploracao.get("Mundo") if isinstance(exploracao, dict) and isinstance(exploracao.get("Mundo"), dict) else {}
        return any(isinstance(valores, (list, tuple, set)) and len(valores) > 0 for valores in mundo.values())

    def Inicializar(self, JOGO):
        self._jogo_ref = JOGO
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
        self._imune_combate_ate_ms = int(JOGO.INFO.get("ImuneCombateAteMs", 0) or 0)
        self._imunidade_combate_pendente = bool(JOGO.INFO.pop("ImuneCombatePendenteMundo", False))
        self._filtro_camera = FiltroCamera()
        self._tela_morrer = TelaMorrer()
        self._tela_creditos = TelaCreditos()
        self._ultimo_chunk_seguro = None
        self._ultimo_chunk_seguro_mundo = None
        self._portal_transicao = None
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

    def Tela(self, JOGO, EVENTOS, dt):
        self.atualizar_cena(JOGO, EVENTOS, dt)
        if self.tela_atual_eh_complexa():
            self.render_base(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_post(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_hud(JOGO.TELA, JOGO, EVENTOS, dt)
        else:
            self.render_tela(JOGO.TELA, JOGO, EVENTOS, dt)

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
