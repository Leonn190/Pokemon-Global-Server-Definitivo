import os
import threading

import pygame

from Codigo.Modulos.DesenhaPlayer import DesenhaPlayer
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto
from Codigo.Server.ServerMenu import criar_personagem

_SKINS_LIBERADAS = [f"S{i}.png" for i in range(1, 13)]

_INICIAIS_FOGO = ["Charmander", "Torchic", "Fennekin", "Litten"]
_INICIAIS_PLANTA = ["Bulbasaur", "Treecko", "Chespin", "Rowlet"]
_INICIAIS_AGUA = ["Squirtle", "Mudkip", "Froakie", "Popplio"]
_LISTA_INICIAIS = _INICIAIS_FOGO + _INICIAIS_PLANTA + _INICIAIS_AGUA

_ESTILO_BOTAO = {
    "radius": 16,
    "border_width": 2,
    "border": (26, 34, 62),
    "border_hover": (255, 220, 120),
    "bg": (25, 34, 60),
    "bg_hover": (40, 53, 90),
    "bg_pressed": (18, 25, 45),
    "hover_scale": 1.03,
    "press_scale": 0.97,
    "text_style": {
        "size": 28,
        "color": (245, 246, 255),
        "hover_color": (255, 226, 120),
        "outline": True,
        "outline_color": (0, 0, 0),
        "outline_thickness": 1,
        "shadow": True,
        "shadow_color": (0, 0, 0, 160),
        "shadow_offset": (2, 2),
    },
}


