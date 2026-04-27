from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pygame

from Codigo.Paineis.PainelEstatisticas import PainelEstatisticas
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto
from Codigo.Server.ServerMenu import obter_estatisticas_player


class _AtorContaAdapter:
    def __init__(self, payload: dict):
        dados = dict(payload or {})
        perfil_src = dict(dados.get("perfil") or {})
        inventario_src = dict(dados.get("inventario") or {})

        self.Nome = str(dados.get("nome") or "Treinador")
        self.NomeSkin = str(dados.get("nome_skin") or "S1.png")
        self.Perfil = SimpleNamespace(
            BatalhasPVPVencidas=int(perfil_src.get("batalhas_pvp_vencidas", 0) or 0),
            BatalhasBotVencidas=int(perfil_src.get("batalhas_bot_vencidas", 0) or 0),
            BatalhasTotais=int(perfil_src.get("batalhas_totais", 0) or 0),
            TempoJogoSegundos=float(perfil_src.get("tempo_jogo_segundos", 0.0) or 0.0),
            BausAbertos=int(perfil_src.get("baus_abertos", 0) or 0),
            Maestria=int(perfil_src.get("maestria", 0) or 0),
            NivelMochila=int(perfil_src.get("nivel_mochila", 1) or 1),
            LimitePokemons=int(perfil_src.get("limite_pokemons", 64) or 64),
            Nivel=int(perfil_src.get("nivel", 0) or 0),
            XP=int(perfil_src.get("xp", 0) or 0),
            XPAlvo=int(perfil_src.get("xp_alvo", 0) or 0),
            Dinheiro=int(perfil_src.get("dinheiro", 0) or 0),
            SkinsLiberadas=list(perfil_src.get("skins_liberadas") or []),
            HabilidadesAprendidas=list(perfil_src.get("habilidades_aprendidas") or []),
            TapaPorSegundo=2.0,
            LimiteTimesPokemon=6,
        )
        self.Inventario = SimpleNamespace(
            Pokemons=list(inventario_src.get("pokemons") or []),
            Itens=list(inventario_src.get("itens") or []),
            TimesPokemons=list(inventario_src.get("times_pokemon") or []),
            LimitePokemons=int(perfil_src.get("limite_pokemons", 64) or 64),
            LimiteTimesPokemon=6,
        )

    def set_skin(self, _surface):
        return None


class TelaConta:
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
        self._modo = "lista"
        self._ator_por_servidor = {}
        self._painel_estatisticas = PainelEstatisticas(None)

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
        if self._modo == "servidor":
            self._modo = "lista"
            self._painel_estatisticas.on_close()
            return
        if callable(self._voltar_callback):
            self._voltar_callback()

    def _deslogar(self):
        if callable(self._deslogar_callback):
            self._deslogar_callback()

    def _selecionar_servidor(self, server_id):
        self._servidor_selecionado = str(server_id or "")
        if not self._servidor_selecionado:
            return
        if self._servidor_selecionado not in self._ator_por_servidor:
            usuario = str(self._conta_info().get("usuario") or self._jogo.CONFIG.get("Usuario") or "").strip()
            resposta = obter_estatisticas_player(self._servidor_selecionado, usuario)
            if resposta.get("status") == "ok" and isinstance(resposta.get("ator"), dict):
                self._ator_por_servidor[self._servidor_selecionado] = _AtorContaAdapter(resposta.get("ator"))
        ator = self._ator_por_servidor.get(self._servidor_selecionado)
        if ator is not None:
            self._painel_estatisticas.Ator = ator
            self._modo = "servidor"

    def _processar_scroll(self, eventos):
        if self._modo != "lista" or not self._area_lista.collidepoint(pygame.mouse.get_pos()):
            return
        for evento in eventos:
            if evento.type == pygame.MOUSEWHEEL:
                self._scroll = max(0, min(self._max_scroll, self._scroll - evento.y * 36))
                self._cache = None

    def _render_lista(self, tela, eventos, dt):
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

        old_clip = tela.get_clip()
        tela.set_clip(self._area_lista)
        for botao in self._botoes_servidor:
            botao.render(tela, eventos, dt, JOGO=self._jogo)
        tela.set_clip(old_clip)

        self._botao_voltar.render(tela, eventos, dt, JOGO=self._jogo)
        self._botao_deslogar.render(tela, eventos, dt, JOGO=self._jogo)

    def _render_servidor(self, tela, eventos, dt):
        area = pygame.Rect(int(tela.get_width() * 0.06), int(tela.get_height() * 0.08), int(tela.get_width() * 0.88), int(tela.get_height() * 0.74))
        self._painel_estatisticas.renderizar(tela, area, eventos=eventos, dt=dt)
        self._botao_voltar.render(tela, eventos, dt, JOGO=self._jogo)
        self._botao_deslogar.render(tela, eventos, dt, JOGO=self._jogo)

    def render(self, tela, eventos, dt):
        self._processar_scroll(eventos)
        self._montar_layout(tela.get_size())

        if self._modo == "servidor" and self._painel_estatisticas.Ator is not None:
            self._render_servidor(tela, eventos, dt)
            return

        self._render_lista(tela, eventos, dt)
