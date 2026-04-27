from __future__ import annotations

from datetime import datetime

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class SubtelaConta:
    def __init__(self, jogo, estilo_base, deslogar_callback=None, voltar_callback=None):
        self._jogo = jogo
        self._estilo_base = estilo_base
        self._deslogar_callback = deslogar_callback
        self._voltar_callback = voltar_callback
        self._cache = None
        self._botao_voltar = None
        self._botao_deslogar = None
        self._botoes_servidor = []
        self._scroll = 0
        self._max_scroll = 0
        self._area_lista = pygame.Rect(0, 0, 0, 0)
        self._servidor_selecionado = None

    def _conta_info(self):
        return dict(self._jogo.CONFIG.get("ContaInfo") or {})

    def _data_br(self, texto_iso):
        try:
            return datetime.strptime(str(texto_iso), "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return str(texto_iso or "--")

    def _montar_layout(self, tela_size):
        if self._cache == tuple(tela_size):
            return
        w, h = tela_size
        info = self._conta_info()
        servidores = list(info.get("servidores_registrados") or [])

        self._area_lista = pygame.Rect(int(w * 0.18), int(h * 0.34), int(w * 0.64), int(h * 0.34))

        estilo_servidor = dict(self._estilo_base)
        estilo_servidor["text_style"] = dict(self._estilo_base["text_style"])
        estilo_servidor["text_style"]["size"] = 26

        self._botoes_servidor = []
        y = self._area_lista.y + 8 - self._scroll
        for servidor in servidores:
            sid = str((servidor or {}).get("id") or "")
            nome = str((servidor or {}).get("nome") or sid or "Servidor")
            rect = pygame.Rect(self._area_lista.x + 10, y, self._area_lista.width - 20, 58)
            botao = Botao(rect, nome, execute=lambda jogo, _botao, sid=sid: self._selecionar_servidor(sid), style=estilo_servidor)
            self._botoes_servidor.append(botao)
            y += 66

        altura_total = max(0, len(self._botoes_servidor) * 66 + 16)
        self._max_scroll = max(0, altura_total - self._area_lista.height)
        self._scroll = max(0, min(self._scroll, self._max_scroll))

        estilo_acao = dict(self._estilo_base)
        estilo_acao["text_style"] = dict(self._estilo_base["text_style"])
        estilo_acao["text_style"]["size"] = 34

        largura_acao = 260
        y_acao = int(h * 0.84)
        self._botao_voltar = Botao(
            pygame.Rect(w // 2 - largura_acao - 20, y_acao, largura_acao, 80),
            "Voltar",
            execute=lambda jogo, botao: self._voltar(),
            style=estilo_acao,
        )

        estilo_deslogar = dict(estilo_acao)
        estilo_deslogar["text_style"] = dict(estilo_acao["text_style"])
        estilo_deslogar["bg"] = (105, 38, 38)
        estilo_deslogar["bg_hover"] = (132, 48, 48)
        estilo_deslogar["bg_pressed"] = (86, 30, 30)

        self._botao_deslogar = Botao(
            pygame.Rect(w // 2 + 20, y_acao, largura_acao, 80),
            "Deslogar",
            execute=lambda jogo, botao: self._deslogar(),
            style=estilo_deslogar,
        )

        self._cache = tuple(tela_size)

    def _voltar(self):
        if callable(self._voltar_callback):
            self._voltar_callback()

    def _deslogar(self):
        if callable(self._deslogar_callback):
            self._deslogar_callback()

    def _selecionar_servidor(self, server_id):
        self._servidor_selecionado = str(server_id or "")

    def _processar_scroll(self, eventos):
        if not self._area_lista.collidepoint(pygame.mouse.get_pos()):
            return
        for evento in eventos:
            if evento.type == pygame.MOUSEWHEEL:
                self._scroll = max(0, min(self._max_scroll, self._scroll - evento.y * 36))
                self._cache = None

    def _render_estatisticas_servidor(self, tela):
        if not self._servidor_selecionado:
            return
        info = self._conta_info()
        mapa = dict(info.get("estatisticas_servidores") or {})
        stats = dict(mapa.get(self._servidor_selecionado) or {})

        painel = pygame.Rect(int(tela.get_width() * 0.22), int(tela.get_height() * 0.20), int(tela.get_width() * 0.56), int(tela.get_height() * 0.56))
        pygame.draw.rect(tela, (12, 18, 34), painel, border_radius=16)
        pygame.draw.rect(tela, (86, 112, 170), painel, 2, border_radius=16)

        titulo = Texto(f"Estatísticas - {self._servidor_selecionado}", (painel.centerx, painel.y + 32), style={"size": 34, "align": "center"})
        titulo.draw(tela)

        linhas = [
            f"Perfil: {stats.get('perfil_nome', '--')}",
            f"Nível: {stats.get('nivel', 0)}",
            f"Batalhas: {stats.get('batalhas', 0)}",
            f"Vitórias: {stats.get('vitorias', 0)}",
            f"Maestria: {stats.get('maestria', 0)}",
            f"Poder máximo: {stats.get('poder_maximo', 0)}",
        ]
        for i, linha in enumerate(linhas):
            Texto(linha, (painel.x + 24, painel.y + 86 + i * 56), style={"size": 28, "align": "topleft"}).draw(tela)

    def render(self, tela, eventos, dt):
        self._processar_scroll(eventos)
        self._montar_layout(tela.get_size())

        info = self._conta_info()
        usuario = str(info.get("usuario") or self._jogo.CONFIG.get("Usuario") or "Visitante")
        data_criacao = self._data_br(info.get("data_criacao"))
        servidores = list(info.get("servidores_registrados") or [])

        Texto("Conta", (tela.get_width() // 2, int(tela.get_height() * 0.10)), style={"size": 50, "align": "center", "outline": True, "outline_color": (0, 0, 0), "outline_thickness": 2}).draw(tela)
        Texto(f"Conta: {usuario}", (int(tela.get_width() * 0.18), int(tela.get_height() * 0.20)), style={"size": 30, "align": "topleft"}).draw(tela)
        Texto(f"Criação: {data_criacao}", (int(tela.get_width() * 0.18), int(tela.get_height() * 0.25)), style={"size": 30, "align": "topleft"}).draw(tela)
        Texto(f"Perfis em servidores: {len(servidores)}", (int(tela.get_width() * 0.18), int(tela.get_height() * 0.30)), style={"size": 30, "align": "topleft"}).draw(tela)

        pygame.draw.rect(tela, (10, 15, 28), self._area_lista, border_radius=12)
        pygame.draw.rect(tela, (70, 92, 145), self._area_lista, 1, border_radius=12)

        for botao in self._botoes_servidor:
            if self._area_lista.colliderect(botao.rect):
                botao.render(tela, eventos, dt, JOGO=self._jogo)

        self._botao_voltar.render(tela, eventos, dt, JOGO=self._jogo)
        self._botao_deslogar.render(tela, eventos, dt, JOGO=self._jogo)

        self._render_estatisticas_servidor(tela)
