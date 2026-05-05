"""Maestro único da cena de mundo no client."""

from __future__ import annotations

from Codigo.ModulosGerais.Server.ServerMundo import consultar_chunks_mundo, receber_pacotes_tick_mundo, desconectar_mundo, definir_bombeamento_local_manual

from .LeitorMundo import LeitorMundo
from .ControladorObjetos import ControladorObjetos
from .ControladorPlayer import ControladorPlayer
from .SistemaPacotes import SistemaPacotes
from Codigo.ModulosMundo.ControladorDungeons import ControladorDungeons
from Codigo.Geradores.ConstrutorDungeon import renderizar_dungeon


class ControladorMundo:
    def __init__(self, jogo, camera):
        self.JOGO = jogo
        self.Camera = camera
        self.Objetos = ControladorObjetos()
        self.Player = ControladorPlayer(self.Objetos, jogo=jogo, callback_transicao_dimensao=self._ao_dimensao_atualizada)
        self.Leitor = LeitorMundo(
            jogo=jogo,
            camera=camera,
            callback_atualizacao=consultar_chunks_mundo,
            callback_dimensao_atual=self._ao_dimensao_atualizada,
            intervalo_poll=0.20,
            raio_chunks=4,
        )
        self.Pacotes = SistemaPacotes(self.Objetos, self.Player, self.Leitor, camera)
        self.Dungeons = ControladorDungeons()
        definir_bombeamento_local_manual(True)
        self.Leitor.ativar_bombeamento_manual(True)
        self.Pacotes.ativar_bombeamento_manual(True)
        self._desconectado = False

    def _tile_px_mundo(self) -> int:
        info = getattr(self.JOGO, "INFO", {}) if self.JOGO is not None else {}
        regras = info.get("RegrasMundo") if isinstance(info, dict) and isinstance(info.get("RegrasMundo"), dict) else {}
        gerais = regras.get("gerais") if isinstance(regras.get("gerais"), dict) else {}
        return max(1, int(gerais.get("camera_px_por_tile", 50) or 50))

    def _sincronizar_tile_px_dimensao(self, dimensao: str) -> None:
        tile_px = 60 if str(dimensao or "").startswith("Dungeon_") else self._tile_px_mundo()
        if int(getattr(self.Camera, "TilePx", tile_px) or tile_px) == tile_px:
            return
        self.Camera.TilePx = int(tile_px)
        normalizar = getattr(self.Camera, "_normalizar_posicao_limites", None)
        if callable(normalizar):
            normalizar()

    def _ao_dimensao_atualizada(self, dimensao: str, forcar_imediato: bool = False) -> None:
        self._sincronizar_tile_px_dimensao(dimensao)
        self.Objetos.definir_dimensao_atual_client(dimensao)
        self.Dungeons.atualizar_dimensao(dimensao, self.Leitor.MetaMundo.get("layout_dungeon") if isinstance(self.Leitor.MetaMundo, dict) else None)
        self.Leitor.forcar_refresh_chunks()
        if bool(forcar_imediato):
            self.Leitor.bombear()

    @property
    def player_local(self):
        return self.Player.player_local

    def montar_player_local(self, dados_player):
        return self.Player.montar_player_local(dados_player)

    def conectar(self, link: str, client_id: str, bootstrap_inicial=None, chunks_bootstrap=None) -> None:
        self.Leitor.conectar_servidor(link)
        self.Leitor.iniciar()
        self.Pacotes.configurar_conexao(link, client_id)
        if isinstance(chunks_bootstrap, dict):
            self.Leitor.processar_pacote_chunks(chunks_bootstrap)
        self._bootstrap_objetos_remotos_iniciais(link, client_id, resposta_precarregada=bootstrap_inicial)
        self.Leitor.preaquecer_chunks_visiveis()
        self.Pacotes.iniciar()

    def _bootstrap_objetos_remotos_iniciais(self, link, client_id, resposta_precarregada=None):
        """Bootstrap one-shot usando o mesmo contrato de pacotes do loop contínuo."""
        raio_chunks = max(1, int(getattr(self.Leitor, "RaioChunks", getattr(self.Leitor, "raio_chunks", 4)) or 4))
        pos_ref = self.Leitor.posicao_referencia()
        resposta = resposta_precarregada if isinstance(resposta_precarregada, dict) else receber_pacotes_tick_mundo(link, client_id, 0, posicao_camera=pos_ref, raio_chunks=raio_chunks)
        if not isinstance(resposta, dict):
            return
        if isinstance(resposta.get("chunks"), list):
            self.Leitor.processar_pacote_chunks({"chunks": resposta.get("chunks", []), "meta": resposta.get("meta", {})})
        self.Pacotes.aplicar_meta_servidor(resposta.get("meta"))
        pacotes = resposta.get("pacotes", []) if isinstance(resposta.get("pacotes"), list) else []
        maior_tick_real = int(getattr(self.Pacotes, "_ultimo_tick_recebido", 0) or 0)
        for pacote_tick in pacotes:
            if not isinstance(pacote_tick, dict):
                continue
            self.Pacotes._distribuir_pacote_tick(pacote_tick)
            if bool(pacote_tick.get("sintetico", False)):
                continue
            tick = int(pacote_tick.get("tick", 0) or 0)
            if tick > maior_tick_real:
                maior_tick_real = tick
        self.Pacotes._ultimo_tick_recebido = int(maior_tick_real)

    def atualizar_frame(self, eventos, dt, bloqueio_gameplay: bool) -> None:
        controle = getattr(self.player_local, "Controle", None) if self.player_local is not None else None
        self._sincronizar_tile_px_dimensao(str(self.Objetos.dimensao_atual_client() or "Mundo"))
        self.Leitor.atualizar_regras_mundo(controle)
        self.Player.atualizar_frame(eventos, dt, self.Camera, bloqueado=bloqueio_gameplay)
        self.Leitor.bombear()
        self.Leitor.bombear_preaquecimento(max_chunks=1)
        self.Pacotes.bombear(max_ciclos=1)
        layout_dungeon = self.Leitor.MetaMundo.get("layout_dungeon") if isinstance(self.Leitor.MetaMundo, dict) else {}
        self.Objetos.definir_layout_dungeon_atual(layout_dungeon)
        dim_local = str(self.Objetos.dimensao_atual_client() or "Mundo")
        self._sincronizar_tile_px_dimensao(dim_local)
        if dim_local.startswith("Dungeon_"):
            self.Dungeons.atualizar_dimensao(dim_local, layout_dungeon)
        definir_layout = getattr(self.Camera, "definir_layout_dungeon", None)
        if callable(definir_layout):
            definir_layout(layout_dungeon)
        ignorar_id = getattr(self.player_local, "Id", None) if self.player_local is not None else None
        player_pos = tuple(self.player_local.Posicao) if self.player_local is not None else None
        self.Objetos.atualizar_visuais(dt, self.Camera, ignorar_id=ignorar_id, player_pos=player_pos)

    def renderizar(self, tela) -> None:
        dim_local = str(self.Objetos.dimensao_atual_client() or "Mundo")
        if dim_local == "Mundo":
            self.Leitor.renderizar_mundo(tela)
        elif dim_local.startswith("Dungeon_"):
            self.Leitor.renderizar_mundo(tela)
            renderizar_dungeon(tela, self.Camera, self.Leitor.MetaMundo.get("layout_dungeon") if isinstance(self.Leitor.MetaMundo, dict) else {})
        if dim_local.startswith("Estadio"):
            self.Objetos.renderizar_estadio_interior(tela, self.Camera)
        ignorar_id = getattr(self.player_local, "Id", None) if self.player_local is not None else None
        player_pos = tuple(self.player_local.Posicao) if self.player_local is not None else None
        self.Objetos.renderizar_entidades(tela, self.Camera, ignorar_id=ignorar_id, player_pos=player_pos)
        self.Player.renderizar(tela, self.Camera)
        if not dim_local.startswith("Dungeon_"):
            self.Objetos.renderizar_estruturas(tela, self.Camera)
        if dim_local.startswith("Dungeon_"):
            player_pos = tuple(self.player_local.Posicao) if self.player_local is not None else None
            layout = self.Leitor.MetaMundo.get("layout_dungeon") if isinstance(self.Leitor.MetaMundo, dict) else {}
            self.Dungeons.renderizar_mascara_sala(tela, self.Camera, player_pos, layout)

    def tempo_mundo_atual(self) -> dict:
        return self.Pacotes.tempo_mundo_atual() if self.Pacotes is not None else {"dia": 0, "hora": 8, "minuto": 0, "chuva_intensidade": 0}

    def parar(self, server_link: str, client_id: str) -> None:
        self.Pacotes.parar()
        self.Leitor.parar()
        if not self._desconectado and server_link:
            desconectar_mundo(server_link, client_id)
        self._desconectado = True
