"""Maestro único da cena de mundo no client."""

from __future__ import annotations

import math
import random

import pygame

from Codigo.Server.ServerMundo import consultar_chunks_mundo, receber_pacotes_tick_mundo, desconectar_mundo

from .LeitorMundo import LeitorMundo
from .ControladorObjetos import ControladorObjetos
from .ControladorPlayer import ControladorPlayer
from .SistemaPacotes import SistemaPacotes


class ControladorMundo:
    _BIOMA_POR_BLOCO = {
        2: "Vale",
        3: "Vale",
        4: "Praia",
        5: "Deserto",
        6: "Neve",
        7: "Magico",
        8: "Vulcao",
        9: "Pantano",
    }
    _ACUMULO_SEGUNDOS = {
        "Vulcao": 3.0,
        "Neve": 5.0,
        "Magico": 5.0,
        "Pantano": 6.0,
        "Deserto": 7.0,
    }
    _CORES_BIOMA = {
        "Neve": (220, 235, 255),
        "Vulcao": (255, 130, 70),
        "Deserto": (240, 205, 120),
        "Magico": (182, 110, 255),
        "Pantano": (120, 128, 116),
    }

    def __init__(self, jogo, camera):
        self.JOGO = jogo
        self.Camera = camera
        self.Objetos = ControladorObjetos()
        self.Player = ControladorPlayer(self.Objetos)
        self.Leitor = LeitorMundo(
            jogo=jogo,
            camera=camera,
            callback_atualizacao=consultar_chunks_mundo,
            callback_dimensao_atual=self.Objetos.definir_dimensao_atual_client,
            intervalo_poll=0.20,
            raio_chunks=4,
        )
        self.Pacotes = SistemaPacotes(self.Objetos, self.Player, self.Leitor, camera, callback_ciclo=self.atualizar_estado_ciclo_servidor)
        self.EstadoCicloServidor = {"dia": 0, "hora": 8, "minuto": 0, "chuva_intensidade": 0}
        self._acumuladores_bioma = {"Neve": 10.0, "Vulcao": 5.0, "Deserto": 0.0, "Magico": 0.0, "Pantano": 0.0}
        self._timers_bioma = {k: 0.0 for k in self._acumuladores_bioma.keys()}
        self._rng_chuva = random.Random(137)
        self._overlay_surface = None
        self._overlay_size = (0, 0)
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
        self.atualizar_estado_ciclo_servidor(resposta.get("ciclo"))
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

    def atualizar_estado_ciclo_servidor(self, ciclo: dict | None) -> None:
        if not isinstance(ciclo, dict):
            return
        self.EstadoCicloServidor = {
            "dia": int(ciclo.get("dia", self.EstadoCicloServidor.get("dia", 0)) or 0),
            "hora": int(ciclo.get("hora", self.EstadoCicloServidor.get("hora", 8)) or 0),
            "minuto": int(ciclo.get("minuto", self.EstadoCicloServidor.get("minuto", 0)) or 0),
            "chuva_intensidade": max(0, min(100, int(ciclo.get("chuva_intensidade", self.EstadoCicloServidor.get("chuva_intensidade", 0)) or 0))),
        }

    def atualizar_frame(self, eventos, dt, bloqueio_gameplay: bool) -> None:
        controle = getattr(self.player_local, "Controle", None) if self.player_local is not None else None
        self.Leitor.atualizar_regras_mundo(controle)
        self.Player.atualizar_frame(eventos, dt, self.Camera, bloqueado=bloqueio_gameplay)

    def _bloco_player(self) -> int:
        player = self.player_local
        if player is None:
            return 0
        try:
            px, py = float(player.Posicao[0]), float(player.Posicao[1])
        except Exception:
            return 0
        bx, by = int(math.floor(px)), int(math.floor(py))
        chunk_blocos = max(1, int(getattr(self.Leitor, "TamanhoChunkBlocos", 10) or 10))
        cx, cy = int(bx // chunk_blocos), int(by // chunk_blocos)
        grid = getattr(self.Leitor, "Chunks", {}).get((cx, cy), [])
        if not grid:
            return 0
        lx, ly = bx - (cx * chunk_blocos), by - (cy * chunk_blocos)
        if ly < 0 or ly >= len(grid):
            return 0
        row = grid[ly]
        if lx < 0 or lx >= len(row):
            return 0
        try:
            return int(row[lx])
        except (TypeError, ValueError):
            return 0

    def _atualizar_acumuladores_bioma(self, dt: float, bioma_atual: str) -> None:
        for bioma, valor in list(self._acumuladores_bioma.items()):
            if bioma == bioma_atual:
                self._timers_bioma[bioma] += dt
                periodo = float(self._ACUMULO_SEGUNDOS.get(bioma, 99999.0))
                while self._timers_bioma[bioma] >= periodo:
                    self._timers_bioma[bioma] -= periodo
                    valor += 1.0
            else:
                self._timers_bioma[bioma] = 0.0
                valor -= 2.0 * dt
            self._acumuladores_bioma[bioma] = max(0.0, min(100.0, float(valor)))

    @staticmethod
    def _luz_dia(hora: int, minuto: int) -> float:
        total_min = ((int(hora) % 24) * 60) + (int(minuto) % 60)
        ciclo = math.cos((2.0 * math.pi * (float(total_min) - 750.0)) / 1440.0)
        return 0.35 + (0.65 * ((ciclo + 1.0) * 0.5))

    def _obter_overlay(self, tela):
        size = tela.get_size()
        if self._overlay_surface is None or self._overlay_size != size:
            self._overlay_surface = pygame.Surface(size, pygame.SRCALPHA)
            self._overlay_size = size
        return self._overlay_surface

    def _aplicar_overlays_visuais(self, tela, dt: float) -> None:
        if not bool(self.JOGO.CONFIG.get("GraficosBons", True)):
            return
        bloco = self._bloco_player()
        bioma = self._BIOMA_POR_BLOCO.get(bloco, "Vale")
        bioma_visual = bioma if bioma in self._acumuladores_bioma else ""
        self._atualizar_acumuladores_bioma(max(0.0, float(dt)), bioma_visual)

        ciclo = self.EstadoCicloServidor
        luz = self._luz_dia(int(ciclo.get("hora", 12) or 12), int(ciclo.get("minuto", 0) or 0))
        chuva = max(0.0, min(100.0, float(ciclo.get("chuva_intensidade", 0) or 0)))

        overlay = self._obter_overlay(tela)
        w, h = overlay.get_size()
        overlay.fill((0, 0, 0, 0))

        alpha_escuro = int(max(0.0, (1.0 - luz) * 145.0))
        if alpha_escuro > 0:
            overlay.fill((8, 12, 20, alpha_escuro))

        intensidade = float(self._acumuladores_bioma.get(bioma_visual, 0.0)) / 100.0
        if intensidade > 0.0:
            r, g, b = self._CORES_BIOMA.get(bioma_visual, (0, 0, 0))
            overlay.fill((r, g, b, int(12 + (55 * intensidade))), special_flags=pygame.BLEND_RGBA_ADD)

        chuva_norm = chuva / 100.0
        if chuva_norm > 0.01:
            overlay.fill((95, 110, 135, int(18 + (24 * chuva_norm))), special_flags=pygame.BLEND_RGBA_ADD)
            gotas = int(50 + (190 * chuva_norm))
            for _ in range(gotas):
                x = self._rng_chuva.randrange(0, max(1, w))
                y = self._rng_chuva.randrange(0, max(1, h))
                pygame.draw.line(overlay, (188, 205, 230, int(38 + 100 * chuva_norm)), (x, y), (x - 2, y + 7), 1)

        tela.blit(overlay, (0, 0))

    def renderizar(self, tela, dt: float = 1.0 / 30.0) -> None:
        self.Leitor.renderizar_mundo(tela)
        self.Objetos.renderizar_estadio_interior(tela, self.Camera)
        ignorar_id = getattr(self.player_local, "Id", None) if self.player_local is not None else None
        player_pos = tuple(self.player_local.Posicao) if self.player_local is not None else None
        self.Objetos.renderizar_entidades(tela, self.Camera, ignorar_id=ignorar_id, player_pos=player_pos)
        self.Player.renderizar(tela, self.Camera)
        self.Objetos.renderizar_estruturas(tela, self.Camera)
        self._aplicar_overlays_visuais(tela, dt=dt)

    def parar(self, server_link: str, client_id: str) -> None:
        self.Pacotes.parar()
        self.Leitor.parar()
        if not self._desconectado and server_link:
            desconectar_mundo(server_link, client_id)
        self._desconectado = True
