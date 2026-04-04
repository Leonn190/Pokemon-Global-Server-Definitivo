"""Maestro único da cena de mundo no client."""

from __future__ import annotations

from Codigo.Server.ServerMundo import consultar_chunks_mundo, receber_pacotes_tick_mundo, desconectar_mundo

from .LeitorMundo import LeitorMundo
from .ControladorObjetos import ControladorObjetos
from .ControladorPlayer import ControladorPlayer
from .SistemaPacotes import SistemaPacotes


class ControladorMundo:
    def __init__(self, jogo, camera):
        self.JOGO = jogo
        self.Camera = camera
        self.Objetos = ControladorObjetos()
        self.Player = ControladorPlayer(self.Objetos)
        self.Leitor = LeitorMundo(jogo=jogo, camera=camera, callback_atualizacao=consultar_chunks_mundo, intervalo_poll=0.20, raio_chunks=4)
        self.Pacotes = SistemaPacotes(self.Objetos, self.Player, self.Leitor, camera)
        self._desconectado = False

    @property
    def player_local(self):
        return self.Player.player_local

    def montar_player_local(self, dados_player):
        return self.Player.montar_player_local(dados_player)

    def conectar(self, link: str, client_id: str) -> None:
        self.Leitor.conectar_servidor(link)
        self.Leitor.iniciar()
        self.Pacotes.configurar_conexao(link, client_id)
        self._bootstrap_objetos_remotos_iniciais(link, client_id)
        self.Pacotes.iniciar()

    def _bootstrap_objetos_remotos_iniciais(self, link, client_id):
        """Bootstrap one-shot usando o mesmo contrato de pacotes do loop contínuo."""
        raio_chunks = max(1, int(getattr(self.Leitor, "RaioChunks", getattr(self.Leitor, "raio_chunks", 4)) or 4))
        resposta = receber_pacotes_tick_mundo(link, client_id, 0, posicao_camera=self.Camera.PosicaoTiles, raio_chunks=raio_chunks)
        if not isinstance(resposta, dict):
            return
        if isinstance(resposta.get("chunks"), list):
            self.Leitor.processar_pacote_chunks({"chunks": resposta.get("chunks", []), "meta": resposta.get("meta", {})})
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
        self.Leitor.atualizar_regras_mundo(controle)
        self.Player.atualizar_frame(eventos, dt, self.Camera, bloqueado=bloqueio_gameplay)

    def renderizar(self, tela) -> None:
        self.Leitor.renderizar_mundo(tela)
        self.Objetos.renderizar_estadio_interior(tela, self.Camera)
        ignorar_id = getattr(self.player_local, "Id", None) if self.player_local is not None else None
        player_pos = tuple(self.player_local.Posicao) if self.player_local is not None else None
        self.Objetos.renderizar_entidades(tela, self.Camera, ignorar_id=ignorar_id, player_pos=player_pos)
        self.Player.renderizar(tela, self.Camera)
        self.Objetos.renderizar_estruturas(tela, self.Camera)

    def parar(self, server_link: str, client_id: str) -> None:
        self.Pacotes.parar()
        self.Leitor.parar()
        if not self._desconectado and server_link:
            desconectar_mundo(server_link, client_id)
        self._desconectado = True