class SubtelaCriarPersonagem:
    def __init__(self, tela_size, ip_server, usuario, concluir_callback=None, voltar_callback=None):
        self.ip_server = ip_server
        self.usuario = usuario
        self.concluir_callback = concluir_callback
        self.voltar_callback = voltar_callback
        self.encerrada = False

        self._overlay = None
        self._overlay_size = (0, 0)
        self._painel = pygame.Rect(0, 0, 0, 0)

        self._skin_index = 0
        self._pokemon_index = 0

        self._skins = self._carregar_skins()
        self._desenhador = DesenhaPlayer(self._skins[self._skin_index], escala=3.0)
        self._icones_pokemon = self._carregar_icones_pokemon()
        self._animacoes_pokemon = self._carregar_animacoes_pokemon()

        self._frame_anim = 0
        self._tempo_anim = 0.0
        self._fps_anim = 10.0

        self._thread = None
        self._resultado = None
        self._mensagem = Texto("Escolha sua skin e seu inicial", (0, 0), style={"size": 24, "align": "center"})

        self.barra_skin = None
        self.botoes_pokemon = []
        self.botao_voltar = None
        self.botao_criar = None

        self._rebuild_layout(tela_size)

    def _carregar_skins(self):
        skins = []
        for nome in _SKINS_LIBERADAS:
            caminho = os.path.join("Recursos", "Visual", "Skins", "Liberadas", nome)
            try:
                skins.append(pygame.image.load(caminho).convert_alpha())
            except pygame.error:
                fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
                fallback.fill((190, 220, 255))
                skins.append(fallback)
        return skins

    def _carregar_icones_pokemon(self):
        icones = {}
        for nome in _LISTA_INICIAIS:
            caminho = os.path.join("Recursos", "Visual", "Pokemons", "Imagens", f"{nome.lower()}.png")
            try:
                img = pygame.image.load(caminho).convert_alpha()
            except pygame.error:
                img = pygame.Surface((64, 64), pygame.SRCALPHA)
                img.fill((35, 38, 50))
                pygame.draw.circle(img, (230, 230, 230), (32, 32), 24)
            icones[nome] = pygame.transform.smoothscale(img, (76, 76)).convert_alpha()
        return icones

    def _carregar_animacoes_pokemon(self):
        animacoes = {}
        for nome in _LISTA_INICIAIS:
            pasta = os.path.join("Recursos", "Visual", "Pokemons", "Animação", nome.lower())
            frames = []
            if os.path.isdir(pasta):
                arquivos = [arq for arq in os.listdir(pasta) if arq.lower().endswith(".png")]
                arquivos.sort(key=lambda n: int(n.rsplit("_", 1)[-1].split(".")[0]) if "_" in n else 0)
                for arq in arquivos:
                    caminho = os.path.join(pasta, arq)
                    try:
                        frames.append(pygame.image.load(caminho).convert_alpha())
                    except pygame.error:
                        pass

            if not frames:
                frames = [self._icones_pokemon[nome]]

            animacoes[nome] = [pygame.transform.smoothscale(frame, (168, 168)).convert_alpha() for frame in frames]
        return animacoes

    def _rebuild_layout(self, tela_size):
        largura, altura = tela_size
        self._overlay_size = tela_size
        self._overlay = pygame.Surface(tela_size, pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 170))

        self._painel = pygame.Rect(0, 0, min(1240, int(largura * 0.92)), min(900, int(altura * 0.92)))
        self._painel.center = (largura // 2, altura // 2)

        x0 = self._painel.left + 40
        y0 = self._painel.top + 40

        self._titulo = Texto("Criar Personagem", (self._painel.centerx, y0), style={"size": 44, "align": "center"})
        self._mensagem.set_pos((self._painel.centerx, y0 + 52))

        self.barra_skin = Barra(
            pygame.Rect(x0, y0 + 95, 410, 34),
            "Skin",
            self._skin_index + 1,
            1,
            len(self._skins),
            casas_decimais=0,
        )

        self._quadro_skin = pygame.Rect(x0 + 450, y0 + 70, 280, 250)

        self._quadro_anim = pygame.Rect(self._painel.right - 260, y0 + 340, 210, 210)

        self.botoes_pokemon = []
        y_btn = y0 + 360
        x_btn = x0
        largura_btn = 86
        altura_btn = 86
        espacamento = 12
        por_linha = 6

        for i, nome in enumerate(_LISTA_INICIAIS):
            col = i % por_linha
            row = i // por_linha
            rect = pygame.Rect(x_btn + col * (largura_btn + espacamento), y_btn + row * (altura_btn + espacamento), largura_btn, altura_btn)
            self.botoes_pokemon.append((nome, rect))

        y_rodape = self._painel.bottom - 90
        self.botao_voltar = Botao(pygame.Rect(self._painel.left + 40, y_rodape, 220, 62), "Voltar", execute=self._voltar, style=_ESTILO_BOTAO)
        self.botao_criar = Botao(pygame.Rect(self._painel.right - 260, y_rodape, 220, 62), "Criar", execute=self._criar, style=_ESTILO_BOTAO)

    def _voltar(self, jogo, botao):
        if callable(self.voltar_callback):
            self.voltar_callback()
        self.encerrada = True

    def _worker_criar(self, skin_nome, pokemon_nome):
        self._resultado = criar_personagem(self.ip_server, self.usuario, skin_nome, pokemon_nome)

    def _criar(self, jogo, botao):
        if self._thread and self._thread.is_alive():
            return

        skin_nome = _SKINS_LIBERADAS[self._skin_index].replace(".png", "")
        pokemon = _LISTA_INICIAIS[self._pokemon_index]

        self._mensagem.set_text("Registrando personagem no servidor...")
        self._thread = threading.Thread(target=self._worker_criar, args=(skin_nome, pokemon), daemon=True)
        self._resultado = None
        self._thread.start()

    def _processar_resultado(self):
        if not self._resultado:
            return

        resposta = self._resultado
        self._resultado = None
        self._thread = None

        if resposta.get("status") == "ok":
            self._mensagem.set_text(resposta.get("mensagem", "Personagem criado!"))
            if callable(self.concluir_callback):
                self.concluir_callback()
            self.encerrada = True
            return

        self._mensagem.set_text(resposta.get("mensagem", "Falha ao criar personagem"))

    def _render_pokemon_botoes(self, tela, eventos):
        mouse = pygame.mouse.get_pos()

        for i, (nome, rect) in enumerate(self.botoes_pokemon):
            hover = rect.collidepoint(mouse)
            selecionado = i == self._pokemon_index

            cor_bg = (28, 38, 64)
            cor_borda = (80, 96, 130)
            if hover:
                cor_bg = (40, 52, 88)
                cor_borda = (255, 220, 120)
            if selecionado:
                cor_bg = (30, 84, 52)
                cor_borda = (180, 240, 180)

            pygame.draw.rect(tela, cor_bg, rect, border_radius=12)
            pygame.draw.rect(tela, cor_borda, rect, 2, border_radius=12)

            icone = self._icones_pokemon[nome]
            icon_rect = icone.get_rect(center=rect.center)
            tela.blit(icone, icon_rect)

        for ev in eventos:
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                for i, (_, rect) in enumerate(self.botoes_pokemon):
                    if rect.collidepoint(ev.pos):
                        self._pokemon_index = i
                        self._frame_anim = 0
                        self._tempo_anim = 0.0
                        break

    def render(self, tela, eventos, dt, JOGO=None):
        size = tela.get_size()
        if size != self._overlay_size:
            self._rebuild_layout(size)

        self._processar_resultado()

        tela.blit(self._overlay, (0, 0))

        pygame.draw.rect(tela, (15, 22, 42), self._painel, border_radius=20)
        pygame.draw.rect(tela, (255, 220, 120), self._painel, 2, border_radius=20)

        self._titulo.draw(tela)
        self._mensagem.draw(tela)

        if self.barra_skin.render(tela, eventos):
            novo_indice = int(round(self.barra_skin.valor)) - 1
            novo_indice = max(0, min(novo_indice, len(self._skins) - 1))
            if novo_indice != self._skin_index:
                self._skin_index = novo_indice
                self._desenhador.set_skin(self._skins[self._skin_index])
        else:
            self.barra_skin.set_valor(self._skin_index + 1)

        pygame.draw.rect(tela, (20, 29, 52), self._quadro_skin, border_radius=14)
        pygame.draw.rect(tela, (95, 110, 150), self._quadro_skin, 2, border_radius=14)

        centro_skin = self._quadro_skin.center
        self._desenhador.desenhar(tela, centro_skin, pygame.mouse.get_pos())

        self._render_pokemon_botoes(tela, eventos)

        nome_poke = _LISTA_INICIAIS[self._pokemon_index]
        texto_poke = Texto(nome_poke, (self._quadro_anim.centerx, self._quadro_anim.top - 26), style={"size": 30, "align": "center"})
        texto_poke.draw(tela)

        pygame.draw.rect(tela, (20, 29, 52), self._quadro_anim, border_radius=14)
        pygame.draw.rect(tela, (95, 110, 150), self._quadro_anim, 2, border_radius=14)

        frames = self._animacoes_pokemon[nome_poke]
        self._tempo_anim += dt
        if self._tempo_anim >= 1.0 / self._fps_anim:
            self._tempo_anim = 0.0
            self._frame_anim = (self._frame_anim + 1) % len(frames)

        frame = frames[self._frame_anim]
        rect_frame = frame.get_rect(center=self._quadro_anim.center)
        tela.blit(frame, rect_frame)

        bloqueado = self._thread is not None and self._thread.is_alive()
        self.botao_criar.set_habilitado(not bloqueado)
        self.botao_voltar.set_habilitado(not bloqueado)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_criar.render(tela, eventos, dt, JOGO=JOGO)
