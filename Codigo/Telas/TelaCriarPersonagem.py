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

_GRUPOS_INICIAIS = [
    ("Fogo", _INICIAIS_FOGO),
    ("Planta", _INICIAIS_PLANTA),
    ("Água", _INICIAIS_AGUA),
]

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


def _scale_to_fit_keep_ratio(img: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    if max_w <= 0 or max_h <= 0:
        return img
    w, h = img.get_size()
    if w <= 0 or h <= 0:
        return img
    scale = min(max_w / w, max_h / h, 1.0)  # só reduz, nunca aumenta
    if abs(scale - 1.0) < 1e-6:
        return img
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return pygame.transform.smoothscale(img, (nw, nh)).convert_alpha()


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
        self._fps_anim = 18.0  # mais rápida

        self._thread = None
        self._resultado = None

        self._titulo = None
        self._mensagem = Texto("Escolha sua skin e seu inicial", (0, 0), style={"size": 24, "align": "center"})

        self.barra_skin = None

        self._botoes_grupos = []
        self._botoes_flat = []

        self.botao_voltar = None
        self.botao_criar = None

        self._quadro_skin = pygame.Rect(0, 0, 0, 0)
        self._quadro_anim = pygame.Rect(0, 0, 0, 0)

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

            icones[nome] = pygame.transform.smoothscale(img, (62, 62)).convert_alpha()
        return icones

    def _carregar_animacoes_pokemon(self):
        animacoes = {}
        for nome in _LISTA_INICIAIS:
            pasta = os.path.join("Recursos", "Visual", "Pokemons", "Animação", nome.lower())
            frames = []

            if os.path.isdir(pasta):
                arquivos = [arq for arq in os.listdir(pasta) if arq.lower().endswith(".png")]

                def _key(n):
                    base = n.rsplit(".", 1)[0]
                    if "_" in base:
                        tail = base.rsplit("_", 1)[-1]
                        if tail.isdigit():
                            return int(tail)
                    return 0

                arquivos.sort(key=_key)

                for arq in arquivos:
                    caminho = os.path.join(pasta, arq)
                    try:
                        frames.append(pygame.image.load(caminho).convert_alpha())
                    except pygame.error:
                        pass

            if not frames:
                frames = [self._icones_pokemon[nome]]

            animacoes[nome] = frames
        return animacoes

    def _rebuild_layout(self, tela_size):
        largura, altura = tela_size

        self._overlay_size = tela_size
        self._overlay = pygame.Surface(tela_size, pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 170))

        # um pouco menor que antes, e com mais respiro interno
        painel_w = min(920, int(largura * 0.82))
        painel_h = min(660, int(altura * 0.80))
        self._painel = pygame.Rect(0, 0, painel_w, painel_h)
        self._painel.center = (largura // 2, altura // 2)

        pad = 34
        x0 = self._painel.left + pad
        y0 = self._painel.top + pad

        # topo
        self._titulo = Texto("Criar Personagem", (self._painel.centerx, y0), style={"size": 42, "align": "center"})
        self._mensagem.set_pos((self._painel.centerx, y0 + 46))

        # ====== medidas do grid (3 blocos 2x2 lado a lado) ======
        btn = 74
        gap_in = 12
        gap_blocos = 22

        bloco_w = (btn * 2) + gap_in
        bloco_h = (btn * 2) + gap_in
        grid_w = (bloco_w * 3) + (gap_blocos * 2)

        # coluna direita com quadros, mas sem invadir / sobrepor
        col_gap = 26
        col_dir_x = x0 + grid_w + col_gap

        # se a tela for estreita, "puxa" grid e quadros pra dentro
        max_right = self._painel.right - pad
        if col_dir_x + 220 > max_right:
            # diminui gaps pra caber (sem destruir layout)
            shrink = (col_dir_x + 220) - max_right
            gap_blocos = max(12, gap_blocos - shrink // 3)
            col_gap = max(16, col_gap - shrink // 2)

            bloco_w = (btn * 2) + gap_in
            bloco_h = (btn * 2) + gap_in
            grid_w = (bloco_w * 3) + (gap_blocos * 2)
            col_dir_x = x0 + grid_w + col_gap

        # ====== barra skin (mesma largura do grid) ======
        barra_h = 34
        barra_y = y0 + 90
        self.barra_skin = Barra(
            pygame.Rect(x0, barra_y, grid_w, barra_h),
            "Skin",
            self._skin_index + 1,
            1,
            len(self._skins),
            casas_decimais=0,
        )

        # quadro da skin (direita, alinhado com barra)
        self._quadro_skin = pygame.Rect(col_dir_x, barra_y - 6, 220, 200)

        # ====== blocos pokemon (abaixo da barra) ======
        blocos_y = barra_y + barra_h + 54  # mais espaço => não encosta nos títulos
        self._botoes_grupos = []
        self._botoes_flat = []

        for gi, (nome_grupo, lista_pokes) in enumerate(_GRUPOS_INICIAIS):
            bloco_x = x0 + gi * (bloco_w + gap_blocos)
            container = pygame.Rect(bloco_x, blocos_y, bloco_w, bloco_h)

            rects = []
            for i in range(4):
                col = i % 2
                row = i // 2
                rx = bloco_x + col * (btn + gap_in)
                ry = blocos_y + row * (btn + gap_in)
                rects.append(pygame.Rect(rx, ry, btn, btn))

            for poke_nome, rect in zip(lista_pokes, rects):
                self._botoes_flat.append((poke_nome, rect))

            # título do bloco com espaço garantido
            titulo_pos = (container.centerx, container.top - 24)
            self._botoes_grupos.append(
                {
                    "nome_grupo": nome_grupo,
                    "pokemon": lista_pokes,
                    "rects": rects,
                    "container": container,
                    "titulo_pos": titulo_pos,
                }
            )

        # ====== quadro animação (direita, alinhado com os blocos) ======
        # posiciona pelo top dos blocos, e deixa um espaço pro nome do pokemon
        self._quadro_anim = pygame.Rect(col_dir_x, blocos_y + 16, 220, 200)

        # rodapé
        y_rodape = self._painel.bottom - 78
        self.botao_voltar = Botao(
            pygame.Rect(self._painel.left + pad, y_rodape, 210, 58),
            "Voltar",
            execute=self._voltar,
            style=_ESTILO_BOTAO,
        )
        self.botao_criar = Botao(
            pygame.Rect(self._painel.right - pad - 210, y_rodape, 210, 58),
            "Criar",
            execute=self._criar,
            style=_ESTILO_BOTAO,
        )

        # se quadros encostarem no rodapé em telas muito baixas, sobe um pouco tudo dos blocos
        bottom_safe = y_rodape - 22
        if self._quadro_anim.bottom > bottom_safe:
            dy = self._quadro_anim.bottom - bottom_safe
            self._quadro_anim.move_ip(0, -dy)
            # opcional: sobe um pouco o quadro skin também pra manter coerência visual
            self._quadro_skin.move_ip(0, -max(0, dy // 2))

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

    def _render_grupos_pokemon(self, tela, eventos):
        mouse = pygame.mouse.get_pos()

        # “plaquinha” por trás do texto do grupo (fica mais organizado visualmente)
        for grp in self._botoes_grupos:
            cx, cy = grp["titulo_pos"]
            placa = pygame.Rect(0, 0, grp["container"].width, 22)
            placa.center = (cx, cy + 2)
            pygame.draw.rect(tela, (18, 26, 48), placa, border_radius=10)
            pygame.draw.rect(tela, (95, 110, 150), placa, 2, border_radius=10)

            t = Texto(grp["nome_grupo"], grp["titulo_pos"], style={"size": 22, "align": "center"})
            t.draw(tela)

        selecionado_nome = _LISTA_INICIAIS[self._pokemon_index]

        for poke_nome, rect in self._botoes_flat:
            hover = rect.collidepoint(mouse)
            selecionado = poke_nome == selecionado_nome

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

            icone = self._icones_pokemon[poke_nome]
            icon_rect = icone.get_rect(center=rect.center)
            tela.blit(icone, icon_rect)

        for ev in eventos:
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                for poke_nome, rect in self._botoes_flat:
                    if rect.collidepoint(ev.pos):
                        self._pokemon_index = _LISTA_INICIAIS.index(poke_nome)
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

        # barra skin
        if self.barra_skin.render(tela, eventos):
            novo_indice = int(round(self.barra_skin.valor)) - 1
            novo_indice = max(0, min(novo_indice, len(self._skins) - 1))
            if novo_indice != self._skin_index:
                self._skin_index = novo_indice
                self._desenhador.set_skin(self._skins[self._skin_index])
        else:
            self.barra_skin.set_valor(self._skin_index + 1)

        # quadro skin
        pygame.draw.rect(tela, (20, 29, 52), self._quadro_skin, border_radius=14)
        pygame.draw.rect(tela, (95, 110, 150), self._quadro_skin, 2, border_radius=14)
        self._desenhador.desenhar(tela, self._quadro_skin.center, pygame.mouse.get_pos())

        # blocos pokemon
        self._render_grupos_pokemon(tela, eventos)

        # quadro animação + nome do pokemon (sem sobrepor)
        nome_poke = _LISTA_INICIAIS[self._pokemon_index]
        texto_poke = Texto(
            nome_poke,
            (self._quadro_anim.centerx, self._quadro_anim.top - 26),
            style={"size": 26, "align": "center"},
        )
        texto_poke.draw(tela)

        pygame.draw.rect(tela, (20, 29, 52), self._quadro_anim, border_radius=14)
        pygame.draw.rect(tela, (95, 110, 150), self._quadro_anim, 2, border_radius=14)

        frames = self._animacoes_pokemon[nome_poke]
        self._tempo_anim += dt
        if self._tempo_anim >= 1.0 / self._fps_anim:
            self._tempo_anim = 0.0
            self._frame_anim = (self._frame_anim + 1) % len(frames)

        frame = frames[self._frame_anim]

        margem = 16
        max_w = self._quadro_anim.width - (margem * 2)
        max_h = self._quadro_anim.height - (margem * 2)
        frame_fit = _scale_to_fit_keep_ratio(frame, max_w, max_h)

        rect_frame = frame_fit.get_rect(center=self._quadro_anim.center)
        tela.blit(frame_fit, rect_frame)

        bloqueado = self._thread is not None and self._thread.is_alive()
        self.botao_criar.set_habilitado(not bloqueado)
        self.botao_voltar.set_habilitado(not bloqueado)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_criar.render(tela, eventos, dt, JOGO=JOGO)